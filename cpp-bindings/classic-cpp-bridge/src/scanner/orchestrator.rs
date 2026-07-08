use crate::runtime_support::{block_on, block_on_result};
use classic_database_core::DatabasePool;
use classic_scanlog_core::{
    AnalysisConfig, BatchScanEventKind, BatchScanOptions, CrashLogScanIntake, CrashLogScanOptions,
    CrashLogScanRun, CrashLogScanRunEventKind, CrashLogScanRunIntent, CrashLogScanRunRequest,
    FcxModeHandler, FcxResetError, GLOBAL_FCX_HANDLER, OrchestratorCore, SHORT_SCAN_CACHE_PROFILE,
    ScanReadyAnalysis, StandardCrashLogScanRunIntent, StandardUnsolvedLogsIntent,
    load_simplify_remove_list as core_load_simplify_remove_list,
    resolve_formid_database_paths as core_resolve_formid_database_paths,
    resolve_user_formid_database_paths as core_resolve_user_formid_database_paths,
};
use log::info;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::time::Duration;

use super::dto::{
    analysis_result_to_batch_dto, analysis_result_to_dto, batch_progress_reset_failure_result,
    batch_reset_failure_result, fcx_issue_to_dto, scan_run_log_outcome_to_dto,
};
use super::ffi;
use super::progress::{
    BatchProgressDiagnostics, emit_progress_event, make_progress_event, map_progress_phase,
};

/// Opaque wrapper holding a fully-loaded AnalysisConfig (from YAML).
pub(crate) struct FullScanConfig {
    prepared: ScanReadyAnalysis,
}

/// Opaque wrapper around OrchestratorCore.
pub(crate) struct Orchestrator {
    inner: OrchestratorCore,
    completed_logs: AtomicU64,
    db_counter_interval: u64,
}

pub(crate) struct ScanCancellationToken {
    cancelled: Arc<AtomicBool>,
}

const SHORT_SCAN_CACHE_CAPACITY: usize = SHORT_SCAN_CACHE_PROFILE.cache_capacity;
const SHORT_SCAN_CLEANUP_THRESHOLD: u64 = SHORT_SCAN_CACHE_PROFILE.cleanup_threshold;
const SHORT_SCAN_CLEANUP_INTERVAL_SECS: u64 = SHORT_SCAN_CACHE_PROFILE.cleanup_interval_secs;
const SHORT_SCAN_CACHE_TTL_SECS: u64 = SHORT_SCAN_CACHE_PROFILE.cache_ttl_secs;
const DB_COUNTER_LOG_INTERVAL_DEFAULT: u64 = 25;

fn diagnostics_enabled() -> bool {
    std::env::var_os("CLASSIC_SCAN_DIAGNOSTICS").is_some()
}

fn parse_db_counter_interval(raw: Option<&str>) -> u64 {
    raw.and_then(|value| value.trim().parse::<u64>().ok())
        .filter(|interval| *interval > 0)
        .unwrap_or(DB_COUNTER_LOG_INTERVAL_DEFAULT)
}

fn resolve_db_counter_interval() -> u64 {
    parse_db_counter_interval(std::env::var("CLASSIC_DB_COUNTER_INTERVAL").ok().as_deref())
}

pub(crate) fn scan_cancellation_token_new() -> Box<ScanCancellationToken> {
    Box::new(ScanCancellationToken {
        cancelled: Arc::new(AtomicBool::new(false)),
    })
}

pub(crate) fn scan_cancellation_token_cancel(token: &ScanCancellationToken) {
    token.cancelled.store(true, Ordering::Relaxed);
}

pub(crate) fn scan_cancellation_token_reset(token: &ScanCancellationToken) {
    token.cancelled.store(false, Ordering::Relaxed);
}

fn apply_short_scan_db_profile(
    pool: &DatabasePool,
    profile: classic_scanlog_core::ShortScanCacheProfile,
) {
    profile.apply_to_pool(pool);
}

