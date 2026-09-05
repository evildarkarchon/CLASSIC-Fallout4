// SPDX-License-Identifier: MIT
// Native DTO traversal for the focused semantic families, included inside the runner namespace.

/// Converts an input string array into an owned bridge vector.
rust::Vec<rust::String> semantic_strings(const json& values) {
    rust::Vec<rust::String> result;
    for (const auto& value : values)
        result.push_back(value.get<std::string>());
    return result;
}

/// Projects a bridge-owned string vector without relying on Rust JSON serialization.
json semantic_string_values(const rust::Vec<rust::String>& values) {
    json result = json::array();
    for (const auto& value : values)
        result.push_back(owned_string(value));
    return result;
}

/// Preserves the authoritative presence bit for a nullable bridge string.
json semantic_optional(bool present, const rust::String& value) {
    return present ? json(owned_string(value)) : json(nullptr);
}

/// Projects the analyzer identity exhaustively; unknown bridge variants fail execution.
std::string semantic_kind(scanner::AnalyzerKind kind) {
    switch (kind) {
    case scanner::AnalyzerKind::CrashSuspect:
        return "crash_suspect";
    case scanner::AnalyzerKind::CrashgenSettings:
        return "crashgen_settings";
    case scanner::AnalyzerKind::ModGuidance:
        return "mod_guidance";
    case scanner::AnalyzerKind::NamedRecordFinding:
        return "named_record_finding";
    case scanner::AnalyzerKind::PluginEvidence:
        return "plugin_evidence";
    case scanner::AnalyzerKind::FormIdFinding:
        return "formid_finding";
    default:
        throw RunnerError("unknown analyzer kind");
    }
}

/// Projects typed analyzer failures independently of the diagnostic text.
json semantic_error(const scanner::AnalyzerErrorDto& error) {
    std::string code;
    switch (error.code) {
    case scanner::AnalyzerErrorCode::InvalidConfiguration:
        code = "invalid_configuration";
        break;
    case scanner::AnalyzerErrorCode::UnsupportedConfigurationVersion:
        code = "unsupported_configuration_version";
        break;
    case scanner::AnalyzerErrorCode::MalformedResult:
        code = "malformed_result";
        break;
    case scanner::AnalyzerErrorCode::OperationalFailure:
        code = "operational_failure";
        break;
    default:
        throw RunnerError("unknown analyzer error code");
    }
    return json{
        {"analyzerKind", semantic_kind(error.analyzer_kind)}, {"code", code}, {"message", owned_string(error.message)}};
}

/// Enforces the result/error sum before converting a completed public operation.
template <class Execution, class Project>
json semantic_result(scanner::AnalyzerKind kind, const Execution& execution, Project project) {
    if (execution.has_result == execution.has_error)
        throw RunnerError("invalid analyzer result presence flags");
    return json{{"analyzerKind", semantic_kind(kind)},
                {"result", execution.has_result ? project(execution.result) : json(nullptr)},
                {"error", execution.has_error ? semantic_error(execution.error) : json(nullptr)}};
}

/// Checks the public constructor status before any analysis and preserves failures.
template <class Construction>
std::optional<json> semantic_construction(scanner::AnalyzerKind kind, const Construction& status) {
    if (status.has_analyzer == status.has_error)
        throw RunnerError("invalid analyzer constructor presence flags");
    if (status.has_error)
        return json{
            {"analyzerKind", semantic_kind(kind)}, {"result", nullptr}, {"error", semantic_error(status.error)}};
    return std::nullopt;
}

/// Projects authored mod match states without converting them to display labels.
std::string semantic_match_state(scanner::ModGuidanceMatchState state) {
    switch (state) {
    case scanner::ModGuidanceMatchState::Matched:
        return "matched";
    case scanner::ModGuidanceMatchState::Missing:
        return "missing";
    case scanner::ModGuidanceMatchState::GpuMismatch:
        return "gpu_mismatch";
    default:
        throw RunnerError("unknown mod guidance match state");
    }
}

