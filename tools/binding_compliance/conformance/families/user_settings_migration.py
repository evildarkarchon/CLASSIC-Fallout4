"""Independent migration oracle compilation and authenticated byte normalization."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from ..compare import NormalizationError, exact_differences
from ..coverage import CoveragePredicate

CANONICAL = "CLASSIC Settings.yaml"
LOCK = CANONICAL + ".commit.lock"
PROPOSED_REVISION = "<verified-proposed-revision>"


def _bytes(raw: object) -> bytes:
    """Require canonical raw hexadecimal evidence instead of runner assertions."""
    if not isinstance(raw, str) or re.fullmatch(r"(?:[0-9a-f]{2})*", raw) is None:
        raise ValueError("migration bytes must be lowercase hexadecimal")
    return bytes.fromhex(raw)


def _changes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize YAML review fragments while preserving ordered typed transitions."""
    from .user_settings import _yaml_nodes

    result = copy.deepcopy(rows)
    for row in result:
        if row["kind"] not in {"schema_version_transition", "location_transition"}:
            for key in ("before", "after"):
                if row[key] is not None:
                    row[key] = _yaml_nodes(row[key].encode("utf-8"))
    return result


def _tree(
    files: Mapping[str, bytes | dict[str, Any]], directories=()
) -> list[dict[str, Any]]:
    """Build an independent complete tree including parents and retained empty directories."""
    dirs = {".", *directories}
    for path in files:
        dirs.update(str(parent) for parent in PurePosixPath(path).parents)
    entries = {path: {"path": {"path": path}, "kind": "directory"} for path in dirs}
    for path, value in files.items():
        entries[path] = {
            "path": {"path": path},
            "kind": "file",
            **(
                {"bytesHex": value.hex()}
                if isinstance(value, bytes)
                else {"proposedYamlNodes": value}
            ),
        }
    return [entries[path] for path in sorted(entries)]


def _endpoint(location: str, version: object) -> dict[str, Any]:
    """Describe one authored version/location endpoint."""
    return {"location": location, "schemaVersion": version}


def _input(
    spec: Mapping[str, Any], case: Mapping[str, Any], fixtures: Mapping[str, str]
) -> tuple[dict, list]:
    """Compile input-only controls and reject undeclared oracle fixture dependencies."""
    fixture_ids = {value: key for key, value in fixtures.items()}
    installation = (
        []
        if case["source_fixture"] is None
        else [
            {
                "fixtureRef": fixture_ids[case["source_fixture"]],
                "path": case["source_path"],
            }
        ]
    )
    references = [item["fixtureRef"] for item in installation]
    for key in ("before_apply", "before_restore"):
        control = spec[key]
        if control is None:
            continue
        kind = control.get("kind")
        fields = {
            "external-edit": {"kind", "fixtureRef", "path"},
            "tamper-backup": {"kind", "fixtureRef"},
            "remove-backup": {"kind"},
            "block-backup-directory": {"kind"},
        }.get(kind)
        if fields is None or set(control) != fields:
            raise ValueError("invalid migration interference control")
        if kind == "external-edit" and control["path"] not in {
            CANONICAL,
            "CLASSIC Data/" + CANONICAL,
        }:
            raise ValueError("migration edit must select a supported settings location")
        if "fixtureRef" in control:
            reference = control["fixtureRef"]
            if reference not in fixtures:
                raise ValueError("migration interference requires a declared fixture")
            if reference not in references:
                references.append(reference)
    if any(type(spec[key]) is not bool for key in ("apply", "restore")):
        raise ValueError("migration approval controls must be booleans")
    return {
        "installationData": installation,
        "apply": spec["apply"],
        "restore": spec["restore"],
        "beforeApply": spec["before_apply"],
        "beforeRestore": spec["before_restore"],
    }, references


