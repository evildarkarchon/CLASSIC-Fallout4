from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RETIRED_CONSTANTS_PY_DIR = (
    REPO_ROOT / "ClassicLib-rs/python-bindings/classic-constants-py"
)
VERSION_REGISTRY_DOC = REPO_ROOT / "docs/api/classic-version-registry-core.md"
PYTHON_API_SURFACE = (
    REPO_ROOT / "docs/implementation/python_api_parity/baseline/python_api_surface.json"
)
NODE_RUST_API_SURFACE = (
    REPO_ROOT / "docs/implementation/node_api_parity/baseline/rust_api_surface.json"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class Phase03ValidationAuditTests(unittest.TestCase):
    def test_retired_classic_constants_py_directory_is_fully_removed(self) -> None:
        self.assertFalse(
            RETIRED_CONSTANTS_PY_DIR.exists(),
            "retired classic-constants-py directory should be fully removed",
        )

    def test_active_docs_do_not_reference_retired_constants_bindings(self) -> None:
        text = read_text(VERSION_REGISTRY_DOC)

        for retired_reference in ["classic-constants-py", "classic_constants"]:
            with self.subTest(retired_reference=retired_reference):
                self.assertNotIn(retired_reference, text)

    def test_committed_parity_surface_artifacts_are_refreshed(self) -> None:
        python_surface = json.loads(read_text(PYTHON_API_SURFACE))
        node_surface = json.loads(read_text(NODE_RUST_API_SURFACE))

        self.assertNotEqual(
            python_surface.get("generated_at_utc"),
            "2026-04-10T10:03:01.246199+00:00",
            "python parity surface should be regenerated after Phase 03",
        )
        self.assertNotEqual(
            node_surface.get("generated_at_utc"),
            "2026-04-10T10:03:05.136620+00:00",
            "node parity surface should be regenerated after Phase 03",
        )

        python_text = read_text(PYTHON_API_SURFACE)
        for retired_reference in [
            "classic_constants",
            "classic-constants-py",
            "classic_yaml",
            "classic-yaml-py",
        ]:
            with self.subTest(surface="python", retired_reference=retired_reference):
                self.assertNotIn(retired_reference, python_text)

        node_text = read_text(NODE_RUST_API_SURFACE)
        for retired_reference in [
            '"classic-constants-core"',
            '"classic-yaml-core"',
            '"classic-crashgen-settings-core"',
            '"constants"',
            '"crashgen_settings"',
        ]:
            with self.subTest(surface="node", retired_reference=retired_reference):
                self.assertNotIn(retired_reference, node_text)


if __name__ == "__main__":
    unittest.main()
