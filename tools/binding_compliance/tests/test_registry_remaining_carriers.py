"""Remaining registry carriers require their actual public construction paths."""

from pathlib import Path

from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.coverage import load_source_parity_rows
from conformance.packs import load_and_validate_pack
from retirement_readiness import candidate_predicates


def test_observed_registry_carriers_and_singleton_have_precise_predicates():
    """No remaining live carrier or confidence alias can rely on mapped-only metadata."""
    root = Path(__file__).resolve().parents[3]
    rows = load_source_parity_rows(root)
    for family, obligations in {
        "version-registry": (
            "parity:python:version_registry.models.CrashgenConfig",
            "parity:python:version-registry-get-singleton",
            "parity:python:version-registry-match-confidence-class",
            "parity:python:version_registry.matching.MatchConfidence.__eq__",
            "parity:python:version_registry.matching.MatchConfidence.__hash__",
            "parity:python:version_registry.matching.MatchConfidence.is_high_confidence",
        ),
        "version-registry-details": (
            "parity:python:version_registry.models.AddressLibraryConfig",
        ),
    }.items():
        pack = load_and_validate_pack(
            root, Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
        ).document()
        for obligation in obligations:
            row = next(row for row in rows if row.obligation_id == obligation)
            assert candidate_predicates(row, pack, FAMILY_COVERAGE_POLICIES[family]), (
                obligation
            )
