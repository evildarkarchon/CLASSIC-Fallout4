//! Input-only receipt participant for focused analyzers and FormID Value Lookup.

use classic_config_core::{
    ConfigLayout, CoreModEntry, CoreModExclude, CrashgenSettingsSnapshot, ModConflictEntry,
    ModSolutionCriteria, ModSolutionEntry, OutcomeKind, RuleSeverity, SuspectErrorRule,
    SuspectStackCountRule, SuspectStackRule, parse_crashgen_expectations,
};
use classic_database_core::{
    FormIdValueLookup, FormIdValueLookupEntry, FormIdValueLookupInMemoryReply,
    FormIdValueLookupOutcome,
};
use classic_scanlog_core::*;
use serde_json::{Value, json};
use std::{
    error::Error,
    fs,
    io::{self, Write},
    path::Path,
};
use tempfile::NamedTempFile;

type RunnerResult<T> = Result<T, Box<dyn Error + Send + Sync>>;

#[path = "semantic_conformance/installed_yaml_data.rs"]
mod installed_yaml_data;

#[path = "semantic_conformance/vocabulary.rs"]
mod vocabulary;

#[path = "semantic_conformance/config_operations.rs"]
mod config_operations;
#[path = "semantic_conformance/database_operations.rs"]
mod database_operations;
#[path = "semantic_conformance/file_operations.rs"]
mod file_operations;
#[path = "semantic_conformance/path_message_operations.rs"]
mod path_message_operations;
#[path = "semantic_conformance/scan_game.rs"]
mod scan_game;
#[path = "semantic_conformance/version_registry.rs"]
mod version_registry;

#[path = "semantic_conformance/aux_operations.rs"]
mod aux_operations;
#[path = "semantic_conformance/file_fingerprint.rs"]
mod file_fingerprint;
#[path = "semantic_conformance/performance.rs"]
mod performance;
#[path = "semantic_conformance/registry_accessors.rs"]
mod registry_accessors;
#[path = "semantic_conformance/registry_keys.rs"]
mod registry_keys;
#[path = "semantic_conformance/settings_extended.rs"]
mod settings_extended;
#[path = "semantic_conformance/settings_load.rs"]
mod settings_load;
#[path = "semantic_conformance/shared_identity.rs"]
mod shared_identity;
#[path = "semantic_conformance/shared_registry.rs"]
mod shared_registry;
#[path = "semantic_conformance/update_decisions.rs"]
mod update_decisions;
#[path = "semantic_conformance/update_services.rs"]
mod update_services;
#[path = "semantic_conformance/version_extended.rs"]
mod version_extended;
#[path = "semantic_conformance/version_values.rs"]
mod version_values;
#[path = "semantic_conformance/xse_operations.rs"]
mod xse_operations;
#[path = "semantic_conformance/xse_folder.rs"]
mod xse_folder;
#[path = "semantic_conformance/installation_paths.rs"]
mod installation_paths;

/// Rejects malformed runner inputs without confusing them with domain errors.
fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

/// Reads a string array from an input-only fixture, rejecting other carriers.
fn strings(value: &Value) -> RunnerResult<Vec<String>> {
    Ok(serde_json::from_value(value.clone())?)
}

/// Reads a required string without coercing absent or malformed input.
fn text(value: &Value) -> RunnerResult<String> {
    value
        .as_str()
        .map(str::to_owned)
        .ok_or_else(|| invalid("expected fixture string").into())
}

/// Reads a nullable string while retaining the distinction from an empty string.
fn optional(value: &Value) -> RunnerResult<Option<String>> {
    if value.is_null() {
        Ok(None)
    } else {
        Ok(Some(text(value)?))
    }
}

