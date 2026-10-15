"""The read-only scripts behind the super admin skills (R-38, R-46; ``qms_superadmin``, ``.claude/skills/``)."""
from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from qms_os.db import create_all, make_engine, make_sessionmaker
from qms_os.fixtures import load
from qms_os.models import AgentProfile, User
from qms_superadmin import (
    access_segregation,
    housekeeping,
    knowledge_integrity,
    review_org,
    workflow_completeness,
)
from qms_superadmin.readonly import Refused, read_only_session

API = Path(__file__).resolve().parents[1]
REPO = API.parents[1]
PKG = API / "qms_superadmin"
SKILLS = REPO / ".claude" / "skills"
SKILL_NAMES = ("housekeeping-check", "review-org", "access-segregation", "knowledge-integrity",
               "inspect-workflow-completeness")


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
    for review in (review_org.review, access_segregation.review, workflow_completeness.review):
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
def test_each_skill_is_human_invoked_preapproves_only_its_script_and_removes_write_tools(name):
    """``allowed-tools`` is not relied on as a restriction (documented as pre-approval only); ``disallowed-tools``
    removes the file-writing tools.
    The boundary is the read-only script (R-46), the SKILL.md rules and the permission settings (R-38 note)."""
    text_ = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    front = text_.split("---")[1]
    assert re.search(r"^name: " + re.escape(name) + r"$", front, re.M)
    assert re.search(r"^disable-model-invocation: true$", front, re.M)
    command = {"housekeeping-check": "housekeeping"}.get(name, name)
    tools = re.search(r"^allowed-tools: (.+)$", front, re.M).group(1)
    assert tools == f'Bash(cmd //c "scripts\\\\run-superadmin.bat {command}")'
    removed = re.search(r"^disallowed-tools: (.+)$", front, re.M).group(1)
    assert [t.strip() for t in removed.split(",")] == ["Write", "Edit", "NotebookEdit"]
    assert "not relied on as a restriction" in text_        # the body states the limit of allowed-tools
    assert (REPO / "docs" / "superadmin" / f"{name}.md").is_file()


def test_agents_are_reviewed_and_an_agent_of_an_inactive_person_is_reported(demo_db):
    """review-org counts agents; access-segregation previews each agent through services/access.py (R-48, D11)."""
    eng = make_engine(demo_db["QMS_DATABASE_URL"])
    with make_sessionmaker(eng)() as s:
        people = {u.email.split("@")[0]: u.id for u in s.scalars(select(User))}
        s.add_all([AgentProfile(label="a", person_id=people["ma"], max_classification="internal",
                                enrolled_by_id=people["viewer"]),
                   AgentProfile(label="b", person_id=people["eng_pm"], max_classification="public",
                                enrolled_by_id=people["viewer"])])
        s.get(User, people["eng_pm"]).active = False
        s.commit()
    eng.dispose()
    with read_only_session(demo_db) as (s, _):
        org, seg = review_org.review(s), access_segregation.review(s)
    assert any(line.startswith("agents: 2 active, 0 revoked") for line in org)
    assert "findings: 1" in org and any("agent 2 is enrolled for inactive person" in line for line in org)
    assert any(line.startswith(f"- agent 1 for person {people['ma']}, ceiling internal: department ") for line in seg)
    assert "findings: 1" in seg and any("/api/v1/org/agents/2/revoke" in line for line in seg)
    assert not any("reads more than" in line for line in seg)


def test_knowledge_integrity_finds_nothing_on_a_sound_store_and_reports_damage(demo_db, tmp_path, monkeypatch):
    """R-34, R-50 to R-54: hashes, synthetic marking, orphans and unreadable objects; refusals give exit code 2."""
    import stat as st

    from qms_os.auth.keys import git_work_tree_of
    from qms_os.evidence import local as L
    from qms_os.evidence.service import store_object

    if git_work_tree_of(tmp_path) is not None:             # workstation only (see tests/test_evidence.py)
        monkeypatch.setattr(L, "git_work_tree_of", lambda _p: None)
    root = L.init_store(tmp_path / "store", "test")
    store = L.LocalContentStore(root, qms_mode="test")
    eng = make_engine(demo_db["QMS_DATABASE_URL"])
    with make_sessionmaker(eng)() as s:
        owner = s.scalar(select(User.id).limit(1))
        good, _ = store_object(s, store, data=b"sound fixture", mime="text/plain", owner_id=owner,
                               classification="internal", synthetic=True)
        bad, _ = store_object(s, store, data=b"fixture to damage", mime="text/plain", owner_id=owner,
                              classification="confidential", synthetic=True)
        good_sha, bad_sha = good.sha256, bad.sha256
        s.commit()
    eng.dispose()
    with pytest.raises(Refused, match="QMS_EVIDENCE_DIR"):
        knowledge_integrity.open_store("demo", {})
    with pytest.raises(Refused, match="operational"):
        knowledge_integrity.open_store("operational", {L.EVIDENCE_ENV: str(root)})
    env = {L.EVIDENCE_ENV: str(root)}
    with read_only_session(demo_db) as (s, mode):
        first = knowledge_integrity.review(s, knowledge_integrity.open_store(mode, env))
    assert "objects in the database: 2; files in the store: 2" in first
    assert [line for line in first if line.startswith("- ")] == [
        f"- object {bad_sha} is classified confidential, above every evidence grant, so no role can read it -> "
        "confirm, or propose an evidence grant"]
    path = store.path_of(bad_sha)
    path.chmod(st.S_IREAD | st.S_IWRITE)
    path.write_bytes(b"damaged")
    store.put(b"orphan fixture")                           # a file without a database row
    with read_only_session(demo_db) as (s, mode):
        report = knowledge_integrity.review(s, knowledge_integrity.open_store(mode, env))
    assert "findings: 3" in report
    assert any(f"object {bad_sha} no longer matches its SHA-256" in line for line in report)
    assert any("has no database row (orphan" in line for line in report)
    assert not any(good_sha in line for line in report)
    assert store.path_of(bad_sha).read_bytes() == b"damaged"      # nothing was repaired or removed


