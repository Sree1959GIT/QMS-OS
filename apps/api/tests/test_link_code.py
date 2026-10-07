"""One-time link verification code (link-code slice; ADR 0003).

A link needs two parts: the link token (shown once to the approving admin) and a verification code (shown once to the
initiating admin, who tells the person in person). Uses the real sign-in harness from test_auth.py.
"""
from __future__ import annotations

import json
import re
from datetime import timedelta

import pytest
import test_auth as TA
from sqlalchemy import select

from qms_os.auth import cli
from qms_os.auth import service as AS
from qms_os.models import AccountAction, AuditEvent

INVALID_LINK = {"detail": "the link is not valid or has expired", "reason": "invalid_link"}


@pytest.fixture
def h(engine):
    return TA.Harness(engine)


def _two_admins(h):
    """The bootstrap admin plus a second account admin (md), both signed in with a fresh step-up."""
    first = h.bootstrap()
    second = h.onboard(first, "md")                                  # single-admin bootstrap invitation
    assert cli.run_grant(h.app.state.sessionmaker, second.email, read_line=lambda _: second.email,
                         write=lambda _: None) == 0
    second.login()
    first.login()
    return first, second


def _setup(h, token, code, password=TA.GOOD):
    return h.client().post("/api/auth/setup", json={"token": token, "verification_code": code, "password": password})


def _action(h, action_id) -> AccountAction:
    with h.db() as s:
        return s.get(AccountAction, action_id)


def _events(h, prefix):
    with h.db() as s:
        return list(s.scalars(select(AuditEvent).where(AuditEvent.action.like(f"{prefix}%")).order_by(AuditEvent.id)))


def test_initiator_gets_only_the_code_and_approver_only_the_link(h):
    first, second = _two_admins(h)
    req = first.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    assert req["status"] == "pending_approval" and req["split_knowledge"] is True
    assert re.fullmatch(r"[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{5}-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{5}",
                        req["verification_code"]) and "link_token" not in req
    assert first.post(f"/api/admin/account-actions/{req['id']}/approve").status_code == 403   # not the initiator
    ok = second.post(f"/api/admin/account-actions/{req['id']}/approve").json()
    assert ok["status"] == "link_issued" and ok["link_token"] and "verification_code" not in ok
    assert _setup(h, ok["link_token"], req["verification_code"].lower().replace("-", " ")).status_code == 200
    qa_events = [e.action for e in _events(h, "auth.invite.") if e.entity_id == h.uid("qa_head")]
    assert qa_events == ["auth.invite.approved"]                     # no single-admin flag for this invitation


def test_neither_part_alone_redeems_the_link(h):
    first, second = _two_admins(h)
    req = first.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    ok = second.post(f"/api/admin/account-actions/{req['id']}/approve").json()
    assert _setup(h, ok["link_token"], "").json() == INVALID_LINK                       # the approver alone
    assert _setup(h, "not-the-link-token", req["verification_code"]).json() == INVALID_LINK   # the initiator alone


def test_the_code_is_checked_only_after_the_token_matches(h):
    first, second = _two_admins(h)
    req = first.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    second.post(f"/api/admin/account-actions/{req['id']}/approve")
    for _ in range(6):                                                # wrong token, right code: nothing counted
        assert _setup(h, "not-the-link-token", req["verification_code"]).json() == INVALID_LINK
    assert _action(h, req["id"]).code_attempts == 0 and _events(h, "auth.link.") == []


def test_five_wrong_codes_void_the_link(h):
    first, second = _two_admins(h)
    req = first.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    token = second.post(f"/api/admin/account-actions/{req['id']}/approve").json()["link_token"]
    for _ in range(5):
        assert _setup(h, token, "22222-22222").json() == INVALID_LINK
    action = _action(h, req["id"])
    assert action.status == "void" and action.code_attempts == 5
    assert _setup(h, token, req["verification_code"]).json() == INVALID_LINK              # even the right code now
    rejected, voided = _events(h, "auth.link.code_rejected"), _events(h, "auth.link.voided")
    assert [e.detail["attempt"] for e in rejected] == [1, 2, 3, 4, 5] and len(voided) == 1


def test_single_admin_bootstrap_invitation_gives_both_parts_and_is_flagged(h):
    admin = h.bootstrap()
    issued = admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    assert issued["split_knowledge"] is False and issued["link_token"] and issued["verification_code"]
    assert issued["status"] == "link_issued"
    flagged = _events(h, "auth.invite.single_admin")
    assert len(flagged) == 1 and flagged[0].detail == {"action_id": issued["id"]}


def test_disabling_the_second_admin_does_not_reopen_the_exception(h):
    first, second = _two_admins(h)
    assert first.post(f"/api/admin/accounts/{h.uid('md')}/disable").status_code == 200
    r = first.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite")
    assert r.status_code == 409 and r.json()["rule"] == "second_admin_required"
    assert "link_token" not in r.text and "verification_code" not in r.text
    assert _events(h, "auth.invite.single_admin")[1:] == []                          # only md's own bootstrap invite
    with h.db() as s:
        assert s.scalars(select(AccountAction).where(AccountAction.split_knowledge.is_(False),
                                                     AccountAction.target_user_id == h.uid("qa_head"))).all() == []


def test_pending_request_expires_after_72_hours(h):
    first, second = _two_admins(h)
    req = first.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    h.now.tick(hours=72)
    second.login()
    r = second.post(f"/api/admin/account-actions/{req['id']}/approve")
    assert r.status_code == 422 and "expired" in r.json()["detail"]


def test_code_expires_with_the_link(h):
    admin = h.bootstrap()
    issued = admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    h.now.tick(hours=24)
    assert _setup(h, issued["link_token"], issued["verification_code"]).json() == INVALID_LINK


def test_links_issued_without_a_code_are_refused(h):
    """Links from before this slice (no code_hash) cannot be redeemed; they must be issued again."""
    admin = h.bootstrap()
    issued = admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    with h.db() as s:
        s.get(AccountAction, issued["id"]).code_hash = None                         # as a pre-upgrade row
        s.commit()
    assert _setup(h, issued["link_token"], issued["verification_code"]).json() == INVALID_LINK


def test_code_is_stored_only_as_argon2id_and_never_logged(h):
    first, second = _two_admins(h)
    req = first.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()
    ok = second.post(f"/api/admin/account-actions/{req['id']}/approve").json()
    _setup(h, ok["link_token"], "22222-22222")
    _setup(h, ok["link_token"], req["verification_code"])
    action = _action(h, req["id"])
    assert action.code_hash.startswith("$argon2id$")
    raw = req["verification_code"].replace("-", "")
    with h.db() as s:
        details = json.dumps([e.detail for e in s.scalars(select(AuditEvent))])
    for secret in (req["verification_code"], raw, ok["link_token"]):
        assert secret not in details and secret not in (action.code_hash or "")


def test_code_alphabet_has_no_look_alikes():
    codes = {AS.new_link_code() for _ in range(200)}
    assert all(len(c) == 11 and c[5] == "-" for c in codes)
    assert not set("".join(codes)) & set("01OIL")
    assert AS.normalise_link_code(" abcde-fghjk ") == "ABCDEFGHJK"


def test_pending_lifetime_and_attempts_are_candidate_limits_that_cannot_be_loosened():
    from qms_os.auth.limits import AuthConfigError, AuthLimits
    AuthLimits(request_lifetime=timedelta(hours=24), link_code_attempts=3)
    for loose in (dict(request_lifetime=timedelta(hours=73)), dict(link_code_attempts=6)):
        with pytest.raises(AuthConfigError, match="not loosened"):
            AuthLimits(**loose)