/// Wraps a public result or typed analyzer failure, preserving empty successes.
fn envelope(kind: AnalyzerKind, result: AnalyzerResult<Value>) -> Value {
    match result {
        Ok(result) => json!({"analyzerKind":kind.as_str(),"result":result,"error":null}),
        Err(error) => json!({"analyzerKind":kind.as_str(),"result":null,"error":{
            "analyzerKind":error.analyzer().as_str(),"code":error.code().as_str(),"message":error.message()}}),
    }
}

/// Reads authored conflict entries without interpreting their matching rules.
fn conflicts(value: &Value) -> RunnerResult<Vec<ModConflictEntry>> {
    value
        .as_array()
        .ok_or_else(|| invalid("conflicts must be an array"))?
        .iter()
        .map(|v| {
            Ok(ModConflictEntry {
                mod_a: text(&v["modA"])?,
                mod_b: text(&v["modB"])?,
                name_a: text(&v["nameA"])?,
                name_b: text(&v["nameB"])?,
                description: text(&v["description"])?,
                fix: optional(&v["fix"])?,
                link: optional(&v["link"])?,
            })
        })
        .collect()
}

/// Converts solution carriers into the public grouped-match configuration.
fn solutions(value: &Value) -> RunnerResult<Vec<ModSolutionEntry>> {
    value
        .as_array()
        .ok_or_else(|| invalid("solutions must be an array"))?
        .iter()
        .map(|v| {
            Ok(ModSolutionEntry {
                id: text(&v["id"])?,
                name: text(&v["name"])?,
                description: text(&v["description"])?,
                criteria: match v["criteriaKind"].as_str() {
                    Some("any") => ModSolutionCriteria::Any(strings(&v["criteria"])?),
                    Some("all") => ModSolutionCriteria::All(strings(&v["criteria"])?),
                    _ => return Err(invalid("unsupported criteriaKind").into()),
                },
                exceptions: strings(&v["exceptions"])?,
            })
        })
        .collect()
}

/// Converts important-mod configuration while retaining nullable authored guidance.
fn important_mods(value: &Value) -> RunnerResult<Vec<CoreModEntry>> {
    value
        .as_array()
        .ok_or_else(|| invalid("importantMods must be an array"))?
        .iter()
        .map(|v| {
            Ok(CoreModEntry {
                detect: text(&v["detect"])?,
                name: text(&v["name"])?,
                description: text(&v["description"])?,
                gpu: optional(&v["gpu"])?,
                gpu_mismatch_warning: optional(&v["gpuMismatchWarning"])?,
                exclude_when: if v["exclude"].is_null() {
                    None
                } else {
                    Some(CoreModExclude::PluginAny(strings(&v["exclude"])?))
                },
            })
        })
        .collect()
}

/// Projects the public match-state enum exhaustively so new variants require review.
fn match_state(value: ModGuidanceMatchState) -> &'static str {
    match value {
        ModGuidanceMatchState::Matched => "matched",
        ModGuidanceMatchState::Missing => "missing",
        ModGuidanceMatchState::GpuMismatch => "gpu_mismatch",
    }
}

/// Projects every authored solution field from the public result.
fn solution_result(values: Vec<ModSolutionGuidance>) -> Vec<Value> {
    values.into_iter().map(|v|json!({"state":match_state(v.state),"id":v.id,"name":v.name,"description":v.description,"matchedPluginIds":v.matched_plugin_ids})).collect()
}

/// Converts owned fixture facts into the public crash-suspect input.
fn crash_suspect_input(r: &Value) -> RunnerResult<CrashSuspectAnalysisInput> {
    Ok(CrashSuspectAnalysisInput {
        main_error: text(&r["mainError"])?,
        call_stack: text(&r["callStack"])?,
    })
}

/// Converts owned fixture facts into the public named-record input.
fn named_record_input(r: &Value) -> RunnerResult<NamedRecordFindingAnalysisInput> {
    Ok(NamedRecordFindingAnalysisInput {
        crash_lines: strings(&r["crashLines"])?,
    })
}

