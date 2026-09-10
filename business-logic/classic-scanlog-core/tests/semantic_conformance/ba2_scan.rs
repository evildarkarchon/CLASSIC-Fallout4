//! Native BA2 scans over independent minimal GNRL and DX10 input archives.

use super::{RunnerResult, invalid};
use classic_scangame_core::{BA2Issues, BA2Scanner};
use serde_json::{Value, json};

/// Projects actual issue vectors and checks native summary methods against their contents.
fn issues(value: &BA2Issues) -> RunnerResult<Value> {
    let total =
        value.tex_dims.len() + value.tex_frmt.len() + value.snd_frmt.len() + value.xse_file.len();
    if value.total_count() != total || value.has_issues() != (total > 0) {
        return Err(invalid("BA2 summary disagrees with issue vectors").into());
    }
    Ok(
        json!({"dimensions":value.tex_dims,"formats":value.tex_frmt,"sounds":value.snd_frmt,"scripts":value.xse_file}),
    )
}

/// Uses only public scanner APIs; the adapter does not parse or classify archive records.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let bytes = fixture["bytes"]
        .as_array()
        .ok_or_else(|| invalid("BA2 bytes must be an array"))?
        .iter()
        .map(|value| {
            value
                .as_u64()
                .and_then(|value| u8::try_from(value).ok())
                .ok_or_else(|| invalid("invalid BA2 byte"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    let path = root.join("fixture.ba2");
    std::fs::write(&path, &bytes)?;
    let scanner = BA2Scanner::new();
    let value = scanner.scan_archive(&path)?;
    let projected = issues(&value)?;
    let custom = BA2Scanner::with_xse_patterns(vec![]).scan_archive(&path)?;
    if !custom.xse_file.is_empty()
        || custom.tex_dims != value.tex_dims
        || custom.tex_frmt != value.tex_frmt
        || custom.snd_frmt != value.snd_frmt
    {
        return Err(invalid("custom XSE patterns changed unrelated issues").into());
    }
    let mut result = json!({"issues":projected,"bytes":std::fs::read(&path)?});
    if fixture["operation"] == "full" {
        let mut found = scanner
            .find_ba2_files(root)
            .iter()
            .map(|path| {
                Ok(path
                    .strip_prefix(root)?
                    .to_string_lossy()
                    .replace('\\', "/"))
            })
            .collect::<RunnerResult<Vec<_>>>()?;
        found.sort();
        let batch = scanner.scan_archives_batch(&[path]);
        let values = batch
            .into_iter()
            .map(|result| Ok(json!(["fixture.ba2", issues(&result?)?])))
            .collect::<RunnerResult<Vec<_>>>()?;
        result["found"] = json!(found);
        result["batch"] = json!(values);
    }
    Ok(result)
}
