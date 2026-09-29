"""Fixtures and demo data must be visibly synthetic: reserved mail domain, role-coded people, '(fixture)'
departments and a fictional organisation name. (No real names are listed here — that would publish them.)"""
from qms_os import fixtures as FX


def test_fixture_identities_are_visibly_synthetic():
    assert FX.MAIL_DOMAIN.endswith(".example")
    assert "fictional" in FX.ORG_NAME.lower()
    assert all(name.endswith("(fixture)") for _, name in FX.DEPARTMENTS)
    assert all(name.startswith("Fixture ") for name, *_ in FX.USERS)
    assert all(code.startswith("P-SYN-") and name.startswith("Synthetic ") for code, name, *_ in FX.PROJECTS)
    assert all(name.startswith("Fixture holiday") for _, name in FX.holidays(2026))


def test_seeded_users_carry_only_the_reserved_domain(api):
    emails = [u["email"] for u in api.as_("ma").get("/api/users").json()]
    assert emails and all(e.endswith("@" + FX.MAIL_DOMAIN) for e in emails)
