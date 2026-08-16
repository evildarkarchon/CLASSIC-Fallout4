"""Execute Crash Log Scan Run conformance plans through the public PyO3 API."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

RUN_PLAN_ENV = "CLASSIC_CONFORMANCE_RUN_PLAN"
OUTPUT_ENV = "CLASSIC_CONFORMANCE_OUTPUT"


class RunnerContractError(RuntimeError):
    """Report an invalid private runner invocation or input-only plan."""


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    """Return one JSON object or raise a path-attributed runner error."""

    if not isinstance(value, Mapping):
        raise RunnerContractError(f"{label} must be an object")
    return value


def _require_sequence(value: object, label: str) -> Sequence[Any]:
    """Return one JSON array while excluding strings and object mappings."""

    if not isinstance(value, list):
        raise RunnerContractError(f"{label} must be an array")
    return value


def _require_string(value: object, label: str) -> str:
    """Return one non-empty string or raise a path-attributed runner error."""

    if not isinstance(value, str) or not value:
        raise RunnerContractError(f"{label} must be a non-empty string")
    return value


def _load_plan(path: Path) -> Mapping[str, Any]:
    """Load one centrally authenticated input-only plan without consulting its pack."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RunnerContractError(
            f"cannot read conformance run plan: {error}"
        ) from error
    plan = _require_mapping(document, "run plan")
    if plan.get("familyId") != "crash-log-scan-run":
        raise RunnerContractError("run plan family must be crash-log-scan-run")
    participant = _require_mapping(plan.get("participant"), "run plan participant")
    if participant != {
        "id": "python",
        "role": "semantic-adapter",
        "executionInstanceId": "python",
    }:
        raise RunnerContractError(
            "run plan is not the Python semantic-adapter invocation"
        )
    scenarios = _require_sequence(plan.get("scenarios"), "run plan scenarios")
    if not scenarios:
        raise RunnerContractError("run plan must contain scenarios")
    for index, raw_scenario in enumerate(scenarios):
        scenario = _require_mapping(raw_scenario, f"run plan scenarios[{index}]")
        if "expected" in scenario:
            raise RunnerContractError(
                "input-only run plan must not contain expectations"
            )
    return plan


def _runtime_path(root: Path, value: object, label: str) -> Path:
    """Resolve one canonical plan-relative path beneath a fresh runtime root."""

    text = _require_string(value, label)
    posix = PurePosixPath(text)
    windows = PureWindowsPath(text)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or "\\" in text
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise RunnerContractError(f"{label} must stay beneath the runtime root")
    candidate = (root / Path(*posix.parts)).resolve(strict=False)
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise RunnerContractError(f"{label} escapes the runtime root") from error
    return candidate


def _relative_path(root: Path, value: object, label: str) -> str:
    """Project one public path result to a canonical runtime-root-relative string."""

    text = _require_string(str(value), label)
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        relative = candidate.resolve(strict=False).relative_to(root.resolve())
    except (OSError, ValueError) as error:
        raise RunnerContractError(
            f"{label} is outside the fresh runtime root"
        ) from error
    return relative.as_posix()


def _path_carrier(root: Path, value: object, label: str) -> dict[str, str]:
    """Create one normalized path carrier used by the common observation contract."""

    return {"path": _relative_path(root, value, label)}


def _copy_declared_fixture(
    plan: Mapping[str, Any],
    scenario: Mapping[str, Any],
    item: Mapping[str, Any],
    root: Path,
    label: str,
) -> None:
    """Copy one scenario-declared fixture to its writable runtime destination."""

    fixture_ref = item.get("fixtureRef")
    if fixture_ref is None:
        return
    reference = _require_string(fixture_ref, f"{label}.fixtureRef")
    scenario_refs = _require_sequence(
        scenario.get("fixtureRefs"), "scenario fixtureRefs"
    )
    if reference not in scenario_refs:
        raise RunnerContractError(f"{label}.fixtureRef is not declared by the scenario")
    fixtures = _require_mapping(plan.get("fixtures"), "run plan fixtures")
    source_text = _require_string(fixtures.get(reference), f"fixture {reference}")
    source = Path(source_text)
    if not source.is_file():
        raise RunnerContractError(f"fixture {reference} is not a readable file")
    destination = _runtime_path(root, item.get("path"), f"{label}.path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _materialize_scenario_inputs(
    plan: Mapping[str, Any], scenario: Mapping[str, Any], root: Path
) -> Mapping[str, Any]:
    """Materialize only plan-declared installation data and Crash Log inputs."""

    inputs = _require_mapping(scenario.get("input"), "scenario input")
    installation = _require_sequence(
        inputs.get("installationData"), "scenario input installationData"
    )
    for index, raw_item in enumerate(installation):
        item = _require_mapping(raw_item, f"installationData[{index}]")
        _copy_declared_fixture(plan, scenario, item, root, f"installationData[{index}]")

    intent = inputs.get("intent")
    input_field = "logInputs" if intent == "standard" else "targetedInputs"
    log_inputs = _require_sequence(
        inputs.get(input_field), f"scenario input {input_field}"
    )
    for index, raw_item in enumerate(log_inputs):
        item = _require_mapping(raw_item, f"{input_field}[{index}]")
        _copy_declared_fixture(plan, scenario, item, root, f"{input_field}[{index}]")

    if intent == "standard":
        standard = _require_mapping(
            inputs.get("standardSource"), "scenario input standardSource"
        )
        base = _require_mapping(standard.get("baseDirectory"), "standard baseDirectory")
        _runtime_path(root, base.get("path"), "standard baseDirectory.path").mkdir(
            parents=True, exist_ok=True
        )
        documents = _require_mapping(
            standard.get("configuredDocumentsRoot"),
            "standard configuredDocumentsRoot",
        )
        _runtime_path(
            root,
            documents.get("path"),
            "standard configuredDocumentsRoot.path",
        ).mkdir(parents=True, exist_ok=True)
    elif intent != "targeted":
        raise RunnerContractError("scenario intent must be standard or targeted")
    return inputs


