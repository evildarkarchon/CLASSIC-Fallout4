from __future__ import annotations

import importlib.util
import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = REPO_ROOT / ".planning/phases/06-repo-root-workspace-cutover"
CLEAN_RUN_HELPER = REPO_ROOT / "tests/planning/phase06_clean_run.ps1"
WORKSPACE_MANIFEST = REPO_ROOT / "Cargo.toml"
ROOT_CARGO_LOCK = REPO_ROOT / "Cargo.lock"
ROOT_CARGO_CONFIG = REPO_ROOT / ".cargo/config.toml"
LEGACY_WORKSPACE_MANIFEST = REPO_ROOT / "ClassicLib-rs/Cargo.toml"
LEGACY_CARGO_LOCK = REPO_ROOT / "ClassicLib-rs/Cargo.lock"
LEGACY_CARGO_CONFIG = REPO_ROOT / "ClassicLib-rs/.cargo/config.toml"
STUB_VALIDATOR = REPO_ROOT / "validate_stubs.py"
LEGACY_STUB_VALIDATOR = REPO_ROOT / "ClassicLib-rs/validate_stubs.py"
REBUILD_SCRIPT = REPO_ROOT / "rebuild_rust.ps1"
CI_RUST_WORKFLOW = REPO_ROOT / ".github/workflows/ci-rust.yml"
BENCHMARKS_WORKFLOW = REPO_ROOT / ".github/workflows/benchmarks.yml"
BENCHMARK_CONFIG = REPO_ROOT / "benchmark-config.yaml"
CRITERION_CONFIG = REPO_ROOT / "criterion.toml"
BENCH_COMMON_DIR = REPO_ROOT / "benches/common"
LEGACY_BENCHMARK_CONFIG = REPO_ROOT / "ClassicLib-rs/benchmark-config.yaml"
LEGACY_CRITERION_CONFIG = REPO_ROOT / "ClassicLib-rs/criterion.toml"
LEGACY_BENCH_COMMON_DIR = REPO_ROOT / "ClassicLib-rs/benches/common"
BENCHMARK_INCLUDE_FILES = [
    REPO_ROOT
    / "ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs",
    REPO_ROOT
    / "ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs",
    REPO_ROOT
    / "ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs",
    REPO_ROOT
    / "ClassicLib-rs/business-logic/classic-database-core/benches/database_benchmarks.rs",
    REPO_ROOT
    / "ClassicLib-rs/python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs",
    REPO_ROOT
    / "ClassicLib-rs/python-bindings/classic-file-io-py/benches/gil_benchmarks.rs",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_contains_all(
    test_case: unittest.TestCase, text: str, fragments: list[str]
) -> None:
    for fragment in fragments:
        with test_case.subTest(fragment=fragment):
            test_case.assertIn(fragment, text)


def load_module(path: Path, module_name: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Phase06ValidationAuditTests(unittest.TestCase):
    def test_validation_bootstrap(self) -> None:
        self.assertTrue(REPO_ROOT.exists())
        self.assertTrue(PHASE_DIR.exists())

    def test_workspace_root_manifest(self) -> None:
        self.assertTrue(WORKSPACE_MANIFEST.exists())
        self.assertFalse(LEGACY_WORKSPACE_MANIFEST.exists())

        text = read_text(WORKSPACE_MANIFEST)
        assert_contains_all(
            self,
            text,
            [
                "[workspace]",
                'resolver = "2"',
                '"ClassicLib-rs/business-logic/classic-scanlog-core"',
                '"ClassicLib-rs/python-bindings/classic-config-py"',
                "[workspace.dependencies]",
                "[workspace.lints.rust]",
                "[profile.release]",
                "[profile.release-with-debug]",
            ],
        )
        self.assertNotIn("default-members", text)

    def test_core_root_files(self) -> None:
        self.assertTrue(ROOT_CARGO_LOCK.exists())
        self.assertTrue(ROOT_CARGO_CONFIG.exists())
        self.assertFalse(LEGACY_CARGO_LOCK.exists())
        self.assertFalse(LEGACY_CARGO_CONFIG.exists())

        assert_contains_all(
            self,
            read_text(ROOT_CARGO_CONFIG),
            [
                "[alias]",
                'flame = "flamegraph"',
                'flame-bench = "flamegraph --bench"',
                'profile-build = "build --profile release-with-debug"',
            ],
        )

    def test_stub_validator(self) -> None:
        self.assertTrue(STUB_VALIDATOR.exists())
        self.assertFalse(LEGACY_STUB_VALIDATOR.exists())

        text = read_text(STUB_VALIDATOR)
        assert_contains_all(
            self,
            text,
            [
                "python validate_stubs.py",
                "--rust-dir ClassicLib-rs",
                "repo root",
                "ClassicLib-rs",
            ],
        )

        module = load_module(STUB_VALIDATOR, "phase06_validate_stubs")
        expected_workspace = REPO_ROOT / "ClassicLib-rs"
        self.assertEqual(module.normalize_rust_dir(REPO_ROOT), expected_workspace)
        self.assertEqual(
            module.normalize_rust_dir(REPO_ROOT / "ClassicLib-rs"),
            expected_workspace,
        )

    def test_rebuild_script(self) -> None:
        self.assertTrue(REBUILD_SCRIPT.exists())
        text = read_text(REBUILD_SCRIPT)

        self.assertNotIn("ClassicLib-rs/Cargo.toml", text)
        self.assertNotIn("--manifest-path", text)
        assert_contains_all(
            self,
            text,
            [
                '$WorkspaceRootManifest = Join-Path $ProjectRoot "Cargo.toml"',
                "& cargo clean",
                '$cargoArgs = @("build")',
                '$cargoArgs += "--workspace"',
                "& cargo clean -p classic-node",
            ],
        )

    def test_cargo_aliases(self) -> None:
        assert_contains_all(
            self,
            read_text(ROOT_CARGO_CONFIG),
            [
                'flame = "flamegraph"',
                'flame-bench = "flamegraph --bench"',
                'profile-build = "build --profile release-with-debug"',
            ],
        )

    def test_benchmark_support_set(self) -> None:
        self.assertTrue(CRITERION_CONFIG.exists())
        self.assertTrue(BENCHMARK_CONFIG.exists())
        self.assertTrue((BENCH_COMMON_DIR / "mod.rs").exists())
        self.assertTrue((BENCH_COMMON_DIR / "config.rs").exists())
        self.assertTrue((BENCH_COMMON_DIR / "db_fixtures.rs").exists())
        self.assertTrue((BENCH_COMMON_DIR / "fixtures.rs").exists())

        self.assertFalse(LEGACY_CRITERION_CONFIG.exists())
        self.assertFalse(LEGACY_BENCHMARK_CONFIG.exists())
        self.assertFalse((LEGACY_BENCH_COMMON_DIR / "mod.rs").exists())
        self.assertFalse((LEGACY_BENCH_COMMON_DIR / "config.rs").exists())
        self.assertFalse((LEGACY_BENCH_COMMON_DIR / "db_fixtures.rs").exists())
        self.assertFalse((LEGACY_BENCH_COMMON_DIR / "fixtures.rs").exists())

        assert_contains_all(
            self,
            read_text(CRITERION_CONFIG),
            [
                'criterion_home = "./target/criterion"',
                "[output]",
                "verbose = true",
            ],
        )
        assert_contains_all(
            self,
            read_text(BENCHMARK_CONFIG),
            [
                "defaults:",
                "warning_threshold: 5",
                "failure_threshold: 10",
                "overrides:",
            ],
        )

        for path in BENCHMARK_INCLUDE_FILES:
            text = read_text(path)
            with self.subTest(path=str(path)):
                self.assertIn("../../../../benches/common/", text)
                self.assertNotIn('#[path = "../../../benches/common/', text)

    def test_repo_root_workflows(self) -> None:
        text = read_text(CI_RUST_WORKFLOW)
        self.assertNotIn("ClassicLib-rs/Cargo.toml", text)
        self.assertNotIn("ClassicLib-rs/target", text)
        self.assertNotIn("--manifest-path", text)
        assert_contains_all(
            self,
            text,
            [
                "cargo fmt --all -- --check",
                "cargo clippy --workspace --all-targets --all-features -- -D warnings",
                "cargo build --workspace --release",
                "cargo test -p classic-message-core -- --nocapture",
                "cargo test --workspace --release -- --nocapture",
                "cargo test --workspace --release --all-features -- --nocapture",
                "path: target",
            ],
        )

    def test_benchmark_workflow_paths(self) -> None:
        text = read_text(BENCHMARKS_WORKFLOW)
        self.assertNotIn("working-directory: ClassicLib-rs", text)
        self.assertNotIn("ClassicLib-rs/target", text)
        assert_contains_all(
            self,
            text,
            [
                "path: target",
                "path: target/criterion/baseline",
                'CONFIG_FILE="benchmark-config.yaml"',
                "run: cargo bench -- --save-baseline current",
            ],
        )

    def test_cargo_root_detection(self) -> None:
        locate_result = subprocess.run(
            ["cargo", "locate-project", "--workspace", "--message-format", "plain"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(Path(locate_result.stdout.strip()), WORKSPACE_MANIFEST)

        metadata_result = subprocess.run(
            ["cargo", "metadata", "--format-version", "1", "--no-deps"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        metadata = json.loads(metadata_result.stdout)
        self.assertEqual(Path(metadata["workspace_root"]), REPO_ROOT)
        self.assertEqual(Path(metadata["target_directory"]), REPO_ROOT / "target")

    def test_old_manifest_audit(self) -> None:
        self.assertFalse(LEGACY_WORKSPACE_MANIFEST.exists())

        for path in [
            CI_RUST_WORKFLOW,
            BENCHMARKS_WORKFLOW,
            REBUILD_SCRIPT,
            STUB_VALIDATOR,
            CLEAN_RUN_HELPER,
        ]:
            text = read_text(path)
            with self.subTest(path=str(path)):
                self.assertNotIn("ClassicLib-rs/Cargo.toml", text)
                self.assertNotIn("--manifest-path", text)

    def test_clean_target_guard(self) -> None:
        self.assertTrue(CLEAN_RUN_HELPER.exists())
        text = read_text(CLEAN_RUN_HELPER)

        for fragment in [
            "ClassicLib-rs/target",
            "cargo locate-project --workspace",
            "cargo metadata --format-version 1 --no-deps",
            "cargo fmt --all -- --check",
            "cargo clippy --workspace --all-targets --all-features -- -D warnings",
            "cargo test --workspace --release -- --nocapture",
            "cargo build -p classic-scanlog-core",
            "python -m pytest tests/planning/test_phase06_validation.py -q",
        ]:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    @unittest.skip("Phase 6 Wave 3 pending")
    def test_readme_sync(self) -> None:
        pass

    @unittest.skip("Phase 6 Wave 3 pending")
    def test_agents_sync(self) -> None:
        pass


if __name__ == "__main__":
    unittest.main()
