"""Native logging proof preserves emitted severity, contents, and absence of extra records."""

import copy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_logging_facts_reject_missing_duplicate_wrong_level_and_wrong_content_records():
    """Logger return success cannot replace the exact emitted record stream."""
    from conformance.families.message_logging import MESSAGE_LOGGING_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/message_logging/v1.json")
    ).document()
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            document, scenario, expected, MESSAGE_LOGGING_COVERAGE_POLICY
        )
        changed = copy.deepcopy(expected)
        changed["records"].append({"level": "INFO", "message": "unexpected"})
        assert not derive_observed_fact_ids(
            document, scenario, changed, MESSAGE_LOGGING_COVERAGE_POLICY
        )
        for index, record in enumerate(expected["records"]):
            for field in ("level", "message"):
                changed = copy.deepcopy(expected)
                changed["records"][index][field] = "wrong"
                assert not derive_observed_fact_ids(
                    document, scenario, changed, MESSAGE_LOGGING_COVERAGE_POLICY
                )
            changed = copy.deepcopy(expected)
            changed["records"].pop(index)
            assert not derive_observed_fact_ids(
                document, scenario, changed, MESSAGE_LOGGING_COVERAGE_POLICY
            )
