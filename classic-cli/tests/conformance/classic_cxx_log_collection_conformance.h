// Native CXX log collection with complete two-stage durable inventories.
namespace {

/// Writes only contained fixture files before a native collection stage.
void collection_materialize(const fs::path& root,const json& values){
    for(const auto& [path,content]:values.items()){
        const auto target=file_operation_path(root,path);fs::create_directories(target.parent_path());
        std::ofstream output(target,std::ios::binary|std::ios::trunc);output<<content.get<std::string>();output.close();
        if(!output)throw RunnerError("cannot materialize collection input");
    }
}

/// Converts actual bridge paths to a stable root-relative set.
json collection_paths(const fs::path& root,const rust::Vec<rust::String>& paths){
    std::vector<std::string> result;
    for(const auto& path:paths)result.push_back(fs::path(owned_string(path)).lexically_relative(root).generic_string());
    std::sort(result.begin(),result.end());return json(result);
}

/// Executes both public collection entrypoints and verifies staged native move/copy effects.
json execute_log_collection(const json& plan,const json& scenario){
    if(scenario.at("action")!="log-collection.collect" && scenario.at("action")!="log-collection.configured")throw RunnerError("unsupported collection action");
    const auto reference=scenario.at("input").at("fixtureRef").get<std::string>();const auto& refs=scenario.at("fixtureRefs");
    if(std::find(refs.begin(),refs.end(),reference)==refs.end())throw RunnerError("undeclared collection fixture");
    std::ifstream input(plan.at("fixtures").at(reference).get<std::string>(),std::ios::binary);const auto fixture=json::parse(input);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),scenario.at("id").get<std::string>());const auto root=temporary.path();
    for(const auto* folder:{"base","xse","custom"})fs::create_directory(root/folder);
    collection_materialize(root,fixture.at("files"));
    TemporaryDirectory yaml_root(plan.at("invocation").at("id").get<std::string>(),scenario.at("id").get<std::string>()+"-yaml");
    const auto collector=[&](){
        if(fixture.value("configured",false)){
            // Explicit local YAML prevents ambient game discovery; bootstrap bytes contain an invocation path.
            std::ofstream yaml(yaml_root.path()/"CLASSIC Fallout4 Local.yaml",std::ios::binary);
            yaml<<"Game_Info:\n  Docs_Folder_XSE: "<<json((root/"xse").string()).dump()<<"\n";yaml.close();
            if(!yaml)throw RunnerError("cannot write collection bootstrap YAML");
            return classic::files::log_collector_new_for_scan((root/"base").string(),yaml_root.path().string(),"Fallout4","OG","",(root/"custom").string());
        }
        return classic::files::log_collector_new((root/"base").string(),(root/"xse").string(),(root/"custom").string());
    }();
    json result{{"before",file_operation_files(root)},{"first",collection_paths(root,classic::files::log_collector_collect_all(*collector))}};
    if(collection_paths(root,classic::files::log_collector_collect_crash_logs(*collector))!=result.at("first"))throw RunnerError("crash discovery changed full results");
    result["afterFirst"]=file_operation_files(root);collection_materialize(root,fixture.at("later"));
    result["second"]=collection_paths(root,classic::files::log_collector_collect_all(*collector));
    if(collection_paths(root,classic::files::log_collector_collect_crash_logs(*collector))!=result.at("second"))throw RunnerError("second crash discovery changed full results");
    result["files"]=file_operation_files(root);
    rust::Vec<rust::String> targeted;
    for(const auto& path:result.at("second"))targeted.push_back((root/path.get<std::string>()).string());
    targeted.push_back((root/"missing-target.log").string());
    const auto resolved=classic::files::resolve_targeted_inputs(rust::Slice<const rust::String>(targeted.data(),targeted.size()));
    if(collection_paths(root,resolved.logs)!=result.at("second") || resolved.rejected_paths.size()!=1 ||
       fs::path(owned_string(resolved.rejected_paths[0]))!=root/"missing-target.log" ||
       resolved.rejected_reasons.size()!=1 || owned_string(resolved.rejected_reasons[0])!="path does not exist") {
        throw RunnerError("targeted resolver changed accepted paths or missing-path rejection");
    }
    if(file_operation_files(root)!=result.at("files"))throw RunnerError("targeted resolver changed owned files");
    return result;
}
}
