//! Observe explicit performance samples and measured timer lifecycle invariants.
use super::{RunnerResult, invalid, text};
use classic_perf_core::{clear_metrics, get_summary, record_timing};
use serde_json::{Value, json};

/// Convert exact authored durations without rounding away native differences.
fn milliseconds(seconds: f64) -> RunnerResult<u64> {
    let value = seconds * 1000.0;
    if !value.is_finite() || value < 0.0 || value > 9_007_199_254_740_991.0 || value.fract() != 0.0
    {
        return Err(invalid("metric duration is not an exact integer millisecond").into());
    }
    Ok(value as u64)
}

/// Execute explicit samples serially; process-global state is cleared even on error.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    clear_metrics();
    let result = observe(fixture);
    // A failed observation must not leave samples for the next fixture.
    clear_metrics();
    result
}

/// Measure clock progress and exactly-once recording through both public constructors.
pub(super) fn execute_timers(fixture: &Value) -> RunnerResult<Value> {
    if fixture != &json!({"constructors": ["direct", "factory"]}) {
        return Err(invalid("unsupported timer fixture").into());
    }
    clear_metrics();
    let mut timers = Vec::new();
    for constructor in ["direct", "factory"] {
        let timer = if constructor == "direct" {
            classic_perf_core::Timer::new(constructor)
        } else {
            classic_perf_core::start_timer(constructor)
        };
        let first = timer.elapsed();
        // Assert progress, not a scheduler-specific elapsed duration.
        std::thread::sleep(std::time::Duration::from_millis(2));
        let later = timer.elapsed();
        timer.finish();
        let summary = get_summary();
        let stats = summary.get(constructor);
        timers.push(json!({
            "constructor": constructor,
            "advanced": first.is_finite() && later.is_finite() && first >= 0.0 && later > first,
            "positive": stats.is_some_and(|s| s.total >= later && later > 0.0),
            "singleSample": stats.is_some_and(|s| s.count == 1),
            "summaryConsistent": stats.is_some_and(|s| s.total == s.average && s.total == s.min && s.total == s.max)
        }));
    }
    clear_metrics();
    Ok(json!({"timers": timers, "cleared": get_summary().is_empty()}))
}

/// Project native statistics into integer milliseconds for exact comparison.
fn observe(fixture: &Value) -> RunnerResult<Value> {
    if fixture.as_object().is_none_or(|object| object.len() != 1) {
        return Err(invalid("unsupported performance fixture").into());
    }
    let operations = fixture["operations"]
        .as_array()
        .ok_or_else(|| invalid("operations must be an array"))?;
    let mut snapshots = Vec::new();
    for operation in operations {
        let object = operation
            .as_object()
            .ok_or_else(|| invalid("operation must be an object"))?;
        match text(&operation["op"])?.as_str() {
            "clear" if object.len() == 1 => clear_metrics(),
            "summary" if object.len() == 1 => {
                let mut snapshot = serde_json::Map::new();
                for (label, stats) in get_summary() {
                    snapshot.insert(label, json!({"count": stats.count,
                        "totalMs": milliseconds(stats.total)?, "averageMs": milliseconds(stats.average)?,
                        "minMs": milliseconds(stats.min)?, "maxMs": milliseconds(stats.max)?}));
                }
                snapshots.push(Value::Object(snapshot));
            }
            "record" if object.len() == 3 => {
                let duration = operation["durationMs"]
                    .as_u64()
                    .filter(|value| *value <= 1_000_000)
                    .ok_or_else(|| invalid("durationMs must be a bounded nonnegative integer"))?;
                record_timing(&text(&operation["label"])?, duration as f64 / 1000.0);
            }
            _ => return Err(invalid("unsupported performance operation").into()),
        }
    }
    Ok(json!({"snapshots": snapshots}))
}
