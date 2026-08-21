"""Load the registries and schemas shipped with the skill."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = SKILL_ROOT / "references"


def load_json(name: str) -> dict[str, Any]:
    path = REFERENCE_DIR / name
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Registry {name} must contain a JSON object")
    return data


def load_runtime_resources() -> dict[str, dict[str, Any]]:
    return {
        "protocol_registry": load_json("protocol-registry.json"),
        "domain_registry": load_json("domain-registry.json"),
        "causal_designs": load_json("causal-designs.json"),
        "claim_schema": load_json("claim-ir.schema.json"),
        "compile_schema": load_json("compile-input.schema.json"),
    }
