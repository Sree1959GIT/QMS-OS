"""CI image-digest check, scripts/check_image_digests.py (R-21; ROADMAP slice 3a). Synthetic files in tmp_path, plus one
run against this repository's tracked files."""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("check_image_digests", REPO / "scripts" / "check_image_digests.py")
CID = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = CID            # dataclasses look the module up
_spec.loader.exec_module(CID)

D1 = "@sha256:" + "a" * 64
D2 = "@sha256:" + "0123456789abcdef" * 4


def run(tmp_path: Path, files: dict[str, str], baseline: str = "") -> list[str]:
    for name, text in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    (tmp_path / "baseline.txt").write_text(baseline, encoding="utf-8")
    problems, _, _ = CID.check(tmp_path, sorted(files), tmp_path / "baseline.txt")
    return problems


def refs(tmp_path: Path, name: str, text: str) -> list[str]:
    (tmp_path / name).write_text(text, encoding="utf-8")
    return [r.reference for r in CID.scan(tmp_path, [name])]


# ---------- pinned, unpinned and the baseline ----------

def test_new_unpinned_image_fails(tmp_path):
    assert run(tmp_path, {"compose.yaml": "services:\n  db:\n    image: postgres:17\n"}) == [
        "compose.yaml:3: image reference without @sha256 digest: postgres:17"]


@pytest.mark.parametrize("ref", [f"postgres{D1}", f"postgres:17.11{D2}", f"ghcr.io/org/app:1.2{D1}"])
def test_pinned_image_passes_including_tag_and_digest(tmp_path, ref):
    assert run(tmp_path, {"compose.yaml": f"services:\n  db:\n    image: {ref}\n"}) == []


@pytest.mark.parametrize("ref", ["postgres@sha256:abc", "postgres@sha256:" + "A" * 64,
                                 "postgres@sha256:${DIGEST}", "postgres:17@sha256", "${IMAGE}"])
def test_malformed_or_variable_digest_fails(tmp_path, ref):
    assert len(run(tmp_path, {"compose.yaml": f"services:\n  db:\n    image: {ref}\n"})) == 1


def test_baseline_entry_passes(tmp_path):
    assert run(tmp_path, {"compose.yaml": "services:\n  db:\n    image: postgres:${TAG:-17}\n"},
               "# comment\ncompose.yaml postgres:${TAG:-17}\n") == []


def test_baseline_entry_is_per_file(tmp_path):
    files = {"compose.yaml": "services:\n  db:\n    image: postgres:17\n",
             "compose.dev.yaml": "services:\n  db:\n    image: postgres:17\n"}
    assert run(tmp_path, files, "compose.yaml postgres:17\n") == [
        "compose.dev.yaml:3: image reference without @sha256 digest: postgres:17"]


def test_stale_baseline_entry_fails(tmp_path):
    assert run(tmp_path, {"compose.yaml": f"services:\n  db:\n    image: postgres:17{D1}\n"},
               "compose.yaml postgres:17\n") == ["baseline.txt: stale entry, remove it: compose.yaml postgres:17"]


def test_unsorted_duplicate_or_malformed_baseline_fails(tmp_path):
    files = {"compose.yaml": "services:\n  a:\n    image: a:1\n  b:\n    image: b:1\n"}
    assert run(tmp_path, files, "compose.yaml b:1\ncompose.yaml a:1\n") == ["baseline.txt: entries are not sorted"]
    assert "baseline.txt: duplicate entries" in run(tmp_path, files, "compose.yaml a:1\ncompose.yaml a:1\n"
                                                                     "compose.yaml b:1\n")
    assert "baseline.txt:1: expected '<path> <reference>'" in run(tmp_path, files, "compose.yaml\n")


# ---------- YAML forms and comments ----------

def test_workflow_service_container_and_docker_action_are_scanned(tmp_path):
    wf = ("jobs:\n  a:\n    container: node:20\n    services:\n      db:\n        image: 'postgres:17'\n"
          "  b:\n    container:\n      image: \"redis:7\"\n    steps:\n      - uses: docker://alpine:3.20\n"
          f"      - uses: docker://alpine{D1}\n      - uses: actions/checkout@{'1' * 40}\n")
    assert refs(tmp_path, "ci.yml", wf) == ["node:20", "postgres:17", "redis:7", "alpine:3.20", f"alpine{D1}"]


