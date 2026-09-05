"""Execute User Settings open, preview, and commit plans through the public PyO3 API."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from collections.abc import Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

RUN_PLAN_ENV = "CLASSIC_CONFORMANCE_RUN_PLAN"
OUTPUT_ENV = "CLASSIC_CONFORMANCE_OUTPUT"
FAMILY_ID = "user-settings"


class RunnerContractError(RuntimeError):
    """Report an invalid private runner invocation or input-only plan."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    """Require one JSON object and retain its location in any error."""
    if not isinstance(value, Mapping):
        raise RunnerContractError(f"{label} must be an object")
    return value


def _array(value: object, label: str) -> list[Any]:
    """Require one JSON array, excluding strings and mappings."""
    if not isinstance(value, list):
        raise RunnerContractError(f"{label} must be an array")
    return value


def _string(value: object, label: str) -> str:
    """Require one nonempty JSON string with an attributed error."""
    if not isinstance(value, str) or not value:
        raise RunnerContractError(f"{label} must be a non-empty string")
    return value


def _load_plan(path: Path) -> Mapping[str, Any]:
    """Read only the centrally supplied plan and validate this participant's identity."""
    try:
        plan = _mapping(json.loads(path.read_text(encoding="utf-8")), "run plan")
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RunnerContractError(
            f"cannot read conformance run plan: {error}"
        ) from error
    if plan.get("familyId") != FAMILY_ID:
        raise RunnerContractError(f"run plan family must be {FAMILY_ID}")
    if plan.get("participant") != {
        "id": "python",
        "role": "semantic-adapter",
        "executionInstanceId": "python",
    }:
        raise RunnerContractError(
            "run plan is not the Python semantic-adapter invocation"
        )
    scenarios = _array(plan.get("scenarios"), "run plan scenarios")
    if not scenarios:
        raise RunnerContractError("run plan must contain scenarios")
    for scenario in scenarios:
        if "expected" in _mapping(scenario, "run plan scenario"):
            raise RunnerContractError(
                "input-only run plan must not contain expectations"
            )
    return plan


def _runtime_path(root: Path, raw_path: object) -> Path:
    """Resolve a canonical relative fixture destination inside the fresh runtime root."""
    value = _string(raw_path, "installationData.path")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        posix.is_absolute()
        or windows.drive
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise RunnerContractError(
            "installationData.path must stay beneath the runtime root"
        )
    path = (root / Path(*posix.parts)).resolve(strict=False)
    if not path.is_relative_to(root):
        raise RunnerContractError("installationData.path escapes the runtime root")
    return path


