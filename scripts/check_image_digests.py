"""CI image-digest check (docs/DECISIONS.md R-21; ROADMAP slice 3a). Standard library only.

Fails when a container image reference in a tracked Dockerfile, Containerfile, compose file or GitHub workflow is not
pinned by digest (``@sha256:`` and 64 lowercase hex characters; ``name:tag@sha256:...`` passes) and is not listed in
the baseline file. The baseline is a ratchet: an entry that no longer matches a reference also fails, so a fixed
reference cannot quietly come back. Baseline lines are ``<path> <reference>``, sorted and unique; ``#`` starts a
comment. One entry covers every occurrence of that reference in that file.

Files are found with ``git ls-files``, so untracked and ignored files (``.env``, ``.private``) are never opened.

Scanned: compose and workflow ``image: <ref>``, workflow ``container: <ref>`` (string form) and
``uses: docker://<ref>``; Dockerfile ``FROM [--platform=...] <ref> [AS name]`` with line continuations joined,
``FROM scratch`` and earlier stage names skipped, ``$X`` / ``${X}`` resolved from an ``ARG X=default`` declared
before the first ``FROM`` (an ARG without a default is a violation). Full-line comments and `` #`` inline comments
are ignored.

Not covered by CI's ruff and mypy, which check ``apps/api`` only (known gap; checked by hand when changed).

Known limits (not detected):
- a ``--build-arg`` given at build time can replace a pinned ARG default;
- ``COPY --from=<image>`` and ``RUN --mount=...,from=<image>`` in Dockerfiles;
- YAML flow mappings (``{image: x}``), anchors and aliases, and multi-line scalars;
- images pulled by scripts (``docker run`` / ``docker pull``) and named in documentation;
- a new file that is not yet tracked: ``git add`` it (or commit it) before running the check locally;
- model revisions (R-21's other half): model names live in the database, and live adapters need ``model_digest``
  (R-25).
An ``image:`` value that is only a variable has no literal digest, so it counts as unpinned (fails closed).

Usage: python scripts/check_image_digests.py [--root DIR] [--baseline FILE]
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "scripts" / "image-digest-baseline.txt"
FILE_PATTERNS = ("Dockerfile*", "*.dockerfile", "Containerfile*", "compose*.yml", "compose*.yaml",
                 "docker-compose*.yml", "docker-compose*.yaml")
WORKFLOW_DIR = ".github/workflows"
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
YAML_REF = re.compile(r"^\s*(?:-\s+)?(?:(image|container)\s*:\s*(.*)|uses\s*:\s*docker://(.*))$")
ARG = re.compile(r"^ARG\s+([A-Za-z_][A-Za-z0-9_]*)(?:=(\S*))?\s*$", re.I)
FROM = re.compile(r"^FROM\s+(?:--\S+\s+)*(\S+)(?:\s+AS\s+(\S+))?\s*$", re.I)
VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


@dataclass(frozen=True, order=True)
class Ref:
    path: str
    reference: str
    line: int = 0


def pinned(reference: str) -> bool:
    return DIGEST.search(reference) is not None


def is_dockerfile(path: str) -> bool:
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatch(name, p) for p in ("Dockerfile*", "*.dockerfile", "Containerfile*"))


def selected(path: str) -> bool:
    p = PurePosixPath(path)
    if str(p.parent) == WORKFLOW_DIR and p.suffix in (".yml", ".yaml"):
        return True
    return any(fnmatch.fnmatch(p.name, pattern) for pattern in FILE_PATTERNS)


def tracked_files(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True).stdout
    return sorted(f for f in out.decode("utf-8").split("\0") if f and selected(f))


def _strip_comment(value: str) -> str:
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def _unquote(value: str) -> str:
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"" else value


def yaml_refs(path: str, text: str) -> list[Ref]:
    refs = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        m = YAML_REF.match(line)
        if not m:
            continue
        value = _unquote(_strip_comment(m.group(2) if m.group(1) else m.group(3)))
        if m.group(1) == "container" and (not value or value.startswith(("{", "&", "*"))):
            continue                                     # mapping form: its image: line is scanned on its own
        if value:
            refs.append(Ref(path, value, n))
    return refs


def _logical_lines(text: str):
    """Dockerfile lines with continuations joined and comment lines dropped, numbered by their first line."""
    buf, start = "", 0
    for n, line in enumerate(text.splitlines(), 1):
        if not buf and line.lstrip().startswith("#"):
            continue
        if not buf:
            start = n
        if line.rstrip().endswith("\\"):
            buf += line.rstrip()[:-1] + " "
            continue
        yield start, (buf + line).strip()
        buf = ""
    if buf:
        yield start, buf.strip()


def dockerfile_refs(path: str, text: str) -> list[Ref]:
    args: dict[str, str | None] = {}
    stages: set[str] = set()
    stages_seen = False
    refs = []
    for n, line in _logical_lines(text):
        if m := ARG.match(line):
            if not stages_seen:                          # only ARGs before the first FROM apply to FROM lines
                args[m.group(1)] = m.group(2)
            continue
        m = FROM.match(line)
        if not m:
            continue
        stages_seen = True
        raw, alias = m.group(1), m.group(2)
        unresolved = False

        def sub(v: re.Match) -> str:
            nonlocal unresolved
            value = args.get(v.group(1) or v.group(2))
            if not value:
                unresolved = True
                return v.group(0)
            return value
        ref = VAR.sub(sub, raw)
        if alias:
            stages.add(alias.lower())
        if not unresolved and (ref.lower() == "scratch" or ref.lower() in stages - {(alias or "").lower()}):
            continue
        refs.append(Ref(path, raw if unresolved else ref, n))
    return refs


def scan(root: Path, files: list[str]) -> list[Ref]:
    refs = []
    for f in files:
        text = (root / f).read_text(encoding="utf-8")
        refs += dockerfile_refs(f, text) if is_dockerfile(f) else yaml_refs(f, text)
    return refs


def read_baseline(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    entries: list[tuple[str, str]] = []
    problems: list[str] = []
    if not path.is_file():
        return entries, problems
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2 or not parts[1].strip():
            problems.append(f"{path.name}:{n}: expected '<path> <reference>'")
            continue
        entries.append((parts[0], parts[1].strip()))
    if entries != sorted(entries):
        problems.append(f"{path.name}: entries are not sorted")
    if len(set(entries)) != len(entries):
        problems.append(f"{path.name}: duplicate entries")
    return entries, problems


def check(root: Path, files: list[str], baseline: Path) -> tuple[list[str], list[Ref], set[tuple[str, str]]]:
    """Returns (problems, references scanned, baseline entries in use)."""
    refs = scan(root, files)
    entries, problems = read_baseline(baseline)
    allowed = set(entries)
    unpinned = {(r.path, r.reference) for r in refs if not pinned(r.reference)}
    for r in sorted(refs):
        if not pinned(r.reference) and (r.path, r.reference) not in allowed:
            problems.append(f"{r.path}:{r.line}: image reference without @sha256 digest: {r.reference}")
    for path, ref in sorted(allowed - unpinned):
        problems.append(f"{baseline.name}: stale entry, remove it: {path} {ref}")
    return problems, refs, allowed & unpinned


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    a = ap.parse_args(argv)
    files = tracked_files(a.root)
    problems, refs, used = check(a.root, files, a.baseline)
    for p in problems:
        print(p)
    print(f"image digest check: {len(refs)} scanned in {len(files)} files, {len(used)} baselined, "
          f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
