"""Core-only inventory cannot invent a Python exception or bypass Rust existence."""

import generate_baseline as gb
import pytest


@pytest.mark.parametrize(
    "changes,exists,status",
    [
        ({}, True, "matched"),
        ({}, False, "missing_rust"),
        ({"pythonModule": "classic_scanlog"}, True, "signature_mismatch"),
        ({"pythonExportPath": "PapyrusError"}, True, "signature_mismatch"),
        ({"pythonExport": "PapyrusError"}, True, "signature_mismatch"),
        ({"rustKind": "struct"}, True, "signature_mismatch"),
        ({"rustCrate": "classic-config-core"}, True, "missing_rust"),
    ],
)
def test_explicit_rust_only_rows_validate_owner_and_forbid_python_claims(
        changes, exists, status
):
    """A retained Rust enum has no Python callable/declaration contract."""
    row = {
        "id": "papyrus-error",
        "tier": "tier1",
        "ownerModule": "scanlog",
        "rustSymbol": "PapyrusError",
        "rustCrate": "classic-scanlog-core",
        "rustKind": "enum",
        "pythonKind": "rust_only",
        **changes,
    }
    symbols = (
        [{"symbol": "PapyrusError", "crate": "classic-scanlog-core", "kind": "enum"}]
        if exists
        else []
    )
    report = gb.generate_diff_report(
        {"tier1Mappings": [row]}, {"symbols": symbols}, {"exports": []}
    )
    assert report["contract_results"][0]["status"] == status
