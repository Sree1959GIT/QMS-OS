"""Policy state, the policy gate for policy-dependent transitions, and the R-9 approval workflow.

Organisational requirement R-9 (supplied by the Admin, 2026-09-29 — not derived from the reference
vault or ISO text): an organisational QMS policy is finally approved only by an authorised Top
Management human (role MD). The quality representative (MA) may prepare, submit and review it but never
gives final approval. Approval binds the exact fingerprint, version, effective date and named
approver; any change to the file or version invalidates it; nobody approves their own submission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import PolicySubmission, User
from ..policy import PolicyContext
from ..rules.findings import Role
from .common import Forbidden, Held, RuleViolation, get_or_404, log

SUBMITTERS = (Role.MA, Role.MD)
FINAL_APPROVER = Role.MD          # Top Management


@dataclass(frozen=True)
class Basis:
    """What a policy-dependent action was performed under."""
    kind: str                     # "organisation" | "synthetic-demo"
    fingerprint: str
    submission_id: int | None


def _approved_for(s: Session, fingerprint: str) -> PolicySubmission | None:
    return s.scalar(select(PolicySubmission).where(PolicySubmission.fingerprint == fingerprint,
                                                   PolicySubmission.status == "APPROVED")
                    .order_by(PolicySubmission.id.desc()))


def _distinct_approver_available(s: Session, submitter_id: int) -> bool:
    return s.scalar(select(User.id).where(User.role == FINAL_APPROVER, User.id != submitter_id).limit(1)) is not None


def state(s: Session, ctx: PolicyContext, today: date) -> dict:
    out = {"mode": ctx.mode.value, "source": ctx.source}
    if ctx.synthetic:
        return out | {"state": "synthetic-demo", "policy": ctx.policy.describe(),
                      "note": "Synthetic example for demo/test only — not organisational QMS policy; "
                              "it cannot be submitted or approved."}
    if ctx.policy is None:
        return out | {"state": "policy_missing",
                      "note": "No organisation policy file is loaded; policy-dependent actions are held."}
    pol = ctx.policy
    out["policy"] = pol.describe()
    approved = _approved_for(s, pol.fingerprint)
    if approved is not None:
        base = out | {"approval": {"submission_id": approved.id, "approved_by": approved.decided_by_name,
                                   "role": approved.decided_role, "approved_at": approved.decided_at,
                                   "effective_date": approved.effective_date}}
        if today < approved.effective_date:
            return base | {"state": "policy_not_effective"}
        return base | {"state": "approved"}
    pending = s.scalar(select(PolicySubmission).where(PolicySubmission.fingerprint == pol.fingerprint,
                                                      PolicySubmission.status == "SUBMITTED"))
    changed = s.scalar(select(PolicySubmission.id).where(PolicySubmission.policy_id == pol.policy_id,
                                                         PolicySubmission.status == "APPROVED").limit(1))
    detail = {"submission": None, "changed_since_approval": changed is not None}
    if pending is not None:
        detail["submission"] = {"id": pending.id, "submitted_by_id": pending.submitted_by_id,
                                "pending_organisational_decision":
                                    not _distinct_approver_available(s, pending.submitted_by_id)}
    return out | {"state": "policy_unapproved"} | detail


def require_effective(s: Session, ctx: PolicyContext, actor: User | None, today: date, *, attempted: str,
                      entity: str, entity_id: int | None) -> Basis:
    """Gate for policy-dependent transitions. Synthetic policy passes only in demo/test mode."""
    if ctx.synthetic:
        return Basis("synthetic-demo", ctx.policy.fingerprint, None)
    st = state(s, ctx, today)
    if st["state"] == "approved":
        return Basis("organisation", ctx.policy.fingerprint, st["approval"]["submission_id"])
    decision = {
        "policy_missing": "load the organisation policy file, then submit it for Top Management approval",
        "policy_unapproved": "submit the loaded policy and obtain final Top Management approval",
        "policy_not_effective": "wait until the approved policy's effective date",
    }[st["state"]]
    raise Held(st["state"], f"organisation QMS policy is not in force ({st['state']})", decision,
               actor=actor, entity=entity, entity_id=entity_id, attempted=attempted)


def _refuse_synthetic(ctx: PolicyContext) -> None:
    if ctx.synthetic:
        raise RuleViolation("a synthetic demo/test policy cannot be submitted or approved as organisational "
                            "QMS policy")


def submit(s: Session, ctx: PolicyContext, actor: User, note: str) -> PolicySubmission:
    _refuse_synthetic(ctx)
    if Role(actor.role) not in SUBMITTERS:
        raise Forbidden("only the quality representative (MA) or Top Management may submit a policy")
    if ctx.policy is None:
        raise RuleViolation("no organisation policy is loaded")
    pol = ctx.policy
    existing = s.scalar(select(PolicySubmission).where(PolicySubmission.fingerprint == pol.fingerprint,
                                                       PolicySubmission.status.in_(("SUBMITTED", "APPROVED"))))
    if existing is not None:
        raise RuleViolation(f"this exact policy is already {existing.status.lower()} (submission {existing.id})")
    for old in s.scalars(select(PolicySubmission).where(PolicySubmission.policy_id == pol.policy_id,
                                                        PolicySubmission.status == "SUBMITTED")):
        old.status = "STALE"
    sub = PolicySubmission(policy_id=pol.policy_id, policy_version=pol.policy_version,
                           effective_date=pol.effective_date, fingerprint=pol.fingerprint,
                           submitted_by_id=actor.id, submit_note=note)
    s.add(sub)
    s.flush()
    log(s, actor, "policy.submitted", "policy_submission", sub.id, fingerprint=pol.fingerprint,
        version=pol.policy_version, effective_date=pol.effective_date)
    return sub


def _decidable(s: Session, ctx: PolicyContext, actor: User, submission_id: int, attempted: str) -> PolicySubmission:
    _refuse_synthetic(ctx)
    if Role(actor.role) is not FINAL_APPROVER:
        raise Forbidden("final policy decisions are reserved for Top Management")
    sub = get_or_404(s, PolicySubmission, submission_id)
    if sub.status != "SUBMITTED":
        raise RuleViolation(f"submission {sub.id} is {sub.status.lower()}")
    if sub.submitted_by_id == actor.id:
        pending = "" if _distinct_approver_available(s, actor.id) else \
            "; no other Top Management approver exists — held pending an organisational decision"
        raise RuleViolation("no person may decide their own policy submission" + pending)
    if ctx.policy is None or ctx.policy.fingerprint != sub.fingerprint:
        raise Held("policy_changed_since_submission", "the loaded policy differs from the submitted one",
                   "submit the currently loaded policy again", actor=actor, entity="policy_submission",
                   entity_id=sub.id, attempted=attempted)
    return sub


def approve(s: Session, ctx: PolicyContext, actor: User, submission_id: int, *, fingerprint: str,
            confirm_version: str, note: str) -> PolicySubmission:
    sub = _decidable(s, ctx, actor, submission_id, "policy_approve")
    if fingerprint != sub.fingerprint:
        raise Held("stale_review", "the fingerprint you reviewed is not the submitted fingerprint",
                   "review the current submission again", actor=actor, entity="policy_submission",
                   entity_id=sub.id, attempted="policy_approve")
    if confirm_version.strip() != sub.policy_version:
        raise RuleViolation("type the exact policy version to confirm approval")
    sub.status, sub.decided_by_id, sub.decided_by_name = "APPROVED", actor.id, actor.name
    sub.decided_role, sub.decided_at, sub.decision_note = actor.role, datetime.now(UTC), note
    log(s, actor, "policy.approved", "policy_submission", sub.id, fingerprint=sub.fingerprint,
        version=sub.policy_version, effective_date=sub.effective_date, approver=actor.name)
    return sub


def reject(s: Session, ctx: PolicyContext, actor: User, submission_id: int, reason: str) -> PolicySubmission:
    if not reason.strip():
        raise RuleViolation("a reason is required to reject")
    sub = _decidable(s, ctx, actor, submission_id, "policy_reject")
    sub.status, sub.decided_by_id, sub.decided_by_name = "REJECTED", actor.id, actor.name
    sub.decided_role, sub.decided_at, sub.decision_note = actor.role, datetime.now(UTC), reason
    log(s, actor, "policy.rejected", "policy_submission", sub.id, reason=reason)
    return sub
