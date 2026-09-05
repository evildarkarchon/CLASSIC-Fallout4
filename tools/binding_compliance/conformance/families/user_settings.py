"""Compile User Settings observations from its independent compatibility oracle."""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

from ..compare import NormalizationError, exact_differences
from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_DEFAULT_FIELDS = {
    "update_check": "Update Check",
    "game_version": "Game Version",
    "move_unsolved_logs": "Move Unsolved Logs",
    "max_concurrent_scans": "Max Concurrent Scans",
    "fcx_mode": "FCX Mode",
    "simplify_logs": "Simplify Logs",
    "show_formid_values": "Show FormID Values",
}


def compile_compatibility_expectations(
    pack: Mapping[str, Any], oracle: Mapping[str, Any], fixture_root: Path
) -> dict[str, Any]:
    """Resolve case references into exact observations without querying Rust.

    The existing compatibility corpus remains the only authored value oracle.
    Field selection is input-only; the receipt comparator still rejects every
    missing or extra observation field. Invalid references raise ``ValueError``.
    """

    if oracle.get("contract_version") != 1:
        raise ValueError("unsupported User Settings compatibility contract version")
    cases = {case["id"]: case for case in oracle["cases"]}
    if len(cases) != len(oracle["cases"]):
        raise ValueError("duplicate User Settings compatibility case identity")
    result = copy.deepcopy(dict(pack))
    selected_cases = [
        scenario["expected"].get("compatibilityCase")
        for scenario in result["scenarios"]
        if scenario["action"] == "user-settings.open"
    ]
    required_cases = set(cases) - {
        "tui_remembered_state",
        "concurrent_revision_conflict",
    }
    if (
        len(selected_cases) != len(set(selected_cases))
        or set(selected_cases) != required_cases
    ):
        raise ValueError(
            "User Settings pack must cover every ordinary open compatibility case exactly once"
        )
    for scenario in result["scenarios"]:
        if scenario["action"] != "user-settings.open":
            continue
        reference = scenario["expected"]
        if set(reference) != {"compatibilityCase"}:
            raise ValueError(
                "User Settings expectations must reference a compatibilityCase"
            )
        case_id = reference["compatibilityCase"]
        if case_id not in cases:
            raise ValueError(f"unknown User Settings compatibility case: {case_id}")
        case = cases[case_id]
        if case_id in {"tui_remembered_state", "concurrent_revision_conflict"}:
            raise ValueError(
                "User Settings open scenarios cannot cover mutating operations"
            )
        if scenario["action"] != "user-settings.open":
            raise ValueError("User Settings read pack requires the open action")
        view = copy.deepcopy(case.get("expected_view", {}))
        if case.get("uses_canonical_defaults") or case.get("uses_degraded_fallbacks"):
            defaults = oracle["canonical_defaults"]["CLASSIC_Settings"]
            fallbacks = oracle["degraded_fallbacks"]["CLASSIC_Settings"]
            view = {field: defaults[label] for field, label in _DEFAULT_FIELDS.items()}
            if case.get("uses_degraded_fallbacks"):
                for field, label in _DEFAULT_FIELDS.items():
                    if label in fallbacks:
                        view[field] = fallbacks[label]["value"]
        inputs = scenario["input"]
        if set(inputs) != {"installationData", "observationFields"}:
            raise ValueError(
                "User Settings open input must contain only installationData and observationFields"
            )
        if inputs["observationFields"] != sorted(view):
            raise ValueError(
                "User Settings observationFields must exactly select the oracle view"
            )
        fixture = case["fixture"]
        installed = inputs["installationData"]
        if fixture is None:
            if installed or scenario["fixtureRefs"]:
                raise ValueError("missing User Settings case cannot install a fixture")
        elif (
            len(installed) != 1
            or set(installed[0]) != {"fixtureRef", "path"}
            or installed[0]["path"] != case["source"]["relative_path"]
            or pack["fixtures"].get(installed[0]["fixtureRef"]) != fixture
            or scenario["fixtureRefs"] != [installed[0]["fixtureRef"]]
        ):
            raise ValueError(
                "User Settings installed input does not match its compatibility case"
            )
        present = fixture is not None
        classification = case["source"]["classification"]
        classification = {
            "canonical_current": "current",
            "current": "current",
            "current_with_diagnostics": "current",
            "current_with_alias": "current",
            "current_with_unknown_entries": "current",
            # This corpus case is the historical nested shape without schema_version.
            "legacy_location": "unversioned",
            "legacy_flat_shape": "legacy_flat",
            "missing": "missing",
            "malformed": "malformed",
            "future_major": "future_major",
        }[classification]
        eligibility = (
            "eligible"
            if case["commit_eligible"]
            else (
                "requires_migration"
                if case["migration_required"]
                else "blocked_untrusted"
            )
        )
        scenario["expected"] = {
            "source": {
                "location": {
                    "classic_root": "canonical",
                    "classic_data_directory": "legacy",
                    "none": "missing",
                }[case["source"]["location"]],
                "path": {"path": case["source"]["relative_path"]} if present else None,
                "classification": classification,
            },
            "commitEligibility": eligibility,
            "diagnostics": copy.deepcopy(case["diagnostics"]),
            "view": view,
            "durableEffects": {"treeUnchanged": True},
            "revision": {
                "kind": "sha256" if present else "missing",
                "matchesSourceBytes": True,
            },
            "originalContent": {"present": present, "matchesSourceBytes": True},
        }
    _compile_operations(result, oracle, fixture_root)
    return result