/// Converts owned fixture facts into the public plugin-evidence input.
fn plugin_evidence_input(r: &Value) -> RunnerResult<PluginEvidenceAnalysisInput> {
    Ok(PluginEvidenceAnalysisInput {
        call_stack: strings(&r["crashLines"])?,
        plugins: strings(&r["plugins"])?,
    })
}

/// Converts owned fixture facts into the public crashgen-settings input.
fn crashgen_settings_input(r: &Value) -> RunnerResult<CrashgenSettingsAnalysisInput> {
    let mut settings = CrashgenSettingsSnapshot::new();
    for (section, values) in r["settings"]
        .as_object()
        .ok_or_else(|| invalid("settings must be an object"))?
    {
        for (key, value) in values
            .as_object()
            .ok_or_else(|| invalid("settings section must be an object"))?
        {
            settings.insert(section, key, text(value)?);
        }
    }
    Ok(CrashgenSettingsAnalysisInput {
        settings,
        installed_plugins: strings(&r["installedPlugins"])?.into_iter().collect(),
        crashgen_version: serde_json::from_value(r["crashgenVersion"].clone())?,
        config_layout: ConfigLayout::parse(&text(&r["configLayout"])?)
            .ok_or_else(|| invalid("invalid configLayout"))?,
    })
}

/// Executes warmup on the same immutable handle before observing the requested call.
fn reused<A, I, O>(
    analyzer: AnalyzerResult<A>,
    input: I,
    warmup: Option<I>,
    run: impl Fn(&A, I) -> AnalyzerResult<O>,
) -> AnalyzerResult<O> {
    let analyzer = analyzer?;
    if let Some(warmup) = warmup {
        run(&analyzer, warmup)?;
    }
    run(&analyzer, input)
}

