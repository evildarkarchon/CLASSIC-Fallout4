//! Stable shared-core tokens and actual shared-runtime access observations.

use super::{RunnerResult, invalid};
use classic_shared_core::{GameId, get_runtime};
use serde_json::{Value, json};

/// Query the public shared owner; never construct a separate Tokio runtime.
pub(super) fn execute(family: &str, _fixture: &Value) -> RunnerResult<Value> {
    match family {
        "game-identity" => Ok(json!({"tokens": GameId::all().map(|game| game.as_str())})),
        "runtime-access" => {
            let mut available = Vec::new();
            let mut diagnostics = Vec::new();
            for _ in 0..2 {
                let runtime = get_runtime();
                // Actual runtime execution establishes usability, while metrics
                // project worker availability without recording host-sized counts.
                available.push(runtime.block_on(async { true }));
                diagnostics.push(runtime.metrics().num_workers() > 0);
            }
            Ok(json!({"available": available, "diagnosticsAvailable": diagnostics}))
        }
        _ => Err(invalid("unsupported shared identity family").into()),
    }
}
