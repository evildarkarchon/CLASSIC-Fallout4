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


def test_imported_inner_field_records_its_core_crate() -> None:
    """A wrapper field imported from core is direct owner evidence."""
    surface = {
        "LogParser": [
            {"symbol": "LogParser", "kind": "struct", "crate": "classic-config-core"},
            {"symbol": "LogParser", "kind": "struct", "crate": "classic-scanlog-core"},
        ]
    }
    info = {
        "rust_name": "PyParser",
        "body": "{\n    inner: LogParser,\n}",
        "decl_body": "{\n    inner: LogParser,\n}",
        "import_map": {"LogParser": "classic_scanlog_core"},
        "from_impls": {},
    }

    res = rps.resolve_export("Parser", info, surface)

    assert (res.rust_symbol, res.rust_crate) == (
        "LogParser",
        "classic-scanlog-core",
    )
    assert rps.source_backed_crate(res) == "classic-scanlog-core"


def test_incidental_typed_field_is_not_source_backed() -> None:
    """A DTO's GameId field does not make GameId its core counterpart."""
    info = {
        "kind": "struct",
        "rust_name": "PyScanRunConfiguration",
        "decl_body": "{\n    game: classic_shared_core::GameId,\n}",
        "body": "{\n    game: classic_shared_core::GameId,\n}",
        "import_map": {},
        "from_impls": {},
    }
    surface = {
        "GameId": [
            {"symbol": "GameId", "kind": "enum", "crate": "classic-shared-core"}
        ]
    }
    res = rps.resolve_export("ScanRunConfiguration", info, surface)

    assert rps.source_backed_crate(res) is None


def test_imported_same_named_core_type_beats_a_config_field() -> None:
    """An orchestrator's config field is input, not its wrapped operation."""
    surface = {
        "GameScanConfig": [
            {"symbol": "GameScanConfig", "kind": "struct", "crate": "classic-scangame-core"}
        ],
        "GameScanOrchestrator": [
            {
                "symbol": "GameScanOrchestrator",
                "kind": "struct",
                "crate": "classic-scangame-core",
            }
        ],
    }
    info = {
        "rust_name": "PyGameScanOrchestrator",
        "body": "{\n config: GameScanConfig,\n GameScanOrchestrator::new(config)\n}",
        "decl_body": "{\n config: GameScanConfig,\n}",
        "import_map": {
            "GameScanConfig": "classic_scangame_core",
            "GameScanOrchestrator": "classic_scangame_core",
        },
        "from_impls": {},
    }

    res = rps.resolve_export("GameScanOrchestrator", info, surface)

    assert rps.source_backed_symbol(res) == "GameScanOrchestrator"


def test_imported_type_associated_method_is_the_function_counterpart() -> None:
    """`UserSettings::open` identifies the public operation, not its receiver type."""
    surface = {
        "UserSettings": [
            {"symbol": "UserSettings", "kind": "struct", "crate": "classic-user-settings-core"}
        ],
        "open": [
            {"symbol": "open", "kind": "function", "crate": "classic-user-settings-core"}
        ],
    }
    info = {
        "kind": "fn",
        "rust_name": "open_user_settings",
        "body": "{ UserSettings::open(classic_root) }",
        "decl_body": "{ UserSettings::open(classic_root) }",
        "import_map": {"UserSettings": "classic_user_settings_core"},
        "from_impls": {},
    }

    res = rps.resolve_export("open_user_settings", info, surface)

    assert rps.source_backed_symbol(res) == "open"


def test_into_core_return_type_beats_incidental_imports() -> None:
    """A conversion's result names the DTO counterpart before helper types."""
    surface = {
        "ModSolutionCriteria": [
            {"symbol": "ModSolutionCriteria", "kind": "enum", "crate": "classic-config-core"}
        ],
        "ModSolutionEntry": [
            {"symbol": "ModSolutionEntry", "kind": "struct", "crate": "classic-config-core"}
        ],
    }
    info = {
        "kind": "struct",
        "rust_name": "PyModGuidanceSolutionRule",
        "body": "{ fn into_core(self) -> ModSolutionEntry { ModSolutionCriteria::Any(vec![]) } }",
        "decl_body": "{}",
        "import_map": {
            "ModSolutionCriteria": "classic_config_core",
            "ModSolutionEntry": "classic_config_core",
        },
        "from_impls": {},
    }

    res = rps.resolve_export("ModGuidanceSolutionRule", info, surface)

    assert rps.source_backed_symbol(res) == "ModSolutionEntry"


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


