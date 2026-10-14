"""access-segregation, first version (journey 1; R-31, R-40): what each person can read, from the same functions that
enforce the reads (``qms_os.services.access``), and the separations that must hold.

Findings only. Deterministic: sorted by id, no timestamps. Agents join the preview in MVP-1 slice 4.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from qms_os.auth.permissions import org_admin_ids
from qms_os.auth.service import ACCOUNT_ADMIN
from qms_os.models import ProjectMember, User
from qms_os.services import access as ACC


def review(s: Session) -> list[str]:
    people = list(s.scalars(select(User).order_by(User.id)))
    org_admins = org_admin_ids(s)
    out = ["effective access (readable ids per kind; from services/access.py, the enforcement path):"]
    findings = []
    for u in people:
        p = ACC.preview(s, u)
        counts = ", ".join(f"{k} {len(p['readable'][k])}/{len(p['readable'][k]) + len(p['denied'][k])}"
                           for k in ACC.KINDS)
        out.append(f"- person {u.id} role {u.role}{'' if u.active else ' (inactive)'}: {counts}")
        if u.active and not p["grants"]:
            findings.append(f"person {u.id} (role {u.role}) has no role grant and reads nothing -> propose a role "
                            "grant (POST /api/v1/org/role-grants) if that is not intended")
        if p["mailbox_scopes"] or p["delegations"]:
            findings.append(f"person {u.id} has a mailbox scope or delegation row; these are declared but must stay "
                            "empty in MVP-1 (R-31)")
        if u.platform_role == ACCOUNT_ADMIN and u.id in org_admins:
            findings.append(f"person {u.id} holds both account admin and org admin; this must never happen (R-40)")
    for m in s.scalars(select(ProjectMember).where(ProjectMember.removed_at.is_(None)).order_by(ProjectMember.id)):
        member = s.get(User, m.user_id)
        if member is not None and not member.active:
            findings.append(f"inactive person {m.user_id} is still a member of project {m.project_id} -> propose "
                            f"POST /api/v1/org/projects/{m.project_id}/members/{m.user_id}/remove")
    out.append(f"findings: {len(findings)}")
    out += [f"- {f}" for f in findings]
    out.append("agents: not covered yet (MVP-1 slice 4 adds them to this review)")
    return out
