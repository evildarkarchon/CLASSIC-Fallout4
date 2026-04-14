from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_MATRIX = REPO_ROOT / "docs/workspace-migration-matrix.md"

LINK_REQUIRED_SURFACES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs/README.md",
    REPO_ROOT / "docs/RUST_DOCUMENTATION_INDEX.md",
    REPO_ROOT / "docs/testing/TESTING_GUIDE_INDEX.md",
    REPO_ROOT / "docs/api/README.md",
    REPO_ROOT / "docs/api/QUICK_START.md",
    REPO_ROOT / "docs/api/binding-contract-refresh-note.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / ".agents/skills/classic-project-guide/SKILL.md",
    REPO_ROOT / ".opencode/skills/classic-project-guide/SKILL.md",
    REPO_ROOT / ".claude/skills/classic-project-guide/SKILL.md",
    REPO_ROOT / ".agent/skills/classic-project-guide/SKILL.md",
]

ACTIVE_TOP_LEVEL_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs/README.md",
    REPO_ROOT / "docs/RUST_DOCUMENTATION_INDEX.md",
    REPO_ROOT / "docs/testing/TESTING_GUIDE_INDEX.md",
]

ACTIVE_API_HUB_DOCS = [
    REPO_ROOT / "docs/api/README.md",
    REPO_ROOT / "docs/api/QUICK_START.md",
    REPO_ROOT / "docs/api/binding-contract-refresh-note.md",
    REPO_ROOT / "docs/api/binding-parity-policy.md",
    REPO_ROOT / "docs/api/node-python-contract-map.md",
    REPO_ROOT / "docs/api/cxx-parity-gate.md",
    REPO_ROOT / "docs/api/error-contract.md",
]

ACTIVE_API_CORE_GROUP_A = [
    REPO_ROOT / "docs/api/classic-shared-core.md",
    REPO_ROOT / "docs/api/classic-message-core.md",
    REPO_ROOT / "docs/api/classic-settings-core.md",
    REPO_ROOT / "docs/api/formid-settings-boundary.md",
]

ACTIVE_API_CORE_GROUP_B = [
    REPO_ROOT / "docs/api/classic-version-core.md",
    REPO_ROOT / "docs/api/classic-version-registry-core.md",
    REPO_ROOT / "docs/api/classic-config-core.md",
    REPO_ROOT / "docs/api/classic-config-core-yaml-schema.md",
    REPO_ROOT / "docs/api/classic-web-core.md",
    REPO_ROOT / "docs/api/classic-update-core.md",
]

ACTIVE_API_RUNTIME_GROUP_C = [
    REPO_ROOT / "docs/api/classic-path-core.md",
    REPO_ROOT / "docs/api/game-setup-workflow.md",
    REPO_ROOT / "docs/api/classic-file-io-core.md",
    REPO_ROOT / "docs/api/classic-resource-core.md",
    REPO_ROOT / "docs/api/classic-registry-core.md",
]

ACTIVE_API_RUNTIME_GROUP_D = [
    REPO_ROOT / "docs/api/classic-scangame-core.md",
    REPO_ROOT / "docs/api/classic-scanlog-core.md",
    REPO_ROOT / "docs/api/classic-database-core.md",
    REPO_ROOT / "docs/api/classic-cpp-bridge-data-entrypoints.md",
    REPO_ROOT / "docs/api/classic-cpp-bridge-game-entrypoints.md",
    REPO_ROOT / "docs/api/classic-cpp-bridge-scan-progress-callback.md",
    REPO_ROOT / "docs/api/classic-gui-scan-progress-consumer.md",
    REPO_ROOT / "docs/api/classic-gui-scan-result-ordering.md",
    REPO_ROOT / "docs/api/classic-xse-core.md",
]

ACTIVE_AGENT_ENTRYPOINTS = [
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / ".agents/skills/classic-project-guide/SKILL.md",
    REPO_ROOT / ".opencode/skills/classic-project-guide/SKILL.md",
    REPO_ROOT / ".claude/skills/classic-project-guide/SKILL.md",
    REPO_ROOT / ".agent/skills/classic-project-guide/SKILL.md",
]

ACTIVE_REPO_GUIDE_MIRRORS = [
    REPO_ROOT / ".agents/skills/classic-project-guide/references/repo-guide.md",
    REPO_ROOT / ".opencode/skills/classic-project-guide/references/repo-guide.md",
    REPO_ROOT / ".claude/skills/classic-project-guide/references/repo-guide.md",
    REPO_ROOT / ".agent/skills/classic-project-guide/references/repo-guide.md",
]

ACTIVE_CODEBASE_MAPS = [
    REPO_ROOT / ".planning/codebase/STRUCTURE.md",
    REPO_ROOT / ".planning/codebase/CONVENTIONS.md",
    REPO_ROOT / ".planning/codebase/TESTING.md",
    REPO_ROOT / ".planning/codebase/ARCHITECTURE.md",
    REPO_ROOT / ".planning/codebase/STACK.md",
]

SCOPED_SWEEP_SURFACES = [
    *ACTIVE_TOP_LEVEL_DOCS,
    *ACTIVE_API_HUB_DOCS,
    *ACTIVE_API_CORE_GROUP_A,
    *ACTIVE_API_CORE_GROUP_B,
    *ACTIVE_API_RUNTIME_GROUP_C,
    *ACTIVE_API_RUNTIME_GROUP_D,
    *ACTIVE_AGENT_ENTRYPOINTS,
    *ACTIVE_REPO_GUIDE_MIRRORS,
    *ACTIVE_CODEBASE_MAPS,
    REPO_ROOT / "rebuild_rust.ps1",
    REPO_ROOT / "rebuild_node.ps1",
    REPO_ROOT / "classic-cli/build_cli.ps1",
    REPO_ROOT / "classic-gui/build_gui.ps1",
    REPO_ROOT / "classic-cli/test_cli.ps1",
    REPO_ROOT / "tests/powershell/rebuild_rust.general_target.test.ps1",
    REPO_ROOT / "tests/powershell/phase10_guidance_tripwires.test.ps1",
]