def _append_local_ignore_padding(inputs: Mapping[str, Any], root: Path) -> None:
    """Append declared bytes that keep the reset transaction observable to cancellation."""

    raw_byte_count = inputs.get("localIgnorePaddingBytes")
    if raw_byte_count is None:
        return
    if type(raw_byte_count) is not int or raw_byte_count < 0:
        raise RunnerContractError(
            "scenario input localIgnorePaddingBytes must be a non-negative integer"
        )
    if raw_byte_count == 0:
        return
    local_ignore_path = root / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    try:
        with local_ignore_path.open("ab") as local_ignore:
            local_ignore.write(b"x" * raw_byte_count)
    except OSError as error:
        raise RunnerContractError(
            "cannot append declared Local Ignore padding"
        ) from error


@contextmanager
def _isolated_runtime_environment(root: Path) -> Iterator[None]:
    """Isolate cache lookup and working-directory state for one hermetic scan."""

    cache_root = root / "isolated-cache"
    cache_root.mkdir(parents=True)
    previous_directory = Path.cwd()
    previous_environment = {
        name: os.environ.get(name) for name in ("LOCALAPPDATA", "XDG_CACHE_HOME")
    }
    os.environ["LOCALAPPDATA"] = str(cache_root)
    os.environ["XDG_CACHE_HOME"] = str(cache_root)
    os.chdir(root)
    try:
        yield
    finally:
        os.chdir(previous_directory)
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _configured_paths(root: Path, raw_paths: object) -> list[str]:
    """Convert plan path values into absolute binding configuration paths."""

    paths = _require_sequence(raw_paths, "scenario input formidDatabasePaths")
    configured = []
    for index, raw_path in enumerate(paths):
        if isinstance(raw_path, Mapping):
            raw_path = raw_path.get("path")
        configured.append(
            str(_runtime_path(root, raw_path, f"formidDatabasePaths[{index}]"))
        )
    return configured


def _build_request(
    classic_scanlog: Any, classic_shared: Any, inputs: Mapping[str, Any], root: Path
) -> Any:
    """Construct the frozen Standard or Targeted request through public factories."""

    if inputs.get("game") != "fallout4":
        raise RunnerContractError("base scenario game must be fallout4")
    max_concurrent = inputs.get("maxConcurrent")
    if type(max_concurrent) is not int:
        raise RunnerContractError("scenario input maxConcurrent must be an integer")
    configuration = classic_scanlog.ScanRunConfiguration(
        installation_root=str(root),
        game=classic_shared.GameId.Fallout4,
        game_version=_require_string(inputs.get("gameVersion"), "gameVersion"),
        show_formid_values=bool(inputs.get("showFormidValues")),
        simplify_logs=bool(inputs.get("simplifyLogs")),
        formid_database_paths=_configured_paths(
            root, inputs.get("formidDatabasePaths")
        ),
        unsolved_logs_destination=None,
        max_concurrent=max_concurrent,
    )
    intent = inputs.get("intent")
    if intent == "standard":
        standard = _require_mapping(inputs.get("standardSource"), "standardSource")
        base = _require_mapping(standard.get("baseDirectory"), "baseDirectory")
        documents = _require_mapping(
            standard.get("configuredDocumentsRoot"), "configuredDocumentsRoot"
        )
        source = classic_scanlog.ScanRunStandardSource(
            base_directory=str(
                _runtime_path(root, base.get("path"), "baseDirectory.path")
            ),
            configured_documents_root=str(
                _runtime_path(
                    root,
                    documents.get("path"),
                    "configuredDocumentsRoot.path",
                )
            ),
        )
        if inputs.get("unsolvedLogs") != "leave-in-place":
            raise RunnerContractError(
                "base Standard scenario must leave unsolved logs in place"
            )
        movement = classic_scanlog.ScanRunUnsolvedLogs.leave_in_place()
        return classic_scanlog.ScanRunRequest.standard(configuration, source, movement)
    if intent == "targeted":
        targeted = _require_sequence(inputs.get("targetedInputs"), "targetedInputs")
        paths = [
            str(
                _runtime_path(
                    root,
                    _require_mapping(item, f"targetedInputs[{index}]").get("path"),
                    f"targetedInputs[{index}].path",
                )
            )
            for index, item in enumerate(targeted)
        ]
        source = classic_scanlog.ScanRunTargetedSource(inputs=paths)
        return classic_scanlog.ScanRunRequest.targeted(configuration, source)
    raise RunnerContractError("scenario intent must be standard or targeted")


