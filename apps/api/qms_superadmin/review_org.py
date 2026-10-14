"""review-org (journey 1; R-30): read the departments and people and report what an org admin should look at.

Findings only; every proposal names the org admin route that would make the change (in the application, with a
fresh step-up). Deterministic: sorted by id, no timestamps.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from qms_os.auth.permissions import org_admin_ids
from qms_os.auth.service import ACCOUNT_ADMIN
from qms_os.models import Department, User


def review(s: Session) -> list[str]:
    depts = list(s.scalars(select(Department).order_by(Department.id)))
    people = list(s.scalars(select(User).order_by(User.id)))
    by_id = {u.id: u for u in people}
    org_admins = org_admin_ids(s)
    out = [f"departments: {len(depts)} ({sum(d.active for d in depts)} active); "
           f"people: {len(people)} ({sum(u.active for u in people)} active)",
           f"org admins: {len(org_admins)}; account admins: {sum(u.platform_role == ACCOUNT_ADMIN for u in people)}",
           "agents: none (agent enablement arrives in MVP-1 slice 4; no person holds an agent)"]
    findings = []
    for d in depts:
        if not d.active:
            continue
        head = by_id.get(d.head_user_id) if d.head_user_id else None
        if head is None:
            findings.append(f"department {d.id} ({d.code}) has no head -> propose PATCH /api/v1/org/departments/{d.id} "
                            "with head_user_id")
        elif not head.active:
            findings.append(f"department {d.id} ({d.code}) is headed by inactive person {head.id} -> propose a new "
                            f"head (PATCH /api/v1/org/departments/{d.id})")
        elif head.department_id != d.id:
            findings.append(f"department {d.id} ({d.code}) is headed by person {head.id}, who belongs to another "
                            "department -> confirm or correct")
    for u in people:
        if u.active and u.department_id is None and u.role not in ("MD", "VIEWER"):
            findings.append(f"person {u.id} (role {u.role}) has no department -> propose PATCH "
                            f"/api/v1/org/people/{u.id} with department_id")
        if u.active and u.department_id is not None:
            home = next((x for x in depts if x.id == u.department_id), None)
            if home is not None and not home.active:
                findings.append(f"person {u.id} belongs to inactive department {home.id} -> move or deactivate")
    out.append(f"findings: {len(findings)}")
    out += [f"- {f}" for f in findings]
    out.append("next: run access-segregation to review what each person can read")
    return out
