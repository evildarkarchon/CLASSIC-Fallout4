"""Timer lifecycle proof requires native elapsed time and exactly one recorded sample."""

import copy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_timer_facts_reject_frozen_clocks_duplicate_samples_and_missing_cleanup():
    """No timer operation earns a fact if any measured lifecycle invariant fails."""
    from conformance.families.performance_timers import (
        PERFORMANCE_TIMERS_COVERAGE_POLICY,
    )

    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/performance_timers/v1.json")
    ).document()
    scenario = document["scenarios"][0]
    observation = scenario["expected"]
    assert derive_observed_fact_ids(
        document, scenario, observation, PERFORMANCE_TIMERS_COVERAGE_POLICY
    )
    for index in range(2):
        for key in ("advanced", "positive", "singleSample", "summaryConsistent"):
            altered = copy.deepcopy(observation)
            altered["timers"][index][key] = False
            assert not derive_observed_fact_ids(
                document, scenario, altered, PERFORMANCE_TIMERS_COVERAGE_POLICY
            )
    altered = copy.deepcopy(observation)
    altered["cleared"] = False
    assert not derive_observed_fact_ids(
        document, scenario, altered, PERFORMANCE_TIMERS_COVERAGE_POLICY
    )
