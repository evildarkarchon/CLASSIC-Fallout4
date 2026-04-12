from __future__ import annotations

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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_contains_all(
    test_case: unittest.TestCase, text: str, fragments: list[str]
) -> None:
    for fragment in fragments:
        with test_case.subTest(fragment=fragment):
            test_case.assertIn(fragment, text)


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

    @unittest.skip("Phase 6 Wave 1 pending")
    def test_stub_validator(self) -> None:
        pass

    @unittest.skip("Phase 6 Wave 1 pending")
    def test_rebuild_script(self) -> None:
        pass

    @unittest.skip("Phase 6 Wave 1 pending")
    def test_cargo_aliases(self) -> None:
        pass

    @unittest.skip("Phase 6 Wave 2 pending")
    def test_benchmark_support_set(self) -> None:
        pass

    @unittest.skip("Phase 6 Wave 3 pending")
    def test_repo_root_workflows(self) -> None:
        pass

    @unittest.skip("Phase 6 Wave 3 pending")
    def test_benchmark_workflow_paths(self) -> None:
        pass

    @unittest.skip("Phase 6 Wave 3 pending")
    def test_cargo_root_detection(self) -> None:
        pass

    @unittest.skip("Phase 6 Wave 3 pending")
    def test_old_manifest_audit(self) -> None:
        pass

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
