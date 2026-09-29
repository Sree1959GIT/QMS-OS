"""FMEA risk register with owner assessment, MA co-approval and Top Management sign-off.

Development references: VREF-07, VREF-20 (candidate guidance for the scoring method).
Organisational requirement R-10 (supplied by the Admin, 2026-09-29 — not derived from the reference
vault or ISO text):

* the owner performs the assessment (ratings, scoring, proposed classification) within their
  authorised scope: the functional head for a department risk, the assigned project manager for a
  project risk; the software only calculates deterministically. Organisational project-manager
  assignment is not implemented yet (D-16), so project-risk submission is held in operational mode;
* the quality representative (MA) reviews and co-approves; Top Management gives final sign-off;
  each gate is a distinct person from the owner and from the other gate;
* every action records actor, role, scope, assessment version, ratings, scoring-policy
  fingerprint, evidence, decision and timestamp (RiskAssessmentRecord);
* any change after review or sign-off makes prior approvals stale and restarts the gates;
* drafts may be captured without an approved scoring policy, but no classification is proposed
  or issued until the scoring policy is in force and both human gates are complete.

State machine: DRAFT -> SUBMITTED -> MA_REVIEWED -> ACTIVE; MA or Top Management may return
SUBMITTED/MA_REVIEWED to DRAFT with a reason; reassessment returns any open state to DRAFT with a
new assessment version while the last signed-off assessment stays visible as "last approved — under
reassessment". Closure authority is unresolved (D-15): closing is held.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..models import Department, Project, Risk, RiskAssessmentRecord, User
from ..policy import PolicyContext
from ..rules import risk as R
from ..rules.findings import Role
from . import policy_gate as G
from .common import Forbidden, Held, RuleViolation, get_or_404, log, require

OPEN = ("DRAFT", "SUBMITTED", "MA_REVIEWED", "ACTIVE")
UNDER_REASSESSMENT = "last approved — under reassessment"


def scope_of(risk: Risk) -> str:
    return f"project:{risk.project.code}" if risk.project_id else f"department:{risk.department.code}"


def is_owner(actor: User, risk: Risk) -> bool:
    """Project risk: the project's assigned manager. Department risk: the functional head."""
    if risk.project_id is not None:
        return risk.project.manager_user_id == actor.id
    return risk.department.head_user_id == actor.id


def _require_owner(actor: User, risk: Risk, doing: str) -> None:
    if not is_owner(actor, risk):
        who = "the assigned project manager" if risk.project_id else "the functional head of the department"
        raise Forbidden(f"only {who} can {doing}")


def _project_ownership_in_force(ctx: PolicyContext, actor: User, risk: Risk, attempted: str) -> None:
    """Organisational project/PM assignment is not implemented (D-16): project risks are held outside demo/test."""
    if risk.project_id is not None and not ctx.synthetic:
        raise Held("project_ownership_not_implemented",
                   "organisational project-manager assignment is not implemented yet",
                   "implement and approve project ownership assignment before submitting project risks",
                   actor=actor, entity="risk", entity_id=risk.id, attempted=attempted)


def _record(s: Session, risk: Risk, actor: User, action: str, decision: str, note: str = "") -> None:
    s.add(RiskAssessmentRecord(
        risk_id=risk.id, assessment_version=risk.assessment_version, action=action, actor_id=actor.id,
        actor_role=actor.role, scope=scope_of(risk), severity=risk.severity, occurrence=risk.occurrence,
        detection=risk.detection, rpn=risk.rpn, classification=risk.proposed_classification,
        policy_fingerprint=risk.policy_fingerprint, evidence_ref=risk.evidence_ref, decision=decision, note=note))
    log(s, actor, f"risk.{action}", "risk", risk.id, version=risk.assessment_version, decision=decision)


def _basic_ratings(*vals: int) -> None:
    for v in vals:
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            raise RuleViolation("ratings must be positive integers")


def _scoring_in_force(s: Session, ctx: PolicyContext, today: date) -> bool:
    if ctx.synthetic:
        return True
    return G.state(s, ctx, today)["state"] == "approved"


def _classify(s: Session, ctx: PolicyContext, today: date, risk: Risk) -> None:
    """Proposed classification only when the scoring policy is in force; otherwise left empty."""
    risk.rpn = risk.severity * risk.occurrence * risk.detection
    if _scoring_in_force(s, ctx, today):
        try:
            sc = R.score(risk.severity, risk.occurrence, risk.detection, ctx.policy)
        except ValueError as e:
            raise RuleViolation(str(e)) from e
        risk.proposed_classification = sc.classification
    else:
        risk.proposed_classification = None


