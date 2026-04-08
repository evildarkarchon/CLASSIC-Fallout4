"""D-05 unit test for validate_contract_rust_symbols (Pitfall 2 guard)."""
from __future__ import annotations

# sys.path bootstrap handled by conftest.py
from check_parity_gate import validate_contract_rust_symbols  # noqa: E402


def test_validate_passes_when_all_symbols_present() -> None:
    contract = {
        "tier1Mappings": [
            {
                "id": "test.foo",
                "rustSymbol": "FooStruct",
                "rustCrate": "classic-test-core",
            }
        ]
    }
    rust_manifest = {"symbols": [{"symbol": "FooStruct"}]}
    diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
    assert diagnostics == []


def test_validate_fails_when_symbol_missing() -> None:
    contract = {
        "tier1Mappings": [
            {
                "id": "test.foo",
                "rustSymbol": "MissingStruct",
                "rustCrate": "classic-test-core",
            }
        ]
    }
    rust_manifest = {"symbols": [{"symbol": "OtherStruct"}]}
    diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
    assert len(diagnostics) == 1
    assert "Pitfall 2" in diagnostics[0]
    assert "test.foo" in diagnostics[0]
    assert "MissingStruct" in diagnostics[0]
    assert "classic-test-core" in diagnostics[0]


def test_validate_fails_when_rustSymbol_field_missing() -> None:
    contract = {
        "tier1Mappings": [
            {"id": "test.bar", "rustCrate": "classic-test-core"}
        ]
    }
    rust_manifest = {"symbols": []}
    diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
    assert len(diagnostics) == 1
    assert "missing 'rustSymbol'" in diagnostics[0]
