"""Execute Crash Log Scan Launch plans through the public ``classic_scanlog`` facade.

The launcher hands this runner an input-only plan. Each scenario launches through
``ScanRunLaunch`` in a fresh Installation Root and records only what the Python
surface reports; comparison against the pack happens centrally (ADR-0008).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

RUN_PLAN_ENV = "CLASSIC_CONFORMANCE_RUN_PLAN"
OUTPUT_ENV = "CLASSIC_CONFORMANCE_OUTPUT"
FAMILY_ID = "crash-log-scan-launch"
SETTINGS_FILE = "CLASSIC Settings.yaml"
INSTALLATION_ROOT_PLACEHOLDER = "{{installationRoot}}"


class RunnerContractError(RuntimeError):
    """Report an invalid private runner invocation or input-only plan."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    """Require one JSON object."""
    if not isinstance(value, Mapping):
        raise RunnerContractError(f"{label} must be an object")
    return value


def _array(value: object, label: str) -> list[Any]:
    """Require one JSON array."""
    if not isinstance(value, list):
        raise RunnerContractError(f"{label} must be an array")
    return value


def _string(value: object, label: str) -> str:
    """Require one non-empty JSON string."""
    if not isinstance(value, str) or not value:
        raise RunnerContractError(f"{label} must be a non-empty string")
    return value


def _load_plan(path: Path) -> Mapping[str, Any]:
    """Read the centrally supplied plan and validate this participant's identity."""
    plan = _mapping(json.loads(path.read_text(encoding="utf-8")), "run plan")
    if plan.get("familyId") != FAMILY_ID:
        raise RunnerContractError(f"run plan family must be {FAMILY_ID}")
    if plan.get("participant") != {
        "id": "python",
        "role": "semantic-adapter",
        "executionInstanceId": "python",
    }:
        raise RunnerContractError("run plan is not the Python semantic-adapter invocation")
    for scenario in _array(plan.get("scenarios"), "run plan scenarios"):
        if "expected" in _mapping(scenario, "run plan scenario"):
            raise RunnerContractError("input-only run plan must not contain expectations")
    return plan


