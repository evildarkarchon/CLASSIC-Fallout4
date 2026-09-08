// Input-only Papyrus monitoring through the public CXX bridge.
namespace {

/// Projects all portable counters transported by the actual native bridge DTO.
json papyrus_stats(const scanner::PapyrusStatsDto& stats) {
    std::ostringstream ratio;
    ratio << std::fixed << std::setprecision(3) << stats.dumps_stacks_ratio;
    return json{{"dumps",stats.dumps},{"stacks",stats.stacks},{"warnings",stats.warnings},
                {"errors",stats.errors},{"lines",stats.lines_processed},{"ratio",ratio.str()}};
}

/// Executes full, tail, incremental, idle and reset operations in an owned directory.
json execute_papyrus_monitor(const json& plan, const json& scenario) {
    const auto reference=scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references=scenario.at("fixtureRefs");
    if (std::find(references.begin(),references.end(),reference)==references.end()) throw RunnerError("undeclared Papyrus fixture");
    if (scenario.at("action")!="papyrus-monitor.observe") throw RunnerError("unsupported Papyrus action");
    std::ifstream input(plan.at("fixtures").at(reference).get<std::string>(),std::ios::binary);
    const auto fixture=json::parse(input);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),scenario.at("id").get<std::string>());
    const auto path=temporary.path()/"Papyrus.0.log";
    if (!fixture.at("content").is_null()) {
        std::ofstream output(path,std::ios::binary);
        output << fixture.at("content").get<std::string>();
        output.close();
        if (!output) throw RunnerError("cannot materialize Papyrus input");
    }
    auto analyzer=scanner::papyrus_analyzer_new(path.string());
    const bool exists=scanner::papyrus_log_exists(*analyzer);
    json result{{"exists",exists},{"error",nullptr},{"initial",nullptr},{"tailStart",nullptr},
                {"updated",nullptr},{"idle",nullptr},{"afterReset",nullptr},{"finalContent",nullptr}};
    try { result["initial"]=papyrus_stats(scanner::papyrus_analyze_full(*analyzer)); }
    catch (const rust::Error&) {
        if (exists) throw;
        result["error"]="missing";
        return result;
    }
    scanner::papyrus_start_monitoring(*analyzer);
    result["tailStart"]=papyrus_stats(scanner::papyrus_check_updates(*analyzer));
    std::ofstream appended(path,std::ios::binary|std::ios::app);
    appended << fixture.at("append").get<std::string>();
    appended.close();
    if (!appended) throw RunnerError("cannot append Papyrus input");
    result["updated"]=papyrus_stats(scanner::papyrus_check_updates(*analyzer));
    result["idle"]=papyrus_stats(scanner::papyrus_check_updates(*analyzer));
    scanner::papyrus_reset(*analyzer);
    result["afterReset"]=papyrus_stats(scanner::papyrus_analyze_full(*analyzer));
    std::ifstream final_file(path,std::ios::binary);
    result["finalContent"]=std::string(std::istreambuf_iterator<char>(final_file),{});
    return result;
}
}
