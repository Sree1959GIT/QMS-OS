"""The read-only scripts behind the super admin skills (R-38, R-46; ``qms_superadmin``, ``.claude/skills/``)."""
from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from qms_os.db import create_all, make_engine, make_sessionmaker
from qms_os.fixtures import load
from qms_superadmin import access_segregation, housekeeping, review_org
from qms_superadmin.readonly import Refused, read_only_session

API = Path(__file__).resolve().parents[1]
REPO = API.parents[1]
PKG = API / "qms_superadmin"
SKILLS = REPO / ".claude" / "skills"
SKILL_NAMES = ("housekeeping-check", "review-org", "access-segregation")


@pytest.fixture
def demo_db(tmp_path) -> dict[str, str]:
    db = tmp_path / "demo.db"
    eng = make_engine(f"sqlite:///{db.as_posix()}")
    create_all(eng)
    with make_sessionmaker(eng)() as s:
        load(s)
        s.commit()
    eng.dispose()
    return {"QMS_MODE": "demo", "QMS_DATABASE_URL": f"sqlite:///{db.as_posix()}"}


def test_database_reviews_are_deterministic_and_find_nothing_on_the_fixture(demo_db):
    for review in (review_org.review, access_segregation.review):
        with read_only_session(demo_db) as (s, mode):
            first = review(s)
        with read_only_session(demo_db) as (s, _):
            second = review(s)
        assert mode == "demo" and first == second and "findings: 0" in first


def test_review_org_reports_a_department_without_a_head(demo_db):
    eng = make_engine(demo_db["QMS_DATABASE_URL"])
    with eng.begin() as c:
        c.execute(text("UPDATE departments SET head_user_id = NULL WHERE code = 'qa'"))
    eng.dispose()
    with read_only_session(demo_db) as (s, _):
        report = review_org.review(s)
    assert "findings: 1" in report and any("(qa) has no head" in line for line in report)


def test_the_session_cannot_write(demo_db):
    with read_only_session(demo_db) as (s, _), pytest.raises(OperationalError, match="readonly"):
        s.execute(text("UPDATE departments SET name = 'changed'"))
        s.flush()


@pytest.mark.parametrize("env, message", [
    ({"QMS_MODE": "operational", "QMS_DATABASE_URL": "sqlite:///x.db"}, "operational mode is refused"),
    ({"QMS_MODE": "demo"}, "set QMS_DATABASE_URL"),
    ({"QMS_MODE": "demo", "QMS_DATABASE_URL": "sqlite://"}, "existing SQLite file"),
])
def test_refusals(env, message):
    with pytest.raises(Refused, match=message), read_only_session(env):
        pass


def test_housekeeping_reports_a_stale_baseline_and_names_no_writing_skill(tmp_path):
    shutil.copytree(REPO / "docs", tmp_path / "docs")
    stale = housekeeping.check(repo=tmp_path, main_hash="f" * 40, branch="some-branch")
    assert any("ROADMAP.md Current baseline" in line and "main is fffffff" in line for line in stale)
    assert all("development pull request" in line for line in stale if line.startswith("- "))
    roadmap = (tmp_path / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    current = re.search(r"prototype on `main` at `([0-9a-f]{7,40})`", roadmap).group(1)
    fresh = housekeeping.check(repo=tmp_path, main_hash=current + "0" * (40 - len(current)), branch="some-branch")
    assert not any("ROADMAP.md Current baseline" in line for line in fresh)


def _code_strings(path: Path) -> list[str]:
    """String constants in the module's code, without docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                  and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


def test_no_script_names_a_private_or_env_path():
    """The register module carries claim text as data (some claims mention ``.env``); what it reads is only the docs
    named in its FILES table, checked below. Every other module may not name such a path at all."""
    for path in sorted(PKG.glob("*.py")):
        if path.name == "claims_register.py":
            continue
        for s in _code_strings(path):
            assert ".private" not in s and ".env" not in s, f"{path.name}: {s!r}"
    tree = ast.parse((PKG / "claims_register.py").read_text(encoding="utf-8"))
    files = next(n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "FILES" for t in n.targets))
    names = [v.value for v in files.values]
    assert names and all(n.endswith(".md") and not n.startswith(".") and ".." not in n for n in names), names


def test_scripts_make_no_network_calls_and_write_no_files():
    forbidden = ("socket", "urllib", "http.client", "requests", "httpx", ".write_text(", ".write_bytes(",
                 "open(", "mkdir(")
    for path in sorted(PKG.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for word in forbidden:
            assert word not in source, f"{path.name} contains {word!r}"


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_each_skill_is_human_invoked_and_may_run_only_its_script(name):
    text_ = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    front = text_.split("---")[1]
    assert re.search(r"^name: " + re.escape(name) + r"$", front, re.M)
    assert re.search(r"^disable-model-invocation: true$", front, re.M)
    command = {"housekeeping-check": "housekeeping"}.get(name, name)
    tools = re.search(r"^allowed-tools: (.+)$", front, re.M).group(1)
    assert tools == f'Bash(cmd //c "scripts\\\\run-superadmin.bat {command}")'
    assert (REPO / "docs" / "superadmin" / f"{name}.md").is_file()
