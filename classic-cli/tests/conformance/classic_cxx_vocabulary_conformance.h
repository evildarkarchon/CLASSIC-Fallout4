// Input-only Vocabulary resolver participant, included within the runner namespace.

/// Identifies the independent configuration and scan-run Vocabulary families.
bool is_vocabulary_family(const json& family) {
    return family == "config-vocabulary" || family == "scan-run-vocabulary";
}

/// Converts fixture tokens into bridge enums and observes the actual public resolver.
/// The central source-derived denominator checks coverage; these pairs only carry inputs.
template <typename Enum, typename Resolver>
json vocabulary_entries(const json& tokens, std::initializer_list<std::pair<std::string_view, Enum>> carriers,
                        Resolver resolve) {
    if (!tokens.is_array())
        throw RunnerError("vocabulary tokens must be an array");
    json entries = json::array();
    for (const auto& value : tokens) {
        const auto token = value.get<std::string>();
        // CXX enums are open: an unknown discriminant must reach the public resolver.
        auto carrier = static_cast<Enum>(255);
        for (const auto& [candidate, known] : carriers) {
            if (token == candidate) {
                carrier = known;
                break;
            }
        }
        const auto label = owned_string(resolve(carrier));
        entries.push_back(json{
            {"token", token}, {"label", label.empty() ? json(nullptr) : json(label)}, {"rejected", label.empty()}});
    }
    return entries;
}

