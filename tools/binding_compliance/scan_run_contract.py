"""Validate Crash Log Scan Run fixtures, source inventory, and forbidden exports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from conformance.families.crash_log_scan_run import (
    REQUIRED_OBSERVATION_FACT_IDS_BY_SCENARIO,
)
from conformance.variant_policy import CRASH_LOG_SCAN_RUN_VARIANT_TARGETS

MANIFEST_PATH = Path("tests/fixtures/crash_log_scan_run/manifest.json")


class ManifestValidationError(ValueError):
    """Raised when scan-run fixtures, source inventory, or export constraints are invalid."""


def load_manifest(repo_root: Path) -> dict[str, Any]:
    """Load the canonical scan-run contract manifest from ``repo_root``."""

    path = repo_root / MANIFEST_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestValidationError(f"Cannot load {path}: {error}") from error
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{path} must contain a JSON object")
    return value


def _snake_case(name: str) -> str:
    """Convert one Rust PascalCase variant to its stable snake_case identifier."""

    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def _matching_brace(source: str, opening: int) -> int:
    """Return the closing brace paired with ``opening`` in Rust source."""

    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ManifestValidationError("Rust enum has no closing brace")


def _top_level_segments(body: str) -> list[str]:
    """Split a Rust enum body at commas outside tuple and struct payloads."""

    segments: list[str] = []
    start = 0
    round_depth = 0
    square_depth = 0
    curly_depth = 0
    for index, character in enumerate(body):
        if character == "(":
            round_depth += 1
        elif character == ")":
            round_depth -= 1
        elif character == "[":
            square_depth += 1
        elif character == "]":
            square_depth -= 1
        elif character == "{":
            curly_depth += 1
        elif character == "}":
            curly_depth -= 1
        elif character == "," and not (round_depth or square_depth or curly_depth):
            segments.append(body[start:index])
            start = index + 1
    segments.append(body[start:])
    return segments


def rust_enum_variants(source: str, enum_name: str) -> tuple[str, ...]:
    """Extract top-level variant names from one named Rust enum."""

    match = re.search(rf"\b(?:pub\s+)?enum\s+{re.escape(enum_name)}\s*{{", source)
    if match is None:
        raise ManifestValidationError(f"Rust enum {enum_name} was not found")
    opening = source.find("{", match.start())
    closing = _matching_brace(source, opening)
    body = source[opening + 1 : closing]
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    body = re.sub(r"//[^\n]*", "", body)

    variants: list[str] = []
    for segment in _top_level_segments(body):
        segment = re.sub(r"#\s*\[[^\]]*\]", "", segment).strip()
        variant = re.match(r"([A-Z][A-Za-z0-9_]*)", segment)
        if variant is not None:
            variants.append(variant.group(1))
    if not variants:
        raise ManifestValidationError(f"Rust enum {enum_name} has no parsed variants")
    return tuple(variants)


def _require_string_list(value: object, label: str) -> list[str]:
    """Return ``value`` as a unique string list or raise a validation error."""

    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ManifestValidationError(f"{label} must be a list of strings")
    if len(value) != len(set(value)):
        raise ManifestValidationError(f"{label} contains duplicates")
    return value


def _contains_forbidden_symbol(source: str, symbol: str) -> bool:
    """Return whether ``source`` contains one forbidden export marker.

    Identifier-shaped markers use Rust/Python/TypeScript identifier boundaries so
    a removed name such as ``scan_run_execute`` does not reject the surviving
    ``scan_run_contract_execute`` operation. Markers containing punctuation or
    whitespace are treated as exact source fragments for visibility declarations.
    """

    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", symbol):
        return (
            re.search(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])", source)
            is not None
        )
    return symbol in source


def _validate_forbidden_exports(
    repo_root: Path,
    forbidden_exports: object,
) -> None:
    """Fail when a contracted scan-execution export remains in a tracked surface.

    Each owner lists public source or generated-contract files and the exact names
    that must be absent. Required paths fail closed when missing; an entry may set
    ``optional`` only for a legacy file whose deletion is itself a valid outcome.
    """

    if not isinstance(forbidden_exports, dict) or not forbidden_exports:
        raise ManifestValidationError("forbiddenExports must be a non-empty object")

    root = repo_root.resolve()
    violations: list[str] = []
    for owner, entries in forbidden_exports.items():
        if not isinstance(owner, str) or not owner:
            raise ManifestValidationError(
                "forbiddenExports owner names must be strings"
            )
        if not isinstance(entries, list) or not entries:
            raise ManifestValidationError(
                f"forbiddenExports.{owner} must be a non-empty list"
            )
        for entry in entries:
            if not isinstance(entry, dict):
                raise ManifestValidationError(
                    f"forbiddenExports.{owner} entries must be objects"
                )
            relative_path = entry.get("path")
            if not isinstance(relative_path, str) or not relative_path:
                raise ManifestValidationError(
                    f"forbiddenExports.{owner} path must be a string"
                )
            symbols = _require_string_list(
                entry.get("symbols"),
                f"forbiddenExports.{owner}.{relative_path}.symbols",
            )
            if not symbols:
                raise ManifestValidationError(
                    f"forbiddenExports.{owner}.{relative_path}.symbols must not be empty"
                )
            optional = entry.get("optional", False)
            if not isinstance(optional, bool):
                raise ManifestValidationError(
                    f"forbiddenExports.{owner}.{relative_path}.optional must be boolean"
                )

            path = (root / relative_path).resolve()
            if not path.is_relative_to(root):
                raise ManifestValidationError(
                    f"forbiddenExports.{owner} path escapes the repository: {relative_path}"
                )
            if not path.is_file():
                if optional:
                    continue
                raise ManifestValidationError(
                    f"Cannot read {owner} forbidden-export surface {relative_path}"
                )
            try:
                source = path.read_text(encoding="utf-8")
            except OSError as error:
                raise ManifestValidationError(
                    f"Cannot read {owner} forbidden-export surface {path}: {error}"
                ) from error

            present = [
                symbol
                for symbol in symbols
                if _contains_forbidden_symbol(source, symbol)
            ]
            if present:
                violations.append(
                    f"{owner} {relative_path}: {', '.join(sorted(present))}"
                )

    if violations:
        raise ManifestValidationError(
            "forbidden legacy exports remain (" + "; ".join(violations) + ")"
        )


def _validate_rust_inventory(
    repo_root: Path,
    manifest: dict[str, Any],
    variants: set[str],
) -> None:
    """Require manifest variants to match every configured Rust enum exactly."""

    enum_specs = manifest.get("rustEnums")
    if not isinstance(enum_specs, list):
        raise ManifestValidationError("rustEnums must be a list")
    for spec in enum_specs:
        if not isinstance(spec, dict):
            raise ManifestValidationError("rustEnums entries must be objects")
        category = spec.get("category")
        relative_path = spec.get("path")
        enum_name = spec.get("name")
        if not all(
            isinstance(value, str) for value in (category, relative_path, enum_name)
        ):
            raise ManifestValidationError(
                "Rust enum category, path, and name must be strings"
            )
        source_path = repo_root / relative_path
        try:
            source = source_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ManifestValidationError(
                f"Cannot read Rust enum source {source_path}: {error}"
            ) from error
        parsed_variants = rust_enum_variants(source, enum_name)
        renames = spec.get("renames", {})
        if not isinstance(renames, dict) or not all(
            isinstance(name, str) and isinstance(value, str)
            for name, value in renames.items()
        ):
            raise ManifestValidationError(
                f"Rust enum {enum_name} renames must be strings"
            )
        unknown_renames = set(renames) - set(parsed_variants)
        if unknown_renames:
            raise ManifestValidationError(
                f"Rust enum {enum_name} has stale renames: {sorted(unknown_renames)}"
            )
        observed = {
            f"{category}.{renames.get(variant, _snake_case(variant))}"
            for variant in parsed_variants
        }
        declared = {
            variant for variant in variants if variant.startswith(f"{category}.")
        }
        missing = observed - declared
        stale = declared - observed
        if missing or stale:
            details = []
            if missing:
                details.append(f"unregistered: {', '.join(sorted(missing))}")
            if stale:
                details.append(f"stale: {', '.join(sorted(stale))}")
            raise ManifestValidationError(
                f"Rust enum {enum_name} does not match the manifest ({'; '.join(details)})"
            )


def _validate_variant_evidence_policy(variants: set[str]) -> None:
    """Require every source variant to name one real fact or retained analyzer."""

    policy_variants = set(CRASH_LOG_SCAN_RUN_VARIANT_TARGETS)
    missing = variants - policy_variants
    stale = policy_variants - variants
    if missing or stale:
        raise ManifestValidationError(
            "Crash Log Scan Run variant evidence policy differs: "
            f"missing={sorted(missing)}, stale={sorted(stale)}"
        )
    for variant, target in CRASH_LOG_SCAN_RUN_VARIANT_TARGETS.items():
        if target.retained_analyzer_id is not None:
            if target.scenario_id is not None:
                raise ManifestValidationError(
                    f"retained variant {variant} cannot claim an executable scenario"
                )
            continue
        scenario_facts = REQUIRED_OBSERVATION_FACT_IDS_BY_SCENARIO.get(
            target.scenario_id or ""
        )
        if scenario_facts is None or target.assertion_id not in scenario_facts:
            raise ManifestValidationError(
                f"variant {variant} references no required executable scenario fact"
            )


def _validate_failure_fixtures(manifest: dict[str, Any], variants: set[str]) -> None:
    """Require shared per-log and infrastructure failures to cover every stage."""

    fixtures = manifest.get("failureFixtures")
    if not isinstance(fixtures, dict):
        raise ManifestValidationError("failureFixtures must be an object")
    log_result = fixtures.get("logResult")
    if not isinstance(log_result, dict):
        raise ManifestValidationError("failureFixtures.logResult must be an object")
    failures = log_result.get("failures")
    if not isinstance(failures, list) or not failures:
        raise ManifestValidationError(
            "failureFixtures.logResult.failures must be a non-empty list"
        )
    observed_log_stages: set[str] = set()
    for failure in failures:
        if not isinstance(failure, dict):
            raise ManifestValidationError("log failure fixtures must be objects")
        stage = failure.get("stage")
        message = failure.get("message")
        if not isinstance(stage, str) or not isinstance(message, str) or not message:
            raise ManifestValidationError(
                "log failure fixtures require string stage and non-empty message"
            )
        observed_log_stages.add(f"log_failure_stage.{stage}")
    expected_log_stages = {
        variant for variant in variants if variant.startswith("log_failure_stage.")
    }
    if observed_log_stages != expected_log_stages:
        raise ManifestValidationError(
            "shared log failure stages differ: "
            f"missing={sorted(expected_log_stages - observed_log_stages)}, "
            f"stale={sorted(observed_log_stages - expected_log_stages)}"
        )

    infrastructure = fixtures.get("infrastructureErrors")
    if not isinstance(infrastructure, list) or not infrastructure:
        raise ManifestValidationError(
            "failureFixtures.infrastructureErrors must be a non-empty list"
        )
    observed_infrastructure_stages: set[str] = set()
    for failure in infrastructure:
        if not isinstance(failure, dict):
            raise ManifestValidationError(
                "infrastructure failure fixtures must be objects"
            )
        stage = failure.get("stage")
        raw_message = failure.get("rawMessage")
        message = failure.get("message")
        path = failure.get("path")
        if not all(
            isinstance(value, str) and value for value in (stage, raw_message, message)
        ):
            raise ManifestValidationError(
                "infrastructure failure fixtures require stage, rawMessage, and message"
            )
        if path is not None and not isinstance(path, str):
            raise ManifestValidationError(
                "infrastructure failure fixture path must be a string or null"
            )
        observed_infrastructure_stages.add(f"infrastructure_error_stage.{stage}")
    expected_infrastructure_stages = {
        variant
        for variant in variants
        if variant.startswith("infrastructure_error_stage.")
    }
    if observed_infrastructure_stages != expected_infrastructure_stages:
        raise ManifestValidationError(
            "shared infrastructure failure stages differ: "
            f"missing={sorted(expected_infrastructure_stages - observed_infrastructure_stages)}, "
            f"stale={sorted(observed_infrastructure_stages - expected_infrastructure_stages)}"
        )


def _validate_reset_fixture_contract(
    repo_root: Path,
    manifest: dict[str, Any],
) -> None:
    """Require the shared Reset To Default fixture corpus to remain repository-owned."""

    relative_root = manifest.get("fixtureRoot")
    if not isinstance(relative_root, str) or not relative_root:
        raise ManifestValidationError("fixtureRoot must be a non-empty string")
    root = repo_root.resolve()
    fixture_root = (root / relative_root).resolve()
    if not fixture_root.is_relative_to(root):
        raise ManifestValidationError("fixtureRoot must remain within the repository")
    if not fixture_root.is_dir():
        raise ManifestValidationError(
            f"fixtureRoot directory is missing: {relative_root}"
        )
    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, dict):
        raise ManifestValidationError("fixtures must be an object")
    installed_yaml_data = fixtures.get("installedYamlData")
    if not isinstance(installed_yaml_data, dict):
        raise ManifestValidationError(
            "fixtures.installedYamlData must be an object"
        )
    reset_outcomes = installed_yaml_data.get("resetOutcomes")
    if not isinstance(reset_outcomes, dict):
        raise ManifestValidationError(
            "fixtures.installedYamlData.resetOutcomes must be an object"
        )
    expected_codes = {
        "conflictCode": "local_ignore_reset_conflict",
        "backupFailureCode": "local_ignore_reset_backup_failure",
        "replacementFailureCode": "local_ignore_reset_replacement_failure",
        "durabilityUnknownCode": "local_ignore_reset_durability_unknown",
        "consumedCode": "scan_run_continuation_consumed",
    }
    for field, expected in expected_codes.items():
        if reset_outcomes.get(field) != expected:
            raise ManifestValidationError(
                "fixtures.installedYamlData.resetOutcomes."
                f"{field} must be {expected!r}"
            )
    expected_reset = installed_yaml_data.get("expectedResetToDefault")
    if not isinstance(expected_reset, dict):
        raise ManifestValidationError(
            "fixtures.installedYamlData.expectedResetToDefault must be an object"
        )
    if expected_reset.get("localIgnoreState") != "reset_to_default":
        raise ManifestValidationError(
            "fixtures.installedYamlData.expectedResetToDefault.localIgnoreState "
            "must be 'reset_to_default'"
        )
    diagnostic_kinds = set(
        _require_string_list(
            expected_reset.get("diagnosticKinds"),
            "fixtures.installedYamlData.expectedResetToDefault.diagnosticKinds",
        )
    )
    required_diagnostics = {"parse", "local_ignore_reset"}
    if diagnostic_kinds != required_diagnostics:
        raise ManifestValidationError(
            "fixtures.installedYamlData.expectedResetToDefault.diagnosticKinds "
            f"must be {sorted(required_diagnostics)}"
        )
    recovery_required = installed_yaml_data.get("expectedRecoveryRequired")
    if not isinstance(recovery_required, dict):
        raise ManifestValidationError(
            "fixtures.installedYamlData.expectedRecoveryRequired must be an object"
        )
    for field in ("mainProvenance", "gameProvenance"):
        retained = recovery_required.get(field)
        if not isinstance(retained, str) or expected_reset.get(field) != retained:
            raise ManifestValidationError(
                "fixtures.installedYamlData.expectedResetToDefault."
                f"{field} must retain expectedRecoveryRequired.{field}"
            )
    expected_outcomes: dict[str, object] = {
        "backupMustEqualMalformedBytes": True,
        "reportMustEqualExistingBytes": True,
        "preResetCancellationMutates": False,
        "postCriticalCancellationStatus": "cancelled",
    }
    for field, expected in expected_outcomes.items():
        if reset_outcomes.get(field) != expected:
            raise ManifestValidationError(
                "fixtures.installedYamlData.resetOutcomes."
                f"{field} must be {expected!r}"
            )


def validate_manifest(repo_root: Path, manifest: dict[str, Any]) -> None:
    """Validate independent fixtures, Rust inventory, variant targets, and export constraints."""

    if manifest.get("schemaVersion") != 1:
        raise ManifestValidationError("schemaVersion must be 1")
    variants = set(
        _require_string_list(manifest.get("contractVariants"), "contractVariants")
    )
    if not variants:
        raise ManifestValidationError("contractVariants must not be empty")

    # Inventory is checked first so a new Rust variant reports directly even if a
    # contributor is still assembling the rest of its cross-interface evidence.
    _validate_rust_inventory(repo_root, manifest, variants)
    _validate_variant_evidence_policy(variants)

    supported = _require_string_list(
        manifest.get("supportedAdapters"), "supportedAdapters"
    )

    fixture_files = _require_string_list(manifest.get("fixtureFiles"), "fixtureFiles")
    missing_fixtures = [
        path for path in fixture_files if not (repo_root / path).is_file()
    ]
    if missing_fixtures:
        raise ManifestValidationError(
            f"Shared fixture files are missing: {', '.join(missing_fixtures)}"
        )
    _validate_reset_fixture_contract(repo_root, manifest)
    _validate_failure_fixtures(manifest, variants)
    forbidden_exports = manifest.get("forbiddenExports")
    if not isinstance(forbidden_exports, dict) or set(forbidden_exports) != set(
        supported
    ):
        raise ManifestValidationError(
            "forbiddenExports must exactly match supportedAdapters"
        )
    # Run the contraction audit after inventory and fixture checks so malformed
    # variant or fixture changes retain their more specific diagnostics.
    _validate_forbidden_exports(repo_root, forbidden_exports)


def main(argv: list[str] | None = None) -> int:
    """Run the source-only scan-run contract validation command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    repo_root = arguments.repo_root.resolve()
    try:
        validate_manifest(repo_root, load_manifest(repo_root))
    except ManifestValidationError as error:
        print(
            f"Crash Log Scan Run contract validation failed: {error}", file=sys.stderr
        )
        return 1
    print("Crash Log Scan Run contract manifest is complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
