use crate::runtime_support::{block_on, block_on_result};
use classic_config_core::YamlDataCore;
use classic_database_core::{BATCH_CACHE_TTL_SECS, DatabasePool};
use classic_scanlog_core::{
    AnalysisConfig, AnalysisResult, FcxModeHandler, FcxResetError, GLOBAL_FCX_HANDLER,
    OrchestratorCore, build_analysis_config_from_yaml,
};
use classic_settings_core::YamlOperations;
use log::info;
use std::collections::{HashSet, VecDeque};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::time::Duration;

use super::dto::{
    analysis_result_to_batch_dto, analysis_result_to_dto, batch_progress_reset_failure_result,
    batch_reset_failure_result, fcx_issue_to_dto,
};
use super::ffi;
use super::progress::{
    BatchProgressDiagnostics, BatchUpdate, drain_ready_progress_events,
    effective_batch_concurrency, emit_progress_event, make_progress_event,
    make_progress_event_with_current_completed, map_progress_phase, next_batch_update,
};

/// Opaque wrapper holding a fully-loaded AnalysisConfig (from YAML).
pub(crate) struct FullScanConfig {
    inner: AnalysisConfig,
    db_paths: Vec<PathBuf>,
}

/// Opaque wrapper around OrchestratorCore.
pub(crate) struct Orchestrator {
    inner: OrchestratorCore,
    completed_logs: AtomicU64,
    db_counter_interval: u64,
}

const SHORT_SCAN_CACHE_CAPACITY: usize = 30_000;
const SHORT_SCAN_CLEANUP_THRESHOLD: u64 = 4_096;
const SHORT_SCAN_CLEANUP_INTERVAL_SECS: u64 = 300;
const SHORT_SCAN_CACHE_TTL_SECS: u64 = BATCH_CACHE_TTL_SECS;
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

fn apply_short_scan_db_profile(pool: &DatabasePool) {
    pool.set_cache_ttl(Duration::from_secs(SHORT_SCAN_CACHE_TTL_SECS));
    pool.set_cache_capacity(SHORT_SCAN_CACHE_CAPACITY);
    pool.set_cache_cleanup_threshold(SHORT_SCAN_CLEANUP_THRESHOLD);
    pool.set_cache_cleanup_interval(Duration::from_secs(SHORT_SCAN_CLEANUP_INTERVAL_SECS));
}

