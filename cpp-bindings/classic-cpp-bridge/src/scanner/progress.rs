use classic_scanlog_core::{AnalysisResult, ScanProgressPhase};
use log::info;
use std::collections::{HashSet, VecDeque};
use std::sync::atomic::{AtomicU32, Ordering};

use super::ffi;

pub(super) fn map_progress_phase(phase: ScanProgressPhase) -> ffi::BatchProgressPhase {
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

pub(super) fn make_progress_event(
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

pub(super) fn make_progress_event_with_current_completed(
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
pub(super) struct BatchProgressDiagnostics {
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

    pub(super) fn log_summary(&self, total: usize) {
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

pub(super) fn emit_progress_event(
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

pub(super) type BatchTaskResult = (u32, String, ffi::BatchProgressPhase, AnalysisResult);

const READY_PROGRESS_DRAIN_MAX_EMPTY_YIELDS: usize = 2;

pub(super) enum BatchUpdate {
    Progress(ffi::BatchProgressEvent),
    Result(BatchTaskResult),
    TasksExhausted,
}

/// Drain all progress currently visible to preserve global event ordering before emitting the
/// terminal Completed/Failed event for a finished task.
pub(super) async fn drain_ready_progress_events(
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

pub(super) async fn next_batch_update<S>(
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

pub(super) fn effective_batch_concurrency(total_logs: usize, max_concurrent: u32) -> usize {
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

#[cfg(test)]
#[path = "progress_tests.rs"]
mod tests;