def _oracle_fixture(fixture_root: Path, filename: str) -> Path:
    """Resolve an authored oracle dependency without escaping its fixture root."""

    relative = PurePosixPath(filename)
    if relative.is_absolute() or "\\" in filename or ".." in relative.parts:
        raise ValueError("User Settings oracle fixture must be a relative path")
    resolved = (fixture_root / filename).resolve(strict=True)
    resolved.relative_to(fixture_root.resolve())
    if not resolved.is_file():
        raise ValueError("User Settings oracle fixture must be a regular file")
    return resolved


def operation_oracle_paths(
    oracle: Mapping[str, Any], fixture_root: Path
) -> tuple[Path, ...]:
    """Return expected document dependencies kept out of adapter run plans."""

    return tuple(
        sorted(
            {
                _oracle_fixture(fixture_root, operation["expected_document"])
                for operation in oracle["operation_scenarios"]
                if "conformance" in operation and operation["writes_document"]
            }
        )
    )


def _yaml_nodes(content: bytes) -> object:
    """Parse YAML independently into type-tagged, deterministic JSON nodes.

    Real scalars retain an explicit type and string representation because the
    shared pack format forbids floating-point JSON values. Duplicate keys,
    nonfinite numbers, cyclic aliases, and unsupported node types are rejected.
    """

    from ruamel.yaml import YAML
    from ruamel.yaml.constructor import SafeConstructor

    class ExactConstructor(SafeConstructor):
        """Keep unknown real scalar precision independent of binary floating point."""

    def decimal_scalar(constructor: Any, scalar: Any) -> Decimal:
        """Decode a YAML real without rounding away authored significant digits."""

        try:
            return Decimal(constructor.construct_scalar(scalar).replace("_", ""))
        except InvalidOperation as error:
            raise ValueError("unsupported nonfinite YAML real") from error

    ExactConstructor.add_constructor("tag:yaml.org,2002:float", decimal_scalar)

    parser = YAML(typ="safe", pure=True)
    parser.Constructor = ExactConstructor
    parser.version = (1, 2)
    parser.allow_duplicate_keys = False
    active: set[int] = set()

    def node(value: object) -> object:
        """Preserve scalar types and collection contents without YAML formatting."""

        if value is None:
            return {"type": "null"}
        if type(value) in (str, bool, int):
            return {
                "type": {str: "string", bool: "boolean", int: "integer"}[type(value)],
                "value": value,
            }
        if isinstance(value, Decimal) and value.is_finite():
            parts = value.as_tuple()
            digits = "".join(str(digit) for digit in parts.digits).rstrip("0")
            exponent = parts.exponent + len(parts.digits) - len(digits)
            return {
                "type": "real",
                "value": ("-" if parts.sign else "") + digits + "e" + str(exponent)
                if digits
                else "0",
            }
        if id(value) in active:
            raise ValueError("cyclic YAML aliases are not supported")
        active.add(id(value))
        try:
            if isinstance(value, dict) and all(type(key) is str for key in value):
                return {
                    "type": "mapping",
                    "value": {key: node(value[key]) for key in sorted(value)},
                }
            if isinstance(value, list):
                return {"type": "sequence", "value": [node(item) for item in value]}
            raise ValueError("unsupported YAML node type")
        finally:
            active.remove(id(value))

    from ruamel.yaml.error import YAMLError

    try:
        return node(parser.load(content.decode("utf-8")))
    except YAMLError as error:
        raise ValueError(f"invalid User Settings YAML observation: {error}") from error


