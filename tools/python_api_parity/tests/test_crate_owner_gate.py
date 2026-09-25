"""Python parity must identify a Rust symbol in its declared source crate."""

from __future__ import annotations

import check_parity_gate as gate
import generate_baseline as baseline
from resolve_python_rust_symbols import Resolution


def test_same_named_symbol_in_wrong_crate_cannot_satisfy_mapping() -> None:
    """A namesake from another crate cannot certify a stale Python row."""
    contract = {
        "tier1Mappings": [
            {
                "id": "stable-python-row",
                "tier": "tier1",
                "ownerModule": "file_io",
                "rustCrate": "classic-right-core",
                "rustSymbol": "SharedName",
                "pythonModule": "classic_file_io",
                "pythonExportPath": "SharedName",
                "pythonKind": "class",
            }
        ]
    }
    rust_manifest = {
        "symbols": [
            {"crate": "classic-other-core", "symbol": "SharedName", "kind": "struct"}
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "classic_file_io",
                "export": "SharedName",
                "kind": "class",
            }
        ]
    }

    diagnostics = gate.validate_contract_rust_symbols(contract, rust_manifest)
    report = baseline.generate_diff_report(contract, rust_manifest, python_manifest)

    assert any(
        "stable-python-row" in message and "classic-right-core" in message
        for message in diagnostics
    )
    assert report["contract_results"][0]["status"] == "missing_rust"
    assert report["contract_results"][0]["id"] == "stable-python-row"
    assert report["contract_results"][0]["rust_crate"] == "classic-right-core"


def test_rust_inventory_module_keeps_its_stable_proxy_row() -> None:
    """A source-only @rust row can name a module in its actual crate."""
    contract = {
        "tier1Mappings": [
            {
                "id": "file_io.encoding.encoding@rust",
                "tier": "tier1",
                "ownerModule": "file_io",
                "rustCrate": "classic-file-io-core",
                "rustSymbol": "encoding",
                "pythonModule": "classic_file_io",
                "pythonExportPath": "EncodingDetector",
                "pythonKind": "class",
            }
        ]
    }
    rust_manifest = {
        "symbols": [
            {"crate": "classic-file-io-core", "symbol": "encoding", "kind": "module"}
        ]
    }

    assert gate.validate_contract_rust_symbols(contract, rust_manifest) == []


def test_wrapper_source_rejects_a_namesake_in_the_claimed_crate() -> None:
    """A row cannot borrow a namesake while its PyO3 wrapper uses another owner."""
    contract = {
        "tier1Mappings": [
            {
                "id": "stable-export-row",
                "tier": "tier1",
                "ownerModule": "file_io",
                "rustCrate": "classic-claimed-core",
                "rustSymbol": "SharedName",
                "pythonModule": "classic_file_io",
                "pythonExportPath": "SharedName",
                "pythonKind": "class",
            }
        ]
    }
    rust_manifest = {
        "symbols": [
            {"crate": "classic-claimed-core", "symbol": "SharedName", "kind": "struct"},
            {"crate": "classic-actual-core", "symbol": "SharedName", "kind": "struct"},
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "classic_file_io",
                "export": "SharedName",
                "export_path": "SharedName",
                "kind": "class",
            }
        ]
    }
    wrappers = {
        "classic_file_io.SharedName": Resolution(
            python_export="SharedName",
            python_module="classic_file_io",
            rust_symbol="SharedName",
            rust_crate="classic-actual-core",
            confidence="exact",
            crate_from_source=True,
        )
    }

    diagnostics = gate.validate_contract_rust_symbols(contract, rust_manifest, wrappers)
    report = baseline.generate_diff_report(contract, rust_manifest, python_manifest, wrappers)

    assert any("stable-export-row" in message and "classic-actual-core" in message
               for message in diagnostics)
    assert report["contract_results"][0]["status"] == "owner_mismatch"


