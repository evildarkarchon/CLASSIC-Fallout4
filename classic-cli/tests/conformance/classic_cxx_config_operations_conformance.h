// SPDX-License-Identifier: MIT
// Explicit config observations traverse the public generated bridge.

namespace config_operations = classic::config;

#include "classic_cxx_config_yaml_values_conformance.h"

/// Re-read every durable file after native execution, preserving exact UTF-8 bytes.
json config_operations_files(const fs::path& root) {
    json result = json::array();
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_symlink())
            throw RunnerError("unexpected link in config workspace");
        if (entry.is_directory())
            continue;
        const auto bytes = read_optional_file(entry.path());
        if (!bytes)
            throw RunnerError("config workspace file disappeared during observation");
        result.push_back(
            json{{"path", relative_path(root, entry.path())}, {"content", std::string(bytes->begin(), bytes->end())}});
    }
    std::sort(result.begin(), result.end(), [](const json& a, const json& b) { return a.at("path") < b.at("path"); });
    return result;
}

/// Execute the exact fixture-selected files and retain structured native error attribution.
json execute_config_operations_scenario(const json& plan, const json& scenario) {
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),
                                 scenario.at("id").get<std::string>());
    const fs::path& root = temporary.path();
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end()) {
        throw RunnerError("config operation fixture is not declared by scenario");
    }
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    if ((fixture.at("operation") != "load-explicit" && fixture.at("operation") != "main-version" &&
         fixture.at("operation") != "persist-local") ||
        fixture.size() != (fixture.at("operation") == "persist-local" ? 4 : 2)) {
        throw RunnerError("unsupported config operation fixture");
    }
    for (const auto& [name, content] : fixture.at("files").items()) {
        if ((name != "main.yaml" && name != "game.yaml" && name != "ignore.yaml" && name != "CLASSIC Main.yaml" &&
             name != "local.yaml" && name != "CLASSIC Settings.yaml") ||
            !content.is_string()) {
            throw RunnerError("config fixture requires owned YAML filenames and UTF-8 text");
        }
        std::ofstream output(root / name, std::ios::binary);
        output << content.get<std::string>();
        output.close();
        if (!output)
            throw RunnerError("cannot write config fixture file");
    }
    if (fixture.at("operation") == "persist-local") {
        config_operations::save_local_yaml_paths(
            (root / "local.yaml").string(),
            fixture.at("gameRoot").is_null() ? "" : fixture.at("gameRoot").get<std::string>(),
            fixture.at("docsRoot").is_null() ? "" : fixture.at("docsRoot").get<std::string>());
        return json{{"result", nullptr}, {"error", nullptr}, {"files", config_operations_files(root)}};
    }
    if (fixture.at("operation") == "main-version") {
        // Own the cache fallback so developer-installed YAML cannot decide this observation.
        RuntimeEnvironment environment(root);
        const auto version = config_operations::load_main_yaml_version(root.string());
        if (!version.error_kind.empty())
            throw RunnerError("main YAML version load failed: " + owned_string(version.error_message));
        return json{{"result", json{{"version", owned_string(version.version)}}},
                    {"error", nullptr},
                    {"files", config_operations_files(root)}};
    }
    config_operations::ExplicitYamlDataPathsDto paths{};
    paths.main_path = (root / "main.yaml").string();
    paths.game_path = (root / "game.yaml").string();
    paths.ignore_path = (root / "ignore.yaml").string();
    auto load = config_operations::explicit_yaml_data_load(std::move(paths),
                                                           config_operations::ExplicitYamlDataGameId::Fallout4, "auto");
    const auto status = config_operations::explicit_yaml_data_load_status(*load);
    if (status.has_snapshot == status.has_error)
        throw RunnerError("invalid explicit config load presence flags");
    json result = nullptr;
    json error = nullptr;
    if (status.has_snapshot) {
        const auto snapshot = config_operations::explicit_yaml_data_load_take_snapshot(std::move(load));
        if (config_operations::explicit_yaml_data_snapshot_game(*snapshot) !=
            config_operations::ExplicitYamlDataGameId::Fallout4) {
            throw RunnerError("explicit snapshot returned an unexpected game");
        }
        if (config_operations::explicit_yaml_data_snapshot_game_role(*snapshot) !=
            config_operations::ExplicitYamlDataGameRole::Fallout4) {
            throw RunnerError("explicit snapshot returned an unexpected game role");
        }
        const auto identity = [](const auto& value) {
            return json{{"sha256", owned_string(value.sha256)}, {"byteLen", value.byte_len}};
        };
        const auto data = config_operations::explicit_yaml_data_snapshot_yaml_data(*snapshot);
        json ignore = json::array();
        for (const auto& value : config_operations::yaml_data_ignore_list(*data))
            ignore.push_back(owned_string(value));
        result =
            json{{"game", "Fallout4"},
                 {"yamlValues", config_yaml_values(*data)},
                 {"gameRole", "Fallout4"},
                 {"identities",
                  json{{"main.yaml", identity(config_operations::explicit_yaml_data_snapshot_main_identity(*snapshot))},
                       {"game.yaml", identity(config_operations::explicit_yaml_data_snapshot_game_identity(*snapshot))},
                       {"ignore.yaml",
                        identity(config_operations::explicit_yaml_data_snapshot_ignore_identity(*snapshot))}}},
                 {"classicVersion", std::string(config_operations::yaml_data_classic_version(*data))},
                 {"xseAcronym", std::string(config_operations::yaml_data_xse_acronym(*data))},
                 {"crashgenName", std::string(config_operations::yaml_data_crashgen_name_field(*data))},
                 {"gameVersion", std::string(config_operations::yaml_data_game_version(*data))},
                 {"ignoreList", std::move(ignore)}};
    } else {
        std::string code;
        using E = config_operations::ExplicitYamlDataLoadErrorKind;
        switch (status.error.kind) {
        case E::Read:
            code = "read";
            break;
        case E::Parse:
            code = "parse";
            break;
        case E::InvalidUtf8:
            code = "invalid_utf8";
            break;
        case E::InvalidRoleData:
            code = "invalid_role_data";
            break;
        case E::UnsupportedGame:
            code = "unsupported_game";
            break;
        default:
            throw RunnerError("unknown explicit config error kind");
        }
        json role = nullptr;
        if (status.error.has_role) {
            using R = config_operations::ExplicitYamlDataRole;
            switch (status.error.role) {
            case R::Main:
                role = "main";
                break;
            case R::Game:
                role = "game";
                break;
            case R::LocalIgnore:
                role = "local_ignore";
                break;
            default:
                throw RunnerError("unknown explicit config error role");
            }
        }
        error =
            json{{"code", code},
                 {"role", role},
                 {"path", status.error.has_path ? json(relative_path(root, fs::path(owned_string(status.error.path))))
                                                : json(nullptr)}};
    }
    return json{{"result", result}, {"error", error}, {"files", config_operations_files(root)}};
}