def _revision(content: bytes | None) -> str:
    """Hash independent source bytes using the public content revision token."""

    return (
        "missing"
        if content is None
        else "sha256:" + hashlib.sha256(content).hexdigest()
    )


def _tree(
    content: bytes | None, *, root_exists: bool, lock: bool = False
) -> list[dict[str, Any]]:
    """Describe the exact expected installation entries, including coordination."""

    tree: list[dict[str, Any]] = []
    if root_exists:
        tree.append({"path": {"path": "."}, "kind": "directory"})
    if content is not None:
        tree.append(
            {
                "path": {"path": "CLASSIC Settings.yaml"},
                "kind": "file",
                "bytesHex": content.hex(),
            }
        )
    if lock:
        tree.append(
            {
                "path": {"path": "CLASSIC Settings.yaml.commit.lock"},
                "kind": "file",
                "bytesHex": "",
            }
        )
    return tree


def _compile_operations(
    pack: dict[str, Any], oracle: Mapping[str, Any], fixture_root: Path
) -> None:
    """Validate executable operation references and compile their exact oracle."""

    operations = {
        operation["id"]: operation
        for operation in oracle["operation_scenarios"]
        if "conformance" in operation
    }
    if len(operations) != sum(
        "conformance" in operation for operation in oracle["operation_scenarios"]
    ):
        raise ValueError("duplicate User Settings operation scenario identity")
    scenarios = [
        scenario
        for scenario in pack["scenarios"]
        if scenario["action"] != "user-settings.open"
    ]
    selected = [scenario["expected"].get("operationScenario") for scenario in scenarios]
    if len(selected) != len(set(selected)) or set(selected) != set(operations):
        raise ValueError(
            "User Settings pack must cover every authored conformance operation exactly once"
        )
    expected_paths = set(operation_oracle_paths(oracle, fixture_root))
    if any(
        _oracle_fixture(fixture_root, name) in expected_paths
        for name in pack["fixtures"].values()
    ):
        raise ValueError(
            "User Settings expected documents cannot be adapter input fixtures"
        )
    fixture_ids = {
        filename: reference for reference, filename in pack["fixtures"].items()
    }
    field_order = (
        "/CLASSIC_Settings/Update Check",
        "/CLASSIC_Settings/Max Concurrent Scans",
    )
    for scenario in scenarios:
        if set(scenario["expected"]) != {"operationScenario"}:
            raise ValueError(
                "User Settings operation expectations must reference an operationScenario"
            )
        operation = operations[scenario["expected"]["operationScenario"]]
        config = operation["conformance"]
        source_name = operation["source_fixture"]
        disk_name = operation["disk_fixture_before"]
        source = (
            None
            if source_name is None
            else _oracle_fixture(fixture_root, source_name).read_bytes()
        )
        disk = (
            None
            if disk_name is None
            else _oracle_fixture(fixture_root, disk_name).read_bytes()
        )
        installation = (
            []
            if source_name is None
            else [
                {
                    "fixtureRef": fixture_ids[source_name],
                    "path": "CLASSIC Settings.yaml",
                }
            ]
        )
        external = (
            None
            if disk_name == source_name
            else {"fixtureRef": fixture_ids[disk_name], "path": "CLASSIC Settings.yaml"}
        )
        expected_input = {
            "installationData": installation,
            "installationRootExists": config["installation_root_exists"],
            "previewMode": config["preview_mode"],
            "requestedUpdate": operation["requested_update"],
            "commit": config["commit"],
            "externalEdit": external,
        }
        refs = [item["fixtureRef"] for item in installation] + (
            [] if external is None else [external["fixtureRef"]]
        )
        capability_ids = ["user-settings.update"]
        if (
            exact_differences(expected_input, scenario["input"])
            or scenario["fixtureRefs"] != refs
            or scenario["action"] != config["action"]
            or scenario["capabilityIds"] != capability_ids
        ):
            raise ValueError(
                "User Settings operation input does not match its independent oracle"
            )
        if set(operation["requested_update"]) - set(field_order):
            raise ValueError("unsupported User Settings operation update selector")
        if (
            type(config["commit"]) is not bool
            or type(config["installation_root_exists"]) is not bool
        ):
            raise ValueError("User Settings operation controls must be booleans")
        if (
            config["preview_mode"] not in {"update", "bootstrap"}
            or config["action"] != "user-settings.update"
        ):
            raise ValueError(
                "User Settings operation must select an explicit supported preview mode"
            )
        diagnostics = copy.deepcopy(config["preview_diagnostics"])
        accepted = not diagnostics
        attempted = accepted and config["commit"]
        committed = attempted and operation["writes_document"]
        preview = {
            "status": "accepted" if accepted else "rejected",
            "baseRevision": _revision(source) if accepted else None,
            "acceptedFields": [
                {"fieldPath": field, "value": operation["requested_update"][field]}
                for field in field_order
                if field in operation["requested_update"]
            ]
            if accepted
            else [],
            "diagnostics": diagnostics,
        }
        commit = {
            "status": "committed"
            if committed
            else "conflict"
            if attempted
            else "not-attempted",
            "revision": {"matchesPublishedBytes": True} if committed else None,
            "expectedRevision": _revision(source)
            if attempted and not committed
            else None,
            "actualRevision": _revision(disk) if attempted and not committed else None,
        }
        before = _tree(source, root_exists=config["installation_root_exists"])
        after = _tree(
            disk,
            root_exists=config["installation_root_exists"] or attempted,
            lock=committed,
        )
        if committed:
            document = {
                "path": {"path": "CLASSIC Settings.yaml"},
                "kind": "file",
                "yamlNodes": _yaml_nodes(
                    _oracle_fixture(
                        fixture_root, operation["expected_document"]
                    ).read_bytes()
                ),
            }
            if disk is None:
                after.insert(1, document)
            else:
                after[1] = document
        scenario["expected"] = {
            "preview": preview,
            "afterPreviewTree": before,
            "commit": commit,
            "finalTree": after,
        }


