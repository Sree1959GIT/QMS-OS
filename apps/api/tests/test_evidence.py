"""The interim original-evidence store (MVP-1 slice 5; R-34, R-50 to R-54). Synthetic fixtures only.

The store's folder must be outside every Git work tree. On a workstation pytest's temporary folders may sit inside
the repository (scripts/env.bat points TEMP at .tmp unless QMS_TEMP_ROOT is set), so the ``store_root`` fixture
disables that one check there, and only there; ``test_store_inside_a_git_work_tree_is_refused`` checks it with a
folder that is inside a work tree everywhere, and in CI (Linux, /tmp) the fixture runs the check unpatched.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

import pytest
from conftest import _As
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from qms_os.auth.keys import git_work_tree_of
from qms_os.auth.testing import TestIdentityProvider
from qms_os.db import make_engine, make_sessionmaker
from qms_os.evidence import local as L
from qms_os.evidence import service as EV
from qms_os.evidence.__main__ import main as evidence_cli
from qms_os.evidence.contract import MAX_BYTES, EvidenceStore, ObjectMissing, StoreRefused
from qms_os.fixtures import load
from qms_os.main import _evidence_store, create_app
from qms_os.models import AgentProfile, AuditEvent, EvidenceObject, User
from qms_os.policy import Mode
from qms_os.services import access as ACC
from qms_os.services.common import RuleViolation

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PDF = b"%PDF-1.7\n% synthetic fixture\n"


@pytest.fixture
def store_root(tmp_path, monkeypatch) -> Path:
    if git_work_tree_of(tmp_path) is not None:            # workstation only; see the module docstring
        monkeypatch.setattr(L, "git_work_tree_of", lambda _p: None)
    return L.init_store(tmp_path / "store", "test")


@pytest.fixture
def store(store_root) -> L.LocalContentStore:
    return L.LocalContentStore(store_root, qms_mode="test")


@pytest.fixture
def ev(engine, clock, store):
    app = create_app(engine=engine, today=clock, mode="test", identity_provider=TestIdentityProvider(),
                     evidence_store=store)
    client = TestClient(app)
    with make_sessionmaker(engine)() as s:
        ids = {u.email.split("@")[0]: u.id for u in s.scalars(select(User))}

    class Ev:
        users = ids

        def as_(self, who):
            return _As(client, {TestIdentityProvider.header: str(ids[who])})

        def put(self, data: bytes, mime="text/plain", owner="ma", classification="internal"):
            with make_sessionmaker(engine)() as s:
                row, created = EV.store_object(s, store, data=data, mime=mime, owner_id=ids[owner],
                                               classification=classification, synthetic=True)
                s.commit()
                return row.sha256, created
    return Ev()


def _events(engine, prefix):
    with make_sessionmaker(engine)() as s:
        return list(s.scalars(select(AuditEvent).where(AuditEvent.action.like(f"{prefix}%")).order_by(AuditEvent.id)))


# ---------- identity, idempotence, no overwrite ----------

def test_object_is_named_by_its_sha256_and_storing_it_again_writes_nothing(ev, engine, store):
    data = b"Synthetic audit evidence (fixture).\n"
    sha, created = ev.put(data)
    assert created and sha == hashlib.sha256(data).hexdigest()
    path = store.path_of(sha)
    assert path == store.root / "sha256" / sha[:2] / sha and path.read_bytes() == data
    assert not os.access(path, os.W_OK)                                   # published files are read-only
    before = path.stat().st_mtime_ns
    assert ev.put(data) == (sha, False)
    assert path.stat().st_mtime_ns == before and list(store.iter_hashes()) == [sha]
    with make_sessionmaker(engine)() as s:
        assert s.scalar(select(EvidenceObject).where(EvidenceObject.sha256 == sha)).size == len(data)
    assert [e.action for e in _events(engine, "evidence.")] == ["evidence.stored", "evidence.duplicate"]
    assert _events(engine, "evidence.stored")[0].detail == {"sha256": sha, "size": len(data), "mime": "text/plain",
                                                            "classification": "internal", "owner_id": ev.users["ma"]}


def test_same_bytes_with_other_metadata_are_refused_and_nothing_changes(ev, engine):
    sha, _ = ev.put(b"fixture")
    with pytest.raises(EV.Conflict):
        ev.put(b"fixture", classification="public")
    with pytest.raises(EV.Conflict):
        ev.put(b"fixture", owner="md")
    with make_sessionmaker(engine)() as s:
        row = s.get(EvidenceObject, sha)
        assert (row.classification, row.owner_id) == ("internal", ev.users["ma"])


def test_no_interface_route_or_method_overwrites_or_deletes(ev, engine):
    assert {m for m in dir(L.LocalContentStore) if not m.startswith("_")} == {
        "integration_mode", "path_of", "put", "read", "verify", "iter_hashes", "stray_files"}
    assert {m for m in vars(EvidenceStore) if not m.startswith("_")} == {"put", "read", "verify", "iter_hashes"}
    assert set(EvidenceStore.__annotations__) == {"integration_mode"}
    from test_org_admin import _routes
    routes = {(m, r.path) for r in _routes(engine) if r.path.startswith("/api/v1/evidence") for m in r.methods}
    assert routes == {("GET", "/api/v1/evidence/{sha256}"), ("GET", "/api/v1/evidence/{sha256}/content")}


def test_database_refuses_update_and_delete_of_evidence_rows(ev, engine):
    sha, _ = ev.put(b"fixture")
    for stmt in ("UPDATE evidence_objects SET classification = 'public'", "DELETE FROM evidence_objects"):
        with engine.connect() as c, pytest.raises(DBAPIError, match="immutable"):
            c.execute(text(stmt))
            c.commit()
    with make_sessionmaker(engine)() as s:
        assert s.get(EvidenceObject, sha).classification == "internal"


@pytest.mark.parametrize("column, value", [("synthetic", False), ("sha256", "A" * 64), ("sha256", "g" * 64),
                                           ("sha256", "a" * 63), ("mime", "text/html"), ("size", MAX_BYTES + 1),
                                           ("classification", "secret")])
def test_database_checks_refuse_non_synthetic_or_malformed_rows(ev, engine, column, value):
    row = {"sha256": "a" * 64, "size": 1, "mime": "text/plain", "owner_id": ev.users["ma"],
           "classification": "internal", "synthetic": True} | {column: value}
    with make_sessionmaker(engine)() as s:
        s.add(EvidenceObject(**row))
        with pytest.raises(IntegrityError):
            s.commit()


# ---------- what may be stored (R-50, R-54) ----------

@pytest.mark.parametrize("data, mime", [
    (b"x", "text/html"), (b"x", "application/octet-stream"), (b"not a pdf", "application/pdf"),
    (PDF, "image/png"), (b"\xff\xfe bad utf-8", "text/plain"), (b"a\x00b", "text/markdown"),
    (b"{not json", "application/json"), (b"x" * (MAX_BYTES + 1), "text/plain"),
], ids=["html", "octet-stream", "pdf-without-magic", "pdf-as-png", "bad-utf8", "nul", "bad-json", "too-large"])
def test_content_that_does_not_match_its_type_or_limits_is_refused(ev, store, data, mime):
    with pytest.raises(RuleViolation):
        ev.put(data, mime=mime)
    assert list(store.iter_hashes()) == []


@pytest.mark.parametrize("data, mime", [(PNG, "image/png"), (PDF, "application/pdf"),
                                        (json.dumps({"a": 1}).encode(), "application/json"),
                                        ("# Überschrift (fixture)\n".encode(), "text/markdown")])
def test_allowed_types_are_stored(ev, data, mime):
    assert ev.put(data, mime=mime)[1] is True


def test_non_synthetic_content_is_refused(engine, store):
    with make_sessionmaker(engine)() as s, pytest.raises(StoreRefused, match="synthetic"):
        EV.store_object(s, store, data=b"x", mime="text/plain", owner_id=1, classification="internal",
                        synthetic=False)
    assert list(store.iter_hashes()) == []


def test_store_refuses_operational_mode_relative_missing_and_unmarked_folders(store_root, tmp_path):
    with pytest.raises(StoreRefused, match="operational"):
        L.LocalContentStore(store_root, qms_mode="operational")
    with pytest.raises(StoreRefused, match="operational"):
        L.init_store(tmp_path / "other", "operational")
    with pytest.raises(StoreRefused, match="absolute"):
        L.LocalContentStore("relative/store", qms_mode="test")
    with pytest.raises(StoreRefused, match="not a folder"):
        L.LocalContentStore(tmp_path / "missing", qms_mode="test")
    (tmp_path / "bare").mkdir()
    with pytest.raises(StoreRefused, match=L.MARKER):
        L.LocalContentStore(tmp_path / "bare", qms_mode="test")
    with pytest.raises(FileExistsError):
        L.init_store(store_root, "test")                  # an existing store is never re-initialised


def test_store_inside_a_git_work_tree_is_refused(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    with pytest.raises(StoreRefused, match="Git work tree"):
        L.init_store(repo / "store", "test")
    (repo / "store").mkdir()
    (repo / "store" / L.MARKER).write_text("x", encoding="utf-8")
    with pytest.raises(StoreRefused, match="Git work tree"):
        L.LocalContentStore(repo / "store", qms_mode="test")


def test_app_opens_the_store_from_the_environment_and_refuses_it_in_operational_mode(store_root):
    env = {L.EVIDENCE_ENV: str(store_root)}
    assert isinstance(_evidence_store(Mode.TEST, env, None), L.LocalContentStore)
    assert _evidence_store(Mode.TEST, {}, None) is None
    with pytest.raises(StoreRefused, match="operational"):
        _evidence_store(Mode.OPERATIONAL, env, None)


# ---------- publishing never replaces (Windows: rename; Linux: link) ----------

def test_the_native_publish_path_is_rename_on_windows_and_link_elsewhere():
    assert L.PUBLISH_PATH == ("rename" if os.name == "nt" else "link")
    assert L._publish is (L._publish_rename if os.name == "nt" else L._publish_link)


def _never_replaces(publish, tmp_path):
    final, tmp = tmp_path / "final", tmp_path / "tmp.part"
    final.write_bytes(b"first")
    tmp.write_bytes(b"second")
    with pytest.raises(FileExistsError):
        publish(tmp, final)
    assert final.read_bytes() == b"first"


def test_link_publish_never_replaces(tmp_path):
    """The Linux path; runs on Windows too (NTFS hard links)."""
    _never_replaces(L._publish_link, tmp_path)


@pytest.mark.skipif(os.name != "nt", reason="os.rename replaces an existing file on POSIX; this path is Windows-only")
def test_rename_publish_never_replaces_on_windows(tmp_path):
    _never_replaces(L._publish_rename, tmp_path)


def test_a_writer_that_loses_the_race_reports_a_duplicate(store, monkeypatch):
    data = b"raced fixture"
    real = L._publish

    def publish_after_the_other_writer(tmp, final):
        real(tmp, final)                                   # the other writer publishes first ...
        raise FileExistsError(final)                       # ... so this writer's publish finds the file there
    monkeypatch.setattr(L, "_publish", publish_after_the_other_writer)
    sha = hashlib.sha256(data).hexdigest()
    assert store.put(data) == (sha, False)
    assert list((store.root / "tmp").iterdir()) == []      # the temporary file is removed


# ---------- reads go through the grant decision; a denied read leaks nothing ----------

def test_a_granted_read_returns_the_bytes(ev):
    sha, _ = ev.put(PDF, mime="application/pdf")
    r = ev.as_("md").get(f"/api/v1/evidence/{sha}/content")
    assert r.status_code == 200 and r.content == PDF and r.headers["content-type"] == "application/pdf"
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store"
    meta = ev.as_("md").get(f"/api/v1/evidence/{sha}").json()
    assert meta["sha256"] == sha and meta["size"] == len(PDF) and meta["synthetic"] is True


def test_denied_unknown_and_malformed_reads_are_the_same_404(ev):
    sha, _ = ev.put(b"confidential fixture", classification="confidential")
    c = ev.as_("ma")                                       # the owner: no bypass (R-51)
    answers = []
    for h in (sha, "0" * 64, "A" * 64, "abc", "...", "0" * 65):
        for suffix in ("", "/content"):
            r = c.get(f"/api/v1/evidence/{h}{suffix}")
            answers.append((r.status_code, r.content))
    assert set(answers) == {(404, b'{"detail":"evidence not found"}')}
    # an encoded path separator never reaches the evidence routes (the router answers 404 itself)
    assert c.get(f"/api/v1/evidence/..%2F..%2F{sha}/content").status_code == 404


def test_agent_and_preview_include_evidence_through_the_same_decision(ev, engine):
    internal, _ = ev.put(b"internal fixture")
    public, _ = ev.put(b"public fixture", classification="public")
    secret, _ = ev.put(b"confidential fixture", classification="confidential")
    with make_sessionmaker(engine)() as s:
        ma = s.get(User, ev.users["ma"])
        p = ACC.preview(s, ma)
        assert sorted(p["readable"]["evidence"]) == sorted([internal, public]) and p["denied"]["evidence"] == [secret]
        a = AgentProfile(label="x", person_id=ma.id, max_classification="public", enrolled_by_id=ev.users["md"])
        s.add(a)
        s.flush()
        assert ACC.agent_preview(s, a)["readable"]["evidence"] == [public]


def test_no_evidence_is_served_when_no_store_is_configured(api):
    assert api.as_("md").get(f"/api/v1/evidence/{'0' * 64}/content").status_code == 404
    assert api.as_("md").get(f"/api/v1/evidence/{'0' * 64}").status_code == 404


# ---------- a tampered or missing object is never served (R-53) ----------

@pytest.mark.parametrize("damage", ["tamper", "remove"])
def test_a_tampered_or_missing_object_is_detected_audited_and_not_served(ev, engine, store, damage):
    original = b"Original fixture evidence.\n"
    sha, _ = ev.put(original)
    path = store.path_of(sha)
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    if damage == "tamper":
        path.write_bytes(b"Altered fixture evidence.\n")
    else:
        path.unlink()
    r = ev.as_("md").get(f"/api/v1/evidence/{sha}/content")
    assert r.status_code == 500 and b"Altered" not in r.content and b"Original" not in r.content
    assert "integrity failure" in r.json()["detail"]
    (event,) = _events(engine, "evidence.integrity_failed")
    assert event.detail == {"sha256": sha} and event.actor_id == ev.users["md"]
    assert not store.verify(sha)
    with pytest.raises(Exception, match=sha):
        store.read(sha)


def test_paths_come_only_from_a_valid_hash(store):
    for bad in ("../" + "a" * 61, "a" * 63, "A" * 64, "a" * 64 + "/x", ""):
        with pytest.raises(ObjectMissing):
            store.path_of(bad)


# ---------- the operator CLI (synthetic only) ----------

def test_cli_stores_a_synthetic_file_audited_and_refuses_without_the_flag_or_in_operational_mode(store_root, tmp_path,
                                                                                                 capsys):
    db = tmp_path / "cli.db"
    eng = make_engine(f"sqlite:///{db.as_posix()}")
    from qms_os.db import create_all
    create_all(eng)
    with make_sessionmaker(eng)() as s:
        load(s)
        s.commit()
    owner = next(u.email for u in make_sessionmaker(eng)().scalars(select(User)) if u.email.startswith("ma@"))
    f = tmp_path / "fixture.md"
    f.write_bytes(b"# Synthetic fixture\n")
    env = {"QMS_MODE": "test", "QMS_DATABASE_URL": f"sqlite:///{db.as_posix()}", L.EVIDENCE_ENV: str(store_root)}
    args = ["put", str(f), "--mime", "text/markdown", "--owner-email", owner, "--classification", "internal"]
    assert evidence_cli(args, env) == 2 and "--synthetic is required" in capsys.readouterr().err
    assert evidence_cli([*args, "--synthetic"], env | {"QMS_MODE": "operational"}) == 2
    assert evidence_cli([*args, "--synthetic"], {k: v for k, v in env.items() if k != L.EVIDENCE_ENV}) == 2
    assert evidence_cli([*args, "--synthetic"], env) == 0
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    assert f"stored {sha}" in capsys.readouterr().out
    with make_sessionmaker(eng)() as s:
        (e,) = s.scalars(select(AuditEvent).where(AuditEvent.action == "evidence.stored"))
        assert (e.actor_id, e.actor_kind, e.channel, e.detail["sha256"]) == (None, "operator", "cli", sha)
    eng.dispose()


def test_tests_never_take_runtime_settings_from_the_terminal(api):
    """conftest.SEALED_ENV: a terminal set up for a super admin skill run must not change a test run."""
    from conftest import SEALED_ENV
    assert not [k for k in SEALED_ENV if k in os.environ]
    assert api.as_("md").get(f"/api/v1/evidence/{'0' * 64}").status_code == 404     # the app started, no store
