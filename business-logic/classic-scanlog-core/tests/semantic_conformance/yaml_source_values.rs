//! Generic YAML source path and display semantics from the public core enum.
use super::{RunnerResult, invalid, text};
use classic_config_core::YamlSource;
use serde_json::{Value, json};
use std::collections::HashSet;

/// Resolve fixture-selected public variants and retain the complete source matrix.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    let game = text(&fixture["game"])?;
    let mut sources = Vec::new();
    let mut rows = Vec::new();
    for raw in fixture["sources"]
        .as_array()
        .ok_or_else(|| invalid("sources must be an array"))?
    {
        let name = text(raw)?;
        let source = match name.as_str() {
            "MAIN" => YamlSource::Main,
            "IGNORE" => YamlSource::Ignore,
            "GAME" => YamlSource::Game,
            "GAME_LOCAL" => YamlSource::GameLocal,
            "TEST" => YamlSource::Test,
            _ => return Err(invalid("unsupported source variant").into()),
        };
        rows.push(json!({"id": name, "path": source.path(&game).to_string_lossy().replace('\\', "/"), "name": source.display_name(), "gameName": source.display_name_with_game(&game)}));
        sources.push(source);
    }
    Ok(
        json!({"sources": rows, "equal": sources.first() == Some(&YamlSource::Main), "different": sources.first() != sources.get(1), "distinct": sources.iter().collect::<HashSet<_>>().len()}),
    )
}
