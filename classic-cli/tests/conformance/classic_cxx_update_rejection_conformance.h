// Original default bridge entry points retain separately proved negative runtime boundaries.

/// Restore the caller environment after injecting an intentionally invalid test credential.
class SyntheticGithubCredential {
    std::optional<std::string> previous_;
public:
    /// A newline is rejected by reqwest while building the Authorization header.
    explicit SyntheticGithubCredential(const std::string& token) : previous_(read_environment("GITHUB_TOKEN")) {
        if (token != "synthetic\ninvalid") throw RunnerError("only synthetic malformed credentials are permitted");
        set_environment("GITHUB_TOKEN", token);
    }
    /// Preserve external environment even when an assertion throws.
    ~SyntheticGithubCredential() {
        try { set_environment("GITHUB_TOKEN", previous_); }
        catch (...) { /* The dedicated test process exits; cleanup must not throw during unwinding. */ }
    }
};

/// Call unconfigured public APIs and require exact errors produced before transport/cache setup.
json execute_update_rejection_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    const auto operation = fixture.at("operation").get<std::string>();
    const auto owner = fixture.at("owner").get<std::string>();
    const auto repo = fixture.at("repo").get<std::string>();
    if (operation == "notification") {
        const auto result = classic::update::check_app_notification(owner, repo, fixture.at("invalidVersion").get<std::string>());
        if (std::string(result.classification) != "error" || !std::string(result.error_message).starts_with("installed version `invalid` is not a valid semver:"))
            throw RunnerError("invalid installed version did not fail at the caller boundary");
        return json{{"boundary", "caller-validation"}, {"error", "invalid-installed-version"}, {"requestBuilt", false}};
    }
    if (operation != "latest") throw RunnerError("unsupported CXX rejection operation");
    SyntheticGithubCredential credential(fixture.at("token").get<std::string>());
    const auto result = classic::update::github_check_for_updates(owner, repo, fixture.at("currentVersion").get<std::string>());
    if (std::string(result.error_message) != "HTTP error: builder error" || result.has_update || !result.latest_version.empty() || !result.release_notes.empty())
        throw RunnerError("expected request-builder rejection, not success or a transport failure");
    return json{{"boundary", "request-builder"}, {"error", "builder-error"}, {"requestBuilt", false}};
}
