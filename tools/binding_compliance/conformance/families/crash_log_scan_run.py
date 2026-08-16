"""Coverage policy for executable Crash Log Scan Run conformance."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_MAIN_SHA256 = "934f888a914fa210688d2b3f17ed003d7ee57efa1d695486c20907456a697ac4"
_GAME_SHA256 = "5ff58f93e2018429043a00b11b43c0199b927b984f809a103eb80aa29f7b2168"
_IGNORE_SHA256 = "1fc79ee2668e143c355dc3b931de1a2c41041227e79e21890da90a744ad3b70c"
_GENERATED_IGNORE_SHA256 = (
    "ba0cbe71c9023ebdb553e3a0acdc5c6ad95e9126694077344f4c57f00e3b71e3"
)
_MALFORMED_IGNORE_SHA256 = (
    "7f6069e760bd534446c062534a54d3766e42ca7841a0d485a2d9af3e42c0cc11"
)
_LARGE_MALFORMED_IGNORE_SHA256 = (
    "2cdeab79c003cd00910cdbcc55abcb31070c28115fc596e3dcbddac083ec305d"
)
_LOCAL_IGNORE_PATH = "CLASSIC Data/CLASSIC Ignore.yaml"
_BACKUP_PARENT = "CLASSIC Backup/YAML Data/Local Ignore"
_TRACE = (
    ("log_queued", None),
    ("log_started", None),
    ("log_phase", "setup"),
    ("log_phase", "parse"),
    ("log_phase", "analyze"),
    ("log_phase", "finalize"),
    ("log_finished", None),
)
_COMPACT_SUCCESS_TRACE = (
    "log_queued",
    "log_started",
    "log_phase:setup",
    "log_phase:parse",
    "log_phase:analyze",
    "log_phase:finalize",
    "log_finished:succeeded",
)
_RECOVERY_PROMPT = {
    "displaySeverities": ["warning"],
    "decisions": [
        {
            "decision": "proceed_without_ignore",
            "label": "Proceed Without Ignore",
            "available": True,
        },
        {
            "decision": "reset_to_default",
            "label": "Reset To Default",
            "available": True,
        },
    ],
}


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


def _diagnostics(value: object, kinds: Sequence[str]) -> bool:
    """Match ordered, path-attributed Local Ignore diagnostic kinds."""

    diagnostics = _sequence(value)
    if diagnostics is None or len(diagnostics) != len(kinds):
        return False
    return all(
        diagnostic
        == {
            "role": None,
            "candidate": None,
            "path": {"path": _LOCAL_IGNORE_PATH},
            "kind": kind,
        }
        for diagnostic, kind in zip(diagnostics, kinds, strict=True)
    )


def _compact_installed_yaml_data(
    value: object,
    *,
    local_ignore_state: str,
    local_ignore_sha256: str,
    local_ignore_byte_length: int,
    diagnostic_kinds: Sequence[str],
    reset_available: bool,
) -> Mapping[str, Any] | None:
    """Validate stable identities and Local Ignore state in a compact projection."""

    installed = _mapping(value)
    if (
        installed is None
        or not _identity(installed.get("mainIdentity"), _MAIN_SHA256, 281)
        or not _identity(installed.get("gameIdentity"), _GAME_SHA256, 463)
        or installed.get("localIgnoreState") != local_ignore_state
        or not _identity(
            installed.get("localIgnoreIdentity"),
            local_ignore_sha256,
            local_ignore_byte_length,
        )
        or not _diagnostics(installed.get("diagnostics"), diagnostic_kinds)
        or installed.get("localIgnoreResetAvailable") is not reset_available
    ):
        return None
    return installed


def _compact_discovery(value: object, stem: str) -> bool:
    """Match retained targeted discovery, including one post-pause late path."""

    discovery = _mapping(value)
    if discovery is None:
        return False
    accepted = f"Recovery/{stem}.log"
    late = f"Recovery/{stem}-late.log"
    return discovery == {
        "source": "targeted",
        "acceptedLogs": [{"path": accepted}],
        "rejectedInputs": [{"path": late, "reason": "path does not exist"}],
        "searchedLocations": [{"path": accepted}, {"path": late}],
    }


def _compact_log(value: object, stem: str, disposition: str) -> bool:
    """Match one discovery-indexed compact terminal log outcome."""

    log = _mapping(value)
    if log is None:
        return False
    expected_report = (
        {"path": f"Recovery/{stem}-AUTOSCAN.md"} if disposition == "succeeded" else None
    )
    expected_message = None if disposition == "succeeded" else "Cancelled by user"
    return log == {
        "discoveryIndex": 0,
        "crashLog": {"path": f"Recovery/{stem}.log"},
        "autoscanReport": expected_report,
        "disposition": disposition,
        "failures": [],
        "message": expected_message,
        "movedToUnsolvedLogs": False,
    }


def _compact_success_events(value: object) -> bool:
    """Match a resumed trace that cannot contain a rediscovery event."""

    return value == {
        "run": ["effective_concurrency_selected"],
        "logs": [{"discoveryIndex": 0, "trace": list(_COMPACT_SUCCESS_TRACE)}],
    }


def _initial_recovery_snapshot(
    observation: Mapping[str, Any],
    stem: str,
    *,
    local_ignore_sha256: str = _MALFORMED_IGNORE_SHA256,
    local_ignore_byte_length: int = 39,
) -> bool:
    """Recognize prepared discovery and YAML identities retained at the pause."""

    initial = _mapping(observation.get("initial"))
    if initial is None:
        return False
    installed = _compact_installed_yaml_data(
        initial.get("installedYamlData"),
        local_ignore_state="recovery_required",
        local_ignore_sha256=local_ignore_sha256,
        local_ignore_byte_length=local_ignore_byte_length,
        diagnostic_kinds=("parse",),
        reset_available=True,
    )
    return (
        _compact_discovery(initial.get("discovery"), stem)
        and installed is not None
        and installed.get("localIgnoreReset") is None
        and initial.get("logs") == []
        and initial.get("events")
        == {
            "run": ["discovery_completed"],
            "logs": [],
        }
    )


def _initial_recovery_prompt(observation: Mapping[str, Any]) -> bool:
    """Recognize a typed recovery pause with both explicit available decisions."""

    initial = _mapping(observation.get("initial"))
    run = _mapping(initial.get("run")) if initial is not None else None
    return (
        initial is not None
        and run
        == {
            "status": "local_ignore_recovery_required",
            "message": "Local Ignore recovery is required",
            "total": 1,
            "succeeded": 0,
            "failed": 0,
            "cancelled": 0,
            "effectiveConcurrency": None,
        }
        and initial.get("continuationAvailable") is True
        and initial.get("recoveryPrompt") == _RECOVERY_PROMPT
    )


def _resume_initial_prompt(observation: Mapping[str, Any]) -> bool:
    """Recognize the prompt in every explicit continuation decision scenario."""

    initial = _mapping(observation.get("initial"))
    return (
        _initial_recovery_prompt(observation)
        and initial is not None
        and any(
            _compact_discovery(initial.get("discovery"), stem)
            for stem in (
                "proceed",
                "reset",
                "reset-conflict",
                "reset-operational",
                "reset-pre-cancelled",
                "reset-post-critical",
            )
        )
    )


def _successful_recovery_terminal(
    observation: Mapping[str, Any],
    stem: str,
    *,
    state: str,
    ignore_sha256: str,
    ignore_byte_length: int,
    diagnostic_kinds: Sequence[str],
) -> Mapping[str, Any] | None:
    """Validate shared terminal success facts for one retained continuation."""

    terminal = _mapping(observation.get("terminal"))
    if terminal is None:
        return None
    installed = _compact_installed_yaml_data(
        terminal.get("installedYamlData"),
        local_ignore_state=state,
        local_ignore_sha256=ignore_sha256,
        local_ignore_byte_length=ignore_byte_length,
        diagnostic_kinds=diagnostic_kinds,
        reset_available=False,
    )
    logs = _sequence(terminal.get("logs"))
    if (
        terminal.get("run")
        != {
            "status": "completed",
            "message": None,
            "total": 1,
            "succeeded": 1,
            "failed": 0,
            "cancelled": 0,
            "effectiveConcurrency": 1,
        }
        or installed is None
        or logs is None
        or len(logs) != 1
        or not _compact_log(logs[0], stem, "succeeded")
        or terminal.get("continuationAvailable") is not False
        or terminal.get("recoveryPrompt") is not None
    ):
        return None
    return installed


def _retained_without_rediscovery(observation: Mapping[str, Any], stem: str) -> bool:
    """Recognize identical discovery and a resume trace that starts after discovery."""

    initial = _mapping(observation.get("initial"))
    terminal = _mapping(observation.get("terminal"))
    return (
        initial is not None
        and terminal is not None
        and initial.get("discovery") == terminal.get("discovery")
        and _compact_discovery(terminal.get("discovery"), stem)
        and _compact_success_events(terminal.get("events"))
    )


def _consumed_replay(value: object, operation: str, decision: str | None) -> bool:
    """Match one typed rejection from reusing the prepared continuation."""

    replay = _mapping(value)
    error = _mapping(replay.get("error")) if replay is not None else None
    return (
        replay is not None
        and replay.get("operation") == operation
        and replay.get("decision") == decision
        and error is not None
        and error.get("kind") == "scan_run_continuation_consumed"
        and error.get("message")
        == "Crash Log Scan Run continuation was already consumed"
        and error.get("displaySeverities") == ["failure", "notice"]
    )


def _all_forbidden_absent(value: object, paths: Sequence[str]) -> bool:
    """Match an exact forbidden-effect inventory with every path still absent."""

    forbidden = _sequence(value)
    return forbidden is not None and forbidden == [
        {"path": path, "exists": False, "identity": None} for path in paths
    ]


def _report_effect(
    value: object,
    path: str,
    sha256: str,
    byte_length: int,
) -> bool:
    """Match one non-empty report with its exact retained byte identity."""

    report = _mapping(value)
    identity = _mapping(report.get("identity")) if report is not None else None
    return (
        report is not None
        and report.get("path") == path
        and report.get("exists") is True
        and report.get("nonEmpty") is True
        and _identity(identity, sha256, byte_length)
    )


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


def _pre_discovery_cancelled_status(observation: Mapping[str, Any]) -> bool:
    """Recognize cancellation before discovery can retain any run work."""

    run = _mapping(observation.get("run"))
    return run == {
        "status": "cancelled_before_discovery",
        "message": "Cancelled before crash log discovery",
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "cancelled": 0,
        "effectiveConcurrency": None,
    }


def _pre_discovery_cancelled_boundary(observation: Mapping[str, Any]) -> bool:
    """Recognize the empty discovery, outcome, and ordered-event boundary."""

    return (
        observation.get("discovery") is None
        and observation.get("logs") == []
        and observation.get("events") == {"run": [], "logs": []}
        and observation.get("observerFailure") is None
    )


def _pre_discovery_cancellation_requested(observation: Mapping[str, Any]) -> bool:
    """Recognize the pre-discovery control remaining cancelled after execution."""

    return _pre_discovery_cancelled_status(observation) and observation.get(
        "cancellation"
    ) == {"requested": True}


def _pre_discovery_forbidden_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize that pre-discovery cancellation publishes no durable artifacts."""

    return observation.get("durableEffects") == {
        "reports": [],
        "forbidden": [
            {
                "path": "Lifecycle/crash-pre-discovery-01-AUTOSCAN.md",
                "exists": False,
            },
            {
                "path": "Lifecycle/crash-pre-discovery-02-AUTOSCAN.md",
                "exists": False,
            },
            {"path": "Unsolved Logs", "exists": False},
        ],
    }


