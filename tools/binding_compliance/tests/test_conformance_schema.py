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
    """Every tracked v1 envelope fails closed on unknown common fields."""

    for name in (
        "scenario-pack-v1.schema.json",
        "run-plan-v1.schema.json",
        "receipt-v1.schema.json",
        "policy-exceptions-v1.schema.json",
        "consumer-obligations-v1.schema.json",
        "conformance-report-v1.schema.json",
    ):
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


def test_receipt_schema_freezes_current_execution_and_status_evidence() -> None:
    """The receipt schema requires actual observations and closed identities."""

    receipt_schema = _schema("receipt-v1.schema.json")
    scenario = receipt_schema["properties"]["scenarios"]["items"]

    assert set(receipt_schema["required"]) == {
        "schemaVersion",
        "familyId",
        "familyVersion",
        "expectationDigest",
        "invocation",
        "participant",
        "runner",
    }
    role_branch = receipt_schema["allOf"][0]
    assert role_branch["then"]["required"] == ["obligations"]
    assert role_branch["else"]["required"] == ["scenarios"]
    assert scenario["properties"]["executionStatus"] == {
        "enum": ["completed", "failed", "not_applicable"]
    }
    assert scenario["properties"]["observation"] == {
        "oneOf": [
            {"$ref": "#/$defs/canonicalJsonObject"},
            {"type": "null"},
        ]
    }
    assert scenario["additionalProperties"] is False


def test_policy_exception_schema_requires_reviewable_exact_scope() -> None:
    """Applicability exceptions name policy, capability, and participant owners."""

    exception_schema = _schema("policy-exceptions-v1.schema.json")
    exception = exception_schema["properties"]["exceptions"]["items"]
    catalog = json.loads(
        (SCHEMA_ROOT.parent / "policy_exceptions.json").read_text(encoding="utf-8")
    )

    assert set(exception["required"]) == {
        "id",
        "capabilityId",
        "participantId",
        "rationale",
        "policyPage",
    }
    assert exception["additionalProperties"] is False
    assert catalog == {"schemaVersion": 1, "exceptions": []}


def test_report_schema_pins_scope_and_enforcement_lifecycle() -> None:
    """The envelope admits only reviewed ratchet states and honest scope labels."""

    report_schema = _schema("conformance-report-v1.schema.json")
    scope = report_schema["properties"]["scope"]

    assert report_schema["properties"]["enforcement"] == {
        "enum": ["shadow", "blocking"]
    }
    assert report_schema["properties"]["repositoryComplete"] == {"type": "boolean"}
    assert scope["additionalProperties"] is False
    assert {choice["properties"]["kind"]["const"] for choice in scope["oneOf"]} == {
        "execution-instance",
        "participant",
        "full-repository",
    }
