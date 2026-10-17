// Original default bridge entry points retain separately proved negative runtime boundaries.

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
    // `update-rejection.latest` left CXX with the binary-release check it called (#309).
    throw RunnerError("unsupported CXX rejection operation");
}
