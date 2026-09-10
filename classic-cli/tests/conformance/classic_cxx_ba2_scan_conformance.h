// Every fail-soft bridge issue-vector getter receives a positive-data fixture.
namespace {

/// Executes all actual per-archive getters and cross-checks the native aggregate summary.
json execute_ba2_scan(const json& plan,const json& scenario){
    if(scenario.at("action")!="ba2-scan.bridge")throw RunnerError("CXX exposes only per-archive BA2 views");
    const auto reference=scenario.at("input").at("fixtureRef").get<std::string>();const auto& refs=scenario.at("fixtureRefs");if(std::find(refs.begin(),refs.end(),reference)==refs.end())throw RunnerError("undeclared BA2 fixture");
    std::ifstream input(plan.at("fixtures").at(reference).get<std::string>(),std::ios::binary);const auto fixture=json::parse(input);
    TemporaryDirectory temporary(plan.at("invocation").at("id").get<std::string>(),scenario.at("id").get<std::string>());const auto path=temporary.path()/"fixture.ba2";
    const auto bytes=fixture.at("bytes").get<std::vector<std::uint8_t>>();std::ofstream file(path,std::ios::binary);file.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));file.close();if(!file)throw RunnerError("cannot materialize BA2 input");
    const auto dimensions=classic::scangame::ba2_get_tex_dims_for_archive(path.string());const auto formats=classic::scangame::ba2_get_tex_frmt_for_archive(path.string());const auto sounds=classic::scangame::ba2_get_snd_frmt_for_archive(path.string());const auto scripts=classic::scangame::ba2_get_xse_files_for_archive(path.string());
    const auto summary=classic::scangame::ba2_scan_archive_summary(path.string());const auto total=dimensions.size()+formats.size()+sounds.size()+scripts.size();
    if(summary.tex_dim_count!=dimensions.size() || summary.tex_fmt_count!=formats.size() || summary.snd_fmt_count!=sounds.size() || summary.xse_file_count!=scripts.size() || summary.total!=total || summary.has_issues!=(total>0))throw RunnerError("BA2 summary disagrees with native vectors");
    std::ifstream after(path,std::ios::binary);std::vector<std::uint8_t> durable((std::istreambuf_iterator<char>(after)),{});
    return json{{"issues",{{"dimensions",semantic_string_values(dimensions)},{"formats",semantic_string_values(formats)},{"sounds",semantic_string_values(sounds)},{"scripts",semantic_string_values(scripts)}}},{"bytes",durable}};
}
}
