"""Calendar rules. Expectations are derived from the (synthetic example) policy, never hard-coded."""
from datetime import date, timedelta
from itertools import pairwise

import pytest

from qms_os.demo_policy import DEMO_POLICY as P
from qms_os.rules import calendar as C

HOL = {date(2026, 1, 1), date(2026, 5, 1)}
DEPTS = ["a", "b", "c", "d", "e"]
MILESTONES = [("notify", "notify_offset_days"), ("evidence_due", "evidence_due_offset_days"),
              ("report_due", "report_due_offset_days"), ("action_plan_due", "action_plan_due_offset_days"),
              ("closure_limit", "closure_limit_days")]


def test_working_day_helpers():
    assert C.next_working_day(date(2026, 1, 3), HOL) == date(2026, 1, 5)       # Sat -> Mon
    assert C.previous_working_day(date(2026, 1, 4), HOL) == date(2026, 1, 2)   # Sun -> Fri
    assert C.previous_working_day(date(2026, 1, 1), HOL) == date(2025, 12, 31)  # holiday


@pytest.mark.parametrize("audit_day", [date(2026, 3, 9) + timedelta(days=i) for i in range(5)])  # Mon..Fri
def test_subplan_milestones_roll_back_to_previous_working_day(audit_day):
    sp = C.subplan(audit_day, P, HOL)
    assert sp.audit == audit_day
    for attr, key in MILESTONES:
        raw = audit_day + timedelta(days=P.v(key))
        got = getattr(sp, attr)
        assert C.is_working_day(got, HOL)
        assert got == (raw if C.is_working_day(raw, HOL) else C.previous_working_day(raw, HOL))
    assert (sp.audit - sp.notify).days >= -P.v("notify_offset_days")       # notice never shrinks
    assert (sp.closure_limit - sp.audit).days <= P.v("closure_limit_days")  # limit never stretches


def test_roll_back_is_exercised_by_the_fixture():
    """Guard against a vacuous test: across one week at least one milestone must land on a weekend."""
    rolled = [attr for i in range(5) for attr, key in MILESTONES
              if not C.is_working_day(date(2026, 3, 9) + timedelta(days=i + P.v(key)), HOL)]
    assert rolled


def test_plan_cycles_default_blocks_cover_all_departments():
    cycles = C.plan_cycles(2026, DEPTS, P, HOL)
    start = date(2026, *map(int, P.v("audit_window_start").split("-")))
    end = date(2026, *map(int, P.v("audit_window_end").split("-")))
    assert [c.code for c in cycles] == [f"2026-C{i + 1}" for i in range(P.v("cycles_per_year"))]
    for c in cycles:
        assert set(c.schedule) == set(DEPTS)
        assert len(c.days) == P.v("audit_block_days") and all(C.is_working_day(d, HOL) for d in c.days)
        assert set(c.schedule.values()) <= set(c.days)
        assert start <= c.days[0] and c.days[-1] <= end
    for earlier, later in pairwise(cycles):
        assert later.days[0] > earlier.days[-1]


def test_plan_cycles_rejects_below_minimum_and_overflow():
    with pytest.raises(ValueError):
        C.plan_cycles(2026, DEPTS, P, HOL, cycles=P.v("min_cycles_per_year") - 1)
    with pytest.raises(ValueError):
        C.plan_cycles(2026, [], P, HOL)
    assert len(C.plan_cycles(2026, DEPTS, P, HOL, cycles=4)) == 4
