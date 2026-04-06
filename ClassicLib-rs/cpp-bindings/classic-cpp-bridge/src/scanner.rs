//! Crash log scanning bridge for CXX FFI.
//!
//! Bridges `classic_scanlog_core::OrchestratorCore` for crash log analysis.
//! This is the PRIMARY FEATURE of the CLASSIC application.
//! Placeholder — will be implemented by Wave 2 agent.

use classic_config_core::YamlDataCore;
use classic_database_core::{BATCH_CACHE_TTL_SECS, DatabasePool};
use classic_scanlog_core::papyrus::{PapyrusAnalyzer, PapyrusStats};
use classic_scanlog_core::{
    AnalysisConfig, AnalysisResult, FcxModeHandler, FcxResetError, OrchestratorCore,
    ScanProgressPhase, build_analysis_config_from_yaml,
};
use classic_shared_core::get_runtime;
use classic_yaml_core::YamlOperations;
use log::info;
use std::collections::{HashSet, VecDeque};
use std::path::Path;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::time::Duration;

/// Opaque wrapper holding a fully-loaded AnalysisConfig (from YAML).
pub struct FullScanConfig {
    inner: AnalysisConfig,
    db_paths: Vec<PathBuf>,
}

/// Opaque wrapper around OrchestratorCore.
pub struct Orchestrator {
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

fn map_progress_phase(phase: ScanProgressPhase) -> ffi::BatchProgressPhase {
    match phase {
        ScanProgressPhase::Setup => ffi::BatchProgressPhase::Setup,
        ScanProgressPhase::Parse => ffi::BatchProgressPhase::Parse,
        ScanProgressPhase::Analyze => ffi::BatchProgressPhase::Analyze,
        ScanProgressPhase::Finalize => ffi::BatchProgressPhase::Finalize,
    }
}

fn event_rank(kind: ffi::BatchProgressEventKind, phase: ffi::BatchProgressPhase) -> u8 {
    match kind {
        ffi::BatchProgressEventKind::Queued => 0,
        ffi::BatchProgressEventKind::Started => 1,
        ffi::BatchProgressEventKind::Phase => match phase {
            ffi::BatchProgressPhase::Setup => 2,
            ffi::BatchProgressPhase::Parse => 3,
            ffi::BatchProgressPhase::Analyze => 4,
            ffi::BatchProgressPhase::Finalize => 5,
            _ => 5,
        },
        ffi::BatchProgressEventKind::Completed | ffi::BatchProgressEventKind::Failed => 6,
        _ => 6,
    }
}

fn make_progress_event(
    event_kind: ffi::BatchProgressEventKind,
    phase: ffi::BatchProgressPhase,
    completed: u32,
    total: u32,
    input_index: u32,
    log_path: &str,
    success: bool,
) -> ffi::BatchProgressEvent {
    ffi::BatchProgressEvent {
        completed,
        total,
        input_index,
        log_path: log_path.to_string(),
        event_kind,
        phase,
        success,
    }
}

fn make_progress_event_with_current_completed(
    event_kind: ffi::BatchProgressEventKind,
    phase: ffi::BatchProgressPhase,
    completed_counter: &AtomicU32,
    total: u32,
    input_index: u32,
    log_path: &str,
    success: bool,
) -> ffi::BatchProgressEvent {
    make_progress_event(
        event_kind,
        phase,
        completed_counter.load(Ordering::Relaxed),
        total,
        input_index,
        log_path,
        success,
    )
}

#[derive(Default)]
struct BatchProgressDiagnostics {
    queued_events: u32,
    started_events: u32,
    phase_events: u32,
    completed_events: u32,
    failed_events: u32,
    in_flight_logs: HashSet<u32>,
    max_in_flight: usize,
}

impl BatchProgressDiagnostics {
    fn record(&mut self, event: &ffi::BatchProgressEvent) {
        match event.event_kind {
            ffi::BatchProgressEventKind::Queued => {
                self.queued_events += 1;
            }
            ffi::BatchProgressEventKind::Started => {
                self.started_events += 1;
                self.in_flight_logs.insert(event.input_index);
            }
            ffi::BatchProgressEventKind::Phase => {
                self.phase_events += 1;
            }
            ffi::BatchProgressEventKind::Completed => {
                self.completed_events += 1;
                self.in_flight_logs.remove(&event.input_index);
            }
            ffi::BatchProgressEventKind::Failed => {
                self.failed_events += 1;
                self.in_flight_logs.remove(&event.input_index);
            }
            _ => {}
        }
        self.max_in_flight = self.max_in_flight.max(self.in_flight_logs.len());
    }