def test_qualified_reference_cannot_borrow_a_namesake_from_another_crate() -> None:
    """A matching export name cannot override the crate named in source."""
    res = resolve(
        {
            "export": "LogParser",
            "rust_name": "LogParser",
            "body": "{ classic_config_core::LogParser::new() }",
        }
    )

    assert (res.rust_symbol, res.rust_crate, res.confidence) == (
        None,
        None,
        "unresolved",
    )


def test_external_reexport_resolves_to_the_defining_core_crate() -> None:
    """A wrapper's config path may reexport a settings-owned operation."""
    surface = {
        "clear_global_yaml_cache": [
            {
                "symbol": "clear_global_yaml_cache",
                "kind": "reexport",
                "crate": "classic-config-core",
                "source_expr": "classic_settings_core::clear_global_yaml_cache",
            },
            {
                "symbol": "clear_global_yaml_cache",
                "kind": "function",
                "crate": "classic-settings-core",
            },
        ]
    }
    info = {
        "kind": "fn",
        "rust_name": "clear_yaml_cache",
        "body": "{ classic_config_core::clear_global_yaml_cache() }",
        "decl_body": "{ classic_config_core::clear_global_yaml_cache() }",
        "import_map": {},
        "from_impls": {},
    }

    res = rps.resolve_export("clear_yaml_cache", info, surface)

    assert (rps.source_backed_crate(res), rps.source_backed_symbol(res)) == (
        "classic-settings-core",
        "clear_global_yaml_cache",
    )


def test_from_impl_keeps_the_core_crate_when_names_collide(tmp_path: Path) -> None:
    """A `From<crate::Type>` path identifies the owner of a converted type."""
    source = tmp_path / "python-bindings" / "classic-example-py" / "src" / "lib.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        "#[pyclass]\npub struct LogParser {}\n"
        "impl From<classic_config_core::LogParser> for LogParser {}\n",
        encoding="utf-8",
    )

    wrappers = rps.collect_python_wrappers(tmp_path)
    res = rps.resolve_export("LogParser", wrappers["classic_example.LogParser"], SURFACE)

    assert (res.rust_symbol, res.rust_crate, res.confidence) == (
        None,
        None,
        "unresolved",
    )


def test_crate_alias_in_from_impl_keeps_the_core_owner(tmp_path: Path) -> None:
    """A Rust `use crate as core` alias must retain its source crate."""
    source = tmp_path / "python-bindings" / "classic-example-py" / "src" / "lib.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        "use classic_config_core as core;\n"
        "#[pyclass]\npub struct LogParser {}\n"
        "impl From<core::LogParser> for LogParser {}\n",
        encoding="utf-8",
    )

    wrappers = rps.collect_python_wrappers(tmp_path)
    res = rps.resolve_export("LogParser", wrappers["classic_example.LogParser"], SURFACE)

    assert (res.rust_symbol, res.rust_crate, res.confidence) == (
        None,
        None,
        "unresolved",
    )


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
        """Facade-qualified keys retain direct-import module ownership."""
        repo_root = Path(__file__).resolve().parents[3]
        wrappers = rps.collect_python_wrappers(repo_root)
        assert len(wrappers) > 100, (
            f"expected the PyO3 binding scan to find many exports, got {len(wrappers)}"
        )
        # A representative pyclass with an explicit Python-visible name.
        assert "classic_scanlog.FormIDAnalyzer" in wrappers
        assert wrappers["classic_scanlog.FormIDAnalyzer"]["rust_name"] == "PyRustFormIDAnalyzer"

    def test_scan_run_configuration_does_not_borrow_game_id_from_docs(self) -> None:
        """A documented GameId input is not the configuration's core owner."""
        repo_root = Path(__file__).resolve().parents[3]
        resolution = rps.resolve_all(repo_root)["classic_scanlog.ScanRunConfiguration"]
        assert rps.source_backed_crate(resolution) is None

    def test_pymethods_with_intervening_attribute_are_collected(self) -> None:
        """The YAML source's allow attribute must not hide its PyO3 methods."""
        repo_root = Path(__file__).resolve().parents[3]
        wrappers = rps.collect_python_wrappers(repo_root)
        assert "classic_config.YamlSource.path" in wrappers

    def test_method_resolution_follows_the_operation_past_incidental_types(self) -> None:
        """Parsing inputs must not replace the core operation's method symbol."""
        repo_root = Path(__file__).resolve().parents[3]
        rows = rps.resolve_all(repo_root)
        update = rows["classic_user_settings.UserSettingsUpdate.set_window_geometry"]
        compatible = rows["classic_version_registry.VersionInfo.get_compatible_crashgens"]
        assert rps.source_backed_symbol(update) == "with_window_geometry"
        assert rps.source_backed_symbol(compatible) == "get_compatible_crashgens"

    def test_analyzer_constructors_use_their_constructed_core_owner(self) -> None:
        """Database lookup factories are inputs to scanlog-owned analyzers."""
        repo_root = Path(__file__).resolve().parents[3]
        rows = rps.resolve_all(repo_root)
        for method in ("in_memory", "sqlite"):
            key = f"classic_scanlog.FormIDFindingAnalyzer.{method}"
            assert rps.source_backed_crate(rows[key]) == "classic-scanlog-core"
            assert rps.source_backed_symbol(rows[key]) is None


