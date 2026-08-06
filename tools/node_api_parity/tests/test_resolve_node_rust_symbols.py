"""Unit tests for the NAPI export -> core Rust symbol resolver.

The resolver replaces guesswork with ranked evidence. These tests pin the cases
where a plausible-looking guess is wrong, and the declaration shapes that were
silently skipped before -- each of those produced either a bogus mapping or no
mapping at all, both of which the parity gate would have reported as fine.
"""

from __future__ import annotations

from pathlib import Path

import resolve_node_rust_symbols as rns

SURFACE = {
    "GithubAsset": [
        {"symbol": "GithubAsset", "kind": "struct", "crate": "classic-update-core"}
    ],
    "MigrationEndpoint": [
        {
            "symbol": "MigrationEndpoint",
            "kind": "struct",
            "crate": "classic-user-settings-core",
        }
    ],
    "YamlOperations": [
        {"symbol": "YamlOperations", "kind": "struct", "crate": "classic-settings-core"}
    ],
    "XseType": [{"symbol": "XseType", "kind": "enum", "crate": "classic-xse-core"}],
    "GameId": [{"symbol": "GameId", "kind": "enum", "crate": "classic-shared-core"}],
    "get_latest_release": [
        {
            "symbol": "get_latest_release",
            "kind": "function",
            "crate": "classic-update-core",
        }
    ],
    "new": [{"symbol": "new", "kind": "function", "crate": "classic-config-core"}],
    "all": [{"symbol": "all", "kind": "function", "crate": "classic-file-io-core"}],
    "as_str": [{"symbol": "as_str", "kind": "function", "crate": "classic-config-core"}],
    "get_runtime": [
        {"symbol": "get_runtime", "kind": "function", "crate": "classic-shared-core"}
    ],
    "path_core": [
        {"symbol": "path_core", "kind": "module", "crate": "classic-shared-core"}
    ],
}


def resolve(**info) -> rns.Resolution:
    base = {
        "kind": "fn",
        "rust_name": "thing",
        "source_file": "x.rs",
        "decl_body": "",
        "body": "",
        "import_map": {},
        "from_impls": {},
        "conversions": {},
        "local_helpers": {},
    }
    export = info.pop("export", "thing")
    base.update(info)
    return rns.resolve_export(export, base, SURFACE)


class TestUbiquitousMethodNames:
    def test_generic_constructor_is_not_a_counterpart(self) -> None:
        """`new` matched anything and produced `checkForUpdates -> new`."""
        res = resolve(
            export="checkForUpdates",
            rust_name="check_for_updates",
            body="{ let c = core::GithubClient::new(o); c.get_latest_release().await }",
            import_map={"core": "classic_update_core"},
        )
        assert res.rust_symbol == "get_latest_release"

    def test_as_str_is_not_a_counterpart(self) -> None:
        res = resolve(
            export="parseThing", rust_name="parse_thing", body="{ rt.as_str() }"
        )
        assert res.rust_symbol != "as_str"

    def test_all_is_not_a_counterpart(self) -> None:
        res = resolve(export="getThings", rust_name="get_things", body="{ x.all() }")
        assert res.rust_symbol != "all"


class TestAssociatedAndTurbofishForms:
    def test_associated_function_call(self) -> None:
        res = resolve(
            export="xseTypeForGame",
            rust_name="xse_type_for_game",
            body="{ XseType::from_game_id(core_game) }",
            import_map={"XseType": "classic_xse_core"},
        )
        assert res.rust_symbol in {"XseType", "from_game_id"}

    def test_enum_variant_in_a_match_arm(self) -> None:
        """`GameId::Fallout4` names the core type as plainly as a call does."""
        res = resolve(
            export="getGameName",
            rust_name="get_game_name",
            body='{ match id { GameId::Fallout4 => "Fallout 4".to_string() } }',
            import_map={"GameId": "classic_shared_core"},
        )
        assert (res.rust_symbol, res.confidence) == ("GameId", "core_assoc")

    def test_turbofish_type_argument(self) -> None:
        res = resolve(
            export="parseXseType",
            rust_name="parse_xse_type",
            body="{ type_name.parse::<XseType>().map_err(to_napi_err) }",
            import_map={"XseType": "classic_xse_core"},
        )
        assert res.rust_symbol == "XseType"


class TestConversionAndFieldEvidence:
    def test_conversion_helper_pairs_a_dto_with_its_core_type(self) -> None:
        """`#[napi(object)]` DTOs never name their core type directly."""
        res = resolve(
            export="JsUserSettingsMigrationEndpoint",
            rust_name="JsUserSettingsMigrationEndpoint",
            kind="struct",
            conversions={"JsUserSettingsMigrationEndpoint": "MigrationEndpoint"},
        )
        assert (res.rust_symbol, res.confidence) == (
            "MigrationEndpoint",
            "conversion_fn",
        )

    def test_inner_field_names_the_wrapped_core_type(self) -> None:
        res = resolve(
            export="YamlDocument",
            rust_name="YamlDocument",
            kind="struct",
            decl_body="{\n    ops: YamlOperations,\n}",
        )
        assert (res.rust_symbol, res.confidence) == ("YamlOperations", "inner_field")

    def test_js_prefix_convention(self) -> None:
        res = resolve(
            export="JsGithubAsset", rust_name="JsGithubAsset", kind="struct"
        )
        assert res.rust_symbol == "GithubAsset"


class TestLocalHelperIndirection:
    def test_one_level_of_indirection_is_followed(self) -> None:
        """The wrapper delegates; only the helper names the core symbol."""
        res = resolve(
            export="getLatest",
            rust_name="get_latest",
            body="{ do_fetch(&owner) }",
            local_helpers={
                "do_fetch": "{ classic_update_core::get_latest_release(owner) }"
            },
        )
        assert res.rust_symbol == "get_latest_release"

    def test_helper_bodies_are_not_searched_when_not_called(self) -> None:
        res = resolve(
            export="unrelated",
            rust_name="unrelated",
            body="{ 42 }",
            local_helpers={
                "do_fetch": "{ classic_update_core::get_latest_release(owner) }"
            },
        )
        assert res.rust_symbol is None


class TestNeverAcceptsPlaceholders:
    def test_a_module_is_never_a_counterpart(self) -> None:
        res = resolve(
            export="joinPaths",
            rust_name="join_paths",
            body="{ classic_shared_core::path_core::helper() }",
            import_map={"path_core": "classic_shared_core"},
        )
        assert res.rust_symbol != "path_core"

    def test_infrastructure_is_never_a_counterpart(self) -> None:
        res = resolve(
            export="loadThing",
            rust_name="load_thing",
            body="{ let rt = get_runtime(); }",
            import_map={"get_runtime": "classic_shared_core"},
        )
        assert res.rust_symbol != "get_runtime"


class TestAgainstRealBindings:
    def test_declarations_with_intervening_attributes_are_found(self) -> None:
        """`#[napi(object)]` + `#[derive(Clone)]` + struct, and attribute comments."""
        repo_root = Path(__file__).resolve().parents[3]
        wrappers = rns.collect_node_wrappers(repo_root)

        # DTO behind a #[derive(Clone)].
        assert "JsGithubAsset" in wrappers
        # Function behind an #[allow(deprecated)] carrying a trailing comment.
        assert "checkForUpdates" in wrappers
        assert wrappers["checkForUpdates"]["rust_name"] == "check_for_updates"