EXCLUDED_PATH_PARTS = [
    ".planning/phases/",
    ".planning/milestones/",
    ".planning/quick/",
    "docs/implementation/",
    "docs/archive/",
]

FORBIDDEN_ACTIVE_PHRASES = [
    "ClassicLib-rs/Cargo.toml",
    "--manifest-path ClassicLib-rs/Cargo.toml",
    "ClassicLib-rs/python-bindings/.venv",
    "ClassicLib-rs/node-bindings/classic-node",
    "working-directory: ClassicLib-rs",
]

ALLOWED_HISTORICAL_LINE_PREFIXES = [
    "> Historical note:",
    "> Migration note:",
    "**Historical note:**",
    "**Migration note:**",
]

ALLOWED_SPECIAL_CASE_LINES: dict[Path, set[str]] = {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def contains_required_matrix_link(text: str) -> bool:
    return "workspace-migration-matrix.md" in text


def is_allowed_historical_line(path: Path, line: str) -> bool:
    stripped_line = line.strip()
    if any(
        stripped_line.startswith(prefix) for prefix in ALLOWED_HISTORICAL_LINE_PREFIXES
    ):
        return True

    return stripped_line in ALLOWED_SPECIAL_CASE_LINES.get(path, set())


class TestPhase10Validation(unittest.TestCase):
    maxDiff = None

    def assert_contract_for_paths(
        self,
        paths: list[Path],
        *,
        require_matrix_link: bool = False,
    ) -> None:
        for path in paths:
            with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                self.assertTrue(path.exists(), msg=f"Expected file to exist: {path}")
                text = read_text(path)
                if require_matrix_link:
                    self.assertTrue(
                        contains_required_matrix_link(text),
                        msg=(
                            "Expected active guidance surface to link to "
                            f"{MIGRATION_MATRIX.relative_to(REPO_ROOT)}: {path}"
                        ),
                    )

    def test_matrix_and_top_level_docs_contract(self) -> None:
        self.assertEqual(
            len(LINK_REQUIRED_SURFACES),
            len(set(LINK_REQUIRED_SURFACES)),
            msg="LINK_REQUIRED_SURFACES should not contain duplicates.",
        )
        self.assertEqual(
            len(ACTIVE_TOP_LEVEL_DOCS),
            len(set(ACTIVE_TOP_LEVEL_DOCS)),
            msg="ACTIVE_TOP_LEVEL_DOCS should not contain duplicates.",
        )
        self.assertEqual(
            MIGRATION_MATRIX,
            REPO_ROOT / "docs/workspace-migration-matrix.md",
        )
        self.assert_contract_for_paths(LINK_REQUIRED_SURFACES, require_matrix_link=True)
        self.assert_contract_for_paths(ACTIVE_TOP_LEVEL_DOCS, require_matrix_link=True)

    def test_api_hubs_and_binding_workflow_contract(self) -> None:
        self.assert_contract_for_paths(ACTIVE_API_HUB_DOCS, require_matrix_link=True)

    def test_api_core_group_a_contract(self) -> None:
        self.assert_contract_for_paths(ACTIVE_API_CORE_GROUP_A)

    def test_api_core_group_b_contract(self) -> None:
        self.assert_contract_for_paths(ACTIVE_API_CORE_GROUP_B)

    def test_api_runtime_group_c_contract(self) -> None:
        self.assert_contract_for_paths(ACTIVE_API_RUNTIME_GROUP_C)

    def test_api_runtime_group_d_contract(self) -> None:
        self.assert_contract_for_paths(ACTIVE_API_RUNTIME_GROUP_D)

    def test_agent_entrypoints_contract(self) -> None:
        self.assert_contract_for_paths(
            ACTIVE_AGENT_ENTRYPOINTS, require_matrix_link=True
        )

    def test_repo_guide_mirrors_contract(self) -> None:
        self.assert_contract_for_paths(ACTIVE_REPO_GUIDE_MIRRORS)

    def test_codebase_maps_contract(self) -> None:
        self.assert_contract_for_paths(ACTIVE_CODEBASE_MAPS)

    def test_scoped_active_guidance_sweep(self) -> None:
        failures: list[str] = []

        for path in SCOPED_SWEEP_SURFACES:
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            with self.subTest(path=relative_path):
                self.assertTrue(
                    path.exists(), msg=f"Expected sweep surface to exist: {path}"
                )
                self.assertFalse(
                    any(part in relative_path for part in EXCLUDED_PATH_PARTS),
                    msg=(
                        "Scoped sweep surface should not overlap excluded history/planning "
                        f"areas: {relative_path}"
                    ),
                )

                for line_number, line in enumerate(
                    read_text(path).splitlines(), start=1
                ):
                    for phrase in FORBIDDEN_ACTIVE_PHRASES:
                        if phrase not in line:
                            continue
                        if is_allowed_historical_line(path, line):
                            continue
                        failures.append(
                            f"{relative_path}:{line_number}: forbidden active guidance '{phrase}'"
                        )

        self.assertEqual(failures, [], msg="\n".join(failures))


if __name__ == "__main__":
    unittest.main()
