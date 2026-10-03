"""The knowledge module is independent, governed, and has no link to the reference vault."""
import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "qms_os"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            out.add(("." * node.level) + (node.module or ""))
    return out


def test_knowledge_module_imports_nothing_from_the_domain():
    for f in (PKG / "knowledge").glob("*.py"):
        for mod in _imports(f):
            assert not mod.startswith("..") and not mod.startswith("qms_os"), f"{f.name} imports {mod}"


def test_domain_does_not_import_knowledge_module():
    for f in list((PKG / "rules").glob("*.py")) + list((PKG / "services").glob("*.py")) + [PKG / "models.py"]:
        assert not any("knowledge" in m for m in _imports(f)), f.name


def test_no_runtime_dependency_on_reference_repository():
    forbidden = ("github.com", "git clone", "subprocess", "urllib", "requests", "httpx")
    for f in PKG.rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        for word in forbidden:
            assert word not in text, f"{f.relative_to(PKG)} contains '{word}'"


def test_governance_flow(api):
    ma, auditee, viewer = api.as_("ma"), api.as_("qa_head"), api.as_("viewer")
    src = ma.post("/api/knowledge/sources", {"name": "Synthetic controlled documents", "kind": "controlled-document"}).json()
    assert auditee.post("/api/knowledge/sources", {"name": "x"}).status_code == 403
    assert auditee.post("/api/knowledge/items", {"source_id": src["id"], "title": "t", "body": "b",
                                                 "origin": " "}).status_code == 422
    v1 = auditee.post("/api/knowledge/items", {
        "source_id": src["id"], "doc_number": "SYN/PROC/DOC", "doc_type": "PROC", "title": "Document control",
        "body": "Documents are reviewed on a defined schedule.", "origin": "authored in QMS OS", "version": "1.0"}).json()
    assert v1["status"] == "candidate"
    assert viewer.get("/api/knowledge/items?q=Document").json() == []          # candidates are not citable
    assert viewer.get("/api/knowledge/items?include_unapproved=true").status_code == 403
    assert ma.post(f"/api/knowledge/items/{v1['id']}/decide", {"approve": True}).json()["status"] == "approved"
    assert [i["id"] for i in viewer.get("/api/knowledge/items?q=Document").json()] == [v1["id"]]

    v2 = auditee.post("/api/knowledge/items", {
        "source_id": src["id"], "doc_number": "SYN/PROC/DOC", "doc_type": "PROC", "title": "Document control",
        "body": "Documents are reviewed on a revised schedule.", "origin": "change request CR-7", "version": "2.0",
        "supersedes_id": v1["id"]}).json()
    ma.post(f"/api/knowledge/items/{v2['id']}/decide", {"approve": True})
    rows = {i["id"]: i["status"] for i in ma.get("/api/knowledge/items?include_unapproved=true").json()}
    assert rows == {v1["id"]: "obsolete", v2["id"]: "approved"}


def test_capturer_cannot_self_approve(api):
    ma = api.as_("ma")
    src = ma.post("/api/knowledge/sources", {"name": "S"}).json()
    item = ma.post("/api/knowledge/items", {"source_id": src["id"], "title": "t", "body": "b", "origin": "o"}).json()
    r = ma.post(f"/api/knowledge/items/{item['id']}/decide", {"approve": True})
    assert r.status_code == 422 and "differ" in r.json()["detail"]
