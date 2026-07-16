"""Validate the shared Crash Log Scan Run fixture and variant acknowledgements."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path("tests/fixtures/crash_log_scan_run/manifest.json")


class ManifestValidationError(ValueError):
    """Raised when scan-run fixture or adapter evidence is incomplete."""


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


def _validate_evidence(repo_root: Path, owner: str, evidence: object) -> None:
    """Require every evidence path and marker declared by one owner to exist."""

    if not isinstance(evidence, list) or not evidence:
        raise ManifestValidationError(f"{owner} must declare evidence")
    for entry in evidence:
        if not isinstance(entry, dict):
            raise ManifestValidationError(f"{owner} evidence entries must be objects")
        path = entry.get("path")
        markers = _require_string_list(
            entry.get("contains"), f"{owner} evidence markers"
        )
        if not isinstance(path, str):
            raise ManifestValidationError(f"{owner} evidence path must be a string")
        evidence_path = repo_root / path
        try:
            text = evidence_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ManifestValidationError(
                f"Cannot read {owner} evidence {evidence_path}: {error}"
            ) from error
        absent = [marker for marker in markers if marker not in text]
        if absent:
            raise ManifestValidationError(
                f"{owner} evidence {path} is missing markers: {', '.join(absent)}"
            )


def _validate_scenarios(repo_root: Path, manifest: dict[str, Any]) -> None:
    """Validate executable scenario and frontend-presentation evidence."""

    for group_name in ("scenarios", "presentations"):
        group = manifest.get(group_name)
        if not isinstance(group, dict) or not group:
            raise ManifestValidationError(f"{group_name} must be a non-empty object")
        for scenario_id, scenario in group.items():
            if not isinstance(scenario, dict):
                raise ManifestValidationError(
                    f"{group_name}.{scenario_id} must be an object"
                )
            required = _require_string_list(
                scenario.get("requiredOwners"),
                f"{group_name}.{scenario_id}.requiredOwners",
            )
            evidence = scenario.get("evidence")
            if not isinstance(evidence, dict):
                raise ManifestValidationError(
                    f"{group_name}.{scenario_id}.evidence must be an object"
                )
            missing = set(required) - set(evidence)
            extra = set(evidence) - set(required)
            if missing or extra:
                raise ManifestValidationError(
                    f"{group_name}.{scenario_id} evidence owners differ: "
                    f"missing={sorted(missing)}, extra={sorted(extra)}"
                )
            for owner, entries in evidence.items():
                _validate_evidence(
                    repo_root, f"{group_name}.{scenario_id}.{owner}", entries
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


def validate_manifest(repo_root: Path, manifest: dict[str, Any]) -> None:
    """Validate fixtures, Rust inventory, adapter acknowledgements, and evidence."""

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

    supported = _require_string_list(
        manifest.get("supportedAdapters"), "supportedAdapters"
    )
    adapters = manifest.get("adapters")
    if not isinstance(adapters, dict):
        raise ManifestValidationError("adapters must be an object")
    if set(adapters) != set(supported):
        raise ManifestValidationError("adapters must exactly match supportedAdapters")
    for adapter in supported:
        entry = adapters[adapter]
        if not isinstance(entry, dict):
            raise ManifestValidationError(f"{adapter} adapter entry must be an object")
        acknowledged = set(
            _require_string_list(
                entry.get("acknowledgedVariants"),
                f"{adapter}.acknowledgedVariants",
            )
        )
        missing = variants - acknowledged
        stale = acknowledged - variants
        if missing or stale:
            raise ManifestValidationError(
                f"{adapter} variant acknowledgements differ: "
                f"missing={sorted(missing)}, stale={sorted(stale)}"
            )
        _validate_evidence(repo_root, adapter, entry.get("evidence"))

    fixture_files = _require_string_list(manifest.get("fixtureFiles"), "fixtureFiles")
    missing_fixtures = [
        path for path in fixture_files if not (repo_root / path).is_file()
    ]
    if missing_fixtures:
        raise ManifestValidationError(
            f"Shared fixture files are missing: {', '.join(missing_fixtures)}"
        )
    _validate_failure_fixtures(manifest, variants)
    _validate_scenarios(repo_root, manifest)


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
