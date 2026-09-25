"""Elapsed-time invariants and exactly-once timer recording from actual native calls."""

import json

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _timers(value):
    """Require both construction paths, measured clock progress, and complete cleanup."""
    return (
        value
        == {
            "timers": [
                {
                    "constructor": constructor,
                    "advanced": True,
                    "positive": True,
                    "singleSample": True,
                    "summaryConsistent": True,
                }
                for constructor in ("direct", "factory")
            ],
            "cleared": True,
        }
        and all(
            type(timer[key]) is bool
            for timer in value["timers"]
            for key in ("advanced", "positive", "singleSample", "summaryConsistent")
        )
        and type(value["cleared"]) is bool
    )


PERFORMANCE_TIMERS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "performance-timers",
    (
        CoveragePredicate(
            id="performance-timers.lifecycle",
            capability_id="performance-timers.observe",
            action="performance-timers.observe",
            observation_family="timer-lifecycle",
            rust_symbols=("Timer", "start_timer"),
            runtime_operations=(None, "__init__", "start_timer", "elapsed", "finish"),
            matches=_timers,
        ),
    ),
)


def validate_performance_timers_pack(document, root):
    """Accept only the bounded two-constructor fixture and exact lifecycle oracle."""
    paths = []
    for scenario in document["scenarios"]:
        reference = scenario["input"].get("fixtureRef")
        if (
            scenario["action"] != "performance-timers.observe"
            or scenario["input"] != {"fixtureRef": reference}
            or scenario["fixtureRefs"] != [reference]
            or not _timers(scenario["expected"])
        ):
            raise ValueError("invalid timer lifecycle scenario")
        path = (
            root / document["fixtureRoot"] / document["fixtures"][reference]
        ).resolve()
        if not path.is_relative_to((root / document["fixtureRoot"]).resolve()):
            raise ValueError("timer fixture escapes root")
        if json.loads(path.read_text(encoding="utf-8")) != {
            "constructors": ["direct", "factory"]
        }:
            raise ValueError(
                "timer fixture must exercise direct and factory construction"
            )
        paths.append(path)
    return tuple(paths)
