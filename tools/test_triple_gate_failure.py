#!/usr/bin/env python3
"""Triple-gate canary injection assertion script (CI-05).

Proves the triple-gate invariant: adding undeclared Rust API surface causes
ALL THREE parity gates (CXX, Python, Node) to detect the drift and fail.

The canary is injected into TWO files because each gate family parses
different source files:
  - CXX gate: parses #[cxx::bridge] blocks in bridge module files
  - Python/Node gates: parse pub items in business-logic -core crate lib.rs files

Injection targets:
  - classic-scanlog-core/src/lib.rs (pub fn, detected by Python and Node gates)
  - classic-cpp-bridge/src/scanner.rs (extern "Rust" fn, detected by CXX gate)

Usage:
    python tools/test_triple_gate_failure.py --repo-root .
    python tools/test_triple_gate_failure.py --repo-root . --verbose

This script is local-only -- not run in CI. The three individual gate jobs
already enforce the invariant on every PR; this script just proves they work
together. Run once during Phase 5 verification and on-demand by maintainers.

Exit codes:
    0 - All three gates detected the canary (PASS)
    1 - At least one gate did NOT detect the canary (invariant broken)
    2 - Collision guard: _ci05_canary already exists in a target file
    3 - Preflight failure: one or more gates failed before canary injection
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


# Gate scripts invoked by this test.
# NOTE: The Node gate requires
# docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json
# to exist. Phase 6 (Documentation Reset) will make the --deferred-registry
# argument optional before deleting governance files. If this script fails on
# the Node gate after Phase 6, verify DOC-01 was applied.
GATE_SCRIPTS: list[tuple[str, str]] = [
    ("CXX", "tools/cxx_api_parity/check_parity_gate.py"),
    ("Python", "tools/python_api_parity/check_parity_gate.py"),
    ("Node", "tools/node_api_parity/check_parity_gate.py"),
]

CANARY_MARKER = "_ci05_canary"

# Canary for Python/Node gates: appended to a -core crate lib.rs
CORE_CANARY = "\npub fn _ci05_canary() {}\n"

# Canary for CXX gate: injected into an extern "Rust" block in a bridge file
CXX_CANARY_LINE = "        fn _ci05_canary() -> bool;\n"

# Relative paths from repo root
CORE_TARGET_REL = (
    "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs"
)
BRIDGE_TARGET_REL = (
    "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs"
)


def run_gate(
    name: str,
    script_path: Path,
    repo_root: Path,
    verbose: bool,
) -> tuple[int, str, str]:
    """Run a single parity gate script and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(script_path), "--repo-root", str(repo_root)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if verbose:
        print(f"\n--- {name} gate stdout ---")
        print(result.stdout)
        if result.stderr:
            print(f"--- {name} gate stderr ---")
            print(result.stderr)
    return result.returncode, result.stdout, result.stderr


def run_preflight(
    repo_root: Path,
    verbose: bool,
) -> bool:
    """Run all three gates and assert they all return 0 (clean baseline).

    Returns True if all gates pass, False otherwise.
    """
    print("Preflight (clean baseline):")
    all_clean = True
    for name, script_rel in GATE_SCRIPTS:
        script_path = repo_root / script_rel
        rc, _stdout, _stderr = run_gate(name, script_path, repo_root, verbose)
        status = "PASS (clean)" if rc == 0 else f"FAIL (rc={rc})"
        print(f"  {name:8s} rc={rc} -> {status}")
        if rc != 0:
            print(
                f"PREFLIGHT FAIL: {name} gate returned rc={rc} "
                f"-- fix before running canary test",
                file=sys.stderr,
            )
            all_clean = False
    return all_clean


def inject_canaries(
    core_file: Path,
    bridge_file: Path,
    core_original: str,
    bridge_original: str,
) -> None:
    """Inject canary markers into both target files."""
    # Core crate: append pub fn at end of file
    core_file.write_text(
        core_original + CORE_CANARY, encoding="utf-8",
    )

    # Bridge crate: inject fn declaration into first extern "Rust" block
    target = 'extern "Rust" {'
    idx = bridge_original.find(target)
    if idx < 0:
        raise RuntimeError(
            f"Cannot find 'extern \"Rust\" {{' in {bridge_file}"
        )
    insert_point = bridge_original.find("\n", idx) + 1
    injected = (
        bridge_original[:insert_point]
        + CXX_CANARY_LINE
        + bridge_original[insert_point:]
    )
    bridge_file.write_text(injected, encoding="utf-8")


def restore_files(
    core_file: Path,
    bridge_file: Path,
    core_original: str,
    bridge_original: str,
) -> None:
    """Restore both files to their original content."""
    core_file.write_text(core_original, encoding="utf-8")
    bridge_file.write_text(bridge_original, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Triple-gate canary injection assertion (CI-05).",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root path (default: current directory).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print stdout/stderr from each gate invocation.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    verbose: bool = args.verbose

    core_file = repo_root / CORE_TARGET_REL
    bridge_file = repo_root / BRIDGE_TARGET_REL

    for target_file in (core_file, bridge_file):
        if not target_file.exists():
            print(
                f"ERROR: target file not found at {target_file}",
                file=sys.stderr,
            )
            return 1

    core_original = core_file.read_text(encoding="utf-8")
    bridge_original = bridge_file.read_text(encoding="utf-8")

    # --- Collision guard ---
    for label, content in [
        (CORE_TARGET_REL, core_original),
        (BRIDGE_TARGET_REL, bridge_original),
    ]:
        if CANARY_MARKER in content:
            print(
                f"ERROR: {CANARY_MARKER} already exists in {label} "
                f"-- aborting to avoid corruption",
                file=sys.stderr,
            )
            return 2

    # --- Preflight baseline ---
    print("=" * 55)
    print("=== Triple-Gate Canary Test (CI-05) ===")
    print("=" * 55)
    print()

    if not run_preflight(repo_root, verbose):
        print(
            "\nPreflight failed. All three gates must pass on a "
            "clean baseline before canary injection.",
            file=sys.stderr,
        )
        return 3

    print()

    # --- Canary injection and gate runs ---
    gate_results: dict[str, int] = {}

    try:
        inject_canaries(
            core_file, bridge_file,
            core_original, bridge_original,
        )
        print(f"Canary injected into:")
        print(f"  {CORE_TARGET_REL} (pub fn {CANARY_MARKER})")
        print(f"  {BRIDGE_TARGET_REL} (extern Rust fn {CANARY_MARKER})")
        print()

        print("After canary injection:")
        for name, script_rel in GATE_SCRIPTS:
            script_path = repo_root / script_rel
            rc, _stdout, _stderr = run_gate(
                name, script_path, repo_root, verbose,
            )
            gate_results[name] = rc
            status = "FAIL (expected)" if rc != 0 else "PASS (unexpected!)"
            print(f"  {name:8s} rc={rc} -> {status}")

    finally:
        # Always restore original content
        restore_files(
            core_file, bridge_file,
            core_original, bridge_original,
        )
        print()
        print("Canary reverted: both files restored to original content.")

    # --- Summary ---
    print()
    all_detected = all(rc != 0 for rc in gate_results.values())

    if all_detected:
        print(
            "TRIPLE-GATE TEST: PASS -- all three gates detected the canary"
        )
        return 0
    else:
        passed_gates = [
            name for name, rc in gate_results.items() if rc == 0
        ]
        print(
            f"TRIPLE-GATE TEST: FAIL -- these gates did NOT detect the "
            f"canary: {', '.join(passed_gates)}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