/// Invokes the public operation using owned facts and serializes only its typed result.
fn analyze(family: &str, c: &Value, r: &Value, warmup: Option<&Value>) -> RunnerResult<Value> {
    Ok(match family {
        "crash-suspect" => {
            let main = c["mainErrorRules"]
                .as_array()
                .ok_or_else(|| invalid("mainErrorRules must be an array"))?
                .iter()
                .map(|v| {
                    Ok(SuspectErrorRule {
                        id: text(&v["id"])?,
                        name: text(&v["name"])?,
                        severity: serde_json::from_value(v["severity"].clone())?,
                        main_error_contains_any: strings(&v["mainErrorContainsAny"])?,
                    })
                })
                .collect::<RunnerResult<Vec<_>>>()?;
            let stack = c["stackRules"]
                .as_array()
                .ok_or_else(|| invalid("stackRules must be an array"))?
                .iter()
                .map(|v| {
                    Ok(SuspectStackRule {
                        id: text(&v["id"])?,
                        name: text(&v["name"])?,
                        severity: serde_json::from_value(v["severity"].clone())?,
                        main_error_required_any: strings(&v["mainErrorRequiredAny"])?,
                        main_error_optional_any: strings(&v["mainErrorOptionalAny"])?,
                        stack_contains_any: strings(&v["stackContainsAny"])?,
                        exclude_if_stack_contains_any: strings(&v["excludeIfStackContainsAny"])?,
                        stack_contains_at_least: v["stackContainsAtLeast"]
                            .as_array()
                            .ok_or_else(|| invalid("stackContainsAtLeast must be an array"))?
                            .iter()
                            .map(|n| {
                                Ok(SuspectStackCountRule {
                                    substring: text(&n["substring"])?,
                                    count: serde_json::from_value(n["count"].clone())?,
                                })
                            })
                            .collect::<RunnerResult<Vec<_>>>()?,
                    })
                })
                .collect::<RunnerResult<Vec<_>>>()?;
            let input = crash_suspect_input(r)?;
            let warmup = warmup.map(crash_suspect_input).transpose()?;
            envelope(AnalyzerKind::CrashSuspect, reused(CrashSuspectAnalyzer::new(main, stack), input, warmup, |a, input| a.analyze(input)).map(|result| {
                let findings:Vec<_> = result.findings.into_iter().map(|f| match f {
                    CrashSuspectFinding::MainErrorRule {rule_id,name,severity} => json!({"kind":"main_error_rule","ruleId":rule_id,"name":name,"severity":severity}),
                    CrashSuspectFinding::StackRule {rule_id,name,severity} => json!({"kind":"stack_rule","ruleId":rule_id,"name":name,"severity":severity}),
                    CrashSuspectFinding::DllInvolvement => json!({"kind":"dll_involvement","ruleId":null,"name":null,"severity":null}),
                }).collect(); json!({"findings":findings})
            }))
        }
        "named-record" => {
            let input = named_record_input(r)?;
            let warmup = warmup.map(named_record_input).transpose()?;
            envelope(AnalyzerKind::NamedRecordFinding, reused(NamedRecordFindingAnalyzer::new(strings(&c["targetRecords"])?,strings(&c["ignoreRecords"])?), input, warmup, |a, input| a.analyze(input)).map(|result|json!({"findings":result.findings.into_iter().map(|v|json!({"record":v.record,"occurrences":v.occurrences})).collect::<Vec<_>>()})))
        }
        "plugin-evidence" => {
            let input = plugin_evidence_input(r)?;
            let warmup = warmup.map(plugin_evidence_input).transpose()?;
            envelope(AnalyzerKind::PluginEvidence, reused(PluginEvidenceAnalyzer::new(strings(&c["ignoredPlugins"])?), input, warmup, |a, input| a.analyze(input)).map(|result|json!({"evidence":result.evidence.into_iter().map(|v|json!({"plugin":v.plugin,"occurrences":v.occurrences})).collect::<Vec<_>>()})))
        }
        "mod-guidance" => {
            let input = ModGuidanceAnalysisInput {
                plugins: r["plugins"]
                    .as_array()
                    .ok_or_else(|| invalid("plugins must be an array"))?
                    .iter()
                    .map(|v| Ok((text(&v["name"])?, text(&v["id"])?)))
                    .collect::<RunnerResult<_>>()?,
                user_gpu: optional(&r["userGpu"])?,
                xse_modules: strings(&r["xseModules"])?.into_iter().collect(),
            };
            envelope(AnalyzerKind::ModGuidance, ModGuidanceAnalyzer::new(conflicts(&c["conflicts"])?,solutions(&c["frequentCrashes"])?,solutions(&c["solutions"])?,important_mods(&c["importantMods"])?).and_then(|a|a.analyze(input)).map(|result|json!({
                "conflicts":result.conflicts.into_iter().map(|v|json!({"state":match_state(v.state),"modA":v.mod_a,"modB":v.mod_b,"nameA":v.name_a,"nameB":v.name_b,"description":v.description,"fix":v.fix,"link":v.link})).collect::<Vec<_>>(),
                "frequentCrashes":solution_result(result.frequent_crashes),"solutions":solution_result(result.solutions),
                "importantMods":result.important_mods.into_iter().map(|v|json!({"state":match_state(v.state),"detect":v.detect,"name":v.name,"description":v.description,"gpu":v.gpu,"gpuMismatchWarning":v.gpu_mismatch_warning})).collect::<Vec<_>>()
            })))
        }
        "crashgen-settings" => {
            let entry = &c["entry"];
            let parsed = if entry["settings_rules"].is_null() {
                Default::default()
            } else {
                parse_crashgen_expectations(
                    &entry["settings_rules"],
                    entry["settings_rules_version"]
                        .as_u64()
                        .map(u32::try_from)
                        .transpose()?,
                )
            };
            let entry = CrashgenEntry {
                display_section: text(&entry["display_section"])?,
                ignore_keys: strings(&entry["ignore_keys"])?.into_iter().collect(),
                settings_rules: parsed.rules,
            };
            let input = crashgen_settings_input(r)?;
            let warmup = warmup.map(crashgen_settings_input).transpose()?;
            envelope(AnalyzerKind::CrashgenSettings, reused(CrashgenSettingsAnalyzer::from_parsed_configuration(text(&c["crashgenName"])?,entry,parsed.diagnostics), input, warmup, |a, input| a.analyze(input)).map(|result|json!({
                "expectationOutcomes":result.expectation_outcomes.into_iter().map(|v|json!({"ruleId":v.rule_id,"kind":match v.kind {OutcomeKind::Notice=>"notice",OutcomeKind::Issue=>"issue",OutcomeKind::Success=>"success"},"severity":match v.severity {RuleSeverity::Info=>"info",RuleSeverity::Warning=>"warning",RuleSeverity::Error=>"error"},"message":v.message,"fix":v.fix,"placement":v.placement.as_str(),"section":v.section,"setting":v.setting,"expected":v.expected,"actual":v.actual})).collect::<Vec<_>>(),
                "disabledSettingNotices":result.disabled_setting_notices.into_iter().map(|v|json!({"settingName":v.setting_name})).collect::<Vec<_>>()
            })))
        }
        "formid-lookup" => lookup_fixture(c, r, warmup)?,
        _ => return Err(invalid("unsupported semantic family").into()),
    })
}

