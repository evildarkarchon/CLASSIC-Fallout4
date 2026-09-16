"""Version conformance credits only operations exercised by input-only scenarios."""

import json
from pathlib import Path

from conformance.families.aux_operations import (
    aux_operations_coverage_policy,
    validate_aux_operations_pack,
)

ROOT = Path(__file__).resolve().parents[3]


def test_remaining_version_operations_have_executable_evidence():
    """Every remaining bound version operation has complete, narrow observations."""
    symbols = set()
    for family in (
            "version-extraction",
            "version-f4se",
            "version-pe",
            "version-pe-path",
    ):
        pack = json.loads(
            (
                    ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
            ).read_text()
        )
        validate_aux_operations_pack(pack, ROOT)
        policy = aux_operations_coverage_policy(family)
        symbols.update(
            symbol
            for predicate in policy.predicates
            for symbol in predicate.rust_symbols
        )
        for predicate in policy.predicates:
            assert any(
                predicate.matches(case["expected"]) for case in pack["scenarios"]
            )
            assert not predicate.matches({})
    assert {
               "extract_version_from_filename",
               "extract_version_from_log",
               "extract_all_versions",
               "is_known_fallout4_version",
               "is_known_f4se_version",
               "extract_pe_version",
               "is_valid_executable_path",
           } <= symbols


def test_extended_version_observations_do_not_credit_comparison_or_other_operations():
    """Complete but unrelated observations never satisfy another public operation."""
    comparison = aux_operations_coverage_policy("version-operations")
    for family in (
            "version-extraction",
            "version-f4se",
            "version-pe",
            "version-pe-path",
    ):
        pack = json.loads(
            (
                    ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
            ).read_text()
        )
        for case in pack["scenarios"]:
            assert all(not p.matches(case["expected"]) for p in comparison.predicates)
            for key in case["expected"]:
                partial = {k: v for k, v in case["expected"].items() if k != key}
                assert all(
                    not p.matches(partial)
                    for p in aux_operations_coverage_policy(family).predicates
                )


def test_extended_packs_pass_public_loader():
    """Public pack validation enforces canonical actions and transport-safe values."""
    from conformance.packs import load_and_validate_pack

    for family in (
            "version_extraction",
            "version_f4se",
            "version_pe",
            "version_pe_path",
            "settings_validation",
            "settings_cached_docs",
            "registry_keys",
    ):
        load_and_validate_pack(
            ROOT, Path("tests/conformance/packs") / family / "v1.json"
        )
