"""Synthetic benchmark prompts (docs/BENCHMARK-PLAN.md, B4 and B5). Fictional codes and wording only: no real
document, title, number, name or path (R-23)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties, "required": required}}}


# Tools offered to every B4 prompt (Ollama ``ChatRequest.tools``, api/types.go:157,310-314,478-495 at 0d0720e5).
# Ollama's parameter type has no ``additionalProperties`` field, so the harness itself rejects argument names the
# schema does not list (harness.validate_arguments).
TOOLS: list[dict[str, Any]] = [
    _tool("record_nonconformity", "Record a nonconformity in the synthetic QMS",
          {"title": {"type": "string"}, "severity": {"type": "string", "enum": ["minor", "major", "critical"]},
           "department_code": {"type": "string"}},
          ["title", "severity", "department_code"]),
    _tool("schedule_audit", "Schedule an internal audit in the synthetic QMS",
          {"area_code": {"type": "string"}, "week": {"type": "integer"}, "auditor_role": {"type": "string"}},
          ["area_code", "week", "auditor_role"]),
    _tool("get_document_revision", "Look up the current revision of a synthetic controlled document",
          {"document_code": {"type": "string"}},
          ["document_code"]),
]


@dataclass(frozen=True)
class Prompt:
    prompt_id: str
    text: str
    expected_tool: str | None = None        # B4: the tool the prompt asks for


B4_PROMPTS = [
    Prompt("b4-01", "Synthetic test. Record a minor nonconformity titled 'Label smudged on fixture part' for "
                    "department SYN-D01. Use a tool.", "record_nonconformity"),
    Prompt("b4-02", "Synthetic test. Schedule an internal audit of area SYN-A07 in week 14; the auditor role is "
                    "'internal auditor'. Use a tool.", "schedule_audit"),
    Prompt("b4-03", "Synthetic test. What is the current revision of controlled document SYN-DOC-0042? Use a tool.",
           "get_document_revision"),
    Prompt("b4-04", "Synthetic test. Record a major nonconformity titled 'Calibration sticker missing on gauge' "
                    "for department SYN-D03. Use a tool.", "record_nonconformity"),
    Prompt("b4-05", "Synthetic test. Schedule an internal audit of area SYN-A02 in week 30 with the auditor role "
                    "'lead auditor'. Use a tool.", "schedule_audit"),
]

B5_PROMPTS = [
    Prompt("b5-01", "Synthetic test. In two sentences, explain why a quality system keeps records of corrective "
                    "actions."),
    Prompt("b5-02", "Synthetic test. List three checks an internal auditor might make on a fictional assembly line."),
    Prompt("b5-03", "Synthetic test. In one paragraph, describe what a document revision history is for."),
]
