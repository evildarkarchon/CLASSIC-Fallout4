"""Public pack, predicate, and materialization checks for semantic families."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.coverage import derive_observed_fact_ids
from conformance.enforcement import enforcement_for_family
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

from receipt_test_support import copy_participant_catalog

ROOT = Path(__file__).resolve().parents[3]
FAMILIES = (
    "crash-suspect",
    "crashgen-settings",
    "mod-guidance",
    "formid-lookup",
    "named-record",
    "plugin-evidence",
)


def test_lookup_memory_carriers_are_owned_only_by_executed_memory_scenarios() -> None:
    """Disabled and SQLite lookups cannot claim construction of in-memory entries."""
    policy = FAMILY_COVERAGE_POLICIES["formid-lookup"]
    carriers = {"FormIdValueLookupEntry", "FormIdValueLookupInMemoryReply"}
    # The entry facts only credited retired Python selectors; no class-wide
    # lookup fact may claim the carriers in their place.
    for predicate in policy.predicates:
        assert not carriers.intersection(predicate.rust_symbols)


@pytest.mark.parametrize("family", FAMILIES)
def test_semantic_pack_has_input_only_fixtures_and_exact_fact_predicates(
        family: str,
) -> None:
    """Every authored scenario proves semantic facts without exporting its oracle."""
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    )
    document = pack.document()
    policy = FAMILY_COVERAGE_POLICIES[family]
    assert enforcement_for_family(family) == "blocking"
    for scenario in document["scenarios"]:
        fixture = json.loads(
            (
                    pack.fixture_root
                    / document["fixtures"][scenario["input"]["fixtureRef"]]
            ).read_text()
        )
        assert set(fixture) <= {"configuration", "request", "warmupRequest"}
        assert set(fixture) >= {"configuration", "request"}
        assert scenario["normalization"]["excludedPaths"] == []
        expected = scenario["expected"]
        assert set(expected) == {"analyzerKind", "result", "error"}
        assert (expected["result"] is None) != (expected["error"] is None)
        assert derive_observed_fact_ids(document, scenario, expected, policy)
        for field in expected:
            mutated = copy.deepcopy(expected)
            del mutated[field]
            assert not derive_observed_fact_ids(document, scenario, mutated, policy)
        changed_action = {**scenario, "action": "unrelated.operation"}
        assert not derive_observed_fact_ids(document, changed_action, expected, policy)


def test_formid_outcomes_and_failures_remain_distinct() -> None:
    """Miss, disabled, malformed reply, and operational failure cannot share facts."""
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/formid_lookup/v1.json")
    )
    document = pack.document()
    policy = FAMILY_COVERAGE_POLICIES["formid-lookup"]
    scenarios = {item["id"]: item for item in document["scenarios"]}
    evidence = [
        set(
            derive_observed_fact_ids(
                document, scenarios[name], scenarios[name]["expected"], policy
            )
        )
        for name in (
            "hit",
            "miss-after-reuse",
            "disabled",
            "blank-value",
            "operational-failure",
        )
    ]
    assert all(evidence)
    assert all(
        not left & right
        for i, left in enumerate(evidence)
        for right in evidence[i + 1:]
    )


def test_occurrence_count_type_and_authored_guidance_are_not_coarsened() -> None:
    """Typed counts and complete authored text remain load-bearing coverage facts."""
    for family, collection, field, value in (
            ("named-record", "findings", "occurrences", True),
            ("mod-guidance", "conflicts", "description", ""),
    ):
        pack = load_and_validate_pack(
            ROOT, Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
        )
        document = pack.document()
        scenario = document["scenarios"][0]
        mutated = copy.deepcopy(scenario["expected"])
        mutated["result"][collection][0][field] = value
        assert not derive_observed_fact_ids(
            document, scenario, mutated, FAMILY_COVERAGE_POLICIES[family]
        )


@pytest.mark.parametrize("family", FAMILIES)
def test_semantic_receipts_validate_their_scope_and_reject_an_omitted_case(
        tmp_path: Path, family: str
) -> None:
    """Central receipt validation passes the projected scope and rejects an omitted case."""
    pack_path = Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    fixture_path = Path("tests/fixtures/semantic_conformance") / family
    (tmp_path / pack_path).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / pack_path, tmp_path / pack_path)
    shutil.copytree(ROOT / fixture_path, tmp_path / fixture_path)
    copy_participant_catalog(ROOT, tmp_path)
    for args in (
            ("init",),
            ("config", "user.email", "conformance@example.invalid"),
            ("config", "user.name", "Conformance Tests"),
            ("add", "."),
            ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True
        )
    pack = load_and_validate_pack(tmp_path, pack_path)
    policy = FAMILY_COVERAGE_POLICIES[family]
    for participant in ("cxx",):
        run = materialize_run_plan(
            pack,
            participant_id=participant,
            participant_role="semantic-adapter",
            execution_instance_id=participant,
            source_paths=(pack_path,),
        )
        plan = run.document()
        assert all("expected" not in scenario for scenario in plan["scenarios"])
        receipt = {
            key: plan[key]
            for key in (
                "schemaVersion",
                "familyId",
                "familyVersion",
                "expectationDigest",
                "invocation",
                "participant",
            )
        }
        receipt["runner"] = {
            "id": "semantic-boundary-test",
            "version": 1,
            "platform": "windows",
            "toolchain": participant,
        }
        receipt["scenarios"] = [
            {
                "id": scenario["id"],
                "executionStatus": "completed",
                "capabilityIds": scenario["capabilityIds"],
                "observation": scenario["expected"],
                "failure": None,
            }
            for scenario in pack.document()["scenarios"]
        ]
        run.receipt_path.write_text(json.dumps(receipt))
        report = validate_prepared_run(pack, run, coverage_policy=policy)
        assert not report.failures
        assert all(scenario.result == "pass" for scenario in report.scenarios)
        assert all(scenario.observed_fact_ids for scenario in report.scenarios)
        if family == "mod-guidance":
            # A nonblank replacement remains a typed observation, but the pack's
            # exact comparator must reject prose different from the authored text.
            changed = copy.deepcopy(receipt)
            observation = changed["scenarios"][0]["observation"]
            observation["result"]["conflicts"][0]["description"] = (
                "Different authored guidance"
            )
            assert derive_observed_fact_ids(
                pack.document(), pack.document()["scenarios"][0], observation, policy
            )
            run.receipt_path.write_text(json.dumps(changed))
            mismatch = validate_prepared_run(pack, run, coverage_policy=policy)
            assert mismatch.scenarios[0].result == "fail"
        receipt["scenarios"].pop(0)
        run.receipt_path.write_text(json.dumps(receipt))
        rejected = validate_prepared_run(pack, run, coverage_policy=policy)
        assert rejected.failures or any(
            scenario.result != "pass" for scenario in rejected.scenarios
        )