def test_rust_inventory_row_does_not_hide_an_ordinary_owner_mismatch() -> None:
    """A companion @rust row cannot disable source checks for a public export."""
    ordinary = {
        "id": "config-clear-yaml-cache",
        "tier": "tier1",
        "ownerModule": "config",
        "rustCrate": "classic-settings-core",
        "rustSymbol": "clear_yaml_cache",
        "pythonModule": "classic_config",
        "pythonExportPath": "clear_yaml_cache",
        "pythonKind": "function",
    }
    inventory = {
        **ordinary,
        "id": "config.cache.clear_yaml_cache@rust",
        "rustCrate": "classic-config-core",
    }
    contract = {"tier1Mappings": [ordinary, inventory]}
    rust_manifest = {
        "symbols": [
            {"crate": crate, "symbol": "clear_yaml_cache", "kind": "function"}
            for crate in ("classic-settings-core", "classic-config-core")
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "classic_config",
                "export": "clear_yaml_cache",
                "export_path": "clear_yaml_cache",
                "kind": "function",
            }
        ]
    }
    wrappers = {
        "classic_config.clear_yaml_cache": Resolution(
            python_export="clear_yaml_cache",
            python_module="classic_config",
            rust_symbol="clear_yaml_cache",
            rust_crate="classic-config-core",
            confidence="exact",
            crate_from_source=True,
        )
    }

    diagnostics = gate.validate_contract_rust_symbols(contract, rust_manifest, wrappers)
    report = baseline.generate_diff_report(contract, rust_manifest, python_manifest, wrappers)

    assert any("config-clear-yaml-cache" in message and "classic-config-core" in message
               for message in diagnostics)
    assert report["contract_results"][0]["status"] == "owner_mismatch"
    assert report["contract_results"][1]["status"] == "matched"


def test_untraceable_checked_in_facade_import_cannot_match() -> None:
    """A facade's declared native import must resolve before its row can match."""
    contract = {
        "tier1Mappings": [
            {
                "id": "stable-facade-row",
                "tier": "tier1",
                "ownerModule": "shared",
                "rustCrate": "classic-shared-core",
                "rustSymbol": "SharedThing",
                "pythonModule": "classic_alpha",
                "pythonExportPath": "AlphaThing",
                "pythonKind": "class",
            }
        ]
    }
    rust_manifest = {
        "symbols": [
            {"crate": "classic-shared-core", "symbol": "SharedThing", "kind": "struct"}
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "classic_alpha",
                "export": "AlphaThing",
                "export_path": "AlphaThing",
                "kind": "class",
            }
        ]
    }
    wrappers = {
        "classic_alpha.AlphaThing": Resolution(
            python_export="AlphaThing",
            python_module="classic_alpha",
            route_error="native export SharedThing not found for classic_alpha.AlphaThing",
        )
    }

    diagnostics = gate.validate_contract_rust_symbols(contract, rust_manifest, wrappers)
    report = baseline.generate_diff_report(contract, rust_manifest, python_manifest, wrappers)

    assert any("stable-facade-row" in message and "SharedThing not found" in message
               for message in diagnostics)
    assert report["contract_results"][0]["status"] == "owner_mismatch"


