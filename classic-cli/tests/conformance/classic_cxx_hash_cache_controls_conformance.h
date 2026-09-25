// CXX exposes cache controls but no public hash-population operation.
namespace {

/// Projects all fields returned by the actual public cache-statistics DTO.
json controlled_hash_stats(){
    const auto value=classic::files::hash_cache_stats();std::ostringstream ratio;ratio<<std::fixed<<std::setprecision(3)<<value.hit_rate;
    return json{{"hits",value.hits},{"misses",value.misses},{"hitRate",ratio.str()},{"size",value.size},{"capacity",value.capacity}};
}

/// Verifies empty-state idempotence through actual CXX controls, without synthetic seeding.
json execute_hash_cache_controls(const json& plan,const json& scenario){
    if(scenario.at("action")!="hash-cache-controls.empty")throw RunnerError("unsupported cache-control action");
    const auto reference=scenario.at("input").at("fixtureRef").get<std::string>();const auto& refs=scenario.at("fixtureRefs");if(std::find(refs.begin(),refs.end(),reference)==refs.end())throw RunnerError("undeclared cache-control fixture");
    std::ifstream input(plan.at("fixtures").at(reference).get<std::string>(),std::ios::binary);if(json::parse(input).at("operation")!="empty-controls")throw RunnerError("unsupported cache-control fixture");
    classic::files::hash_cache_clear();classic::files::reset_hash_cache_stats();const auto initial=controlled_hash_stats();const auto size=classic::files::hash_cache_size();
    classic::files::reset_hash_cache_stats();const auto reset=controlled_hash_stats();classic::files::hash_cache_clear();
    return json{{"initial",initial},{"initialSize",size},{"afterReset",reset},{"afterClear",controlled_hash_stats()},{"finalSize",classic::files::hash_cache_size()}};
}
}
