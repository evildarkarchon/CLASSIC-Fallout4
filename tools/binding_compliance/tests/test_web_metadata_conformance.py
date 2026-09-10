"""User-agent and mod-site facts must be authored and credited narrowly."""

import json
from pathlib import Path

from conformance.families.aux_operations import aux_operations_coverage_policy

ROOT = Path(__file__).resolve().parents[3]


def test_web_metadata_covers_public_helpers_without_game_url_credit():
    """All common site and user-agent helpers execute, without Python game URL claims."""
    pack = json.loads(
        (ROOT / "tests/conformance/packs/web_operations/v1.json").read_text()
    )
    symbols = {
        symbol
        for p in aux_operations_coverage_policy("web-operations").predicates
        for symbol in p.rust_symbols
    }
    assert {"get_user_agent", "get_user_agent_with_suffix", "ModSite"} <= symbols
    for case in pack["scenarios"]:
        if case["action"] != "web-operations.observe":
            continue
        assert case["expected"]["userAgent"] == "CLASSIC/8.0.0"
        assert len(case["expected"]["sites"]) == 3
    site = next(
        p
        for p in aux_operations_coverage_policy("web-operations").predicates
        if "ModSite" in p.rust_symbols
    )
    assert not site.covers_runtime_operation("game_url")
    assert site.covers_runtime_operation("__eq__")


def test_web_suffix_cases_include_empty_and_unicode():
    """Suffix bytes, including empty text and Unicode, remain observable."""
    pack = json.loads(
        (ROOT / "tests/conformance/packs/web_operations/v1.json").read_text()
    )
    suffixes = []
    for case in pack["scenarios"]:
        if case["action"] != "web-operations.observe":
            continue
        request = json.loads(
            (ROOT / pack["fixtureRoot"] / pack["fixtures"][case["id"]]).read_text()
        )["request"]
        suffixes.append(request["suffix"])
        assert (
            case["expected"]["userAgentWithSuffix"]
            == "CLASSIC/8.0.0 (" + request["suffix"] + ")"
        )
    assert "" in suffixes
    assert "conformance / 雪" in suffixes
