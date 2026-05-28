use super::super::ffi;
use super::*;
use classic_scanlog_core::AnalysisResult;
use classic_shared_core::get_runtime;
use std::collections::VecDeque;
use std::sync::atomic::{AtomicU32, Ordering};

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

        fn poll_next(mut self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
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

        fn poll_next(mut self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
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

                let update =
                    next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks)
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

        fn poll_next(mut self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
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

                let update =
                    next_batch_update(&mut pending_progress_events, &mut progress_rx, &mut tasks)
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

        fn poll_next(mut self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
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
