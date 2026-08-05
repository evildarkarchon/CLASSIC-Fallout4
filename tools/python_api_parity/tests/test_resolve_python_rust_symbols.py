"""Unit tests for the PyO3 export -> core Rust symbol resolver.

The resolver's job is to replace guesswork with evidence, so the tests focus on
which evidence wins and on the cases where a plausible-looking guess would be
wrong.
"""

from __future__ import annotations

from pathlib import Path

import resolve_python_rust_symbols as rps

SURFACE = {
    "YamlDataCore": [{"symbol": "YamlDataCore", "kind": "struct", "crate": "classic-config-core"}],
    "FormIDAnalyzer": [
        {"symbol": "FormIDAnalyzer", "kind": "struct", "crate": "classic-scanlog-core"}
    ],
    "RustFormIDAnalyzer": [
        {"symbol": "RustFormIDAnalyzer", "kind": "struct", "crate": "classic-scanlog-core"}
    ],
    "LogParser": [{"symbol": "LogParser", "kind": "struct", "crate": "classic-scanlog-core"}],
    "is_valid_executable_path": [
        {
            "symbol": "is_valid_executable_path",
            "kind": "function",
            "crate": "classic-version-core",
        }
    ],
    "pe_version": [
        {"symbol": "pe_version", "kind": "module", "crate": "classic-version-core"}
    ],
    "get_runtime": [
        {"symbol": "get_runtime", "kind": "function", "crate": "classic-shared-core"}
    ],
    "yamldata": [
        {"symbol": "yamldata", "kind": "module", "crate": "classic-config-core"}
    ],
}


def resolve(info: dict) -> rps.Resolution:
    base = {
        "kind": "struct",
        "rust_name": "PyThing",
        "source_file": "x.rs",
        "decl_body": "",
        "body": "",
        "import_map": {},
        "from_impls": {},
    }
    base.update(info)
    return rps.resolve_export(base.pop("export", "Thing"), base, SURFACE)


def test_inner_field_beats_a_same_named_decoy() -> None:
    """`FormIDAnalyzer` exists in core, but the wrapper wraps RustFormIDAnalyzer."""
    res = resolve(
        {
            "export": "FormIDAnalyzer",
            "rust_name": "PyRustFormIDAnalyzer",
            "decl_body": "{\n    inner: RustFormIDAnalyzer,\n}",
        }
    )
    assert (res.rust_symbol, res.confidence) == ("RustFormIDAnalyzer", "inner_field")


def test_inner_field_resolves_a_suffixed_core_type() -> None:
    """`YamlData` has no same-named core type; the field names YamlDataCore."""
    res = resolve(
        {
            "export": "YamlData",
            "rust_name": "PyYamlData",
            "decl_body": "{\n    inner: YamlDataCore,\n}",
        }
    )
    assert res.rust_symbol == "YamlDataCore"


def test_name_match_used_when_there_is_no_inner_field() -> None:
    res = resolve({"export": "LogParser", "rust_name": "PyLogParser"})
    assert (res.rust_symbol, res.confidence) == ("LogParser", "name_match")


def test_multi_segment_qualified_path_yields_the_final_symbol() -> None:
    """`a::b::c` must resolve to `c`, not to the module `b`."""
    res = resolve(
        {
            "export": "is_valid_pe_path",
            "rust_name": "is_valid_pe_path",
            "kind": "fn",
            "body": (
                "{ classic_version_core::pe_version::is_valid_executable_path"
                "(std::path::Path::new(path)) }"
            ),
        }
    )
    assert res.rust_symbol == "is_valid_executable_path"


def test_a_module_is_never_accepted_as_a_counterpart() -> None:
    """The whole point: an export may not resolve onto a Rust module."""
    res = resolve(
        {
            "export": "Thing",
            "rust_name": "PyThing",
            "body": "{ classic_config_core::yamldata::helper() }",
            "import_map": {"yamldata": "classic_config_core"},
        }
    )
    assert res.rust_symbol != "yamldata"
    assert res.confidence == "unresolved"


def test_infrastructure_is_not_a_counterpart() -> None:
    """`get_runtime` is plumbing present in nearly every wrapper."""
    res = resolve(
        {
            "export": "Thing",
            "rust_name": "PyThing",
            "import_map": {"get_runtime": "classic_shared_core"},
            "body": "{ let rt = get_runtime(); }",
        }
    )
    assert res.rust_symbol != "get_runtime"


def test_unresolvable_export_reports_candidates() -> None:
    res = resolve({"export": "Mystery", "rust_name": "PyMystery"})
    assert res.confidence == "unresolved"
    assert res.rust_symbol is None


class TestAgainstRealBindings:
    def test_resolver_runs_over_the_repo_and_finds_exports(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        wrappers = rps.collect_python_wrappers(repo_root)
        assert len(wrappers) > 100, (
            f"expected the PyO3 binding scan to find many exports, got {len(wrappers)}"
        )
        # A representative pyclass with an explicit Python-visible name.
        assert "FormIDAnalyzer" in wrappers
        assert wrappers["FormIDAnalyzer"]["rust_name"] == "PyRustFormIDAnalyzer"