/// Projects the strict lookup outcome without collapsing disabled and successful misses.
fn lookup_outcome(outcome: FormIdValueLookupOutcome) -> Value {
    match outcome {
        FormIdValueLookupOutcome::Disabled => json!({"kind":"disabled","value":null}),
        FormIdValueLookupOutcome::Missing => json!({"kind":"missing","value":null}),
        FormIdValueLookupOutcome::Found(value) => json!({"kind":"found","value":value}),
    }
}

/// Preserves optional key context and the core-owned diagnostic for strict lookup failures.
fn lookup_error(error: classic_database_core::FormIdValueLookupError) -> Value {
    json!({"analyzerKind":null,"result":null,"error":{"analyzerKind":null,"code":error.code(),"message":error.message(),"formid":error.formid(),"plugin":error.plugin()}})
}

/// Executes public constructor, single and positional batch operations on one shared-runtime handle.
fn lookup_fixture(c: &Value, r: &Value, warmup: Option<&Value>) -> RunnerResult<Value> {
    let runtime = classic_shared_core::get_runtime();
    let lookup = match c["mode"].as_str() {
        Some("disabled") => FormIdValueLookup::disabled(),
        Some("in-memory") => FormIdValueLookup::in_memory(
            c["entries"]
                .as_array()
                .ok_or_else(|| invalid("entries must be an array"))?
                .iter()
                .map(|v| {
                    Ok(FormIdValueLookupEntry::new(
                        text(&v["formid"])?,
                        text(&v["plugin"])?,
                        match optional(&v["operationalFailure"])? {
                            Some(message) => {
                                FormIdValueLookupInMemoryReply::OperationalFailure(message)
                            }
                            None => FormIdValueLookupInMemoryReply::Value(optional(&v["value"])?),
                        },
                    ))
                })
                .collect::<RunnerResult<Vec<_>>>()?,
        ),
        Some("sqlite-missing") => match runtime.block_on(FormIdValueLookup::sqlite(
            text(&c["databasePath"])?.into(),
            text(&c["gameTable"])?,
        )) {
            Ok(_) => return Err(invalid("missing SQLite fixture unexpectedly exists").into()),
            Err(error) => return Ok(lookup_error(error)),
        },
        Some("shared-pool") => FormIdValueLookup::shared_pool(std::sync::Arc::new(
            classic_database_core::DatabasePool::new(
                Some(1),
                std::time::Duration::from_secs(60),
                text(&c["gameTable"])?,
            ),
        )),
        _ => return Err(invalid("unsupported lookup mode").into()),
    };
    if let Some(warmup) = warmup {
        // Reuse the actual handle to detect cached-hit leakage into a later miss.
        runtime.block_on(lookup.lookup(&text(&warmup["formid"])?, &text(&warmup["plugin"])?))?;
    }
    let result = if let Some(pairs) = r.get("pairs") {
        let pairs = pairs
            .as_array()
            .ok_or_else(|| invalid("pairs must be an array"))?
            .iter()
            .map(|p| Ok((text(&p["formid"])?, text(&p["plugin"])?)))
            .collect::<RunnerResult<Vec<_>>>()?;
        runtime.block_on(lookup.lookup_batch(pairs)).map(|outcomes|json!({"outcomes":outcomes.into_iter().map(lookup_outcome).collect::<Vec<_>>()}))
    } else {
        runtime
            .block_on(lookup.lookup(&text(&r["formid"])?, &text(&r["plugin"])?))
            .map(lookup_outcome)
    };
    Ok(match result {
        Ok(result) => json!({"analyzerKind":null,"result":result,"error":null}),
        Err(error) => lookup_error(error),
    })
}