/// Copies owned solution configuration through the generated CXX contract.
rust::Vec<scanner::ModGuidanceSolutionConfigurationDto> semantic_solutions(const json& values) {
    rust::Vec<scanner::ModGuidanceSolutionConfigurationDto> result;
    for (const auto& value : values) {
        scanner::ModGuidanceSolutionConfigurationDto entry{};
        entry.id = value.at("id").get<std::string>();
        const auto kind = value.at("criteriaKind").get<std::string>();
        if (kind != "any" && kind != "all")
            throw RunnerError("unknown criteriaKind");
        entry.criteria_kind =
            kind == "any" ? scanner::ModGuidanceCriteriaKind::Any : scanner::ModGuidanceCriteriaKind::All;
        entry.criteria = semantic_strings(value.at("criteria"));
        entry.exceptions = semantic_strings(value.at("exceptions"));
        entry.name = value.at("name").get<std::string>();
        entry.description = value.at("description").get<std::string>();
        result.push_back(std::move(entry));
    }
    return result;
}

/// Traverses every solution result field in native C++.
json semantic_solution_results(const rust::Vec<scanner::ModSolutionGuidanceDto>& values) {
    json result = json::array();
    for (const auto& v : values)
        result.push_back(json{{"state", semantic_match_state(v.state)},
                              {"id", owned_string(v.id)},
                              {"name", owned_string(v.name)},
                              {"description", owned_string(v.description)},
                              {"matchedPluginIds", semantic_string_values(v.matched_plugin_ids)}});
    return result;
}

/// Preserves the strict lookup error code and optional input-key context.
json semantic_lookup_error(const classic::database::FormIdValueLookupErrorDto& error) {
    namespace database = classic::database;
    std::string code;
    switch (error.code) {
    case database::FormIdValueLookupErrorCode::MalformedResult:
        code = "malformed_result";
        break;
    case database::FormIdValueLookupErrorCode::OperationalFailure:
        code = "operational_failure";
        break;
    default:
        throw RunnerError("unknown lookup error");
    }
    return json{{"analyzerKind", nullptr},
                {"result", nullptr},
                {"error", json{{"analyzerKind", nullptr},
                               {"code", code},
                               {"message", owned_string(error.message)},
                               {"formid", semantic_optional(error.has_formid, error.formid)},
                               {"plugin", semantic_optional(error.has_plugin, error.plugin)}}}};
}

/// Traverses the public outcome and verifies its returned key matches the requested position.
json semantic_lookup_outcome(const classic::database::FormIdValueLookupOutcomeDto& value, const json& request) {
    namespace database = classic::database;
    std::string kind;
    switch (value.kind) {
    case database::FormIdValueLookupOutcomeKind::Disabled:
        kind = "disabled";
        break;
    case database::FormIdValueLookupOutcomeKind::Missing:
        kind = "missing";
        break;
    case database::FormIdValueLookupOutcomeKind::Found:
        kind = "found";
        break;
    default:
        throw RunnerError("unknown lookup outcome");
    }
    if (owned_string(value.formid) != request.at("formid").get<std::string>() ||
        owned_string(value.plugin) != request.at("plugin").get<std::string>())
        throw RunnerError("lookup outcome key changed");
    return json{{"kind", kind}, {"value", kind == "found" ? json(owned_string(value.value)) : json(nullptr)}};
}

