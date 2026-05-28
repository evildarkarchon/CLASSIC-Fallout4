use classic_scanlog_core::papyrus::{PapyrusAnalyzer, PapyrusStats};
use std::path::PathBuf;

use super::ffi;

/// Opaque wrapper around `PapyrusAnalyzer` for CXX FFI.
pub(crate) struct CxxPapyrusAnalyzer {
    inner: PapyrusAnalyzer,
}

/// Convert `PapyrusStats` to the CXX-shared DTO.
fn papyrus_stats_to_dto(stats: &PapyrusStats) -> ffi::PapyrusStatsDto {
    ffi::PapyrusStatsDto {
        dumps: stats.dumps as u32,
        stacks: stats.stacks as u32,
        warnings: stats.warnings as u32,
        errors: stats.errors as u32,
        lines_processed: stats.lines_processed as u32,
        dumps_stacks_ratio: stats.dumps_to_stacks_ratio(),
    }
}

pub(crate) fn papyrus_analyzer_new(log_path: &str) -> Box<CxxPapyrusAnalyzer> {
    Box::new(CxxPapyrusAnalyzer {
        inner: PapyrusAnalyzer::new(PathBuf::from(log_path)),
    })
}

pub(crate) fn papyrus_start_monitoring(analyzer: &mut CxxPapyrusAnalyzer) -> Result<(), String> {
    analyzer
        .inner
        .start_monitoring()
        .map_err(|e| format!("{e}"))
}

pub(crate) fn papyrus_check_updates(analyzer: &mut CxxPapyrusAnalyzer) -> ffi::PapyrusStatsDto {
    // Poll for new data; if there are updates they're folded into internal stats.
    // Errors are silently ignored -- C++ gets the last-known stats either way.
    let _ = analyzer.inner.check_for_updates();
    papyrus_stats_to_dto(analyzer.inner.stats())
}

pub(crate) fn papyrus_analyze_full(
    analyzer: &mut CxxPapyrusAnalyzer,
) -> Result<ffi::PapyrusStatsDto, String> {
    let stats = analyzer.inner.analyze_full().map_err(|e| format!("{e}"))?;
    Ok(papyrus_stats_to_dto(&stats))
}

pub(crate) fn papyrus_log_exists(analyzer: &CxxPapyrusAnalyzer) -> bool {
    analyzer.inner.log_exists()
}

pub(crate) fn papyrus_reset(analyzer: &mut CxxPapyrusAnalyzer) {
    analyzer.inner.reset();
}

#[cfg(test)]
#[path = "papyrus_tests.rs"]
mod tests;