def _queued_cancelled_status(observation: Mapping[str, Any]) -> bool:
    """Recognize the all-queued post-discovery terminal status."""

    return observation.get("run") == {
        "status": "cancelled",
        "message": None,
        "total": 2,
        "succeeded": 0,
        "failed": 0,
        "cancelled": 2,
        "effectiveConcurrency": 1,
    }


def _queued_cancellation_requested(observation: Mapping[str, Any]) -> bool:
    """Recognize the queued-boundary control remaining cancelled after execution."""

    return _queued_cancelled_status(observation) and observation.get(
        "cancellation"
    ) == {"requested": True}


def _queued_cancelled_boundary(observation: Mapping[str, Any]) -> bool:
    """Recognize two queued logs finishing cancelled without either admission."""

    paths = (
        "Lifecycle/crash-queued-01.log",
        "Lifecycle/crash-queued-02.log",
    )
    return (
        observation.get("discovery")
        == {
            "source": "targeted",
            "acceptedLogs": [{"path": path} for path in paths],
            "rejectedInputs": [],
            "searchedLocations": [{"path": path} for path in paths],
        }
        and observation.get("logs")
        == [
            {
                "discoveryIndex": index,
                "crashLog": {"path": path},
                "autoscanReport": None,
                "disposition": "cancelled_before_start",
                "failures": [],
                "message": "Cancelled by user",
                "movedToUnsolvedLogs": False,
            }
            for index, path in enumerate(paths)
        ]
        and observation.get("events")
        == {
            "run": ["discovery_completed", "effective_concurrency_selected"],
            "logs": [
                {
                    "discoveryIndex": index,
                    "trace": [
                        "log_queued",
                        "log_finished:cancelled_before_start",
                    ],
                }
                for index in range(2)
            ],
        }
        and observation.get("observerFailure") is None
    )


