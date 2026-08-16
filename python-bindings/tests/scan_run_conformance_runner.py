"""Execute Crash Log Scan Run conformance plans through the public PyO3 API."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
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


def _observation(
    execution: Any, callbacks: Sequence[Any], root: Path
) -> dict[str, Any]:
    """Project one public execution envelope to the frozen normalized observation."""

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


def _execute_scenario(
    plan: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute one planned scenario through the installed public binding operation."""

    with tempfile.TemporaryDirectory(prefix="classic-python-conformance-") as directory:
        root = Path(directory).resolve()
        inputs = _materialize_scenario_inputs(plan, scenario, root)
        with _isolated_runtime_environment(root):
            import classic_scanlog
            import classic_shared

            request = _build_request(classic_scanlog, classic_shared, inputs, root)
            callbacks: list[Any] = []
            execution = classic_scanlog.scan_run_execute(
                request,
                classic_scanlog.ScanRunCancellation(),
                callbacks.append,
            )
            return _observation(execution, callbacks, root)


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
