"""Finding lifecycle and risk rules. Numeric expectations are derived from the (synthetic example) policy."""
from datetime import date, timedelta
from itertools import product
from math import prod

import pytest

from qms_os.demo_policy import DEMO_POLICY as P
from qms_os.rules import findings as F
from qms_os.rules import risk as R
from qms_os.rules.findings import Action, Category, Role, Status

REPORT = date(2026, 3, 2)
LIMIT = REPORT + timedelta(days=P.v("closure_limit_days"))
AMBER = P.v("amber_window_days")


def test_nc_happy_path_and_roles():
    s = Status.DRAFT
    s = F.next_status(Category.MINOR_NC, s, Action.ISSUE_REPORT, Role.AUDITOR)
    s = F.next_status(Category.MINOR_NC, s, Action.ACCEPT_ACTION_PLAN, Role.MA)
    s = F.next_status(Category.MINOR_NC, s, Action.SUBMIT_CLOSURE, Role.AUDITEE)
    assert F.next_status(Category.MINOR_NC, s, Action.REJECT_VERIFICATION, Role.AUDITOR) is Status.ACTION_PLANNED
    assert F.next_status(Category.MINOR_NC, s, Action.VERIFY, Role.AUDITOR) is Status.CLOSED


@pytest.mark.parametrize("cat,cur,act,role", [
    (Category.MAJOR_NC, Status.OPEN, Action.ACCEPT_ACTION_PLAN, Role.AUDITEE),   # wrong role
    (Category.MAJOR_NC, Status.OPEN, Action.VERIFY, Role.AUDITOR),               # skips stages
    (Category.MAJOR_NC, Status.OPEN, Action.ACKNOWLEDGE_AFI, Role.MA),           # AFI-only action
    (Category.AFI, Status.OPEN, Action.ESCALATE, Role.MA),                       # NC-only action
    (Category.COMPLIANCE, Status.CLOSED, Action.VERIFY, Role.AUDITOR),
])
def test_illegal_transitions(cat, cur, act, role):
    with pytest.raises(F.TransitionError):
        F.next_status(cat, cur, act, role)


def test_compliance_closes_on_report_and_afi_can_be_acknowledged():
    assert F.next_status(Category.COMPLIANCE, Status.DRAFT, Action.ISSUE_REPORT, Role.AUDITOR) is Status.CLOSED
    assert F.next_status(Category.AFI, Status.OPEN, Action.ACKNOWLEDGE_AFI, Role.MA) is Status.CLOSED


def test_codes():
    assert F.finding_code("2026-C1", "HRD", Category.MAJOR_NC, 2) == "2026-c1-hrd-nc-2"
    assert F.finding_code("2026-C1", "hrd", Category.AFI, 1) == "2026-c1-hrd-afi-1"


def test_planned_closure_limit():
    F.check_planned_closure(LIMIT, REPORT, P)                     # exactly on the limit is allowed
    with pytest.raises(ValueError):
        F.check_planned_closure(LIMIT + timedelta(days=1), REPORT, P)
    with pytest.raises(ValueError):
        F.check_planned_closure(REPORT - timedelta(days=1), REPORT, P)


def test_aging():
    a = lambda st, today, planned=None: F.aging(st, REPORT, planned, today, P)  # noqa: E731
    assert a(Status.OPEN, LIMIT - timedelta(days=AMBER + 1)) is F.Aging.GREEN
    assert a(Status.OPEN, LIMIT - timedelta(days=AMBER)) is F.Aging.AMBER
    assert a(Status.OPEN, LIMIT) is F.Aging.AMBER
    assert a(Status.OPEN, LIMIT + timedelta(days=1)) is F.Aging.RED
    planned = REPORT + timedelta(days=1)
    assert a(Status.ACTION_PLANNED, planned + timedelta(days=1), planned=planned) is F.Aging.RED
    assert a(Status.ESCALATED, REPORT + timedelta(days=1)) is F.Aging.RED
    assert a(Status.CLOSED, LIMIT + timedelta(days=60)) is F.Aging.NONE


def test_monthly_report_does_not_carry_forward_closed():
    m0, m1 = date(2026, 4, 1), date(2026, 4, 30)
    assert F.in_monthly_report(Status.OPEN, None, REPORT, m0, m1)
    assert F.in_monthly_report(Status.CLOSED, date(2026, 4, 10), REPORT, m0, m1)
    assert not F.in_monthly_report(Status.CLOSED, date(2026, 3, 20), REPORT, m0, m1)
    assert not F.in_monthly_report(Status.OPEN, None, date(2026, 5, 3), m0, m1)


def test_rpn_threshold_boundary():
    lo, hi, t = P.v("risk_rating_min"), P.v("risk_rating_max"), P.v("risk_significant_rpn")
    triples = list(product(range(lo, hi + 1), repeat=3))
    at = next(x for x in triples if prod(x) == t)                  # a rating combination exactly on the threshold
    below = max((x for x in triples if prod(x) < t), key=prod)     # the highest combination below it
    assert R.score(*at, P) == R.RiskScore(t, "S", True)
    assert R.score(*below, P) == R.RiskScore(prod(below), "A", False)
    assert R.score(lo, lo, lo, P).classification == "A"
    for bad in [(lo - 1, lo, lo), (hi + 1, lo, lo), (lo, lo, "3")]:
        with pytest.raises(ValueError):
            R.score(*bad, P)