def _materialize_inputs(
    plan: Mapping[str, Any], scenario: Mapping[str, Any], root: Path
) -> Mapping[str, Any]:
    """Copy exclusively scenario-declared fixtures into the private installation."""
    inputs = _mapping(scenario.get("input"), "scenario input")
    fixtures = _mapping(plan.get("fixtures"), "run plan fixtures")
    references = _array(scenario.get("fixtureRefs"), "scenario fixtureRefs")
    for raw_item in _array(inputs.get("installationData"), "installationData"):
        item = _mapping(raw_item, "installationData item")
        reference = _string(item.get("fixtureRef"), "installationData.fixtureRef")
        if reference not in references:
            raise RunnerContractError(
                "installationData fixture is not declared by the scenario"
            )
        source = Path(_string(fixtures.get(reference), f"fixture {reference}"))
        destination = _runtime_path(root, item.get("path"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return inputs


def _tree_snapshot(root: Path) -> dict[str, bytes | None]:
    """Capture all directory entries and exact file bytes as durable effect evidence."""
    snapshot = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RunnerContractError(
                "runtime tree contains an unexpected symbolic link"
            )
        snapshot[path.relative_to(root).as_posix()] = (
            None if path.is_dir() else path.read_bytes()
        )
    return snapshot


def _selected_view(snapshot: Any, fields: object) -> dict[str, Any]:
    """Project requested common fields directly from the public typed binding getters."""
    scan = snapshot.crash_log_scan_settings
    geometry = snapshot.frontend_state.window_geometry
    available = {
        "update_check": snapshot.update_preferences.update_check,
        "game_version": scan.game_version_selection,
        "move_unsolved_logs": scan.move_unsolved_logs,
        "max_concurrent_scans": scan.max_concurrent_scans,
        "fcx_mode": scan.fcx_mode,
        "simplify_logs": scan.simplify_logs,
        "show_formid_values": scan.formid_value_lookup,
        "formid_databases": scan.formid_databases,
        "main_tab_width": geometry.main_tab.width,
        "main_tab_maximized": geometry.main_tab.maximized,
        "custom_scan_folder": scan.custom_scan_input,
        "mods_folder": snapshot.game_setup_settings.mods_root,
    }
    for tab in ("main_tab", "backups_tab", "articles_tab", "results_tab"):
        public_geometry = getattr(geometry, tab)
        available[tab] = {
            "maximized": public_geometry.maximized,
            "width": public_geometry.width,
            "height": public_geometry.height,
        }
    selected = {}
    for field in _array(fields, "observationFields"):
        name = _string(field, "observationFields item")
        if name not in available:
            raise RunnerContractError(f"unsupported observation field: {name}")
        selected[name] = available[name]
    return selected


def _execute_scenario(
    plan: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    """Dispatch public operations or open once and compare source-byte evidence."""
    import classic_user_settings

    action = scenario.get("action")
    if action == "user-settings.update":
        return _execute_operation(plan, scenario)
    if action != "user-settings.open":
        raise RunnerContractError("unsupported User Settings action")
    with tempfile.TemporaryDirectory(
        prefix="classic-user-settings-conformance-"
    ) as temporary:
        root = Path(temporary).resolve()
        inputs = _materialize_inputs(plan, scenario, root)
        before = _tree_snapshot(root)
        snapshot = classic_user_settings.open_user_settings(str(root))
        after = _tree_snapshot(root)
        source_path = snapshot.source_path
        relative = None
        source_bytes = None
        if source_path is not None:
            try:
                relative = Path(source_path).resolve().relative_to(root).as_posix()
            except ValueError as error:
                raise RunnerContractError(
                    "public source path escapes the runtime root"
                ) from error
            source_bytes = before.get(relative)
            if not isinstance(source_bytes, bytes):
                raise RunnerContractError(
                    "public source path was not a pre-open fixture file"
                )
        # Compare against pre-open bytes so rewriting the source cannot make false evidence agree.
        expected_revision = (
            "missing"
            if source_bytes is None
            else f"sha256:{hashlib.sha256(source_bytes).hexdigest()}"
        )
        revision = snapshot.revision
        if revision == "missing":
            revision_kind = "missing"
        elif revision.startswith("sha256:"):
            revision_kind = "sha256"
        else:
            raise RunnerContractError(
                "public revision has an unsupported identity kind"
            )
        original = snapshot.original_content
        return {
            "source": {
                "location": snapshot.source_location,
                "path": None if relative is None else {"path": relative},
                "classification": snapshot.classification,
            },
            "commitEligibility": snapshot.commit_eligibility,
            "diagnostics": [diagnostic.code for diagnostic in snapshot.diagnostics],
            "view": _selected_view(snapshot, inputs.get("observationFields")),
            "durableEffects": {"treeUnchanged": before == after},
            "revision": {
                "kind": revision_kind,
                "matchesSourceBytes": revision == expected_revision,
            },
            "originalContent": {
                "present": original is not None,
                "matchesSourceBytes": original == source_bytes,
            },
        }


def _requested_update(fields: object) -> Any:
    """Translate input selectors into public setters, leaving value policy in Rust."""
    import classic_user_settings

    update = classic_user_settings.UserSettingsUpdate()
    for path, value in _mapping(fields, "requestedUpdate").items():
        if path == "/CLASSIC_Settings/Update Check":
            if not isinstance(value, bool):
                raise RunnerContractError("Update Check input must be a boolean")
            update.set_update_check(value)
        elif path == "/CLASSIC_Settings/Max Concurrent Scans":
            if not isinstance(value, int) or isinstance(value, bool):
                raise RunnerContractError(
                    "Max Concurrent Scans input must be an integer"
                )
            update.set_max_concurrent_scans(value)
        else:
            raise RunnerContractError(f"unsupported requested field: {path}")
    return update


def _install_external_edit(
    plan: Mapping[str, Any], scenario: Mapping[str, Any], root: Path, raw_edit: object
) -> None:
    """Materialize one declared caller edit after preview without interpreting its bytes."""
    edit = _mapping(raw_edit, "externalEdit")
    reference = _string(edit.get("fixtureRef"), "externalEdit.fixtureRef")
    references = _array(scenario.get("fixtureRefs"), "scenario fixtureRefs")
    if reference not in references:
        raise RunnerContractError(
            "external edit fixture is not declared by the scenario"
        )
    fixtures = _mapping(plan.get("fixtures"), "run plan fixtures")
    source = Path(_string(fixtures.get(reference), f"fixture {reference}"))
    destination = _runtime_path(root, edit.get("path"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _durable_tree(root: Path) -> list[dict[str, Any]]:
    """Observe every durable entry and exact bytes, distinguishing absent and empty roots."""
    if root.is_symlink():
        raise RunnerContractError("runtime root must be a regular directory")
    if not root.exists():
        return []
    if not root.is_dir():
        raise RunnerContractError("runtime root must be a regular directory")
    result: list[dict[str, Any]] = [{"path": {"path": "."}, "kind": "directory"}]
    for path, content in sorted(_tree_snapshot(root).items()):
        if content is None:
            result.append({"path": {"path": path}, "kind": "directory"})
        else:
            result.append(
                {"path": {"path": path}, "kind": "file", "bytesHex": content.hex()}
            )
    return result


def _execute_operation(
    plan: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    """Preview and optionally commit through public APIs, preserving each durable phase."""
    import classic_user_settings

    with tempfile.TemporaryDirectory(
        prefix="classic-user-settings-operation-"
    ) as temporary:
        # An absent installation is an input: previews must not silently create its root.
        root = Path(temporary).resolve() / "installation"
        inputs = _mapping(scenario.get("input"), "scenario input")
        root_exists = inputs.get("installationRootExists")
        if not isinstance(root_exists, bool):
            raise RunnerContractError("installationRootExists must be a boolean")
        if root_exists:
            root.mkdir()
        inputs = _materialize_inputs(plan, scenario, root)
        commit_requested = inputs.get("commit")
        if not isinstance(commit_requested, bool):
            raise RunnerContractError("commit must be a boolean")
        if "externalEdit" not in inputs:
            raise RunnerContractError("externalEdit must be supplied explicitly")
        preview_mode = inputs.get("previewMode")
        if preview_mode not in {"update", "bootstrap"}:
            raise RunnerContractError("previewMode must be update or bootstrap")
        update = _requested_update(inputs.get("requestedUpdate"))
        snapshot = classic_user_settings.open_user_settings(str(root))
        preview = (
            snapshot.preview_bootstrap(update)
            if preview_mode == "bootstrap"
            else snapshot.preview_update(update)
        )
        after_preview = _durable_tree(root)
        if inputs.get("externalEdit") is not None:
            _install_external_edit(plan, scenario, root, inputs.get("externalEdit"))
        commit: dict[str, Any] = {
            "status": "not-attempted",
            "revision": None,
            "expectedRevision": None,
            "actualRevision": None,
        }
        if commit_requested and preview.accepted:
            outcome = preview.commit(str(root))
            commit = {
                "status": outcome.status,
                "revision": outcome.revision,
                "expectedRevision": outcome.expected_revision,
                "actualRevision": outcome.actual_revision,
            }
        return {
            "preview": {
                "status": "accepted" if preview.accepted else "rejected",
                "baseRevision": preview.base_revision,
                "acceptedFields": [
                    {"fieldPath": field.canonical_path, "value": field.value}
                    for field in preview.fields
                ],
                "diagnostics": [
                    {
                        "fieldPath": diagnostic.field_path,
                        "code": diagnostic.code,
                        "message": diagnostic.message,
                    }
                    for diagnostic in preview.diagnostics
                ],
            },
            "afterPreviewTree": after_preview,
            "commit": commit,
            "finalTree": _durable_tree(root),
        }


def _scenario_receipt(plan: Mapping[str, Any], raw_scenario: object) -> dict[str, Any]:
    """Preserve failed scenario executions as explicit fresh receipt evidence."""
    scenario = _mapping(raw_scenario, "run plan scenario")
    result = {
        "id": _string(scenario.get("id"), "scenario id"),
        "capabilityIds": _array(
            scenario.get("capabilityIds"), "scenario capabilityIds"
        ),
        "executionStatus": "completed",
        "observation": {},
        "failure": None,
    }
    try:
        result["observation"] = _execute_scenario(plan, scenario)
    except Exception as error:  # noqa: BLE001 - failed adapter cases still owe a receipt.
        result["executionStatus"] = "failed"
        result["failure"] = {
            "kind": "python-runner-error",
            "message": f"{type(error).__name__}: {error}",
        }
    return result


def _build_receipt(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Copy central envelope identities and append actual participant observations."""
    return {
        **{
            key: plan.get(key)
            for key in (
                "schemaVersion",
                "familyId",
                "familyVersion",
                "expectationDigest",
            )
        },
        "invocation": dict(_mapping(plan.get("invocation"), "run plan invocation")),
        "participant": dict(_mapping(plan.get("participant"), "run plan participant")),
        "runner": {
            "id": "classic-python-conformance",
            "version": 1,
            "platform": {"win32": "windows", "darwin": "macos"}.get(
                sys.platform, "linux"
            ),
            "toolchain": sys.implementation.name,
        },
        "scenarios": [
            _scenario_receipt(plan, scenario)
            for scenario in _array(plan.get("scenarios"), "run plan scenarios")
        ],
    }


def _publish_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    """Atomically publish fresh canonical JSON without accepting stale output reuse."""
    if path.exists():
        raise RunnerContractError("conformance receipt destination already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    payload = json.dumps(
        receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    try:
        with temporary.open("xb") as output:
            output.write(payload.encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    """Execute an environment-only invocation and publish its sibling receipt file."""
    try:
        plan_path = Path(_string(os.environ.get(RUN_PLAN_ENV), RUN_PLAN_ENV)).resolve(
            strict=True
        )
        output_path = Path(_string(os.environ.get(OUTPUT_ENV), OUTPUT_ENV)).resolve(
            strict=False
        )
        if output_path.parent != plan_path.parent:
            raise RunnerContractError(
                "conformance receipt must be a sibling of its immutable run plan"
            )
        _publish_receipt(output_path, _build_receipt(_load_plan(plan_path)))
    except (OSError, RunnerContractError) as error:
        print(f"classic-python-conformance: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
