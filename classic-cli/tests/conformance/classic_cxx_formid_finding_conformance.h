// Complete native FormID Finding factory/status/result traversal.
namespace {

/// Preserves the exact typed lookup outcome independently of optional payload fields.
std::string finding_lookup_status(scanner::FormIDValueLookupStatus status){
    switch(status){case scanner::FormIDValueLookupStatus::NotApplicable:return "not_applicable";case scanner::FormIDValueLookupStatus::Disabled:return "disabled";case scanner::FormIDValueLookupStatus::Missing:return "missing";case scanner::FormIDValueLookupStatus::Found:return "found";default:throw RunnerError("unknown finding lookup status");}
}

/// Retains native error code/message and checks the analyzer identity before projection.
json finding_error(const std::string& mode,const scanner::AnalyzerErrorDto& error){
    const auto projected=semantic_error(error);if(projected.at("analyzerKind")!="formid_finding")throw RunnerError("incorrect native FormID error identity");
    return json{{"mode",mode},{"findings",nullptr},{"error",{{"code",projected.at("code")},{"message",projected.at("message")}}}};
}

/// Executes public disabled, memory and SQLite factories and the aggregate analyze operation.
json execute_formid_finding(const json& plan,const json& scenario){
    if(scenario.at("action")!="formid-finding.analyze" && scenario.at("action")!="formid-finding.sqlite")throw RunnerError("unsupported FormID Finding action");
    const auto reference=scenario.at("input").at("fixtureRef").get<std::string>();const auto& refs=scenario.at("fixtureRefs");if(std::find(refs.begin(),refs.end(),reference)==refs.end())throw RunnerError("undeclared FormID Finding fixture");
    std::ifstream input_stream(plan.at("fixtures").at(reference).get<std::string>(),std::ios::binary);const auto fixture=json::parse(input_stream);const auto mode=fixture.at("mode").get<std::string>();
    if((mode=="sqlite-missing")!=(scenario.at("action")=="formid-finding.sqlite"))throw RunnerError("FormID factory mode disagrees with action");
    const auto analyzer=[&](){
        if(mode=="disabled")return scanner::formid_finding_analyzer_disabled_new();
        if(mode=="sqlite-missing"){
            const auto path=fixture.at("databasePath").get<std::string>();if(fs::exists(path))throw RunnerError("missing SQLite path unexpectedly exists");return scanner::formid_finding_analyzer_sqlite_new(path,"Fallout4");
        }
        if(mode!="in-memory")throw RunnerError("unknown FormID factory mode");
        rust::Vec<scanner::FormIDFindingLookupEntryDto> entries;
        for(const auto& value:fixture.at("entries")){
            scanner::FormIDFindingLookupEntryDto entry{};entry.formid=value.at("formid").get<std::string>();entry.plugin=value.at("plugin").get<std::string>();
            if(value.contains("failure")&&!value.at("failure").is_null()){entry.reply_kind=scanner::FormIDFindingLookupReplyKind::OperationalFailure;entry.error_message=value.at("failure").get<std::string>();}
            else if(value.contains("value")&&!value.at("value").is_null()){entry.reply_kind=scanner::FormIDFindingLookupReplyKind::Found;entry.value=value.at("value").get<std::string>();}
            else entry.reply_kind=scanner::FormIDFindingLookupReplyKind::Missing;
            entries.push_back(std::move(entry));
        }
        return scanner::formid_finding_analyzer_in_memory_new(std::move(entries));
    }();
    const auto construction=scanner::formid_finding_analyzer_construction_result(*analyzer);if(construction.has_analyzer==construction.has_error)throw RunnerError("invalid FormID constructor sum");if(construction.has_error)return finding_error(mode,construction.error);
    if(mode=="sqlite-missing")throw RunnerError("missing SQLite analyzer unexpectedly constructed");
    scanner::FormIDFindingAnalysisInputDto request{};request.crash_lines=semantic_strings(fixture.at("lines"));
    for(const auto& value:fixture.at("plugins")){scanner::FormIDPluginDto plugin{};plugin.name=value.at("name").get<std::string>();plugin.prefix=value.at("prefix").get<std::string>();request.plugins.push_back(std::move(plugin));}
    const auto execution=scanner::formid_finding_analyze(*analyzer,std::move(request));if(execution.has_result==execution.has_error)throw RunnerError("invalid FormID execution sum");if(execution.has_error)return finding_error(mode,execution.error);
    json findings=json::array();for(const auto& finding:execution.result.findings)findings.push_back(json{{"identifier",owned_string(finding.identifier)},{"occurrences",finding.occurrences},{"plugin",semantic_optional(finding.has_plugin,finding.plugin)},{"status",finding_lookup_status(finding.value_lookup_status)},{"value",semantic_optional(finding.has_value,finding.value)}});
    return json{{"mode",mode},{"findings",findings},{"error",nullptr}};
}
}
