#!/usr/bin/env python3
"""Check whether classic-node index.d.ts is fresh."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and return the completed process."""
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    return completed


def run_build(package_dir: Path) -> None:
    """Regenerate Node binding outputs via debug build."""
    print("Running `bun run build:debug` to refresh generated bindings...")
    result = run_command(["bun", "run", "build:debug"], cwd=package_dir)
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="")
        raise RuntimeError(
            "Failed to run `bun run build:debug` for d.ts freshness check."
        )


def collect_git_diff(package_dir: Path) -> str:
    """Collect git diff output for index.d.ts relative to the package directory."""
    result = run_command(["git", "diff", "--", "index.d.ts"], cwd=package_dir)
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="")
        raise RuntimeError("Failed to collect `git diff` for index.d.ts.")
    return result.stdout


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON output with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Check freshness of classic-node index.d.ts."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--package-dir",
        default="node-bindings/classic-node",
        help="Path to classic-node package directory, relative to repo root.",
    )
    parser.add_argument(
        "--output-dir",
        default="node-bindings/classic-node/parity-artifacts",
        help="Directory for freshness artifacts, relative to repo root.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Skip build step and only verify whether index.d.ts has pending changes.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    package_dir = repo_root / args.package_dir
    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.check_only:
        run_build(package_dir)

    diff_output = collect_git_diff(package_dir)
    diff_path = output_dir / "index_dts.diff"
    summary_path = output_dir / "dts_freshness_report.json"

    is_fresh = not diff_output.strip()
    diff_path.write_text(diff_output, encoding="utf-8")
    write_json(
        summary_path,
        {
            "check_only": args.check_only,
            "fresh": is_fresh,
            "package_dir": str(package_dir),
            "diff_artifact": str(diff_path),
        },
    )

    print(f"- {summary_path}")
    print(f"- {diff_path}")

    if not is_fresh:
        print(
            "index.d.ts is stale. Regenerate bindings and commit updated declarations."
        )
        return 1

    print("index.d.ts freshness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