fn maybe_log_db_perf_counters(orch: &Orchestrator, scanned_path: &str) {
    let completed = orch.completed_logs.fetch_add(1, Ordering::Relaxed) + 1;
    let interval = orch.db_counter_interval;

    if !completed.is_multiple_of(interval) {
        return;
    }

    let Some(pool) = orch.inner.database_pool() else {
        return;
    };

    let Ok(stats) = pool.get_stats() else {
        return;
    };

    let cache_queries = stats.cache_hits.saturating_add(stats.cache_misses);
    let cache_hit_rate = if cache_queries == 0 {
        0.0
    } else {
        (stats.cache_hits as f64 / cache_queries as f64) * 100.0
    };
    let log_name = Path::new(scanned_path)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or(scanned_path);

    info!(
        "DB counters @{} logs (last={}): cache_size={}/{}, cache_hits={}, cache_misses={}, hit_rate={:.1}%, evictions={}, cleanup_runs={}, cleanup_removed={}, cleanup_total_ms={:.3}, cleanup_max_ms={:.3}, eviction_total_ms={:.3}, eviction_max_ms={:.3}, stable_shape_selections={}, stable_shape_padding_pairs={}",
        completed,
        log_name,
        pool.cache_size(),
        pool.get_cache_capacity(),
        stats.cache_hits,
        stats.cache_misses,
        cache_hit_rate,
        stats.cache_evictions,
        stats.cleanup_runs,
        stats.cleanup_removed,
        stats.cleanup_elapsed_total_ns as f64 / 1_000_000.0,
        stats.cleanup_elapsed_max_ns as f64 / 1_000_000.0,
        stats.eviction_elapsed_total_ns as f64 / 1_000_000.0,
        stats.eviction_elapsed_max_ns as f64 / 1_000_000.0,
        stats.stable_shape_selections,
        stats.stable_shape_padding_pairs
    );
}

pub(crate) fn fcx_reset_global_state() -> Result<(), String> {
    match FcxModeHandler::reset_global_state() {
        Ok(()) | Err(FcxResetError::Unnecessary) => Ok(()),
        Err(error) => Err(error.to_string()),
    }
}

/// Return a snapshot of all FCX configuration issues currently held in the global handler.
///
/// # Empty-state contract
///
/// - Fresh process (no scan run): lazy-init handler has no issues → returns empty Vec.
/// - After `fcx_reset_global_state()`: detected_issues cleared → returns empty Vec.
/// - After scan with no FCX issues: returns empty Vec.
/// - After scan with issues: returns one `FcxIssueDto` per `ConfigIssue`, order preserved.
///
/// # No-throw guarantee
///
/// The function is infallible. It uses `parking_lot::Mutex::lock()` which blocks until
/// acquired and never returns an error. Callers on the C++ side wrap it in `try` as a
/// belt-and-suspenders convention, but the fn itself cannot panic under normal operation.
pub(crate) fn get_fcx_config_issues() -> Vec<ffi::FcxIssueDto> {
    // parking_lot::Mutex::lock() returns the guard directly — no Result unwrap needed.
    let handler = GLOBAL_FCX_HANDLER.lock();
    handler
        .get_detected_issues()
        .iter()
        .map(fcx_issue_to_dto)
        .collect()
}

// ── Config construction ─────────────────────────────────────────────

pub(crate) fn build_full_scan_config(
    yaml_dir_root: &str,
    yaml_dir_data: &str,
    game: &str,
    game_version: &str,
    show_formid_values: bool,
    fcx_mode: bool,
    simplify_logs: bool,
) -> Result<Box<FullScanConfig>, String> {
    let options = CrashLogScanOptions::new(show_formid_values, fcx_mode, simplify_logs);
    let prepared = block_on_result(
        CrashLogScanIntake::from_yaml_paths(
            yaml_dir_root,
            yaml_dir_data,
            game,
            game_version,
            options,
        )
        .prepare(),
    )?;

    Ok(Box::new(FullScanConfig { prepared }))
}

// ── Orchestrator ────────────────────────────────────────────────────

pub(crate) fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>, String> {
    let mut orch = OrchestratorCore::new(config.prepared.analysis_config().clone())
        .map_err(|e| format!("{e}"))?;

    // Match Python behavior: when FormID values are enabled, initialize DB pool
    // with intake-selected Main + hardcoded + user-configured database paths.
    if config.prepared.should_initialize_formid_database() {
        let cache_profile = config.prepared.cache_profile();
        let pool = Arc::new(DatabasePool::new(
            None,
            Duration::from_secs(cache_profile.cache_ttl_secs),
            config.prepared.analysis_config().game.clone(),
        ));
        apply_short_scan_db_profile(&pool, cache_profile);

        block_on_result(
            pool.initialize(config.prepared.formid_readiness().database_paths().to_vec()),
        )?;

        orch.attach_database_pool(pool)
            .map_err(|e| format!("{e}"))?;
    }

    Ok(Box::new(Orchestrator {
        inner: orch,
        completed_logs: AtomicU64::new(0),
        db_counter_interval: resolve_db_counter_interval(),
    }))
}

