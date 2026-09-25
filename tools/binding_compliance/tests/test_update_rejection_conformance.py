"""Default update entry points prove only deterministic rejection before transport."""

from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_rejection_facts_never_accept_success_or_transport_failure():
    """A failed network request cannot masquerade as pre-network input rejection."""
    from conformance.families.update_rejection import UPDATE_REJECTION_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/update_rejection/v1.json")
    ).document()
    for scenario in document["scenarios"]:
        assert derive_observed_fact_ids(
            document, scenario, scenario["expected"], UPDATE_REJECTION_COVERAGE_POLICY
        )
        for altered in (
                {"error": None},
                {"boundary": "transport", "error": "timeout"},
                {**scenario["expected"], "requestBuilt": True},
        ):
            assert not derive_observed_fact_ids(
                document, scenario, altered, UPDATE_REJECTION_COVERAGE_POLICY
            )
