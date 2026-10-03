from datetime import date

import pytest

from qms_os.demo_policy import DEMO_POLICY as P
from qms_os.rules.assignment import AssignmentError, Auditor, Slot, assign, validate

DEPTS = ["a", "b", "c", "d", "e", "f"]
D1, D2, D3, D4 = date(2026, 2, 2), date(2026, 2, 3), date(2026, 6, 1), date(2026, 6, 2)
AUDITORS = [Auditor(i + 1, d) for i, d in enumerate(DEPTS)] + [Auditor(7, "a"), Auditor(8, "f", trained=False)]


def slots():
    out = []
    for cyc, (x, y) in enumerate([(D1, D2), (D3, D4)], start=1):
        out += [Slot(cyc, d, x if i < 3 else y) for i, d in enumerate(DEPTS)]
    return out


def test_assignment_satisfies_all_hard_rules_and_is_deterministic():
    res = assign(slots(), AUDITORS, P)
    assert [v for v in validate(res, P) if v.blocking] == []
    assert all(a.trained for a in res.values())
    assert res == assign(slots(), AUDITORS, P)


def test_rotation_prefers_new_auditor_department_each_cycle():
    res = assign(slots(), AUDITORS, P)
    for d in DEPTS:
        c1 = next(a.dept for s, a in res.items() if s.auditee == d and s.cycle == 1)
        c2 = next(a.dept for s, a in res.items() if s.auditee == d and s.cycle == 2)
        assert c1 != c2


def test_validate_flags_each_rule():
    s1, s2, s3 = Slot(1, "a", D1), Slot(1, "b", D1), Slot(1, "c", D1)
    v = validate({s1: Auditor(1, "a")}, P)
    assert [x.rule for x in v] == ["independence"]
    v = validate({s1: Auditor(2, "b"), s2: Auditor(1, "a")}, P)
    assert [(x.rule, x.blocking) for x in v] == [("reciprocity_d13", False)]   # D-13 unresolved: advisory only
    v = validate({s2: Auditor(9, "d"), s3: Auditor(9, "d")}, P)
    assert [x.rule for x in v] == ["workload"]
    v = validate({s1: Auditor(8, "f", trained=False)}, P)
    assert [(x.rule, x.blocking) for x in v] == [("trained", True)]


def test_infeasible_roster_raises():
    with pytest.raises(AssignmentError):
        assign(slots(), [Auditor(1, "a")], P)


def test_fixed_assignments_are_respected_and_reciprocity_is_avoided_when_possible():
    fixed = {Slot(1, "b", D1): Auditor(1, "a")}
    res = assign(slots(), AUDITORS, P, fixed=fixed)
    assert res[Slot(1, "b", D1)].id == 1
    assert not any(s.auditee == "a" and a.dept == "b" for s, a in res.items())
