"""Grants and the effective-access preview (MVP-1 slice 3; R-31, R-43, R-44).

The preview and the enforcement use the same two functions (``services/access.py``); these tests check that they
agree for every fixture person and every grant-governed resource, after narrowing the synthetic fixture grants.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from qms_os.db import make_sessionmaker
from qms_os.models import (
    ORG_ADMIN,
    AuditEvent,
    Delegation,
    Department,
    MailboxScope,
    PlatformPermission,
    Project,
    RoleGrant,
    User,
)
from qms_os.services import access as ACC
from qms_os.timeutil import utcnow

ORG = "/api/v1/org"
LISTS = {"department": "/api/v1/departments", "person": "/api/v1/users", "project": "/api/v1/projects"}


def _session(engine):
    return make_sessionmaker(engine)()


def _narrow(engine) -> dict:
    """Make the fixture grants differ by role and resource: one confidential department that only MA may read, VIEWER
    sees projects only as a member, and one confidential person."""
    with _session(engine) as s:
        qa = s.scalar(select(Department).where(Department.code == "qa"))
        qa.classification = "confidential"
        s.add(RoleGrant(role="MA", resource_kind="department", max_classification="confidential"))
        for g in s.scalars(select(RoleGrant).where(RoleGrant.role == "VIEWER", RoleGrant.resource_kind == "project")):
            g.revoked_at = utcnow()
        s.add(RoleGrant(role="VIEWER", resource_kind="project", max_classification="internal", scope="member"))
        md = s.scalar(select(User).where(User.email.like("md@%")))
        md.classification = "confidential"
        s.commit()
        return {"qa": qa.id, "md": md.id}


def _all_ids(engine) -> dict[str, list[int]]:
    with _session(engine) as s:
        return {k: list(s.scalars(select(m.id).order_by(m.id))) for k, m in ACC.MODELS.items()}


@pytest.fixture
def oa(api, engine):
    with _session(engine) as s:
        s.add(PlatformPermission(user_id=api.users["viewer"], permission=ORG_ADMIN))
        s.commit()
    return api.as_("viewer")


def test_fixture_grants_reproduce_the_previous_directory_visibility(api, engine):
    every = _all_ids(engine)
    for who in ("ma", "md", "qa_head", "eng_auditor", "viewer"):
        for kind, url in LISTS.items():
            assert [r["id"] for r in api.as_(who).get(url).json()] == every[kind], (who, kind)


def test_preview_and_enforcement_agree_for_every_fixture_person_and_resource(api, engine, oa):
    _narrow(engine)
    every = _all_ids(engine)
    disagreements = []
    for local, uid in api.users.items():
        preview = oa.get(f"{ORG}/access-preview/{uid}").json()
        caller = api.as_(uid)
        for kind, url in LISTS.items():
            listed = [r["id"] for r in caller.get(url).json()]
            single = [i for i in every[kind] if caller.get(f"{url}/{i}").status_code == 200]
            if not (preview["readable"][kind] == listed == single):
                disagreements.append((local, kind, preview["readable"][kind], listed, single))
            assert sorted(preview["readable"][kind] + preview["denied"][kind]) == every[kind]
    assert disagreements == []


def test_narrowed_grants_have_the_expected_effect(api, engine, oa):
    ids = _narrow(engine)
    assert ids["qa"] in [d["id"] for d in api.as_("ma").get(LISTS["department"]).json()]
    assert ids["qa"] not in [d["id"] for d in api.as_("md").get(LISTS["department"]).json()]
    assert api.as_("viewer").get(LISTS["project"]).json() == []             # VIEWER: member scope, no memberships
    pm_projects = [p["id"] for p in api.as_("eng_pm").get(LISTS["project"]).json()]
    assert len(pm_projects) == 2                                          # AUDITEE keeps scope all


def test_a_denied_single_read_is_404_and_leaks_nothing(api, engine):
    ids = _narrow(engine)
    with _session(engine) as s:
        qa = s.get(Department, ids["qa"])
        secret_values = [qa.code, qa.name]
    r = api.as_("qa_auditor").get(f"{LISTS['department']}/{ids['qa']}")
    assert r.status_code == 404
    body = json.dumps(r.json())
    assert not any(v in body for v in secret_values)
    missing = api.as_("qa_auditor").get(f"{LISTS['department']}/999999")
    assert missing.status_code == 404 and set(missing.json()) == set(r.json())   # same shape as a missing record
    # a readable person in an unreadable department does not reveal the department's name
    person = next(p for p in api.as_("qa_auditor").get(LISTS["person"]).json() if p["department_id"] == ids["qa"])
    assert person["department"] is None


def test_member_scope_follows_membership_changes(api, engine, oa):
    _narrow(engine)
    viewer = api.users["viewer"]
    with _session(engine) as s:
        project = s.scalar(select(Project).order_by(Project.id))
    # the org admin is the viewer here, so membership is managed for another VIEWER-role check via MD's role instead
    with _session(engine) as s:
        for g in s.scalars(select(RoleGrant).where(RoleGrant.role == "MD", RoleGrant.resource_kind == "project")):
            g.revoked_at = utcnow()
        s.add(RoleGrant(role="MD", resource_kind="project", max_classification="internal", scope="member"))
        s.commit()
    md = api.as_("md")
    assert md.get(f"{LISTS['project']}/{project.id}").status_code == 404
    assert oa.post(f"{ORG}/projects/{project.id}/members", {"user_id": api.users["md"]}).status_code == 200
    assert md.get(f"{LISTS['project']}/{project.id}").status_code == 200
    assert oa.post(f"{ORG}/projects/{project.id}/members/{api.users['md']}/remove").status_code == 200
    assert md.get(f"{LISTS['project']}/{project.id}").status_code == 404
    assert oa.post(f"{ORG}/projects/{project.id}/members", {"user_id": viewer}).status_code == 403   # not themselves


def test_role_grant_changes_are_audited_and_never_for_the_org_admins_own_role(api, engine, oa):
    r = oa.post(f"{ORG}/role-grants", {"role": "AUDITOR", "resource_kind": "person", "max_classification": "public"})
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    assert oa.post(f"{ORG}/role-grants/{gid}/revoke").json()["active"] is False
    assert oa.post(f"{ORG}/role-grants", {"role": "VIEWER", "resource_kind": "person",
                                          "max_classification": "confidential"}).status_code == 403   # own role
    assert oa.post(f"{ORG}/role-grants", {"role": "AUDITOR", "resource_kind": "mailbox",
                                          "max_classification": "public"}).status_code == 422
    assert oa.post(f"{ORG}/role-grants", {"role": "AUDITOR", "resource_kind": "person", "max_classification": "secret",
                                          }).status_code == 422
    assert oa.post(f"{ORG}/role-grants", {"role": "AUDITOR", "resource_kind": "person", "max_classification": "public",
                                          "scope": "member"}).status_code == 422
    with _session(engine) as s:
        actions = [e.action for e in s.scalars(select(AuditEvent).where(AuditEvent.action.like("org.role_grant.%"))
                                               .order_by(AuditEvent.id))]
    assert actions == ["org.role_grant.added", "org.role_grant.revoked"]


def test_mailbox_scope_and_delegation_are_declared_empty_and_do_not_decide(api, engine):
    with _session(engine) as s:
        assert s.scalar(select(MailboxScope.id)) is None and s.scalar(select(Delegation.id)) is None
        md = s.scalar(select(User).where(User.email.like("md@%")))
        before = ACC.effective_access(s, md)
        s.add(MailboxScope(user_id=md.id, mailbox_ref="synthetic-mailbox"))
        s.add(Delegation(from_user_id=api.users["ma"], to_user_id=md.id, starts_at=utcnow(), ends_at=utcnow()))
        s.flush()
        after = ACC.effective_access(s, md)
        resources = [ACC.resource_of(o) for m in ACC.MODELS.values() for o in s.scalars(select(m))]
        assert [ACC.decide(before, r) for r in resources] == [ACC.decide(after, r) for r in resources]
        assert after.mailbox_scopes and after.delegations                 # visible in the preview, never decisive
        s.rollback()


def test_a_deactivated_person_reads_nothing(api, engine):
    with _session(engine) as s:
        s.get(User, api.users["eng_auditor"]).active = False
        s.commit()
    for url in LISTS.values():
        assert api.as_("eng_auditor").get(url).json() == []


def test_without_role_grants_nobody_reads_the_directory(api, engine):
    """R-43: operational mode starts with no role grants, so only org admins (through /org) see the directory."""
    with _session(engine) as s:
        for g in s.scalars(select(RoleGrant)):
            g.revoked_at = utcnow()
        s.commit()
    for who in ("ma", "md", "viewer"):
        for url in LISTS.values():
            assert api.as_(who).get(url).json() == []


def test_the_preview_needs_the_org_admin_permission(api):
    assert api.as_("ma").get(f"{ORG}/access-preview/{api.users['md']}").status_code == 403
