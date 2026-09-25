// Public validator observations through the generated settings bridge.

#include <charconv>
#include <cmath>

/// Preserve shortest round-trip digits with the same scientific exponent spelling as Rust.
std::string settings_float_text(double value) {
    if (std::isnan(value)) return "NaN";
    if (std::isinf(value)) return value < 0 ? "-inf" : "inf";
    char buffer[64];
    const auto result = std::to_chars(buffer, buffer + sizeof(buffer), value, std::chars_format::scientific);
    if (result.ec != std::errc{}) throw RunnerError("cannot format coerced float");
    const std::string formatted(buffer, result.ptr);
    const auto exponent = formatted.find('e');
    if (exponent == std::string::npos) throw RunnerError("missing scientific float exponent");
    return formatted.substr(0, exponent + 1) + std::to_string(std::stoi(formatted.substr(exponent + 1)));
}

/// Preserve the public tagged coerced value without parsing values in the adapter.
json execute_settings_validation_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("settings validation fixture is not declared");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const auto fixture = json::parse(stream);
    json results = json::array();
    for (const auto& item : fixture.at("cases")) {
        const auto input = item.at("value").get<std::string>();
        const auto type = item.at("type").get<std::string>();
        const bool valid = classic::settings::settings_validate_value(input, type);
        json value = nullptr;
        json error = nullptr;
        try {
            const auto native = classic::settings::settings_coerce_value(input, type);
            const auto kind = std::string(native.kind);
            if (kind == "int") value = native.int_val;
            else if (kind == "float") {
                // Receipt JSON excludes floating numbers; retain the numeric kind explicitly.
                value = json{{"float", settings_float_text(native.float_val)}};
            }
            else if (kind == "bool") value = native.bool_val;
            else if (kind == "string" || kind == "path") value = std::string(native.string_val);
            else throw RunnerError("unknown coerced settings value kind");
        } catch (const rust::Error& failure) {
            error = std::string(failure.what());
        }
        results.push_back(json{{"valid", valid}, {"value", value}, {"error", error}});
    }
    return json{{"results", results}};
}
