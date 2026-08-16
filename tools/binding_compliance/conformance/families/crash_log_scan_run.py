"""Coverage policy for the base Crash Log Scan Run conformance pack."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_MAIN_SHA256 = "934f888a914fa210688d2b3f17ed003d7ee57efa1d695486c20907456a697ac4"
_GAME_SHA256 = "5ff58f93e2018429043a00b11b43c0199b927b984f809a103eb80aa29f7b2168"
_IGNORE_SHA256 = "1fc79ee2668e143c355dc3b931de1a2c41041227e79e21890da90a744ad3b70c"
_TRACE = (
    ("log_queued", None),
    ("log_started", None),
    ("log_phase", "setup"),
    ("log_phase", "parse"),
    ("log_phase", "analyze"),
    ("log_phase", "finalize"),
    ("log_finished", None),
)


def _mapping(value: object) -> Mapping[str, Any] | None:
    """Return ``value`` as a mapping when its runtime shape permits it."""

    return value if isinstance(value, Mapping) else None


def _sequence(value: object) -> Sequence[Any] | None:
    """Return a JSON array shape while excluding strings and object mappings."""

    return value if isinstance(value, list) else None


def _path(value: object) -> str | None:
    """Read one normalized ``{"path": ...}`` carrier."""

    carrier = _mapping(value)
    path = carrier.get("path") if carrier is not None else None
    return path if isinstance(path, str) and path else None


def _run_status(observation: Mapping[str, Any]) -> bool:
    """Recognize a complete two-log happy-path terminal result."""

    run = _mapping(observation.get("run"))
    return run is not None and {
        "status": run.get("status"),
        "message": run.get("message"),
        "total": run.get("total"),
        "succeeded": run.get("succeeded"),
        "failed": run.get("failed"),
        "cancelled": run.get("cancelled"),
    } == {
        "status": "completed",
        "message": None,
        "total": 2,
        "succeeded": 2,
        "failed": 0,
        "cancelled": 0,
    }


def _discovery(observation: Mapping[str, Any]) -> bool:
    """Recognize either authored Standard or Targeted ordered discovery result."""

    discovery = _mapping(observation.get("discovery"))
    if discovery is None:
        return False
    accepted = _sequence(discovery.get("acceptedLogs"))
    rejected = _sequence(discovery.get("rejectedInputs"))
    searched = _sequence(discovery.get("searchedLocations"))
    if accepted is None or rejected is None or searched is None:
        return False
    accepted_paths = [_path(item) for item in accepted]
    searched_paths = [_path(item) for item in searched]
    if discovery.get("source") == "standard":
        return (
            accepted_paths
            == [
                "Standard/Crash Logs/crash-shared-standard-01.log",
                "Standard/Crash Logs/crash-shared-standard-02.log",
            ]
            and rejected == []
            and searched_paths == ["Standard", "Standard/Crash Logs", "Documents"]
        )
    if discovery.get("source") != "targeted" or len(rejected) != 1:
        return False
    rejected_item = _mapping(rejected[0])
    return (
        accepted_paths
        == [
            "Targeted/crash-shared-targeted-02.log",
            "Targeted/crash-shared-targeted-01.log",
        ]
        and rejected_item is not None
        and rejected_item.get("path") == "Targeted/missing-input.txt"
        and rejected_item.get("reason") == "path does not exist"
        and searched_paths
        == [
            "Targeted/crash-shared-targeted-02.log",
            "Targeted/missing-input.txt",
            "Targeted/crash-shared-targeted-01.log",
        ]
    )


def _setup(observation: Mapping[str, Any]) -> bool:
    """Recognize the deliberately absent non-FCX setup projection."""

    run = _mapping(observation.get("run"))
    return run is not None and "setup" in run and run["setup"] is None


def _effective_concurrency(observation: Mapping[str, Any]) -> bool:
    """Recognize concurrency capped by the two accepted Crash Logs."""

    run = _mapping(observation.get("run"))
    return run is not None and run.get("effectiveConcurrency") == 2


def _identity(value: object, sha256: str, byte_length: int) -> bool:
    """Match one exact Installed YAML Data byte identity."""

    identity = _mapping(value)
    return identity is not None and identity == {
        "sha256": sha256,
        "byteLength": byte_length,
    }


def _installed_yaml_data(observation: Mapping[str, Any]) -> bool:
    """Recognize the exact bundled Main/game and existing Local Ignore inputs."""

    installed = _mapping(observation.get("installedYamlData"))
    if installed is None:
        return False
    main = _mapping(installed.get("main"))
    game = _mapping(installed.get("gameFile"))
    return (
        main is not None
        and game is not None
        and {
            key: main.get(key)
            for key in ("role", "provenance", "schemaMajor", "schemaMinor")
        }
        == {
            "role": "main",
            "provenance": "bundled",
            "schemaMajor": 2,
            "schemaMinor": 0,
        }
        and _identity(main.get("identity"), _MAIN_SHA256, 281)
        and {
            key: game.get(key)
            for key in ("role", "provenance", "schemaMajor", "schemaMinor")
        }
        == {
            "role": "game",
            "provenance": "bundled",
            "schemaMajor": 1,
            "schemaMinor": 0,
        }
        and _identity(game.get("identity"), _GAME_SHA256, 463)
        and installed.get("localIgnoreState") == "existing"
        and _identity(installed.get("localIgnoreIdentity"), _IGNORE_SHA256, 29)
        and installed.get("diagnostics") == []
        and installed.get("localIgnoreResetAvailable") is False
    )


def _log_outcomes(observation: Mapping[str, Any]) -> bool:
    """Recognize ordered successful terminal results and report paths."""

    discovery = _mapping(observation.get("discovery"))
    logs = _sequence(observation.get("logs"))
    accepted = (
        _sequence(discovery.get("acceptedLogs")) if discovery is not None else None
    )
    if logs is None or accepted is None or len(logs) != 2 or len(accepted) != 2:
        return False
    for index, (raw_log, raw_accepted) in enumerate(zip(logs, accepted, strict=True)):
        log = _mapping(raw_log)
        crash_log = _path(log.get("crashLog")) if log is not None else None
        if (
            log is None
            or crash_log is None
            or crash_log != _path(raw_accepted)
            or log.get("discoveryIndex") != index
            or log.get("disposition") != "succeeded"
            or log.get("failures") != []
            or log.get("message") is not None
            or log.get("movedToUnsolvedLogs") is not False
            or _path(log.get("autoscanReport"))
            != crash_log.removesuffix(".log") + "-AUTOSCAN.md"
        ):
            return False
    return True


def _events(observation: Mapping[str, Any]) -> bool:
    """Recognize stable run events and each discovery-indexed lifecycle trace."""

    events = _mapping(observation.get("events"))
    if events is None:
        return False
    run_events = _sequence(events.get("run"))
    log_events = _sequence(events.get("logs"))
    if run_events is None or log_events is None or len(log_events) != 2:
        return False
    if [
        _mapping(event).get("kind") if _mapping(event) is not None else None
        for event in run_events
    ] != ["discovery_completed", "effective_concurrency_selected"]:
        return False
    for index, raw_log_events in enumerate(log_events):
        log = _mapping(raw_log_events)
        trace = _sequence(log.get("trace")) if log is not None else None
        if log is None or trace is None or log.get("discoveryIndex") != index:
            return False
        actual_trace = []
        for raw_event in trace:
            event = _mapping(raw_event)
            if event is None:
                return False
            actual_trace.append((event.get("kind"), event.get("phase")))
        if tuple(actual_trace) != _TRACE:
            return False
        finished = _mapping(trace[-1])
        if finished is None or finished.get("disposition") != "succeeded":
            return False
    return True


def _display_content(observation: Mapping[str, Any]) -> bool:
    """Recognize the complete terminal carrier block for either happy path."""

    lines = _sequence(observation.get("displayContent"))
    logs = _sequence(observation.get("logs"))
    if lines is None or logs is None or len(logs) != 2 or len(lines) not in {13, 14}:
        return False
    terminal_paths = {
        _path(_mapping(log).get("autoscanReport"))
        for log in logs
        if _mapping(log) is not None
    }
    displayed_paths = {
        segment.get("path")
        for raw_line in lines
        if (line := _mapping(raw_line)) is not None
        for raw_segment in (_sequence(line.get("segments")) or ())
        if (segment := _mapping(raw_segment)) is not None
        and segment.get("kind") == "path"
    }
    return None not in terminal_paths and terminal_paths <= displayed_paths


def _durable_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize two non-empty reports and the forbidden movement destination."""

    effects = _mapping(observation.get("durableEffects"))
    logs = _sequence(observation.get("logs"))
    if effects is None or logs is None:
        return False
    reports = _sequence(effects.get("reports"))
    unsolved = _mapping(effects.get("unsolvedLogs"))
    expected_paths = [
        _path(_mapping(log).get("autoscanReport"))
        for log in logs
        if _mapping(log) is not None
    ]
    return (
        reports is not None
        and len(reports) == 2
        and [report.get("path") for report in reports if isinstance(report, Mapping)]
        == expected_paths
        and all(
            isinstance(report, Mapping)
            and report.get("exists") is True
            and report.get("nonEmpty") is True
            for report in reports
        )
        and unsolved == {"path": "Unsolved Logs", "exists": False}
    )