def create_risk(s: Session, actor: User, ctx: PolicyContext, today: date, *, process: str, failure_mode: str,
                severity: int, occurrence: int, detection: int, department_id: int | None = None,
                project_id: int | None = None, effect: str = "", cause: str = "", current_controls: str = "",
                mitigation_plan: str = "", mitigation_due: date | None = None, evidence_ref: str = "") -> Risk:
    project = get_or_404(s, Project, project_id) if project_id is not None else None
    if project is not None:
        if department_id is not None and department_id != project.department_id:
            raise RuleViolation("department_id does not match the project's department")
        dept = project.department
        if project.manager_user_id != actor.id:
            raise Forbidden("project risks are owned and assessed by the assigned project manager")
    else:
        if department_id is None:
            raise RuleViolation("department_id or project_id is required")
        dept = get_or_404(s, Department, department_id)
        if dept.head_user_id != actor.id:
            raise Forbidden("department risks are owned and assessed by the functional head of the department")
    if not (process.strip() and failure_mode.strip()):
        raise RuleViolation("process and failure mode are required")
    _basic_ratings(severity, occurrence, detection)
    n = s.scalar(select(func.count()).select_from(Risk).where(Risk.department_id == dept.id)) + 1
    risk = Risk(code=f"R-{dept.code.upper()}-{n:03d}", department=dept, department_id=dept.id, project=project,
                project_id=project.id if project else None, process=process,
                failure_mode=failure_mode, effect=effect, cause=cause, current_controls=current_controls,
                severity=severity, occurrence=occurrence, detection=detection, rpn=0,
                mitigation_plan=mitigation_plan, mitigation_due=mitigation_due, evidence_ref=evidence_ref,
                owner_id=actor.id, status="DRAFT", assessment_version=1)
    _classify(s, ctx, today, risk)
    s.add(risk)
    s.flush()
    _record(s, risk, actor, "captured", "draft")
    return risk


def reassess(s: Session, actor: User, risk_id: int, ctx: PolicyContext, today: date, *, severity: int,
             occurrence: int, detection: int, mitigation_plan: str | None = None, mitigation_due: date | None = None,
             evidence_ref: str | None = None, note: str = "") -> Risk:
    """Owner changes the assessment. After submission, review or sign-off this starts a new version and
    marks every prior gate decision stale."""
    risk = get_or_404(s, Risk, risk_id)
    _require_owner(actor, risk, "change the assessment")
    if risk.status not in OPEN:
        raise RuleViolation(f"a {risk.status.lower()} risk cannot be reassessed")
    _basic_ratings(severity, occurrence, detection)
    if risk.status != "DRAFT":
        s.execute(update(RiskAssessmentRecord).where(RiskAssessmentRecord.risk_id == risk.id,
                                                     RiskAssessmentRecord.assessment_version == risk.assessment_version)
                  .values(stale=True))
        risk.assessment_version += 1
        risk.status, risk.ma_reviewed_by_id, risk.signed_off_by_id = "DRAFT", None, None
        risk.effective_classification, risk.policy_fingerprint, risk.review_due = None, None, None
    risk.severity, risk.occurrence, risk.detection = severity, occurrence, detection
    if mitigation_plan is not None:
        risk.mitigation_plan = mitigation_plan
    if mitigation_due is not None:
        risk.mitigation_due = mitigation_due
    if evidence_ref is not None:
        risk.evidence_ref = evidence_ref
    _classify(s, ctx, today, risk)
    _record(s, risk, actor, "reassessed", "draft", note)
    return risk


def submit(s: Session, actor: User, risk_id: int, ctx: PolicyContext, today: date) -> Risk:
    risk = get_or_404(s, Risk, risk_id)
    _require_owner(actor, risk, "submit the assessment")
    if risk.status != "DRAFT":
        raise RuleViolation("only a draft assessment can be submitted")
    _project_ownership_in_force(ctx, actor, risk, "risk_submit")
    basis = G.require_effective(s, ctx, actor, today, attempted="risk_submit", entity="risk", entity_id=risk.id)
    _classify(s, ctx, today, risk)
    if risk.proposed_classification == "S" and not (risk.mitigation_plan.strip() and risk.mitigation_due):
        raise RuleViolation("a significant risk needs a mitigation plan and target date before submission")
    risk.status, risk.policy_fingerprint = "SUBMITTED", basis.fingerprint
    _record(s, risk, actor, "submitted", "submitted")
    return risk