/// Executes a fixture against one reusable native handle, including optional warmup.
json execute_semantic_fixture(const std::string& family, const json& fixture) {
    const auto& c = fixture.at("configuration");
    const auto& request = fixture.at("request");
    if (family == "crash-suspect") {
        scanner::CrashSuspectAnalyzerConfigurationDto config{};
        for (const auto& v : c.at("mainErrorRules")) {
            scanner::CrashSuspectMainErrorRuleDto entry{};
            entry.id = v.at("id").get<std::string>();
            entry.name = v.at("name").get<std::string>();
            entry.severity = v.at("severity").get<std::int32_t>();
            entry.main_error_contains_any = semantic_strings(v.at("mainErrorContainsAny"));
            config.main_error_rules.push_back(std::move(entry));
        }
        for (const auto& v : c.at("stackRules")) {
            scanner::CrashSuspectStackRuleDto entry{};
            entry.id = v.at("id").get<std::string>();
            entry.name = v.at("name").get<std::string>();
            entry.severity = v.at("severity").get<std::int32_t>();
            entry.main_error_required_any = semantic_strings(v.at("mainErrorRequiredAny"));
            entry.main_error_optional_any = semantic_strings(v.at("mainErrorOptionalAny"));
            entry.stack_contains_any = semantic_strings(v.at("stackContainsAny"));
            entry.exclude_if_stack_contains_any = semantic_strings(v.at("excludeIfStackContainsAny"));
            for (const auto& count : v.at("stackContainsAtLeast"))
                entry.stack_contains_at_least.push_back(scanner::CrashSuspectStackCountRuleDto{
                    count.at("substring").get<std::string>(), count.at("count").get<std::size_t>()});
            config.stack_rules.push_back(std::move(entry));
        }
        const auto analyzer = scanner::crash_suspect_analyzer_new(std::move(config));
        if (const auto error = semantic_construction(scanner::AnalyzerKind::CrashSuspect,
                                                     scanner::crash_suspect_analyzer_construction_result(*analyzer)))
            return *error;
        // Warmup uses the same handle so state leakage into the observed empty call is detectable.
        const auto run = [&](const json& r) {
            return scanner::crash_suspect_analyze(
                *analyzer, scanner::CrashSuspectAnalysisInputDto{r.at("mainError").get<std::string>(),
                                                                 r.at("callStack").get<std::string>()});
        };
        if (fixture.contains("warmupRequest")) {
            const auto warmup = run(fixture.at("warmupRequest"));
            if (!warmup.has_result || warmup.has_error)
                throw RunnerError("crash suspect warmup failed");
        }
        return semantic_result(scanner::AnalyzerKind::CrashSuspect, run(request), [](const auto& result) {
            json findings = json::array();
            for (const auto& v : result.findings) {
                std::string kind;
                switch (v.kind) {
                case scanner::CrashSuspectFindingKind::MainErrorRule:
                    kind = "main_error_rule";
                    break;
                case scanner::CrashSuspectFindingKind::StackRule:
                    kind = "stack_rule";
                    break;
                case scanner::CrashSuspectFindingKind::DllInvolvement:
                    kind = "dll_involvement";
                    break;
                default:
                    throw RunnerError("unknown suspect finding kind");
                }
                findings.push_back(json{{"kind", kind},
                                        {"ruleId", semantic_optional(v.has_rule_id, v.rule_id)},
                                        {"name", semantic_optional(v.has_name, v.name)},
                                        {"severity", v.has_severity ? json(v.severity) : json(nullptr)}});
            }
            return json{{"findings", findings}};
        });
    }
    if (family == "named-record") {
        auto analyzer = scanner::named_record_finding_analyzer_new(scanner::NamedRecordFindingAnalyzerConfigurationDto{
            semantic_strings(c.at("targetRecords")), semantic_strings(c.at("ignoreRecords"))});
        if (const auto error =
                semantic_construction(scanner::AnalyzerKind::NamedRecordFinding,
                                      scanner::named_record_finding_analyzer_construction_result(*analyzer)))
            return *error;
        const auto run = [&](const json& r) {
            return scanner::named_record_finding_analyze(
                *analyzer, scanner::NamedRecordFindingAnalysisInputDto{semantic_strings(r.at("crashLines"))});
        };
        if (fixture.contains("warmupRequest")) {
            const auto warmup = run(fixture.at("warmupRequest"));
            if (!warmup.has_result || warmup.has_error)
                throw RunnerError("named record warmup failed");
        }
        return semantic_result(scanner::AnalyzerKind::NamedRecordFinding, run(request), [](const auto& result) {
            json values = json::array();
            for (const auto& v : result.findings)
                values.push_back(json{{"record", owned_string(v.record)}, {"occurrences", v.occurrences}});
            return json{{"findings", values}};
        });
    }
    if (family == "plugin-evidence") {
        auto analyzer = scanner::plugin_evidence_analyzer_new(
            scanner::PluginEvidenceAnalyzerConfigurationDto{semantic_strings(c.at("ignoredPlugins"))});
        if (const auto error = semantic_construction(scanner::AnalyzerKind::PluginEvidence,
                                                     scanner::plugin_evidence_analyzer_construction_result(*analyzer)))
            return *error;
        const auto run = [&](const json& r) {
            return scanner::plugin_evidence_analyze(
                *analyzer, scanner::PluginEvidenceAnalysisInputDto{semantic_strings(r.at("crashLines")),
                                                                   semantic_strings(r.at("plugins"))});
        };
        if (fixture.contains("warmupRequest")) {
            const auto warmup = run(fixture.at("warmupRequest"));
            if (!warmup.has_result || warmup.has_error)
                throw RunnerError("plugin evidence warmup failed");
        }
        return semantic_result(scanner::AnalyzerKind::PluginEvidence, run(request), [](const auto& result) {
            json values = json::array();
            for (const auto& v : result.evidence)
                values.push_back(json{{"plugin", owned_string(v.plugin)}, {"occurrences", v.occurrences}});
            return json{{"evidence", values}};
        });
    }
    if (family == "mod-guidance") {
        scanner::ModGuidanceAnalyzerConfigurationDto config{};
        for (const auto& v : c.at("conflicts")) {
            scanner::ModGuidanceConflictConfigurationDto entry{};
            entry.mod_a = v.at("modA").get<std::string>();
            entry.mod_b = v.at("modB").get<std::string>();
            entry.name_a = v.at("nameA").get<std::string>();
            entry.name_b = v.at("nameB").get<std::string>();
            entry.description = v.at("description").get<std::string>();
            entry.has_fix = !v.at("fix").is_null();
            if (entry.has_fix)
                entry.fix = v.at("fix").get<std::string>();
            entry.has_link = !v.at("link").is_null();
            if (entry.has_link)
                entry.link = v.at("link").get<std::string>();
            config.conflicts.push_back(std::move(entry));
        }
        config.frequent_crashes = semantic_solutions(c.at("frequentCrashes"));
        config.solutions = semantic_solutions(c.at("solutions"));
        for (const auto& v : c.at("importantMods")) {
            scanner::ModGuidanceImportantModConfigurationDto entry{};
            entry.detect = v.at("detect").get<std::string>();
            entry.name = v.at("name").get<std::string>();
            entry.description = v.at("description").get<std::string>();
            entry.has_gpu = !v.at("gpu").is_null();
            if (entry.has_gpu)
                entry.gpu = v.at("gpu").get<std::string>();
            entry.has_gpu_mismatch_warning = !v.at("gpuMismatchWarning").is_null();
            if (entry.has_gpu_mismatch_warning)
                entry.gpu_mismatch_warning = v.at("gpuMismatchWarning").get<std::string>();
            entry.has_exclude_when_plugin_any = !v.at("exclude").is_null();
            if (entry.has_exclude_when_plugin_any)
                entry.exclude_when_plugin_any = semantic_strings(v.at("exclude").at("pluginAny"));
            config.important_mods.push_back(std::move(entry));
        }
        auto analyzer = scanner::mod_guidance_analyzer_new(std::move(config));
        if (const auto error = semantic_construction(scanner::AnalyzerKind::ModGuidance,
                                                     scanner::mod_guidance_analyzer_construction_result(*analyzer)))
            return *error;
        scanner::ModGuidanceAnalysisInputDto input{};
        for (const auto& v : request.at("plugins"))
            input.plugins.push_back(
                scanner::ModGuidancePluginDto{v.at("name").get<std::string>(), v.at("id").get<std::string>()});
        input.has_user_gpu = !request.at("userGpu").is_null();
        if (input.has_user_gpu)
            input.user_gpu = request.at("userGpu").get<std::string>();
        input.xse_modules = semantic_strings(request.at("xseModules"));
        return semantic_result(
            scanner::AnalyzerKind::ModGuidance, scanner::mod_guidance_analyze(*analyzer, std::move(input)),
            [](const auto& result) {
                json conflicts = json::array(), important = json::array();
                for (const auto& v : result.conflicts)
                    conflicts.push_back(json{{"state", semantic_match_state(v.state)},
                                             {"modA", owned_string(v.mod_a)},
                                             {"modB", owned_string(v.mod_b)},
                                             {"nameA", owned_string(v.name_a)},
                                             {"nameB", owned_string(v.name_b)},
                                             {"description", owned_string(v.description)},
                                             {"fix", semantic_optional(v.has_fix, v.fix)},
                                             {"link", semantic_optional(v.has_link, v.link)}});
                for (const auto& v : result.important_mods)
                    important.push_back(json{
                        {"state", semantic_match_state(v.state)},
                        {"detect", owned_string(v.detect)},
                        {"name", owned_string(v.name)},
                        {"description", owned_string(v.description)},
                        {"gpu", semantic_optional(v.has_gpu, v.gpu)},
                        {"gpuMismatchWarning", semantic_optional(v.has_gpu_mismatch_warning, v.gpu_mismatch_warning)}});
                return json{{"conflicts", conflicts},
                            {"frequentCrashes", semantic_solution_results(result.frequent_crashes)},
                            {"solutions", semantic_solution_results(result.solutions)},
                            {"importantMods", important}};
            });
    }
    if (family == "crashgen-settings") {
        scanner::CrashgenSettingsAnalyzerConfigurationDto config{};
        const auto& entry = c.at("entry");
        config.crashgen_name = c.at("crashgenName").get<std::string>();
        config.display_section = entry.at("display_section").get<std::string>();
        config.ignore_keys = semantic_strings(entry.at("ignore_keys"));
        config.has_settings_rules = entry.contains("settings_rules") && !entry.at("settings_rules").is_null();
        if (config.has_settings_rules)
            config.settings_rules_json = entry.at("settings_rules").dump();
        config.has_settings_rules_version =
            entry.contains("settings_rules_version") && !entry.at("settings_rules_version").is_null();
        if (config.has_settings_rules_version)
            config.settings_rules_version = entry.at("settings_rules_version").get<std::uint32_t>();
        auto analyzer = scanner::crashgen_settings_analyzer_new(std::move(config));
        if (const auto error =
                semantic_construction(scanner::AnalyzerKind::CrashgenSettings,
                                      scanner::crashgen_settings_analyzer_construction_result(*analyzer)))
            return *error;
        const auto run = [&](const json& r) {
            scanner::CrashgenSettingsAnalysisInputDto input{};
            for (const auto& [section, values] : r.at("settings").items())
                for (const auto& [key, value] : values.items())
                    input.settings.push_back(scanner::CrashgenSettingDto{true, section, key, value.get<std::string>()});
            input.installed_plugins = semantic_strings(r.at("installedPlugins"));
            input.has_crashgen_version = !r.at("crashgenVersion").is_null();
            if (input.has_crashgen_version) {
                const auto& version = r.at("crashgenVersion");
                input.crashgen_version_major = version.at(0).get<std::uint32_t>();
                input.crashgen_version_minor = version.at(1).get<std::uint32_t>();
                input.crashgen_version_patch = version.at(2).get<std::uint32_t>();
            }
            const auto layout = r.at("configLayout").get<std::string>();
            if (layout == "og")
                input.config_layout = scanner::CrashgenConfigLayout::Og;
            else if (layout == "vr")
                input.config_layout = scanner::CrashgenConfigLayout::Vr;
            else if (layout == "unknown")
                input.config_layout = scanner::CrashgenConfigLayout::Unknown;
            else
                throw RunnerError("unknown crashgen layout");
            return scanner::crashgen_settings_analyze(*analyzer, std::move(input));
        };
        if (fixture.contains("warmupRequest")) {
            const auto warmup = run(fixture.at("warmupRequest"));
            if (!warmup.has_result || warmup.has_error)
                throw RunnerError("crashgen warmup failed");
        }
        return semantic_result(scanner::AnalyzerKind::CrashgenSettings, run(request), [](const auto& result) {
            json outcomes = json::array(), notices = json::array();
            for (const auto& v : result.expectation_outcomes) {
                std::string kind, severity, placement;
                switch (v.kind) {
                case scanner::CrashgenExpectationOutcomeKind::Notice:
                    kind = "notice";
                    break;
                case scanner::CrashgenExpectationOutcomeKind::Issue:
                    kind = "issue";
                    break;
                case scanner::CrashgenExpectationOutcomeKind::Success:
                    kind = "success";
                    break;
                default:
                    throw RunnerError("unknown expectation outcome");
                }
                switch (v.severity) {
                case scanner::CrashgenExpectationSeverity::Info:
                    severity = "info";
                    break;
                case scanner::CrashgenExpectationSeverity::Warning:
                    severity = "warning";
                    break;
                case scanner::CrashgenExpectationSeverity::Error:
                    severity = "error";
                    break;
                default:
                    throw RunnerError("unknown expectation severity");
                }
                switch (v.placement) {
                case scanner::AutoscanReportPlacement::Settings:
                    placement = "settings";
                    break;
                case scanner::AutoscanReportPlacement::ErrorInformation:
                    placement = "error_information";
                    break;
                default:
                    throw RunnerError("unknown expectation placement");
                }
                outcomes.push_back(json{{"ruleId", owned_string(v.rule_id)},
                                        {"kind", kind},
                                        {"severity", severity},
                                        {"message", owned_string(v.message)},
                                        {"fix", semantic_optional(v.has_fix, v.fix)},
                                        {"placement", placement},
                                        {"section", semantic_optional(v.has_section, v.section)},
                                        {"setting", semantic_optional(v.has_setting, v.setting)},
                                        {"expected", semantic_optional(v.has_expected, v.expected)},
                                        {"actual", semantic_optional(v.has_actual, v.actual)}});
            }
            for (const auto& v : result.disabled_setting_notices)
                notices.push_back(json{{"settingName", owned_string(v.setting_name)}});
            return json{{"expectationOutcomes", outcomes}, {"disabledSettingNotices", notices}};
        });
    }
    if (family == "formid-lookup") {
        namespace database = classic::database;
        const auto lookup = [&]() {
            if (c.at("mode") == "disabled")
                return database::formid_value_lookup_disabled_new();
            if (c.at("mode") == "sqlite-missing")
                return database::formid_value_lookup_sqlite_new(c.at("databasePath").get<std::string>(),
                                                                c.at("gameTable").get<std::string>());
            if (c.at("mode") == "shared-pool") {
                const auto pool = database::db_pool_new(c.at("gameTable").get<std::string>(), 1, 60);
                return database::formid_value_lookup_shared_pool_new(*pool);
            }
            if (c.at("mode") != "in-memory")
                throw RunnerError("unsupported lookup mode");
            database::FormIdValueLookupInMemoryConfigurationDto config{};
            for (const auto& v : c.at("entries")) {
                database::FormIdValueLookupInMemoryEntryDto entry{};
                entry.formid = v.at("formid").get<std::string>();
                entry.plugin = v.at("plugin").get<std::string>();
                if (!v.at("operationalFailure").is_null()) {
                    entry.reply_kind = database::FormIdValueLookupReplyKind::OperationalFailure;
                    entry.error_message = v.at("operationalFailure").get<std::string>();
                } else if (v.at("value").is_null())
                    entry.reply_kind = database::FormIdValueLookupReplyKind::Missing;
                else {
                    entry.reply_kind = database::FormIdValueLookupReplyKind::Found;
                    entry.value = v.at("value").get<std::string>();
                }
                config.entries.push_back(std::move(entry));
            }
            return database::formid_value_lookup_in_memory_new(std::move(config));
        }();
        const auto status = database::formid_value_lookup_construction_result(*lookup);
        if (status.has_lookup == status.has_error)
            throw RunnerError("invalid lookup constructor presence flags");
        if (status.has_error)
            return semantic_lookup_error(status.error);
        if (c.at("mode") == "sqlite-missing")
            throw RunnerError("missing SQLite fixture unexpectedly exists");
        if (request.contains("pairs")) {
            database::FormIdValueLookupBatchInputDto input{};
            for (const auto& pair : request.at("pairs"))
                input.pairs.push_back(database::FormIdValueLookupKeyDto{pair.at("formid").get<std::string>(),
                                                                        pair.at("plugin").get<std::string>()});
            const auto result = database::formid_value_lookup_lookup_batch(*lookup, std::move(input));
            if (result.has_outcomes == result.has_error)
                throw RunnerError("invalid lookup batch presence flags");
            if (result.has_error)
                return semantic_lookup_error(result.error);
            if (result.outcomes.size() != request.at("pairs").size())
                throw RunnerError("lookup batch length changed");
            json outcomes = json::array();
            for (std::size_t i = 0; i < result.outcomes.size(); ++i)
                outcomes.push_back(semantic_lookup_outcome(result.outcomes[i], request.at("pairs").at(i)));
            return json{{"analyzerKind", nullptr}, {"result", json{{"outcomes", outcomes}}}, {"error", nullptr}};
        }
        const auto run = [&](const json& r) {
            return database::formid_value_lookup_lookup(*lookup, r.at("formid").get<std::string>(),
                                                        r.at("plugin").get<std::string>());
        };
        if (fixture.contains("warmupRequest")) {
            const auto warmup = run(fixture.at("warmupRequest"));
            if (!warmup.has_outcome || warmup.has_error)
                throw RunnerError("lookup warmup failed");
        }
        const auto result = run(request);
        if (result.has_outcome == result.has_error)
            throw RunnerError("invalid lookup presence flags");
        if (result.has_error)
            return semantic_lookup_error(result.error);
        return json{{"analyzerKind", nullptr},
                    {"result", semantic_lookup_outcome(result.outcome, request)},
                    {"error", nullptr}};
    }
    throw RunnerError("unsupported semantic family");
}

/// Resolves an explicitly declared input fixture without reading scenario expectations.
json execute_semantic_scenario(const json& plan, const json& scenario) {
    const auto reference = scenario.at("input").at("fixtureRef").get<std::string>();
    const auto& references = scenario.at("fixtureRefs");
    if (std::find(references.begin(), references.end(), reference) == references.end())
        throw RunnerError("undeclared semantic fixture");
    std::ifstream stream(fs::path(plan.at("fixtures").at(reference).get<std::string>()), std::ios::binary);
    if (!stream)
        throw RunnerError("cannot read semantic fixture");
    return execute_semantic_fixture(plan.at("familyId").get<std::string>(), json::parse(stream));
}

/// Identifies only the six repository-owned focused semantic family contracts.
bool is_semantic_family(const json& family) {
    return family == "crash-suspect" || family == "crashgen-settings" || family == "mod-guidance" ||
           family == "named-record" || family == "plugin-evidence" || family == "formid-lookup";
}