def test_untraceable_facade_import_fails_with_multiple_ordinary_rows() -> None:
    """Shared export names cannot hide an explicit broken facade route."""
    rows = [
        {
            "id": f"snapshot-source-{symbol}",
            "tier": "tier1",
            "ownerModule": "user_settings",
            "rustCrate": "classic-user-settings-core",
            "rustSymbol": symbol,
            "pythonModule": "classic_user_settings",
            "pythonExportPath": "UserSettingsSnapshot",
            "pythonKind": "class",
        }
        for symbol in ("UserSettings", "FrontendState")
    ]
    contract = {"tier1Mappings": rows}
    rust_manifest = {
        "symbols": [
            {"crate": "classic-user-settings-core", "symbol": symbol, "kind": "struct"}
            for symbol in ("UserSettings", "FrontendState")
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "classic_user_settings",
                "export": "UserSettingsSnapshot",
                "export_path": "UserSettingsSnapshot",
                "kind": "class",
            }
        ]
    }
    wrappers = {
        "classic_user_settings.UserSettingsSnapshot": Resolution(
            python_export="UserSettingsSnapshot",
            python_module="classic_user_settings",
            route_error="no traceable native import",
        )
    }

    diagnostics = gate.validate_contract_rust_symbols(contract, rust_manifest, wrappers)
    report = baseline.generate_diff_report(contract, rust_manifest, python_manifest, wrappers)

    assert len(diagnostics) == 2
    assert all(any(row["id"] in message for message in diagnostics) for row in rows)
    assert [row["status"] for row in report["contract_results"]] == [
        "owner_mismatch", "owner_mismatch"
    ]


def test_method_source_rejects_a_same_named_wrong_crate() -> None:
    """A PyO3 method's direct core call must agree with its mapped crate."""
    contract = {
        "tier1Mappings": [
            {
                "id": "scanlog.request.standard",
                "tier": "tier1",
                "ownerModule": "scanlog",
                "rustCrate": "classic-claimed-core",
                "rustSymbol": "standard",
                "pythonModule": "classic_scanlog",
                "pythonExportPath": "ScanRunRequest.standard",
                "pythonKind": "method",
            }
        ]
    }
    rust_manifest = {
        "symbols": [
            {"crate": crate, "symbol": "standard", "kind": "function"}
            for crate in ("classic-claimed-core", "classic-actual-core")
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "classic_scanlog",
                "export": "standard",
                "export_path": "ScanRunRequest.standard",
                "kind": "method",
            }
        ]
    }
    wrappers = {
        "classic_scanlog.ScanRunRequest.standard": Resolution(
            python_export="standard",
            python_module="classic_scanlog",
            rust_symbol="standard",
            rust_crate="classic-actual-core",
            confidence="exact",
            crate_from_source=True,
        )
    }

    diagnostics = gate.validate_contract_rust_symbols(contract, rust_manifest, wrappers)
    report = baseline.generate_diff_report(contract, rust_manifest, python_manifest, wrappers)

    assert any("scanlog.request.standard" in message and "classic-actual-core" in message
               for message in diagnostics)
    assert report["contract_results"][0]["status"] == "owner_mismatch"


def test_method_source_accepts_an_owner_type_row_in_the_same_crate() -> None:
    """An owner-type row can differ from the invoked method while keeping its crate."""
    contract = {
        "tier1Mappings": [
            {
                "id": "registry.match",
                "tier": "tier1",
                "ownerModule": "version_registry",
                "rustCrate": "classic-version-registry-core",
                "rustSymbol": "VersionRegistry",
                "pythonModule": "classic_version_registry",
                "pythonExportPath": "VersionRegistry.match_version",
                "pythonKind": "method",
            }
        ]
    }
    rust_manifest = {
        "symbols": [
            {
                "crate": "classic-version-registry-core",
                "symbol": "VersionRegistry",
                "kind": "struct",
            },
            {
                "crate": "classic-version-registry-core",
                "symbol": "match_version",
                "kind": "function",
            },
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "classic_version_registry",
                "export": "match_version",
                "export_path": "VersionRegistry.match_version",
                "kind": "method",
            }
        ]
    }
    wrappers = {
        "classic_version_registry.VersionRegistry.match_version": Resolution(
            python_export="match_version",
            python_module="classic_version_registry",
            rust_symbol="match_version",
            rust_crate="classic-version-registry-core",
            confidence="associated_fn",
            crate_from_source=True,
        )
    }

    assert gate.validate_contract_rust_symbols(contract, rust_manifest, wrappers) == []
    report = baseline.generate_diff_report(contract, rust_manifest, python_manifest, wrappers)
    assert report["contract_results"][0]["status"] == "matched"
