// Input-only reconstruction of Wrye issue rows from the actual public bridge.
namespace {

/// Retains the known native severity vocabulary and rejects future unmapped variants.
std::string wrye_severity(classic::scangame::WryeSeverity value) {
    switch(value) {
    case classic::scangame::WryeSeverity::Info:return "Info";
    case classic::scangame::WryeSeverity::Warning:return "Warning";
    case classic::scangame::WryeSeverity::Error:return "Error";
    default:throw RunnerError("unknown Wrye severity");
    }
}

/// Reconstructs grouped issues, including no-plugin sentinel rows, without an oracle.
json execute_wrye_report(const json& plan,const json& scenario) {
    if(scenario.at("action")!="wrye-report.parse")throw RunnerError("CXX has no Wrye formatter export");
    const auto reference=scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& refs=scenario.at("fixtureRefs");
    if(std::find(refs.begin(),refs.end(),reference)==refs.end())throw RunnerError("undeclared Wrye fixture");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(),std::ios::binary);
    const auto fixture=json::parse(stream);
    rust::Vec<rust::String> keys;rust::Vec<rust::String> values;
    for(const auto& [key,value]:fixture.at("warnings").items()){keys.push_back(key);values.push_back(value.get<std::string>());}
    const auto rows=classic::scangame::wrye_parse_html_rows(fixture.at("html").get<std::string>(),
        rust::Slice<const rust::String>(keys.data(),keys.size()),rust::Slice<const rust::String>(values.data(),values.size()));
    json issues=json::array();
    for(const auto& row:rows) {
        const json warning=row.has_warning_message ? json(owned_string(row.warning_message_or_empty)) : json(nullptr);
        const auto section=owned_string(row.section_title);const auto severity=wrye_severity(row.severity);
        if(row.issue_index>issues.size())throw RunnerError("Wrye bridge skipped an issue index");
        if(row.issue_index==issues.size())issues.push_back(json{{"section",section},{"plugins",json::array()},{"warning",warning},{"severity",severity}});
        auto& issue=issues.at(row.issue_index);
        if(issue.at("section")!=section || issue.at("warning")!=warning || issue.at("severity")!=severity)throw RunnerError("inconsistent flattened Wrye issue metadata");
        const auto plugin=owned_string(row.plugin);if(!plugin.empty())issue["plugins"].push_back(plugin);
    }
    return json{{"issues",issues}};
}
}
