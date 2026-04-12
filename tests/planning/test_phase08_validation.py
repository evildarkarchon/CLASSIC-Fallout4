from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestPhase08Validation(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
