"""File/text similarity must retain independently authored numeric results."""

import copy
import json
from pathlib import Path

from conformance.families.file_operations import FILE_OPERATIONS_COVERAGE_POLICY


def test_similarity_results_are_required_and_cannot_be_replaced_by_identity_only():
    """The partial match catches implementations that return only equal/not-equal."""
    root = Path(__file__).resolve().parents[3]
    pack = json.loads(
        (root / "tests/conformance/packs/file_operations/v1.json").read_text()
    )
    expected = next(
        s["expected"]
        for s in pack["scenarios"]
        if s["action"] == "file-operations.read-text"
    )
    assert expected["similarity"] == ["1.000000", "0.000000", "0.500000"]
    predicates = [
        p
        for p in FILE_OPERATIONS_COVERAGE_POLICY.predicates
        if "calculate_similarity" in p.rust_symbols
    ]
    assert any(p.matches(expected) for p in predicates)
    changed = copy.deepcopy(expected)
    changed["similarity"][-1] = 0.0
    assert not any(p.matches(changed) for p in predicates)
