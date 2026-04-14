from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestPhase08Validation(unittest.TestCase):
    maxDiff = None

    def run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 900,
        expected_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        output = result.stdout + result.stderr
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                f"Command failed: {' '.join(command)}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            ),
        )
        if expected_text is not None:
            self.assertIn(expected_text, output)
        return result

    def load_json(self, *parts: str) -> dict:
        return json.loads((REPO_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))

    def test_wrapper_paths_are_repo_root_only(self) -> None:
        rebuild_rust = (REPO_ROOT / "rebuild_rust.ps1").read_text(encoding="utf-8")
        rebuild_node = (REPO_ROOT / "rebuild_node.ps1").read_text(encoding="utf-8")

        self.assertIn('Join-Path $ProjectRoot "python-bindings"', rebuild_rust)
        self.assertIn(
            'Join-Path $ProjectRoot "node-bindings/classic-node"', rebuild_rust
        )
        self.assertNotIn("ClassicLib-rs/python-bindings", rebuild_rust)
        self.assertNotIn("ClassicLib-rs/node-bindings", rebuild_rust)
        self.assertIn("rebuild_rust.ps1", rebuild_node)
        self.assertIn("-Target node", rebuild_node)
        self.assertNotIn("bun run build", rebuild_node)

    def test_native_bridge_paths_and_tui_probe_are_repo_root_based(self) -> None:
        cli_cmake = (REPO_ROOT / "classic-cli" / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        gui_cmake = (REPO_ROOT / "classic-gui" / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        tui_main = (
            REPO_ROOT / "ui-applications" / "classic-tui" / "src" / "main.rs"
        ).read_text(encoding="utf-8")

        for text in (cli_cmake, gui_cmake):
            self.assertIn("cpp-bindings/classic-cpp-bridge/include", text)
            self.assertNotIn(
                "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include", text
            )

        self.assertIn("env::args", tui_main)
        self.assertIn("--version", tui_main)
        self.assertIn("--help", tui_main)
        self.assertLess(
            tui_main.index("handle_cli_probe()"),
            tui_main.index("let mut stderr_handle = stderr()"),
        )

    def test_parity_tools_and_package_scripts_are_repo_root_only(self) -> None:
        files = {
            "validate_stubs.py": REPO_ROOT / "validate_stubs.py",
            "python_check": REPO_ROOT
            / "tools"
            / "python_api_parity"
            / "check_parity_gate.py",
            "python_generate": REPO_ROOT
            / "tools"
            / "python_api_parity"
            / "generate_baseline.py",
            "node_check": REPO_ROOT
            / "tools"
            / "node_api_parity"
            / "check_parity_gate.py",
            "node_dts": REPO_ROOT
            / "tools"
            / "node_api_parity"
            / "check_dts_freshness.py",
            "node_generate": REPO_ROOT
            / "tools"
            / "node_api_parity"
            / "generate_baseline.py",
            "cxx_check": REPO_ROOT
            / "tools"
            / "cxx_api_parity"
            / "check_parity_gate.py",
            "cxx_generate": REPO_ROOT
            / "tools"
            / "cxx_api_parity"
            / "generate_baseline.py",
            "package": REPO_ROOT / "node-bindings" / "classic-node" / "package.json",
        }

        for path in files.values():
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("ClassicLib-rs/python-bindings", text)
            self.assertNotIn("ClassicLib-rs/node-bindings", text)
            self.assertNotIn("ClassicLib-rs/cpp-bindings", text)

        package_text = files["package"].read_text(encoding="utf-8")
        self.assertIn(
            "../../tools/node_api_parity/check_parity_gate.py --repo-root ../..",
            package_text,
        )
        self.assertIn(
            "../../tools/node_api_parity/check_dts_freshness.py --repo-root ../.. --check-only",
            package_text,
        )
        self.assertIn("../../tools/enter_vs_dev_shell.ps1", package_text)

    def test_checked_in_parity_artifacts_no_longer_encode_legacy_paths(self) -> None:
        artifact_paths = [
            REPO_ROOT / "docs" / "implementation" / "python_api_parity" / "baseline",
            REPO_ROOT / "docs" / "implementation" / "node_api_parity" / "baseline",
            REPO_ROOT / "docs" / "implementation" / "cxx_api_parity" / "baseline",
        ]

        for directory in artifact_paths:
            for artifact in directory.iterdir():
                if artifact.is_file() and artifact.suffix in {".json", ".md"}:
                    text = artifact.read_text(encoding="utf-8")
                    self.assertNotIn(
                        "ClassicLib-rs/python-bindings", text, artifact.as_posix()
                    )
                    self.assertNotIn(
                        "ClassicLib-rs/node-bindings", text, artifact.as_posix()
                    )
                    self.assertNotIn(
                        "ClassicLib-rs/cpp-bindings", text, artifact.as_posix()
                    )

    def test_live_repo_root_tui_entrypoint_smoke(self) -> None:
        self.run_command(
            ["cargo", "run", "-p", "classic-tui", "--", "--version"],
            timeout=300,
            expected_text="classic-tui 0.1.0",
        )

    def test_live_native_wrapper_test_flows_smoke(self) -> None:
        self.run_command(
            [
                "pwsh",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "classic-cli" / "build_cli.ps1"),
                "-Test",
            ],
            timeout=900,
            expected_text="RESULT: ALL TESTS PASSED",
        )
        self.run_command(
            [
                "pwsh",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "classic-gui" / "build_gui.ps1"),
                "-Test",
            ],
            timeout=900,
            expected_text="Tests passed.",
        )

    def test_live_python_parity_and_stub_flows_smoke(self) -> None:
        self.run_command(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "python_api_parity" / "check_parity_gate.py"),
                "--repo-root",
                ".",
            ],
            timeout=300,
            expected_text="Tier-1 parity gate passed.",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            json_out = Path(temp_dir) / "stub_validation_report.json"
            self.run_command(
                [
                    sys.executable,
                    str(REPO_ROOT / "validate_stubs.py"),
                    "--rust-dir",
                    ".",
                    "--parity-contract",
                    "docs/implementation/python_api_parity/baseline/parity_contract.json",
                    "--json-out",
                    str(json_out),
                    "--fail-on-warnings",
                ],
                timeout=300,
                expected_text="[OK] Crates passed: 16/16",
            )
            self.assertTrue(json_out.is_file())

    def test_live_node_package_scripts_smoke(self) -> None:
        package_dir = REPO_ROOT / "node-bindings" / "classic-node"
        self.run_command(
            ["bun", "run", "parity:gate"],
            cwd=package_dir,
            timeout=300,
            expected_text="Tier-1 parity gate passed.",
        )
        self.run_command(
            ["bun", "run", "dts:freshness:check"],
            cwd=package_dir,
            timeout=300,
            expected_text="index.d.ts freshness check passed.",
        )
        self.run_command(
            ["bun", "run", "build"],
            cwd=package_dir,
            timeout=300,
            expected_text="bun x tsc -p tsconfig.json",
        )

    def test_live_repo_root_rebuild_wrappers_smoke(self) -> None:
        self.run_command(
            [
                "pwsh",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "rebuild_rust.ps1"),
                "-Target",
                "python",
                "-BuildOnly",
            ],
            timeout=900,
            expected_text="✨ Rebuild target 'python' complete.",
        )
        self.run_command(
            [
                "pwsh",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "rebuild_rust.ps1"),
                "-Target",
                "node",
                "-BuildOnly",
            ],
            timeout=600,
            expected_text="✨ Rebuild target 'node' complete.",
        )
        self.run_command(
            [
                "pwsh",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "rebuild_node.ps1"),
            ],
            timeout=600,
            expected_text="✨ Rebuild target 'node' complete.",
        )
        self.run_command(
            [
                "pwsh",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "rebuild_node.ps1"),
                "-Debug",
            ],
            timeout=600,
            expected_text="✨ Rebuild target 'node' complete.",
        )

    def test_python_checked_in_artifacts_lock_semantics_and_repo_root_metadata(
        self,
    ) -> None:
        contract = self.load_json(
            "docs",
            "implementation",
            "python_api_parity",
            "baseline",
            "parity_contract.json",
        )
        diff_report = self.load_json(
            "docs",
            "implementation",
            "python_api_parity",
            "baseline",
            "parity_diff_report.json",
        )
        runtime_summary = self.load_json(
            "docs",
            "implementation",
            "python_api_parity",
            "baseline",
            "runtime_coverage_summary.json",
        )
        python_surface = self.load_json(
            "docs",
            "implementation",
            "python_api_parity",
            "baseline",
            "python_api_surface.json",
        )
        rust_surface = self.load_json(
            "docs",
            "implementation",
            "python_api_parity",
            "baseline",
            "rust_api_surface.json",
        )

        contract_ids = [row["id"] for row in contract["tier1Mappings"]]
        diff_ids = [row["id"] for row in diff_report["contract_results"]]
        tracked_contract_ids = [
            row["contractId"]
            for row in runtime_summary["trackedSurface"]
            if row.get("trackedType") == "contract_row"
        ]

        self.assertEqual(len(contract_ids), 1098)
        self.assertEqual(len(contract_ids), len(set(contract_ids)))
        self.assertEqual(set(diff_ids), set(contract_ids))
        self.assertEqual(set(tracked_contract_ids), set(contract_ids))
        self.assertEqual(
            set(contract["ownerModules"]),
            {
                "scanlog",
                "config",
                "version_registry",
                "aux",
                "database",
                "file_io",
                "scangame",
                "registry",
                "perf",
                "settings",
                "message",
                "path",
                "version",
                "resource",
                "xse",
                "web",
                "update",
                "shared",
            },
        )

        self.assertEqual(diff_report["summary"]["tier1_contract_total"], 1098)
        self.assertEqual(diff_report["summary"]["tier1_matched"], 1098)
        self.assertEqual(diff_report["summary"]["tier1_gap_total"], 0)

        self.assertEqual(
            runtime_summary["sources"]["runtime_registry"],
            "python-bindings/tests/fixtures/runtime_coverage_registry.json",
        )
        self.assertEqual(runtime_summary["summary"]["tracked_surface_total"], 1264)
        self.assertEqual(runtime_summary["summary"]["runtime_verified_total"], 1264)
        self.assertEqual(runtime_summary["summary"]["tier1_contract_total"], 1098)
        self.assertEqual(runtime_summary["summary"]["registry_mismatch_total"], 0)
        self.assertEqual(runtime_summary["perOwnerModule"]["scanlog"]["total"], 377)
        self.assertEqual(runtime_summary["perOwnerModule"]["shared"]["total"], 69)

        self.assertEqual(len(python_surface["scope"]["target_modules"]), 17)
        self.assertEqual(len(python_surface["scope"]["source_files"]), 17)
        self.assertIn(
            "foundation/classic-shared-py/classic_shared.pyi",
            python_surface["scope"]["source_files"],
        )
        for rel_path in python_surface["scope"]["source_files"]:
            self.assertTrue(
                rel_path.startswith("python-bindings/")
                or rel_path.startswith("foundation/classic-shared-py/"),
                rel_path,
            )

        self.assertEqual(len(rust_surface["scope"]["target_crates"]), 18)
        self.assertEqual(len(rust_surface["scope"]["source_files"]), 18)
        self.assertIn(
            "foundation/classic-shared-py/src/lib.rs",
            rust_surface["scope"]["source_files"],
        )

    def test_node_checked_in_artifacts_lock_semantics_and_repo_root_metadata(
        self,
    ) -> None:
        contract = self.load_json(
            "docs",
            "implementation",
            "node_api_parity",
            "baseline",
            "parity_contract.json",
        )
        diff_report = self.load_json(
            "docs",
            "implementation",
            "node_api_parity",
            "baseline",
            "parity_diff_report.json",
        )
        runtime_summary = self.load_json(
            "docs",
            "implementation",
            "node_api_parity",
            "baseline",
            "runtime_coverage_summary.json",
        )
        node_surface = self.load_json(
            "docs",
            "implementation",
            "node_api_parity",
            "baseline",
            "node_api_surface.json",
        )
        rust_surface = self.load_json(
            "docs",
            "implementation",
            "node_api_parity",
            "baseline",
            "rust_api_surface.json",
        )

        contract_ids = [row["id"] for row in contract["tier1Mappings"]]
        diff_ids = [row["id"] for row in diff_report["contract_results"]]
        tracked_contract_ids = [
            row["contractId"]
            for row in runtime_summary["trackedSurface"]
            if row.get("trackedType") == "contract_row"
        ]

        self.assertEqual(len(contract_ids), 705)
        self.assertEqual(Counter(diff_ids), Counter(contract_ids))
        self.assertEqual(Counter(tracked_contract_ids), Counter(contract_ids))
        self.assertIn(
            "one-tier 705-row Node vs Rust parity contract", contract["description"]
        )

        self.assertEqual(diff_report["summary"]["tier1_contract_total"], 705)
        self.assertEqual(diff_report["summary"]["tier1_matched"], 705)
        self.assertEqual(diff_report["summary"]["tier1_gap_total"], 0)

        self.assertEqual(
            runtime_summary["sources"]["runtime_registry"],
            "node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json",
        )
        self.assertEqual(
            runtime_summary["sources"]["index_dts"],
            "node-bindings/classic-node/index.d.ts",
        )
        self.assertEqual(runtime_summary["summary"]["tracked_surface_total"], 731)
        self.assertEqual(runtime_summary["summary"]["runtime_verified_total"], 731)
        self.assertEqual(runtime_summary["summary"]["tier1_contract_total"], 705)
        self.assertEqual(runtime_summary["summary"]["registry_mismatch_total"], 0)
        self.assertEqual(runtime_summary["perOwnerModule"]["aux"]["total"], 169)
        self.assertEqual(runtime_summary["perOwnerModule"]["scanlog"]["total"], 95)

        self.assertEqual(
            node_surface["scope"]["source_file"],
            "node-bindings/classic-node/index.d.ts",
        )
        self.assertEqual(len(rust_surface["scope"]["target_crates"]), 16)
        self.assertEqual(len(rust_surface["scope"]["source_files"]), 16)
        for rel_path in rust_surface["scope"]["source_files"]:
            self.assertTrue(
                rel_path.startswith("business-logic/")
                or rel_path.startswith("foundation/classic-shared-core/"),
                rel_path,
            )


if __name__ == "__main__":
    unittest.main()
