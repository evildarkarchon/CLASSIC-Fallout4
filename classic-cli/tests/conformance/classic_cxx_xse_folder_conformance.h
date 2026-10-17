// SPDX-License-Identifier: MIT
// Locate the XSE log with isolated metadata and Local.yaml inputs.

/// Restores the process cwd before the owned XSE log fixture root is destroyed.
///
/// The resolver reads relative fixture folders against cwd, so the scenario switches
/// into its owned root for the call. Failure to restore terminates this isolated runner,
/// because every later scenario would otherwise resolve against the wrong directory.
class XseLogWorkingDirectory final {
public:
    /// Change cwd only within the dedicated serial family participant process.
    explicit XseLogWorkingDirectory(const fs::path& root) : previous_(fs::current_path()) {
        fs::current_path(root);
    }
    /// Avoid throwing during stack unwinding; see the class comment.
    ~XseLogWorkingDirectory() {
        std::error_code error;
        fs::current_path(previous_, error);
        if (error) std::terminate();
    }
    XseLogWorkingDirectory(const XseLogWorkingDirectory&) = delete;
    XseLogWorkingDirectory& operator=(const XseLogWorkingDirectory&) = delete;

private:
    fs::path previous_;
};

/// Locate the XSE log (`xse-folder.log`) against owned registry, Local.yaml and empty logs.
///
/// The resolver runs with the owned root as cwd so the relative fixture folders resolve inside
/// it and the returned log stays root-relative. The bridge's empty-string sentinel is absence;
/// only the core's "cannot inspect XSE log" `rust::Error` is the typed operational failure.
json execute_xse_log_scenario(const json& plan, const json& scenario) {
    static const std::set<std::string> controlled_log_files{
        "configured-docs/F4SE/f4se.log", "configured-docs/F4SE/f4sevr.log", "local-docs/F4SE/f4se.log",
        "explicit-xse/f4se.log"};
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(), scenario.at("id").get<std::string>());
    const auto& root = temporary.path();
    const auto game = fixture.at("game").get<std::string>();
    if (game != "Fallout4" && game != "Fallout4VR") throw RunnerError("unsupported XSE log game");
    {
        std::ofstream output(root / "CLASSIC Main.yaml", std::ios::binary);
        output << fixture.at("registryYaml").get<std::string>();
        output.close();
        if (!output) throw RunnerError("cannot seed controlled XSE registry");
    }
    if (!fixture.at("localYaml").is_null()) {
        std::ofstream output(root / ("CLASSIC " + game + " Local.yaml"), std::ios::binary);
        output << fixture.at("localYaml").get<std::string>();
        output.close();
        if (!output) throw RunnerError("cannot seed XSE Local.yaml");
    }
    for (const auto& file : fixture.at("logFiles")) {
        const auto relative = file.get<std::string>();
        if (!controlled_log_files.contains(relative)) throw RunnerError("uncontrolled XSE log file");
        const auto path = root / fs::path(relative);
        fs::create_directories(path.parent_path());
        std::ofstream output(path, std::ios::binary);
        output.close();
        if (!output) throw RunnerError("cannot seed XSE log");
    }
    // Relative folders must resolve inside the owned root. The version registry the resolver
    // consults initializes lazily on its first call, which therefore also happens in that root.
    XseLogWorkingDirectory cwd(root);
    try {
        auto log = owned_string(classic::xse::resolve_xse_log_for_scan(root.string(), game,
            fixture.at("selectedVersion").get<std::string>(), fixture.at("configuredDocs").get<std::string>()));
        std::replace(log.begin(), log.end(), '\\', '/');
        return json{{"log", log.empty() ? json(nullptr) : json(log)}, {"error", nullptr}};
    } catch (const rust::Error& error) {
        if (!std::string_view(error.what()).starts_with("cannot inspect XSE log ")) throw;
        return json{{"log", nullptr}, {"error", "inspect"}};
    }
}

/// Dispatches XSE folder scenarios; only `xse-folder.log` still runs on CXX.
///
/// `xse-folder.resolve` left CXX with the folder-resolution export it called (#309).
json execute_xse_folder_scenario(const json& plan, const json& scenario) {
    if (scenario.at("action").get<std::string>() != "xse-folder.log") {
        throw RunnerError("unsupported xse-folder action");
    }
    return execute_xse_log_scenario(plan, scenario);
}