def _beneath(root: Path, relative: str) -> Path:
    """Join a scenario-supplied relative path that must stay beneath the root."""
    parts = PurePosixPath(relative).parts
    if (
            "\\" in relative
            or ":" in relative
            or not parts
            or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise RunnerContractError(f"{relative} must stay beneath the Installation Root")
    return root.joinpath(*parts)


def _root_relative(root: Path, value: str | None) -> str | None:
    """Render a reported path relative to the Installation Root; the root itself is ``.``."""
    if value is None:
        return None
    relative = Path(value).relative_to(root)
    text = relative.as_posix()
    return "." if text in {"", "."} else text


def _overrides(scanlog: Any, shared: Any, value: Mapping[str, Any], root: Path) -> Any:
    """Build the facade's override object from the scenario's overrides."""
    arguments: dict[str, Any] = {}
    if "game" in value:
        arguments["game"] = getattr(shared.GameId, _string(value["game"], "game"))
    if "gameVersion" in value:
        arguments["game_version"] = _string(value["gameVersion"], "gameVersion")
    if "scanPath" in value:
        arguments["scan_path"] = str(_beneath(root, _string(value["scanPath"], "scanPath")))
    if "maxConcurrent" in value:
        arguments["max_concurrent"] = value["maxConcurrent"]
    if value.get("showFormidValues") is True:
        arguments["show_formid_values"] = True
    if value.get("simplifyLogs") is True:
        arguments["simplify_logs"] = True
    if value.get("fcxMode") is True:
        arguments["fcx_mode"] = True
    return scanlog.ScanRunLaunchOverrides(**arguments)


def _installation_root_fixture(fixture: str, root: Path) -> str:
    """Replace the fixture's ``{{installationRoot}}`` placeholder with this run's root.

    The root is written with ``/`` separators so it reads the same inside any YAML
    quoting; both separators name the same folders on Windows.
    """
    return fixture.replace(INSTALLATION_ROOT_PLACEHOLDER, root.as_posix())


def _setup_context_view(context: Any, root: Path) -> dict[str, Any] | None:
    """Project the FCX setup facts root-relatively, or ``None`` when FCX Mode is off."""
    if context is None:
        return None
    return {
        "gameRoot": _root_relative(root, context.game_root),
        "docsRoot": _root_relative(root, context.docs_root),
        "gameExePath": _root_relative(root, context.game_exe_path),
        "xseLogPath": _root_relative(root, context.xse_log_path),
    }


def _request_view(launch: Any, root: Path) -> dict[str, Any]:
    """Project the launched request through the facade's read-only properties."""
    inputs = launch.targeted_inputs
    return {
        "intent": launch.intent,
        "game": launch.game.as_str(),
        "gameVersion": launch.game_version,
        "showFormidValues": launch.show_formid_values,
        "simplifyLogs": launch.simplify_logs,
        "formidDatabasePaths": [path.replace("\\", "/") for path in launch.formid_database_paths],
        "unsolvedLogsDestination": _root_relative(root, launch.unsolved_logs_destination),
        "maxConcurrent": launch.max_concurrent,
        "baseDirectory": _root_relative(root, launch.base_directory),
        "customScanDirectory": _root_relative(root, launch.custom_scan_directory),
        "configuredDocumentsRoot": _root_relative(root, launch.configured_documents_root),
        "unsolvedLogs": launch.unsolved_logs,
        "targetedInputs": None
        if inputs is None
        else [_root_relative(root, path) for path in inputs],
        "fcxEnabled": launch.fcx_enabled,
        "setupContext": _setup_context_view(launch.setup_context, root),
    }


def _execute_scenario(plan: Mapping[str, Any], scenario: Mapping[str, Any]) -> dict[str, Any]:
    """Launch one scenario in a fresh Installation Root and observe the outcome."""
    import classic_scanlog
    import classic_shared

    inputs = _mapping(scenario.get("input"), "scenario input")
    fixtures = _mapping(plan.get("fixtures"), "run plan fixtures")
    reference = _string(inputs.get("settingsFixtureRef"), "settingsFixtureRef")
    if reference not in _array(scenario.get("fixtureRefs"), "scenario fixtureRefs"):
        raise RunnerContractError("settings fixture is not declared by the scenario")
    with tempfile.TemporaryDirectory(prefix="classic-scan-launch-") as raw_root:
        root = Path(raw_root)
        settings = root / SETTINGS_FILE
        fixture = Path(_string(fixtures.get(reference), "settings fixture"))
        settings.write_bytes(
            _installation_root_fixture(fixture.read_text(encoding="utf-8"), root).encode("utf-8")
        )
        before = settings.read_bytes()
        # Scenario files (game executables, XSE logs) are empty files beneath the root.
        for item in _array(inputs.get("files", []), "files"):
            path = _beneath(root, _string(item, "file"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"")
        overrides = _overrides(
            classic_scanlog,
            classic_shared,
            _mapping(inputs.get("overrides"), "overrides"),
            root,
        )
        intent = _string(inputs.get("intent"), "intent")
        try:
            if intent == "standard":
                launch = classic_scanlog.ScanRunLaunch.standard(str(root), overrides)
            elif intent == "targeted":
                targeted = [
                    str(_beneath(root, _string(item, "targeted input")))
                    for item in _array(inputs.get("targetedInputs"), "targetedInputs")
                ]
                launch = classic_scanlog.ScanRunLaunch.targeted(str(root), targeted, overrides)
            else:
                raise RunnerContractError(f"unsupported intent {intent}")
        except classic_scanlog.ScanRunLaunchError as error:
            # Each frozen launch error token has its own exception subclass.
            if isinstance(error, classic_scanlog.ScanRunLaunchTargetedWithoutInputsError):
                kind = "targeted_without_inputs"
            elif isinstance(error, classic_scanlog.ScanRunLaunchXseLogInspectError):
                kind = "xse_log_inspect"
            else:
                raise
            return {
                "outcome": "error",
                "errorKind": kind,
                "request": None,
                "diagnostics": [],
                "settingsUnchanged": settings.read_bytes() == before,
            }
        # The executable copy must exist for every launch; executing is the scan-run family's job.
        launch.request()
        return {
            "outcome": "launched",
            "errorKind": None,
            "request": _request_view(launch, root),
            "diagnostics": [
                {"kind": diagnostic.kind, "code": diagnostic.code}
                for diagnostic in launch.diagnostics
            ],
            "settingsUnchanged": settings.read_bytes() == before,
        }


def _scenario_receipt(plan: Mapping[str, Any], raw_scenario: object) -> dict[str, Any]:
    """Preserve failed scenario executions as explicit receipt evidence."""
    scenario = _mapping(raw_scenario, "run plan scenario")
    result: dict[str, Any] = {
        "id": _string(scenario.get("id"), "scenario id"),
        "capabilityIds": _array(scenario.get("capabilityIds"), "scenario capabilityIds"),
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
    """Copy central envelope identities and append actual observations."""
    return {
        **{
            key: plan.get(key)
            for key in ("schemaVersion", "familyId", "familyVersion", "expectationDigest")
        },
        "invocation": dict(_mapping(plan.get("invocation"), "run plan invocation")),
        "participant": dict(_mapping(plan.get("participant"), "run plan participant")),
        "runner": {
            "id": "classic-python-scan-launch-conformance",
            "version": 1,
            "platform": {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux"),
            "toolchain": sys.implementation.name,
        },
        "scenarios": [
            _scenario_receipt(plan, scenario)
            for scenario in _array(plan.get("scenarios"), "run plan scenarios")
        ],
    }


def _publish_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    """Atomically publish fresh canonical JSON without reusing stale output."""
    if path.exists():
        raise RunnerContractError("conformance receipt destination already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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
        plan_path = Path(_string(os.environ.get(RUN_PLAN_ENV), RUN_PLAN_ENV)).resolve(strict=True)
        output_path = Path(_string(os.environ.get(OUTPUT_ENV), OUTPUT_ENV)).resolve(strict=False)
        if output_path.parent != plan_path.parent:
            raise RunnerContractError(
                "conformance receipt must be a sibling of its immutable run plan"
            )
        _publish_receipt(output_path, _build_receipt(_load_plan(plan_path)))
    except (OSError, RunnerContractError, json.JSONDecodeError) as error:
        print(f"classic-python-scan-launch-conformance: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
