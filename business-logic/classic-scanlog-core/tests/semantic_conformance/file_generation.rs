//! Native generation observations in an isolated process-relative working root.

use super::file_operations::{destination, files};
use super::{RunnerResult, invalid, text};
use classic_file_io_core::generation::{
    FileGenerator, FileGeneratorConfig, generate_ignore_file, generate_local_yaml,
};
use serde_json::{Value, json};
use std::fs;

/// Executes every native generation API and restores cwd after all awaited work.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let game = text(&fixture["game"])?;
    if !matches!(game.as_str(), "Fallout4" | "Fallout4VR") {
        return Err(invalid("invalid generator game").into());
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (path, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        let target = destination(root, path)?;
        fs::create_dir_all(
            target
                .parent()
                .ok_or_else(|| invalid("file needs parent"))?,
        )?;
        fs::write(target, text(content)?.as_bytes())?;
    }
    let previous = std::env::current_dir()?;
    // The dedicated receipt process runs scenarios serially; native generators
    // use relative paths, so every future is joined before restoring the cwd.
    std::env::set_current_dir(root)?;
    let result = (|| -> RunnerResult<Value> {
        let config = FileGeneratorConfig::new(
            text(&fixture["ignore"])?,
            text(&fixture["local"])?,
            game.clone(),
        );
        let generator = FileGenerator::new(config.clone());
        let copied = generator.config();
        if copied.ignore_file_content != config.ignore_file_content
            || copied.local_yaml_content != config.local_yaml_content
            || copied.game_name != config.game_name
        {
            return Err(invalid("generator config accessor changed state").into());
        }
        let mut observation = json!({"paths":[generator.ignore_file_path().to_string_lossy().replace('\\',"/"),generator.local_yaml_path().to_string_lossy().replace('\\',"/")],"before":files(root)?});
        let runtime = classic_shared_core::get_runtime();
        observation["generated"] = json!(runtime.block_on(generator.generate_all_files_async())?);
        observation["existing"] = json!([
            runtime.block_on(generator.generate_ignore_file_async())?,
            runtime.block_on(generator.generate_local_yaml_async())?
        ]);
        observation["standalone"] = json!([
            runtime.block_on(generate_ignore_file("must not replace"))?,
            runtime.block_on(generate_local_yaml("must not replace", game))?
        ]);
        observation["files"] = files(root)?;
        Ok(observation)
    })();
    std::env::set_current_dir(previous)?;
    result
}