def _display_content(lines: object, root: Path) -> list[dict[str, Any]]:
    """Serialize frozen Display Content, preserving every ordered carrier field."""

    serialized = []
    for line in lines:
        segments = []
        for segment in line.segments:
            segment_path = str(segment.path)
            if segment_path:
                segment_path = _relative_path(
                    root, segment_path, "display segment path"
                )
            segments.append(
                {
                    "kind": str(segment.kind),
                    "text": str(segment.text),
                    "path": segment_path,
                    "count": int(segment.count),
                }
            )
        serialized.append({"severity": str(line.severity), "segments": segments})
    return serialized


def _serialize_setup(setup: object | None, root: Path) -> object | None:
    """Serialize unexpected FCX setup data so a non-null regression stays visible."""

    if setup is None:
        return None
    return {
        "status": str(setup.status),
        "message": setup.message,
        "renderedReport": str(setup.rendered_report),
        "checks": [
            {
                "kind": str(check.kind),
                "state": str(check.state),
                "message": str(check.message),
                "details": [str(detail) for detail in check.details],
            }
            for check in setup.checks
        ],
        "pathUpdates": [
            {
                "kind": str(update.kind),
                "path": _path_carrier(root, update.path, "setup path update"),
            }
            for update in setup.path_updates
        ],
        "actions": [str(action) for action in setup.actions],
        "fatalErrors": [str(error) for error in setup.fatal_errors],
    }


def _content_identity(identity: Any, byte_length_attribute: str) -> dict[str, Any]:
    """Serialize one exact-byte Installed YAML Data identity."""

    return {
        "sha256": str(identity.sha256),
        "byteLength": int(getattr(identity, byte_length_attribute)),
    }


def _installed_yaml_data(installed: object | None, root: Path) -> object | None:
    """Serialize the immutable Installed YAML Data snapshot used by the run."""

    if installed is None:
        return None
    diagnostics = []
    for diagnostic in installed.diagnostics:
        path = diagnostic.path
        diagnostics.append(
            {
                "role": diagnostic.role,
                "candidate": diagnostic.candidate,
                "path": None
                if path is None
                else _path_carrier(root, path, "Installed YAML Data diagnostic path"),
                "kind": str(diagnostic.kind),
                "message": str(diagnostic.message),
            }
        )
    return {
        "main": {
            "role": str(installed.main.role),
            "provenance": str(installed.main.provenance),
            "schemaMajor": int(installed.main.schema_major),
            "schemaMinor": int(installed.main.schema_minor),
            "identity": _content_identity(installed.main, "byte_length"),
        },
        "gameFile": {
            "role": str(installed.game_file.role),
            "provenance": str(installed.game_file.provenance),
            "schemaMajor": int(installed.game_file.schema_major),
            "schemaMinor": int(installed.game_file.schema_minor),
            "identity": _content_identity(installed.game_file, "byte_length"),
        },
        "localIgnoreState": str(installed.local_ignore_state),
        "localIgnoreIdentity": _content_identity(
            installed.local_ignore_identity, "byte_len"
        ),
        "diagnostics": diagnostics,
        "localIgnoreResetAvailable": bool(installed.local_ignore_reset_available),
    }


def _identity_from_bytes(content: bytes) -> dict[str, Any]:
    """Return the exact SHA-256 and byte length of durable file content."""

    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "byteLength": len(content),
    }


def _read_optional_file(path: Path) -> bytes | None:
    """Read one file, treating only absence as optional and propagating other I/O errors."""

    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _local_ignore_installed_yaml_data(
    installed: object | None, root: Path
) -> object | None:
    """Project stable Local Ignore metadata without temporary-root diagnostic prose."""

    if installed is None:
        return None
    diagnostics = [
        {
            "role": diagnostic.role,
            "candidate": diagnostic.candidate,
            "path": None
            if diagnostic.path is None
            else _path_carrier(
                root,
                diagnostic.path,
                "Installed YAML Data diagnostic path",
            ),
            "kind": str(diagnostic.kind),
        }
        for diagnostic in installed.diagnostics
    ]
    reset = installed.local_ignore_reset
    reset_observation = None
    if reset is not None:
        backup_path = Path(str(reset.backup_path))
        backup_content = _read_optional_file(backup_path)
        backup_identity = (
            None if backup_content is None else _identity_from_bytes(backup_content)
        )
        reset_observation = {
            "localIgnorePath": _path_carrier(
                root, reset.local_ignore_path, "Local Ignore reset path"
            ),
            "backup": {
                "parentPath": _relative_path(
                    root, backup_path.parent, "Local Ignore backup parent"
                ),
                "exists": backup_content is not None,
                "identityMatchesReceipt": backup_identity
                == _content_identity(reset.backup_identity, "byte_len"),
            },
            "malformedIdentity": _content_identity(
                reset.malformed_identity, "byte_len"
            ),
            "backupIdentity": _content_identity(reset.backup_identity, "byte_len"),
            "replacementIdentity": _content_identity(
                reset.replacement_identity, "byte_len"
            ),
        }
    return {
        "mainIdentity": _content_identity(installed.main, "byte_length"),
        "gameIdentity": _content_identity(installed.game_file, "byte_length"),
        "localIgnoreState": str(installed.local_ignore_state),
        "localIgnoreIdentity": _content_identity(
            installed.local_ignore_identity, "byte_len"
        ),
        "diagnostics": diagnostics,
        "localIgnoreResetAvailable": bool(installed.local_ignore_reset_available),
        "localIgnoreReset": reset_observation,
    }


