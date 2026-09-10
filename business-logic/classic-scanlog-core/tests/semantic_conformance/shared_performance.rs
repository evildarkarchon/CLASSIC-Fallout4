//! Direct observations of foundation metric storage and real timer transitions.

use super::{RunnerResult, invalid};
use classic_shared_core::performance_core::{Timer, get_global_metrics};
use serde_json::{Value, json};
use std::time::Duration;

/// Record controlled samples and a separate real timer in a dedicated process.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let metrics = get_global_metrics();
    metrics.clear();
    let result = (|| -> RunnerResult<Value> {
        let missing = metrics.get_stats("samples").is_none();
        for record in fixture["records"]
            .as_array()
            .ok_or_else(|| invalid("expected metric records"))?
        {
            metrics.record_timing(
                "samples",
                Duration::from_millis(
                    record["milliseconds"]
                        .as_u64()
                        .ok_or_else(|| invalid("expected milliseconds"))?,
                ),
            );
            metrics.record_bytes(
                "samples",
                record["bytes"]
                    .as_u64()
                    .ok_or_else(|| invalid("expected byte count"))?,
            );
        }
        let stats = metrics
            .get_stats("samples")
            .ok_or_else(|| invalid("missing recorded samples"))?;
        let samples = json!({"count":stats.count,"total_ms":stats.total.as_millis(),"avg_ms":stats.average.as_millis(),"min_ms":stats.min.as_millis(),"max_ms":stats.max.as_millis(),"bytes_processed":stats.bytes_processed,"throughput":format!("{:.3}",stats.throughput().ok_or_else(|| invalid("missing throughput"))?)});
        let mut timer = Timer::start("timer");
        timer.set_bytes(
            fixture["timerBytes"]
                .as_u64()
                .ok_or_else(|| invalid("expected timer byte count"))?,
        );
        timer.stop();
        let timing = metrics
            .get_stats("timer")
            .ok_or_else(|| invalid("missing timer"))?;
        let mut operations: Vec<_> = metrics.get_operations();
        operations.sort();
        Ok(
            json!({"missingBefore":missing,"samples":samples,"operations":operations,"timer":{"count":timing.count,"bytes":timing.bytes_processed,"durationValid":timing.min <= timing.average && timing.average <= timing.max && timing.max <= timing.total}}),
        )
    })();
    metrics.clear();
    let mut result = result?;
    result["emptyAfter"] =
        json!(metrics.get_operations().is_empty() && metrics.get_stats("samples").is_none());
    Ok(result)
}
