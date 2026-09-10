"""Exact public registry Keys carrier observations."""

import json
from collections.abc import Mapping

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

NAMES = (
    "YAML_CACHE",
    "MANUAL_DOCS_GUI",
    "GAME_PATH_GUI",
    "GAME_PATH",
    "DOCS_PATH",
    "IS_GUI_MODE",
    "OPEN_FILE_FUNC",
    "GAME",
    "GAME_VERSION",
    "VERSION_AUTO_DETECTED",
    "LOCAL_DIR",
    "IS_PRERELEASE",
    "XSE_VALID",
    "XSE_VERSION",
    "ENB_PRESENT",
    "GAME_VERSION_DETECTED",
)


def _observed(value):
    """Require every common public key without granting unnamed constants credit."""
    return (
        isinstance(value, Mapping)
        and set(value) == {"keys"}
        and isinstance(value["keys"], Mapping)
        and set(value["keys"]) == set(NAMES)
        and all(isinstance(v, str) and bool(v) for v in value["keys"].values())
    )


def validate_registry_keys_pack(document, root):
    """Reject inputs containing result values before reading public constants."""
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != "registry-keys.observe"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("registry keys must declare only their fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if (
            not path.is_relative_to(fixture_root)
            or json.loads(path.read_text()) != {"request": {}}
            or not _observed(case["expected"])
        ):
            raise ValueError("invalid registry keys input or observation")
        paths.append(path)
    return tuple(paths)


REGISTRY_KEYS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "registry-keys",
    (
        CoveragePredicate(
            id="registry-keys-public-constants",
            capability_id="registry-keys.observe",
            action="registry-keys.observe",
            observation_family="key-values",
            rust_symbols=("Keys",),
            runtime_operations=(None,),
            matches=_observed,
        ),
    ),
)