def compile_migrations(
    pack: dict[str, Any], oracle: Mapping[str, Any], fixture_root: Path
) -> None:
    """Compile exactly the independently authored migration cases into public observations.

    Expected documents and review rows come from the shared compatibility corpus;
    adapters receive only fixture references and explicit caller actions.
    """
    from .user_settings import _oracle_fixture, _revision, _yaml_nodes

    specs = {item["id"]: item for item in oracle.get("migration_scenarios", [])}
    if len(specs) != len(oracle.get("migration_scenarios", [])):
        raise ValueError("duplicate migration oracle scenario")
    scenarios = [
        item for item in pack["scenarios"] if item["action"] == "user-settings.migrate"
    ]
    selected = [item["expected"].get("migrationScenario") for item in scenarios]
    if len(selected) != len(set(selected)) or set(selected) != set(specs):
        raise ValueError(
            "User Settings pack must cover every migration oracle scenario exactly once"
        )
    if any(
        item["action"]
        not in {"user-settings.open", "user-settings.update", "user-settings.migrate"}
        for item in pack["scenarios"]
    ):
        raise ValueError("unsupported User Settings scenario action")

    def fixture(name: str) -> bytes:
        """Read one contained independent fixture dependency."""
        return _oracle_fixture(fixture_root, name).read_bytes()

    for scenario in scenarios:
        if set(scenario["expected"]) != {"migrationScenario"}:
            raise ValueError("migration expectations must reference the shared oracle")
        spec = specs[scenario["expected"]["migrationScenario"]]
        case = oracle["migration_cases"][spec["case"]]
        inputs, refs = _input(spec, case, pack["fixtures"])
        normalization = {
            "rootRelativePaths": True,
            "unorderedPaths": [],
            "excludedPaths": [],
        }
        if "optional_empty_files" in spec:
            normalization["optionalEmptyFiles"] = spec["optional_empty_files"]
        if (
            exact_differences(inputs, scenario["input"])
            or scenario["fixtureRefs"] != refs
            or scenario["capabilityIds"] != ["user-settings.migrate"]
            or exact_differences(normalization, scenario["normalization"])
        ):
            raise ValueError("migration input does not match its independent oracle")
        original = (
            None if case["source_fixture"] is None else fixture(case["source_fixture"])
        )
        files = {} if original is None else {case["source_path"]: original}
        initial = _tree(files)
        planned = case["status"] == "planned"
        source = _endpoint(
            "legacy"
            if case["source_path"].startswith("CLASSIC Data/")
            else "canonical",
            case.get("source_version"),
        )
        target = _endpoint("canonical", {"major": 1, "minor": 0})
        proposed = _yaml_nodes(fixture(case["expected_document"])) if planned else None
        plan = (
            None
            if not planned
            else {
                "required": case["required"],
                "baseRevision": _revision(original),
                "source": source,
                "target": target,
                "changes": _changes(case["changes"]),
                "originalHex": original.hex(),
                "proposedYamlNodes": proposed,
            }
        )
        planning = {
            "status": case["status"],
            "diagnostics": case["diagnostics"],
            "plan": plan,
        }
        apply = {
            "status": spec["apply_status"],
            "expectedRevision": None,
            "actualRevision": None,
            "errorCode": None,
            "receipt": None,
        }
        restore = {
            "status": spec["restore_status"],
            "revision": None,
            "expectedRevision": None,
            "actualRevision": None,
            "errorCode": None,
        }

        def interfere(
            control: Mapping[str, Any] | None, backup: str | None, files: dict
        ) -> None:
            """Apply only authored external changes to the expected tree."""
            if control is None:
                return
            kind = control["kind"]
            if kind == "block-backup-directory":
                files["CLASSIC Backup"] = b"blocked"
            elif kind == "remove-backup":
                del files[backup]
            else:
                path = backup if kind == "tamper-backup" else control["path"]
                files[path] = fixture(pack["fixtures"][control["fixtureRef"]])

        backup = None
        if planned and spec["apply"]:
            interfere(spec["before_apply"], None, files)
            if apply["status"] == "conflict":
                apply.update(
                    expectedRevision=_revision(original),
                    actualRevision=_revision(
                        files.get(CANONICAL, files.get(case["source_path"]))
                    ),
                )
            else:
                files[LOCK] = b""
                if apply["status"] == "error":
                    apply["errorCode"] = spec["error_code"]
                else:
                    backup = (
                        "CLASSIC Backup/User Settings/Migrations/"
                        + _revision(original).removeprefix("sha256:")
                        + ".yaml"
                    )
                    files[backup] = original
                    files[CANONICAL] = proposed
                    apply["receipt"] = {
                        "sourcePath": {"path": case["source_path"]},
                        "destinationPath": {"path": CANONICAL},
                        "backupPath": {"path": backup},
                        "source": source,
                        "target": target,
                        "backupRevision": _revision(original),
                        "publishedRevision": PROPOSED_REVISION,
                    }
        after_apply = _tree(files)
        retained_dirs = [
            entry["path"]["path"]
            for entry in after_apply
            if entry["kind"] == "directory"
        ]
        if backup is not None and spec["restore"]:
            interfere(spec["before_restore"], backup, files)
            if restore["status"] == "restored":
                files[case["source_path"]] = original
                if source["location"] == "legacy":
                    del files[CANONICAL]
                restore["revision"] = _revision(original)
            elif restore["status"] == "error":
                restore["errorCode"] = spec["error_code"]
            else:
                edit_path = spec["before_restore"]["path"]
                restore.update(
                    expectedRevision=PROPOSED_REVISION
                    if edit_path == CANONICAL
                    else _revision(original),
                    actualRevision=_revision(files[edit_path]),
                )
        scenario["expected"] = {
            "planning": planning,
            "repeatedPlanning": {"matchesPlanning": True},
            "reversedPlan": {"verifiedInverse": True} if planned else None,
            "roundTripPlan": {"matchesPlanning": True} if planned else None,
            "afterPlanningTree": initial,
            "apply": apply,
            "afterApplyTree": after_apply,
            "restore": restore,
            "finalTree": _tree(files, retained_dirs),
        }


