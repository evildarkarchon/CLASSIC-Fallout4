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
#[serial_test::serial]
fn test_fcx_reset_global_state_treats_unnecessary_as_success() {
    {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.reset();
    }

    assert!(fcx_reset_global_state().is_ok());
    assert_clean_fcx_state();
}

#[test]
#[serial_test::serial]
fn test_fcx_reset_global_state_clears_dirty_state() {
    seed_dirty_fcx_state();

    assert!(fcx_reset_global_state().is_ok());
    assert_clean_fcx_state();
}

#[test]
#[serial_test::serial]
fn test_orchestrator_process_log_resets_fcx_before_scan_start() {
    let orchestrator =
        orchestrator_new_minimal("Fallout4", "auto", "Buffout 4", "F4SE").unwrap();
    seed_dirty_fcx_state();

    let result = orchestrator_process_log(&orchestrator, "missing.log");
    assert!(result.is_err());
    assert_clean_fcx_state();
}

#[test]
#[serial_test::serial]
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
fn test_detect_crash_pattern_positive_fixture_excerpt() {
    let result = detect_crash_pattern(include_str!(
        "../../../business-logic/classic-scanlog-core/benches/fixtures/crash-2022-06-05-12-58-02.log"
    ));

    assert_eq!(
        result,
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF6A1C08F6A Fallout4.exe+1AF8F6A"
    );
}

#[test]
fn test_detect_crash_pattern_repeated_calls_keep_same_positive_result() {
    let input = include_str!(
        "../../../business-logic/classic-scanlog-core/benches/fixtures/crash-2022-06-05-12-58-02.log"
    );

    let first = detect_crash_pattern(input);
    let second = detect_crash_pattern(input);

    assert!(!first.is_empty());
    assert_eq!(first, second);
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

// ── FCX getter tests (CXXS-03) ────────────────────────────────────

/// Empty-state contract: after reset, get_fcx_config_issues() returns empty Vec.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_after_reset_returns_empty() {
    let _ = fcx_reset_global_state();
    let issues = get_fcx_config_issues();
    assert!(
        issues.is_empty(),
        "Expected empty Vec after reset, got {} issues",
        issues.len()
    );
}

/// Fresh-state contract: before any scan, handler lazy-inits with empty detected_issues.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_fresh_state_returns_empty() {
    // Reset to known-clean state first
    let _ = fcx_reset_global_state();
    let issues = get_fcx_config_issues();
    assert!(
        issues.is_empty(),
        "Expected empty Vec on fresh state, got {} issues",
        issues.len()
    );
}

/// Idempotence: calling get_fcx_config_issues() twice without state change returns same length.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_idempotent() {
    let _ = fcx_reset_global_state();
    let issues1 = get_fcx_config_issues();
    let issues2 = get_fcx_config_issues();
    assert_eq!(
        issues1.len(),
        issues2.len(),
        "get_fcx_config_issues() must be read-only; repeated calls should return same length"
    );
}

/// Round-trip: section None maps to section_or_empty="" + has_section=false;
/// section Some("Display") maps to section_or_empty="Display" + has_section=true.
/// Also verifies all other fields are correctly mapped.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_round_trips_section_none_and_some() {
    let _ = fcx_reset_global_state();

    // Inject two issues: one with section: None, one with section: Some("Display")
    {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.set_detected_issues(vec![
            ConfigIssue::new(
                "Fallout4.ini".to_string(),
                None,
                "iNumThreads".to_string(),
                "4".to_string(),
                "8".to_string(),
                "thread count too low".to_string(),
                "warning".to_string(),
            ),
            ConfigIssue::new(
                "Fallout4Prefs.ini".to_string(),
                Some("Display".to_string()),
                "iSize W".to_string(),
                "640".to_string(),
                "1920".to_string(),
                "resolution too low".to_string(),
                "info".to_string(),
            ),
        ]);
    }

    let issues = get_fcx_config_issues();
    assert_eq!(issues.len(), 2, "Expected exactly 2 issues after injection");

    // First issue: section None → section_or_empty="" + has_section=false
    assert_eq!(issues[0].file_path, "Fallout4.ini");
    assert_eq!(
        issues[0].section_or_empty, "",
        "section: None must produce section_or_empty = \"\""
    );
    assert!(
        !issues[0].has_section,
        "section: None must produce has_section = false"
    );
    assert_eq!(issues[0].setting, "iNumThreads");
    assert_eq!(issues[0].current_value, "4");
    assert_eq!(issues[0].recommended_value, "8");
    assert_eq!(issues[0].description, "thread count too low");
    assert_eq!(issues[0].severity, "warning");

    // Second issue: section Some("Display") → section_or_empty="Display" + has_section=true
    assert_eq!(issues[1].file_path, "Fallout4Prefs.ini");
    assert_eq!(
        issues[1].section_or_empty, "Display",
        "section: Some(\"Display\") must produce section_or_empty = \"Display\""
    );
    assert!(
        issues[1].has_section,
        "section: Some(\"Display\") must produce has_section = true"
    );
    assert_eq!(issues[1].setting, "iSize W");
    assert_eq!(issues[1].current_value, "640");
    assert_eq!(issues[1].recommended_value, "1920");
    assert_eq!(issues[1].description, "resolution too low");
    assert_eq!(issues[1].severity, "info");

    // Cleanup
    let _ = fcx_reset_global_state();
}

/// Regression: fcx_reset_global_state() still works correctly (D-08 preserved).
#[test]
#[serial_test::serial]
fn test_fcx_reset_clears_issues_visible_to_getter() {
    // Seed some issues
    {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.set_detected_issues(vec![ConfigIssue::new(
            "file.ini".to_string(),
            None,
            "key".to_string(),
            "old".to_string(),
            "new".to_string(),
            "desc".to_string(),
            "info".to_string(),
        )]);
    }

    // Verify issues are present
    let before_reset = get_fcx_config_issues();
    assert_eq!(before_reset.len(), 1, "Expected 1 issue before reset");

    // Reset clears everything
    let _ = fcx_reset_global_state();

    // Getter must now return empty Vec
    let after_reset = get_fcx_config_issues();
    assert!(
        after_reset.is_empty(),
        "Expected empty Vec after reset, got {} issues",
        after_reset.len()
    );
}

/// Order preservation: Vec returned by getter matches injection order.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_preserves_order() {
    let _ = fcx_reset_global_state();

    {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.set_detected_issues(vec![
            ConfigIssue::new(
                "first.ini".to_string(),
                None,
                "alpha".to_string(),
                "a".to_string(),
                "b".to_string(),
                "first issue".to_string(),
                "error".to_string(),
            ),
            ConfigIssue::new(
                "second.ini".to_string(),
                None,
                "beta".to_string(),
                "c".to_string(),
                "d".to_string(),
                "second issue".to_string(),
                "warning".to_string(),
            ),
        ]);
    }

    let issues = get_fcx_config_issues();
    assert_eq!(issues.len(), 2);
    assert_eq!(issues[0].file_path, "first.ini");
    assert_eq!(issues[1].file_path, "second.ini");

    let _ = fcx_reset_global_state();
}
