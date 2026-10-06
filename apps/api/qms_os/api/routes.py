from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Audit, AuditProgram, Department, Finding, Notification, Project, Risk, User, Workpaper
from ..policy import PolicyContext
from ..rules.findings import Role
from ..services import findings as FS
from ..services import policy_gate as G
from ..services import program as PS
from ..services import reports as RP
from ..services import risks as RS
from ..services.common import Forbidden, NotFound, can_see_audit, can_see_finding, can_see_workpapers, get_or_404, \
    require
from .deps import current_user, get_session, policy, public, step_up_user, today

router = APIRouter(prefix="/api")


# ---------- identity & reference data ----------

def user_row(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "department_id": u.department_id,
            "department": u.department.name if u.department else None, "trained_auditor": u.trained_auditor}


@router.get("/health")
def health(_: None = Depends(public), s: Session = Depends(get_session), t: date = Depends(today),
           p: PolicyContext = Depends(policy)):
    """Unauthenticated liveness: mode and policy state only (no policy content)."""
    return {"ok": True, "mode": p.mode.value, "policy_state": G.state(s, p, t)["state"]}


@router.get("/users")
def users(s: Session = Depends(get_session), u: User = Depends(current_user)):
    """Directory of people, for signed-in users."""
    return [user_row(u) for u in s.scalars(select(User).order_by(User.id))]


@router.get("/me")
def me(u: User = Depends(current_user)):
    return user_row(u)


@router.get("/departments")
def departments(s: Session = Depends(get_session), u: User = Depends(current_user)):
    return [{"id": d.id, "code": d.code, "name": d.name, "head_user_id": d.head_user_id}
            for d in s.scalars(select(Department).order_by(Department.id))]


@router.get("/policy")
def get_policy(s: Session = Depends(get_session), u: User = Depends(current_user), t: date = Depends(today),
               p: PolicyContext = Depends(policy)):
    return G.state(s, p, t)


class Note(BaseModel):
    note: str = ""


def submission_row(x) -> dict:
    return {c: getattr(x, c) for c in ("id", "policy_id", "policy_version", "effective_date", "fingerprint", "status",
                                       "submitted_by_id", "submitted_at", "decided_by_id", "decided_by_name",
                                       "decided_role", "decided_at", "decision_note")}


@router.post("/policy/submit")
def submit_policy(body: Note, s: Session = Depends(get_session), u: User = Depends(current_user),
                  p: PolicyContext = Depends(policy)):
    return submission_row(G.submit(s, p, u, body.note))


class PolicyApproveIn(BaseModel):
    fingerprint: str
    confirm_version: str
    note: str = ""


@router.post("/policy/submissions/{submission_id}/approve")
def approve_policy(submission_id: int, body: PolicyApproveIn, s: Session = Depends(get_session),
                   u: User = Depends(step_up_user), p: PolicyContext = Depends(policy)):
    return submission_row(G.approve(s, p, u, submission_id, fingerprint=body.fingerprint,
                                    confirm_version=body.confirm_version, note=body.note))


class RejectIn(BaseModel):
    reason: str = ""


@router.post("/policy/submissions/{submission_id}/reject")
def reject_policy(submission_id: int, body: RejectIn, s: Session = Depends(get_session),
                  u: User = Depends(step_up_user), p: PolicyContext = Depends(policy)):
    return submission_row(G.reject(s, p, u, submission_id, body.reason))


# ---------- audit programme ----------

def audit_row(a: Audit) -> dict:
    return {"id": a.id, "cycle": a.cycle.code, "department_id": a.department_id, "department": a.department.name,
            "auditor_id": a.auditor_id, "auditor": a.auditor.name if a.auditor else None,
            "notify_on": a.notify_on, "evidence_due": a.evidence_due, "audit_date": a.audit_date,
            "report_due": a.report_due, "action_plan_due": a.action_plan_due, "closure_limit": a.closure_limit,
            "status": a.status, "reported_on": a.reported_on}


