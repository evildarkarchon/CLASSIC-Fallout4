use super::*;
use std::sync::{Arc, Mutex};
use std::time::Duration;

/// Mock dispatcher that executes closures immediately (synchronously)
/// and tracks dispatch count for verification.
///
/// This enables testing bridge logic without a running Slint event loop.
struct MockDispatcher {
    dispatch_count: Arc<Mutex<u32>>,
}

impl MockDispatcher {
    fn new() -> (Self, Arc<Mutex<u32>>) {
        let count = Arc::new(Mutex::new(0));
        (
            Self {
                dispatch_count: count.clone(),
            },
            count,
        )
    }
}

impl EventLoopDispatcher for MockDispatcher {
    fn dispatch(&self, f: Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError> {
        *self.dispatch_count.lock().unwrap() += 1;
        f(); // Execute immediately for test verification
        Ok(())
    }
}

/// Mock dispatcher that always fails dispatch, simulating a stopped event loop.
struct FailingDispatcher;

impl EventLoopDispatcher for FailingDispatcher {
    fn dispatch(&self, _f: Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError> {
        Err(BridgeError::DispatchFailed(
            "event loop not running".to_string(),
        ))
    }
}

// ---- Error type tests ----

#[test]
fn test_bridge_error_timeout_display() {
    let err = BridgeError::Timeout(Duration::from_secs(5));
    let msg = err.to_string();
    assert!(
        msg.contains("5s"),
        "Timeout display should contain duration: {msg}"
    );
    assert!(
        msg.contains("timed out"),
        "Timeout display should mention timeout: {msg}"
    );
}

#[test]
fn test_bridge_error_cancelled_display() {
    let err = BridgeError::Cancelled;
    let msg = err.to_string();
    assert!(
        msg.contains("cancelled"),
        "Cancelled display should mention cancellation: {msg}"
    );
}

#[test]
fn test_bridge_error_dispatch_failed_display() {
    let err = BridgeError::DispatchFailed("event loop stopped".to_string());
    let msg = err.to_string();
    assert!(
        msg.contains("event loop stopped"),
        "DispatchFailed display should contain inner message: {msg}"
    );
    assert!(
        msg.contains("dispatch"),
        "DispatchFailed display should mention dispatch: {msg}"
    );
}

#[test]
fn test_bridge_error_timeout_various_durations() {
    // Sub-second duration
    let err = BridgeError::Timeout(Duration::from_millis(500));
    assert!(err.to_string().contains("500ms"));

    // Zero duration
    let err = BridgeError::Timeout(Duration::ZERO);
    let msg = err.to_string();
    assert!(
        msg.contains("timed out"),
        "Zero duration should still show timeout: {msg}"
    );

    // Large duration
    let err = BridgeError::Timeout(Duration::from_secs(300));
    assert!(err.to_string().contains("300s"));
}

// ---- Type safety tests ----

#[test]
fn test_bridge_error_is_send_sync() {
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<BridgeError>();
}

#[test]
fn test_async_bridge_type_exists() {
    // Compile verification -- AsyncBridge is a zero-sized struct
    assert_eq!(std::mem::size_of::<AsyncBridge>(), 0);
}

#[test]
fn test_slint_dispatcher_type_exists() {
    // Compile verification -- SlintDispatcher is constructible as a unit struct
    let _ = SlintDispatcher;
    assert_eq!(std::mem::size_of::<SlintDispatcher>(), 0);
}

// ---- MockDispatcher trait contract tests ----

#[test]
fn test_mock_dispatcher_implements_trait() {
    let (mock, count) = MockDispatcher::new();
    let result = mock.dispatch(Box::new(|| {}));
    assert!(result.is_ok());
    assert_eq!(*count.lock().unwrap(), 1);
}

#[test]
fn test_mock_dispatcher_executes_closure() {
    let (mock, _count) = MockDispatcher::new();
    let flag = Arc::new(Mutex::new(false));
    let flag_clone = flag.clone();
    let result = mock.dispatch(Box::new(move || {
        *flag_clone.lock().unwrap() = true;
    }));
    assert!(result.is_ok());
    assert!(
        *flag.lock().unwrap(),
        "MockDispatcher should execute the closure synchronously"
    );
}

#[test]
fn test_mock_dispatcher_tracks_multiple_dispatches() {
    let (mock, count) = MockDispatcher::new();
    for _ in 0..5 {
        let _ = mock.dispatch(Box::new(|| {}));
    }
    assert_eq!(*count.lock().unwrap(), 5);
}

#[test]
fn test_mock_dispatcher_closure_captures_work() {
    let (mock, _count) = MockDispatcher::new();
    let values = Arc::new(Mutex::new(Vec::new()));

    for i in 0..3 {
        let values_clone = values.clone();
        let _ = mock.dispatch(Box::new(move || {
            values_clone.lock().unwrap().push(i);
        }));
    }

    let collected = values.lock().unwrap().clone();
    assert_eq!(collected, vec![0, 1, 2]);
}

// ---- FailingDispatcher tests ----

#[test]
fn test_failing_dispatcher_returns_error() {
    let dispatcher = FailingDispatcher;
    let result = dispatcher.dispatch(Box::new(|| {}));
    assert!(result.is_err());
    if let Err(BridgeError::DispatchFailed(msg)) = result {
        assert!(msg.contains("not running"));
    } else {
        panic!("Expected DispatchFailed error");
    }
}

#[test]
fn test_failing_dispatcher_does_not_execute_closure() {
    let dispatcher = FailingDispatcher;
    let flag = Arc::new(Mutex::new(false));
    let flag_clone = flag.clone();
    let _ = dispatcher.dispatch(Box::new(move || {
        *flag_clone.lock().unwrap() = true;
    }));
    assert!(
        !*flag.lock().unwrap(),
        "FailingDispatcher should NOT execute the closure"
    );
}

// ---- BridgeError Debug/matching tests ----

#[test]
fn test_bridge_error_debug_format() {
    let err = BridgeError::Timeout(Duration::from_secs(10));
    let debug = format!("{err:?}");
    assert!(
        debug.contains("Timeout"),
        "Debug format should contain variant name: {debug}"
    );

    let err = BridgeError::Cancelled;
    let debug = format!("{err:?}");
    assert!(
        debug.contains("Cancelled"),
        "Debug format should contain variant name: {debug}"
    );
}

#[test]
fn test_bridge_error_pattern_matching() {
    // Verify all variants are matchable (exhaustive check)
    let errors: Vec<BridgeError> = vec![
        BridgeError::Timeout(Duration::from_secs(1)),
        BridgeError::Cancelled,
        BridgeError::DispatchFailed("test".to_string()),
    ];

    for err in errors {
        match err {
            BridgeError::Timeout(d) => assert!(d.as_secs() > 0 || d.as_secs() == 1),
            BridgeError::Cancelled => {} // Expected
            BridgeError::DispatchFailed(msg) => assert!(!msg.is_empty()),
        }
    }
}

// NOTE: Testing run_with_ui_update, run_with_timeout, and run_cancellable
// requires the DISPATCHER OnceLock to be set AND a running Tokio runtime.
// Since the global DISPATCHER can only be set once per process and tests
// share the process, integration-level tests for the full bridge methods
// should verify at the classic-gui crate level where the full stack is available.
//
// The unit tests here validate:
// - Error types and Display/Debug impls
// - Dispatcher trait contract (MockDispatcher, FailingDispatcher)
// - Type safety (Send + Sync bounds, zero-sized types)
// - Closure execution semantics
// - Pattern matching exhaustiveness
