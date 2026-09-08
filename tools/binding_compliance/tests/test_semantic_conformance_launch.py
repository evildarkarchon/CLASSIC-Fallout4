"""Invocation isolation and native preparation for focused semantic families."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from conformance.adapters.prepare_cxx_conformance import (
    SUPPORTED_FAMILIES,
    prepare_cxx_run,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_new_native_helpers_automatically_enter_source_identity() -> None:
    """Adding an included helper must not require a separate fingerprint list edit."""
    from conformance.adapters.prepare_cxx_conformance import _cxx_source_paths

    assert REPO_ROOT / "classic-cli/tests/conformance" in _cxx_source_paths(
        REPO_ROOT, "user-settings"
    )


@pytest.mark.parametrize("family", SUPPORTED_FAMILIES)
def test_native_semantic_family_plans_are_fresh_and_input_only(
    tmp_path: Path,
    family: str,
) -> None:
    """Both native compilers receive the same oracle identity and unique invocations."""

    artifact_root = (
        REPO_ROOT
        / "tools/binding_compliance/artifacts/test-semantic-launch"
        / tmp_path.name
    )
    plans = []
    try:
        for compiler in ("msvc", "clang-cl"):
            prepared = prepare_cxx_run(
                REPO_ROOT,
                compiler=compiler,
                family=family,
                artifact_root=artifact_root,
            )
            plan = prepared.document()
            plans.append(plan)
            assert plan["familyId"] == family
            assert plan["participant"]["executionInstanceId"] == f"windows-{compiler}"
            assert plan["scenarios"]
            assert all("expected" not in scenario for scenario in plan["scenarios"])
            assert not prepared.receipt_path.exists()
        assert plans[0]["expectationDigest"] == plans[1]["expectationDigest"]
        assert plans[0]["invocation"]["id"] != plans[1]["invocation"]["id"]
    finally:
        # Artifacts are invocation-owned children of the explicit test directory.
        if artifact_root.exists():
            assert artifact_root.resolve().is_relative_to(
                REPO_ROOT / "tools/binding_compliance/artifacts/test-semantic-launch"
            )
            shutil.rmtree(artifact_root)
