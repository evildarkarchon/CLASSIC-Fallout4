"""New free-function aliases must retain identity through real source loading."""

import copy
import json
from pathlib import Path

import pytest
from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.coverage import load_source_parity_rows
from conformance.packs import load_and_validate_pack

from receipt_test_support import copy_source_inventory

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "family",
    [
        "settings-load",
        "performance",
        "update-decisions",
        "xse-operations",
        "string-operations",
        "registry-operations",
        "game-identity",
        "runtime-access",
        "file-fingerprint",
    ],
)
@pytest.mark.parametrize("participant", ["node", "python"])
def test_source_loaded_alias_cannot_borrow_owner_receipt(
        tmp_path: Path, family: str, participant: str
) -> None:
    """A newly exported wrapper cannot inherit the aggregate Rust carrier's fact."""
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    ).document()
    owner = pack["domainOwner"]["rustCrate"]
    symbols = {
        symbol
        for capability in pack["capabilities"]
        for symbol in capability["rustSymbols"]
    }
    copy_source_inventory(ROOT, tmp_path)
    path = (
            tmp_path
            / f"docs/implementation/{participant}_api_parity/baseline/parity_contract.json"
    )
    contract = json.loads(path.read_text())
    candidates = [
        row
        for row in contract["tier1Mappings"]
        if row.get("rustCrate") == owner and row.get("rustSymbol") in symbols
    ]
    if not candidates:
        assert participant == "python" and family == "runtime-access"
        return
    alias = copy.deepcopy(candidates[0])
    alias["id"] = "future-owner-alias"
    alias["nodeKind" if participant == "node" else "pythonKind"] = "function"
    alias["nodeExport" if participant == "node" else "pythonExportPath"] = (
        "futureOwnerAlias" if participant == "node" else "future_owner_alias"
    )
    contract["tier1Mappings"].append(alias)
    path.write_text(json.dumps(contract))
    added = next(
        row
        for row in load_source_parity_rows(tmp_path)
        if row.obligation_id == f"parity:{participant}:future-owner-alias"
    )
    assert added.runtime_operation is not None
    assert not any(
        predicate.covers_runtime_operation(added.runtime_operation)
        for predicate in FAMILY_COVERAGE_POLICIES[family].predicates
    )
