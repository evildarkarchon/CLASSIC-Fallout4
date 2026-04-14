from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = REPO_ROOT / ".planning" / "phases" / "09-clean-validation-and-ci-refresh"
AUDIT_PATH = PHASE_DIR / "09-CLEAN-VALIDATION-AUDIT.md"
HARNESS_PATH = REPO_ROOT / "tests" / "planning" / "phase09_clean_run.ps1"
CI_RUST_PATH = REPO_ROOT / ".github" / "workflows" / "ci-rust.yml"
CI_CPP_PATH = REPO_ROOT / ".github" / "workflows" / "ci-cpp.yml"
BENCHMARKS_PATH = REPO_ROOT / ".github" / "workflows" / "benchmarks.yml"
CI_PYTHON_BINDINGS_PATH = REPO_ROOT / ".github" / "workflows" / "ci-python-bindings.yml"
CI_TYPESCRIPT_PATH = REPO_ROOT / ".github" / "workflows" / "ci-typescript.yml"


class TestPhase09Validation(unittest.TestCase):
    maxDiff = None

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

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

    def test_required_audit_sections_present(self) -> None:
        audit_text = self.read_text(AUDIT_PATH)

        for section in (
            "## Targeted Clean Inventory",
            "## Workflow Contract Matrix",
            "## CI-Owned Artifact Scope",
            "## Refreshed Artifact Results",
            "## GUI Package Proof Surface",
            "## Legacy Residue Failure Rules",
        ):
            self.assertIn(section, audit_text)

    def test_workflow_and_package_surface(self) -> None:
        audit_text = self.read_text(AUDIT_PATH)
        harness_text = self.read_text(HARNESS_PATH)

        for workflow in (
            ".github/workflows/ci-rust.yml",
            ".github/workflows/ci-python-bindings.yml",
            ".github/workflows/ci-typescript.yml",
            ".github/workflows/ci-cpp.yml",
            ".github/workflows/benchmarks.yml",
        ):
            self.assertIn(workflow, audit_text)

        self.assertIn("classic-gui/build_gui.ps1 -Package", audit_text)
        self.assertIn("classic-gui/build_gui.ps1 -Package", harness_text)
        self.assertIn("test_phase09_validation.py", harness_text)

    def test_clean_state_and_residue(self) -> None:
        audit_text = self.read_text(AUDIT_PATH)
        harness_text = self.read_text(HARNESS_PATH)

        for clean_target in (
            "ClassicLib-rs/target",
            "repo-root `target`",
            "python-bindings/.venv",
            "node-bindings/classic-node/node_modules",
            "node-bindings/classic-node/dist",
            "built `.node` outputs under `node-bindings/classic-node`",
            "python-bindings/parity-artifacts",
            "node-bindings/classic-node/parity-artifacts",
            "cpp-bindings/classic-cpp-bridge/parity-artifacts",
        ):
            self.assertIn(clean_target, audit_text)

        for harness_target in (
            "ClassicLib-rs/target.phase9-backup",
            "python-bindings/.venv",
            "node-bindings/classic-node/node_modules",
            "node-bindings/classic-node/dist",
            "cpp-bindings/classic-cpp-bridge/parity-artifacts",
            "Get-LegacyGeneratedSnapshot",
            "Compare-Object",
        ):
            self.assertIn(harness_target, harness_text)

        self.assertIn(
            "Any new generated output under `ClassicLib-rs/` is a Phase 9 failure.",
            audit_text,
        )

    def test_rust_cpp_benchmark_workflows(self) -> None:
        audit_text = self.read_text(AUDIT_PATH)
        ci_rust_text = self.read_text(CI_RUST_PATH)
        ci_cpp_text = self.read_text(CI_CPP_PATH)
        benchmarks_text = self.read_text(BENCHMARKS_PATH)

        for required_text in (
            ".github/workflows/ci-rust.yml",
            ".github/workflows/ci-cpp.yml",
            ".github/workflows/benchmarks.yml",
            "foundation/**/*.rs",
            "cpp-bindings/classic-cpp-bridge/parity-artifacts/",
            "target/criterion/baseline",
        ):
            self.assertIn(required_text, audit_text)

        self.assertNotIn("ClassicLib-rs/**/*.rs", ci_rust_text)
        self.assertNotIn("ClassicLib-rs/**/*.rs", ci_cpp_text)
        self.assertNotIn("ClassicLib-rs/**/*.rs", benchmarks_text)
        self.assertNotIn("ClassicLib-rs/target", ci_cpp_text)
        self.assertIn("hashFiles('foundation/**/*.rs'", ci_rust_text)
        self.assertIn("hashFiles('foundation/**/*.rs'", benchmarks_text)
        self.assertIn("cpp-bindings/classic-cpp-bridge/parity-artifacts/", ci_cpp_text)
        self.assertIn("target/criterion/baseline", benchmarks_text)

    def test_gui_package_surface(self) -> None:
        audit_text = self.read_text(AUDIT_PATH)
        harness_text = self.read_text(HARNESS_PATH)

        self.assertIn("classic-gui/build_gui.ps1 -Package", audit_text)
        self.assertIn("classic-gui/build_gui.ps1 -Package", harness_text)

    def test_python_node_workflows(self) -> None:
        audit_text = self.read_text(AUDIT_PATH)
        ci_python_text = self.read_text(CI_PYTHON_BINDINGS_PATH)
        ci_typescript_text = self.read_text(CI_TYPESCRIPT_PATH)

        for required_text in (
            ".github/workflows/ci-python-bindings.yml",
            "python validate_stubs.py --rust-dir .",
            "python-bindings/.venv",
            ".github/workflows/ci-typescript.yml",
            "node-bindings/classic-node",
            "node-bindings/classic-node/parity-artifacts/",
        ):
            self.assertIn(required_text, audit_text)

        self.assertNotIn("ClassicLib-rs/validate_stubs.py", ci_python_text)
        self.assertNotIn("ClassicLib-rs/python-bindings", ci_python_text)
        self.assertNotIn("ClassicLib-rs/node-bindings/classic-node", ci_typescript_text)
        self.assertNotIn("ClassicLib-rs/target", ci_typescript_text)
        self.assertIn("python validate_stubs.py --rust-dir .", ci_python_text)
        self.assertIn(
            "python-bindings/parity-artifacts/stub_validation_report.json",
            ci_python_text,
        )
        self.assertIn("python-bindings/.venv", ci_python_text)
        self.assertIn("python-bindings/requirements-ci.txt", ci_python_text)
        self.assertIn("python-bindings/tests -q", ci_python_text)
        self.assertIn(
            "working-directory: node-bindings/classic-node", ci_typescript_text
        )
        self.assertIn(
            "node-bindings/classic-node/parity-artifacts/", ci_typescript_text
        )
        self.assertIn("path: target", ci_python_text)
        self.assertIn("path: target", ci_typescript_text)

    def test_artifact_scope_rules(self) -> None:
        audit_text = self.read_text(AUDIT_PATH)

        for required_text in (
            "python-bindings/parity-artifacts/",
            "node-bindings/classic-node/parity-artifacts/",
            "docs/implementation/**/baseline/",
            "Anything outside those directories is out of scope for this phase",
            "## Refreshed Artifact Results",
            "cpp-bindings/classic-cpp-bridge/parity-artifacts/",
        ):
            self.assertIn(required_text, audit_text)

    def test_no_new_legacy_residue(self) -> None:
        audit_text = self.read_text(AUDIT_PATH)
        harness_text = self.read_text(HARNESS_PATH)

        for required_text in (
            "cargo locate-project --workspace --message-format plain",
            "python validate_stubs.py --rust-dir .",
            "bun run dts:freshness:check",
            "classic-gui/build_gui.ps1 -Package",
            "python -m pytest tests/planning/test_phase09_validation.py -q",
        ):
            self.assertIn(required_text, audit_text)
            self.assertIn(required_text, harness_text)

        proof_order = [
            "cargo locate-project --workspace --message-format plain",
            "cargo metadata --format-version 1 --no-deps",
            "python tools/python_api_parity/check_parity_gate.py --repo-root .",
            "python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings",
            "bun install",
            "bun run build",
            "bun run parity:gate",
            "bun run dts:freshness:check",
            "python tools/cxx_api_parity/check_parity_gate.py --repo-root .",
            "pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package",
            "python -m pytest tests/planning/test_phase09_validation.py -q",
        ]
        harness_positions = [harness_text.index(command) for command in proof_order]
        audit_proof_block = audit_text.split(
            "The final clean proof runs these commands in order:", 1
        )[1]
        audit_positions = [audit_proof_block.index(command) for command in proof_order]
        self.assertEqual(harness_positions, sorted(harness_positions))
        self.assertEqual(audit_positions, sorted(audit_positions))

        self.assertIn("Post-proof legacy residue check", audit_text)
        self.assertIn("ClassicLib-rs/", audit_text)
        self.assertIn("$PreProofLegacyState", harness_text)
        self.assertIn("$PostProofLegacyState", harness_text)
