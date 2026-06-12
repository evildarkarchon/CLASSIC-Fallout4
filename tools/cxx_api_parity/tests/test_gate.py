"""Integration tests for the CXX parity gate.

These tests exercise the full CLI surface via subprocess (matching how CI runs
the gate) and the drift-detection path by mutating fixture files in tmp_path
synthetic bridge trees.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_SCRIPT = REPO_ROOT / "tools" / "cxx_api_parity" / "check_parity_gate.py"
BOOTSTRAP_SCRIPT = REPO_ROOT / "tools" / "cxx_api_parity" / "generate_baseline.py"
BASELINE_DIR = REPO_ROOT / "docs" / "implementation" / "cxx_api_parity" / "baseline"
BRIDGE_BUILD_RS = REPO_ROOT / "cpp-bindings" / "classic-cpp-bridge" / "build.rs"

# Make the parser importable so we can derive the expected module set from build.rs
# at test time instead of hardcoding it (D-07: build.rs is the single source of truth).
sys.path.insert(0, str(REPO_ROOT / "tools" / "cxx_api_parity"))
from generate_baseline import parse_build_rs_file_list  # noqa: E402


def _expected_modules_from_build_rs() -> set[str]:
    """Derive the expected bridge-module set from build.rs.

    The baseline must enumerate exactly the modules listed in
    `cxx_build::bridges([...])`. Phase 2 added several new modules; rather than
    bump a hardcoded count each time, derive it from the same source the
    parser uses.
    """
    files = parse_build_rs_file_list(BRIDGE_BUILD_RS.read_text(encoding="utf-8"))
    # Files look like "src/scanner.rs"; strip the "src/" prefix and ".rs" suffix.
    return {Path(f).stem for f in files}


# ----- Committed-baseline assertions (CXXG-02) -----


class TestBaselineExists:
    def test_baseline_file_exists(self):
        """CXXG-02: committed baseline exists at the D-05 path."""
        assert (BASELINE_DIR / "parity_contract.json").exists()

    def test_baseline_covers_all_build_rs_modules(self):
        """CXXG-02: committed baseline enumerates exactly the modules build.rs declares.

        Phase 1 hardcoded a 14-module set; Phase 2 added new bridge modules
        (constants, path, version_registry, web, xse) per CXXS-01..09. Rather
        than bumping a constant each time, derive the expected module set from
        build.rs (the same source the parser uses — D-07).
        """
        data = json.loads(
            (BASELINE_DIR / "parity_contract.json").read_text(encoding="utf-8")
        )
        modules = {entry["bridgeModule"] for entry in data["entries"]}
        expected = _expected_modules_from_build_rs()
        assert modules == expected, (
            f"baseline modules drift from build.rs:\n"
            f"  in baseline only: {sorted(modules - expected)}\n"
            f"  in build.rs only: {sorted(expected - modules)}"
        )

    def test_baseline_schema_shape(self):
        """D-03/D-04: contract uses flat `entries` list, NO tier1Mappings, NO tier2*."""
        data = json.loads(
            (BASELINE_DIR / "parity_contract.json").read_text(encoding="utf-8")
        )
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert "tier1Mappings" not in data
        assert not any(k.startswith("tier2") for k in data)

    def test_baseline_entries_are_sorted(self):
        """Determinism: baseline entries sorted by (bridgeModule, kind, rustSymbol)."""
        data = json.loads(
            (BASELINE_DIR / "parity_contract.json").read_text(encoding="utf-8")
        )
        keys = [
            (e["bridgeModule"], e["kind"], e["rustSymbol"]) for e in data["entries"]
        ]
        assert keys == sorted(keys)


# ----- Gate smoke (CXXG-03) -----


class TestGateSmoke:
    def test_gate_passes_on_unchanged_source(self):
        """CXXG-03: gate exits 0 against the committed born-green baseline."""
        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--repo-root", str(REPO_ROOT)],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0, (
            f"gate should pass against committed baseline. "
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "CXX parity gate passed" in result.stdout


# ----- Drift detection (CXXG-03) -----


def _bootstrap_synthetic_gate(tmp_path: Path, fixture_files: dict[str, str]) -> Path:
    """Build a synthetic bridge crate tree + baseline under tmp_path.

    Returns the synthetic repo root. The caller can then mutate files and
    re-run the gate to exercise drift cases.
    """
    synth_repo = tmp_path / "repo"
    bridge = synth_repo / "cpp-bindings" / "classic-cpp-bridge"
    (bridge / "src").mkdir(parents=True)

    # Write build.rs
    bridges_list = ", ".join(f'"src/{name}"' for name in fixture_files)
    (bridge / "build.rs").write_text(
        "#[cfg(windows)]\nfn main() {\n"
        f"    cxx_build::bridges([{bridges_list}])\n"
        '        .compile("x");\n}\n',
        encoding="utf-8",
    )
    for name, content in fixture_files.items():
        (bridge / "src" / name).write_text(content, encoding="utf-8")

    # Bootstrap the baseline for this synthetic tree
    result = subprocess.run(
        [
            sys.executable,
            str(BOOTSTRAP_SCRIPT),
            "--repo-root",
            str(synth_repo),
            "--write-baseline",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, (
        f"bootstrap failed. stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    # Initial gate should pass -- run with --update-baseline once to reconcile
    # the gate_report placeholder vs the real gate output.
    result = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--repo-root",
            str(synth_repo),
            "--update-baseline",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, (
        f"initial --update-baseline gate run failed. "
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    # Final clean gate run
    result = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--repo-root", str(synth_repo)],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, (
        f"post-bootstrap gate run failed. "
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return synth_repo


def _run_gate(synth_repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--repo-root", str(synth_repo)],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )


_SIMPLE_BRIDGE = (
    '#[cxx::bridge(namespace = "classic::synth")]\n'
    "mod ffi {\n"
    "    struct SynthStruct {\n"
    "        name: String,\n"
    "        count: u32,\n"
    "    }\n"
    '    extern "Rust" {\n'
    "        fn synth_hello(name: &str) -> String;\n"
    "        fn synth_count(items: u32) -> u32;\n"
    "    }\n"
    "}\n"
)


class TestDriftDetection:
    def test_gate_fails_on_added_function(self, tmp_path: Path):
        """CXXG-03: adding a fn to a bridge file -> gate exits 1."""
        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        synth_file = synth_repo / "cpp-bindings/classic-cpp-bridge/src/synth.rs"
        mutated = _SIMPLE_BRIDGE.replace(
            "fn synth_count(items: u32) -> u32;",
            "fn synth_count(items: u32) -> u32;\n        fn synth_new_fn() -> bool;",
        )
        synth_file.write_text(mutated, encoding="utf-8")

        result = _run_gate(synth_repo)
        assert result.returncode == 1, (
            f"gate should fail on added fn. stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert (
            "drift" in result.stderr.lower() or "missing_from_contract" in result.stderr
        )

    def test_gate_fails_on_removed_function(self, tmp_path: Path):
        """CXXG-03: removing a fn -> gate exits 1 with missing_from_current drift."""
        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        synth_file = synth_repo / "cpp-bindings/classic-cpp-bridge/src/synth.rs"
        mutated = _SIMPLE_BRIDGE.replace(
            "        fn synth_count(items: u32) -> u32;\n", ""
        )
        synth_file.write_text(mutated, encoding="utf-8")

        result = _run_gate(synth_repo)
        assert result.returncode == 1
        assert "missing_from_current" in result.stderr

    def test_gate_fails_on_struct_field_rename(self, tmp_path: Path):
        """CXXG-03: renaming a struct field -> gate exits 1 with signature_mismatch."""
        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        synth_file = synth_repo / "cpp-bindings/classic-cpp-bridge/src/synth.rs"
        mutated = _SIMPLE_BRIDGE.replace("name: String,", "renamed_name: String,")
        synth_file.write_text(mutated, encoding="utf-8")

        result = _run_gate(synth_repo)
        assert result.returncode == 1
        assert "signature_mismatch" in result.stderr

    def test_gate_fails_on_function_signature_change(self, tmp_path: Path):
        """CXXG-03: changing a fn return type -> gate exits 1 with signature_mismatch."""
        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        synth_file = synth_repo / "cpp-bindings/classic-cpp-bridge/src/synth.rs"
        mutated = _SIMPLE_BRIDGE.replace(
            "fn synth_count(items: u32) -> u32;",
            "fn synth_count(items: u32) -> u64;",
        )
        synth_file.write_text(mutated, encoding="utf-8")

        result = _run_gate(synth_repo)
        assert result.returncode == 1
        assert "signature_mismatch" in result.stderr


def test_cxx_gate_defaults_use_repo_root_paths() -> None:
    gate_source = (
        REPO_ROOT / "tools" / "cxx_api_parity" / "check_parity_gate.py"
    ).read_text(encoding="utf-8")
    generator_source = (
        REPO_ROOT / "tools" / "cxx_api_parity" / "generate_baseline.py"
    ).read_text(encoding="utf-8")
    assert 'default="cpp-bindings/classic-cpp-bridge/parity-artifacts"' in gate_source
    assert (
        'bridge_crate_rel: str = "cpp-bindings/classic-cpp-bridge"' in generator_source
    )
    assert "ClassicLib-rs/cpp-bindings/classic-cpp-bridge" not in gate_source
    assert "ClassicLib-rs/cpp-bindings/classic-cpp-bridge" not in generator_source


# ----- Stale-artifact detection (CXXG-03 freshness, D-14) -----


class TestStaleArtifact:
    def test_gate_fails_on_stale_artifact(self, tmp_path: Path):
        """D-14: manually corrupting a committed baseline artifact -> gate exits 1."""
        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        stale_md = (
            synth_repo
            / "docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md"
        )
        stale_md.write_text(
            "# CXX Parity Diff Report\n\nSTALE PLACEHOLDER\n", encoding="utf-8"
        )

        result = _run_gate(synth_repo)
        assert result.returncode == 1, (
            f"gate should fail on stale md. stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "stale" in result.stderr.lower()

    def test_update_baseline_clears_stale(self, tmp_path: Path):
        """D-08/D-14: --update-baseline refreshes committed artifacts; next run is clean."""
        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        stale_md = (
            synth_repo
            / "docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md"
        )
        stale_md.write_text("STALE\n", encoding="utf-8")

        # Pre-refresh: gate fails
        pre = _run_gate(synth_repo)
        assert pre.returncode == 1

        # Refresh
        refresh = subprocess.run(
            [
                sys.executable,
                str(GATE_SCRIPT),
                "--repo-root",
                str(synth_repo),
                "--update-baseline",
            ],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        assert refresh.returncode == 0, (
            f"--update-baseline should succeed. stderr:\n{refresh.stderr}"
        )

        # Post-refresh: gate passes
        post = _run_gate(synth_repo)
        assert post.returncode == 0, (
            f"post-refresh gate should pass. stdout:\n{post.stdout}\nstderr:\n{post.stderr}"
        )


# ----- CLI surface (CXXG-04 / D-12) -----


class TestNoDeferredRegistry:
    def test_no_deferred_registry_arg(self):
        """CXXG-04 / D-12: --deferred-registry is NOT a registered argument."""
        result = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "--deferred-registry" not in result.stdout
        assert "--runtime-registry" not in result.stdout
        # Positive: the arguments that DO exist
        assert "--repo-root" in result.stdout
        assert "--contract" in result.stdout
        assert "--update-baseline" in result.stdout

    def test_unknown_deferred_registry_arg_rejected(self):
        """CXXG-04: passing --deferred-registry produces an argparse error (exit 2)."""
        result = subprocess.run(
            [
                sys.executable,
                str(GATE_SCRIPT),
                "--deferred-registry",
                "whatever.json",
            ],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        # argparse unrecognized-argument error code is 2
        assert result.returncode == 2
        assert (
            "unrecognized arguments" in result.stderr.lower()
            or "error" in result.stderr.lower()
        )
