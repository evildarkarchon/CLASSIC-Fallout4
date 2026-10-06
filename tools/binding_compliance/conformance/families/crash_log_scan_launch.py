"""Crash Log Scan Launch: the read-only projection of User Settings into a scan request."""

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_ACTION = "crash-log-scan-launch.prepare"

#: Every field a launched request observation carries, whatever the intent.
_REQUEST_FIELDS = frozenset(
    {
        "intent",
        "game",
        "gameVersion",
        "showFormidValues",
        "simplifyLogs",
        "formidDatabasePaths",
        "unsolvedLogsDestination",
        "maxConcurrent",
        "baseDirectory",
        "customScanDirectory",
        "configuredDocumentsRoot",
        "unsolvedLogs",
        "targetedInputs",
        "fcxEnabled",
        "setupContext",
    }
)
_OBSERVATION_FIELDS = frozenset(
    {"outcome", "errorKind", "request", "diagnostics", "settingsUnchanged"}
)
#: The four FCX setup facts a Crash Log Scan Setup Context carries (#286).
_SETUP_CONTEXT_FIELDS = frozenset({"gameRoot", "docsRoot", "gameExePath", "xseLogPath"})
#: Frozen launch error tokens: invalid caller input, and the operational XSE log failure.
_ERROR_KINDS = frozenset({"targeted_without_inputs", "xse_log_inspect"})


def _diagnostics_are_typed(observation):
    """Require each diagnostic to carry a frozen kind token and a stable code."""
    diagnostics = observation["diagnostics"]
    return isinstance(diagnostics, list) and all(
        isinstance(item, dict)
        and set(item) == {"kind", "code"}
        and item["kind"] == "user_settings"
        and isinstance(item["code"], str)
        and bool(item["code"])
        for item in diagnostics
    )


def _setup_context_is_consistent(request):
    """FCX on carries exactly the four setup facts; FCX off carries no setup context."""
    context = request["setupContext"]
    if request["fcxEnabled"] is not True:
        return context is None
    return (
        isinstance(context, dict)
        and set(context) == _SETUP_CONTEXT_FIELDS
        and all(value is None or isinstance(value, str) for value in context.values())
    )


def _launched(observation):
    """A launch that produced a request, never wrote User Settings, and typed its diagnostics."""
    return (
        set(observation) == _OBSERVATION_FIELDS
        and observation["outcome"] == "launched"
        and observation["errorKind"] is None
        and isinstance(observation["request"], dict)
        and set(observation["request"]) == _REQUEST_FIELDS
        and _setup_context_is_consistent(observation["request"])
        and observation["settingsUnchanged"] is True
        and _diagnostics_are_typed(observation)
    )


def _typed_error(observation):
    """A launch refused with a typed error, without a request and without writing settings."""
    return (
        set(observation) == _OBSERVATION_FIELDS
        and observation["outcome"] == "error"
        and observation["errorKind"] in _ERROR_KINDS
        and observation["request"] is None
        and observation["diagnostics"] == []
        and observation["settingsUnchanged"] is True
    )


#: The launch operation, its intent and overrides, and the request it returns are credited
#: by any launched scenario; the typed error and its kind only by a refused one.
_SHARED_SYMBOLS = ("prepare_launch", "CrashLogScanIntent", "CrashLogScanLaunchOverrides")

CRASH_LOG_SCAN_LAUNCH_COVERAGE_POLICY = FamilyCoveragePolicy(
    "crash-log-scan-launch",
    (
        CoveragePredicate(
            id="crash-log-scan-launch.launched",
            capability_id=_ACTION,
            action=_ACTION,
            observation_family="launch-request",
            rust_symbols=_SHARED_SYMBOLS
            + (
                "CrashLogScanLaunchRequest",
                "CrashLogScanLaunchDiagnostic",
                "CrashLogScanLaunchDiagnosticKind",
            ),
            matches=_launched,
        ),
        CoveragePredicate(
            id="crash-log-scan-launch.typed-error",
            capability_id=_ACTION,
            action=_ACTION,
            observation_family="launch-request",
            rust_symbols=_SHARED_SYMBOLS
            + ("CrashLogScanLaunchError", "CrashLogScanLaunchErrorKind"),
            matches=_typed_error,
        ),
    ),
)
