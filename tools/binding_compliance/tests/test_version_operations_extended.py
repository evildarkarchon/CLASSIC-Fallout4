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


def test_moved_version_rows_name_shared_core_and_keep_operation_identity():
    """Loose and PE helper rows name their shared-core owner without re-keying.

    The helpers moved from classic-version-core to classic-shared-core (#243).
    Every binding row must name the actual owner while keeping the exported
    operation identity it had, so runtime evidence cannot be borrowed by a
    different export; the known-version queries stay with their policy owner.
    """
    from conformance.coverage import load_source_parity_rows

    rows = {row.obligation_id: row for row in load_source_parity_rows(ROOT)}
    moved = {
        "parity:cxx:b2ef7e82ec676f1a": "extract_pe_version_string",
        "parity:node:version-pe-extract": "extract_pe_version",
        "parity:node:version-pe-is-valid-path": "is_valid_pe_path",
        "parity:node:version-registry-promote-parse-version": "parse_version",
        "parity:python:version.lib.is_valid_pe_path": "is_valid_pe_path",
        "parity:python:version.lib.extract_pe_version": "extract_pe_version",
        "parity:python:version.lib.compare_versions": "compare_versions",
    }
    for obligation, operation in moved.items():
        row = rows[obligation]
        assert row.rust_crate == "classic-shared-core", obligation
        assert row.runtime_operation == operation, obligation
    for obligation in (
            "parity:node:version-registry-promote-is-known-fallout4-version",
            "parity:python:version.lib.is_known_fallout4_version",
            "parity:python:version.lib.is_known_f4se_version",
    ):
        assert rows[obligation].rust_crate == "classic-version-core", obligation
    # xse no longer re-exports the loose helpers, so no row may claim it does.
    assert not [
        key
        for key, row in rows.items()
        if row.rust_crate == "classic-xse-core"
        and (row.rust_symbol or "").removesuffix("@rust")
        in {"parse_version", "try_parse_version", "compare_versions"}
    ]


def test_version_rows_keep_predicate_candidates_across_owners():
    """Every version row still finds an executable predicate after the owner split.

    version-extraction exercises both the shared-core extract helpers and the
    known-version query owned by classic-version-core. Coverage binds one
    crate per capability, so each owner needs its own capability or its rows
    silently lose their runtime credit (#243).
    """
    from conformance.coverage import load_source_parity_rows
    from retirement_readiness import candidate_predicates

    rows = {row.obligation_id: row for row in load_source_parity_rows(ROOT)}
    expected = {
        "version-extraction": (
            "parity:node:version-registry-promote-extract-version-from-filename",
            "parity:node:version-registry-promote-is-known-fallout4-version",
            "parity:python:version.lib.extract_all_versions",
            "parity:python:version.lib.is_known_fallout4_version",
        ),
        "version-f4se": ("parity:python:version.lib.is_known_f4se_version",),
        "version-pe": (
            "parity:cxx:b2ef7e82ec676f1a",
            "parity:node:version-pe-extract",
            "parity:python:version.lib.extract_pe_version",
        ),
        "version-pe-path": (
            "parity:node:version-pe-is-valid-path",
            "parity:python:version.lib.is_valid_pe_path",
        ),
    }
    for family, obligations in expected.items():
        pack = json.loads(
            (
                    ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
            ).read_text()
        )
        policy = aux_operations_coverage_policy(family)
        for obligation in obligations:
            assert candidate_predicates(rows[obligation], pack, policy), obligation