def _queued_cancelled_forbidden_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize that queued cancellation publishes no report or movement."""

    return observation.get("durableEffects") == {
        "reports": [],
        "forbidden": [
            {
                "path": "Lifecycle/crash-queued-01-AUTOSCAN.md",
                "exists": False,
            },
            {
                "path": "Lifecycle/crash-queued-02-AUTOSCAN.md",
                "exists": False,
            },
            {"path": "Unsolved Logs", "exists": False},
        ],
    }


def _admitted_cancelled_status(observation: Mapping[str, Any]) -> bool:
    """Recognize one admitted success and one unstarted cancelled log."""

    return observation.get("run") == {
        "status": "cancelled",
        "message": None,
        "total": 2,
        "succeeded": 1,
        "failed": 0,
        "cancelled": 1,
        "effectiveConcurrency": 1,
    }


def _admitted_cancellation_requested(observation: Mapping[str, Any]) -> bool:
    """Recognize the admitted-boundary control remaining cancelled at return."""

    return _admitted_cancelled_status(observation) and observation.get(
        "cancellation"
    ) == {"requested": True}


def _admitted_cancelled_boundary(observation: Mapping[str, Any]) -> bool:
    """Recognize the admitted log's full trace and the later unstarted log."""

    paths = (
        "Lifecycle/crash-admitted-01.log",
        "Lifecycle/crash-admitted-02.log",
    )
    return (
        observation.get("discovery")
        == {
            "source": "targeted",
            "acceptedLogs": [{"path": path} for path in paths],
            "rejectedInputs": [],
            "searchedLocations": [{"path": path} for path in paths],
        }
        and observation.get("logs")
        == [
            {
                "discoveryIndex": 0,
                "crashLog": {"path": paths[0]},
                "autoscanReport": {"path": "Lifecycle/crash-admitted-01-AUTOSCAN.md"},
                "disposition": "succeeded",
                "failures": [],
                "message": None,
                "movedToUnsolvedLogs": False,
            },
            {
                "discoveryIndex": 1,
                "crashLog": {"path": paths[1]},
                "autoscanReport": None,
                "disposition": "cancelled_before_start",
                "failures": [],
                "message": "Cancelled by user",
                "movedToUnsolvedLogs": False,
            },
        ]
        and observation.get("events")
        == {
            "run": ["discovery_completed", "effective_concurrency_selected"],
            "logs": [
                {
                    "discoveryIndex": 0,
                    "trace": [
                        "log_queued",
                        "log_started",
                        "log_phase:setup",
                        "log_phase:parse",
                        "log_phase:analyze",
                        "log_phase:finalize",
                        "log_finished:succeeded",
                    ],
                },
                {
                    "discoveryIndex": 1,
                    "trace": [
                        "log_queued",
                        "log_finished:cancelled_before_start",
                    ],
                },
            ],
        }
        and observation.get("observerFailure") is None
    )


def _admitted_durable_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize durable completion for admitted work and no later artifacts."""

    return observation.get("durableEffects") == {
        "reports": [
            {
                "path": "Lifecycle/crash-admitted-01-AUTOSCAN.md",
                "exists": True,
                "nonEmpty": True,
            }
        ],
        "forbidden": [
            {
                "path": "Lifecycle/crash-admitted-02-AUTOSCAN.md",
                "exists": False,
            },
            {"path": "Unsolved Logs", "exists": False},
        ],
    }


def _observer_failure_status(observation: Mapping[str, Any]) -> bool:
    """Recognize safe cancellation immediately after discovery delivery fails."""

    return observation.get("run") == {
        "status": "cancelled",
        "message": "Cancelled after crash log discovery",
        "total": 1,
        "succeeded": 0,
        "failed": 0,
        "cancelled": 1,
        "effectiveConcurrency": None,
    }


def _observer_failure_boundary(observation: Mapping[str, Any]) -> bool:
    """Recognize retained discovery with no later event delivered or work admitted."""

    path = "Lifecycle/crash-observer-failure.log"
    return (
        observation.get("discovery")
        == {
            "source": "targeted",
            "acceptedLogs": [{"path": path}],
            "rejectedInputs": [],
            "searchedLocations": [{"path": path}],
        }
        and observation.get("logs")
        == [
            {
                "discoveryIndex": 0,
                "crashLog": {"path": path},
                "autoscanReport": None,
                "disposition": "cancelled_before_start",
                "failures": [],
                "message": "Cancelled by user",
                "movedToUnsolvedLogs": False,
            }
        ]
        and observation.get("events")
        == {
            "run": ["discovery_completed"],
            "logs": [{"discoveryIndex": 0, "trace": []}],
        }
    )


def _observer_failure_observed(observation: Mapping[str, Any]) -> bool:
    """Recognize the structured adapter-delivery failure observation."""

    return observation.get("observerFailure") == {
        "kind": "observer_delivery_failure",
        "eventKind": "discovery_completed",
        "messageNonEmpty": True,
    }


def _observer_failure_cancellation_requested(
    observation: Mapping[str, Any],
) -> bool:
    """Recognize cancellation requested separately after observer failure."""

    return _observer_failure_status(observation) and observation.get(
        "cancellation"
    ) == {"requested": True}


def _observer_failure_forbidden_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize observer failure prevents reports and movement artifacts."""

    return observation.get("durableEffects") == {
        "reports": [],
        "forbidden": [
            {
                "path": "Lifecycle/crash-observer-failure-AUTOSCAN.md",
                "exists": False,
            },
            {"path": "Unsolved Logs", "exists": False},
        ],
    }


def _generated_status(observation: Mapping[str, Any]) -> bool:
    """Recognize the one-log generated-Ignore terminal status."""

    return observation.get("run") == {
        "status": "completed",
        "message": None,
        "total": 1,
        "succeeded": 1,
        "failed": 0,
        "cancelled": 0,
        "effectiveConcurrency": 1,
    }


def _generated_discovery(observation: Mapping[str, Any]) -> bool:
    """Recognize the generated-Ignore scenario's exact targeted discovery."""

    return observation.get("discovery") == {
        "source": "targeted",
        "acceptedLogs": [{"path": "Generated/crash-generated-local-ignore.log"}],
        "rejectedInputs": [],
        "searchedLocations": [{"path": "Generated/crash-generated-local-ignore.log"}],
    }


def _generated_installed_yaml_data(observation: Mapping[str, Any]) -> bool:
    """Recognize the exact generated Local Ignore identity and diagnostic."""

    installed = _compact_installed_yaml_data(
        observation.get("installedYamlData"),
        local_ignore_state="generated",
        local_ignore_sha256=_GENERATED_IGNORE_SHA256,
        local_ignore_byte_length=28,
        diagnostic_kinds=("local_ignore_generated",),
        reset_available=False,
    )
    return (
        installed is not None
        and installed.get("localIgnoreReset") is None
        and observation.get("continuationAvailable") is False
        and observation.get("recoveryPrompt") is None
    )


