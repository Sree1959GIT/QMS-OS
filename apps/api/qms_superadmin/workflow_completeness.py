"""inspect-workflow-completeness (journey 2; R-56 to R-62): inspect workflow template versions for completeness,
review changes proposed from findings, and check every baselined version's digest against its approval.

Read-only: the read-only session (R-46) and the workflow engine's own pure functions (the validator and the digest).
Findings only. Deterministic: sorted by id, no timestamps.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from qms_os.models import WorkflowApproval, WorkflowCase, WorkflowProposal, WorkflowTemplateVersion
from qms_os.workflow.service import contributors, digest_of, findings_of
from qms_os.workflow.validator import VALIDATOR_VERSION, errors


def review(s: Session) -> list[str]:
    versions = list(s.scalars(select(WorkflowTemplateVersion).order_by(WorkflowTemplateVersion.id)))
    by_status: dict[str, int] = {}
    for v in versions:
        by_status[v.status] = by_status.get(v.status, 0) + 1
    out = [f"workflow versions: {len(versions)} ({', '.join(f'{k} {n}' for k, n in sorted(by_status.items()))}); "
           f"validator version {VALIDATOR_VERSION}"]
    findings: list[str] = []
    for v in versions:
        label = f"version {v.id} (template {v.template_id}, no. {v.version_no}, {v.status})"
        if v.status in ("draft", "proposed"):
            failing = errors(findings_of(s, v))
            codes = sorted({f["code"] for f in failing})
            out.append(f"- {label}: " + ("complete" if not failing else f"{len(failing)} error(s): {', '.join(codes)}"))
            if v.status == "proposed" and failing:
                findings.append(f"{label} is proposed but incomplete ({', '.join(codes)}) -> it cannot be baselined; "
                                f"propose POST /api/v1/workflow/versions/{v.id}/withdraw and fix the draft")
            if v.status == "proposed" and v.digest != digest_of(s, v):
                findings.append(f"{label}: its stored digest does not match its content -> investigate")
        else:
            approvals = list(s.scalars(select(WorkflowApproval).where(WorkflowApproval.version_id == v.id,
                                                                      WorkflowApproval.decision == "approved")))
            if len(approvals) != 1:
                findings.append(f"{label} has {len(approvals)} approvals; exactly one is required (R-59)")
                continue
            a = approvals[0]
            recomputed = digest_of(s, v)
            if not (recomputed == v.digest == a.digest):
                findings.append(f"{label}: digest mismatch (content {recomputed[:12]}, stored "
                                f"{(v.digest or '')[:12]}, approved {a.digest[:12]}) -> investigate; the approval "
                                "does not cover this content")
            if a.decided_by_id in contributors(s, v):
                findings.append(f"{label} was approved by a contributor (person {a.decided_by_id}); self-approval "
                                "must never happen (R-57)")
            out.append(f"- {label}: digest matches its approval by person {a.decided_by_id}"
                       if recomputed == v.digest == a.digest else f"- {label}: digest does NOT match")
        if v.origin == "finding":
            state = ("baselined after review" if v.status in ("baselined", "superseded")
                     else "awaiting review; not published")
            out.append(f"  change proposed from finding {v.origin_ref}: {state} (journey 2: never auto-published)")
    for c in s.scalars(select(WorkflowCase).where(WorkflowCase.status == "running").order_by(WorkflowCase.id)):
        pinned = s.get(WorkflowTemplateVersion, c.version_id)
        if pinned is None or pinned.status not in ("baselined", "superseded"):
            findings.append(f"case {c.id} is pinned to version {c.version_id}, which is not baselined -> investigate")
    open_proposals = s.scalars(select(WorkflowProposal.id).where(WorkflowProposal.status == "open")).all()
    out.append(f"open proposals: {len(open_proposals)} (drafts only after review; never baselined by the form)")
    out.append(f"findings: {len(findings)}")
    out += [f"- {f}" for f in findings]
    return out