def normalize_operation_observation(
    expected: Mapping[str, Any], actual: Mapping[str, Any]
) -> dict[str, Any]:
    """Authenticate committed revisions and normalize only published YAML bytes.

    All preview, rejection, conflict, and incidental-file observations remain
    exact. The receipt must provide raw bytes; pre-normalized YAML or a runner's
    self-reported revision match cannot substitute for observed evidence.
    """

    result = copy.deepcopy(dict(actual))
    if expected.get("commit", {}).get("status") != "committed":
        return result
    try:
        tree = result["finalTree"]
        if not isinstance(tree, list) or any(
            not isinstance(entry, dict) for entry in tree
        ):
            raise ValueError(
                "committed observation tree must contain file or directory objects"
            )
        documents = [
            entry
            for entry in tree
            if entry.get("path") == {"path": "CLASSIC Settings.yaml"}
        ]
        if len(documents) != 1:
            raise ValueError(
                "committed observation must contain one canonical document"
            )
        document = documents[0]
        if set(document) != {"path", "kind", "bytesHex"} or document["kind"] != "file":
            raise ValueError(
                "committed document requires a raw regular-file byte observation"
            )
        encoded = document.pop("bytesHex")
        if (
            not isinstance(encoded, str)
            or re.fullmatch(r"(?:[0-9a-f]{2})*", encoded) is None
        ):
            raise ValueError("committed document bytes must be lowercase hexadecimal")
        content = bytes.fromhex(encoded)
        if result["commit"]["revision"] != _revision(content):
            raise ValueError(
                "committed revision does not match observed published bytes"
            )
        document["yamlNodes"] = _yaml_nodes(content)
        result["commit"]["revision"] = {"matchesPublishedBytes": True}
    except (KeyError, TypeError, ValueError) as error:
        raise NormalizationError(str(error), "$.finalTree") from error
    return result