pub(crate) fn orchestrator_new_minimal(
    game: &str,
    game_version: &str,
    crashgen_name: &str,
    xse_acronym: &str,
) -> Result<Box<Orchestrator>, String> {
    let mut config = AnalysisConfig::new(game.to_string(), game_version.to_string());
    config.crashgen_name = crashgen_name.to_string();
    config.xse_acronym = xse_acronym.to_string();
    let orch = OrchestratorCore::new(config).map_err(|e| format!("{e}"))?;
    Ok(Box::new(Orchestrator {
        inner: orch,
        completed_logs: AtomicU64::new(0),
        db_counter_interval: resolve_db_counter_interval(),
    }))
}

pub(crate) fn orchestrator_process_log(
    orch: &Orchestrator,
    log_path: &str,
) -> Result<ffi::ScanResult, String> {
    fcx_reset_global_state()?;

    match block_on(orch.inner.process_log(log_path.to_string())) {
        Ok(result) => {
            maybe_log_db_perf_counters(orch, result.log_path.as_str());
            Ok(analysis_result_to_dto(result))
        }
        Err(e) => {
            maybe_log_db_perf_counters(orch, log_path);
            Err(format!("{e}"))
        }
    }
}

pub(crate) fn orchestrator_process_logs_batch(
    orch: &Orchestrator,
    log_paths: &[String],
    max_concurrent: u32,
) -> Vec<ffi::ScanResult> {
    if let Err(error) = fcx_reset_global_state() {
        let log_path = log_paths.first().cloned().unwrap_or_default();
        return vec![batch_reset_failure_result(log_path, error)];
    }

    let paths: Vec<String> = log_paths.to_vec();
    let max_parallel = if max_concurrent == 0 {
        None
    } else {
        Some(max_concurrent as usize)
    };
    let results = block_on(orch.inner.process_logs_batch(paths, max_parallel));
    for result in &results {
        maybe_log_db_perf_counters(orch, result.log_path.as_str());
    }
    results.into_iter().map(analysis_result_to_dto).collect()
}

pub(crate) fn orchestrator_process_logs_batch_with_progress(
    orch: &Orchestrator,
    log_paths: &[String],
    max_concurrent: u32,
    callback: &ffi::ScanBatchProgressCallback,
) -> Vec<ffi::BatchScanResult> {
    if let Err(error) = fcx_reset_global_state() {
        let log_path = log_paths.first().cloned().unwrap_or_default();
        return vec![batch_progress_reset_failure_result(
            0,
            log_paths.len() as u32,
            log_path,
            error,
        )];
    }

    let total = log_paths.len();
    if total == 0 {
        return Vec::new();
    }

    let diagnostics_enabled = diagnostics_enabled();
    let paths = log_paths.to_vec();
    let max_parallel = if max_concurrent == 0 {
        None
    } else {
        Some(max_concurrent as usize)
    };
    block_on(async {
        let mut diagnostics = diagnostics_enabled.then(BatchProgressDiagnostics::default);
        let indexed_results = orch
            .inner
            .process_logs_batch_with_events(
                paths,
                BatchScanOptions {
                    max_concurrent: max_parallel,
                    preserve_order: false,
                    cancellation: None,
                },
                |event| {
                    let event_kind = match event.kind {
                        BatchScanEventKind::Queued => ffi::BatchProgressEventKind::Queued,
                        BatchScanEventKind::Started => ffi::BatchProgressEventKind::Started,
                        BatchScanEventKind::Phase => ffi::BatchProgressEventKind::Phase,
                        BatchScanEventKind::Completed => ffi::BatchProgressEventKind::Completed,
                        BatchScanEventKind::Failed => ffi::BatchProgressEventKind::Failed,
                    };
                    emit_progress_event(
                        callback,
                        diagnostics.as_mut(),
                        make_progress_event(
                            event_kind,
                            map_progress_phase(event.phase),
                            event.completed as u32,
                            event.total as u32,
                            event.input_index as u32,
                            &event.log_path,
                            event.success,
                        ),
                    );
                },
            )
            .await;

        if let Some(diagnostics) = diagnostics.as_ref() {
            diagnostics.log_summary(total);
        }

        indexed_results
            .into_iter()
            .map(|indexed| {
                maybe_log_db_perf_counters(orch, indexed.result.log_path.as_str());
                analysis_result_to_batch_dto(
                    indexed.input_index as u32,
                    indexed.completed as u32,
                    indexed.total as u32,
                    indexed.result,
                )
            })
            .collect()
    })
}