def _discovery(discovery: object | None, root: Path) -> object | None:
    """Serialize ordered discovery paths and Targeted rejection reasons."""

    if discovery is None:
        return None
    return {
        "source": str(discovery.source),
        "acceptedLogs": [
            _path_carrier(root, path, "accepted Crash Log")
            for path in discovery.accepted_logs
        ],
        "rejectedInputs": [
            {
                "path": _relative_path(root, rejected.path, "rejected input"),
                "reason": str(rejected.reason),
            }
            for rejected in discovery.rejected_inputs
        ],
        "searchedLocations": [
            _path_carrier(root, path, "searched location")
            for path in discovery.searched_locations
        ],
    }


def _log_results(logs: object, root: Path) -> list[dict[str, Any]]:
    """Serialize discovery-ordered terminal log outcomes without timing fields."""

    serialized = []
    for log in logs:
        report = log.autoscan_report
        serialized.append(
            {
                "discoveryIndex": int(log.discovery_index),
                "crashLog": _path_carrier(root, log.crash_log, "result Crash Log"),
                "autoscanReport": None
                if report is None
                else _path_carrier(root, report, "Autoscan Report"),
                "disposition": str(log.disposition),
                "failures": [
                    {"stage": str(failure.stage), "message": str(failure.message)}
                    for failure in log.failures
                ],
                "message": log.message,
                "movedToUnsolvedLogs": bool(log.moved_to_unsolved_logs),
            }
        )
    return serialized


def _events(events: Sequence[Any], root: Path) -> dict[str, Any]:
    """Partition serialized callbacks into stable run and per-log ordered traces."""

    run_events: list[dict[str, Any]] = []
    log_streams: dict[int, dict[str, Any]] = {}
    for event in events:
        value: dict[str, Any] = {
            "kind": str(event.kind),
            "displayContent": _display_content(event.display_lines, root),
        }
        log = event.log
        if log is None:
            if event.effective_concurrency is not None:
                value["effectiveConcurrency"] = int(event.effective_concurrency)
            run_events.append(value)
            continue
        discovery_index = int(log.discovery_index)
        stream = log_streams.setdefault(
            discovery_index,
            {
                "discoveryIndex": discovery_index,
                "crashLog": _path_carrier(root, log.crash_log, "event Crash Log"),
                "trace": [],
            },
        )
        if event.phase is not None:
            value["phase"] = str(event.phase)
        if event.disposition is not None:
            value["disposition"] = str(event.disposition)
        stream["trace"].append(value)
    return {
        "run": run_events,
        "logs": [log_streams[index] for index in sorted(log_streams)],
    }


def _compact_events(result: Any, events: Sequence[Any], root: Path) -> dict[str, Any]:
    """Project stable event tokens while preserving the run and per-log order."""

    logs = list(result.logs)
    positions = {int(log.discovery_index): index for index, log in enumerate(logs)}
    traces: list[list[str]] = [[] for _ in logs]
    run_events: list[str] = []
    for event in events:
        kind = str(event.kind)
        if kind in {"discovery_completed", "effective_concurrency_selected"}:
            run_events.append(kind)
            continue
        log = event.log
        if log is None:
            raise RunnerContractError(f"compact event {kind} has no log identity")
        discovery_index = int(log.discovery_index)
        position = positions.get(discovery_index)
        if position is None:
            raise RunnerContractError(
                f"compact event references unknown discovery index {discovery_index}"
            )
        result_path = _relative_path(
            root, logs[position].crash_log, "compact result Crash Log"
        )
        event_path = _relative_path(root, log.crash_log, "compact event Crash Log")
        if result_path != event_path:
            raise RunnerContractError(
                f"compact event Crash Log differs at discovery index {discovery_index}"
            )
        if kind == "log_phase":
            token = f"{kind}:{event.phase}"
        elif kind == "log_finished":
            token = f"{kind}:{event.disposition}"
        elif kind in {"log_queued", "log_started"}:
            token = kind
        else:
            raise RunnerContractError(f"unknown compact scan-run event {kind}")
        traces[position].append(token)
    return {
        "run": run_events,
        "logs": [
            {"discoveryIndex": int(log.discovery_index), "trace": traces[index]}
            for index, log in enumerate(logs)
        ],
    }


def _durable_effects(logs: object, root: Path) -> dict[str, Any]:
    """Observe report persistence and the forbidden Unsolved Logs destination."""

    reports = []
    for log in logs:
        if log.autoscan_report is None:
            continue
        report_path = Path(str(log.autoscan_report))
        if not report_path.is_absolute():
            report_path = root / report_path
        reports.append(
            {
                "path": _relative_path(root, report_path, "durable Autoscan Report"),
                "exists": report_path.is_file(),
                "nonEmpty": report_path.is_file() and report_path.stat().st_size > 0,
            }
        )
    unsolved = root / "Unsolved Logs"
    return {
        "reports": reports,
        "unsolvedLogs": {"path": "Unsolved Logs", "exists": unsolved.exists()},
    }


def _file_effect(root: Path, path: Path, label: str) -> dict[str, Any]:
    """Project a path's existence and file identity, including non-file effects."""

    try:
        path_metadata = path.stat()
    except FileNotFoundError:
        path_metadata = None
    content = (
        path.read_bytes()
        if path_metadata is not None and stat.S_ISREG(path_metadata.st_mode)
        else None
    )
    return {
        "path": _relative_path(root, path, label),
        "exists": path_metadata is not None,
        "identity": None if content is None else _identity_from_bytes(content),
    }