_PREDICATE_FACTS = (
    ("scan-run.status", "run-status", ("Request",), _run_status),
    ("scan-run.discovery", "discovery", ("Request",), _discovery),
    ("scan-run.setup", "setup", ("Request",), _setup),
    (
        "scan-run.effective-concurrency",
        "effective-concurrency",
        ("Request",),
        _effective_concurrency,
    ),
    (
        "scan-run.installed-yaml-data",
        "installed-yaml-data",
        ("RunResult",),
        _installed_yaml_data,
    ),
    (
        "scan-run.log-outcomes",
        "log-outcomes",
        ("LogDisposition",),
        _log_outcomes,
    ),
    ("scan-run.events", "events", ("RunResult",), _events),
    (
        "scan-run.display-content",
        "display-content",
        ("RunResult",),
        _display_content,
    ),
    (
        "scan-run.durable-effects",
        "durable-effects",
        ("RunResult",),
        _durable_effects,
    ),
)

REQUIRED_OBSERVATION_FACT_IDS = tuple(sorted(row[0] for row in _PREDICATE_FACTS))
"""Every semantic fact required from both base happy-path scenarios."""

CRASH_LOG_SCAN_RUN_COVERAGE_POLICY = FamilyCoveragePolicy(
    family_id="crash-log-scan-run",
    predicates=tuple(
        CoveragePredicate(
            id=fact_id,
            capability_id="scan-run.execute",
            action="scan-run.execute",
            observation_family=observation_family,
            rust_symbols=rust_symbols,
            matches=matches,
        )
        for fact_id, observation_family, rust_symbols, matches in _PREDICATE_FACTS
    ),
)
"""The centrally derived coverage policy for Crash Log Scan Run v1."""