def _source(observation: Mapping[str, Any]) -> bool:
    """Recognize actual typed source, revision, and retained-byte observations."""

    source = observation.get("source")
    revision = observation.get("revision")
    original = observation.get("originalContent")
    return (
        isinstance(source, Mapping)
        and source.get("location") in {"canonical", "legacy", "missing"}
        and isinstance(revision, Mapping)
        and revision.get("matchesSourceBytes") is True
        and isinstance(original, Mapping)
        and original.get("matchesSourceBytes") is True
    )


def _update_projection(observation: Mapping[str, Any]) -> bool:
    """Recognize the observed update preference independently of other groups."""

    view = observation.get("view")
    return isinstance(view, Mapping) and type(view.get("update_check")) is bool


def _scan_projection(observation: Mapping[str, Any]) -> bool:
    """Require the observed game-version, movement, and concurrency projection."""

    view = observation.get("view")
    return (
        isinstance(view, Mapping)
        and view.get("game_version") in {"auto", "Original", "NextGen"}
        and type(view.get("move_unsolved_logs")) is bool
        and type(view.get("max_concurrent_scans")) is int
        and view["max_concurrent_scans"] >= 0
    )


def _frontend_projection(observation: Mapping[str, Any]) -> bool:
    """Require complete typed window geometry before covering frontend carriers."""

    view = observation.get("view")
    geometry = view.get("main_tab") if isinstance(view, Mapping) else None
    return (
        isinstance(geometry, Mapping)
        and set(geometry) == {"maximized", "width", "height"}
        and type(geometry["maximized"]) is bool
        and type(geometry["width"]) is int
        and type(geometry["height"]) is int
    )


def _diagnostics(observation: Mapping[str, Any]) -> bool:
    """Recognize explicit ordered diagnostic codes, including an empty list."""

    diagnostics = observation.get("diagnostics")
    return isinstance(diagnostics, list) and all(
        isinstance(code, str) for code in diagnostics
    )


def _read_only(observation: Mapping[str, Any]) -> bool:
    """Require an observed unchanged installation tree after opening settings."""

    return observation.get("durableEffects") == {"treeUnchanged": True}


def _accepted_update(observation: Mapping[str, Any]) -> bool:
    """Recognize an accepted revision-anchored preview artifact."""

    preview = observation.get("preview")
    return (
        isinstance(preview, Mapping)
        and preview.get("status") == "accepted"
        and isinstance(preview.get("baseRevision"), str)
        and preview.get("diagnostics") == []
        and isinstance(preview.get("acceptedFields"), list)
    )


def _accepted_fields(observation: Mapping[str, Any]) -> bool:
    """Cover accepted field carriers only when actual artifact fields are present."""

    if not _accepted_update(observation):
        return False
    fields = observation["preview"]["acceptedFields"]
    return bool(fields) and all(
        isinstance(field, Mapping)
        and set(field) == {"fieldPath", "value"}
        and isinstance(field["fieldPath"], str)
        and type(field["value"]) in (bool, int)
        for field in fields
    )


def _rejected_update(observation: Mapping[str, Any]) -> bool:
    """Require explicit field/code/message diagnostics from a rejected preview."""

    preview = observation.get("preview")
    if not isinstance(preview, Mapping) or preview.get("status") != "rejected":
        return False
    diagnostics = preview.get("diagnostics")
    return (
        preview.get("acceptedFields") == []
        and preview.get("baseRevision") is None
        and isinstance(diagnostics, list)
        and bool(diagnostics)
        and all(
            isinstance(diagnostic, Mapping)
            and set(diagnostic) == {"fieldPath", "code", "message"}
            and (
                diagnostic["fieldPath"] is None
                or isinstance(diagnostic["fieldPath"], str)
            )
            and isinstance(diagnostic["code"], str)
            and isinstance(diagnostic["message"], str)
            for diagnostic in diagnostics
        )
    )


