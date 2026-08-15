"""Structural checks for the tracked common conformance JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "tests" / "conformance" / "schemas"


def _schema(name: str) -> dict[str, object]:
    """Load one required tracked JSON Schema object."""

    value = json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_tracked_common_schemas_are_closed_and_versioned() -> None:
    """Both tracked v1 envelopes fail closed on unknown common fields."""

    for name in ("scenario-pack-v1.schema.json", "run-plan-v1.schema.json"):
        schema = _schema(name)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        assert schema["properties"]["schemaVersion"] == {"const": 1}


def test_run_plan_schema_structurally_withholds_scenario_expectations() -> None:
    """The tracked adapter plan schema cannot admit the central oracle field."""

    pack_schema = _schema("scenario-pack-v1.schema.json")
    run_plan_schema = _schema("run-plan-v1.schema.json")
    pack_scenario = pack_schema["properties"]["scenarios"]["items"]
    run_plan_scenario = run_plan_schema["properties"]["scenarios"]["items"]

    assert "expected" in pack_scenario["required"]
    assert "expected" in pack_scenario["properties"]
    assert "expected" not in run_plan_scenario["required"]
    assert "expected" not in run_plan_scenario["properties"]
    assert run_plan_scenario["additionalProperties"] is False


def test_pack_schema_recursively_excludes_floating_point_payload_numbers() -> None:
    """The tracked pack schema points input and oracle data at canonical JSON."""

    pack_schema = _schema("scenario-pack-v1.schema.json")
    scenario = pack_schema["properties"]["scenarios"]["items"]
    canonical_value = pack_schema["$defs"]["canonicalJsonValue"]

    assert pack_schema["x-classic-reject-floating-point-lexemes"] is True
    assert scenario["properties"]["input"] == {"$ref": "#/$defs/canonicalJsonObject"}
    assert scenario["properties"]["expected"] == {"$ref": "#/$defs/canonicalJsonObject"}
    assert {choice.get("type") for choice in canonical_value["oneOf"]} == {
        "array",
        "boolean",
        "integer",
        "null",
        "object",
        "string",
    }
