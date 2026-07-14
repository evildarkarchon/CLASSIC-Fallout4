//! Regenerates or checks the checked-in CLASSIC_Info.default_settings compatibility mirror.

#[path = "../../default_settings.rs"]
mod default_settings;
mod mirror;

use mirror::{check_compatibility_mirror, replace_compatibility_mirror};
use std::path::{Path, PathBuf};

/// Parses the narrow developer-tool command line.
fn arguments() -> Result<(PathBuf, bool), String> {
    let mut repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let mut check = false;
    let mut args = std::env::args().skip(1);
    while let Some(argument) = args.next() {
        match argument.as_str() {
            "--check" => check = true,
            "--repo-root" => {
                repo_root = args
                    .next()
                    .map(PathBuf::from)
                    .ok_or_else(|| "--repo-root requires a path".to_string())?;
            }
            _ => return Err(format!("unknown argument: {argument}")),
        }
    }
    Ok((repo_root, check))
}

/// Runs mirror generation or a read-only freshness check.
fn run(repo_root: &Path, check: bool) -> Result<(), String> {
    let path = repo_root.join("CLASSIC Data/databases/CLASSIC Main.yaml");
    let source = std::fs::read_to_string(&path)
        .map_err(|error| format!("failed to read {}: {error}", path.display()))?;
    if check {
        return check_compatibility_mirror(&source);
    }
    let generated = replace_compatibility_mirror(&source)?;
    if generated != source {
        std::fs::write(&path, generated)
            .map_err(|error| format!("failed to write {}: {error}", path.display()))?;
    }
    Ok(())
}

/// Reports a concise diagnostic and returns a non-zero status on invalid or stale mirrors.
fn main() {
    let result = arguments().and_then(|(repo_root, check)| run(&repo_root, check));
    if let Err(error) = result {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