def test_same_named_exports_in_two_facades_are_both_retained(tmp_path: Path) -> None:
    """One facade's wrapper cannot silently replace another's."""
    for module in ("classic_alpha", "classic_beta"):
        source = (
            tmp_path / "python-bindings" / f"{module.replace('_', '-')}-py"
            / "src" / "lib.rs"
        )
        source.parent.mkdir(parents=True)
        source.write_text("#[pyfunction]\npub fn shared() {}\n", encoding="utf-8")

    wrappers = rps.collect_python_wrappers(tmp_path)

    assert set(wrappers) == {"classic_alpha.shared", "classic_beta.shared"}


def test_merged_adapter_discovers_facade_scoped_source(tmp_path: Path) -> None:
    """A future single PyO3 crate can keep wrappers under facade paths."""
    crate = tmp_path / "python-bindings" / "classic-python-adapter"
    (crate / "Cargo.toml").parent.mkdir(parents=True)
    (crate / "Cargo.toml").write_text(
        '[package]\nname = "classic-python-adapter"\n', encoding="utf-8"
    )
    source = crate / "src" / "facades" / "classic_alpha.rs"
    source.parent.mkdir(parents=True)
    source.write_text("#[pyfunction]\npub fn shared() {}\n", encoding="utf-8")

    wrappers = rps.collect_python_wrappers(tmp_path)

    assert set(wrappers) == {"classic_alpha.shared"}


def test_merged_py_crate_prefers_facade_path_over_crate_name(tmp_path: Path) -> None:
    """A merged adapter named `-py` still attributes each nested facade."""
    crate = tmp_path / "python-bindings" / "classic-unified-py"
    (crate / "Cargo.toml").parent.mkdir(parents=True)
    (crate / "Cargo.toml").write_text(
        '[package]\nname = "classic-unified-py"\n', encoding="utf-8"
    )
    source = crate / "src" / "facades" / "classic_alpha.rs"
    source.parent.mkdir(parents=True)
    source.write_text("#[pyfunction]\npub fn shared() {}\n", encoding="utf-8")

    wrappers = rps.collect_python_wrappers(tmp_path)

    assert set(wrappers) == {"classic_alpha.shared"}


def _write_shared_native_adapter(tmp_path: Path) -> Path:
    """Create one native PyO3 type and two direct-import Python facades."""
    crate = tmp_path / "python-bindings" / "classic-unified-py"
    crate.mkdir(parents=True)
    (crate / "Cargo.toml").write_text(
        '[package]\nname = "classic-unified-py"\n'
        '[lib]\nname = "_classic_native"\n',
        encoding="utf-8",
    )
    source = crate / "src" / "types.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        '#[pyclass(name = "SharedThing")]\n'
        'pub struct PySharedThing {\n    inner: classic_shared_core::SharedThing,\n}\n',
        encoding="utf-8",
    )
    alpha = crate / "python" / "classic_alpha" / "__init__.py"
    alpha.parent.mkdir(parents=True)
    alpha.write_text(
        "from _classic_native import SharedThing as AlphaThing\n",
        encoding="utf-8",
    )
    beta = crate / "python" / "classic_beta.py"
    beta.write_text(
        "from _classic_native import SharedThing as BetaThing\n",
        encoding="utf-8",
    )
    return crate


