"""Cross-language logging contract helpers for startup diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

EVENT_STARTUP_BINDING_CONTRACT_VALIDATED = "classic.startup.binding_contract.validated"
EVENT_STARTUP_BINDING_CONTRACT_FAILED = "classic.startup.binding_contract.failed"
EVENT_STARTUP_ACCELERATION_STATUS = "classic.startup.acceleration.status"

_SECRET_KEY_TOKENS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "session",
    "credential",
    "private_key",
)

_PATH_KEY_TOKENS: tuple[str, ...] = (
    "path",
    "file",
    "filename",
    "filepath",
    "directory",
    "dir",
    "location",
)

_SECRET_VALUE_MARKERS: tuple[str, ...] = (
    "token=",
    "password=",
    "secret=",
    "api_key=",
    "apikey=",
)


def _contains_token(value: str, tokens: tuple[str, ...]) -> bool:
    value_lower = value.lower()
    return any(token in value_lower for token in tokens)


def _redact_field(key: str, value: str) -> str:
    if _contains_token(key, _SECRET_KEY_TOKENS):
        return "[REDACTED]"
    if _contains_token(key, _PATH_KEY_TOKENS):
        return "<path-redacted>"
    if _contains_token(value, _SECRET_VALUE_MARKERS):
        return "[REDACTED]"
    return value


def _fallback_format_contract_event(
    component: str,
    event: str,
    severity: str,
    outcome: str,
    context: Mapping[str, str],
) -> str:
    segments = [
        f"event={event}",
        f"severity={severity}",
        f"component={component}",
        f"outcome={outcome}",
    ]
    for key in sorted(context):
        value = _redact_field(key, context[key])
        segments.append(f"{key}={value}")
    return " ".join(segments)


def format_contract_event(
    *,
    component: str,
    event: str,
    severity: str,
    outcome: str,
    context: Mapping[str, object] | None = None,
) -> str:
    """Format a contract event, preferring Rust formatter when available."""
    normalized_context: dict[str, str] = {}
    if context:
        normalized_context = {key: str(value) for key, value in context.items() if value is not None}

    try:
        import classic_message
    except ImportError:
        return _fallback_format_contract_event(component, event, severity, outcome, normalized_context)

    return classic_message.format_contract_event(component, event, severity, outcome, normalized_context)
