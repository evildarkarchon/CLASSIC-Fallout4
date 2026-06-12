"""Output envelopes, text rendering, and diagnostics for the CLI."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

from .context import CommandContext
from .exit_codes import ExitCode


SCHEMA_VERSION = "1.0"


@dataclass
class CommandResult:
    """A handler result that can render to text or a JSON envelope."""

    command: str
    success: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    exit_code: int = int(ExitCode.SUCCESS)
    error: dict[str, Any] | None = None
    text_lines: list[str] = field(default_factory=list)


def success(command: str, summary: str, data: dict[str, Any] | None = None, *, artifacts: list[str] | None = None, text_lines: list[str] | None = None) -> CommandResult:
    """Create a successful command result envelope."""

    return CommandResult(command=command, success=True, summary=summary, data=data or {}, artifacts=artifacts or [], text_lines=text_lines or [])


def failure(command: str, summary: str, exit_code: int, *, error: dict[str, Any] | None = None, data: dict[str, Any] | None = None, artifacts: list[str] | None = None, text_lines: list[str] | None = None) -> CommandResult:
    """Create a failed command result envelope with a stable exit status."""

    return CommandResult(command=command, success=False, summary=summary, data=data or {}, artifacts=artifacts or [], exit_code=exit_code, error=error or {"message": summary}, text_lines=text_lines or [])


def binding_exception(command: str, module_name: str, exc: BaseException) -> CommandResult:
    """Convert an exception from a public binding call into structured output."""

    return failure(
        command,
        f"{module_name} raised {type(exc).__name__}: {exc}",
        int(ExitCode.PRODUCT_FAILURE),
        error={"classification": "binding-exception", "module": module_name, "type": type(exc).__name__, "message": str(exc)},
    )


def envelope(result: CommandResult) -> dict[str, Any]:
    """Return the machine-readable JSON envelope for a command result."""

    body: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "command": result.command,
        "success": result.success,
        "summary": result.summary,
        "data": result.data,
        "artifacts": result.artifacts,
        "exitCode": result.exit_code,
    }
    if result.error is not None:
        body["error"] = result.error
    return body


def render_result(result: CommandResult, context: CommandContext) -> int:
    """Render a command result to stdout while preserving JSON cleanliness."""

    if context.json_output:
        print(json.dumps(envelope(result), indent=2, sort_keys=True))
    else:
        for line in result.text_lines or [result.summary]:
            print(line)
        if result.artifacts:
            print("Artifacts:")
            for artifact in result.artifacts:
                print(f"  {artifact}")
    return result.exit_code


def diagnostic(message: str, context: CommandContext) -> None:
    """Write diagnostic information to stderr when verbosity requests it."""

    if context.verbose:
        print(message, file=sys.stderr)