/// Loads only a scenario-declared fixture and invokes its public domain operation.
fn execute(plan: &Value, scenario: &Value) -> RunnerResult<Value> {
    if scenario.get("expected").is_some() {
        return Err(invalid("input plan exposed expectations").into());
    }
    if vocabulary::is_family(&plan["familyId"]) {
        return vocabulary::execute(&text(&plan["familyId"])?, scenario);
    }
    let reference = &scenario["input"]["fixtureRef"];
    if !scenario["fixtureRefs"]
        .as_array()
        .ok_or_else(|| invalid("fixtureRefs must be an array"))?
        .contains(reference)
    {
        return Err(invalid("undeclared fixtureRef").into());
    }
    let fixture: Value =
        serde_json::from_slice(&fs::read(text(&plan["fixtures"][text(reference)?])?)?)?;
    if plan["familyId"] == "installed-yaml-data" {
        if scenario["action"] != format!("installed-yaml-data.{}", text(&fixture["operation"])?) {
            return Err(invalid("installed YAML action does not match fixture operation").into());
        }
        return installed_yaml_data::execute(&fixture);
    }
    match plan["familyId"].as_str() {
        Some(
            "game-version-parse"
            | "game-version-distance"
            | "game-version-order"
            | "fallout4-identity"
            | "fallout4-paths"
            | "fallout4-metadata",
        ) => return version_values::execute(&text(&plan["familyId"])?, &fixture),
        Some("registry-keys") => return registry_keys::execute(&fixture),
        Some("file-fingerprint") => return file_fingerprint::execute(&fixture),
        Some("registry-game" | "registry-gui" | "registry-context" | "registry-paths") => {
            return registry_accessors::execute(&text(&plan["familyId"])?, &fixture);
        }
        Some("settings-validation" | "settings-cached-docs") => {
            return settings_extended::execute(&text(&plan["familyId"])?, &fixture);
        }
        Some("settings-load" | "settings-yaml" | "settings-yaml-batch") => {
            return settings_load::execute(&fixture);
        }
        Some("xse-folder") => return xse_folder::execute(&fixture),
        Some("installation-paths") => return installation_paths::execute(&fixture),
        Some("xse-operations") => return xse_operations::execute(&fixture),
        Some("game-identity" | "runtime-access") => {
            return shared_identity::execute(&text(&plan["familyId"])?, &fixture);
        }
        Some("performance") => return performance::execute(&fixture),
        Some("update-decisions") => return update_decisions::execute(&fixture),
        Some("update-services") => return update_services::execute(&fixture, scenario),
        Some("string-operations" | "registry-operations") => {
            return shared_registry::execute(&text(&plan["familyId"])?, &fixture);
        }
        Some(
            "web-operations"
            | "resource-operations"
            | "version-operations"
            | "version-extraction"
            | "version-f4se"
            | "version-pe"
            | "version-pe-path",
        ) => {
            return aux_operations::execute(&text(&plan["familyId"])?, &fixture);
        }
        Some("config-operations") => return config_operations::execute(&fixture),
        Some("database-operations") => return database_operations::execute(&fixture),
        Some("version-registry" | "version-registry-details" | "version-registry-values") => {
            return version_registry::execute(&fixture);
        }
        Some("scan-game") => return scan_game::observe(&fixture),
        Some("file-operations") => {
            if scenario["action"] != format!("file-operations.{}", text(&fixture["operation"])?) {
                return Err(invalid("file action does not match fixture operation").into());
            }
            return file_operations::observe(&fixture);
        }
        Some("path-operations" | "path-normalization" | "message-operations") => {
            return path_message_operations::execute(&text(&plan["familyId"])?, &fixture);
        }
        _ => { /* Focused analyzers use their existing dispatch below. */ }
    }
    analyze(
        &text(&plan["familyId"])?,
        &fixture["configuration"],
        &fixture["request"],
        fixture.get("warmupRequest"),
    )
}

