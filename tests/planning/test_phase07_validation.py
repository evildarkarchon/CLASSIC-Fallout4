from __future__ import annotations

import json
import subprocess
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = REPO_ROOT / ".planning/phases/07-crate-relocation-and-path-rewire"
RELOCATION_AUDIT = PHASE_DIR / "07-RELOCATION-AUDIT.md"
WORKSPACE_MANIFEST = REPO_ROOT / "Cargo.toml"
LEGACY_ROOT = REPO_ROOT / "ClassicLib-rs"
CRITERION_CONFIG = REPO_ROOT / "criterion.toml"
BENCHMARK_CONFIG = REPO_ROOT / "benchmark-config.yaml"
BENCH_COMMON_DIR = REPO_ROOT / "benches/common"
LEGACY_CRITERION_CONFIG = REPO_ROOT / "ClassicLib-rs/criterion.toml"
LEGACY_BENCHMARK_CONFIG = REPO_ROOT / "ClassicLib-rs/benchmark-config.yaml"
LEGACY_BENCH_COMMON_DIR = REPO_ROOT / "ClassicLib-rs/benches/common"
MOVED_LAYER_DIRS = [
    REPO_ROOT / "foundation",
    REPO_ROOT / "business-logic",
    REPO_ROOT / "cpp-bindings",
    REPO_ROOT / "node-bindings",
    REPO_ROOT / "python-bindings",
    REPO_ROOT / "ui-applications",
]
REPRESENTATIVE_MANIFESTS = {
    REPO_ROOT / "cpp-bindings/classic-cpp-bridge/Cargo.toml": {
        "classic-shared-core": "../../foundation/classic-shared-core",
        "classic-config-core": "../../business-logic/classic-config-core",
        "classic-scanlog-core": "../../business-logic/classic-scanlog-core",
    },
    REPO_ROOT / "node-bindings/classic-node/Cargo.toml": {
        "classic-shared-core": "../../foundation/classic-shared-core",
        "classic-settings-core": "../../business-logic/classic-settings-core",
        "classic-update-core": "../../business-logic/classic-update-core",
    },
    REPO_ROOT / "python-bindings/classic-config-py/Cargo.toml": {
        "classic-config-core": "../../business-logic/classic-config-core",
        "classic-shared-py": "../../foundation/classic-shared-py",
    },
    REPO_ROOT / "ui-applications/classic-tui/Cargo.toml": {
        "classic-shared-core": "../../foundation/classic-shared-core",
        "classic-scanlog-core": "../../business-logic/classic-scanlog-core",
        "classic-version-registry-core": "../../business-logic/classic-version-registry-core",
    },
}
BENCHMARK_INCLUDE_FILES = [
    REPO_ROOT / "business-logic/classic-settings-core/benches/yaml_benchmarks.rs",
    REPO_ROOT / "business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs",
    REPO_ROOT / "business-logic/classic-file-io-core/benches/file_io_benchmarks.rs",
    REPO_ROOT / "business-logic/classic-database-core/benches/database_benchmarks.rs",
    REPO_ROOT / "python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs",
    REPO_ROOT / "python-bindings/classic-file-io-py/benches/gil_benchmarks.rs",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def audit_residue_rows(text: str) -> list[str]:
    rows: list[str] = []
    in_residue_section = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## Legacy ClassicLib-rs Residue":
            in_residue_section = True
            continue
        if in_residue_section and stripped.startswith("## "):
            break
        if (
            in_residue_section
            and stripped.startswith("| `")
            and stripped.endswith("` |")
        ):
            rows.append(stripped[3:-3])

    return rows


def assert_contains_all(
    test_case: unittest.TestCase, text: str, fragments: list[str]
) -> None:
    for fragment in fragments:
        with test_case.subTest(fragment=fragment):
            test_case.assertIn(fragment, text)


def workspace_members() -> list[str]:
    workspace = read_toml(WORKSPACE_MANIFEST)["workspace"]
    assert isinstance(workspace, dict)
    members = workspace["members"]
    assert isinstance(members, list)
    return [str(member) for member in members]


def cargo_metadata() -> dict[str, object]:
    result = subprocess.run(
        ["cargo", "metadata", "--format-version", "1", "--no-deps"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    return json.loads(result.stdout)


class Phase07ValidationAuditTests(unittest.TestCase):
    def test_validation_bootstrap(self) -> None:
        self.assertTrue(REPO_ROOT.exists())
        self.assertTrue(PHASE_DIR.exists())
        self.assertTrue(RELOCATION_AUDIT.exists())

    def test_workspace_members_relocated(self) -> None:
        members = workspace_members()

        self.assertEqual(37, len(members))
        for member in members:
            with self.subTest(member=member):
                self.assertFalse(member.startswith("ClassicLib-rs/"))
                self.assertTrue((REPO_ROOT / member).exists())
                self.assertTrue((REPO_ROOT / member / "Cargo.toml").exists())

    def test_moved_layer_directories(self) -> None:
        for layer_dir in MOVED_LAYER_DIRS:
            with self.subTest(layer=str(layer_dir.relative_to(REPO_ROOT))):
                self.assertTrue(layer_dir.exists())
                self.assertFalse((LEGACY_ROOT / layer_dir.name).exists())

    def test_representative_manifest_paths(self) -> None:
        for manifest_path, expected_paths in REPRESENTATIVE_MANIFESTS.items():
            manifest_data = read_toml(manifest_path)
            dependencies = manifest_data["dependencies"]
            assert isinstance(dependencies, dict)

            for dependency_name, expected_path in expected_paths.items():
                with self.subTest(
                    manifest=str(manifest_path.relative_to(REPO_ROOT)),
                    dependency=dependency_name,
                ):
                    spec = dependencies[dependency_name]
                    assert isinstance(spec, dict)
                    self.assertEqual(expected_path, spec["path"])
                    resolved = (manifest_path.parent / expected_path).resolve()
                    self.assertTrue(resolved.exists())
                    self.assertTrue((resolved / "Cargo.toml").exists())

    def test_relocation_audit_complete(self) -> None:
        members = workspace_members()
        text = read_text(RELOCATION_AUDIT)

        assert_contains_all(
            self,
            text,
            [
                "# Phase 7 Relocation Audit",
                "## Old to New Crate Mapping",
                "## Cargo Root Proof",
                "## Stale Member and Manifest Sweep",
                "## Legacy ClassicLib-rs Residue",
                f"workspace_root={REPO_ROOT}",
                f"target_directory={REPO_ROOT / 'target'}",
                "members=37",
                "ClassicLib-rs/**/Cargo.toml` returned no files",
                "ClassicLib-rs/**/*.rs` contains no files outside legacy `target/` residue",
            ],
        )

        for member in members:
            row = f"| ClassicLib-rs/{member} | {member} |"
            with self.subTest(mapping=row):
                self.assertIn(row, text)

        for residue in audit_residue_rows(text):
            with self.subTest(residue=residue):
                self.assertIn(f"| `{residue}` |", text)

    def test_relocation_audit_mapping_matches_workspace_exactly(self) -> None:
        members = workspace_members()
        text = read_text(RELOCATION_AUDIT)

        actual_rows = sorted(
            line.strip()
            for line in text.splitlines()
            if line.startswith("| ClassicLib-rs/")
        )
        expected_rows = sorted(
            f"| ClassicLib-rs/{member} | {member} | Moved intact |"
            for member in members
        )

        self.assertEqual(expected_rows, actual_rows)

    def test_legacy_residue_inventory_matches_disk(self) -> None:
        actual_residue = sorted(
            f"{entry.name}/" if entry.is_dir() else entry.name
            for entry in LEGACY_ROOT.iterdir()
        )

        self.assertEqual(
            sorted(audit_residue_rows(read_text(RELOCATION_AUDIT))),
            actual_residue,
        )

    def test_benchmark_include_path_fallout_rewired(self) -> None:
        self.assertTrue(CRITERION_CONFIG.exists())
        self.assertTrue(BENCHMARK_CONFIG.exists())
        self.assertTrue((BENCH_COMMON_DIR / "mod.rs").exists())
        self.assertTrue((BENCH_COMMON_DIR / "config.rs").exists())
        self.assertFalse(LEGACY_CRITERION_CONFIG.exists())
        self.assertFalse(LEGACY_BENCHMARK_CONFIG.exists())
        self.assertFalse((LEGACY_BENCH_COMMON_DIR / "mod.rs").exists())
        self.assertFalse((LEGACY_BENCH_COMMON_DIR / "config.rs").exists())

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
            with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                self.assertIn("../../../benches/common/", text)
                self.assertNotIn("../../../../benches/common/", text)

    def test_cargo_root_detection(self) -> None:
        locate_result = subprocess.run(
            ["cargo", "locate-project", "--workspace", "--message-format", "plain"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        metadata = cargo_metadata()
        packages = metadata["packages"]
        assert isinstance(packages, list)

        self.assertEqual(str(WORKSPACE_MANIFEST), locate_result.stdout.strip())
        self.assertEqual(str(REPO_ROOT), metadata["workspace_root"])
        self.assertEqual(str(REPO_ROOT / "target"), metadata["target_directory"])
        self.assertEqual(37, len(metadata["workspace_members"]))

        for package in packages:
            manifest_path = Path(package["manifest_path"])
            with self.subTest(package=package["name"]):
                self.assertTrue(manifest_path.is_relative_to(REPO_ROOT))
                self.assertFalse(manifest_path.is_relative_to(LEGACY_ROOT))

    def test_legacy_classiclib_rs_boundary(self) -> None:
        legacy_manifests = sorted(
            path.relative_to(REPO_ROOT) for path in LEGACY_ROOT.rglob("Cargo.toml")
        )
        legacy_rust_files = sorted(
            path.relative_to(REPO_ROOT)
            for path in LEGACY_ROOT.rglob("*.rs")
            if "target" not in path.relative_to(LEGACY_ROOT).parts
        )

        self.assertEqual([], legacy_manifests)
        self.assertEqual([], legacy_rust_files)
