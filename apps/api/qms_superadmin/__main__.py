"""python -m qms_superadmin COMMAND  (run from apps/api; scripts\\run-superadmin.bat does that).

Commands: housekeeping | review-org | access-segregation | knowledge-integrity | inspect-workflow-completeness |
          claims-register [--print]
Exit codes: 0 nothing to report, 1 findings reported, 2 refused (wrong mode or no database named).
Every command reads only; none writes a file, calls the network or reads .private or .env (R-46).
"""
from __future__ import annotations

import argparse
import sys

from . import (
    access_segregation,
    claims_register,
    housekeeping,
    knowledge_integrity,
    review_org,
    workflow_completeness,
)
from .readonly import Refused, read_only_session


def _report(lines: list[str]) -> int:
    print("\n".join(lines))
    findings = next((ln for ln in lines if ln.startswith("findings: ")), "findings: 0")
    return 0 if findings == "findings: 0" else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m qms_superadmin")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("housekeeping", help="what needs doing in the documentation")
    sub.add_parser("review-org", help="departments and people (synthetic database, read-only)")
    sub.add_parser("access-segregation", help="what each person and agent can read (synthetic database, read-only)")
    sub.add_parser("knowledge-integrity", help="the interim evidence store: synthetic only, hashes match (read-only)")
    sub.add_parser("inspect-workflow-completeness",
                   help="workflow versions: completeness, digests against approvals, changes from findings")
    cr = sub.add_parser("claims-register", help="check the claims register's line references")
    cr.add_argument("--print", action="store_true", help="print the generated register section to stdout")
    args = ap.parse_args(argv)
    if args.cmd == "housekeeping":
        return _report(housekeeping.check())
    if args.cmd == "claims-register":
        if args.print:
            lines, _ = claims_register.build(housekeeping.REPO / "docs")
            print("\n".join(lines))
            return 0
        diffs = claims_register.check(housekeeping.REPO / "docs")
        return _report([f"findings: {len(diffs)}", *[f"- {d}" for d in diffs]])
    try:
        with read_only_session() as (s, mode):
            if args.cmd == "knowledge-integrity":
                lines = knowledge_integrity.review(s, knowledge_integrity.open_store(mode))
            elif args.cmd == "inspect-workflow-completeness":
                lines = workflow_completeness.review(s)
            else:
                lines = (review_org.review(s) if args.cmd == "review-org" else access_segregation.review(s))
            return _report([f"database mode: {mode} (read-only)", *lines])
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
