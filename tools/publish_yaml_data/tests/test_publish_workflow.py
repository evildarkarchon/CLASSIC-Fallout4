"""Regression tests for the YAML-data publish workflow contract."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "publish-yaml-data.yml"


def test_release_is_discoverable_before_pages_pointer_can_publish() -> None:
    """Pin the client-discovery ordering around the gh-pages pointer push."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assets_reachable = workflow.index("- name: Verify assets reachable anonymously")
    clear_prerelease = workflow.index(
        "- name: Clear prerelease flag (make client-discoverable)"
    )
    deploy_pages = workflow.index("- name: Deploy manifest to gh-pages")

    assert assets_reachable < clear_prerelease < deploy_pages


def test_pages_smoke_test_uses_strict_body_comparison() -> None:
    """Pin strict-body Pages smoke test for same-tag republish safety."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    smoke_step = workflow.index("- name: Smoke-test Pages manifest")
    smoke_block = workflow[smoke_step : smoke_step + 600]

    assert "--expected-body-path" in smoke_block
    assert "$RUNNER_TEMP/staging/manifest.json" in smoke_block
    assert "--tag" not in smoke_block