def _generated_log_outcome(observation: Mapping[str, Any]) -> bool:
    """Recognize the generated-Ignore scenario's sole successful outcome."""

    logs = _sequence(observation.get("logs"))
    return (
        logs is not None
        and len(logs) == 1
        and logs[0]
        == {
            "discoveryIndex": 0,
            "crashLog": {"path": "Generated/crash-generated-local-ignore.log"},
            "autoscanReport": {
                "path": "Generated/crash-generated-local-ignore-AUTOSCAN.md"
            },
            "disposition": "succeeded",
            "failures": [],
            "message": None,
            "movedToUnsolvedLogs": False,
        }
    )


def _generated_events(observation: Mapping[str, Any]) -> bool:
    """Recognize the generated-Ignore scenario's compact lifecycle trace."""

    return observation.get("events") == {
        "run": ["discovery_completed", "effective_concurrency_selected"],
        "logs": [{"discoveryIndex": 0, "trace": list(_COMPACT_SUCCESS_TRACE)}],
    }


def _generated_durable_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize generated bytes, one report, and every forbidden effect."""

    effects = _mapping(observation.get("durableEffects"))
    reports = _sequence(effects.get("reports")) if effects is not None else None
    return (
        effects is not None
        and effects.get("localIgnore")
        == {
            "path": _LOCAL_IGNORE_PATH,
            "exists": True,
            "identity": {
                "sha256": _GENERATED_IGNORE_SHA256,
                "byteLength": 28,
            },
        }
        and effects.get("backups") == []
        and reports is not None
        and len(reports) == 1
        and _report_effect(
            reports[0],
            "Generated/crash-generated-local-ignore-AUTOSCAN.md",
            "6b62381b815b5febd0b1cbf5a3bb4a9638187e21c08fb7a0ee293ffd93881133",
            1042,
        )
        and _all_forbidden_absent(
            effects.get("forbidden"),
            (_LOCAL_IGNORE_PATH + ".prev", "Unsolved Logs"),
        )
    )


def _proceed_terminal(observation: Mapping[str, Any]) -> bool:
    """Recognize successful Proceed Without Ignore terminal state."""

    installed = _successful_recovery_terminal(
        observation,
        "proceed",
        state="proceed_without_ignore",
        ignore_sha256=_MALFORMED_IGNORE_SHA256,
        ignore_byte_length=39,
        diagnostic_kinds=("parse",),
    )
    return installed is not None and installed.get("localIgnoreReset") is None


def _proceed_no_rediscovery(observation: Mapping[str, Any]) -> bool:
    """Recognize Proceed using the retained discovery after late files appear."""

    return _retained_without_rediscovery(observation, "proceed")


def _proceed_durable_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize byte-exact non-mutation and forbidden Proceed effects."""

    effects = _mapping(observation.get("durableEffects"))
    reports = _sequence(effects.get("reports")) if effects is not None else None
    return (
        effects is not None
        and effects.get("localIgnore")
        == {
            "path": _LOCAL_IGNORE_PATH,
            "exists": True,
            "identity": {
                "sha256": _MALFORMED_IGNORE_SHA256,
                "byteLength": 39,
            },
        }
        and effects.get("backups") == []
        and reports is not None
        and len(reports) == 1
        and _report_effect(
            reports[0],
            "Recovery/proceed-AUTOSCAN.md",
            "fcd495692097a88127999ca1905d2a93cdf120b62c131976bfde86806425c37f",
            1021,
        )
        and _all_forbidden_absent(
            effects.get("forbidden"),
            (
                _LOCAL_IGNORE_PATH + ".prev",
                "Unsolved Logs",
                "Recovery/proceed-late-AUTOSCAN.md",
            ),
        )
        and observation.get("cancellation")
        == {
            "beforeTerminal": False,
            "afterTerminal": False,
            "afterReplays": False,
        }
    )


def _proceed_replay(observation: Mapping[str, Any]) -> bool:
    """Recognize one rejected Proceed replay on the already claimed continuation."""

    replays = _sequence(observation.get("replays"))
    return (
        replays is not None
        and len(replays) == 1
        and _consumed_replay(replays[0], "resume", "proceed_without_ignore")
    )


def _reset_terminal(observation: Mapping[str, Any]) -> bool:
    """Recognize successful Reset To Default terminal state and receipt."""

    installed = _successful_recovery_terminal(
        observation,
        "reset",
        state="reset_to_default",
        ignore_sha256=_GENERATED_IGNORE_SHA256,
        ignore_byte_length=28,
        diagnostic_kinds=("parse", "local_ignore_reset"),
    )
    if installed is None:
        return False
    reset = _mapping(installed.get("localIgnoreReset"))
    return (
        reset is not None
        and reset.get("localIgnorePath") == {"path": _LOCAL_IGNORE_PATH}
        and reset.get("backup")
        == {
            "parentPath": _BACKUP_PARENT,
            "exists": True,
            "identityMatchesReceipt": True,
        }
        and _identity(reset.get("malformedIdentity"), _MALFORMED_IGNORE_SHA256, 39)
        and _identity(reset.get("backupIdentity"), _MALFORMED_IGNORE_SHA256, 39)
        and _identity(reset.get("replacementIdentity"), _GENERATED_IGNORE_SHA256, 28)
    )


def _reset_no_rediscovery(observation: Mapping[str, Any]) -> bool:
    """Recognize Reset using the retained discovery after late files appear."""

    return _retained_without_rediscovery(observation, "reset")


