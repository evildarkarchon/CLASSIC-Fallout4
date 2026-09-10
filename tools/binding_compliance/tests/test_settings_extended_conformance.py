"""Remaining settings operations must have explicit public evidence."""

import importlib


def test_cached_document_receipts_retain_replacement_file_bytes():
    """Cached reads must not conceal stale-source writeback or unexpected files."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    pack = json.loads(
        (root / "tests/conformance/packs/settings_cached_docs/v1.json").read_text()
    )
    for case in pack["scenarios"]:
        assert case["expected"]["files"] == {"input.yaml": "changed: true\n"}


def test_remaining_settings_family_predicates_are_narrow():
    """Validation and cached-document evidence cannot substitute for each other."""
    module = importlib.import_module("conformance.families.settings_extended")
    for family in ("settings-validation", "settings-cached-docs"):
        policy = module.settings_extended_coverage_policy(family)
        assert policy.predicates
        assert all(not p.matches({}) for p in policy.predicates)


def test_extended_settings_packs_reject_missing_facts_and_input_oracles():
    """Input-only packs provide exact facts for every public operation."""
    import copy
    import json
    from pathlib import Path

    import pytest

    module = importlib.import_module("conformance.families.settings_extended")
    root = Path(__file__).resolve().parents[3]
    for family in ("settings-validation", "settings-cached-docs"):
        pack = json.loads(
            (
                root / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
            ).read_text()
        )
        assert len(module.validate_settings_extended_pack(pack, root)) == len(
            pack["scenarios"]
        )
        for case in pack["scenarios"]:
            for predicate in module.settings_extended_coverage_policy(
                family
            ).predicates:
                assert predicate.matches(case["expected"])
                for key in case["expected"]:
                    incomplete = {k: v for k, v in case["expected"].items() if k != key}
                    assert not predicate.matches(incomplete)
        changed = copy.deepcopy(pack)
        changed["scenarios"][0]["input"]["expected"] = {}
        with pytest.raises(ValueError):
            module.validate_settings_extended_pack(changed, root)
