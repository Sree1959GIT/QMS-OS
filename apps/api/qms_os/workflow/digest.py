"""Canonical serialisation and digest of a workflow template version (R-32, R-59).

The digest is the SHA-256 (lower-case hex) of the UTF-8 bytes of::

    json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

where ``content`` is ``{"schema": SCHEMA, "guideline_id", "template_id", "version_no", "title", "graph"}``, the
graph's nodes are sorted by id and its edges by (from, to, condition), every string is NFC-normalised, and floats are
refused (integers only). The same content therefore always gives the same digest, whatever the key order or Unicode
normal form it arrived in; any change to the title, the graph or the version's identity gives another digest.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata

SCHEMA = "qms-os/workflow-version/1"


def _normalise(v):
    if isinstance(v, str):
        return unicodedata.normalize("NFC", v)
    if isinstance(v, bool) or v is None or isinstance(v, int):
        return v
    if isinstance(v, float):
        raise ValueError("floats are not allowed in a workflow version (the digest must be stable)")
    if isinstance(v, list):
        return [_normalise(x) for x in v]
    if isinstance(v, dict):
        return {_normalise(k): _normalise(x) for k, x in v.items()}
    raise ValueError(f"unsupported value type {type(v).__name__}")


def canonical_graph(graph: dict) -> dict:
    g = _normalise(graph)
    g["nodes"] = sorted(g["nodes"], key=lambda n: n["id"])
    g["edges"] = sorted(g["edges"], key=lambda e: (e["from"], e["to"], e.get("condition", "")))
    return g


def dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def graph_text(graph: dict) -> str:
    """The canonical JSON stored in ``workflow_template_versions.graph_json``."""
    return dumps(canonical_graph(graph))


def version_digest(*, guideline_id: int, template_id: int, version_no: int, title: str, graph: dict) -> str:
    content = {"schema": SCHEMA, "guideline_id": guideline_id, "template_id": template_id, "version_no": version_no,
               "title": _normalise(title), "graph": canonical_graph(graph)}
    return hashlib.sha256(dumps(content).encode("utf-8")).hexdigest()
