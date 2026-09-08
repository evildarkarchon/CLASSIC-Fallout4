//! Shared data-set identity for supported game variants.

/// Returns the canonical game name used by CLASSIC YAML files and keyed data.
///
/// Fallout 4 VR has its own runtime identity for paths, executables, and version
/// selection, but it consumes the same `CLASSIC Fallout4.yaml` data set and
/// `Fallout4`-keyed shared values as the flat-screen release.
pub(crate) fn canonical_game_data_name(game: &str) -> &str {
    match game {
        "Fallout4VR" => "Fallout4",
        _ => game,
    }
}

#[cfg(test)]
#[path = "game_data_tests.rs"]
mod tests;
