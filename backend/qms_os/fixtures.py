"""Synthetic organisation used by tests and the local demo seed.

Entirely fictional and deliberately artificial: role-coded people, "(fixture)" department names, a reserved
``.example`` mail domain and invented holiday dates. No names, documents, dates or data are taken from the
development reference or any real organisation, and none of it should look like one.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from .models import Department, Holiday, Project, User

ORG_NAME = "Fixture Organisation (fictional test data)"
MAIL_DOMAIN = "fixture-org.example"     # RFC 2606 reserved domain — never deliverable

DEPARTMENTS = [
    ("qa", "Quality (fixture)"),
    ("pur", "Purchasing (fixture)"),
    ("ita", "IT (fixture)"),
    ("hrd", "People (fixture)"),
    ("mkt", "Sales (fixture)"),
    ("eng", "Engineering (fixture)"),
]

# (name, email-local, role, dept code, trained auditor, is head) — role-coded, not personal names
USERS = [
    ("Fixture MA", "ma", "MA", "qa", False, False),
    ("Fixture Top Management", "md", "MD", None, False, False),
    ("Fixture Quality Head", "qa_head", "AUDITEE", "qa", True, True),
    ("Fixture Purchasing Head", "pur_head", "AUDITEE", "pur", True, True),
    ("Fixture IT Head", "it_head", "AUDITEE", "ita", True, True),
    ("Fixture People Head", "hr_head", "AUDITEE", "hrd", True, True),
    ("Fixture Sales Head", "mkt_head", "AUDITEE", "mkt", True, True),
    ("Fixture Engineering Head", "eng_head", "AUDITEE", "eng", True, True),
    ("Fixture Auditor (Engineering)", "eng_auditor", "AUDITOR", "eng", True, False),
    ("Fixture Auditor (Quality)", "qa_auditor", "AUDITOR", "qa", True, False),
    ("Fixture Auditor (untrained)", "untrained_auditor", "AUDITOR", "mkt", False, False),
    ("Fixture Viewer", "viewer", "VIEWER", None, False, False),
    ("Fixture Project Manager", "eng_pm", "AUDITEE", "eng", False, False),
]

# (code, name, department code, project manager email-local) — fictional
PROJECTS = [
    ("P-SYN-01", "Synthetic test-rig upgrade", "eng", "eng_pm"),
    ("P-SYN-02", "Synthetic supplier onboarding", "pur", "qa_auditor"),
]


def holidays(year: int) -> list[tuple[date, str]]:
    """Invented fixed-date holidays (not any country's or organisation's calendar)."""
    return [(date(year, 3, 10), "Fixture holiday A"), (date(year, 6, 9), "Fixture holiday B"),
            (date(year, 9, 22), "Fixture holiday C"), (date(year, 11, 26), "Fixture holiday D")]


def load(s: Session, years: tuple[int, ...] = (2026, 2027)) -> dict[str, User]:
    depts = {code: Department(code=code, name=name) for code, name in DEPARTMENTS}
    s.add_all(depts.values())
    s.flush()
    users: dict[str, User] = {}
    for name, local, role, dept, trained, head in USERS:
        u = User(name=name, email=f"{local}@{MAIL_DOMAIN}", role=role,
                 department_id=depts[dept].id if dept else None, trained_auditor=trained)
        s.add(u)
        s.flush()
        users[local] = u
        if head:
            depts[dept].head_user_id = u.id
    for code, name, dept, manager in PROJECTS:
        s.add(Project(code=code, name=name, department_id=depts[dept].id, manager_user_id=users[manager].id,
                      assignment_basis="synthetic-fixture"))
    for y in years:
        for d, n in holidays(y):
            s.add(Holiday(day=d, name=n))
    s.flush()
    return users
