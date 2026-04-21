#[cxx::bridge(namespace = "classic::mixed")]
mod ffi {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum BatchProgressEventKind {
        Queued = 0,
        Started = 1,
        Completed = 2,
    }

    struct BatchProgressEvent {
        completed: u32,
        total: u32,
        event_kind: BatchProgressEventKind,
        success: bool,
    }

    unsafe extern "C++" {
        include!("fake_header.h");
        type ScanProgressCallback;
        fn on_progress(self: &ScanProgressCallback, event: &BatchProgressEvent);
    }

    extern "Rust" {
        type MixedOrchestrator;
        fn orchestrator_new() -> Box<MixedOrchestrator>;
        fn orchestrator_run(orch: &MixedOrchestrator, callback: &ScanProgressCallback) -> Vec<BatchProgressEvent>;
    }
}