def _local_ignore_durable_effects(
    result: Any | None, inputs: Mapping[str, Any], root: Path
) -> dict[str, Any]:
    """Observe Local Ignore and every durable effect, including failed resume outcomes."""

    backup_directory = root / "CLASSIC Backup" / "YAML Data" / "Local Ignore"
    try:
        backup_entries = sorted(backup_directory.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        backup_entries = []
    backups = []
    for path in backup_entries:
        if not stat.S_ISREG(path.stat().st_mode):
            continue
        content = _read_optional_file(path)
        if content is None:
            raise RunnerContractError(
                "enumerated Local Ignore backup disappeared before observation"
            )
        backups.append(
            {
                "parentPath": _relative_path(
                    root, path.parent, "Local Ignore backup parent"
                ),
                "identity": _identity_from_bytes(content),
            }
        )

    reports = []
    logs = () if result is None else result.logs
    for log in logs:
        if log.autoscan_report is None:
            continue
        report_path = Path(str(log.autoscan_report))
        if not report_path.is_absolute():
            report_path = root / report_path
        content = _read_optional_file(report_path)
        reports.append(
            {
                "path": _relative_path(root, report_path, "durable Autoscan Report"),
                "exists": content is not None,
                "nonEmpty": content is not None and len(content) > 0,
                "identity": None if content is None else _identity_from_bytes(content),
            }
        )

    forbidden = []
    for index, raw_path in enumerate(
        _require_sequence(
            inputs.get("forbiddenEffectPaths", []), "forbiddenEffectPaths"
        )
    ):
        path = _runtime_path(root, raw_path, f"forbiddenEffectPaths[{index}]")
        forbidden.append(_file_effect(root, path, "forbidden effect"))

    return {
        "localIgnore": _file_effect(
            root,
            root / "CLASSIC Data" / "CLASSIC Ignore.yaml",
            "durable Local Ignore",
        ),
        "backups": backups,
        "reports": reports,
        "forbidden": forbidden,
    }


def _result_or_raise(execution: Any) -> Any:
    """Return a public result or raise the adapter failure carried by its envelope."""

    if execution.observer_error is not None:
        raise RunnerContractError(
            f"observer delivery failed: {execution.observer_error}"
        )
    if execution.error is not None:
        path = "" if execution.error.path is None else f" ({execution.error.path})"
        raise RunnerContractError(
            f"scan failed during {execution.error.stage}: {execution.error.message}{path}"
        )
    result = execution.result
    if result is None:
        raise RunnerContractError("public scan operation returned no result or error")
    return result


def _observation(
    execution: Any, callbacks: Sequence[Any], root: Path
) -> dict[str, Any]:
    """Project one public execution envelope to the frozen normalized observation."""

    result = _result_or_raise(execution)
    return {
        "run": {
            "status": str(result.status),
            "message": result.message,
            "total": int(result.total),
            "succeeded": int(result.succeeded),
            "failed": int(result.failed),
            "cancelled": int(result.cancelled),
            "setup": _serialize_setup(result.setup, root),
            "effectiveConcurrency": result.effective_concurrency,
        },
        "discovery": _discovery(result.discovery, root),
        "installedYamlData": _installed_yaml_data(result.installed_yaml_data, root),
        "logs": _log_results(result.logs, root),
        "events": _events(callbacks, root),
        "displayContent": _display_content(execution.display_lines, root),
        "durableEffects": _durable_effects(result.logs, root),
    }


def _decision_token(classic_scanlog: Any, decision: Any) -> str:
    """Map the public recovery enum to its Rust-owned vocabulary token."""

    enum = classic_scanlog.ScanRunLocalIgnoreRecoveryDecision
    if decision == enum.ProceedWithoutIgnore:
        return "proceed_without_ignore"
    if decision == enum.ResetToDefault:
        return "reset_to_default"
    raise RunnerContractError("recovery prompt exposed an unknown decision")


def _recovery_decision(classic_scanlog: Any, token: object, label: str) -> Any:
    """Resolve one plan decision token to the public Python recovery enum."""

    value = _require_string(token, label)
    enum = classic_scanlog.ScanRunLocalIgnoreRecoveryDecision
    if value == "proceed-without-ignore":
        return enum.ProceedWithoutIgnore
    if value == "reset-to-default":
        return enum.ResetToDefault
    raise RunnerContractError(f"{label} is not a supported recovery decision")


def _project_recovery_prompt(classic_scanlog: Any, prompt: Any) -> dict[str, Any]:
    """Project prompt severities plus public decision labels and availability."""

    return {
        "displaySeverities": [str(line.severity) for line in prompt.lines],
        "decisions": [
            {
                "decision": _decision_token(classic_scanlog, decision.decision),
                "label": str(decision.label),
                "available": bool(decision.available),
            }
            for decision in prompt.decisions
        ],
    }


def _local_ignore_phase(
    classic_scanlog: Any,
    execution: Any,
    callbacks: Sequence[Any],
    root: Path,
    *,
    continuation_available: bool,
    recovery_prompt: Any | None,
) -> dict[str, Any]:
    """Project one initial or terminal Local Ignore phase without filesystem effects."""

    result = _result_or_raise(execution)
    if result.setup is not None:
        raise RunnerContractError(
            "Local Ignore scenario unexpectedly returned setup data"
        )
    return {
        "run": {
            "status": str(result.status),
            "message": result.message,
            "total": int(result.total),
            "succeeded": int(result.succeeded),
            "failed": int(result.failed),
            "cancelled": int(result.cancelled),
            "effectiveConcurrency": result.effective_concurrency,
        },
        "discovery": _discovery(result.discovery, root),
        "installedYamlData": _local_ignore_installed_yaml_data(
            result.installed_yaml_data, root
        ),
        "logs": _log_results(result.logs, root),
        "events": _compact_events(result, callbacks, root),
        "continuationAvailable": continuation_available,
        "recoveryPrompt": None
        if recovery_prompt is None
        else _project_recovery_prompt(classic_scanlog, recovery_prompt),
    }


def _local_ignore_observation(
    classic_scanlog: Any,
    execution: Any,
    callbacks: Sequence[Any],
    inputs: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Project a terminal Local Ignore run and its exact durable effects."""

    result = _result_or_raise(execution)
    observation = _local_ignore_phase(
        classic_scanlog,
        execution,
        callbacks,
        root,
        continuation_available=result.continuation is not None,
        recovery_prompt=execution.recovery_prompt,
    )
    observation["durableEffects"] = _local_ignore_durable_effects(result, inputs, root)
    return observation


def _continuation_action(raw_action: object, label: str) -> tuple[str, str | None]:
    """Validate one continuation operation and its optional plan decision."""

    action = _require_mapping(raw_action, label)
    operation = _require_string(action.get("operation"), f"{label}.operation")
    raw_decision = action.get("decision")
    decision = None
    if raw_decision is not None:
        decision = _require_string(raw_decision, f"{label}.decision")
    if operation == "resume" and decision in {
        "proceed-without-ignore",
        "reset-to-default",
    }:
        return operation, decision
    if operation == "abandon" and decision is None:
        return operation, None
    if operation == "resume":
        raise RunnerContractError(f"{label} has no supported recovery decision")
    if operation == "abandon":
        raise RunnerContractError(f"{label} abandon operation must not have a decision")
    raise RunnerContractError(f"{label}.operation must be resume or abandon")


def _run_continuation_action(
    classic_scanlog: Any,
    continuation: Any,
    cancellation: Any,
    raw_action: object,
    label: str,
    callbacks: list[Any] | None,
) -> Any:
    """Invoke one public resume or abandon operation on the retained continuation."""

    operation, decision = _continuation_action(raw_action, label)
    observer = None if callbacks is None else callbacks.append
    if operation == "resume":
        return classic_scanlog.scan_run_resume(
            continuation,
            _recovery_decision(classic_scanlog, decision, f"{label}.decision"),
            cancellation,
            observer,
        )
    return classic_scanlog.scan_run_abandon(
        continuation,
        cancellation,
        observer,
    )


def _project_replay_error(
    raw_action: object, label: str, error: Exception
) -> dict[str, Any]:
    """Project a typed consumed-continuation rejection without adapter-only prose."""

    operation, decision = _continuation_action(raw_action, label)
    kind = getattr(error, "kind", None)
    display_lines = getattr(error, "display_lines", None)
    if not isinstance(kind, str) or display_lines is None:
        raise RunnerContractError(
            f"{label} raised an untyped replay error: {type(error).__name__}: {error}"
        ) from error
    decision_token = None if decision is None else decision.replace("-", "_")
    return {
        "operation": operation,
        "decision": decision_token,
        "error": {
            "kind": kind,
            "message": str(error),
            "displaySeverities": [str(line.severity) for line in display_lines],
        },
    }


def _optional_error_identity(error: Exception, attribute: str) -> dict[str, Any] | None:
    """Project an optional exact-byte identity carried by a typed resume exception."""

    identity = getattr(error, attribute, None)
    return None if identity is None else _content_identity(identity, "byte_len")


def _optional_error_path(
    error: Exception, attribute: str, root: Path, label: str
) -> dict[str, str] | None:
    """Project an optional typed resume-exception path beneath the runtime root."""

    path = getattr(error, attribute, None)
    return None if path is None else _path_carrier(root, path, label)


def _project_terminal_resume_error(
    error: Exception, callbacks: Sequence[Any], root: Path
) -> dict[str, Any]:
    """Normalize a public reset conflict or backup failure without OS-dependent prose."""

    kind = getattr(error, "kind", None)
    code = getattr(error, "code", None)
    display_lines = getattr(error, "display_lines", None)
    if (
        kind
        not in {
            "local_ignore_reset_conflict",
            "local_ignore_reset_backup_failure",
        }
        or display_lines is None
    ):
        raise RunnerContractError(
            "terminal continuation raised an unsupported untyped error: "
            f"{type(error).__name__}"
        ) from error
    if callbacks:
        raise RunnerContractError(
            "failed Local Ignore reset unexpectedly emitted scan events"
        ) from error
    if not isinstance(code, str) or code != kind:
        raise RunnerContractError(
            "terminal continuation error kind and code must agree"
        ) from error
    stage = getattr(error, "stage", None)
    if stage is not None and not isinstance(stage, str):
        raise RunnerContractError(
            "typed Local Ignore reset failure exposed a non-string stage"
        ) from error
    return {
        "code": code,
        "kind": kind,
        "path": _optional_error_path(error, "path", root, "reset failure path"),
        "stage": stage,
        "expectedIdentity": _optional_error_identity(error, "expected_identity"),
        "actualIdentity": _optional_error_identity(error, "actual_identity"),
        "backupPath": _optional_error_path(
            error,
            "backup_path",
            root,
            "reset failure backup path",
        ),
        "malformedIdentity": _optional_error_identity(error, "malformed_identity"),
        "backupIdentity": _optional_error_identity(error, "backup_identity"),
        "replacementIdentity": _optional_error_identity(error, "replacement_identity"),
        "displaySeverities": [str(line.severity) for line in display_lines],
        "messageNonEmpty": bool(str(error)),
        "events": [],
    }


def _materialize_post_pause_data(
    plan: Mapping[str, Any],
    scenario: Mapping[str, Any],
    raw_placements: object,
    root: Path,
) -> None:
    """Apply declared mutations only after the initial continuation has been retained."""

    placements = _require_sequence(raw_placements, "continuationFlow.postPauseData")
    for index, raw_placement in enumerate(placements):
        label = f"continuationFlow.postPauseData[{index}]"
        placement = _require_mapping(raw_placement, label)
        _require_string(placement.get("fixtureRef"), f"{label}.fixtureRef")
        _copy_declared_fixture(plan, scenario, placement, root, label)


def _execute_continuation_flow(
    classic_scanlog: Any,
    plan: Mapping[str, Any],
    scenario: Mapping[str, Any],
    inputs: Mapping[str, Any],
    root: Path,
    cancellation: Any,
    initial_execution: Any,
    initial_callbacks: Sequence[Any],
) -> dict[str, Any]:
    """Resolve one prepared run across reset outcomes and prove its claim rejects replays."""

    flow = _require_mapping(inputs.get("continuationFlow"), "continuationFlow")
    action = flow.get("action")
    _continuation_action(action, "continuationFlow.action")
    replays = _require_sequence(flow.get("replays", []), "continuationFlow.replays")
    for index, replay in enumerate(replays):
        _continuation_action(replay, f"continuationFlow.replays[{index}]")
    cancellation_boundary = flow.get("cancellation")
    if cancellation_boundary is not None:
        cancellation_boundary = _require_string(
            cancellation_boundary, "continuationFlow.cancellation"
        )
        if cancellation_boundary not in {
            "before-resume",
            "after-reset-critical-section",
        }:
            raise RunnerContractError(
                "continuationFlow.cancellation must be before-resume or "
                "after-reset-critical-section"
            )

    initial_result = _result_or_raise(initial_execution)
    continuation = initial_result.continuation
    if continuation is None:
        raise RunnerContractError(
            "continuationFlow initial result has no retained continuation"
        )
    prompt = initial_execution.recovery_prompt
    if prompt is None:
        raise RunnerContractError(
            "continuationFlow initial execution has no recovery prompt"
        )
    initial = _local_ignore_phase(
        classic_scanlog,
        initial_execution,
        initial_callbacks,
        root,
        continuation_available=True,
        recovery_prompt=prompt,
    )

    _materialize_post_pause_data(
        plan,
        scenario,
        flow.get("postPauseData", []),
        root,
    )
    reset_entry_observed: threading.Event | None = None
    canceller: threading.Thread | None = None
    if cancellation_boundary == "before-resume":
        cancellation.cancel()
    elif cancellation_boundary == "after-reset-critical-section":
        operation, decision = _continuation_action(action, "continuationFlow.action")
        if operation != "resume" or decision != "reset-to-default":
            raise RunnerContractError(
                "after-reset-critical-section cancellation requires reset-to-default"
            )
        reset_lock = root / ".classic-local-ignore-reset.lock"
        reset_entry_observed = threading.Event()

        def cancel_after_reset_entry() -> None:
            """Cancel only after the public reset transaction exposes its lock boundary."""

            deadline = time.monotonic() + 5
            while not reset_lock.exists() and time.monotonic() < deadline:
                time.sleep(0.001)
            if reset_lock.exists():
                reset_entry_observed.set()
                cancellation.cancel()

        canceller = threading.Thread(target=cancel_after_reset_entry)
        canceller.start()

    cancelled_before_terminal = bool(cancellation.is_cancelled)
    terminal_callbacks: list[Any] = []
    terminal_result = None
    terminal = None
    terminal_error = None
    try:
        terminal_execution = _run_continuation_action(
            classic_scanlog,
            continuation,
            cancellation,
            action,
            "continuationFlow.action",
            terminal_callbacks,
        )
    except Exception as error:  # noqa: BLE001 - typed reset rejection is receipt data.
        terminal_error = _project_terminal_resume_error(error, terminal_callbacks, root)
    else:
        terminal_result = _result_or_raise(terminal_execution)
        terminal = _local_ignore_phase(
            classic_scanlog,
            terminal_execution,
            terminal_callbacks,
            root,
            continuation_available=False,
            recovery_prompt=None,
        )
    finally:
        if canceller is not None:
            canceller.join()
    if reset_entry_observed is not None and not reset_entry_observed.is_set():
        raise RunnerContractError(
            "Local Ignore reset critical section was not observed before its deadline"
        )
    cancelled_after_terminal = bool(cancellation.is_cancelled)

    replay_observations = []
    for index, replay in enumerate(replays):
        label = f"continuationFlow.replays[{index}]"
        try:
            _run_continuation_action(
                classic_scanlog,
                continuation,
                cancellation,
                replay,
                label,
                None,
            )
        except Exception as error:  # noqa: BLE001 - typed rejection is receipt data.
            replay_observations.append(_project_replay_error(replay, label, error))
        else:
            raise RunnerContractError(
                f"{label} unexpectedly consumed a continuation more than once"
            )

    return {
        "initial": initial,
        "terminal": terminal,
        "terminalError": terminal_error,
        "replays": replay_observations,
        "cancellation": {
            "beforeTerminal": cancelled_before_terminal,
            "afterTerminal": cancelled_after_terminal,
            "afterReplays": bool(cancellation.is_cancelled),
        },
        "durableEffects": _local_ignore_durable_effects(terminal_result, inputs, root),
    }


def _execute_scenario(
    plan: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute one planned scenario through the installed public binding operation."""

    with tempfile.TemporaryDirectory(prefix="classic-python-conformance-") as directory:
        root = Path(directory).resolve()
        inputs = _materialize_scenario_inputs(plan, scenario, root)
        _append_local_ignore_padding(inputs, root)
        with _isolated_runtime_environment(root):
            import classic_scanlog
            import classic_shared

            request = _build_request(classic_scanlog, classic_shared, inputs, root)
            cancellation = classic_scanlog.ScanRunCancellation()
            callbacks: list[Any] = []
            execution = classic_scanlog.scan_run_execute(
                request,
                cancellation,
                callbacks.append,
            )
            continuation_flow = inputs.get("continuationFlow")
            profile = inputs.get("observationProfile", "base")
            if continuation_flow is not None:
                if profile != "local-ignore":
                    raise RunnerContractError(
                        "continuationFlow requires observationProfile local-ignore"
                    )
                return _execute_continuation_flow(
                    classic_scanlog,
                    plan,
                    scenario,
                    inputs,
                    root,
                    cancellation,
                    execution,
                    callbacks,
                )
            if profile == "base":
                return _observation(execution, callbacks, root)
            if profile == "local-ignore":
                return _local_ignore_observation(
                    classic_scanlog,
                    execution,
                    callbacks,
                    inputs,
                    root,
                )
            raise RunnerContractError("observationProfile must be base or local-ignore")


def _scenario_receipt(plan: Mapping[str, Any], raw_scenario: object) -> dict[str, Any]:
    """Execute one scenario and retain command failures as receipt evidence."""

    scenario = _require_mapping(raw_scenario, "run plan scenario")
    scenario_id = _require_string(scenario.get("id"), "scenario id")
    capability_ids = list(
        _require_sequence(scenario.get("capabilityIds"), "scenario capabilityIds")
    )
    try:
        observation = _execute_scenario(plan, scenario)
    except Exception as error:  # noqa: BLE001 - a failed adapter case still owes a receipt.
        return {
            "id": scenario_id,
            "executionStatus": "failed",
            "capabilityIds": capability_ids,
            "observation": {},
            "failure": {
                "kind": "python-runner-error",
                "message": f"{type(error).__name__}: {error}",
            },
        }
    return {
        "id": scenario_id,
        "executionStatus": "completed",
        "capabilityIds": capability_ids,
        "observation": observation,
        "failure": None,
    }


def _platform_id() -> str:
    """Return the stable platform token recorded by this private runner."""

    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _build_receipt(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Build one current receipt while copying every centrally owned identity."""

    scenarios = _require_sequence(plan.get("scenarios"), "run plan scenarios")
    return {
        "schemaVersion": plan.get("schemaVersion"),
        "familyId": plan.get("familyId"),
        "familyVersion": plan.get("familyVersion"),
        "expectationDigest": plan.get("expectationDigest"),
        "invocation": dict(
            _require_mapping(plan.get("invocation"), "run plan invocation")
        ),
        "participant": dict(
            _require_mapping(plan.get("participant"), "run plan participant")
        ),
        "runner": {
            "id": "classic-python-conformance",
            "version": 1,
            "platform": _platform_id(),
            "toolchain": sys.implementation.name,
        },
        "scenarios": [_scenario_receipt(plan, scenario) for scenario in scenarios],
    }


def _publish_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    """Atomically publish one fresh canonical JSON receipt without stale reuse."""

    if path.exists():
        raise RunnerContractError("conformance receipt destination already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    payload = json.dumps(
        receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    try:
        with temporary.open("xb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise RunnerContractError(
            f"cannot publish conformance receipt: {error}"
        ) from error


def main() -> int:
    """Read the environment-only invocation, execute its plan, and emit a receipt."""

    run_plan_value = os.environ.get(RUN_PLAN_ENV)
    output_value = os.environ.get(OUTPUT_ENV)
    if not run_plan_value or not output_value:
        print(
            f"{RUN_PLAN_ENV} and {OUTPUT_ENV} are required",
            file=sys.stderr,
        )
        return 2
    try:
        run_plan_path = Path(run_plan_value).resolve(strict=True)
        output_path = Path(output_value).resolve(strict=False)
        if output_path.parent != run_plan_path.parent:
            raise RunnerContractError(
                "conformance receipt must be a sibling of its immutable run plan"
            )
        plan = _load_plan(run_plan_path)
        receipt = _build_receipt(plan)
        _publish_receipt(output_path, receipt)
    except (OSError, RunnerContractError) as error:
        print(f"classic-python-conformance: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