def _gate(s: Session, ctx: PolicyContext, actor: User, today: date, risk: Risk, attempted: str) -> None:
    _project_ownership_in_force(ctx, actor, risk, attempted)
    G.require_effective(s, ctx, actor, today, attempted=attempted, entity="risk", entity_id=risk.id)
    if ctx.policy.fingerprint != risk.policy_fingerprint:
        raise Held("policy_changed_since_submission", "the scoring policy changed after this assessment was submitted",
                   "the owner must resubmit under the policy now in force", actor=actor, entity="risk",
                   entity_id=risk.id, attempted=attempted)


def ma_review(s: Session, actor: User, risk_id: int, ctx: PolicyContext, today: date, *, approve: bool,
              note: str) -> Risk:
    require(actor, Role.MA)
    risk = get_or_404(s, Risk, risk_id)
    if risk.status != "SUBMITTED":
        raise RuleViolation("only a submitted assessment can be reviewed by the quality representative (MA)")
    if actor.id == risk.owner_id:
        raise RuleViolation("the reviewer must be a different person from the risk owner")
    if not approve and not note.strip():
        raise RuleViolation("a reason is required to return an assessment")
    _gate(s, ctx, actor, today, risk, "risk_ma_review")
    if approve:
        risk.status, risk.ma_reviewed_by_id = "MA_REVIEWED", actor.id
        _record(s, risk, actor, "ma_reviewed", "approved", note)
    else:
        risk.status = "DRAFT"
        _record(s, risk, actor, "ma_returned", "returned", note)
    return risk


def tm_signoff(s: Session, actor: User, risk_id: int, ctx: PolicyContext, today: date, *, approve: bool,
               note: str) -> Risk:
    require(actor, Role.MD)
    risk = get_or_404(s, Risk, risk_id)
    if risk.status != "MA_REVIEWED":
        raise RuleViolation("Top Management sign-off requires a completed MA review")
    if actor.id in (risk.owner_id, risk.ma_reviewed_by_id):
        raise RuleViolation("final sign-off must come from a person other than the owner and the MA reviewer")
    if not approve and not note.strip():
        raise RuleViolation("a reason is required to return an assessment")
    _gate(s, ctx, actor, today, risk, "risk_tm_signoff")
    if approve:
        risk.status, risk.signed_off_by_id = "ACTIVE", actor.id
        risk.effective_classification = risk.proposed_classification
        risk.review_due = R.next_review(today, ctx.policy)
        risk.last_approved_version, risk.last_approved_at = risk.assessment_version, datetime.now(timezone.utc)
        risk.last_approved_by_id, risk.last_approved_policy_fingerprint = actor.id, risk.policy_fingerprint
        risk.last_approved_classification = risk.proposed_classification
        risk.last_approved_ratings = {"severity": risk.severity, "occurrence": risk.occurrence,
                                      "detection": risk.detection, "rpn": risk.rpn}
        _record(s, risk, actor, "signed_off", "approved", note)
    else:
        risk.status, risk.ma_reviewed_by_id = "DRAFT", None
        _record(s, risk, actor, "tm_returned", "returned", note)
    return risk


def close(s: Session, actor: User, risk_id: int, reason: str) -> Risk:
    """Closure authority is an unresolved organisational decision (docs/DECISIONS.md D-15): every
    closure request is held and recorded; no role may close a risk until the authority is decided."""
    risk = get_or_404(s, Risk, risk_id)
    raise Held("closure_authority_unresolved", "who may close a risk has not been decided by the organisation",
               "an organisational decision on risk-closure authority (D-15)", actor=actor, entity="risk",
               entity_id=risk.id, attempted="risk_close")


def last_approved(risk: Risk) -> dict | None:
    """The previous signed-off assessment, shown distinctly while a newer version is being reassessed."""
    if risk.last_approved_version is None or risk.status == "ACTIVE":
        return None
    return {"label": UNDER_REASSESSMENT, "assessment_version": risk.last_approved_version,
            "signed_off_at": risk.last_approved_at, "signed_off_by_id": risk.last_approved_by_id,
            "policy_fingerprint": risk.last_approved_policy_fingerprint,
            "classification": risk.last_approved_classification, "ratings": risk.last_approved_ratings}


def assessment_label(risk: Risk) -> str:
    if risk.status == "ACTIVE":
        return f"v{risk.assessment_version} approved (signed off)"
    return f"v{risk.assessment_version} {risk.status.lower().replace('_', ' ')} — not approved"


def records(s: Session, risk_id: int) -> list[RiskAssessmentRecord]:
    return list(s.scalars(select(RiskAssessmentRecord).where(RiskAssessmentRecord.risk_id == risk_id)
                          .order_by(RiskAssessmentRecord.id)))
