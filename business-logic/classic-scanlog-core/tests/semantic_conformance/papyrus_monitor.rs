//! Native Papyrus full-analysis and tail-monitor lifetime observations.

use super::{RunnerResult, invalid, text};
use classic_scanlog_core::papyrus::{PapyrusAnalyzer, PapyrusError, PapyrusStats};
use serde_json::{Value, json};
use std::{fs, io::Write};

/// Projects portable counters and the public ratio query, excluding clock timestamps.
fn stats(value: &PapyrusStats) -> Value {
    json!({"dumps":value.dumps,"stacks":value.stacks,"warnings":value.warnings,
        "errors":value.errors,"lines":value.lines_processed,"ratio":format!("{:.3}",value.dumps_to_stacks_ratio())})
}

/// Runs full, tail, append, idle and reset stages in an owned disposable directory.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let path = temporary.path().join("Papyrus.0.log");
    if !fixture["content"].is_null() {
        fs::write(&path, text(&fixture["content"])?.as_bytes())?;
    }
    let mut analyzer = PapyrusAnalyzer::new(path.clone());
    if fixture["operation"] == "full" {
        return match analyzer.analyze_full() {
            Ok(value) => Ok(
                json!({"stats":{"dumps":value.dumps,"stacks":value.stacks,"warnings":value.warnings,"errors":value.errors,"lines":value.lines_processed},"error":null,"content":fs::read_to_string(path)?}),
            ),
            Err(PapyrusError::LogNotFound(_)) => {
                Ok(json!({"stats":null,"error":"missing","content":null}))
            }
            Err(error) => Err(error.into()),
        };
    }
    let mut result = json!({"exists":analyzer.log_exists(),"error":null,"initial":null,
        "tailStart":null,"updated":null,"idle":null,"afterReset":null,"finalContent":null});
    if analyzer.log_path() != path || stats(analyzer.stats()) != stats(&PapyrusStats::new()) {
        return Err(invalid("new Papyrus analyzer has wrong initial state").into());
    }
    result["initial"] = match analyzer.analyze_full() {
        Ok(value) => stats(&value),
        Err(PapyrusError::LogNotFound(_)) => {
            result["error"] = json!("missing");
            return Ok(result);
        }
        Err(error) => return Err(error.into()),
    };
    let value = analyzer.stats();
    let expected = format!(
        "NUMBER OF DUMPS    : {}\nNUMBER OF STACKS   : {}\nDUMPS/STACKS RATIO : {:.3}\nNUMBER OF WARNINGS : {}\nNUMBER OF ERRORS   : {}\nLINES PROCESSED    : {}",
        value.dumps,
        value.stacks,
        value.dumps_to_stacks_ratio(),
        value.warnings,
        value.errors,
        value.lines_processed
    );
    if analyzer.analyze_to_string() != expected {
        return Err(invalid("Papyrus summary disagrees with statistics").into());
    }
    analyzer.start_monitoring()?;
    if analyzer.check_for_updates()?.is_some() {
        return Err(invalid("tail start replayed old lines").into());
    }
    result["tailStart"] = stats(analyzer.stats());
    let appended = text(&fixture["append"])?;
    fs::OpenOptions::new()
        .append(true)
        .open(&path)?
        .write_all(appended.as_bytes())?;
    if let Some((lines, _)) = analyzer.check_for_updates()?
        && lines != appended.lines().map(str::to_owned).collect::<Vec<_>>()
    {
        return Err(invalid("tail update changed lines").into());
    }
    result["updated"] = stats(analyzer.stats());
    if analyzer.check_for_updates()?.is_some() {
        return Err(invalid("idle poll replayed lines").into());
    }
    result["idle"] = stats(analyzer.stats());
    analyzer.reset();
    result["afterReset"] = stats(&analyzer.analyze_full()?);
    result["finalContent"] = json!(fs::read_to_string(path)?);
    Ok(result)
}
