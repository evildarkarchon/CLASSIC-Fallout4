//! Stable shared-core tokens and actual shared-runtime access observations.

use super::{RunnerResult, invalid};
use classic_shared_core::{GameId, get_runtime};
use serde_json::{Value, json};

/// Query the public shared owner; never construct a separate Tokio runtime.
pub(super) fn execute(family: &str, fixture: &Value) -> RunnerResult<Value> {
    match family {
        "game-identity" => {
            let games = GameId::all();
            if fixture["request"]["operation"] == "metadata" {
                return Ok(json!({"labels": games.map(|game| game.display_name())}));
            }
            if fixture["request"]["operation"] == "details" {
                use std::hash::{Hash, Hasher};
                let values = games.iter().enumerate().map(|(index, game)| {
                    let copy: GameId = game.as_str().parse().expect("public token parses");
                    let mut left = std::collections::hash_map::DefaultHasher::new();
                    let mut right = std::collections::hash_map::DefaultHasher::new();
                    game.hash(&mut left); copy.hash(&mut right);
                    json!({"exeName": game.exe_name(), "vr": game.is_vr(), "text": game.to_string(), "repr": format!("GameId.{game:?}"), "equalCopy": *game == copy, "equalOther": *game == games[(index+1)%games.len()], "hashCopy": left.finish() == right.finish()})
                }).collect::<Vec<_>>();
                return Ok(json!({"games": values}));
            }
            Ok(json!({"tokens": games.map(|game| game.as_str())}))
        }
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
