"""Autoscan Report goldens at the public pack and receipt boundaries."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.compare import NormalizationError
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.enforcement import enforcement_for_family
from conformance.families.autoscan_report import expand_report_expectation
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/autoscan_report/v1.json")


@pytest.mark.parametrize(
    "root, game_line, loader",
    [
        (
                r"C:\fixture",
                b"Game Root: C:\\fixture\\fcx-game\n",
                b"C:\\fixture\\fcx-game\\f4se_loader.exe",
        ),
        (
                "/fixture",
                b"Game Root: /fixture/fcx-game\n",
                b"/fixture/fcx-game/f4se_loader.exe",
        ),
    ],
)
def test_fcx_expands_only_environment_path_tokens(
        root: str, game_line: bytes, loader: bytes
) -> None:
    """Platform paths expand against literal expectations, without touching report prose."""
    scenario = load_and_validate_pack(ROOT, PACK).document()["scenarios"][2]
    expanded = expand_report_expectation(scenario["expected"], {"executionRoot": root})
    data = bytes.fromhex(expanded["durableEffects"]["reports"][0]["bytesHex"])
    assert game_line in data
    assert loader in data
    assert b"Data\\F4SE\\Plugins" in data
    assert b"* NOTICE: FCX LOCAL FILE CHECKS ARE ENABLED FOR THIS SCAN * \n" in data
    assert b"{{" not in data


@pytest.mark.parametrize(
    "root", ["relative", "", "/fixture/../escape", "/fixture\nspoof", None]
)
def test_report_root_cannot_inject_template_content(root: object) -> None:
    """Only absolute path metadata may participate in byte-oracle expansion."""
    scenario = load_and_validate_pack(ROOT, PACK).document()["scenarios"][2]
    with pytest.raises(NormalizationError):
        expand_report_expectation(scenario["expected"], {"executionRoot": root})


def test_goldens_remain_independent_and_all_adapters_are_blocking() -> None:
    """Every original owner golden remains an oracle, never an adapter fixture."""
    pack = load_and_validate_pack(ROOT, PACK)
    document = pack.document()
    assert [s["id"] for s in document["scenarios"]] == [
        "empty-findings",
        "populated-findings",
        "fcx-mode",
    ]
    assert len(pack.oracle_paths) == 3
    assert not set(pack.oracle_paths) & {f.resolved_path for f in pack.fixtures}
    for scenario, oracle in zip(document["scenarios"], pack.oracle_paths, strict=True):
        report = scenario["expected"]["durableEffects"]["reports"][0]
        assert bytes.fromhex(report["bytesHex"]) == oracle.read_bytes()
        assert report["sha256"] == hashlib.sha256(oracle.read_bytes()).hexdigest()
        assert report["byteLength"] == len(oracle.read_bytes())
    assert document["consumerObligations"] == []
    applicability = derive_applicability(document, load_source_parity_rows(ROOT))
    assert {p.id for p in applicability.participants} == {
        "rust",
        "cxx",
        "node",
        "python",
    }
    assert enforcement_for_family("autoscan-report") == "blocking"
    assert "autoscan-report" in FAMILY_COVERAGE_POLICIES


@pytest.mark.parametrize("participant", ["rust", "cxx", "node", "python"])
def test_receipts_reject_byte_display_effect_and_execution_mutations(
        tmp_path: Path, participant: str
) -> None:
    """Only fresh exact public observations grant coverage; no adapter is an oracle."""
    fixtures = Path("tests/fixtures/autoscan_report_goldens")
    (tmp_path / PACK).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / PACK, tmp_path / PACK)
    shutil.copytree(ROOT / fixtures, tmp_path / fixtures)
    for args in (
            ("init",),
            ("config", "user.email", "test@example.invalid"),
            ("config", "user.name", "Conformance Test"),
            ("add", "."),
            ("commit", "-m", "Fixture"),
    ):
        subprocess.run(
            ("git", "-C", str(tmp_path), *args), check=True, capture_output=True
        )
    pack = load_and_validate_pack(tmp_path, PACK)
    document = pack.document()
    policy = FAMILY_COVERAGE_POLICIES["autoscan-report"]
    run = materialize_run_plan(
        pack,
        participant_id=participant,
        participant_role="semantic-adapter",
        execution_instance_id=participant,
        source_paths=(PACK,),
    )
    plan = run.document()
    assert all("expected" not in s for s in plan["scenarios"])
    assert all(not p.endswith("expected.md") for p in plan["fixtures"].values())
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
        "id": "autoscan-boundary-test",
        "version": 1,
        "platform": "windows",
        "toolchain": participant,
    }
    receipt["scenarios"] = [
        {
            "id": s["id"],
            "executionStatus": "completed",
            "capabilityIds": s["capabilityIds"],
            "observation": expand_report_expectation(
                s["expected"], {"executionRoot": str(tmp_path / "execution")}
            ),
            "failure": None,
        }
        for s in document["scenarios"]
    ]

    def validate(value: dict):
        """Submit mutated execution evidence through the public receipt boundary."""
        run.receipt_path.write_text(json.dumps(value), encoding="utf-8")
        return validate_prepared_run(pack, run, coverage_policy=policy)

    report = validate(receipt)
    assert not report.failures
    assert all(s.result == "pass" for s in report.scenarios)
    rows = load_source_parity_rows(ROOT)
    if participant != "rust":
        coverage = derive_row_coverage(
            document,
            rows,
            policy,
            (report,),
            scope_participant_id=participant,
            retained_analyzers=load_retained_analyzer_kinds(ROOT),
        )
        assert coverage.rows and not coverage.failures
        prototype = next(
            r
            for r in rows
            if r.participant_id == participant and r.rust_symbol == "LogDisposition"
        )
        future = replace(
            prototype,
            obligation_id="parity:test:future-report-api",
            runtime_operation="future_method",
            required_evidence_kind="runtime",
            retained_analyzer_id=None,
        )
        expanded = derive_row_coverage(
            document,
            (*rows, future),
            policy,
            (report,),
            scope_participant_id=participant,
            retained_analyzers=load_retained_analyzer_kinds(ROOT),
        )
        assert expanded.failures
    mutations = [
        ("durableEffects", "reports", 0, "bytesHex"),
        ("durableEffects", "reports", 0, "sha256"),
        ("durableEffects", "reports", 0, "byteLength"),
        ("durableEffects", "reports", 0, "path"),
        ("durableEffects", "inputFiles", 0, "sha256"),
        ("durableEffects", "forbiddenPaths", 0, "exists"),
        ("displayContent", 0, "segments", 0, "path"),
        ("logs", 0, "formidCount"),
        ("semanticInputs", "showFormidValues"),
    ]
    for keys in mutations:
        changed = copy.deepcopy(receipt)
        value = changed["scenarios"][0]["observation"]
        for key in keys[:-1]:
            value = value[key]
        value[keys[-1]] = "wrong"
        assert validate(changed).failures, keys
    changed = copy.deepcopy(receipt)
    changed["scenarios"][2]["observation"]["durableEffects"]["unexpectedFiles"] = [
        "extra.tmp"
    ]
    assert validate(changed).failures
    for status in ("skipped", "unsupported", "failed"):
        changed = copy.deepcopy(receipt)
        changed["scenarios"][0]["executionStatus"] = status
        assert validate(changed).failures
    changed = copy.deepcopy(receipt)
    changed["scenarios"].pop()
    assert validate(changed).failures
    changed = copy.deepcopy(receipt)
    changed["invocation"]["id"] = "stale"
    assert validate(changed).failures
    # Changing an authored golden invalidates both expectation and source identity.
    pack.oracle_paths[0].write_bytes(pack.oracle_paths[0].read_bytes() + b" ")
    changed_pack = load_and_validate_pack(tmp_path, PACK)
    assert changed_pack.expectation_digest != pack.expectation_digest
    assert validate(receipt).failures