    fn log_summary(&self, total: usize) {
        info!(
            "Batch progress diagnostics: total_logs={}, queued={}, started={}, phase={}, completed={}, failed={}, max_in_flight={}",
            total,
            self.queued_events,
            self.started_events,
            self.phase_events,
            self.completed_events,
            self.failed_events,
            self.max_in_flight,
        );
    }
}

fn emit_progress_event(
    callback: &ffi::ScanBatchProgressCallback,
    diagnostics: Option<&mut BatchProgressDiagnostics>,
    event: ffi::BatchProgressEvent,
) {
    if let Some(diagnostics) = diagnostics {
        diagnostics.record(&event);
        info!(
            "Batch progress event: idx={}, kind={:?}, phase={:?}, completed={}/{}, success={}, log={}",
            event.input_index,
            event.event_kind,
            event.phase,
            event.completed,
            event.total,
            event.success,
            event.log_path,
        );
    }
    callback.on_batch_progress(&event);
}

type BatchTaskResult = (u32, String, ffi::BatchProgressPhase, AnalysisResult);

const READY_PROGRESS_DRAIN_MAX_EMPTY_YIELDS: usize = 2;

enum BatchUpdate {
    Progress(ffi::BatchProgressEvent),
    Result(BatchTaskResult),
    TasksExhausted,
}

/// Drain all progress currently visible to preserve global event ordering before emitting the
/// terminal Completed/Failed event for a finished task.
async fn drain_ready_progress_events(
    pending_progress_events: &mut VecDeque<ffi::BatchProgressEvent>,
    progress_rx: &mut tokio::sync::mpsc::UnboundedReceiver<ffi::BatchProgressEvent>,
) -> Vec<ffi::BatchProgressEvent> {
    let mut events = Vec::new();

    while let Some(event) = pending_progress_events.pop_front() {
        events.push(event);
    }

    let mut empty_yields_remaining = READY_PROGRESS_DRAIN_MAX_EMPTY_YIELDS;
    loop {
        match progress_rx.try_recv() {
            Ok(event) => {
                events.push(event);
                empty_yields_remaining = READY_PROGRESS_DRAIN_MAX_EMPTY_YIELDS;
            }
            Err(tokio::sync::mpsc::error::TryRecvError::Empty) if empty_yields_remaining > 0 => {
                // A same-log phase send can be queued a couple runtime turns after the task
                // result becomes visible. Yield a small, bounded number of times so already-
                // scheduled sends can land before the terminal event without paying the old
                // eight-yield busy-poll cost on every empty drain.
                empty_yields_remaining -= 1;
                tokio::task::yield_now().await;
            }
            Err(tokio::sync::mpsc::error::TryRecvError::Empty) => break,
            Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => {
                // The sender side is gone, so only already-buffered task results remain.
                break;
            }
        }
    }

    events
}

async fn next_batch_update<S>(
    pending_progress_events: &mut VecDeque<ffi::BatchProgressEvent>,
    progress_rx: &mut tokio::sync::mpsc::UnboundedReceiver<ffi::BatchProgressEvent>,
    tasks: &mut S,
) -> BatchUpdate
where
    S: futures::stream::Stream<Item = BatchTaskResult> + Unpin,
{
    use futures::StreamExt;

    if let Some(event) = pending_progress_events.pop_front() {
        return BatchUpdate::Progress(event);
    }

    tokio::select! {
        biased;
        maybe_event = progress_rx.recv() => {
            match maybe_event {
                Some(event) => BatchUpdate::Progress(event),
                None => match tasks.next().await {
                    Some(result) => BatchUpdate::Result(result),
                    None => BatchUpdate::TasksExhausted,
                },
            }
        }
        maybe_result = tasks.next() => {
            match maybe_result {
                Some(result) => BatchUpdate::Result(result),
                None => BatchUpdate::TasksExhausted,
            }
        }
    }
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

fn fcx_reset_global_state() -> Result<(), String> {
    match FcxModeHandler::reset_global_state() {
        Ok(()) | Err(FcxResetError::Unnecessary) => Ok(()),
        Err(error) => Err(error.to_string()),
    }
}

fn batch_reset_failure_result(log_path: String, error_message: String) -> ffi::ScanResult {
    ffi::ScanResult {
        log_path,
        success: false,
        report_lines: Vec::new(),
        error_message,
        processing_time_ms: 0,
        formid_count: 0,
        plugin_count: 0,
        suspect_count: 0,
    }
}

fn batch_progress_reset_failure_result(
    input_index: u32,
    total: u32,
    log_path: String,
    error_message: String,
) -> ffi::BatchScanResult {
    ffi::BatchScanResult {
        input_index,
        completed: 0,
        total,
        log_path,
        success: false,
        report_lines: Vec::new(),
        error_message,
        processing_time_ms: 0,
        formid_count: 0,
        plugin_count: 0,
        suspect_count: 0,
    }
}

// ── Config construction ─────────────────────────────────────────────

fn build_full_scan_config(
    yaml_dir_root: &str,
    yaml_dir_data: &str,
    game: &str,
    game_version: &str,
    show_formid_values: bool,
    fcx_mode: bool,
    simplify_logs: bool,
) -> Result<Box<FullScanConfig>, String> {
    let dirs = vec![PathBuf::from(yaml_dir_root), PathBuf::from(yaml_dir_data)];
    let yaml = get_runtime()
        .block_on(YamlDataCore::load_from_yaml_files(
            dirs,
            game.to_string(),
            game_version.to_string(),
        ))
        .map_err(|e| format!("{e}"))?;

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

fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>, String> {
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

        get_runtime()
            .block_on(pool.initialize(config.db_paths.clone()))
            .map_err(|e| format!("{e}"))?;

        orch.attach_database_pool(pool)
            .map_err(|e| format!("{e}"))?;
    }

    Ok(Box::new(Orchestrator {
        inner: orch,
        completed_logs: AtomicU64::new(0),
        db_counter_interval: resolve_db_counter_interval(),
    }))
}

fn orchestrator_new_minimal(
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

fn orchestrator_process_log(
    orch: &Orchestrator,
    log_path: &str,
) -> Result<ffi::ScanResult, String> {
    fcx_reset_global_state()?;

    match get_runtime().block_on(orch.inner.process_log(log_path.to_string())) {
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

fn orchestrator_process_logs_batch(
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
    let results = get_runtime().block_on(orch.inner.process_logs_batch(paths, max_parallel));
    for result in &results {
        maybe_log_db_perf_counters(orch, result.log_path.as_str());
    }
    results.into_iter().map(analysis_result_to_dto).collect()
}

fn effective_batch_concurrency(total_logs: usize, max_concurrent: u32) -> usize {
    if total_logs == 0 {
        return 1;
    }
    if max_concurrent > 0 {
        return (max_concurrent as usize).max(1);
    }

    let cpu_count = std::thread::available_parallelism()
        .map(std::num::NonZeroUsize::get)
        .unwrap_or(4);

    if total_logs < cpu_count {
        total_logs.max(1)
    } else {
        cpu_count.max(4)
    }
}

fn orchestrator_process_logs_batch_with_progress(
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

    get_runtime().block_on(async {
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

fn analysis_result_to_dto(r: AnalysisResult) -> ffi::ScanResult {
    ffi::ScanResult {
        log_path: r.log_path,
        success: r.success,
        report_lines: r.report_lines,
        error_message: r.error.unwrap_or_default(),
        processing_time_ms: r.processing_time_ms,
        formid_count: r.formid_count as u32,
        plugin_count: r.plugin_count as u32,
        suspect_count: r.suspect_count as u32,
    }
}

fn analysis_result_to_batch_dto(
    input_index: u32,
    completed: u32,
    total: u32,
    r: AnalysisResult,
) -> ffi::BatchScanResult {
    ffi::BatchScanResult {
        input_index,
        completed,
        total,
        log_path: r.log_path,
        success: r.success,
        report_lines: r.report_lines,
        error_message: r.error.unwrap_or_default(),
        processing_time_ms: r.processing_time_ms,
        formid_count: r.formid_count as u32,
        plugin_count: r.plugin_count as u32,
        suspect_count: r.suspect_count as u32,
    }
}

// ── Utility functions ───────────────────────────────────────────────

fn detect_vr_log(content: &str) -> bool {
    // VR logs contain "Fallout4VR.esm" or "SkyrimVR.esm" in plugin list
    content.contains("Fallout4VR.esm") || content.contains("SkyrimVR.esm")
}

fn detect_crash_pattern(content: &str) -> String {
    // Parse the crash header to extract the main error/crash module
    let parser = classic_scanlog_core::LogParser::new(None).unwrap();
    let lines: Vec<String> = content.lines().map(|l| l.to_string()).collect();
    match parser.parse_crash_header(&lines) {
        Ok(header) => header.get("main_error").cloned().unwrap_or_default(),
        Err(_) => String::new(),
    }
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

// ── Papyrus monitoring ────────────────────────────────────────────

/// Opaque wrapper around `PapyrusAnalyzer` for CXX FFI.
pub struct CxxPapyrusAnalyzer {
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

fn papyrus_analyzer_new(log_path: &str) -> Box<CxxPapyrusAnalyzer> {
    Box::new(CxxPapyrusAnalyzer {
        inner: PapyrusAnalyzer::new(PathBuf::from(log_path)),
    })
}

fn papyrus_start_monitoring(analyzer: &mut CxxPapyrusAnalyzer) -> Result<(), String> {
    analyzer
        .inner
        .start_monitoring()
        .map_err(|e| format!("{e}"))
}

fn papyrus_check_updates(analyzer: &mut CxxPapyrusAnalyzer) -> ffi::PapyrusStatsDto {
    // Poll for new data; if there are updates they're folded into internal stats.
    // Errors are silently ignored -- C++ gets the last-known stats either way.
    let _ = analyzer.inner.check_for_updates();
    papyrus_stats_to_dto(analyzer.inner.stats())
}

fn papyrus_analyze_full(analyzer: &mut CxxPapyrusAnalyzer) -> Result<ffi::PapyrusStatsDto, String> {
    let stats = analyzer.inner.analyze_full().map_err(|e| format!("{e}"))?;
    Ok(papyrus_stats_to_dto(&stats))
}

fn papyrus_log_exists(analyzer: &CxxPapyrusAnalyzer) -> bool {
    analyzer.inner.log_exists()
}

fn papyrus_reset(analyzer: &mut CxxPapyrusAnalyzer) {
    analyzer.inner.reset();
}

#[cxx::bridge(namespace = "classic::scanner")]
mod ffi {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum BatchProgressEventKind {
        Queued = 0,
        Started = 1,
        Phase = 2,
        Completed = 3,
        Failed = 4,
    }

    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum BatchProgressPhase {
        Setup = 0,
        Parse = 1,
        Analyze = 2,
        Finalize = 3,
    }

    struct BatchProgressEvent {
        completed: u32,
        total: u32,
        input_index: u32,
        log_path: String,
        event_kind: BatchProgressEventKind,
        phase: BatchProgressPhase,
        success: bool,
    }

    /// Result of scanning a single crash log.
    struct ScanResult {
        log_path: String,
        success: bool,
        report_lines: Vec<String>,
        error_message: String,
        processing_time_ms: u64,
        formid_count: u32,
        plugin_count: u32,
        suspect_count: u32,
    }

    /// Batch scan result plus progress metadata for each completed log.
    struct BatchScanResult {
        input_index: u32,
        completed: u32,
        total: u32,
        log_path: String,
        success: bool,
        report_lines: Vec<String>,
        error_message: String,
        processing_time_ms: u64,
        formid_count: u32,
        plugin_count: u32,
        suspect_count: u32,
    }

    /// Papyrus log statistics transferred across the FFI boundary.
    struct PapyrusStatsDto {
        dumps: u32,
        stacks: u32,
        warnings: u32,
        errors: u32,
        lines_processed: u32,
        dumps_stacks_ratio: f64,
    }

    unsafe extern "C++" {
        include!("classic_cxx_bridge/scan_progress_callback.h");
        type ScanBatchProgressCallback;
        fn on_batch_progress(self: &ScanBatchProgressCallback, event: &BatchProgressEvent);
    }

    extern "Rust" {
        type FullScanConfig;
        type Orchestrator;

        // Config construction
        fn build_full_scan_config(
            yaml_dir_root: &str,
            yaml_dir_data: &str,
            game: &str,
            game_version: &str,
            show_formid_values: bool,
            fcx_mode: bool,
            simplify_logs: bool,
        ) -> Result<Box<FullScanConfig>>;

        // Orchestrator
        fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>>;
        fn orchestrator_new_minimal(
            game: &str,
            game_version: &str,
            crashgen_name: &str,
            xse_acronym: &str,
        ) -> Result<Box<Orchestrator>>;
        fn fcx_reset_global_state() -> Result<()>;
        fn orchestrator_process_log(orch: &Orchestrator, log_path: &str) -> Result<ScanResult>;
        fn orchestrator_process_logs_batch(
            orch: &Orchestrator,
            log_paths: &[String],
            max_concurrent: u32,
        ) -> Vec<ScanResult>;
        fn orchestrator_process_logs_batch_with_progress(
            orch: &Orchestrator,
            log_paths: &[String],
            max_concurrent: u32,
            callback: &ScanBatchProgressCallback,
        ) -> Vec<BatchScanResult>;

        // Utilities
        fn detect_vr_log(content: &str) -> bool;
        fn detect_crash_pattern(content: &str) -> String;

        // Papyrus monitoring
        type CxxPapyrusAnalyzer;
        fn papyrus_analyzer_new(log_path: &str) -> Box<CxxPapyrusAnalyzer>;
        fn papyrus_start_monitoring(analyzer: &mut CxxPapyrusAnalyzer) -> Result<()>;
        fn papyrus_check_updates(analyzer: &mut CxxPapyrusAnalyzer) -> PapyrusStatsDto;
        fn papyrus_analyze_full(analyzer: &mut CxxPapyrusAnalyzer) -> Result<PapyrusStatsDto>;
        fn papyrus_log_exists(analyzer: &CxxPapyrusAnalyzer) -> bool;
        fn papyrus_reset(analyzer: &mut CxxPapyrusAnalyzer);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use classic_scanlog_core::{ConfigIssue, GLOBAL_FCX_HANDLER};
    use std::io::Write;
    use tempfile::NamedTempFile;
    use tempfile::tempdir;

    fn sample_issue() -> ConfigIssue {
        ConfigIssue::new(
            "test.ini".to_string(),
            Some("General".to_string()),
            "bExample".to_string(),
            "0".to_string(),
            "1".to_string(),
            "Example issue".to_string(),
            "warning".to_string(),
        )
    }

    fn seed_dirty_fcx_state() {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.fcx_mode = true;
        handler.set_main_files_result("Main files OK\n".to_string());
        handler.set_game_files_result("Game files OK\n".to_string());
        handler.set_detected_issues(vec![sample_issue()]);
        handler.checks_run = true;
    }

    fn assert_clean_fcx_state() {
        let handler = GLOBAL_FCX_HANDLER.lock();
        assert!(handler.main_files_check.is_none());
        assert!(handler.game_files_check.is_none());
        assert!(handler.detected_issues.is_empty());
        assert!(!handler.checks_run);
    }

    #[test]
    fn test_orchestrator_new_minimal() {
        let result = orchestrator_new_minimal("Fallout4", "auto", "Buffout 4", "F4SE");
        assert!(result.is_ok());
    }

    #[test]
    fn test_fcx_reset_global_state_treats_unnecessary_as_success() {
        {
            let mut handler = GLOBAL_FCX_HANDLER.lock();
            handler.reset();
        }

        assert!(fcx_reset_global_state().is_ok());
        assert_clean_fcx_state();
    }

    #[test]
    fn test_fcx_reset_global_state_clears_dirty_state() {
        seed_dirty_fcx_state();

        assert!(fcx_reset_global_state().is_ok());
        assert_clean_fcx_state();
    }

    #[test]
    fn test_orchestrator_process_log_resets_fcx_before_scan_start() {
        let orchestrator =
            orchestrator_new_minimal("Fallout4", "auto", "Buffout 4", "F4SE").unwrap();
        seed_dirty_fcx_state();

        let result = orchestrator_process_log(&orchestrator, "missing.log");
        assert!(result.is_err());
        assert_clean_fcx_state();
    }

    #[test]
    fn test_orchestrator_process_logs_batch_resets_fcx_before_scan_start() {
        let orchestrator =
            orchestrator_new_minimal("Fallout4", "auto", "Buffout 4", "F4SE").unwrap();
        seed_dirty_fcx_state();

        let results =
            orchestrator_process_logs_batch(&orchestrator, &["missing.log".to_string()], 1);
        assert_eq!(results.len(), 1);
        assert!(!results[0].success);
        assert_clean_fcx_state();
    }

    #[test]
    fn test_detect_vr_log_positive() {
        assert!(detect_vr_log("some content\nFallout4VR.esm\nmore content"));
        assert!(detect_vr_log("SkyrimVR.esm"));
    }

    #[test]
    fn test_detect_vr_log_negative() {
        assert!(!detect_vr_log("Fallout4.esm\nregular content"));
        assert!(!detect_vr_log(""));
    }

    #[test]
    fn test_parse_db_counter_interval() {
        assert_eq!(
            parse_db_counter_interval(None),
            DB_COUNTER_LOG_INTERVAL_DEFAULT
        );
        assert_eq!(
            parse_db_counter_interval(Some(" 50 ")),
            50,
            "Valid positive interval should be accepted"
        );
        assert_eq!(
            parse_db_counter_interval(Some("0")),
            DB_COUNTER_LOG_INTERVAL_DEFAULT,
            "Zero should fall back to default"
        );
        assert_eq!(
            parse_db_counter_interval(Some("not-a-number")),
            DB_COUNTER_LOG_INTERVAL_DEFAULT,
            "Invalid values should fall back to default"
        );
    }

    #[test]
    fn test_detect_crash_pattern_empty() {
        let result = detect_crash_pattern("");
        // Empty content should not match any crash pattern
        assert!(result.is_empty());
    }

    #[test]
    fn test_build_full_scan_config_invalid_dirs() {
        let result = build_full_scan_config(
            "nonexistent_root",
            "nonexistent_data",
            "Fallout4",
            "auto",
            false,
            false,
            false,
        );
        assert!(result.is_err());
    }

    #[test]
    fn test_resolve_formid_db_paths_includes_main_and_hardcoded_folon() {
        let temp = tempdir().unwrap();
        let root = temp.path();
        let data = root.join("CLASSIC Data");
        std::fs::create_dir_all(data.join("databases")).unwrap();

        // Explicit empty user list should still include hardcoded FOLON path.
        std::fs::write(
            root.join("CLASSIC Settings.yaml"),
            "CLASSIC_Settings:\n  FormID Databases:\n    Fallout4: []\n",
        )
        .unwrap();

        let paths =
            resolve_formid_db_paths(&root.to_string_lossy(), &data.to_string_lossy(), "Fallout4");
        let main = data.join("databases").join("Fallout4 FormIDs Main.db");
        let folon = data.join("databases").join("FOLON FormIDs.db");

        assert_eq!(paths, vec![main, folon]);
    }

    #[test]
    fn test_resolve_formid_db_paths_deduplicates_hardcoded_and_user_paths() {
        let temp = tempdir().unwrap();
        let root = temp.path();
        let data = root.join("CLASSIC Data");
        std::fs::create_dir_all(data.join("databases")).unwrap();
        let custom = data.join("databases").join("custom.db");

        let settings_yaml = "CLASSIC_Settings:\n  FormID Databases:\n    Fallout4:\n      - databases/FOLON FormIDs.db\n      - databases/custom.db\n";
        std::fs::write(root.join("CLASSIC Settings.yaml"), settings_yaml).unwrap();

        let paths =
            resolve_formid_db_paths(&root.to_string_lossy(), &data.to_string_lossy(), "Fallout4");
        let main = data.join("databases").join("Fallout4 FormIDs Main.db");
        let folon = data.join("databases").join("FOLON FormIDs.db");

        assert_eq!(paths, vec![main, folon, custom]);
    }

    #[test]
    fn test_load_user_formid_db_paths_ignores_legacy_underscore_settings_filename() {
        let temp = tempdir().unwrap();
        let root = temp.path();
        let data = root.join("CLASSIC Data");
        std::fs::create_dir_all(data.join("databases")).unwrap();

        let settings_yaml =
            "CLASSIC_Settings:\n  FormID Databases:\n    Fallout4:\n      - databases/custom.db\n";
        std::fs::write(root.join("CLASSIC_Settings.yaml"), settings_yaml).unwrap();

        let paths =
            load_user_formid_db_paths(&root.to_string_lossy(), &data.to_string_lossy(), "Fallout4");

        assert!(paths.is_empty());
    }

    #[test]
    fn test_load_exclude_log_records_reads_main_yaml_setting() {
        let temp = tempdir().unwrap();
        let data = temp.path();
        std::fs::create_dir_all(data.join("databases")).unwrap();

        std::fs::write(
            data.join("databases").join("CLASSIC Main.yaml"),
            "exclude_log_records:\n  - '(void*)'\n  - 'Basic Render Driver'\n",
        )
        .unwrap();

        let records = load_exclude_log_records(&data.to_string_lossy());
        assert_eq!(
            records,
            vec!["(void*)".to_string(), "Basic Render Driver".to_string()]
        );
    }

    #[test]
    fn test_scan_result_dto() {
        let ar = AnalysisResult::success("test.log".to_string(), vec!["line1".to_string()], 1000);
        let dto = analysis_result_to_dto(ar);
        assert_eq!(dto.log_path, "test.log");
        assert!(dto.success);
        assert_eq!(dto.report_lines, vec!["line1"]);
        assert!(dto.error_message.is_empty());
    }

    #[test]
    fn test_event_rank_stays_monotonic_for_successful_lifecycle() {
        let events = [
            (
                ffi::BatchProgressEventKind::Queued,
                ffi::BatchProgressPhase::Setup,
            ),
            (
                ffi::BatchProgressEventKind::Started,
                ffi::BatchProgressPhase::Setup,
            ),
            (
                ffi::BatchProgressEventKind::Phase,
                ffi::BatchProgressPhase::Setup,
            ),
            (
                ffi::BatchProgressEventKind::Phase,
                ffi::BatchProgressPhase::Parse,
            ),
            (
                ffi::BatchProgressEventKind::Phase,
                ffi::BatchProgressPhase::Analyze,
            ),
            (
                ffi::BatchProgressEventKind::Phase,
                ffi::BatchProgressPhase::Finalize,
            ),
            (
                ffi::BatchProgressEventKind::Completed,
                ffi::BatchProgressPhase::Finalize,
            ),
        ];

        let mut previous = 0;
        for (kind, phase) in events {
            let rank = event_rank(kind, phase);
            assert!(rank >= previous, "event rank should not regress");
            previous = rank;
        }
    }

    #[test]
    fn test_make_progress_event_with_current_completed_uses_emit_time_snapshot() {
        let completed_counter = AtomicU32::new(2);

        let started = make_progress_event_with_current_completed(
            ffi::BatchProgressEventKind::Started,
            ffi::BatchProgressPhase::Setup,
            &completed_counter,
            5,
            1,
            "first.log",
            false,
        );
        assert_eq!(started.completed, 2);

        completed_counter.store(3, Ordering::Relaxed);
        let phase = make_progress_event_with_current_completed(
            ffi::BatchProgressEventKind::Phase,
            ffi::BatchProgressPhase::Analyze,
            &completed_counter,
            5,
            1,
            "first.log",
            false,
        );
        assert_eq!(phase.completed, 3);
    }

    #[test]
    fn test_next_batch_update_prefers_progress_events_when_both_are_ready() {
        use futures::stream;
        use tokio::sync::mpsc;

        get_runtime().block_on(async {
            let (progress_tx, mut progress_rx) = mpsc::unbounded_channel();
            let mut pending_progress_events = VecDeque::new();
            progress_tx
                .send(make_progress_event(
                    ffi::BatchProgressEventKind::Started,
                    ffi::BatchProgressPhase::Setup,
                    0,
                    1,
                    0,
                    "test.log",
                    false,
                ))
                .expect("progress event should send");

            let mut tasks = stream::iter(vec![(
                0,
                "test.log".to_string(),
                ffi::BatchProgressPhase::Setup,
                AnalysisResult::success("test.log".to_string(), vec![], 0),
            )]);

            let update = next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks)
                .await;
            assert!(matches!(update, BatchUpdate::Progress(event) if event.event_kind == ffi::BatchProgressEventKind::Started));

            drop(progress_tx);

            let update = next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks)
                .await;
            assert!(matches!(update, BatchUpdate::Result((0, _, _, _))));
        });
    }

    #[test]
    fn test_drain_ready_progress_events_flushes_phase_emitted_during_result_poll() {
        use futures::stream::Stream;
        use std::pin::Pin;
        use std::task::{Context, Poll};
        use tokio::sync::mpsc;

        struct ResultAfterPhaseStream {
            emitted: bool,
            progress_tx: mpsc::UnboundedSender<ffi::BatchProgressEvent>,
        }

        impl Stream for ResultAfterPhaseStream {
            type Item = BatchTaskResult;

            fn poll_next(
                mut self: Pin<&mut Self>,
                _cx: &mut Context<'_>,
            ) -> Poll<Option<Self::Item>> {
                if self.emitted {
                    return Poll::Ready(None);
                }

                self.progress_tx
                    .send(make_progress_event(
                        ffi::BatchProgressEventKind::Phase,
                        ffi::BatchProgressPhase::Finalize,
                        0,
                        1,
                        0,
                        "test.log",
                        false,
                    ))
                    .expect("phase event should send");

                self.emitted = true;

                Poll::Ready(Some((
                    0,
                    "test.log".to_string(),
                    ffi::BatchProgressPhase::Finalize,
                    AnalysisResult::success("test.log".to_string(), vec![], 0),
                )))
            }
        }

        get_runtime().block_on(async {
            let (progress_tx, mut progress_rx) = mpsc::unbounded_channel();
            let mut pending_progress_events = VecDeque::new();
            let mut tasks = ResultAfterPhaseStream {
                emitted: false,
                progress_tx: progress_tx.clone(),
            };

            let update =
                next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks).await;
            assert!(matches!(update, BatchUpdate::Result((0, _, _, _))));

            let drained =
                drain_ready_progress_events(&mut pending_progress_events, &mut progress_rx).await;
            assert_eq!(drained.len(), 1);
            assert_eq!(drained[0].event_kind, ffi::BatchProgressEventKind::Phase);
            assert_eq!(drained[0].phase, ffi::BatchProgressPhase::Finalize);
            assert_eq!(drained[0].input_index, 0);
            assert_eq!(drained[0].log_path, "test.log");
            assert!(!drained[0].success);
            assert!(pending_progress_events.is_empty());
            assert!(progress_rx.try_recv().is_err());

            drop(progress_tx);
        });
    }

    #[test]
    fn test_drain_ready_progress_events_flushes_phase_scheduled_for_next_tick() {
        use futures::stream::Stream;
        use std::pin::Pin;
        use std::task::{Context, Poll};
        use tokio::sync::mpsc;
        use tokio::task::LocalSet;

        struct ResultBeforeScheduledPhaseStream {
            emitted: bool,
            progress_tx: mpsc::UnboundedSender<ffi::BatchProgressEvent>,
        }

        impl Stream for ResultBeforeScheduledPhaseStream {
            type Item = BatchTaskResult;

            fn poll_next(
                mut self: Pin<&mut Self>,
                _cx: &mut Context<'_>,
            ) -> Poll<Option<Self::Item>> {
                if self.emitted {
                    return Poll::Ready(None);
                }

                let progress_tx = self.progress_tx.clone();
                tokio::task::spawn_local(async move {
                    tokio::task::yield_now().await;
                    progress_tx
                        .send(make_progress_event(
                            ffi::BatchProgressEventKind::Phase,
                            ffi::BatchProgressPhase::Finalize,
                            0,
                            1,
                            0,
                            "test.log",
                            false,
                        ))
                        .expect("scheduled phase event should send");
                });

                self.emitted = true;

                Poll::Ready(Some((
                    0,
                    "test.log".to_string(),
                    ffi::BatchProgressPhase::Finalize,
                    AnalysisResult::success("test.log".to_string(), vec![], 0),
                )))
            }
        }

        get_runtime().block_on(async {
            LocalSet::new()
                .run_until(async {
                    let (progress_tx, mut progress_rx) = mpsc::unbounded_channel();
                    let mut pending_progress_events = VecDeque::new();
                    let mut tasks = ResultBeforeScheduledPhaseStream {
                        emitted: false,
                        progress_tx: progress_tx.clone(),
                    };

                    let update = next_batch_update(
                        &mut pending_progress_events,
                        &mut progress_rx,
                        &mut tasks,
                    )
                    .await;
                    assert!(matches!(update, BatchUpdate::Result((0, _, _, _))));

                    let drained =
                        drain_ready_progress_events(&mut pending_progress_events, &mut progress_rx)
                            .await;
                    assert_eq!(drained.len(), 1);
                    assert_eq!(drained[0].event_kind, ffi::BatchProgressEventKind::Phase);
                    assert_eq!(drained[0].phase, ffi::BatchProgressPhase::Finalize);
                    assert_eq!(drained[0].input_index, 0);
                    assert_eq!(drained[0].log_path, "test.log");
                    assert!(pending_progress_events.is_empty());
                    assert!(progress_rx.try_recv().is_err());

                    drop(progress_tx);
                })
                .await;
        });
    }

    #[test]
    fn test_drain_ready_progress_events_flushes_phase_scheduled_after_multiple_yields() {
        use futures::stream::Stream;
        use std::pin::Pin;
        use std::task::{Context, Poll};
        use tokio::sync::mpsc;
        use tokio::task::LocalSet;

        struct ResultBeforeDelayedPhaseStream {
            emitted: bool,
            progress_tx: mpsc::UnboundedSender<ffi::BatchProgressEvent>,
        }

        impl Stream for ResultBeforeDelayedPhaseStream {
            type Item = BatchTaskResult;

            fn poll_next(
                mut self: Pin<&mut Self>,
                _cx: &mut Context<'_>,
            ) -> Poll<Option<Self::Item>> {
                if self.emitted {
                    return Poll::Ready(None);
                }

                let progress_tx = self.progress_tx.clone();
                tokio::task::spawn_local(async move {
                    tokio::task::yield_now().await;
                    tokio::task::spawn_local(async move {
                        progress_tx
                            .send(make_progress_event(
                                ffi::BatchProgressEventKind::Phase,
                                ffi::BatchProgressPhase::Finalize,
                                0,
                                1,
                                0,
                                "test.log",
                                false,
                            ))
                            .expect("delayed phase event should send");
                    });
                });

                self.emitted = true;

                Poll::Ready(Some((
                    0,
                    "test.log".to_string(),
                    ffi::BatchProgressPhase::Finalize,
                    AnalysisResult::success("test.log".to_string(), vec![], 0),
                )))
            }
        }

        get_runtime().block_on(async {
            LocalSet::new()
                .run_until(async {
                    let (progress_tx, mut progress_rx) = mpsc::unbounded_channel();
                    let mut pending_progress_events = VecDeque::new();
                    let mut tasks = ResultBeforeDelayedPhaseStream {
                        emitted: false,
                        progress_tx: progress_tx.clone(),
                    };

                    let update = next_batch_update(
                        &mut pending_progress_events,
                        &mut progress_rx,
                        &mut tasks,
                    )
                    .await;
                    assert!(matches!(update, BatchUpdate::Result((0, _, _, _))));

                    let drained =
                        drain_ready_progress_events(&mut pending_progress_events, &mut progress_rx)
                            .await;
                    assert_eq!(drained.len(), 1);
                    assert_eq!(drained[0].event_kind, ffi::BatchProgressEventKind::Phase);
                    assert_eq!(drained[0].phase, ffi::BatchProgressPhase::Finalize);
                    assert_eq!(drained[0].input_index, 0);
                    assert_eq!(drained[0].log_path, "test.log");
                    assert!(pending_progress_events.is_empty());
                    assert!(progress_rx.try_recv().is_err());

                    drop(progress_tx);
                })
                .await;
        });
    }

    #[test]
    fn test_drain_ready_progress_events_emits_other_logs_without_rebuffering() {
        use futures::stream::Stream;
        use std::pin::Pin;
        use std::task::{Context, Poll};
        use tokio::sync::mpsc;

        struct ResultAfterCrossLogPhasesStream {
            emitted: bool,
            progress_tx: mpsc::UnboundedSender<ffi::BatchProgressEvent>,
        }

        impl Stream for ResultAfterCrossLogPhasesStream {
            type Item = BatchTaskResult;

            fn poll_next(
                mut self: Pin<&mut Self>,
                _cx: &mut Context<'_>,
            ) -> Poll<Option<Self::Item>> {
                if self.emitted {
                    return Poll::Ready(None);
                }

                self.progress_tx
                    .send(make_progress_event(
                        ffi::BatchProgressEventKind::Phase,
                        ffi::BatchProgressPhase::Analyze,
                        0,
                        2,
                        1,
                        "other.log",
                        false,
                    ))
                    .expect("other log phase event should send");
                self.progress_tx
                    .send(make_progress_event(
                        ffi::BatchProgressEventKind::Phase,
                        ffi::BatchProgressPhase::Finalize,
                        0,
                        2,
                        0,
                        "target.log",
                        false,
                    ))
                    .expect("target log phase event should send");

                self.emitted = true;

                Poll::Ready(Some((
                    0,
                    "target.log".to_string(),
                    ffi::BatchProgressPhase::Finalize,
                    AnalysisResult::success("target.log".to_string(), vec![], 0),
                )))
            }
        }

        get_runtime().block_on(async {
            let (progress_tx, mut progress_rx) = mpsc::unbounded_channel();
            let mut pending_progress_events = VecDeque::new();
            let mut tasks = ResultAfterCrossLogPhasesStream {
                emitted: false,
                progress_tx: progress_tx.clone(),
            };

            let update =
                next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks).await;
            assert!(matches!(update, BatchUpdate::Result((0, _, _, _))));

            let drained =
                drain_ready_progress_events(&mut pending_progress_events, &mut progress_rx).await;
            assert_eq!(
                drained.len(),
                2,
                "other-log progress should be forwarded immediately instead of rebuffered"
            );
            assert_eq!(drained[0].input_index, 1);
            assert_eq!(drained[0].log_path, "other.log");
            assert_eq!(drained[0].event_kind, ffi::BatchProgressEventKind::Phase);
            assert_eq!(drained[0].phase, ffi::BatchProgressPhase::Analyze);

            assert_eq!(drained[1].input_index, 0);
            assert_eq!(drained[1].log_path, "target.log");
            assert_eq!(drained[1].event_kind, ffi::BatchProgressEventKind::Phase);
            assert_eq!(drained[1].phase, ffi::BatchProgressPhase::Finalize);

            assert!(pending_progress_events.is_empty());
            assert!(progress_rx.try_recv().is_err());

            drop(progress_tx);
        });
    }

    #[test]
    fn test_next_batch_update_prefers_buffered_progress_events_before_results() {
        use futures::stream;
        use tokio::sync::mpsc;

        get_runtime().block_on(async {
            let (_progress_tx, mut progress_rx) = mpsc::unbounded_channel();
            let mut pending_progress_events = VecDeque::from([make_progress_event(
                ffi::BatchProgressEventKind::Phase,
                ffi::BatchProgressPhase::Analyze,
                0,
                2,
                1,
                "buffered.log",
                false,
            )]);
            let mut tasks = stream::iter(vec![(
                0,
                "result.log".to_string(),
                ffi::BatchProgressPhase::Finalize,
                AnalysisResult::success("result.log".to_string(), vec![], 0),
            )]);

            let update = next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks)
                .await;
            assert!(matches!(update, BatchUpdate::Progress(event) if event.input_index == 1 && event.log_path == "buffered.log"));

            let update = next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks)
                .await;
            assert!(matches!(update, BatchUpdate::Result((0, _, _, _))));
        });
    }

    #[test]
    fn test_event_rank_stays_monotonic_for_failed_lifecycle() {
        let events = [
            (
                ffi::BatchProgressEventKind::Queued,
                ffi::BatchProgressPhase::Setup,
            ),
            (
                ffi::BatchProgressEventKind::Started,
                ffi::BatchProgressPhase::Setup,
            ),
            (
                ffi::BatchProgressEventKind::Phase,
                ffi::BatchProgressPhase::Setup,
            ),
            (
                ffi::BatchProgressEventKind::Phase,
                ffi::BatchProgressPhase::Analyze,
            ),
            (
                ffi::BatchProgressEventKind::Failed,
                ffi::BatchProgressPhase::Analyze,
            ),
        ];

        let mut previous = 0;
        for (kind, phase) in events {
            let rank = event_rank(kind, phase);
            assert!(rank >= previous, "failed event rank should not regress");
            previous = rank;
        }
    }

    #[test]
    fn test_apply_short_scan_db_profile_sets_pool_knobs() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "Fallout4".to_string());
        apply_short_scan_db_profile(&pool);

        assert_eq!(pool.get_cache_capacity(), SHORT_SCAN_CACHE_CAPACITY);
        assert_eq!(
            pool.get_cache_ttl(),
            Duration::from_secs(SHORT_SCAN_CACHE_TTL_SECS)
        );
        assert_eq!(
            pool.get_cache_cleanup_threshold(),
            SHORT_SCAN_CLEANUP_THRESHOLD
        );
        assert_eq!(
            pool.get_cache_cleanup_interval(),
            Duration::from_secs(SHORT_SCAN_CLEANUP_INTERVAL_SECS)
        );
    }

    // ── Papyrus bridge tests ──────────────────────────────────────

    #[test]
    fn test_papyrus_analyzer_new() {
        let analyzer = papyrus_analyzer_new("/some/path/Papyrus.0.log");
        // Should not panic; analyzer wraps the path without file access
        assert!(!papyrus_log_exists(&analyzer));
    }

    #[test]
    fn test_papyrus_log_exists_with_real_file() {
        let temp = NamedTempFile::new().unwrap();
        let path = temp.path().to_str().unwrap();
        let analyzer = papyrus_analyzer_new(path);
        assert!(papyrus_log_exists(&analyzer));
    }

    #[test]
    fn test_papyrus_analyze_full() {
        let mut temp = NamedTempFile::new().unwrap();
        writeln!(temp, "Dumping Stacks for thread 0x1234").unwrap();
        writeln!(temp, "Dumping Stack for function foo").unwrap();
        writeln!(temp, "[2024/01/01] warning: Variable not initialized").unwrap();
        writeln!(temp, "[2024/01/01] error: Null reference").unwrap();
        temp.flush().unwrap();

        let path = temp.path().to_str().unwrap();
        let mut analyzer = papyrus_analyzer_new(path);
        let dto = papyrus_analyze_full(&mut analyzer).unwrap();

        assert_eq!(dto.dumps, 1);
        assert_eq!(dto.stacks, 1);
        assert_eq!(dto.warnings, 1);
        assert_eq!(dto.errors, 1);
        assert_eq!(dto.lines_processed, 4);
        assert!(dto.dumps_stacks_ratio > 0.0);
    }

    #[test]
    fn test_papyrus_analyze_full_nonexistent() {
        let mut analyzer = papyrus_analyzer_new("/nonexistent/Papyrus.0.log");
        let result = papyrus_analyze_full(&mut analyzer);
        assert!(result.is_err());
    }

    #[test]
    fn test_papyrus_start_monitoring_nonexistent() {
        let mut analyzer = papyrus_analyzer_new("/nonexistent/Papyrus.0.log");
        let result = papyrus_start_monitoring(&mut analyzer);
        assert!(result.is_err());
    }

    #[test]
    fn test_papyrus_start_monitoring_and_check_updates() {
        let mut temp = NamedTempFile::new().unwrap();
        writeln!(temp, "Initial line").unwrap();
        temp.flush().unwrap();

        let path = temp.path().to_str().unwrap();
        let mut analyzer = papyrus_analyzer_new(path);

        // Start monitoring positions at end of file
        papyrus_start_monitoring(&mut analyzer).unwrap();

        // No new data yet -- stats should be empty
        let dto = papyrus_check_updates(&mut analyzer);
        assert_eq!(dto.dumps, 0);
        assert_eq!(dto.lines_processed, 0);

        // Append new data
        writeln!(temp, "Dumping Stacks for thread 0xABC").unwrap();
        writeln!(temp, "[2024/01/01] error: Something bad").unwrap();
        temp.flush().unwrap();

        // Now check_updates should pick up the new lines
        let dto = papyrus_check_updates(&mut analyzer);
        assert_eq!(dto.dumps, 1);
        assert_eq!(dto.errors, 1);
        assert_eq!(dto.lines_processed, 2);
    }

    #[test]
    fn test_papyrus_reset() {
        let mut temp = NamedTempFile::new().unwrap();
        writeln!(temp, "Dumping Stacks").unwrap();
        writeln!(temp, "[2024/01/01] error: Null ref").unwrap();
        temp.flush().unwrap();

        let path = temp.path().to_str().unwrap();
        let mut analyzer = papyrus_analyzer_new(path);

        // Analyze to populate stats
        papyrus_analyze_full(&mut analyzer).unwrap();

        // Reset clears everything
        papyrus_reset(&mut analyzer);

        // check_updates after reset should re-read from beginning
        let dto = papyrus_check_updates(&mut analyzer);
        assert_eq!(dto.dumps, 1);
        assert_eq!(dto.errors, 1);
        assert_eq!(dto.lines_processed, 2);
    }

    #[test]
    fn test_papyrus_stats_dto_no_activity() {
        let stats = PapyrusStats {
            dumps: 0,
            stacks: 0,
            warnings: 10,
            errors: 0,
            last_modified: None,
            lines_processed: 100,
        };
        let dto = papyrus_stats_to_dto(&stats);
        assert_eq!(dto.dumps_stacks_ratio, 0.0);
        assert_eq!(dto.warnings, 10);
        assert_eq!(dto.lines_processed, 100);
    }

    #[test]
    fn test_papyrus_stats_dto_with_activity() {
        let stats = PapyrusStats {
            dumps: 5,
            stacks: 2,
            warnings: 0,
            errors: 10,
            last_modified: None,
            lines_processed: 50,
        };
        let dto = papyrus_stats_to_dto(&stats);
        assert_eq!(dto.dumps, 5);
        assert_eq!(dto.stacks, 2);
        assert_eq!(dto.errors, 10);
        assert_eq!(dto.dumps_stacks_ratio, 2.5);
    }
}
