"""Regenerate golden files from Rust orchestrator output.

After implementing new sorting behavior (severity-based for suspects,
plugin-ID-based for mods), this script regenerates golden files from
the Rust orchestrator to establish the new baseline.

Usage:
    uv run python tests/golden/regenerate_rust_golden.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ClassicLib.integration.rust.orchestrator_api import ClassicOrchestrator
from tests.fixtures.golden_fixtures import (
    GOLDEN_DIR,
    mask_dynamic_data,
    normalize_paths,
)

# Source directories
CRASH_LOGS_DIR = project_root / "Crash Logs"
MANIFEST_PATH = GOLDEN_DIR / "report_manifest.json"


def regenerate_golden_file(
    log_path: Path,
    golden_name: str,
    orchestrator: ClassicOrchestrator,
) -> Path:
    """Regenerate a single golden file from Rust output.

    Args:
        log_path: Path to crash log file.
        golden_name: Base name for golden file.
        orchestrator: ClassicOrchestrator instance.

    Returns:
        Path to saved golden file.
    """
    # Process with Rust orchestrator
    result = orchestrator.process_crash_log(log_path)

    # Join lines (they already contain newlines)
    content = "".join(result.report_lines)

    # Apply normalization per CONTEXT.md
    normalized = mask_dynamic_data(content)
    normalized = normalize_paths(normalized)

    # Save as golden file
    golden_path = GOLDEN_DIR / f"{golden_name}_report.golden.md"
    golden_path.write_text(normalized, encoding="utf-8")
    return golden_path


def main() -> int:
    """Regenerate all golden files from Rust output.

    Returns:
        0 on success, 1 on failure.
    """
    print("Regenerating golden files from Rust orchestrator")
    print(f"  Source: {CRASH_LOGS_DIR}")
    print(f"  Destination: {GOLDEN_DIR}")
    print()

    # Load manifest
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found: {MANIFEST_PATH}")
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(f"Found {len(manifest)} entries in manifest")
    print()

    # Initialize orchestrator
    orchestrator = ClassicOrchestrator()

    regenerated = 0
    errors: list[tuple[str, str]] = []

    for golden_name, entry in manifest.items():
        log_name = entry["source_log"]
        log_path = CRASH_LOGS_DIR / log_name

        if not log_path.exists():
            print(f"  SKIP: {log_name} (not found)")
            continue

        try:
            golden_path = regenerate_golden_file(log_path, golden_name, orchestrator)
            print(f"  OK: {log_name} -> {golden_path.name}")
            regenerated += 1
        except Exception as e:
            print(f"  ERROR: {log_name} - {e}")
            errors.append((log_name, str(e)))

    print()
    print(f"Regenerated: {regenerated}/{len(manifest)} golden files")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for log_name, error in errors:
            print(f"  - {log_name}: {error}")

    return 0 if regenerated > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