def program_row(p: AuditProgram, u: User, warnings: list | None = None) -> dict:
    return {"id": p.id, "year": p.year, "status": p.status, "approved_at": p.approved_at,
            "policy_basis": p.policy_basis, "policy_fingerprint": p.policy_fingerprint,
            "policy_submission_id": p.policy_submission_id, "label": PS.label(p), "warnings": warnings or [],
            "cycles": [{"code": c.code, "seq": c.seq,
                        "audits": [audit_row(a) for a in c.audits if can_see_audit(u, a)]} for c in p.cycles]}


@router.get("/programs")
def programs(s: Session = Depends(get_session), u: User = Depends(current_user)):
    return [program_row(p, u) for p in s.scalars(select(AuditProgram).order_by(AuditProgram.year.desc()))]


class ProgramIn(BaseModel):
    year: int = Field(ge=2000, le=2100)
    cycles: int | None = Field(default=None, ge=1, le=12)


@router.post("/programs")
def create_program(body: ProgramIn, s: Session = Depends(get_session), u: User = Depends(current_user),
                   t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return program_row(PS.create_program(s, u, body.year, p, t, body.cycles), u)


@router.get("/programs/{program_id}/violations")
def program_violations(program_id: int, s: Session = Depends(get_session), u: User = Depends(current_user),
                       t: date = Depends(today), p: PolicyContext = Depends(policy)):
    require(u, Role.MA)
    G.require_effective(s, p, u, t, attempted="view_violations", entity="audit_program", entity_id=program_id)
    return PS.violations(s, get_or_404(s, AuditProgram, program_id), p.policy)


@router.post("/programs/{program_id}/approve")
def approve_program(program_id: int, s: Session = Depends(get_session), u: User = Depends(step_up_user),
                    t: date = Depends(today), p: PolicyContext = Depends(policy)):
    program, warnings = PS.approve_program(s, u, program_id, p, t)
    return program_row(program, u, warnings)


class AssignIn(BaseModel):
    auditor_id: int


@router.post("/audits/{audit_id}/assign")
def assign(audit_id: int, body: AssignIn, s: Session = Depends(get_session), u: User = Depends(current_user),
           t: date = Depends(today), p: PolicyContext = Depends(policy)):
    audit, warnings = PS.assign_auditor(s, u, audit_id, body.auditor_id, p, t)
    return audit_row(audit) | {"warnings": warnings}


class RescheduleIn(BaseModel):
    audit_date: date
    reason: str


@router.post("/audits/{audit_id}/reschedule")
def reschedule(audit_id: int, body: RescheduleIn, s: Session = Depends(get_session),
               u: User = Depends(current_user), t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return audit_row(PS.reschedule_audit(s, u, audit_id, body.audit_date, body.reason, p, t))


@router.get("/audits/{audit_id}")
def audit_detail(audit_id: int, s: Session = Depends(get_session), u: User = Depends(current_user),
                 t: date = Depends(today), p: PolicyContext = Depends(policy)):
    a = get_or_404(s, Audit, audit_id)
    if not can_see_audit(u, a):
        raise NotFound(f"Audit {audit_id} not found")
    fs = [f for f in s.scalars(select(Finding).where(Finding.audit_id == a.id).order_by(Finding.id))
          if can_see_finding(u, f)]
    out = audit_row(a)
    out["findings"] = [RP.finding_row(f, t, RP.display_policy(s, p, t)) for f in fs]
    out["workpapers"] = ([{"id": w.id, "kind": w.kind, "content": w.content, "created_at": w.created_at}
                          for w in s.scalars(select(Workpaper).where(Workpaper.audit_id == a.id))]
                         if can_see_workpapers(u, a) else None)
    out["prior_findings"] = [
        {"id": f.id, "code": f.code, "statement": f.statement, "status": f.status}
        for f in s.scalars(select(Finding).join(Audit).where(Audit.department_id == a.department_id,
                                                             Audit.id != a.id, Finding.status != "DRAFT"))
    ] if a.auditor_id == u.id or Role(u.role) is Role.MA else []
    return out


class WorkpaperIn(BaseModel):
    kind: str
    content: str


@router.post("/audits/{audit_id}/workpapers")
def add_workpaper(audit_id: int, body: WorkpaperIn, s: Session = Depends(get_session),
                  u: User = Depends(current_user)):
    wp = PS.add_workpaper(s, u, audit_id, body.kind, body.content)
    return {"id": wp.id}


class FindingIn(BaseModel):
    category: str
    statement: str
    objective_evidence: str = ""
    iso_clause: str = ""
    qms_ref: str = ""
    repeat_of_id: int | None = None


@router.post("/audits/{audit_id}/findings")
def add_finding(audit_id: int, body: FindingIn, s: Session = Depends(get_session), u: User = Depends(current_user),
                t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return RP.finding_row(FS.add_finding(s, u, audit_id, **body.model_dump()), t, RP.display_policy(s, p, t))


@router.post("/audits/{audit_id}/report")
def issue_report(audit_id: int, s: Session = Depends(get_session), u: User = Depends(current_user),
                 t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return audit_row(FS.issue_report(s, u, audit_id, t, p))


# ---------- findings ----------

@router.get("/findings")
def findings(s: Session = Depends(get_session), u: User = Depends(current_user), t: date = Depends(today),
             p: PolicyContext = Depends(policy)):
    return [RP.finding_row(f, t, RP.display_policy(s, p, t)) for f in RP.visible_findings(s, u)]


def _visible(s: Session, u: User, finding_id: int) -> Finding:
    f = get_or_404(s, Finding, finding_id)
    if not can_see_finding(u, f):
        raise NotFound(f"Finding {finding_id} not found")
    return f


class ConcurrenceIn(BaseModel):
    concurred: bool
    note: str = ""


@router.post("/findings/{finding_id}/concurrence")
def concurrence(finding_id: int, body: ConcurrenceIn, s: Session = Depends(get_session),
                u: User = Depends(current_user), t: date = Depends(today), p: PolicyContext = Depends(policy)):
    _visible(s, u, finding_id)
    return RP.finding_row(FS.record_concurrence(s, u, finding_id, body.concurred, body.note), t, RP.display_policy(s, p, t))


class ActionPlanIn(BaseModel):
    root_cause: str
    corrective_action: str
    owner_name: str
    planned_closure: date
    containment: str = ""
    correction: str = ""
    related_risks: str = ""


@router.post("/findings/{finding_id}/action-plan")
def action_plan(finding_id: int, body: ActionPlanIn, s: Session = Depends(get_session),
                u: User = Depends(current_user), t: date = Depends(today), p: PolicyContext = Depends(policy)):
    f = _visible(s, u, finding_id)
    FS.submit_action_plan(s, u, finding_id, p, t, **body.model_dump())
    s.refresh(f)
    return RP.finding_row(f, t, RP.display_policy(s, p, t))


@router.post("/findings/{finding_id}/accept")
def accept(finding_id: int, s: Session = Depends(get_session), u: User = Depends(step_up_user),
           t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return RP.finding_row(FS.accept_action_plan(s, u, finding_id, p, t), t, RP.display_policy(s, p, t))


class ClosureIn(BaseModel):
    evidence_ref: str
    note: str = ""


@router.post("/findings/{finding_id}/closure")
def closure(finding_id: int, body: ClosureIn, s: Session = Depends(get_session), u: User = Depends(current_user),
            t: date = Depends(today), p: PolicyContext = Depends(policy)):
    _visible(s, u, finding_id)
    return RP.finding_row(FS.submit_closure(s, u, finding_id, body.evidence_ref, body.note), t, RP.display_policy(s, p, t))


class VerifyIn(BaseModel):
    effective: bool
    note: str


@router.post("/findings/{finding_id}/verify")
def verify(finding_id: int, body: VerifyIn, s: Session = Depends(get_session), u: User = Depends(step_up_user),
           t: date = Depends(today), p: PolicyContext = Depends(policy)):
    _visible(s, u, finding_id)
    return RP.finding_row(FS.verify(s, u, finding_id, body.effective, body.note, t), t, RP.display_policy(s, p, t))


class ReasonIn(BaseModel):
    reason: str = ""


@router.post("/findings/{finding_id}/escalate")
def escalate(finding_id: int, body: ReasonIn, s: Session = Depends(get_session), u: User = Depends(current_user),
             t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return RP.finding_row(FS.escalate(s, u, finding_id, body.reason, up=True), t, RP.display_policy(s, p, t))


@router.post("/findings/{finding_id}/deescalate")
def deescalate(finding_id: int, body: ReasonIn, s: Session = Depends(get_session), u: User = Depends(current_user),
               t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return RP.finding_row(FS.escalate(s, u, finding_id, body.reason, up=False), t, RP.display_policy(s, p, t))


@router.post("/findings/{finding_id}/acknowledge")
def acknowledge(finding_id: int, body: Note, s: Session = Depends(get_session), u: User = Depends(step_up_user),
                t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return RP.finding_row(FS.acknowledge_afi(s, u, finding_id, body.note, t), t, RP.display_policy(s, p, t))


class LinkRiskIn(BaseModel):
    risk_id: int


@router.post("/findings/{finding_id}/risks")
def link_risk(finding_id: int, body: LinkRiskIn, s: Session = Depends(get_session), u: User = Depends(current_user),
              t: date = Depends(today), p: PolicyContext = Depends(policy)):
    _visible(s, u, finding_id)
    return RP.finding_row(FS.link_risk(s, u, finding_id, body.risk_id), t, RP.display_policy(s, p, t))


# ---------- risks (R-10: owner assessment, MA co-approval, Top Management sign-off) ----------

def risk_row(r: Risk) -> dict:
    return {c: getattr(r, c) for c in (
        "id", "code", "department_id", "process", "failure_mode", "effect", "cause", "current_controls", "severity",
        "occurrence", "detection", "rpn", "proposed_classification", "effective_classification", "mitigation_plan",
        "mitigation_due", "evidence_ref", "status", "assessment_version", "policy_fingerprint", "owner_id",
        "ma_reviewed_by_id", "signed_off_by_id", "review_due", "project_id")} | {
        "department": r.department.name, "project": r.project.code if r.project else None,
        "scope": RS.scope_of(r), "assessment_label": RS.assessment_label(r), "last_approved": RS.last_approved(r),
        "findings": [{"id": f.id, "code": f.code} for f in r.findings]}


def _can_see_risk(u: User, r: Risk) -> bool:
    if Role(u.role) in (Role.MA, Role.MD, Role.VIEWER):
        return True
    return r.department_id == u.department_id or (r.project is not None and r.project.manager_user_id == u.id)


@router.get("/projects")
def projects(s: Session = Depends(get_session), u: User = Depends(current_user)):
    return [{"id": p.id, "code": p.code, "name": p.name, "department_id": p.department_id,
             "manager_user_id": p.manager_user_id, "assignment_basis": p.assignment_basis}
            for p in s.scalars(select(Project).order_by(Project.id))]


@router.get("/risks")
def risks(s: Session = Depends(get_session), u: User = Depends(current_user)):
    return [risk_row(r) for r in s.scalars(select(Risk).order_by(Risk.rpn.desc(), Risk.id)) if _can_see_risk(u, r)]


@router.get("/risks/{risk_id}/records")
def risk_records(risk_id: int, s: Session = Depends(get_session), u: User = Depends(current_user)):
    r = get_or_404(s, Risk, risk_id)
    if not _can_see_risk(u, r):
        raise NotFound(f"Risk {risk_id} not found")
    return [{c: getattr(x, c) for c in ("assessment_version", "action", "actor_id", "actor_role", "scope",
                                         "severity", "occurrence", "detection", "rpn", "classification",
                                         "policy_fingerprint", "evidence_ref", "decision", "note", "stale", "at")}
            for x in RS.records(s, risk_id)]


class RiskIn(BaseModel):
    department_id: int | None = None
    project_id: int | None = None
    process: str
    failure_mode: str
    severity: int
    occurrence: int
    detection: int
    effect: str = ""
    cause: str = ""
    current_controls: str = ""
    mitigation_plan: str = ""
    mitigation_due: date | None = None
    evidence_ref: str = ""


@router.post("/risks")
def create_risk(body: RiskIn, s: Session = Depends(get_session), u: User = Depends(current_user),
                t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return risk_row(RS.create_risk(s, u, p, t, **body.model_dump()))


class ReassessIn(BaseModel):
    severity: int
    occurrence: int
    detection: int
    mitigation_plan: str | None = None
    mitigation_due: date | None = None
    evidence_ref: str | None = None
    note: str = ""


@router.post("/risks/{risk_id}/reassess")
def reassess(risk_id: int, body: ReassessIn, s: Session = Depends(get_session), u: User = Depends(current_user),
             t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return risk_row(RS.reassess(s, u, risk_id, p, t, **body.model_dump()))


@router.post("/risks/{risk_id}/submit")
def submit_risk(risk_id: int, s: Session = Depends(get_session), u: User = Depends(current_user),
                t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return risk_row(RS.submit(s, u, risk_id, p, t))


class GateIn(BaseModel):
    approve: bool
    note: str = ""


@router.post("/risks/{risk_id}/ma-review")
def ma_review_risk(risk_id: int, body: GateIn, s: Session = Depends(get_session), u: User = Depends(step_up_user),
                   t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return risk_row(RS.ma_review(s, u, risk_id, p, t, approve=body.approve, note=body.note))


@router.post("/risks/{risk_id}/signoff")
def signoff_risk(risk_id: int, body: GateIn, s: Session = Depends(get_session), u: User = Depends(step_up_user),
                 t: date = Depends(today), p: PolicyContext = Depends(policy)):
    return risk_row(RS.tm_signoff(s, u, risk_id, p, t, approve=body.approve, note=body.note))


@router.post("/risks/{risk_id}/close")
def close_risk(risk_id: int, body: ReasonIn, s: Session = Depends(get_session), u: User = Depends(step_up_user)):
    return risk_row(RS.close(s, u, risk_id, body.reason))


# ---------- outbound drafts (HITL) ----------

def notification_row(n: Notification) -> dict:
    return {c: getattr(n, c) for c in ("id", "kind", "to", "subject", "body", "status", "entity", "entity_id",
                                       "created_at", "decided_at")}


@router.get("/notifications")
def notifications(s: Session = Depends(get_session), u: User = Depends(current_user)):
    require(u, Role.MA)
    return [notification_row(n) for n in s.scalars(select(Notification).order_by(Notification.id.desc()))]


@router.post("/notifications/prepare-circulars")
def prepare_circulars(s: Session = Depends(get_session), u: User = Depends(current_user), t: date = Depends(today),
                      p: PolicyContext = Depends(policy)):
    return {"drafted": len(PS.prepare_due_circulars(s, u, t, p))}


@router.post("/notifications/reminders")
def reminders(s: Session = Depends(get_session), u: User = Depends(current_user), t: date = Depends(today),
              p: PolicyContext = Depends(policy)):
    return {"drafted": FS.draft_reminders(s, u, t, p)}


class DecideIn(BaseModel):
    approve: bool


@router.post("/notifications/{notification_id}/decide")
def decide(notification_id: int, body: DecideIn, s: Session = Depends(get_session), u: User = Depends(step_up_user)):
    return notification_row(PS.decide_notification(s, u, notification_id, body.approve))


# ---------- reports ----------

@router.get("/dashboard")
def dashboard(s: Session = Depends(get_session), u: User = Depends(current_user), t: date = Depends(today),
              p: PolicyContext = Depends(policy)):
    return RP.dashboard(s, u, t, p)


@router.get("/reports/monthly")
def monthly(year: int, month: int, s: Session = Depends(get_session), u: User = Depends(current_user),
            t: date = Depends(today), p: PolicyContext = Depends(policy)):
    if not 1 <= month <= 12:
        raise Forbidden("month must be 1-12")
    return RP.monthly_report(s, u, year, month, t, p)


@router.get("/events")
def events(s: Session = Depends(get_session), u: User = Depends(current_user)):
    return RP.events(s, u)