/// Executes an authenticated input-only invocation and publishes a fresh sibling receipt.
fn publish(plan_path: &Path, output_path: &Path) -> RunnerResult<()> {
    let plan: Value = serde_json::from_slice(&fs::read(plan_path)?)?;
    if plan["schemaVersion"] != 1
        || plan["familyVersion"] != 1
        || plan["participant"]
            != json!({"id":"rust","role":"semantic-adapter","executionInstanceId":"rust"})
    {
        return Err(invalid("invalid Rust semantic run plan").into());
    }
    if !plan_path.is_absolute()
        || !output_path.is_absolute()
        || output_path.exists()
        || plan_path.parent() != output_path.parent()
    {
        return Err(invalid("receipt must be a fresh absolute sibling of the plan").into());
    }
    let scenarios = plan["scenarios"].as_array().filter(|v|!v.is_empty()).ok_or_else(||invalid("scenarios must be nonempty"))?.iter().map(|scenario| match execute(&plan,scenario) {
        Ok(observation)=>json!({"id":scenario["id"],"capabilityIds":scenario["capabilityIds"],"executionStatus":"completed","observation":observation,"failure":null}),
        Err(error)=>json!({"id":scenario["id"],"capabilityIds":scenario["capabilityIds"],"executionStatus":"failed","observation":{},"failure":{"kind":"rust-runner-error","message":error.to_string()}}),
    }).collect::<Vec<_>>();
    let receipt = json!({"schemaVersion":plan["schemaVersion"],"familyId":plan["familyId"],"familyVersion":plan["familyVersion"],"expectationDigest":plan["expectationDigest"],"invocation":plan["invocation"],"participant":plan["participant"],"runner":{"id":"classic-rust-semantic-conformance","version":1,"platform":std::env::consts::OS,"toolchain":"rust"},"scenarios":scenarios});
    let mut temporary = NamedTempFile::new_in(
        output_path
            .parent()
            .ok_or_else(|| invalid("receipt has no parent"))?,
    )?;
    temporary.write_all(&serde_json::to_vec(&receipt)?)?;
    temporary.as_file().sync_all()?;
    temporary.persist_noclobber(output_path)?;
    Ok(())
}

/// Participates only when the launcher supplies both immutable input and fresh output paths.
#[test]
fn writes_semantic_conformance_receipt() {
    match (
        std::env::var_os("CLASSIC_CONFORMANCE_RUN_PLAN"),
        std::env::var_os("CLASSIC_CONFORMANCE_OUTPUT"),
    ) {
        (None, None) => {
            eprintln!("Semantic conformance launcher variables absent; receipt run skipped")
        }
        (Some(plan), Some(output)) => publish(Path::new(&plan), Path::new(&output))
            .expect("Rust semantic receipt must publish"),
        _ => panic!("both conformance launcher paths are required"),
    }
}
