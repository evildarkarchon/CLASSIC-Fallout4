// SPDX-License-Identifier: MIT
// Explicit samples exercise public formatted and numeric performance projections.

/// Clear global state when a scenario exits, including exception unwinding.
class PerformanceCleanup final {
public:
    PerformanceCleanup() { classic::perf::perf_clear_metrics(); }
    ~PerformanceCleanup() { classic::perf::perf_clear_metrics(); }
    PerformanceCleanup(const PerformanceCleanup&) = delete;
    PerformanceCleanup& operator=(const PerformanceCleanup&) = delete;
};

/// Require exact authored millisecond values without tolerance or rounding.
std::uint64_t performance_milliseconds(double seconds) {
    const auto value = seconds * 1000.0;
    if (!std::isfinite(value) || value < 0.0 || value > 9007199254740991.0 || std::floor(value) != value) {
        throw RunnerError("metric duration is not an exact integer millisecond");
    }
    return static_cast<std::uint64_t>(value);
}

/// Convert native whole-nanosecond seconds without hiding non-integral drift.
std::uint64_t performance_nanoseconds(double seconds) {
    const auto value = seconds * 1e9;
    const auto rounded = std::round(value);
    if (!std::isfinite(value) || value < 0.0 || std::abs(value - rounded) > 1e-3) {
        throw RunnerError("metric duration is not a whole nanosecond");
    }
    return static_cast<std::uint64_t>(rounded);
}

/// Read the seconds spelling of a dual-unit fixture sample.
double performance_sample_seconds(const json& operation) {
    if (operation.size() != 4 || !operation.at("label").is_string() || !operation.at("seconds").is_number()
        || !operation.at("milliseconds").is_number()) {
        throw RunnerError("unsupported dual-unit sample");
    }
    return operation.at("seconds").get<double>();
}

/// Return the stable core token that prefixes a bridge `rust::Error` message.
std::string performance_rejection_token(const rust::Error& failure) {
    const std::string message = failure.what();
    const auto separator = message.find(": ");
    if (separator == std::string::npos || separator == 0) throw RunnerError("rejected sample lacks a stable token");
    return message.substr(0, separator);
}

/// Labels currently present in the formatted summary carrier.
std::vector<std::string> performance_labels() {
    std::vector<std::string> labels;
    for (const auto& raw : classic::perf::perf_get_summary()) {
        const auto line = owned_string(raw);
        const auto separator = line.find(": count=");
        if (separator == std::string::npos) throw RunnerError("unsupported performance summary carrier");
        labels.push_back(line.substr(0, separator));
    }
    return labels;
}

/// Project single-sample nanosecond averages through the numeric accessors.
json performance_nanosecond_snapshot() {
    json snapshot = json::object();
    for (const auto& label : performance_labels()) {
        snapshot[label] = json{{"count", classic::perf::perf_get_operation_count(label)},
            {"averageNs", performance_nanoseconds(classic::perf::perf_get_operation_average(label))}};
    }
    return snapshot;
}

/// Parse the bridge's fixed formatted carrier and cross-check numeric projections.
json performance_snapshot() {
    json snapshot = json::object();
    const std::regex pattern(R"(^([^:]+): count=([0-9]+), total=([0-9]+\.[0-9]{3})s, avg=([0-9]+\.[0-9]{3})s, min=([0-9]+\.[0-9]{3})s, max=([0-9]+\.[0-9]{3})s$)");
    for (const auto& raw : classic::perf::perf_get_summary()) {
        const auto line = owned_string(raw);
        std::smatch match;
        if (!std::regex_match(line, match, pattern)) throw RunnerError("unsupported performance summary carrier");
        const auto label = match[1].str();
        const auto count = std::stoull(match[2].str());
        const auto average = performance_milliseconds(std::stod(match[4].str()));
        if (snapshot.contains(label) || classic::perf::perf_get_operation_count(label) != count
            || performance_milliseconds(classic::perf::perf_get_operation_average(label)) != average) {
            throw RunnerError("performance summary and numeric projections disagree");
        }
        snapshot[label] = json{{"count", count}, {"totalMs", performance_milliseconds(std::stod(match[3].str()))},
            {"averageMs", average}, {"minMs", performance_milliseconds(std::stod(match[5].str()))},
            {"maxMs", performance_milliseconds(std::stod(match[6].str()))}};
    }
    if (classic::perf::perf_get_operation_count("unrecorded") != 0
        || classic::perf::perf_get_operation_average("unrecorded") != 0.0) {
        throw RunnerError("missing metric must have zero numeric projections");
    }
    return snapshot;
}

/// Execute explicit clear/record/summary operations in the dedicated serial runner.
json execute_performance_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    if (scenario.at("fixtureRefs") != json::array({reference})) throw RunnerError("undeclared performance fixture");
    std::ifstream stream(plan.at("fixtures").at(reference).get<std::string>(), std::ios::binary);
    const json fixture = json::parse(stream);
    if (fixture.size() != 1 || !fixture.at("operations").is_array()) throw RunnerError("unsupported performance fixture");
    PerformanceCleanup cleanup;
    json snapshots = json::array();
    json rejections = json::array();
    for (const auto& operation : fixture.at("operations")) {
        const auto op = operation.at("op").get<std::string>();
        if (op == "clear" && operation.size() == 1) classic::perf::perf_clear_metrics();
        else if (op == "summary" && operation.size() == 1) snapshots.push_back(performance_snapshot());
        else if (op == "summaryNs" && operation.size() == 1) snapshots.push_back(performance_nanosecond_snapshot());
        else if (op == "sample") {
            classic::perf::perf_record_timing(operation.at("label").get<std::string>(), performance_sample_seconds(operation));
        } else if (op == "reject") {
            const auto seconds = performance_sample_seconds(operation);
            bool accepted = false;
            // Only the bridge's rust::Error counts as the documented rejection.
            try {
                classic::perf::perf_record_timing(operation.at("label").get<std::string>(), seconds);
                accepted = true;
            } catch (const rust::Error& failure) {
                rejections.push_back(performance_rejection_token(failure));
            }
            if (accepted) throw RunnerError("invalid sample was accepted");
        }
        else if (op == "record" && operation.size() == 3 && operation.at("label").is_string()
                 && operation.at("durationMs").is_number_integer() && operation.at("durationMs") >= 0
                 && operation.at("durationMs") <= 1000000) {
            classic::perf::perf_record_timing(operation.at("label").get<std::string>(), operation.at("durationMs").get<double>() / 1000.0);
        } else throw RunnerError("unsupported performance operation");
    }
    return json{{"snapshots", snapshots}, {"rejections", rejections}};
}
