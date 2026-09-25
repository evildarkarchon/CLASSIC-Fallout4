// Positive issue fixtures exercise every fail-soft checker and orchestration getter.
namespace {

/// Execute both APIs and compare each summary count against native issue/plugin vectors.
json execute_crashgen_check(const json& plan,const json& scenario){
    if(scenario.at("action")!="crashgen-check.check")throw RunnerError("unsupported Crashgen action");
    const auto reference=scenario.at("input").at("fixtureRef").get<std::string>();const auto& refs=scenario.at("fixtureRefs");if(std::find(refs.begin(),refs.end(),reference)==refs.end())throw RunnerError("undeclared Crashgen fixture");
    std::ifstream input(plan.at("fixtures").at(reference).get<std::string>(),std::ios::binary);const auto fixture=json::parse(input);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),scenario.at("id").get<std::string>());const auto root=temporary.path();
    for(const auto&[name,content]:fixture.at("files").items()){
        const auto relative=std::filesystem::path(name);if(relative.is_absolute()||name.find(':')!=std::string::npos||name.find('\\')!=std::string::npos)throw RunnerError("invalid Crashgen path");for(const auto& part:relative)if(part==".."||part==".")throw RunnerError("invalid Crashgen path");
        const auto path=root/relative;std::filesystem::create_directories(path.parent_path());std::ofstream file(path,std::ios::binary);file<<content.get<std::string>();file.close();if(!file)throw RunnerError("cannot materialize Crashgen fixture");
    }
    const auto inventory=[&](){std::map<std::string,std::string> files;for(const auto& entry:std::filesystem::recursive_directory_iterator(root))if(entry.is_regular_file()){std::ifstream file(entry.path(),std::ios::binary);files[std::filesystem::relative(entry.path(),root).generic_string()]=std::string(std::istreambuf_iterator<char>(file),{});}json result=json::array();for(const auto&[path,content]:files)result.push_back({{"path",path},{"content",content}});return result;};
    const auto project=[&](const auto& values){json result=json::array();for(const auto& value:values){std::string severity;switch(value.severity){case classic::scangame::TomlIssueSeverity::Info:severity="Info";break;case classic::scangame::TomlIssueSeverity::Warning:severity="Warning";break;case classic::scangame::TomlIssueSeverity::Error:severity="Error";break;default:throw RunnerError("unknown TOML severity");}result.push_back({{"path",std::filesystem::relative(std::string(value.file_path),root).generic_string()},{"section",std::string(value.section)},{"setting",std::string(value.setting)},{"current",std::string(value.current_value)},{"recommended",std::string(value.recommended_value)},{"description",std::string(value.description)},{"severity",severity}});}return result;};
    const auto before=inventory();const auto checker=classic::scangame::crashgen_checker_check(root.string(),"Buffout4");const auto values=classic::scangame::crashgen_checker_get_issues(root.string(),"Buffout4");const auto report=classic::scangame::crashgen_orchestrator_check_summary(root.string(),"Buffout4");const auto orchestrated=classic::scangame::crashgen_orchestrator_get_issues(root.string(),"Buffout4");const auto native_plugins=classic::scangame::crashgen_orchestrator_get_installed_plugins(root.string(),"Buffout4");
    auto plugins=semantic_string_values(native_plugins);std::sort(plugins.begin(),plugins.end());const auto issues=project(values);
    if(std::string(checker.report_text)!=std::string(report.message)||checker.issue_count!=values.size()||report.issue_count!=orchestrated.size()||project(orchestrated)!=issues||report.installed_plugin_count!=native_plugins.size()||report.has_config_path!=!report.config_path_or_empty.empty())throw RunnerError("Crashgen summaries disagree with native vectors");
    const json config=report.has_config_path?json(std::filesystem::relative(std::string(report.config_path_or_empty),root).generic_string()):json(nullptr);
    return {{"message",std::string(report.message)},{"issues",issues},{"name",std::string(report.crashgen_name)},{"config",config},{"plugins",plugins},{"beforeFiles",before},{"files",inventory()}};
}
}