fn maybe_log_db_perf_counters(orch: &Orchestrator, scanned_path: &str) {
    let completed = orch.completed_logs.fetch_add(1, Ordering::Relaxed) + 1;
    let interval = orch.db_counter_interval;

    if completed % interval != 0 {
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
    let dirs = vec![PathBuf::from(yaml_dir_root), PathBuf::from(yaml_dir_data)];
    let yaml = block_on_result(YamlDataCore::load_from_yaml_files(
        dirs,
        game.to_string(),
        game_version.to_string(),
    ))?;

    let remove_list = load_exclude_log_records(yaml_dir_data);
    let config = build_analysis_config_from_yaml(
        &yaml,
        game,
        game_version,
        show_formid_values,
        fcx_mode,
        simplify_logs,
        remove_list,
    );
    let db_paths = resolve_formid_db_paths(yaml_dir_root, yaml_dir_data, game);
    Ok(Box::new(FullScanConfig {
        inner: config,
        db_paths,
    }))
}

// ── Orchestrator ────────────────────────────────────────────────────

pub(crate) fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>, String> {
    let mut orch = OrchestratorCore::new(config.inner.clone()).map_err(|e| format!("{e}"))?;

    // Match Python behavior: when FormID values are enabled, initialize DB pool
    // with Main + hardcoded + user-configured database paths.
    if config.inner.show_formid_values {
        let pool = Arc::new(DatabasePool::new(
            None,
            Duration::from_secs(SHORT_SCAN_CACHE_TTL_SECS),
            config.inner.game.clone(),
        ));
        apply_short_scan_db_profile(&pool);

        block_on_result(pool.initialize(config.db_paths.clone()))?;

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
    use futures::stream::{self, StreamExt};
    use tokio::sync::mpsc;

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

    let concurrency = effective_batch_concurrency(total, max_concurrent);
    let diagnostics_enabled = diagnostics_enabled();
    let indexed_paths: Vec<(u32, String)> = log_paths
        .iter()
        .cloned()
        .enumerate()
        .map(|(idx, path)| (idx as u32, path))
        .collect();

    block_on(async {
        let mut completed = 0_u32;
        let completed_counter = Arc::new(AtomicU32::new(0));
        let mut batch_results = Vec::with_capacity(indexed_paths.len());
        let mut diagnostics = diagnostics_enabled.then(BatchProgressDiagnostics::default);
        let mut pending_progress_events = VecDeque::new();

        for (input_index, log_path) in &indexed_paths {
            emit_progress_event(
                callback,
                diagnostics.as_mut(),
                // Queued events announce discovered work before any log has finished, so
                // their completed count intentionally stays at the batch-level snapshot of 0.
                make_progress_event(
                    ffi::BatchProgressEventKind::Queued,
                    ffi::BatchProgressPhase::Setup,
                    completed,
                    total as u32,
                    *input_index,
                    log_path,
                    false,
                ),
            );
        }

        let (progress_tx, mut progress_rx) = mpsc::unbounded_channel::<ffi::BatchProgressEvent>();

        let mut tasks = stream::iter(indexed_paths)
            .map(|(input_index, log_path)| {
                let log_path_for_error = log_path.clone();
                let completed_counter = Arc::clone(&completed_counter);
                let progress_tx = progress_tx.clone();
                async move {
                    let started_event = make_progress_event_with_current_completed(
                        ffi::BatchProgressEventKind::Started,
                        ffi::BatchProgressPhase::Setup,
                        completed_counter.as_ref(),
                        total as u32,
                        input_index,
                        &log_path,
                        false,
                    );
                    let _ = progress_tx.send(started_event);

                    let mut last_phase = ffi::BatchProgressPhase::Setup;
                    let result = match orch
                        .inner
                        .process_log_with_progress(log_path.clone(), |phase| {
                            last_phase = map_progress_phase(phase);
                            let _ = progress_tx.send(make_progress_event_with_current_completed(
                                ffi::BatchProgressEventKind::Phase,
                                last_phase,
                                completed_counter.as_ref(),
                                total as u32,
                                input_index,
                                &log_path,
                                false,
                            ));
                        })
                        .await
                    {
                        Ok(result) => result,
                        Err(e) => AnalysisResult::failure(log_path_for_error, e.to_string()),
                    };
                    (input_index, log_path, last_phase, result)
                }
            })
            .buffer_unordered(concurrency);

        while completed < total as u32 {
            match next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks)
                .await
            {
                BatchUpdate::Progress(event) => {
                    emit_progress_event(callback, diagnostics.as_mut(), event);
                }
                BatchUpdate::Result((input_index, scanned_path, last_phase, result)) => {
                    for event in
                        drain_ready_progress_events(&mut pending_progress_events, &mut progress_rx)
                            .await
                    {
                        emit_progress_event(callback, diagnostics.as_mut(), event);
                    }

                    completed += 1;
                    completed_counter.store(completed, Ordering::Relaxed);
                    maybe_log_db_perf_counters(orch, scanned_path.as_str());
                    emit_progress_event(
                        callback,
                        diagnostics.as_mut(),
                        make_progress_event(
                            if result.success {
                                ffi::BatchProgressEventKind::Completed
                            } else {
                                ffi::BatchProgressEventKind::Failed
                            },
                            last_phase,
                            completed,
                            total as u32,
                            input_index,
                            &result.log_path,
                            result.success,
                        ),
                    );
                    batch_results.push(analysis_result_to_batch_dto(
                        input_index,
                        completed,
                        total as u32,
                        result,
                    ));
                }
                BatchUpdate::TasksExhausted => break,
            }
        }

        drop(tasks);
        drop(progress_tx);

        // Any events left here come from an abnormal shutdown path where some task results never
        // surfaced. Keep emitting them for diagnostics, even though they may be orphaned from a
        // terminal Completed/Failed event; under the normal invariant, all logs finish above.
        while let Some(event) = pending_progress_events.pop_front() {
            emit_progress_event(callback, diagnostics.as_mut(), event);
        }

        while let Some(event) = progress_rx.recv().await {
            emit_progress_event(callback, diagnostics.as_mut(), event);
        }

        if let Some(diagnostics) = diagnostics.as_ref() {
            diagnostics.log_summary(total);
        }

        batch_results
    })
}

// ── FormID database path resolution ─────────────────────────────────

fn hardcoded_formid_db_relpaths(game: &str) -> &'static [&'static str] {
    match game {
        "Fallout4" | "Fallout4VR" => &["databases/FOLON FormIDs.db"],
        _ => &[],
    }
}

