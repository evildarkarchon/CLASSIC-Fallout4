"""Runtime context resolution for command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandContext:
    """Resolved command configuration shared by all handlers."""

    repo_root: Path
    fixture_root: Path
    output_path: Path | None
    json_output: bool
    no_color: bool
    verbose: bool
    tracebacks: bool


def find_repo_root(start: Path | None = None) -> Path:
    """Find the repository root by walking upward from the supplied path."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "Cargo.toml").exists() and (candidate / "python-bindings").exists():
            return candidate
    return current


def fallback_context(args: object) -> CommandContext:
    """Build a minimal context from global flags when path resolution fails."""

    return CommandContext(
        repo_root=Path.cwd(),
        fixture_root=Path.cwd(),
        output_path=None,
        json_output=bool(getattr(args, "json", False)),
        no_color=bool(getattr(args, "no_color", False)),
        verbose=bool(getattr(args, "verbose", False)),
        tracebacks=bool(getattr(args, "tracebacks", False)),
    )


def resolve_context(args: object) -> CommandContext:
    """Resolve paths and global flags from parsed argparse options."""

    repo_root_arg = getattr(args, "repo_root", None)
    repo_root = Path(repo_root_arg).resolve() if repo_root_arg else find_repo_root()
    fixture_root_arg = getattr(args, "fixture_root", None)
    fixture_root = Path(fixture_root_arg).resolve() if fixture_root_arg else repo_root / "sample_logs" / "FO4"
    output_path_arg = getattr(args, "output", None)
    return CommandContext(
        repo_root=repo_root,
        fixture_root=fixture_root,
        output_path=Path(output_path_arg).resolve() if output_path_arg else None,
        json_output=bool(getattr(args, "json", False)),
        no_color=bool(getattr(args, "no_color", False)),
        verbose=bool(getattr(args, "verbose", False)),
        tracebacks=bool(getattr(args, "tracebacks", False)),
    )
