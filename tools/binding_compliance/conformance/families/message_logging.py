"""Exact emitted logging contracts from initialized native adapters."""

import json
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_EXPECTED = {
    "basic": {
        "records": [
            {"level": "INFO", "message": "fixture-info"},
            {"level": "WARN", "message": "fixture-warning"},
            {"level": "ERROR", "message": "fixture-error"},
            {"level": "DEBUG", "message": "fixture-debug"},
        ]
    },
    "extended": {
        "records": [
            {"level": "TRACE", "message": "fixture-trace"},
            {"level": "INFO", "message": "fixture-dynamic"},
            {
                "level": "WARN",
                "message": "fixture-title: fixture-message - fixture-details",
            },
        ],
        "enabled": [True, True, True, True],
        "name": "CLASSIC",
        "invalidLog": True,
        "invalidEnabled": True,
    },
    "startup": {
        "records": [
            {"level": "TRACE", "message": "fixture-trace"},
            {
                "level": "INFO",
                "message": "event=classic.startup.binding_contract.validated "
                "severity=info component=integration.startup outcome=success "
                "checked_bindings=2 contract=fixture correlation_id=case",
            },
            {
                "level": "ERROR",
                "message": "event=classic.startup.binding_contract.failed severity=error "
                "component=integration.startup outcome=failure "
                "contract=fixture correlation_id=case error=fixture-error "
                "failure_hint=retry failure_type=fixture "
                "missing_binding=fixture-binding",
            },
            {
                "level": "INFO",
                "message": "event=classic.startup.acceleration.status severity=info "
                "component=integration.startup outcome=success "
                "acceleration_level=fixture active_components=1 "
                "correlation_id=case total_components=2",
            },
        ]
    },
    "format": {
        "records": [],
        "formatted": "event=fixture.event severity=warning component=conformance outcome=ok "
        'count=2 label="two words"',
    },
}
_INPUTS = {
    "basic": {
        "operation": "basic",
        "messages": {
            "info": "fixture-info",
            "warning": "fixture-warning",
            "error": "fixture-error",
            "debug": "fixture-debug",
        },
        "name": "CLASSIC",
    },
    "extended": {
        "operation": "extended",
        "trace": "fixture-trace",
        "dynamic": "fixture-dynamic",
        "message": "fixture-message",
        "title": "fixture-title",
        "details": "fixture-details",
        "invalid": "invalid",
    },
    "startup": {
        "operation": "startup",
        "trace": "fixture-trace",
        "contract": "fixture",
        "checked": 2,
        "correlation": "case",
        "missing": "fixture-binding",
        "failureType": "fixture",
        "hint": "retry",
        "error": "fixture-error",
        "active": 1,
        "total": 2,
        "acceleration": "fixture",
    },
    "format": {
        "operation": "format",
        "component": "conformance",
        "event": "fixture.event",
        "severity": "warning",
        "outcome": "ok",
        "context": {"count": "2", "label": "two words"},
    },
}
_SPECS = {
    "basic": {
        "symbols": ["Logger", "init", "info", "warning", "error", "debug"],
        "ops": [
            None,
            "__init__",
            "createLogger",
            "initLogging",
            "init_logging",
            "info",
            "warning",
            "error",
            "debug",
            "log_info",
            "log_warning",
            "log_error",
            "log_debug",
        ],
    },
    "extended": {
        "symbols": ["Logger"],
        "ops": [
            "trace",
            "log",
            "log_message",
            "name",
            "is_enabled_for",
            "is_info_enabled",
            "is_debug_enabled",
            "is_trace_enabled",
        ],
    },
    "startup": {
        "symbols": [
            "trace",
            "log_startup_binding_contract_validated",
            "log_startup_binding_contract_failed",
            "log_startup_acceleration_status",
        ],
        "ops": [
            "log_trace",
            "log_startup_binding_contract_validated",
            "log_startup_binding_contract_failed",
            "log_startup_acceleration_status",
        ],
    },
    "format": {"symbols": ["format_contract_event"], "ops": ["format_contract_event"]},
}


def _matches(operation, observation):
    """Compare complete log streams and typed results, excluding only environmental log prefixes."""
    return json.dumps(observation, sort_keys=True) == json.dumps(
        _EXPECTED[operation], sort_keys=True
    )


MESSAGE_LOGGING_COVERAGE_POLICY = FamilyCoveragePolicy(
    "message-logging",
    tuple(
        CoveragePredicate(
            id=f"message-logging.{operation}",
            capability_id=f"message-logging.{operation}",
            action=f"message-logging.{operation}",
            observation_family="log-records",
            rust_symbols=tuple(spec["symbols"]),
            runtime_operations=tuple(spec["ops"]),
            matches=partial(_matches, operation),
        )
        for operation, spec in _SPECS.items()
    ),
)


def validate_message_logging_pack(document, root):
    """Reject fixture oracles and require the bounded reviewed logger operations."""
    paths = []
    fixture_root = (root / document["fixtureRoot"]).resolve()
    for scenario in document["scenarios"]:
        reference = scenario["input"].get("fixtureRef")
        operation = scenario["action"].removeprefix("message-logging.")
        if (
            operation not in _INPUTS
            or scenario["input"] != {"fixtureRef": reference}
            or scenario["fixtureRefs"] != [reference]
        ):
            raise ValueError("invalid logging scenario input")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("logging fixture escapes root")
        if json.loads(path.read_text(encoding="utf-8")) != _INPUTS[
            operation
        ] or not _matches(operation, scenario["expected"]):
            raise ValueError("invalid logging fixture or expected contract")
        paths.append(path)
    return tuple(paths)
