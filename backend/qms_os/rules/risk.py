"""FMEA risk scoring.

Derived from development reference VREF-07 (candidate guidance):
Severity x Occurrence x Detection, each on a policy-configured rating scale; an RPN at
or above the policy threshold is Significant (action plan required), below it
Acceptable; periodic review at a policy-configured interval.

Arithmetic is deterministic and never delegated to an AI component. Rating-scale
definitions await process-owner confirmation (docs/DECISIONS.md D-07).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ..policy import Policy


@dataclass(frozen=True)
class RiskScore:
    rpn: int
    classification: str        # "S" significant | "A" acceptable
    action_plan_required: bool


def score(severity: int, occurrence: int, detection: int, policy: Policy) -> RiskScore:
    lo, hi = policy.v("risk_rating_min"), policy.v("risk_rating_max")
    for name, val in (("severity", severity), ("occurrence", occurrence), ("detection", detection)):
        if not isinstance(val, int) or not lo <= val <= hi:
            raise ValueError(f"{name} must be an integer from {lo} to {hi}")
    rpn = severity * occurrence * detection
    significant = rpn >= policy.v("risk_significant_rpn")
    return RiskScore(rpn=rpn, classification="S" if significant else "A", action_plan_required=significant)


def next_review(from_day: date, policy: Policy) -> date:
    return from_day + timedelta(days=policy.v("risk_review_interval_days"))
