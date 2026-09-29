"""Audit calendar planning.

Derived from development references VREF-10, VREF-17 (candidate guidance):
equitable spacing of audit cycles across a planning window, a multi-day department
block, working-day adjustment and a per-audit milestone sub-plan (notify, evidence,
audit, report, action plan, closure limit); a reschedule recomputes only the affected
audit. All counts, windows and offsets come from policy (docs/DECISIONS.md).

Design choice: sub-plan milestones that land on a non-working day move to the *previous*
working day, so notice periods never shrink and closure limits never stretch.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from ..policy import Policy


def is_working_day(d: date, holidays: set[date]) -> bool:
    return d.weekday() < 5 and d not in holidays


def next_working_day(d: date, holidays: set[date]) -> date:
    while not is_working_day(d, holidays):
        d += timedelta(days=1)
    return d


def previous_working_day(d: date, holidays: set[date]) -> date:
    while not is_working_day(d, holidays):
        d -= timedelta(days=1)
    return d


@dataclass(frozen=True)
class SubPlan:
    notify: date
    evidence_due: date
    audit: date
    report_due: date
    action_plan_due: date
    closure_limit: date


def subplan(audit_day: date, policy: Policy, holidays: set[date]) -> SubPlan:
    def at(offset: int) -> date:
        return previous_working_day(audit_day + timedelta(days=offset), holidays)

    return SubPlan(
        notify=at(policy.v("notify_offset_days")),
        evidence_due=at(policy.v("evidence_due_offset_days")),
        audit=audit_day,
        report_due=at(policy.v("report_due_offset_days")),
        action_plan_due=at(policy.v("action_plan_due_offset_days")),
        closure_limit=at(policy.v("closure_limit_days")),
    )


@dataclass(frozen=True)
class PlannedCycle:
    code: str
    days: tuple[date, ...]
    # department code -> audit day
    schedule: dict[str, date]


def _mmdd(year: int, mmdd: str) -> date:
    m, d = mmdd.split("-")
    return date(year, int(m), int(d))


def plan_cycles(year: int, departments: Iterable[str], policy: Policy, holidays: set[date],
                cycles: int | None = None) -> list[PlannedCycle]:
    """Spread ``cycles`` audit blocks equitably across the policy window.

    Each cycle audits every department within a block of ``audit_block_days``
    consecutive working days, departments split evenly across the block days.
    """
    depts = list(departments)
    if not depts:
        raise ValueError("at least one department is required")
    n = cycles if cycles is not None else policy.v("cycles_per_year")
    if n < policy.v("min_cycles_per_year"):
        raise ValueError(f"at least {policy.v('min_cycles_per_year')} internal audit cycle(s) required per year")
    start = _mmdd(year, policy.v("audit_window_start"))
    end = _mmdd(year, policy.v("audit_window_end"))
    if end <= start:
        raise ValueError("audit window end must be after start")
    step = (end - start).days // n                      # equal slices of the window, one cycle per slice
    anchors = [start + timedelta(days=i * step) for i in range(n)]
    block = max(1, policy.v("audit_block_days"))
    per_day = -(-len(depts) // block)  # ceil

    out: list[PlannedCycle] = []
    for number, anchor in enumerate(anchors, start=1):
        days: list[date] = [next_working_day(anchor, holidays)]
        while len(days) < block:
            days.append(next_working_day(days[-1] + timedelta(days=1), holidays))
        if days[-1] > end:
            raise ValueError(f"cycle {number} does not fit inside the audit window")
        schedule = {dept: days[min(i // per_day, block - 1)] for i, dept in enumerate(depts)}
        out.append(PlannedCycle(code=f"{year}-C{number}", days=tuple(days), schedule=schedule))
    return out
