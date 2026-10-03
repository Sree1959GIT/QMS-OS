"""Auditor assignment and objectivity checks.

Derived from development references VREF-02, VREF-03, VREF-13, VREF-17 (candidate
guidance; the VREF register is kept locally and not published):
- BLOCKING: the auditor is independent of the audited function; the auditor has a recorded
  training; a per-day workload limit from policy;
- ADVISORY ONLY: non-reciprocal pairing within a year (A audits B => B does not audit A),
  judged at department level. This is an UNRESOLVED candidate rule (docs/DECISIONS.md D-13),
  not approved organisational policy: it is reported as a warning and preferred by the
  automatic assignment, but it never blocks.
- rotation across cycles is a preference.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..policy import Policy


@dataclass(frozen=True)
class Auditor:
    id: int
    dept: str
    trained: bool = True


@dataclass(frozen=True)
class Slot:
    """One audit to staff: cycle index, auditee department, audit day."""
    cycle: int
    auditee: str
    day: date


@dataclass(frozen=True)
class Violation:
    rule: str
    message: str
    blocking: bool = True


class AssignmentError(ValueError):
    pass


def validate(assignments: dict[Slot, Auditor], policy: Policy) -> list[Violation]:
    """Check a complete or partial assignment. Blocking violations and D-13 advisories are both returned."""
    out: list[Violation] = []
    pairs: dict[tuple[str, str], Slot] = {}
    load: dict[tuple[int, date], int] = {}
    for slot, a in sorted(assignments.items(), key=lambda kv: (kv[0].cycle, kv[0].day, kv[0].auditee)):
        if a.dept == slot.auditee:
            out.append(Violation("independence", f"auditor {a.id} is from {slot.auditee} and cannot audit it"))
        if not a.trained:
            out.append(Violation("trained", f"auditor {a.id} has no recorded internal-audit training"))
        if (slot.auditee, a.dept) in pairs:
            out.append(Violation("reciprocity_d13", f"D-13 unresolved: {a.dept} audits {slot.auditee} and "
                                 f"{slot.auditee} also audits {a.dept}", blocking=False))
        pairs.setdefault((a.dept, slot.auditee), slot)
        k = (a.id, slot.day)
        load[k] = load.get(k, 0) + 1
        if load[k] == policy.v("auditor_max_audits_per_day") + 1:
            out.append(Violation("workload", f"auditor {a.id} has more than "
                                 f"{policy.v('auditor_max_audits_per_day')} audit(s) on {slot.day}"))
    return out


def assign(slots: list[Slot], auditors: list[Auditor], policy: Policy,
           fixed: dict[Slot, Auditor] | None = None, max_steps: int = 200_000) -> dict[Slot, Auditor]:
    """Find an assignment satisfying all blocking rules; prefers non-reciprocal pairs, then rotation.

    ``fixed`` holds assignments that must be kept (e.g. earlier cycles already published) and count
    towards load, reciprocity preference and rotation. Deterministic: same input -> same output.
    """
    fixed = dict(fixed or {})
    bad = [v for v in validate(fixed, policy) if v.blocking]
    if bad:
        raise AssignmentError("existing assignments violate rules: " + "; ".join(v.message for v in bad))

    pool = [a for a in auditors if a.trained]
    todo = sorted((s for s in slots if s not in fixed), key=lambda s: (s.cycle, s.day, s.auditee))
    result = dict(fixed)
    pairs = {(a.dept, s.auditee) for s, a in fixed.items()}
    history = {(s.auditee, a.dept) for s, a in fixed.items()}
    load: dict[tuple[int, date], int] = {}
    for s, a in fixed.items():
        load[(a.id, s.day)] = load.get((a.id, s.day), 0) + 1
    max_load = policy.v("auditor_max_audits_per_day")
    steps = 0

    def candidates(s: Slot) -> list[Auditor]:
        ok = [a for a in pool if a.dept != s.auditee and load.get((a.id, s.day), 0) < max_load]
        total = lambda a: sum(v for (aid, _), v in load.items() if aid == a.id)  # noqa: E731
        # preference order: avoid a reciprocal pair (D-13 advisory), then rotation, then lighter load, then id
        return sorted(ok, key=lambda a: ((s.auditee, a.dept) in pairs, (s.auditee, a.dept) in history,
                                         total(a), a.id))

    def solve(i: int) -> bool:
        nonlocal steps
        if i == len(todo):
            return True
        s = todo[i]
        for a in candidates(s):
            steps += 1
            if steps > max_steps:
                raise AssignmentError("no assignment found within search limit")
            new_pair = (a.dept, s.auditee) not in pairs
            new_hist = (s.auditee, a.dept) not in history
            result[s] = a
            pairs.add((a.dept, s.auditee))
            history.add((s.auditee, a.dept))
            load[(a.id, s.day)] = load.get((a.id, s.day), 0) + 1
            if solve(i + 1):
                return True
            del result[s]
            if new_pair:
                pairs.discard((a.dept, s.auditee))
            if new_hist:
                history.discard((s.auditee, a.dept))
            load[(a.id, s.day)] -= 1
        return False

    if not solve(0):
        raise AssignmentError("no assignment satisfies independence, training and workload rules; "
                              "add trained auditors or change the plan")
    return result