def test_inspect_workflow_completeness_checks_digests_completeness_findings_and_cases(demo_db):
    """R-56 to R-62: a sound baselined version passes. Reported: a proposed version that has become incomplete (nobody
    holds a role it uses) and whose content no longer matches its digest, a baselined version whose content no longer
    matches its approved digest, and a case pinned to a draft. A change proposed from a finding is listed as not
    published."""
    from datetime import date

    from workflow_support import GRAPH, graph

    from qms_os.models import Department, WorkflowCase, WorkflowTemplateVersion
    from qms_os.workflow import cases as C
    from qms_os.workflow import service as W

    day = date(2026, 1, 2)
    eng = make_engine(demo_db["QMS_DATABASE_URL"])
    with make_sessionmaker(eng)() as s:
        people = {u.email.split("@")[0]: s.get(User, u.id) for u in s.scalars(select(User))}
        qa = s.scalar(select(Department.id).where(Department.code == "qa"))
        author, ma = people["eng_head"], people["ma"]
        g = W.create_guideline(s, author, "Synthetic process", qa, list(GRAPH["references"]))
        t = W.create_template(s, author, g.id, "Synthetic template")
        good = W.create_version(s, author, t.id, "Synthetic template", GRAPH)
        W.submit_version(s, author, good.id)
        W.approve_version(s, ma, good.id, digest=good.digest, effective_date=day, today=day)
        case = C.start_case(s, ma, t.id, "Synthetic case", day, None, day)
        s.commit()
        good_id, case_id = good.id, case.id
    with read_only_session(demo_db) as (s, _):
        first = workflow_completeness.review(s)
    assert "findings: 0" in first and any(f"version {good_id} " in ln and "digest matches" in ln for ln in first)

    with make_sessionmaker(eng)() as s:
        incomplete = W.create_version(s, author, t.id, "Synthetic template", graph())
        W.submit_version(s, author, incomplete.id)
        s.flush()
        s.execute(text("DROP TRIGGER workflow_version_frozen"))       # a damaged database, for this test only
        s.execute(text(f"UPDATE workflow_template_versions SET graph_json = replace(graph_json, 'Do the work', "
                       f"'Do other work') WHERE id IN ({good_id}, {incomplete.id})"))
        from_finding = W.create_version(s, author, t.id, "Synthetic template", GRAPH, origin="finding", origin_ref=7)
        draft = W.create_version(s, author, t.id, "Synthetic template", GRAPH)
        s.get(WorkflowCase, case_id).version_id = draft.id
        s.execute(text("UPDATE users SET role = 'AUDITEE' WHERE role = 'MA'"))     # the approval step's role
        s.commit()
        incomplete_id = incomplete.id
        assert s.get(WorkflowTemplateVersion, from_finding.id).status == "draft"
    eng.dispose()
    with read_only_session(demo_db) as (s, _):
        report = workflow_completeness.review(s)
    assert "findings: 4" in report
    assert any(f"version {incomplete_id} " in ln and "proposed but incomplete (no_qualified_owner)" in ln
               for ln in report)
    assert any(f"version {good_id} " in ln and "digest mismatch" in ln for ln in report)
    assert any(f"version {incomplete_id} " in ln and "stored digest does not match" in ln for ln in report)
    assert any(f"case {case_id} is pinned to version {draft.id}" in ln for ln in report)
    assert any("change proposed from finding 7: awaiting review; not published" in ln for ln in report)
