"""Application boundary for the CLASSIC Python binding CLI."""

from __future__ import annotations

import sys
import traceback

from .context import fallback_context, resolve_context
from .exit_codes import ExitCode
from .output import failure, render_result
from .parser import build_parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, normalize boundary errors, and return a stable exit code."""

    parser = build_parser()
    args = parser.parse_args(_normalize_global_options(list(argv) if argv is not None else sys.argv[1:]))
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
