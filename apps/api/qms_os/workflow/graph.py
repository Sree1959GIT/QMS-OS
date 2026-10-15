"""The shape of a workflow graph (R-58, R-59). This module checks only the structure every version must have (types,
known keys, unique node ids, edges between existing nodes, size limits); whether the workflow is complete is the
validator's job (``validator.py``, slice 7).

A value of ``"?"`` marks an unknown fact (an open question; ``docs/SPECIFICATION.md`` line 57). Floats are refused so
that the canonical serialisation, and so the digest, is stable.
"""
from __future__ import annotations

import re

from ..rules.findings import Role

UNKNOWN = "?"
NODE_TYPES = ("start", "task", "approval", "decision", "end")
DATA_CLASSES = ("public", "internal", "confidential")
ROLES = tuple(r.value for r in Role)
ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}")
MAX_NODES, MAX_EDGES, MAX_TEXT, MAX_LIST = 200, 400, 200, 20
NODE_KEYS = {"id", "type", "name", "role", "evidence", "sla_days", "sop_ref", "data_class", "notify", "approves"}
GRAPH_KEYS = {"nodes", "edges", "target_days", "references"}
EDGE_KEYS = {"from", "to", "condition"}


class GraphError(ValueError):
    """The graph does not have the required shape."""


def _text(v, where: str, *, unknown_ok: bool = False) -> str:
    if not isinstance(v, str) or not v.strip() or len(v) > MAX_TEXT:
        raise GraphError(f"{where} must be text of 1 to {MAX_TEXT} characters")
    if v == UNKNOWN and not unknown_ok:
        raise GraphError(f"{where} cannot be unknown")
    return v


def _int_or_unknown(v, where: str) -> int | str:
    if v == UNKNOWN or (isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 3650):
        return v
    raise GraphError(f"{where} must be a whole number of days from 0 to 3650, or \"?\"")


def _list(v, where: str) -> list:
    if not isinstance(v, list) or len(v) > MAX_LIST:
        raise GraphError(f"{where} must be a list of at most {MAX_LIST} items")
    return v


def check_shape(graph) -> dict:
    """Return the graph if its shape is valid; raise ``GraphError`` otherwise."""
    if not isinstance(graph, dict) or set(graph) - GRAPH_KEYS or not {"nodes", "edges"} <= set(graph):
        raise GraphError(f"the graph must be an object with nodes and edges (allowed keys: {sorted(GRAPH_KEYS)})")
    nodes, edges = graph["nodes"], graph["edges"]
    if not isinstance(nodes, list) or not isinstance(edges, list) or len(nodes) > MAX_NODES or len(edges) > MAX_EDGES:
        raise GraphError(f"nodes and edges must be lists (at most {MAX_NODES} nodes and {MAX_EDGES} edges)")
    if "target_days" in graph:
        _int_or_unknown(graph["target_days"], "target_days")
    for i, ref in enumerate(_list(graph.get("references", []), "references")):
        _text(ref, f"references[{i}]")
    ids: set[str] = set()
    for n in nodes:
        if not isinstance(n, dict) or set(n) - NODE_KEYS or not {"id", "type", "name"} <= set(n):
            raise GraphError(f"each node is an object with id, type and name (allowed keys: {sorted(NODE_KEYS)})")
        nid = n["id"]
        if not isinstance(nid, str) or not ID_RE.fullmatch(nid) or nid in ids:
            raise GraphError(f"node id {nid!r} must be unique, lower-case letters, digits, - or _ (at most 40)")
        ids.add(nid)
        if n["type"] not in NODE_TYPES:
            raise GraphError(f"node {nid}: type must be one of {', '.join(NODE_TYPES)}")
        _text(n["name"], f"node {nid} name")
        if "role" in n and n["role"] != UNKNOWN and n["role"] not in ROLES:
            raise GraphError(f"node {nid}: role must be one of {', '.join(ROLES)} or \"?\"")
        for i, e in enumerate(_list(n.get("evidence", []), f"node {nid} evidence")):
            _text(e, f"node {nid} evidence[{i}]", unknown_ok=True)
        if "sla_days" in n:
            _int_or_unknown(n["sla_days"], f"node {nid} sla_days")
        if "sop_ref" in n:
            ref = n["sop_ref"]
            if not isinstance(ref, dict) or set(ref) != {"id", "revision"}:
                raise GraphError(f"node {nid}: sop_ref must be an object with id and revision")
            _text(ref["id"], f"node {nid} sop_ref id")
            _text(ref["revision"], f"node {nid} sop_ref revision", unknown_ok=True)
        if "data_class" in n and n["data_class"] != UNKNOWN and n["data_class"] not in DATA_CLASSES:
            raise GraphError(f"node {nid}: data_class must be one of {', '.join(DATA_CLASSES)} or \"?\"")
        for r in _list(n.get("notify", []), f"node {nid} notify"):
            if r not in ROLES:
                raise GraphError(f"node {nid}: notify lists QMS roles only")
        if "approves" in n and (not isinstance(n["approves"], str) or n["type"] != "approval"):
            raise GraphError(f"node {nid}: approves is a node id, on approval nodes only")
    for n in nodes:
        if "approves" in n and n["approves"] not in ids:
            raise GraphError(f"node {n['id']}: approves names an unknown node")
    for e in edges:
        if not isinstance(e, dict) or set(e) - EDGE_KEYS or not {"from", "to"} <= set(e):
            raise GraphError(f"each edge is an object with from and to (allowed keys: {sorted(EDGE_KEYS)})")
        if e["from"] not in ids or e["to"] not in ids:
            raise GraphError(f"edge {e.get('from')!r} -> {e.get('to')!r} names an unknown node")
        if "condition" in e:
            _text(e["condition"], f"edge {e['from']} -> {e['to']} condition")
    return graph