def test_comments_are_ignored(tmp_path):
    text = (f"services:\n  # image: commented:1\n  db:\n    image: postgres{D1}   # was postgres:17\n"
            "    #image: also-commented:2\n")
    assert refs(tmp_path, "compose.yaml", text) == [f"postgres{D1}"]


# ---------- Dockerfiles ----------

def test_dockerfile_from_platform_alias_stage_and_scratch(tmp_path):
    text = ("# FROM commented:1\nFROM --platform=$BUILDPLATFORM python:3.12 AS build\nRUN echo\n"
            "FROM build AS test\nFROM scratch\n"
            f"FROM \\\n    debian:12{D1} AS final\nCOPY --from=build /a /b\n")
    assert refs(tmp_path, "Dockerfile", text) == ["python:3.12", f"debian:12{D1}"]


def test_dockerfile_arg_defaults_are_resolved(tmp_path):
    pinned = f"ARG BASE=python:3.12{D1}\nFROM ${{BASE}}\n"
    unpinned = "ARG BASE=python:3.12\nFROM $BASE AS x\n"
    no_default = "ARG BASE\nFROM ${BASE}\n"
    after_from = f"FROM python:3.12{D1}\nARG LATER=python:3.12{D1}\nFROM ${{LATER}}\n"
    assert run(tmp_path, {"Dockerfile": pinned}) == []
    assert run(tmp_path, {"Dockerfile": unpinned}) == [
        "Dockerfile:2: image reference without @sha256 digest: python:3.12"]
    assert run(tmp_path, {"Dockerfile": no_default}) == [
        "Dockerfile:2: image reference without @sha256 digest: ${BASE}"]
    assert run(tmp_path, {"Dockerfile": after_from}) == [
        "Dockerfile:3: image reference without @sha256 digest: ${LATER}"]


def test_known_limits_are_not_detected(tmp_path):
    """Documented limits in the script's docstring: COPY --from and RUN --mount from= image references."""
    text = (f"FROM python:3.12{D1}\nCOPY --from=nginx:1 /a /b\n"
            "RUN --mount=type=cache,from=alpine:3,target=/x true\n")
    assert refs(tmp_path, "Dockerfile", text) == [f"python:3.12{D1}"]


@pytest.mark.parametrize("path,chosen", [
    ("compose.yaml", True), ("docker-compose.override.yml", True), ("Dockerfile", True), ("api.dockerfile", True),
    ("apps/api/Dockerfile.dev", True), ("Containerfile", True), (".github/workflows/ci.yml", True),
    (".github/dependabot.yml", False), ("docs/UPSTREAMS.md", False), ("apps/api/pyproject.toml", False),
])
def test_file_selection(path, chosen):
    assert CID.selected(path) is chosen


# ---------- this repository ----------

@pytest.mark.skipif(shutil.which("git") is None or not (REPO / ".git").exists(), reason="needs a git checkout")
def test_this_repository_passes_with_exactly_the_compose_baseline(capsys):
    files = CID.tracked_files(REPO)
    problems, scanned, used = CID.check(REPO, files, CID.BASELINE)
    assert problems == []
    found = {(r.path, r.reference) for r in scanned}
    assert ("compose.yaml", "postgres:${POSTGRES_TAG:-17}") in found
    assert (".github/workflows/ci.yml",
            "postgres:17.11@sha256:d74eeac9a635390a49bc21bd49fccd973de707e2a53a76ac49b552b8712ec46f") in found
    entries, baseline_problems = CID.read_baseline(CID.BASELINE)
    assert baseline_problems == [] and entries == [("compose.yaml", "postgres:${POSTGRES_TAG:-17}")]
    assert used == set(entries)
    assert CID.main([]) == 0
    out = capsys.readouterr().out
    assert f"{len(scanned)} scanned in {len(files)} files, 1 baselined, 0 problems" in out and len(scanned) >= 2