def normalize_migration(
    expected: Mapping[str, Any], actual: Mapping[str, Any]
) -> dict[str, Any]:
    """Authenticate exact plan/reversal/publication identities before YAML normalization.

    Only YAML representation, verified proposed revision tokens, and an optional
    empty conflict coordination file vary across adapters. Backups, original and
    restored bytes, errors, tree contents, and all other fields compare exactly.
    """
    from .user_settings import _revision, _yaml_nodes

    result = copy.deepcopy(dict(actual))
    try:
        planning = result["planning"]
        if exact_differences(planning, result["repeatedPlanning"]):
            raise ValueError("migration planning is not deterministic")
        result["repeatedPlanning"] = {"matchesPlanning": True}
        plan = planning["plan"]
        proposed = None
        proposed_revision = None
        if plan is not None:
            original = _bytes(plan["originalHex"])
            proposed = _bytes(plan["proposedHex"])
            if plan["baseRevision"] != _revision(original):
                raise ValueError(
                    "migration base revision does not match retained original bytes"
                )
            proposed_revision = _revision(proposed)
            inverse = copy.deepcopy(plan)
            inverse.update(
                source=plan["target"],
                target=plan["source"],
                baseRevision=proposed_revision,
                originalHex=plan["proposedHex"],
                proposedHex=plan["originalHex"],
            )
            inverse["changes"] = [
                {
                    **row,
                    "sourcePath": row["targetPath"],
                    "targetPath": row["sourcePath"],
                    "before": row["after"],
                    "after": row["before"],
                }
                for row in reversed(plan["changes"])
            ]
            if exact_differences(inverse, result["reversedPlan"]):
                raise ValueError("migration reversal is not the exact inverse")
            if exact_differences(plan, result["roundTripPlan"]):
                raise ValueError("migration double reversal changed the plan")
            result["reversedPlan"] = {"verifiedInverse": True}
            result["roundTripPlan"] = {"matchesPlanning": True}
            plan["changes"] = _changes(plan["changes"])
            del plan["proposedHex"]
            plan["proposedYamlNodes"] = _yaml_nodes(proposed)
        receipt = result["apply"]["receipt"]
        if receipt is not None:
            if proposed is None or receipt["publishedRevision"] != proposed_revision:
                raise ValueError(
                    "migration published revision does not match the approved proposal"
                )
            receipt["publishedRevision"] = PROPOSED_REVISION
        if expected["restore"]["expectedRevision"] == PROPOSED_REVISION:
            if result["restore"]["expectedRevision"] != proposed_revision:
                raise ValueError(
                    "restore conflict is not anchored to the published revision"
                )
            result["restore"]["expectedRevision"] = PROPOSED_REVISION
        for checkpoint in ("afterPlanningTree", "afterApplyTree", "finalTree"):
            tree = result[checkpoint]
            if not isinstance(tree, list):
                raise TypeError("migration checkpoint must be a tree array")
            expected_entries = {
                entry["path"]["path"]: entry for entry in expected[checkpoint]
            }
            for entry in tree:
                authored = expected_entries.get(entry["path"]["path"], {})
                if "proposedYamlNodes" in authored:
                    if (
                        set(entry) != {"path", "kind", "bytesHex"}
                        or entry["kind"] != "file"
                    ):
                        raise ValueError(
                            "published migration requires raw regular-file byte evidence"
                        )
                    if _bytes(entry["bytesHex"]) != proposed:
                        raise ValueError(
                            "published migration bytes differ from the approved proposal"
                        )
                    del entry["bytesHex"]
                    entry["proposedYamlNodes"] = _yaml_nodes(proposed)
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise NormalizationError(str(error), "$.planning") from error
    return result


