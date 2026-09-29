"""Synthetic example policy — loaded ONLY in explicit demo or test mode.

These values are illustrative, not recommendations, and not any organisation's policy.
A synthetic policy can never be submitted or approved as organisational QMS policy, and
programmes planned with it are labelled synthetic.
"""
from .policy import SCHEMA_VERSION, build_policy

SYN = "synthetic example — not organisational policy"
_VALUES = {
    "cycles_per_year": 3,
    "min_cycles_per_year": 1,
    "audit_window_start": "02-01",
    "audit_window_end": "10-31",
    "audit_block_days": 3,
    "notify_offset_days": -10,
    "evidence_due_offset_days": -5,
    "report_due_offset_days": 5,
    "action_plan_due_offset_days": 14,
    "closure_limit_days": 45,
    "amber_window_days": 10,
    "auditor_max_audits_per_day": 1,
    "risk_rating_min": 1,
    "risk_rating_max": 10,
    "risk_significant_rpn": 100,
    "risk_review_interval_days": 180,
}

DEMO_POLICY = build_policy({
    "schema_version": SCHEMA_VERSION,
    "policy_id": "synthetic-demo",
    "policy_version": "demo-1",
    "effective_date": "2000-01-01",
    "declared_status": "synthetic-example",
    "params": {k: {"value": v, "source": SYN} for k, v in _VALUES.items()},
}, origin="synthetic-demo")
