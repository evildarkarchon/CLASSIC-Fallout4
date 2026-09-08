//! Native aggregate FormID Finding result and strict lookup-error observations.

use super::{RunnerResult, invalid, text};
use classic_database_core::{
    FormIdValueLookup, FormIdValueLookupEntry, FormIdValueLookupInMemoryReply,
};
use classic_scanlog_core::{
    FormIDFindingAnalysisInput, FormIDFindingAnalyzer, FormIDPlugin, FormIDValueLookupStatus,
};
use serde_json::{Value, json};

/// Executes explicit lookup construction followed by owned aggregate analysis.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let mode = text(&fixture["mode"])?;
    let runtime = classic_shared_core::get_runtime();
    let lookup = match mode.as_str() {
        "disabled" => FormIdValueLookup::disabled(),
        "in-memory" => {
            let entries = fixture["entries"]
                .as_array()
                .ok_or_else(|| invalid("entries must be an array"))?
                .iter()
                .map(|entry| {
                    Ok(FormIdValueLookupEntry::new(
                        text(&entry["formid"])?,
                        text(&entry["plugin"])?,
                        if let Some(message) = entry["failure"].as_str() {
                            FormIdValueLookupInMemoryReply::OperationalFailure(message.to_owned())
                        } else {
                            FormIdValueLookupInMemoryReply::Value(
                                entry["value"].as_str().map(str::to_owned),
                            )
                        },
                    ))
                })
                .collect::<RunnerResult<Vec<_>>>()?;
            FormIdValueLookup::in_memory(entries)
        }
        "sqlite-missing" => {
            let path = text(&fixture["databasePath"])?;
            if std::path::Path::new(&path).exists() {
                return Err(invalid("missing SQLite path unexpectedly exists").into());
            }
            return match runtime.block_on(FormIdValueLookup::sqlite(path.into(), "Fallout4".into()))
            {
                Err(error) => Ok(
                    json!({"mode":mode,"findings":null,"error":{"code":error.code(),"message":error.message()}}),
                ),
                Ok(_) => Err(invalid("missing SQLite lookup unexpectedly constructed").into()),
            };
        }
        _ => return Err(invalid("unknown FormID Finding mode").into()),
    };
    let analyzer = FormIDFindingAnalyzer::new(lookup);
    let input = FormIDFindingAnalysisInput {
        crash_lines: fixture["lines"]
            .as_array()
            .ok_or_else(|| invalid("lines must be an array"))?
            .iter()
            .map(text)
            .collect::<RunnerResult<Vec<_>>>()?,
        plugins: fixture["plugins"]
            .as_array()
            .ok_or_else(|| invalid("plugins must be an array"))?
            .iter()
            .map(|plugin| {
                Ok(FormIDPlugin {
                    name: text(&plugin["name"])?,
                    prefix: text(&plugin["prefix"])?,
                })
            })
            .collect::<RunnerResult<Vec<_>>>()?,
    };
    match runtime.block_on(analyzer.analyze(input)) {
        Ok(result) => Ok(
            json!({"mode":mode,"findings":result.findings.into_iter().map(|finding|json!({"identifier":finding.identifier,"occurrences":finding.occurrences,"plugin":finding.plugin,"status":match finding.value_lookup_status{FormIDValueLookupStatus::NotApplicable=>"not_applicable",FormIDValueLookupStatus::Disabled=>"disabled",FormIDValueLookupStatus::Missing=>"missing",FormIDValueLookupStatus::Found=>"found"},"value":finding.value})).collect::<Vec<_>>(),"error":null}),
        ),
        Err(error) => Ok(
            json!({"mode":mode,"findings":null,"error":{"code":error.code().as_str(),"message":error.message()}}),
        ),
    }
}
