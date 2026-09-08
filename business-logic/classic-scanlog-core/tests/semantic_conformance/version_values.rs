//! Version value observations using public APIs and fixture-owned registry configuration.
use super::{RunnerResult, invalid, text};
use classic_version_registry_core::{Fallout4Version, GameVersion};
use serde_json::{Value, json};
use std::hash::{Hash, Hasher};

/// Compare hashes as a semantic equality property without exposing unstable hash numbers.
fn same_hash<T: Hash>(left: T, right: T) -> bool {
    let mut a = std::collections::hash_map::DefaultHasher::new();
    let mut b = std::collections::hash_map::DefaultHasher::new();
    left.hash(&mut a);
    right.hash(&mut b);
    a.finish() == b.finish()
}

/// Observe exact public values; dedicated receipt processes isolate singleton initialization.
pub(super) fn execute(family: &str, fixture: &Value) -> RunnerResult<Value> {
    let request = &fixture["request"];
    if family == "game-version-parse" {
        return Ok(
            json!({"parsed":GameVersion::parse(&text(&request["version"])?).ok().map(|v|v.to_string())}),
        );
    }
    if matches!(family, "game-version-distance" | "game-version-order") {
        let a = GameVersion::parse(&text(&request["a"])?)?;
        let b = GameVersion::parse(&text(&request["b"])?)?;
        if family == "game-version-distance" {
            return Ok(json!({"distance":a.semantic_distance(&b)}));
        }
        return Ok(
            json!({"equal":a==b,"less":a<b,"lessEqual":a<=b,"greater":a>b,"greaterEqual":a>=b,"sameMajor":a.same_major(&b),"hashEqualCopy":same_hash(a,GameVersion::parse(&text(&request["a"])?)?)}),
        );
    }
    let temporary = tempfile::tempdir()?;
    let path = temporary.path().join("CLASSIC Main.yaml");
    std::fs::write(&path, text(&fixture["registryYaml"])?)?;
    let previous = std::env::current_dir()?;
    std::env::set_current_dir(temporary.path())?;
    // Initialize from authored bytes before leaving the temporary cwd; later getters use OnceLock.
    // Initialize the singleton only after installing the test-owned YAML root.
    let _ = classic_version_registry_core::get_version_registry();
    std::env::set_current_dir(previous)?;
    let variants = Fallout4Version::all();
    let mut result = if family == "fallout4-identity" {
        json!({"variants":variants.iter().map(|v|json!({"isVr":v.is_vr(),"exeName":v.exe_name(),"steamAppId":v.steam_app_id()})).collect::<Vec<_>>()})
    } else if family == "fallout4-paths" {
        json!({"variants":variants.iter().map(|v|json!({"token":v.as_str(),"docsName":v.docs_folder_name(),"standard":v.is_standard(),"registryId":v.registry_id()})).collect::<Vec<_>>()})
    } else {
        let copies = [
            Fallout4Version::Original,
            Fallout4Version::NextGen,
            Fallout4Version::AnniversaryEdition,
            Fallout4Version::Vr,
        ];
        let aliases = request["aliases"]
            .as_array()
            .ok_or_else(|| invalid("missing version aliases"))?
            .iter()
            .map(|v| Ok(text(v)?.parse::<Fallout4Version>().ok().map(|v| v.as_str())))
            .collect::<RunnerResult<Vec<_>>>()?;
        json!({"variants":variants.iter().enumerate().map(|(i,v)|json!({"version":v.game_version().to_string(),"shortName":v.short_name(),"xse":v.xse_acronym(),"displayName":v.display_name(),"repr":format!("Fallout4Version.{}",v.as_str()),"text":v.as_str(),"equalCopy":*v==copies[i],"hashEqualCopy":same_hash(*v,copies[i])})).collect::<Vec<_>>(),"aliases":aliases})
    };
    let mut files = Vec::new();
    for entry in std::fs::read_dir(temporary.path())? {
        let entry = entry?;
        if !entry.file_type()?.is_file() {
            return Err(invalid("unexpected version fixture artifact").into());
        }
        files.push(json!({"path":entry.file_name().to_string_lossy(),"content":std::fs::read_to_string(entry.path())?}));
    }
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    result["files"] = json!(files);
    Ok(result)
}