def _committed_update(observation: Mapping[str, Any]) -> bool:
    """Cover publication only after central raw-byte revision authentication."""

    commit = observation.get("commit")
    return (
        isinstance(commit, Mapping)
        and commit.get("status") == "committed"
        and commit.get("revision") == {"matchesPublishedBytes": True}
        and any("yamlNodes" in entry for entry in observation.get("finalTree", []))
    )


def _conflicting_update(observation: Mapping[str, Any]) -> bool:
    """Require the two observed revisions of an explicitly refused stale commit."""

    commit = observation.get("commit")
    return (
        isinstance(commit, Mapping)
        and commit.get("status") == "conflict"
        and isinstance(commit.get("expectedRevision"), str)
        and isinstance(commit.get("actualRevision"), str)
        and commit["expectedRevision"] != commit["actualRevision"]
    )


def _operation_effects(observation: Mapping[str, Any]) -> bool:
    """Require both real-tree checkpoints independently of a claimed outcome."""

    return all(
        isinstance(observation.get(key), list)
        for key in ("afterPreviewTree", "finalTree")
    )


def _operation_predicates() -> tuple[CoveragePredicate, ...]:
    """Bind the same observable contracts to ordinary and bootstrap actions."""

    predicates = []
    for action in ("user-settings.update",):
        for suffix, family, symbols, matches in (
            (
                "accepted-preview",
                "projection",
                (
                    "UserSettingsUpdate",
                    "UserSettingsUpdatePreview",
                    "AcceptedUserSettingsUpdate",
                ),
                _accepted_update,
            ),
            (
                "accepted-fields",
                "projection",
                ("UserSettingsUpdateField",),
                _accepted_fields,
            ),
            (
                "rejected-preview",
                "diagnostics",
                ("UserSettingsUpdatePreview", "UpdateDiagnostic"),
                _rejected_update,
            ),
            (
                "committed",
                "durable-effects",
                ("UserSettingsCommitOutcome",),
                _committed_update,
            ),
            (
                "conflict",
                "durable-effects",
                ("UserSettingsCommitOutcome",),
                _conflicting_update,
            ),
            ("tree-checkpoints", "durable-effects", (), _operation_effects),
        ):
            predicates.append(
                CoveragePredicate(
                    f"{action}.{suffix}",
                    "user-settings.update",
                    action,
                    family,
                    symbols,
                    matches,
                )
            )
    return tuple(predicates)


USER_SETTINGS_COVERAGE_POLICY = FamilyCoveragePolicy(
    family_id="user-settings",
    predicates=(
        *_operation_predicates(),
        CoveragePredicate(
            "user-settings.source",
            "user-settings.open",
            "user-settings.open",
            "source",
            (
                "UserSettings",
                "SettingsSource",
                "SourceLocation",
                "DocumentClassification",
                "CommitEligibility",
                "Revision",
            ),
            _source,
        ),
        CoveragePredicate(
            "user-settings.update-preferences",
            "user-settings.open",
            "user-settings.open",
            "projection",
            ("UpdatePreferences",),
            _update_projection,
        ),
        CoveragePredicate(
            "user-settings.scan-settings",
            "user-settings.open",
            "user-settings.open",
            "projection",
            ("CrashLogScanSettings",),
            _scan_projection,
        ),
        CoveragePredicate(
            "user-settings.frontend-state",
            "user-settings.open",
            "user-settings.open",
            "projection",
            ("FrontendState", "WindowGeometry"),
            _frontend_projection,
        ),
        CoveragePredicate(
            "user-settings.diagnostics",
            "user-settings.open",
            "user-settings.open",
            "diagnostics",
            ("Diagnostic",),
            _diagnostics,
        ),
        CoveragePredicate(
            "user-settings.read-only",
            "user-settings.open",
            "user-settings.open",
            "durable-effects",
            (),
            _read_only,
        ),
    ),
)
