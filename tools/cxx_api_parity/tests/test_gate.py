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

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_SCRIPT = REPO_ROOT / "tools" / "cxx_api_parity" / "check_parity_gate.py"
BOOTSTRAP_SCRIPT = REPO_ROOT / "tools" / "cxx_api_parity" / "generate_baseline.py"
BASELINE_DIR = REPO_ROOT / "docs" / "implementation" / "cxx_api_parity" / "baseline"
MAPPINGS_FILE = REPO_ROOT / "tools" / "cxx_api_parity" / "canonical_mappings.json"
BRIDGE_BUILD_RS = REPO_ROOT / "cpp-bindings" / "classic-cpp-bridge" / "build.rs"

# Make the parser importable so we can derive the expected module set from build.rs
# at test time instead of hardcoding it (D-07: build.rs is the single source of truth).
sys.path.insert(0, str(REPO_ROOT / "tools" / "cxx_api_parity"))
from generate_baseline import (  # noqa: E402
    parse_build_rs_file_list,
    parse_cxx_bridge_surface,
)


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
        assert data["schema_version"] == 2
        assert "tier1Mappings" not in data
        assert not any(k.startswith("tier2") for k in data)

    def test_baseline_rows_have_exact_canonical_or_binding_only_metadata(self):
        """Every generated row is traceable without relabeling CXX-only declarations."""

        data = json.loads(
            (BASELINE_DIR / "parity_contract.json").read_text(encoding="utf-8")
        )
        canonical = [row for row in data["entries"] if "ownerModule" in row]
        binding_only = [row for row in data["entries"] if "unmappedReason" in row]

        assert canonical
        assert binding_only
        assert len(canonical) + len(binding_only) == len(data["entries"])
        assert all(
            all(
                row.get(field)
                for field in ("ownerModule", "rustCrate", "coreRustSymbol")
            )
            and "unmappedReason" not in row
            for row in canonical
        )
        assert all(
            row["unmappedReason"]
            and not any(
                field in row for field in ("ownerModule", "rustCrate", "coreRustSymbol")
            )
            for row in binding_only
        )

    def test_reviewed_mapping_inventory_exactly_covers_baseline(self):
        """The independent sidecar neither omits nor outlives a generated row."""

        baseline = json.loads(
            (BASELINE_DIR / "parity_contract.json").read_text(encoding="utf-8")
        )
        mappings = json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))

        assert {row["id"] for row in mappings["entries"]} == {
            row["id"] for row in baseline["entries"]
        }

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