def test_merged_adapter_routes_one_native_type_to_two_facades(tmp_path: Path) -> None:
    """Facade imports, not Rust file paths, own each public name."""
    _write_shared_native_adapter(tmp_path)
    manifest = {
        "symbols": [
            {"symbol": "SharedThing", "kind": "struct", "crate": "classic-shared-core"}
        ]
    }

    resolutions = rps.resolve_all(tmp_path, manifest)

    assert set(resolutions) == {"classic_alpha.AlphaThing", "classic_beta.BetaThing"}
    assert {
        (rps.source_backed_crate(row), rps.source_backed_symbol(row))
        for row in resolutions.values()
    } == {("classic-shared-core", "SharedThing")}


def test_merged_facade_missing_native_export_is_unresolved(tmp_path: Path) -> None:
    """An import of an absent native name must not claim a core owner."""
    crate = _write_shared_native_adapter(tmp_path)
    alpha = crate / "python" / "classic_alpha" / "__init__.py"
    alpha.write_text(
        "from _classic_native import SharedThing as AlphaThing\n"
        "from _classic_native import MissingThing as Phantom\n",
        encoding="utf-8",
    )

    resolutions = rps.resolve_all(tmp_path, {"symbols": []})

    missing = resolutions["classic_alpha.Phantom"]
    assert missing.confidence == "unresolved"
    assert rps.source_backed_crate(missing) is None
    assert "MissingThing" in missing.route_error


def test_merged_native_source_without_facade_route_fails_closed(tmp_path: Path) -> None:
    """A generic native file cannot inherit the merged crate's name as a facade."""
    crate = _write_shared_native_adapter(tmp_path)
    (crate / "python" / "classic_alpha" / "__init__.py").unlink()
    (crate / "python" / "classic_beta.py").unlink()

    import pytest

    with pytest.raises(ValueError, match="no facade route"):
        rps.collect_python_wrappers(tmp_path)


def test_merged_facade_module_alias_and_all_are_traced(tmp_path: Path) -> None:
    """Attribute aliases route through the extension; untraced public names do not."""
    crate = _write_shared_native_adapter(tmp_path)
    alpha = crate / "python" / "classic_alpha" / "__init__.py"
    alpha.write_text(
        "from . import _classic_native as native\n"
        "AlphaThing = native.SharedThing\n"
        '__all__ = ["AlphaThing", "UnroutedThing"]\n',
        encoding="utf-8",
    )
    manifest = {
        "symbols": [
            {"symbol": "SharedThing", "kind": "struct", "crate": "classic-shared-core"}
        ]
    }

    resolutions = rps.resolve_all(tmp_path, manifest)

    assert rps.source_backed_symbol(resolutions["classic_alpha.AlphaThing"]) == "SharedThing"
    assert resolutions["classic_alpha.UnroutedThing"].route_error is not None


def test_nested_python_local_is_not_a_public_facade_route(tmp_path: Path) -> None:
    """A function-local alias cannot satisfy a declared public facade name."""
    crate = _write_shared_native_adapter(tmp_path)
    alpha = crate / "python" / "classic_alpha" / "__init__.py"
    alpha.write_text(
        "import _classic_native as native\n"
        "def helper():\n    Hidden = native.SharedThing\n"
        '__all__ = ["Hidden"]\n',
        encoding="utf-8",
    )

    resolutions = rps.resolve_all(tmp_path, {"symbols": []})

    assert resolutions["classic_alpha.Hidden"].route_error is not None


def test_method_cannot_borrow_a_namesake_from_wrong_core_crate(tmp_path: Path) -> None:
    """A dotted method row needs its own crate-qualified source evidence."""
    source = tmp_path / "python-bindings" / "classic-example-py" / "src" / "lib.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        '#[pyclass(name = "Thing")]\npub struct PyThing {}\n'
        '#[pymethods]\nimpl PyThing {\n'
        '    #[staticmethod]\n    fn scan() { classic_expected_core::scan(); }\n}\n',
        encoding="utf-8",
    )
    manifest = {
        "symbols": [
            {"symbol": "scan", "kind": "function", "crate": "classic-other-core"}
        ]
    }

    resolutions = rps.resolve_all(tmp_path, manifest)

    method = resolutions["classic_example.Thing.scan"]
    assert method.confidence == "unresolved"
    assert rps.source_backed_crate(method) is None