def _reset_durable_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize one byte-exact backup, repaired bytes, and forbidden effects."""

    effects = _mapping(observation.get("durableEffects"))
    backups = _sequence(effects.get("backups")) if effects is not None else None
    reports = _sequence(effects.get("reports")) if effects is not None else None
    return (
        effects is not None
        and effects.get("localIgnore")
        == {
            "path": _LOCAL_IGNORE_PATH,
            "exists": True,
            "identity": {
                "sha256": _GENERATED_IGNORE_SHA256,
                "byteLength": 28,
            },
        }
        and backups
        == [
            {
                "parentPath": _BACKUP_PARENT,
                "identity": {
                    "sha256": _MALFORMED_IGNORE_SHA256,
                    "byteLength": 39,
                },
            }
        ]
        and reports is not None
        and len(reports) == 1
        and _report_effect(
            reports[0],
            "Recovery/reset-AUTOSCAN.md",
            "ff71d48fbc44a50ca1e29d2be906034c9ebf63cb3099641f897c6b8bea6e903b",
            1019,
        )
        and _all_forbidden_absent(
            effects.get("forbidden"),
            (
                _LOCAL_IGNORE_PATH + ".prev",
                "Unsolved Logs",
                "Recovery/reset-late-AUTOSCAN.md",
            ),
        )
        and observation.get("cancellation")
        == {
            "beforeTerminal": False,
            "afterTerminal": False,
            "afterReplays": False,
        }
    )


def _reset_replay(observation: Mapping[str, Any]) -> bool:
    """Recognize one rejected Reset replay without a second backup."""

    replays = _sequence(observation.get("replays"))
    return (
        replays is not None
        and len(replays) == 1
        and _consumed_replay(replays[0], "resume", "reset_to_default")
    )


def _reset_terminal_error(
    observation: Mapping[str, Any],
    *,
    kind: str,
    path: str | None,
    expected_identity: tuple[str, int] | None,
    actual_identity: tuple[str, int] | None,
    display_severities: Sequence[str],
) -> bool:
    """Match one normalized typed reset rejection and its stable diagnostics."""

    error = _mapping(observation.get("terminalError"))
    if observation.get("terminal") is not None or error is None:
        return False
    expected = (
        {"sha256": expected_identity[0], "byteLength": expected_identity[1]}
        if expected_identity is not None
        else None
    )
    actual = (
        {"sha256": actual_identity[0], "byteLength": actual_identity[1]}
        if actual_identity is not None
        else None
    )
    return error == {
        "kind": kind,
        "code": kind,
        "messageNonEmpty": True,
        "path": {"path": path} if path is not None else None,
        "stage": None,
        "expectedIdentity": expected,
        "actualIdentity": actual,
        "backupPath": None,
        "malformedIdentity": None,
        "backupIdentity": None,
        "replacementIdentity": None,
        "displaySeverities": list(display_severities),
        "events": [],
    }


def _reset_nonmutating_effects(
    observation: Mapping[str, Any],
    *,
    stem: str,
    local_ignore_sha256: str,
    local_ignore_byte_length: int,
    cancellation: Mapping[str, bool],
    extra_forbidden_paths: Sequence[str] = (),
) -> bool:
    """Prove an interrupted reset wrote no backup, report, replacement, or stray path."""

    effects = _mapping(observation.get("durableEffects"))
    return (
        effects is not None
        and effects.get("localIgnore")
        == {
            "path": _LOCAL_IGNORE_PATH,
            "exists": True,
            "identity": {
                "sha256": local_ignore_sha256,
                "byteLength": local_ignore_byte_length,
            },
        }
        and effects.get("backups") == []
        and effects.get("reports") == []
        and _all_forbidden_absent(
            effects.get("forbidden"),
            (
                _LOCAL_IGNORE_PATH + ".prev",
                "Unsolved Logs",
                f"Recovery/{stem}-AUTOSCAN.md",
                f"Recovery/{stem}-late-AUTOSCAN.md",
                *extra_forbidden_paths,
            ),
        )
        and observation.get("cancellation") == cancellation
    )


def _reset_conflict_terminal(observation: Mapping[str, Any]) -> bool:
    """Recognize an early identity conflict without accepting an overwrite."""

    return _reset_terminal_error(
        observation,
        kind="local_ignore_reset_conflict",
        path=None,
        expected_identity=(_MALFORMED_IGNORE_SHA256, 39),
        actual_identity=(_IGNORE_SHA256, 29),
        display_severities=("failure", "info", "info", "notice"),
    )


def _reset_conflict_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize preservation of intervening canonical bytes and zero reset effects."""

    return _reset_nonmutating_effects(
        observation,
        stem="reset-conflict",
        local_ignore_sha256=_IGNORE_SHA256,
        local_ignore_byte_length=29,
        cancellation={
            "beforeTerminal": False,
            "afterTerminal": False,
            "afterReplays": False,
        },
    )


def _reset_operational_failure_terminal(observation: Mapping[str, Any]) -> bool:
    """Recognize a portable backup-directory failure through the public seam."""

    return _reset_terminal_error(
        observation,
        kind="local_ignore_reset_backup_failure",
        path=_BACKUP_PARENT,
        expected_identity=None,
        actual_identity=None,
        display_severities=("failure", "failure", "info"),
    )


def _reset_operational_failure_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize an operational reset rejection before any durable mutation."""

    return _reset_nonmutating_effects(
        observation,
        stem="reset-operational",
        local_ignore_sha256=_MALFORMED_IGNORE_SHA256,
        local_ignore_byte_length=39,
        cancellation={
            "beforeTerminal": False,
            "afterTerminal": False,
            "afterReplays": False,
        },
    )


def _reset_pre_cancelled_terminal(observation: Mapping[str, Any]) -> bool:
    """Recognize cancellation before reset enters the durable transaction."""

    terminal = _mapping(observation.get("terminal"))
    logs = _sequence(terminal.get("logs")) if terminal is not None else None
    return (
        observation.get("terminalError") is None
        and terminal is not None
        and terminal.get("run")
        == {
            "status": "cancelled",
            "message": "Cancelled after crash log discovery",
            "total": 1,
            "succeeded": 0,
            "failed": 0,
            "cancelled": 1,
            "effectiveConcurrency": None,
        }
        and _compact_discovery(terminal.get("discovery"), "reset-pre-cancelled")
        and terminal.get("installedYamlData") is None
        and logs is not None
        and len(logs) == 1
        and _compact_log(logs[0], "reset-pre-cancelled", "cancelled_before_start")
        and terminal.get("events")
        == {"run": [], "logs": [{"discoveryIndex": 0, "trace": []}]}
        and terminal.get("continuationAvailable") is False
        and terminal.get("recoveryPrompt") is None
    )


def _reset_pre_cancelled_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize monotonic pre-reset cancellation with no filesystem mutation."""

    return _reset_nonmutating_effects(
        observation,
        stem="reset-pre-cancelled",
        local_ignore_sha256=_MALFORMED_IGNORE_SHA256,
        local_ignore_byte_length=39,
        cancellation={
            "beforeTerminal": True,
            "afterTerminal": True,
            "afterReplays": True,
        },
        extra_forbidden_paths=(".classic-local-ignore-reset.lock",),
    )


