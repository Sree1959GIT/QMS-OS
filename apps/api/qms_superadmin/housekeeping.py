"""housekeeping-check (R-38): report what needs doing in the documentation and name what to use for it.

Read-only: ``git rev-parse`` (local refs only, no network) and the files under ``docs/``. Nothing is written. Checks:
the baseline hashes and "as of" text in ROADMAP and HANDOFF against ``main``; the work-in-progress branch named in
HANDOFF against the current branch; the claims register's line references (``claims_register.check``).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import claims_register

REPO = Path(__file__).resolve().parents[3]
NO_SKILL = "a development pull request (no skill writes documents)"


def _git(*args: str, repo: Path) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else ""


def _main_hash(repo: Path) -> str:
    return _git("rev-parse", "origin/main", repo=repo) or _git("rev-parse", "main", repo=repo)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def check(repo: Path = REPO, main_hash: str | None = None, branch: str | None = None) -> list[str]:
    docs = repo / "docs"
    main = main_hash if main_hash is not None else _main_hash(repo)
    current = branch if branch is not None else _git("rev-parse", "--abbrev-ref", "HEAD", repo=repo)
    findings: list[str] = []
    roadmap, handoff = _read(docs / "ROADMAP.md"), _read(docs / "HANDOFF.md")
    places = [
        ("docs/ROADMAP.md Current baseline", re.search(r"## Current baseline\s+A synthetic-data backend prototype on "
                                                       r"`main` at `([0-9a-f]{7,40})`", roadmap)),
        ("docs/ROADMAP.md remaining-slices \"as of\"", re.search(r"as of `([0-9a-f]{7,40})`", roadmap)),
        ("docs/HANDOFF.md snapshot baseline",
         re.search(r"Baseline recorded here: `main` at `([0-9a-f]{7,40})`", handoff)),
    ]
    for where, m in places:
        if m is None:
            findings.append(f"{where}: no baseline hash found -> check the wording; use {NO_SKILL}")
        elif main and not main.startswith(m.group(1)):
            findings.append(f"{where}: says {m.group(1)}, main is {main[:7]} -> update it; use {NO_SKILL}")
    wip = re.search(r"Work in progress: branch `([^`]+)`", handoff)
    if wip and current and wip.group(1) != current:
        findings.append(f"docs/HANDOFF.md work in progress names branch {wip.group(1)}, the current branch is "
                        f"{current} -> update the snapshot; use {NO_SKILL}")
    try:
        diffs = claims_register.check(docs)
    except claims_register.AnchorError as e:
        diffs = [f"anchor error: {e}"]
    if diffs:
        findings.append(f"docs/UPSTREAMS.md claims register: {len(diffs)} line(s) out of date (first: {diffs[0]}) -> "
                        "print the current register with `python -m qms_superadmin claims-register --print` and "
                        f"replace the section; use {NO_SKILL}")
    out = [f"main: {main[:7] if main else 'unknown'}; current branch: {current or 'unknown'}",
           f"findings: {len(findings)}"]
    out += [f"- {f}" for f in findings]
    out.append("database reviews: run the review-org, access-segregation and inspect-workflow-completeness skills on "
               "the synthetic demo or test database (QMS_DATABASE_URL, QMS_MODE=demo or test), and "
               "knowledge-integrity on the interim evidence store (also QMS_EVIDENCE_DIR)")
    return out