def _write_synthetic_canonical_inventory(synth_repo: Path) -> None:
    """Write exact fake core declarations and mappings for a synthetic bridge."""

    parsed = parse_cxx_bridge_surface(synth_repo)
    synth_lib = synth_repo / "business-logic" / "classic-synth-core" / "src" / "lib.rs"
    synth_lib.parent.mkdir(parents=True, exist_ok=True)
    declarations: list[str] = []
    for row in parsed["entries"]:
        symbol = row["rustSymbol"]
        if row["kind"] == "function":
            declarations.append(f"pub fn {symbol}() {{}}")
        elif row["kind"] == "enum":
            declarations.append(f"pub enum {symbol} {{ Placeholder }}")
        else:
            declarations.append(f"pub struct {symbol};")
    synth_lib.write_text("\n".join(declarations) + "\n", encoding="utf-8")

    mapping_path = synth_repo / "tools" / "cxx_api_parity" / "canonical_mappings.json"
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "rustCrates": [
                    {
                        "ownerModule": "synth",
                        "rustCrate": "classic-synth-core",
                        "libRs": "business-logic/classic-synth-core/src/lib.rs",
                    }
                ],
                "entries": [
                    {
                        "id": row["id"],
                        "rustSymbol": row["rustSymbol"],
                        "kind": row["kind"],
                        "bridgeModule": row["bridgeModule"],
                        "ownerModule": "synth",
                        "rustCrate": "classic-synth-core",
                        "coreRustSymbol": row["rustSymbol"],
                    }
                    for row in parsed["entries"]
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


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

    # Synthetic rows use a one-to-one fake core mapping. Production mappings are
    # reviewed individually; this fixture only needs an exact inventory so gate
    # mutation tests can distinguish bridge drift from mapping drift.
    _write_synthetic_canonical_inventory(synth_repo)

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
        """An added bridge function fails closed until its mapping is reviewed."""
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
        assert "missing canonical mappings" in result.stderr

    def test_update_baseline_accepts_an_intentional_bridge_change(self, tmp_path: Path):
        """The documented one-step refresh actually accepts an added, removed, or changed item.

        `--update-baseline` used to mirror the committed contract straight back, so the
        contract never moved and the very next run reported the same drift. The flag only
        refreshed the reports, while the contributor guide documented it as the way to accept
        an intentional bridge change; the two-step bootstrap was the only path that worked.
        """
        mutations = {
            "added": _SIMPLE_BRIDGE.replace(
                "fn synth_count(items: u32) -> u32;",
                "fn synth_count(items: u32) -> u32;\n        fn synth_new_fn() -> bool;",
            ),
            "removed": _SIMPLE_BRIDGE.replace(
                "        fn synth_count(items: u32) -> u32;\n", ""
            ),
            "changed": _SIMPLE_BRIDGE.replace("count: u32,", "total: u32,"),
        }
        for label, mutated in mutations.items():
            synth_repo = _bootstrap_synthetic_gate(
                tmp_path / label, {"synth.rs": _SIMPLE_BRIDGE}
            )
            synth_file = synth_repo / "cpp-bindings/classic-cpp-bridge/src/synth.rs"
            synth_file.write_text(mutated, encoding="utf-8")
            _write_synthetic_canonical_inventory(synth_repo)

            # The change is real drift until it is accepted.
            assert _run_gate(synth_repo).returncode == 1, f"{label} was not detected"

            accept = subprocess.run(
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
            assert accept.returncode == 0, (
                f"{label}: --update-baseline should accept the change. "
                f"stdout:\n{accept.stdout}\nstderr:\n{accept.stderr}"
            )

            # One refresh is enough: the next plain run is clean, with nothing left stale.
            settled = _run_gate(synth_repo)
            assert settled.returncode == 0, (
                f"{label}: gate still reports drift after one refresh. "
                f"stdout:\n{settled.stdout}\nstderr:\n{settled.stderr}"
            )

    def test_gate_fails_on_removed_function(self, tmp_path: Path):
        """A removed bridge function fails closed until its mapping is removed."""
        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        synth_file = synth_repo / "cpp-bindings/classic-cpp-bridge/src/synth.rs"
        mutated = _SIMPLE_BRIDGE.replace(
            "        fn synth_count(items: u32) -> u32;\n", ""
        )
        synth_file.write_text(mutated, encoding="utf-8")

        result = _run_gate(synth_repo)
        assert result.returncode == 1
        assert "stale canonical mappings" in result.stderr

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


class TestCanonicalMappingDrift:
    def test_gate_fails_when_a_current_row_loses_its_mapping(self, tmp_path: Path):
        """A bridge row cannot be accepted or refreshed without reviewed metadata."""

        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        mapping_path = (
            synth_repo / "tools" / "cxx_api_parity" / "canonical_mappings.json"
        )
        mappings = json.loads(mapping_path.read_text(encoding="utf-8"))
        mappings["entries"].pop()
        mapping_path.write_text(json.dumps(mappings, indent=2) + "\n", encoding="utf-8")

        result = _run_gate(synth_repo)

        assert result.returncode == 1
        assert "missing canonical mappings" in result.stderr

    def test_gate_fails_when_a_mapping_outlives_its_row(self, tmp_path: Path):
        """Removing bridge source cannot leave stale canonical metadata behind."""

        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        mapping_path = (
            synth_repo / "tools" / "cxx_api_parity" / "canonical_mappings.json"
        )
        mappings = json.loads(mapping_path.read_text(encoding="utf-8"))
        mappings["entries"].append(
            {
                "id": "removed-row-id",
                "rustSymbol": "removed_bridge_symbol",
                "kind": "function",
                "bridgeModule": "synth",
                "unmappedReason": "Synthetic row removed from bridge source.",
            }
        )
        mapping_path.write_text(json.dumps(mappings, indent=2) + "\n", encoding="utf-8")

        result = _run_gate(synth_repo)

        assert result.returncode == 1
        assert "stale canonical mappings" in result.stderr

    def test_gate_and_refresh_reject_a_stale_live_rust_target(self, tmp_path: Path):
        """Neither a normal run nor baseline refresh can bless a removed core symbol."""

        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        synth_lib = (
            synth_repo / "business-logic" / "classic-synth-core" / "src" / "lib.rs"
        )
        synth_lib.write_text("pub fn unrelated() {}\n", encoding="utf-8")

        result = _run_gate(synth_repo)
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

        assert result.returncode == 1
        assert refresh.returncode == 1
        assert "missing live Rust targets" in result.stderr
        assert "missing live Rust targets" in refresh.stderr

    def test_gate_rejects_tampered_contract_metadata_until_refresh(
        self, tmp_path: Path
    ):
        """The committed contract cannot contradict the independent mapping sidecar."""

        synth_repo = _bootstrap_synthetic_gate(tmp_path, {"synth.rs": _SIMPLE_BRIDGE})
        contract_path = (
            synth_repo
            / "docs/implementation/cxx_api_parity/baseline/parity_contract.json"
        )
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        row = contract["entries"][0]
        row.pop("ownerModule")
        row.pop("rustCrate")
        row.pop("coreRustSymbol")
        row["unmappedReason"] = "Fabricated binding-only classification."
        contract_path.write_text(
            json.dumps(contract, indent=2) + "\n", encoding="utf-8"
        )

        result = _run_gate(synth_repo)
        assert result.returncode == 1
        assert "stale canonical metadata" in result.stderr

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
        assert refresh.returncode == 0, refresh.stderr
        assert _run_gate(synth_repo).returncode == 0


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