/// Calls one public bridge resolver using direct scenario facts and retains input order.
json execute_vocabulary_scenario(const json& plan, const json& scenario) {
    if (scenario.at("action") != "vocabulary.resolve" || scenario.at("fixtureRefs") != json::array())
        throw RunnerError("vocabulary scenarios require direct inputs and vocabulary.resolve");
    const auto family = plan.at("familyId").get<std::string>();
    const auto& input = scenario.at("input");
    const auto operation = input.at("operation").get<std::string>();
    const auto& tokens = input.at("tokens");
    json entries;
    if (family == "config-vocabulary" && operation == "scan_run_installed_yaml_data_provenance_label") {
        using Carrier = scanner::ScanRunInstalledYamlDataProvenance;
        entries = vocabulary_entries<Carrier>(
            tokens, {{"updated", Carrier::Updated}, {"previous", Carrier::Previous}, {"bundled", Carrier::Bundled}},
            scanner::scan_run_installed_yaml_data_provenance_label);
    } else if (family == "config-vocabulary" && operation == "installed_yaml_data_provenance_label") {
        using Carrier = classic::config::InstalledYamlDataProvenance;
        entries = vocabulary_entries<Carrier>(
            tokens, {{"updated", Carrier::Updated}, {"previous", Carrier::Previous}, {"bundled", Carrier::Bundled}},
            classic::config::installed_yaml_data_provenance_label);
    } else if (family == "config-vocabulary" && operation == "installed_yaml_data_diagnostic_kind_label") {
        using Carrier = classic::config::InstalledYamlDataDiagnosticKind;
        entries = vocabulary_entries<Carrier>(tokens,
                                              {{"cache_unavailable", Carrier::CacheUnavailable},
                                               {"missing", Carrier::Missing},
                                               {"read", Carrier::Read},
                                               {"invalid_utf8", Carrier::InvalidUtf8},
                                               {"parse", Carrier::Parse},
                                               {"invalid_schema", Carrier::InvalidSchema},
                                               {"incompatible_schema", Carrier::IncompatibleSchema},
                                               {"invalid_role_data", Carrier::InvalidRoleData},
                                               {"local_ignore_generated", Carrier::LocalIgnoreGenerated},
                                               {"local_ignore_reset", Carrier::LocalIgnoreReset}},
                                              classic::config::installed_yaml_data_diagnostic_kind_label);
    } else if (family == "config-vocabulary" && operation == "local_ignore_yaml_data_state_label") {
        using Carrier = classic::config::LocalIgnoreYamlDataState;
        entries = vocabulary_entries<Carrier>(tokens,
                                              {{"existing", Carrier::Existing},
                                               {"generated", Carrier::Generated},
                                               {"proceed_without_ignore", Carrier::ProceedWithoutIgnore},
                                               {"reset_to_default", Carrier::ResetToDefault}},
                                              classic::config::local_ignore_yaml_data_state_label);
    } else if (family == "scan-run-vocabulary" && operation == "scan_run_installed_yaml_data_diagnostic_kind_label") {
        using Carrier = scanner::ScanRunInstalledYamlDataDiagnosticKind;
        entries = vocabulary_entries<Carrier>(tokens,
                                              {{"cache_unavailable", Carrier::CacheUnavailable},
                                               {"missing", Carrier::Missing},
                                               {"read", Carrier::Read},
                                               {"invalid_utf8", Carrier::InvalidUtf8},
                                               {"parse", Carrier::Parse},
                                               {"invalid_schema", Carrier::InvalidSchema},
                                               {"incompatible_schema", Carrier::IncompatibleSchema},
                                               {"invalid_role_data", Carrier::InvalidRoleData},
                                               {"local_ignore_generated", Carrier::LocalIgnoreGenerated},
                                               {"local_ignore_reset", Carrier::LocalIgnoreReset}},
                                              scanner::scan_run_installed_yaml_data_diagnostic_kind_label);
    } else if (family == "scan-run-vocabulary" && operation == "scan_run_local_ignore_yaml_data_state_label") {
        using Carrier = scanner::ScanRunLocalIgnoreYamlDataState;
        entries = vocabulary_entries<Carrier>(tokens,
                                              {{"existing", Carrier::Existing},
                                               {"generated", Carrier::Generated},
                                               {"proceed_without_ignore", Carrier::ProceedWithoutIgnore},
                                               {"reset_to_default", Carrier::ResetToDefault},
                                               {"recovery_required", Carrier::RecoveryRequired}},
                                              scanner::scan_run_local_ignore_yaml_data_state_label);
    } else if (family == "scan-run-vocabulary" && operation == "scan_run_log_disposition_label") {
        using Carrier = scanner::ScanRunContractLogDisposition;
        entries = vocabulary_entries<Carrier>(tokens,
                                              {{"succeeded", Carrier::Succeeded},
                                               {"failed", Carrier::Failed},
                                               {"cancelled_before_start", Carrier::CancelledBeforeStart}},
                                              scanner::scan_run_log_disposition_label);
    } else if (family == "scan-run-vocabulary" && operation == "scan_run_log_failure_stage_label") {
        using Carrier = scanner::ScanRunContractLogFailureStage;
        entries = vocabulary_entries<Carrier>(tokens,
                                              {{"analysis", Carrier::Analysis},
                                               {"report_write", Carrier::ReportWrite},
                                               {"unsolved_logs_finalization", Carrier::UnsolvedLogsFinalization}},
                                              scanner::scan_run_log_failure_stage_label);
    } else if (family == "scan-run-vocabulary" && operation == "scan_run_infrastructure_error_stage_label") {
        using Carrier = scanner::ScanRunContractInfrastructureErrorStage;
        entries = vocabulary_entries<Carrier>(tokens,
                                              {{"request_validation", Carrier::RequestValidation},
                                               {"discovery", Carrier::Discovery},
                                               {"intake", Carrier::Intake},
                                               {"formid_database_access", Carrier::FormIdDatabaseAccess},
                                               {"initialization", Carrier::Initialization},
                                               {"internal_invariant", Carrier::InternalInvariant}},
                                              scanner::scan_run_infrastructure_error_stage_label);
    } else if (family == "scan-run-vocabulary" && operation == "scan_run_local_ignore_reset_failure_stage_label") {
        using Carrier = scanner::ScanRunLocalIgnoreResetFailureStage;
        entries = vocabulary_entries<Carrier>(tokens,
                                              {{"create", Carrier::Create},
                                               {"write", Carrier::Write},
                                               {"flush", Carrier::Flush},
                                               {"sync", Carrier::Sync},
                                               {"publish", Carrier::Publish}},
                                              scanner::scan_run_local_ignore_reset_failure_stage_label);
    } else {
        throw RunnerError("unsupported vocabulary operation for family");
    }
    return json{{"operation", operation}, {"entries", entries}};
}