def _reset_post_critical_terminal(observation: Mapping[str, Any]) -> bool:
    """Recognize cancellation only after a complete durable reset receipt exists."""

    terminal = _mapping(observation.get("terminal"))
    if terminal is None or observation.get("terminalError") is not None:
        return False
    installed = _compact_installed_yaml_data(
        terminal.get("installedYamlData"),
        local_ignore_state="reset_to_default",
        local_ignore_sha256=_GENERATED_IGNORE_SHA256,
        local_ignore_byte_length=28,
        diagnostic_kinds=("parse", "local_ignore_reset"),
        reset_available=False,
    )
    reset = (
        _mapping(installed.get("localIgnoreReset")) if installed is not None else None
    )
    logs = _sequence(terminal.get("logs"))
    return (
        terminal.get("run")
        == {
            "status": "cancelled",
            "message": "Cancelled after crash log discovery",
            "total": 1,
            "succeeded": 0,
            "failed": 0,
            "cancelled": 1,
            "effectiveConcurrency": None,
        }
        and _compact_discovery(terminal.get("discovery"), "reset-post-critical")
        and reset is not None
        and reset.get("localIgnorePath") == {"path": _LOCAL_IGNORE_PATH}
        and reset.get("backup")
        == {
            "parentPath": _BACKUP_PARENT,
            "exists": True,
            "identityMatchesReceipt": True,
        }
        and _identity(
            reset.get("malformedIdentity"), _LARGE_MALFORMED_IGNORE_SHA256, 16_777_255
        )
        and _identity(
            reset.get("backupIdentity"), _LARGE_MALFORMED_IGNORE_SHA256, 16_777_255
        )
        and _identity(reset.get("replacementIdentity"), _GENERATED_IGNORE_SHA256, 28)
        and logs is not None
        and len(logs) == 1
        and _compact_log(logs[0], "reset-post-critical", "cancelled_before_start")
        and terminal.get("events")
        == {"run": [], "logs": [{"discoveryIndex": 0, "trace": []}]}
        and terminal.get("continuationAvailable") is False
        and terminal.get("recoveryPrompt") is None
    )


