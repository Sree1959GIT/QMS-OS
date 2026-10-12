"""The benchmark Ollama service in compose.yaml (MVP-0 slice 1b; docs/BENCHMARK-PLAN.md, pre-run checklist). Reads the
file as text: no YAML library, no Docker, no network. Synthetic compose snippets show that the checks fail when they
should."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SERVICE = "ollama-bench"
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")


def _value(line: str) -> str:
    v = line.split(":", 1)[1].split(" #", 1)[0].strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v


def service(text: str, name: str = SERVICE) -> dict[str, object]:
    """The keys checked here, from one service in block-style compose YAML (2-space indents, as compose.yaml uses)."""
    lines = text.splitlines()
    start = lines.index(f"  {name}:")
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith("    "):
            break
        if line.strip() and not line.lstrip().startswith("#"):
            body.append(line)
    out: dict[str, object] = {"ports": [], "environment": {}, "profiles": []}
    section = ""
    for line in body:
        if not line.startswith("     "):          # a key of the service (4-space indent)
            key = line.strip().split(":", 1)[0]
            section = key
            if key == "image":
                out["image"] = _value(line)
            elif key == "profiles" and "[" in line:
                out["profiles"] = [p.strip().strip("\"'") for p in line.split("[", 1)[1].split("]")[0].split(",")]
            continue
        item = line.strip()
        if section == "ports" and item.startswith("- "):
            out["ports"].append(item[2:].strip().strip("\"'"))  # type: ignore[union-attr]
        elif section == "environment":
            k, v = (item[2:].split("=", 1) if item.startswith("- ") else (item.split(":", 1)[0], _value(item)))
            out["environment"][k.strip()] = v.strip().strip("\"'")  # type: ignore[index]
        elif section == "profiles" and item.startswith("- "):
            out["profiles"].append(item[2:].strip().strip("\"'"))  # type: ignore[union-attr]
    return out


def problems(svc: dict[str, object]) -> list[str]:
    found = []
    if not DIGEST.search(str(svc.get("image", ""))):
        found.append("image not pinned by digest")
    ports = svc["ports"]
    if len(ports) != 1 or not ports[0].startswith("127.0.0.1:"):  # type: ignore[arg-type,index]
        found.append("port binding not loopback only")
    if svc["environment"].get("OLLAMA_NO_CLOUD") != "1":  # type: ignore[attr-defined]
        found.append("OLLAMA_NO_CLOUD is not 1")
    if svc["profiles"] != ["benchmark"]:
        found.append("profile is not benchmark")
    return found


def test_repository_benchmark_service_meets_the_pre_run_checklist():
    svc = service((REPO / "compose.yaml").read_text(encoding="utf-8"))
    assert DIGEST.search(str(svc["image"]))
    assert svc["ports"] == ["127.0.0.1:11435:11434"]
    assert svc["environment"] == {"OLLAMA_NO_CLOUD": "1"}
    assert svc["profiles"] == ["benchmark"]
    assert problems(svc) == []


GOOD = """services:
  ollama-bench:
    image: example/runtime:1.0@sha256:{d}
    profiles: ["benchmark"]
    environment:
      OLLAMA_NO_CLOUD: "1"
    ports:
      - "127.0.0.1:11435:11434"
volumes:
  models:
""".replace("{d}", "0123456789abcdef" * 4)


@pytest.mark.parametrize(("old", "new", "expected"), [
    ("@sha256:" + "0123456789abcdef" * 4, "", "image not pinned by digest"),
    ('"127.0.0.1:11435:11434"', '"0.0.0.0:11435:11434"', "port binding not loopback only"),
    ('"127.0.0.1:11435:11434"', '"11435:11434"', "port binding not loopback only"),
    ('      - "127.0.0.1:11435:11434"', '      - "127.0.0.1:11435:11434"\n      - "11436:11434"',
     "port binding not loopback only"),
    ('OLLAMA_NO_CLOUD: "1"', 'OLLAMA_NO_CLOUD: "0"', "OLLAMA_NO_CLOUD is not 1"),
    ('      OLLAMA_NO_CLOUD: "1"\n', "      OTHER: x\n", "OLLAMA_NO_CLOUD is not 1"),
    ('profiles: ["benchmark"]', 'profiles: ["default"]', "profile is not benchmark"),
    ('    profiles: ["benchmark"]\n', "", "profile is not benchmark"),
])
def test_synthetic_violations_are_reported(old, new, expected):
    assert problems(service(GOOD)) == []
    text = GOOD.replace(old, new)
    assert text != GOOD
    assert problems(service(text)) == [expected]


def test_list_forms_are_read():
    text = GOOD.replace('profiles: ["benchmark"]', "profiles:\n      - benchmark").replace(
        'OLLAMA_NO_CLOUD: "1"', "- OLLAMA_NO_CLOUD=1")
    assert problems(service(text)) == []