def migration_predicates() -> tuple[CoveragePredicate, ...]:
    """Grant coverage only to centrally compared observations of actual public outcomes."""

    def planned(observation: Mapping[str, Any]) -> bool:
        """Recognize a centrally authenticated plan and its exact inverse."""
        return observation.get("planning", {}).get(
            "status"
        ) == "planned" and observation.get("reversedPlan") == {"verifiedInverse": True}

    def applied(observation: Mapping[str, Any]) -> bool:
        """Recognize an applied receipt with observed durable checkpoints."""
        return observation.get("apply", {}).get("status") == "applied" and bool(
            observation.get("afterApplyTree")
        )

    def restored(observation: Mapping[str, Any]) -> bool:
        """Recognize explicit restoration through an actual retained receipt."""
        return observation.get("restore", {}).get("status") == "restored" and bool(
            observation.get("finalTree")
        )

    def failed(observation: Mapping[str, Any]) -> bool:
        """Recognize a normalized stable operational error from a public operation."""
        return any(
            observation.get(stage, {}).get("status") == "error"
            for stage in ("apply", "restore")
        )

    def unsupported(observation: Mapping[str, Any]) -> bool:
        """Recognize explicit unsupported planning diagnostics."""
        return observation.get("planning", {}).get("status") == "unsupported" and bool(
            observation["planning"]["diagnostics"]
        )

    return tuple(
        CoveragePredicate(
            "user-settings.migrate." + suffix,
            "user-settings.migrate",
            "user-settings.migrate",
            family,
            symbols,
            predicate,
        )
        for suffix, family, symbols, predicate in (
            (
                "plan",
                "projection",
                (
                    "MigrationPlanningOutcome",
                    "UserSettingsMigrationPlan",
                    "MigrationEndpoint",
                    "MigrationChange",
                    "MigrationChangeKind",
                ),
                planned,
            ),
            (
                "apply",
                "durable-effects",
                ("UserSettingsMigrationApplyOutcome", "UserSettingsMigrationReceipt"),
                applied,
            ),
            (
                "restore",
                "durable-effects",
                ("UserSettingsMigrationRestoreOutcome",),
                restored,
            ),
            ("error", "diagnostics", ("UserSettingsMigrationError",), failed),
            ("unsupported", "diagnostics", ("MigrationDiagnostic",), unsupported),
        )
    )
