"""Tests for the binding compliance requirement catalog."""

from __future__ import annotations

from catalog import REQUIREMENTS, requirements_for_profile


def test_catalog_maps_policy_to_all_required_surfaces() -> None:
    expected_surfaces = {
        "cxx",
        "node",
        "python",
        "shared_rust_api_inventory",
        "generated_artifacts",
        "runtime_coverage",
        "stubs_declarations",
        "docs",
        "policy",
    }
    assert expected_surfaces <= {requirement.surface for requirement in REQUIREMENTS}


def test_catalog_requires_receipt_coverage_instead_of_a_registry_gap() -> None:
    """CXX has executable receipts; an absent registry is no longer a gap."""
    classifications = {requirement.classification for requirement in REQUIREMENTS}
    assert {
               "existing_gate",
               "new_check",
           } <= classifications
    requirements = {requirement.id: requirement for requirement in REQUIREMENTS}
    assert "cxx-runtime-coverage-gap" not in requirements
    assert requirements["repository-receipt-coverage"].blocking


def test_ci_profile_reuses_lower_level_binding_gates() -> None:
    command_ids = {
        requirement.id
        for requirement in requirements_for_profile("ci")
        if requirement.command is not None
    }
    assert {
               "cxx-parity-gate",
               "node-parity-gate",
               "python-parity-gate",
               "python-stub-validation",
           } <= command_ids


def test_full_profile_includes_runtime_backstops() -> None:
    command_ids = {
        requirement.id
        for requirement in requirements_for_profile("full")
        if requirement.command is not None
    }
    assert {
               "node-dts-freshness",
               "node-bun-runtime-tests",
               "node-node-runtime-tests",
               "python-bindings-rebuild",
               "python-runtime-smoke-tests",
           } <= command_ids


def test_static_profiles_block_on_scan_run_source_contract() -> None:
    """The shared scan-run manifest is mandatory for every source-level profile."""

    requirements = {requirement.id: requirement for requirement in REQUIREMENTS}
    requirement = requirements["scan-run-contract-variants"]

    assert requirement.blocking is True
    assert requirement.profiles == (
        "static",
        "ci",
        "full",
        "cxx-ci",
        "node-ci",
        "python-ci",
    )
    assert requirement.command is not None
    assert requirement.command.argv == (
        "python",
        "tools/binding_compliance/scan_run_contract.py",
        "--repo-root",
        ".",
    )


def test_static_profiles_block_on_promoted_scan_run_workflow_policy() -> None:
    """Deleting or weakening any receipt job must fail source-level CI."""

    requirements = {requirement.id: requirement for requirement in REQUIREMENTS}
    requirement = requirements["scan-run-workflow-policy"]

    assert requirement.blocking is True
    assert requirement.profiles == (
        "static",
        "ci",
        "full",
        "cxx-ci",
        "node-ci",
        "python-ci",
    )
    assert requirement.command is not None
    assert requirement.command.argv == (
        "python",
        "tools/binding_compliance/scan_run_workflow_policy.py",
        "--repo-root",
        ".",
    )
