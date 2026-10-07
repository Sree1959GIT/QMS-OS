"""Finding (NC/AFI/Compliance) lifecycle, identifiers, aging and reporting rules.

Derived from development references VREF-04, VREF-06, VREF-08, VREF-09, VREF-11,
VREF-16 (candidate guidance): finding classifications; auditor and auditee sections of
the nonconformity report; corrective action with owner and target date; follow-up
verification by the auditor before closure; a periodic NC status report that does not
carry forward earlier closures; a policy-configured closure limit with green/amber/red
aging; closure requires an evidence reference.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from ..policy import Policy


class Category(StrEnum):
    MAJOR_NC = "MAJOR_NC"
    MINOR_NC = "MINOR_NC"
    AFI = "AFI"
    COMPLIANCE = "COMPLIANCE"

    @property
    def is_nc(self) -> bool:
        return self in (Category.MAJOR_NC, Category.MINOR_NC)


class Status(StrEnum):
    DRAFT = "DRAFT"                      # auditor working state, before report issue
    OPEN = "OPEN"                        # reported to auditee; awaiting accepted action plan
    ACTION_PLANNED = "ACTION_PLANNED"    # MA accepted corrective action plan
    PENDING_VERIFICATION = "PENDING_VERIFICATION"  # auditee submitted closure evidence
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"


class Role(StrEnum):
    MA = "MA"              # quality management representative (role code)
    AUDITOR = "AUDITOR"
    AUDITEE = "AUDITEE"    # department head / process owner
    MD = "MD"
    VIEWER = "VIEWER"


class Action(StrEnum):
    ISSUE_REPORT = "issue_report"
    ACCEPT_ACTION_PLAN = "accept_action_plan"
    SUBMIT_CLOSURE = "submit_closure"
    VERIFY = "verify"
    REJECT_VERIFICATION = "reject_verification"
    ESCALATE = "escalate"
    DEESCALATE = "deescalate"
    ACKNOWLEDGE_AFI = "acknowledge_afi"


@dataclass(frozen=True)
class Transition:
    to: Status
    roles: frozenset[Role]
    categories: frozenset[Category]


_NC = frozenset({Category.MAJOR_NC, Category.MINOR_NC})
_NC_AFI = _NC | {Category.AFI}
_ALL = frozenset(Category)

TRANSITIONS: dict[tuple[Status, Action], Transition] = {
    (Status.DRAFT, Action.ISSUE_REPORT): Transition(Status.OPEN, frozenset({Role.AUDITOR}), _NC_AFI),
    (Status.OPEN, Action.ACCEPT_ACTION_PLAN): Transition(Status.ACTION_PLANNED, frozenset({Role.MA}), _NC_AFI),
    (Status.ESCALATED, Action.ACCEPT_ACTION_PLAN): Transition(Status.ACTION_PLANNED, frozenset({Role.MA}), _NC_AFI),
    (Status.ACTION_PLANNED, Action.SUBMIT_CLOSURE):
        Transition(Status.PENDING_VERIFICATION, frozenset({Role.AUDITEE}), _NC_AFI),
    (Status.PENDING_VERIFICATION, Action.VERIFY): Transition(Status.CLOSED, frozenset({Role.AUDITOR}), _NC_AFI),
    (Status.PENDING_VERIFICATION, Action.REJECT_VERIFICATION):
        Transition(Status.ACTION_PLANNED, frozenset({Role.AUDITOR}), _NC_AFI),
    (Status.OPEN, Action.ESCALATE): Transition(Status.ESCALATED, frozenset({Role.MA}), _NC),
    (Status.ACTION_PLANNED, Action.ESCALATE): Transition(Status.ESCALATED, frozenset({Role.MA}), _NC),
    (Status.ESCALATED, Action.DEESCALATE): Transition(Status.OPEN, frozenset({Role.MA}), _NC),
    (Status.OPEN, Action.ACKNOWLEDGE_AFI): Transition(Status.CLOSED, frozenset({Role.MA}), frozenset({Category.AFI})),
}


class TransitionError(ValueError):
    pass


def next_status(category: Category, current: Status, action: Action, role: Role) -> Status:
    """Validate a lifecycle transition. Compliance findings close on report issue."""
    if category is Category.COMPLIANCE:
        if current is Status.DRAFT and action is Action.ISSUE_REPORT and role is Role.AUDITOR:
            return Status.CLOSED
        raise TransitionError("compliance observations have no lifecycle beyond report issue")
    t = TRANSITIONS.get((current, action))
    if t is None or category not in t.categories:
        raise TransitionError(f"'{action}' is not allowed for a {category} in status {current}")
    if role not in t.roles:
        raise TransitionError(f"'{action}' requires role {'/'.join(sorted(t.roles))}")
    return t.to


def finding_code(cycle_code: str, dept_code: str, category: Category, n: int) -> str:
    """e.g. 2026-c1-hr-nc-2 / 2026-c1-hr-afi-1 / 2026-c1-hr-cmp-1"""
    kind = "nc" if category.is_nc else ("afi" if category is Category.AFI else "cmp")
    return f"{cycle_code.lower()}-{dept_code.lower()}-{kind}-{n}"


def closure_limit(report_date: date, policy: Policy) -> date:
    return report_date + timedelta(days=policy.v("closure_limit_days"))


def check_planned_closure(planned: date, report_date: date, policy: Policy) -> None:
    """VREF-08 (plan acceptance): plans beyond the closure limit are bounced."""
    if planned < report_date:
        raise ValueError("planned closure date cannot be before the report date")
    limit = closure_limit(report_date, policy)
    if planned > limit:
        raise ValueError(f"planned closure {planned} is after the closure limit {limit} "
                         f"({policy.v('closure_limit_days')} days from report)")


class Aging(StrEnum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    NONE = "NONE"   # closed or not yet reported


def aging(status: Status, report_date: date | None, planned_closure: date | None,
          today: date, policy: Policy) -> Aging:
    """VREF-09: RED = overdue or open beyond the closure limit."""
    if status in (Status.CLOSED, Status.DRAFT) or report_date is None:
        return Aging.NONE
    due = planned_closure or closure_limit(report_date, policy)
    due = min(due, closure_limit(report_date, policy))
    if status is Status.ESCALATED or today > due:
        return Aging.RED
    if (due - today).days <= policy.v("amber_window_days"):
        return Aging.AMBER
    return Aging.GREEN


def in_monthly_report(status: Status, closed_on: date | None, reported_on: date | None,
                      month_start: date, month_end: date) -> bool:
    """VREF-04: the MA monthly NC status report lists NCs open during the month;
    NCs closed in an earlier month are not carried forward."""
    if status is Status.DRAFT or reported_on is None or reported_on > month_end:
        return False
    if status is Status.CLOSED and closed_on is not None and closed_on < month_start:
        return False
    return True
