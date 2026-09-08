"""Public registry Keys evidence includes every shared constant."""

import copy
import json
from pathlib import Path

from conformance.families.registry_keys import (
    REGISTRY_KEYS_COVERAGE_POLICY,
    validate_registry_keys_pack,
)


def test_registry_keys_require_all_public_constant_observations():
    """Deleting any constant removes Keys carrier evidence."""
    root = Path(__file__).resolve().parents[3]
    pack = json.loads(
        (root / "tests/conformance/packs/registry_keys/v1.json").read_text()
    )
    assert len(validate_registry_keys_pack(pack, root)) == 1
    observed = pack["scenarios"][0]["expected"]
    predicate = REGISTRY_KEYS_COVERAGE_POLICY.predicates[0]
    assert predicate.matches(observed)
    assert len(observed["keys"]) == 16
    for key in observed["keys"]:
        partial = copy.deepcopy(observed)
        del partial["keys"][key]
        assert not predicate.matches(partial)
    assert not predicate.covers_runtime_operation("future_unobserved_constant")
