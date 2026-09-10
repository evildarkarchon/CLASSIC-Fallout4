"""Bridge-owned presentation helpers use actual CXX and private Rust reference execution."""

import copy
from pathlib import Path

from conformance.applicability import derive_applicability
from conformance.coverage import derive_observed_fact_ids, load_source_parity_rows
from conformance.packs import load_and_validate_pack


def test_interface_helpers_have_no_fabricated_core_owner_or_extra_adapter():
    """Exact binding selectors enroll only the actual CXX surface and its Rust reference."""
    from conformance.families.interface_helpers import interface_coverage_policy

    root = Path(__file__).resolve().parents[3]
    for family in ("markdown-rendering", "report-discovery"):
        document = load_and_validate_pack(
            root, Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
        ).document()
        assert document["domainOwner"]["rustCrate"] == "classic-cpp-bridge"
        assert {
            p.id
            for p in derive_applicability(
                document, load_source_parity_rows(root)
            ).participants
        } == {"rust", "cxx"}
        policy = interface_coverage_policy(family)
        for scenario in document["scenarios"]:
            assert derive_observed_fact_ids(
                document, scenario, scenario["expected"], policy
            )
            for key in scenario["expected"]:
                changed = copy.deepcopy(scenario["expected"])
                del changed[key]
                assert not derive_observed_fact_ids(document, scenario, changed, policy)
