#!/usr/bin/env python3
"""Check whether classic-node index.d.ts is fresh."""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

INDEX_DTS_FILENAME = "index.d.ts"


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


def generate_temp_dts(package_dir: Path, temp_output_dir: Path) -> Path:
    """Generate ``index.d.ts`` into a temporary output directory."""
    print(
        "Running `bun x napi build` in a temporary output directory to verify "
        "generated bindings..."
    )
    result = run_command(
        [
            "bun",
            "x",
            "napi",
            "build",
            "--platform",
            "--manifest-path",
            "./Cargo.toml",
            "--output-dir",
            str(temp_output_dir),
            "--dts",
            INDEX_DTS_FILENAME,
            "--no-js",
        ],
        cwd=package_dir,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="")
        raise RuntimeError(
            "Failed to generate temp `index.d.ts` for d.ts freshness check."
        )
    generated_dts = temp_output_dir / INDEX_DTS_FILENAME
    if not generated_dts.is_file():
        raise RuntimeError(
            f"Expected generated d.ts at {generated_dts}, but it was not created."
        )
    return generated_dts


def normalize_text(text: str) -> str:
    """Normalize line endings for stable cross-platform comparisons."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def collect_content_diff(tracked_path: Path, generated_path: Path) -> str:
    """Collect a unified diff between tracked and freshly generated d.ts files."""
    tracked_text = normalize_text(tracked_path.read_text(encoding="utf-8"))
    generated_text = normalize_text(generated_path.read_text(encoding="utf-8"))
    return "".join(
        difflib.unified_diff(
            tracked_text.splitlines(keepends=True),
            generated_text.splitlines(keepends=True),
            fromfile=str(tracked_path),
            tofile=str(generated_path),
        )
    )


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
        help=(
            "Retained for compatibility. The freshness check is now always "
            "read-only and compares temp-generated output to the tracked file."
        ),
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    package_dir = repo_root / args.package_dir
    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tracked_dts = package_dir / INDEX_DTS_FILENAME

    with tempfile.TemporaryDirectory(prefix="classic-node-dts-") as temp_dir:
        generated_dts = generate_temp_dts(package_dir, Path(temp_dir))
        diff_output = collect_content_diff(tracked_dts, generated_dts)

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
            "tracked_dts": str(tracked_dts),
            "diff_artifact": str(diff_path),
            "comparison_mode": "temp-generated-content",
            "line_endings_normalized": True,
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
