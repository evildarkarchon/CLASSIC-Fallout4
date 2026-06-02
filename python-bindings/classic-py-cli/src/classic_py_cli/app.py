"""Application boundary for the CLASSIC Python binding CLI."""

from __future__ import annotations

import io
import sys
import traceback
from contextlib import redirect_stderr
from pathlib import Path

from .context import CommandContext, fallback_context, resolve_context
from .exit_codes import ExitCode
from .output import failure, render_result
from .parser import build_parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, normalize boundary errors, and return a stable exit code."""

    parser = build_parser()
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    normalized_argv = _normalize_global_options(raw_argv)
    args = _parse_args(parser, normalized_argv)
    if isinstance(args, int):
        return args
    context = fallback_context(args)
    try:
        context = resolve_context(args)
        result = args.handler(args, context)
    except KeyboardInterrupt:
        result = failure("interrupted", "Command interrupted", int(ExitCode.INTERRUPTED))
    except Exception as exc:  # noqa: BLE001 - final CLI boundary normalization.
        if context.tracebacks:
            traceback.print_exc(file=sys.stderr)
        result = failure("startup", f"Unexpected CLI failure: {exc}", int(ExitCode.USAGE), error={"type": type(exc).__name__, "message": str(exc)})
    return render_result(result, context)


def _parse_args(parser: object, normalized_argv: list[str]) -> object | int:
    """Parse argv and normalize JSON-mode argparse failures through render_result."""

    json_mode = _json_mode_requested(normalized_argv)
    if not json_mode:
        return parser.parse_args(normalized_argv)  # type: ignore[union-attr]

    stderr_capture = io.StringIO()
    try:
        with redirect_stderr(stderr_capture):
            return parser.parse_args(normalized_argv)  # type: ignore[union-attr]
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else int(ExitCode.USAGE)
        if exit_code == 0:
            raise
        message = _parse_error_message(stderr_capture.getvalue())
        context = _fallback_context_from_argv(normalized_argv)
        result = failure(
            "usage",
            message,
            int(ExitCode.USAGE),
            error={"classification": "parse-error", "message": message},
        )
        return render_result(result, context)


def _json_mode_requested(argv: list[str]) -> bool:
    """Return whether the caller requested JSON output from raw argv tokens."""

    return "--json" in argv


def _fallback_context_from_argv(argv: list[str]) -> CommandContext:
    """Build a minimal context from global flags when argparse fails early."""

    return CommandContext(
        repo_root=Path.cwd(),
        fixture_root=Path.cwd(),
        output_path=None,
        json_output=_json_mode_requested(argv),
        no_color="--no-color" in argv,
        verbose="--verbose" in argv,
        tracebacks="--tracebacks" in argv,
    )


def _parse_error_message(captured: str) -> str:
    """Extract the actionable argparse message without the usage banner."""

    lines = [line.strip() for line in captured.splitlines() if line.strip()]
    if not lines:
        return "Invalid command arguments"
    for line in reversed(lines):
        marker = "error:"
        if marker in line:
            return line.split(marker, maxsplit=1)[1].strip()
    for line in lines:
        if not line.startswith("usage:"):
            return line
    return lines[-1]


def _normalize_global_options(argv: list[str]) -> list[str]:
    """Allow documented global options before or after subcommands."""

    flags = {"--json", "--no-color", "--verbose", "--tracebacks"}
    valued = {"--output", "--repo-root", "--fixture-root"}
    globals_out: list[str] = []
    rest: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in flags:
            globals_out.append(token)
            index += 1
        elif token in valued and index + 1 < len(argv):
            globals_out.extend([token, argv[index + 1]])
            index += 2
        elif any(token.startswith(f"{name}=") for name in valued):
            globals_out.append(token)
            index += 1
        else:
            rest.append(token)
            index += 1
    return [*globals_out, *rest]