def test_getter_cannot_borrow_a_namesake_from_wrong_core_crate(tmp_path: Path) -> None:
    """A property getter's namesake elsewhere cannot certify its source owner."""
    source = tmp_path / "python-bindings" / "classic-example-py" / "src" / "lib.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        '#[pyclass(name = "Thing")]\npub struct PyThing {}\n'
        '#[pymethods]\nimpl PyThing {\n'
        '    #[getter]\n    fn size(&self) -> usize { '
        'classic_expected_core::size() }\n}\n',
        encoding="utf-8",
    )
    manifest = {
        "symbols": [
            {"symbol": "size", "kind": "function", "crate": "classic-other-core"}
        ]
    }

    resolutions = rps.resolve_all(tmp_path, manifest)

    getter = resolutions["classic_example.Thing.size"]
    assert getter.confidence == "unresolved"
    assert rps.source_backed_crate(getter) is None


def test_method_uses_its_qualified_core_call_when_names_collide(tmp_path: Path) -> None:
    """The Rust crate written in one method body selects its namesake."""
    source = tmp_path / "python-bindings" / "classic-example-py" / "src" / "lib.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        '#[pyclass(name = "Thing")]\npub struct PyThing {}\n'
        '#[pymethods]\nimpl PyThing {\n'
        '    fn scan(&self) { classic_expected_core::scan(); }\n}\n',
        encoding="utf-8",
    )
    manifest = {
        "symbols": [
            {"symbol": "scan", "kind": "function", "crate": "classic-other-core"},
            {"symbol": "scan", "kind": "function", "crate": "classic-expected-core"},
        ]
    }

    method = rps.resolve_all(tmp_path, manifest)["classic_example.Thing.scan"]

    assert (rps.source_backed_crate(method), rps.source_backed_symbol(method)) == (
        "classic-expected-core",
        "scan",
    )


def test_getter_on_typed_inner_receiver_keeps_its_core_crate(tmp_path: Path) -> None:
    """A getter calling its typed inner value has method-level owner evidence."""
    source = tmp_path / "python-bindings" / "classic-example-py" / "src" / "lib.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        '#[pyclass(name = "Thing")]\n'
        'pub struct PyThing {\n    inner: classic_expected_core::Thing,\n}\n'
        '#[pymethods]\nimpl PyThing {\n'
        '    #[getter]\n    fn get_size(&self) -> usize { self.inner.size() }\n}\n',
        encoding="utf-8",
    )
    manifest = {
        "symbols": [
            {"symbol": "Thing", "kind": "struct", "crate": "classic-expected-core"},
            {"symbol": "size", "kind": "function", "crate": "classic-other-core"},
            {"symbol": "size", "kind": "function", "crate": "classic-expected-core"},
        ]
    }

    getter = rps.resolve_all(tmp_path, manifest)["classic_example.Thing.size"]

    assert (rps.source_backed_crate(getter), rps.source_backed_symbol(getter)) == (
        "classic-expected-core",
        "size",
    )


def test_resolve_all_uses_a_provided_rust_manifest(tmp_path: Path) -> None:
    """A parity gate can reuse its Rust scan for source resolution."""
    source = tmp_path / "python-bindings" / "classic-example-py" / "src" / "lib.rs"
    source.parent.mkdir(parents=True)
    source.write_text(
        "#[pyfunction]\npub fn parse_log() { "
        "classic_scanlog_core::parse_log(); }\n",
        encoding="utf-8",
    )
    manifest = {
        "symbols": [
            {"symbol": "parse_log", "kind": "function", "crate": "classic-scanlog-core"}
        ]
    }

    resolutions = rps.resolve_all(tmp_path, manifest)

    resolution = resolutions["classic_example.parse_log"]
    assert (resolution.rust_symbol, resolution.rust_crate) == (
        "parse_log",
        "classic-scanlog-core",
    )
    assert rps.source_backed_crate(resolution) == "classic-scanlog-core"
    assert rps.source_backed_symbol(resolution) == "parse_log"