def _reset_post_critical_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize byte-exact repair before post-critical cancellation returns."""

    effects = _mapping(observation.get("durableEffects"))
    return (
        effects is not None
        and effects.get("localIgnore")
        == {
            "path": _LOCAL_IGNORE_PATH,
            "exists": True,
            "identity": {"sha256": _GENERATED_IGNORE_SHA256, "byteLength": 28},
        }
        and effects.get("backups")
        == [
            {
                "parentPath": _BACKUP_PARENT,
                "identity": {
                    "sha256": _LARGE_MALFORMED_IGNORE_SHA256,
                    "byteLength": 16_777_255,
                },
            }
        ]
        and effects.get("reports") == []
        and _all_forbidden_absent(
            effects.get("forbidden"),
            (
                _LOCAL_IGNORE_PATH + ".prev",
                "Unsolved Logs",
                "Recovery/reset-post-critical-AUTOSCAN.md",
                "Recovery/reset-post-critical-late-AUTOSCAN.md",
            ),
        )
        and observation.get("cancellation")
        == {
            "beforeTerminal": False,
            "afterTerminal": True,
            "afterReplays": True,
        }
    )


def _abandon_initial(observation: Mapping[str, Any]) -> bool:
    """Recognize the prepared abandonment snapshot and typed recovery prompt."""

    return _initial_recovery_snapshot(
        observation, "abandon"
    ) and _initial_recovery_prompt(observation)


def _abandon_terminal(observation: Mapping[str, Any]) -> bool:
    """Recognize ordinary post-discovery cancellation without recovery state."""

    terminal = _mapping(observation.get("terminal"))
    logs = _sequence(terminal.get("logs")) if terminal is not None else None
    return (
        terminal is not None
        and terminal.get("run")
        == {
            "status": "cancelled",
            "message": "Cancelled after crash log discovery",
            "total": 1,
            "succeeded": 0,
            "failed": 0,
            "cancelled": 1,
            "effectiveConcurrency": None,
        }
        and _compact_discovery(terminal.get("discovery"), "abandon")
        and terminal.get("installedYamlData") is None
        and logs is not None
        and len(logs) == 1
        and _compact_log(logs[0], "abandon", "cancelled_before_start")
        and terminal.get("events")
        == {"run": [], "logs": [{"discoveryIndex": 0, "trace": []}]}
        and terminal.get("continuationAvailable") is False
        and terminal.get("recoveryPrompt") is None
    )


def _abandon_cancellation(observation: Mapping[str, Any]) -> bool:
    """Recognize abandonment as the sole source of monotonic cancellation."""

    return _abandon_terminal(observation) and observation.get("cancellation") == {
        "beforeTerminal": False,
        "afterTerminal": True,
        "afterReplays": True,
    }


def _abandon_shared_replay(observation: Mapping[str, Any]) -> bool:
    """Recognize shared one-shot rejection through abandon and resume APIs."""

    replays = _sequence(observation.get("replays"))
    return (
        replays is not None
        and len(replays) == 2
        and _consumed_replay(replays[0], "abandon", None)
        and _consumed_replay(replays[1], "resume", "reset_to_default")
    )


def _abandon_durable_effects(observation: Mapping[str, Any]) -> bool:
    """Recognize byte-exact abandonment with no reports, backups, or movement."""

    effects = _mapping(observation.get("durableEffects"))
    return (
        effects is not None
        and effects.get("localIgnore")
        == {
            "path": _LOCAL_IGNORE_PATH,
            "exists": True,
            "identity": {
                "sha256": _MALFORMED_IGNORE_SHA256,
                "byteLength": 39,
            },
        }
        and effects.get("backups") == []
        and effects.get("reports") == []
        and _all_forbidden_absent(
            effects.get("forbidden"),
            (
                _LOCAL_IGNORE_PATH + ".prev",
                "Unsolved Logs",
                "Recovery/abandon-AUTOSCAN.md",
                "Recovery/abandon-late-AUTOSCAN.md",
            ),
        )
    )


_BASE_PREDICATE_FACTS = (
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

_BASE_PREDICATES = tuple(
    CoveragePredicate(
        id=fact_id,
        capability_id="scan-run.execute",
        action="scan-run.execute",
        observation_family=observation_family,
        rust_symbols=rust_symbols,
        matches=matches,
    )
    for fact_id, observation_family, rust_symbols, matches in _BASE_PREDICATE_FACTS
)

_PRE_DISCOVERY_CANCELLATION_PREDICATES = (
    CoveragePredicate(
        "scan-run.lifecycle.pre-discovery-status",
        "scan-run.execute",
        "scan-run.execute",
        "run-status",
        ("RunResult",),
        _pre_discovery_cancelled_status,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.pre-discovery-boundary",
        "scan-run.execute",
        "scan-run.execute",
        "events",
        ("RunResult", "LogDisposition"),
        _pre_discovery_cancelled_boundary,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.pre-discovery-cancellation",
        "scan-run.execute",
        "scan-run.execute",
        "cancellation",
        ("Cancellation",),
        _pre_discovery_cancellation_requested,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.pre-discovery-forbidden-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("RunResult",),
        _pre_discovery_forbidden_effects,
    ),
)

_QUEUED_CANCELLATION_PREDICATES = (
    CoveragePredicate(
        "scan-run.lifecycle.queued-status",
        "scan-run.execute",
        "scan-run.execute",
        "run-status",
        ("RunResult",),
        _queued_cancelled_status,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.queued-boundary",
        "scan-run.execute",
        "scan-run.execute",
        "events",
        ("RunResult", "LogDisposition"),
        _queued_cancelled_boundary,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.queued-cancellation",
        "scan-run.execute",
        "scan-run.execute",
        "cancellation",
        ("Cancellation",),
        _queued_cancellation_requested,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.queued-forbidden-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("RunResult",),
        _queued_cancelled_forbidden_effects,
    ),
)

_ADMITTED_CANCELLATION_PREDICATES = (
    CoveragePredicate(
        "scan-run.lifecycle.admitted-status",
        "scan-run.execute",
        "scan-run.execute",
        "run-status",
        ("RunResult",),
        _admitted_cancelled_status,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.admitted-boundary",
        "scan-run.execute",
        "scan-run.execute",
        "events",
        ("RunResult", "LogDisposition"),
        _admitted_cancelled_boundary,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.admitted-cancellation",
        "scan-run.execute",
        "scan-run.execute",
        "cancellation",
        ("Cancellation",),
        _admitted_cancellation_requested,
    ),
    CoveragePredicate(
        "scan-run.lifecycle.admitted-durable-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("RunResult",),
        _admitted_durable_effects,
    ),
)

_OBSERVER_FAILURE_PREDICATES = (
    CoveragePredicate(
        "scan-run.observer-failure.status",
        "scan-run.execute",
        "scan-run.execute",
        "run-status",
        ("RunResult",),
        _observer_failure_status,
    ),
    CoveragePredicate(
        "scan-run.observer-failure.boundary",
        "scan-run.execute",
        "scan-run.execute",
        "events",
        ("RunResult", "LogDisposition"),
        _observer_failure_boundary,
    ),
    CoveragePredicate(
        "scan-run.observer-failure.structured-observation",
        "scan-run.execute",
        "scan-run.execute",
        "observer-failure",
        ("Observer",),
        _observer_failure_observed,
    ),
    CoveragePredicate(
        "scan-run.observer-failure.cancellation",
        "scan-run.execute",
        "scan-run.execute",
        "cancellation",
        ("Cancellation",),
        _observer_failure_cancellation_requested,
    ),
    CoveragePredicate(
        "scan-run.observer-failure.forbidden-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("RunResult",),
        _observer_failure_forbidden_effects,
    ),
)

_GENERATED_PREDICATES = (
    CoveragePredicate(
        "scan-run.generated.status",
        "scan-run.execute",
        "scan-run.execute",
        "run-status",
        ("RunResult",),
        _generated_status,
    ),
    CoveragePredicate(
        "scan-run.generated.discovery",
        "scan-run.execute",
        "scan-run.execute",
        "discovery",
        ("Request",),
        _generated_discovery,
    ),
    CoveragePredicate(
        "scan-run.generated.installed-yaml-data",
        "scan-run.execute",
        "scan-run.execute",
        "installed-yaml-data",
        ("RunResult",),
        _generated_installed_yaml_data,
    ),
    CoveragePredicate(
        "scan-run.generated.log-outcome",
        "scan-run.execute",
        "scan-run.execute",
        "log-outcomes",
        ("LogDisposition",),
        _generated_log_outcome,
    ),
    CoveragePredicate(
        "scan-run.generated.events",
        "scan-run.execute",
        "scan-run.execute",
        "events",
        ("RunResult",),
        _generated_events,
    ),
    CoveragePredicate(
        "scan-run.generated.durable-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("RunResult",),
        _generated_durable_effects,
    ),
)

_RESUME_PREDICATES = (
    CoveragePredicate(
        "scan-run.recovery.initial-retained-snapshot",
        "scan-run.execute",
        "scan-run.execute",
        "recovery",
        ("CrashLogScanRunContinuation", "LocalIgnoreRecoveryDecision"),
        lambda observation: (
            _initial_recovery_snapshot(observation, "proceed")
            or _initial_recovery_snapshot(observation, "reset")
            or _initial_recovery_snapshot(observation, "reset-conflict")
            or _initial_recovery_snapshot(observation, "reset-operational")
            or _initial_recovery_snapshot(observation, "reset-pre-cancelled")
            or _initial_recovery_snapshot(
                observation,
                "reset-post-critical",
                local_ignore_sha256=_LARGE_MALFORMED_IGNORE_SHA256,
                local_ignore_byte_length=16_777_255,
            )
        ),
    ),
    CoveragePredicate(
        "scan-run.recovery.initial-prompt",
        "scan-run.execute",
        "scan-run.execute",
        "recovery",
        ("LocalIgnoreRecoveryDecision",),
        _resume_initial_prompt,
    ),
    CoveragePredicate(
        "scan-run.recovery.proceed-without-ignore",
        "scan-run.execute",
        "scan-run.execute",
        "installed-yaml-data",
        ("LocalIgnoreRecoveryDecision",),
        _proceed_terminal,
    ),
    CoveragePredicate(
        "scan-run.recovery.proceed-no-rediscovery",
        "scan-run.execute",
        "scan-run.execute",
        "events",
        ("LocalIgnoreRecoveryDecision",),
        _proceed_no_rediscovery,
    ),
    CoveragePredicate(
        "scan-run.recovery.proceed-no-mutation",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("LocalIgnoreRecoveryDecision",),
        _proceed_durable_effects,
    ),
    CoveragePredicate(
        "scan-run.recovery.proceed-replay-rejected",
        "scan-run.execute",
        "scan-run.execute",
        "replay",
        ("ResumeError",),
        _proceed_replay,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-to-default",
        "scan-run.execute",
        "scan-run.execute",
        "installed-yaml-data",
        ("LocalIgnoreRecoveryDecision",),
        _reset_terminal,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-no-rediscovery",
        "scan-run.execute",
        "scan-run.execute",
        "events",
        ("LocalIgnoreRecoveryDecision",),
        _reset_no_rediscovery,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-backup-and-repair",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("LocalIgnoreRecoveryDecision",),
        _reset_durable_effects,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-replay-rejected",
        "scan-run.execute",
        "scan-run.execute",
        "replay",
        ("ResumeError",),
        _reset_replay,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-conflict",
        "scan-run.execute",
        "scan-run.execute",
        "recovery",
        ("ResumeError", "LocalIgnoreResetConflictError"),
        _reset_conflict_terminal,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-conflict-forbidden-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("LocalIgnoreResetConflictError",),
        _reset_conflict_effects,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-operational-failure",
        "scan-run.execute",
        "scan-run.execute",
        "recovery",
        ("ResumeError", "LocalIgnoreResetFailure"),
        _reset_operational_failure_terminal,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-operational-forbidden-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("LocalIgnoreResetFailure",),
        _reset_operational_failure_effects,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-pre-cancelled",
        "scan-run.execute",
        "scan-run.execute",
        "recovery",
        ("Cancellation", "CrashLogScanRunContinuation"),
        _reset_pre_cancelled_terminal,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-pre-cancelled-forbidden-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("Cancellation",),
        _reset_pre_cancelled_effects,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-post-critical-cancelled",
        "scan-run.execute",
        "scan-run.execute",
        "recovery",
        ("Cancellation", "LocalIgnoreResetRunData"),
        _reset_post_critical_terminal,
    ),
    CoveragePredicate(
        "scan-run.recovery.reset-post-critical-durable-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("Cancellation", "LocalIgnoreResetRunData"),
        _reset_post_critical_effects,
    ),
)

_ABANDON_PREDICATES = (
    CoveragePredicate(
        "scan-run.recovery.abandon-initial",
        "scan-run.execute",
        "scan-run.execute",
        "recovery",
        ("CrashLogScanRunContinuation",),
        _abandon_initial,
    ),
    CoveragePredicate(
        "scan-run.recovery.abandon-terminal",
        "scan-run.execute",
        "scan-run.execute",
        "log-outcomes",
        ("CrashLogScanRunContinuation",),
        _abandon_terminal,
    ),
    CoveragePredicate(
        "scan-run.recovery.abandon-cancellation",
        "scan-run.execute",
        "scan-run.execute",
        "recovery",
        ("CrashLogScanRunContinuation",),
        _abandon_cancellation,
    ),
    CoveragePredicate(
        "scan-run.recovery.abandon-shared-replay",
        "scan-run.execute",
        "scan-run.execute",
        "replay",
        ("CrashLogScanRunContinuation", "ResumeError"),
        _abandon_shared_replay,
    ),
    CoveragePredicate(
        "scan-run.recovery.abandon-forbidden-effects",
        "scan-run.execute",
        "scan-run.execute",
        "durable-effects",
        ("CrashLogScanRunContinuation",),
        _abandon_durable_effects,
    ),
)

REQUIRED_OBSERVATION_FACT_IDS = tuple(
    sorted(predicate.id for predicate in _BASE_PREDICATES)
)
"""Every semantic fact required from both base happy-path scenarios."""

REQUIRED_OBSERVATION_FACT_IDS_BY_SCENARIO: Mapping[str, tuple[str, ...]] = {
    "standard-happy-path": REQUIRED_OBSERVATION_FACT_IDS,
    "targeted-happy-path": REQUIRED_OBSERVATION_FACT_IDS,
    "pre-discovery-cancelled": tuple(
        sorted(predicate.id for predicate in _PRE_DISCOVERY_CANCELLATION_PREDICATES)
    ),
    "post-discovery-queued-cancelled": tuple(
        sorted(predicate.id for predicate in _QUEUED_CANCELLATION_PREDICATES)
    ),
    "admitted-durable-cancelled": tuple(
        sorted(predicate.id for predicate in _ADMITTED_CANCELLATION_PREDICATES)
    ),
    "observer-delivery-failure": tuple(
        sorted(predicate.id for predicate in _OBSERVER_FAILURE_PREDICATES)
    ),
    "generated-local-ignore": tuple(
        sorted(predicate.id for predicate in _GENERATED_PREDICATES)
    ),
    "proceed-without-ignore-recovery": tuple(
        sorted(
            {
                "scan-run.recovery.initial-retained-snapshot",
                "scan-run.recovery.initial-prompt",
                "scan-run.recovery.proceed-without-ignore",
                "scan-run.recovery.proceed-no-rediscovery",
                "scan-run.recovery.proceed-no-mutation",
                "scan-run.recovery.proceed-replay-rejected",
            }
        )
    ),
    "reset-to-default-recovery": tuple(
        sorted(
            {
                "scan-run.recovery.initial-retained-snapshot",
                "scan-run.recovery.initial-prompt",
                "scan-run.recovery.reset-to-default",
                "scan-run.recovery.reset-no-rediscovery",
                "scan-run.recovery.reset-backup-and-repair",
                "scan-run.recovery.reset-replay-rejected",
            }
        )
    ),
    "reset-intervening-change-conflict": tuple(
        sorted(
            {
                "scan-run.recovery.initial-retained-snapshot",
                "scan-run.recovery.initial-prompt",
                "scan-run.recovery.reset-conflict",
                "scan-run.recovery.reset-conflict-forbidden-effects",
                "scan-run.recovery.reset-replay-rejected",
            }
        )
    ),
    "reset-operational-failure": tuple(
        sorted(
            {
                "scan-run.recovery.initial-retained-snapshot",
                "scan-run.recovery.initial-prompt",
                "scan-run.recovery.reset-operational-failure",
                "scan-run.recovery.reset-operational-forbidden-effects",
                "scan-run.recovery.reset-replay-rejected",
            }
        )
    ),
    "reset-pre-cancelled": tuple(
        sorted(
            {
                "scan-run.recovery.initial-retained-snapshot",
                "scan-run.recovery.initial-prompt",
                "scan-run.recovery.reset-pre-cancelled",
                "scan-run.recovery.reset-pre-cancelled-forbidden-effects",
                "scan-run.recovery.reset-replay-rejected",
            }
        )
    ),
    "reset-post-critical-cancelled": tuple(
        sorted(
            {
                "scan-run.recovery.initial-retained-snapshot",
                "scan-run.recovery.initial-prompt",
                "scan-run.recovery.reset-post-critical-cancelled",
                "scan-run.recovery.reset-post-critical-durable-effects",
                "scan-run.recovery.reset-replay-rejected",
            }
        )
    ),
    "abandon-local-ignore-recovery": tuple(
        sorted(predicate.id for predicate in _ABANDON_PREDICATES)
    ),
}
"""Exact centrally derived semantic fact IDs required by each v1 scenario."""

CRASH_LOG_SCAN_RUN_COVERAGE_POLICY = FamilyCoveragePolicy(
    family_id="crash-log-scan-run",
    predicates=(
        _BASE_PREDICATES
        + _PRE_DISCOVERY_CANCELLATION_PREDICATES
        + _QUEUED_CANCELLATION_PREDICATES
        + _ADMITTED_CANCELLATION_PREDICATES
        + _OBSERVER_FAILURE_PREDICATES
        + _GENERATED_PREDICATES
        + _RESUME_PREDICATES
        + _ABANDON_PREDICATES
    ),
)
"""The centrally derived coverage policy for Crash Log Scan Run v1."""