pub(crate) fn scan_run_execute(
    request: &ffi::ScanRunRequestDto,
    callback: &ffi::ScanBatchProgressCallback,
    cancellation_token: &ScanCancellationToken,
) -> Result<Vec<ffi::ScanRunLogResult>, String> {
    let options = CrashLogScanOptions::new(
        request.show_formid_values,
        request.fcx_mode,
        request.simplify_logs,
    );
    let prepared = block_on_result(
        CrashLogScanIntake::from_yaml_paths(
            request.yaml_dir_root.as_str(),
            request.yaml_dir_data.as_str(),
            request.game.as_str(),
            request.game_version.as_str(),
            options,
        )
        .prepare(),
    )?;

    let intent = scan_run_intent_from_request(request);

    let max_parallel = if request.max_concurrent == 0 {
        None
    } else {
        Some(request.max_concurrent as usize)
    };
    let run = CrashLogScanRun::new(prepared);
    let run_request = CrashLogScanRunRequest {
        logs: request
            .log_paths
            .iter()
            .map(|path| PathBuf::from(path.as_str()))
            .collect(),
        intent,
        max_concurrent: max_parallel,
        cancellation: Some(Arc::clone(&cancellation_token.cancelled)),
        preserve_order: false,
    };

    let result = block_on_result(run.run(run_request, |event| {
        let log_path = event.crash_log.to_string_lossy();
        callback.on_batch_progress(&make_progress_event(
            match event.kind {
                CrashLogScanRunEventKind::Queued => ffi::BatchProgressEventKind::Queued,
                CrashLogScanRunEventKind::Started => ffi::BatchProgressEventKind::Started,
                CrashLogScanRunEventKind::Phase => ffi::BatchProgressEventKind::Phase,
                CrashLogScanRunEventKind::Completed => ffi::BatchProgressEventKind::Completed,
                CrashLogScanRunEventKind::Failed => ffi::BatchProgressEventKind::Failed,
            },
            map_progress_phase(event.phase),
            event.completed as u32,
            event.total as u32,
            event.input_index as u32,
            log_path.as_ref(),
            event.success,
        ));
    }))?;

    Ok(result
        .logs
        .into_iter()
        .map(scan_run_log_outcome_to_dto)
        .collect())
}

fn scan_run_intent_from_request(request: &ffi::ScanRunRequestDto) -> CrashLogScanRunIntent {
    if request.targeted_mode {
        return CrashLogScanRunIntent::Targeted;
    }

    let unsolved_logs = if !request.move_unsolved_logs {
        StandardUnsolvedLogsIntent::LeaveInPlace
    } else {
        let destination = request.unsolved_logs_destination.trim();
        if destination.is_empty() {
            StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault
        } else {
            StandardUnsolvedLogsIntent::MoveToCustom(PathBuf::from(destination))
        }
    };

    CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent { unsolved_logs })
}

// ── FormID database path resolution ─────────────────────────────────

fn load_user_formid_db_paths(yaml_dir_root: &str, yaml_dir_data: &str, game: &str) -> Vec<PathBuf> {
    core_resolve_user_formid_database_paths(yaml_dir_root, yaml_dir_data, game)
}

fn load_exclude_log_records(yaml_dir_data: &str) -> Vec<String> {
    core_load_simplify_remove_list(yaml_dir_data)
}

fn resolve_formid_db_paths(yaml_dir_root: &str, yaml_dir_data: &str, game: &str) -> Vec<PathBuf> {
    core_resolve_formid_database_paths(yaml_dir_root, yaml_dir_data, game)
}

#[cfg(test)]
#[path = "orchestrator_tests.rs"]
mod tests;
