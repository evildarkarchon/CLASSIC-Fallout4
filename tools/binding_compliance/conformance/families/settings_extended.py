"""Input-only settings validators and cached document conformance."""

import json
from collections.abc import Mapping
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observation(family, value):
    """Require exact domain fields and distinct absent versus empty documents."""
    if not isinstance(value, Mapping):
        return False
    if family == "settings-validation":
        return (
            set(value) == {"results"}
            and isinstance(value["results"], list)
            and bool(value["results"])
            and all(
                isinstance(item, Mapping)
                and set(item) == {"valid", "value", "error"}
                and type(item["valid"]) is bool
                and (
                    (
                        item["error"] is None
                        and (
                            isinstance(item["value"], (str, int, bool))
                            or isinstance(item["value"], Mapping)
                            and set(item["value"]) == {"float"}
                            and isinstance(item["value"]["float"], str)
                        )
                    )
                    or (
                        item["value"] is None
                        and isinstance(item["error"], str)
                        and bool(item["error"])
                    )
                )
                for item in value["results"]
            )
        )
    return (
        set(value)
        == {"before", "cached", "afterFileChange", "afterInvalidate", "files"}
        and value["before"] is None
        and isinstance(value["cached"], list)
        and isinstance(value["afterFileChange"], list)
        and value["afterInvalidate"] is None
        and isinstance(value["files"], Mapping)
        and set(value["files"]) == {"input.yaml"}
        and isinstance(value["files"]["input.yaml"], str)
    )


def validate_settings_extended_pack(document, root):
    """Reject input oracles and malformed requests before calling native adapters."""
    family = document["familyId"]
    if family not in {"settings-validation", "settings-cached-docs"}:
        raise ValueError("unknown settings extended family")
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for scenario in document["scenarios"]:
        reference = scenario["input"].get("fixtureRef")
        if (
            scenario["action"] != family + ".observe"
            or scenario["input"] != {"fixtureRef": reference}
            or scenario["fixtureRefs"] != [reference]
        ):
            raise ValueError("settings scenario must declare only its fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("settings fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if family == "settings-validation":
            if (
                set(fixture) != {"cases"}
                or not isinstance(fixture["cases"], list)
                or not fixture["cases"]
                or not all(
                    isinstance(item, Mapping)
                    and set(item) == {"value", "type"}
                    and isinstance(item["value"], str)
                    and item["type"] in {"int", "float", "bool", "path", "string"}
                    for item in fixture["cases"]
                )
            ):
                raise ValueError("invalid setting validator inputs")
            if len(scenario["expected"].get("results", [])) != len(fixture["cases"]):
                raise ValueError("validator observations must account for every input")
        elif set(fixture) != {"content", "replacement"} or not all(
            isinstance(v, str) for v in fixture.values()
        ):
            raise ValueError("cached documents require authored YAML strings")
        if not _observation(family, scenario["expected"]):
            raise ValueError("malformed settings observation")
        paths.append(path)
    return tuple(paths)


def settings_extended_coverage_policy(family):
    """Credit only explicitly invoked validator or cache retrieval operations."""
    operations = (
        (
            ("validate_setting_value", "settings_validate_value"),
            ("coerce_setting_value", "settings_coerce_value"),
        )
        if family == "settings-validation"
        else (("get_cached", "getCached"),)
    )
    return FamilyCoveragePolicy(
        family,
        tuple(
            CoveragePredicate(
                id=symbol.replace("_", "-"),
                capability_id=family + ".observe",
                action=family + ".observe",
                observation_family="values-and-errors"
                if family == "settings-validation"
                else "cached-documents",
                rust_symbols=(symbol,),
                matches=partial(_observation, family),
                runtime_operations=(None, symbol, alias),
            )
            for symbol, alias in operations
        ),
    )