fn normalize_path(path: PathBuf) -> PathBuf {
    path.components().collect()
}

fn dedupe_paths(paths: Vec<PathBuf>) -> Vec<PathBuf> {
    let mut seen = HashSet::new();
    let mut deduped = Vec::with_capacity(paths.len());
    for path in paths {
        let normalized = normalize_path(path);
        if seen.insert(normalized.clone()) {
            deduped.push(normalized);
        }
    }
    deduped
}

fn load_user_formid_db_paths(yaml_dir_root: &str, yaml_dir_data: &str, game: &str) -> Vec<PathBuf> {
    let settings_path = PathBuf::from(yaml_dir_root).join("CLASSIC Settings.yaml");

    if !settings_path.exists() {
        return Vec::new();
    }

    let ops = YamlOperations::new();
    let doc = match ops.load_yaml_file(Path::new(&settings_path)) {
        Ok(doc) => doc,
        Err(_) => return Vec::new(),
    };

    let key_path = format!("CLASSIC_Settings.FormID Databases.{game}");
    let raw_paths = ops.get_vec_value(&doc, &key_path);
    raw_paths
        .into_iter()
        .map(PathBuf::from)
        .map(|p| {
            if p.is_absolute() {
                normalize_path(p)
            } else {
                normalize_path(PathBuf::from(yaml_dir_data).join(p))
            }
        })
        .collect()
}

fn load_exclude_log_records(yaml_dir_data: &str) -> Vec<String> {
    let main_yaml = PathBuf::from(yaml_dir_data)
        .join("databases")
        .join("CLASSIC Main.yaml");

    if !main_yaml.exists() {
        return Vec::new();
    }

    let ops = YamlOperations::new();
    let doc = match ops.load_yaml_file(Path::new(&main_yaml)) {
        Ok(doc) => doc,
        Err(_) => return Vec::new(),
    };

    ops.get_vec_value(&doc, "exclude_log_records")
}

fn resolve_formid_db_paths(yaml_dir_root: &str, yaml_dir_data: &str, game: &str) -> Vec<PathBuf> {
    let data_dir = PathBuf::from(yaml_dir_data);
    let main_db = data_dir
        .join("databases")
        .join(format!("{game} FormIDs Main.db"));

    let hardcoded = hardcoded_formid_db_relpaths(game)
        .iter()
        .map(|rel| data_dir.join(rel))
        .collect::<Vec<_>>();

    let user_paths = load_user_formid_db_paths(yaml_dir_root, yaml_dir_data, game);

    let mut all_paths = Vec::with_capacity(1 + hardcoded.len() + user_paths.len());
    all_paths.push(main_db);
    all_paths.extend(hardcoded);
    all_paths.extend(user_paths);
    dedupe_paths(all_paths)
}

#[cfg(test)]
#[path = "orchestrator_tests.rs"]
mod tests;
