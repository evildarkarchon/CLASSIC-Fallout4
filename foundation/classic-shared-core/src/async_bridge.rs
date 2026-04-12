//! Async Bridge - Coordinate between Slint event loop and Tokio async runtime
//!
//! This module provides utilities to bridge between Slint's UI event loop and Tokio's
//! async runtime. It handles the complexity of running async operations from UI callbacks
//! and updating the UI from async contexts.
//!
//! # Architecture
//!
//! - **Slint Event Loop**: Runs on the main thread, handles UI updates
//! - **Tokio Runtime**: Shared multi-threaded runtime for async I/O (ONE RUNTIME RULE)
//! - **AsyncBridge**: Coordinates between the two, managing thread transitions
//! - **EventLoopDispatcher**: Trait abstracting UI-thread dispatch for testability
//!
//! # Methods
//!
//! - [`AsyncBridge::run_with_ui_update`] - Execute async operation, update UI with result
//! - [`AsyncBridge::spawn_background`] - Fire-and-forget async operation
//! - [`AsyncBridge::invoke_on_ui_thread`] - Invoke a function on the Slint event loop
//! - [`AsyncBridge::run_with_timeout`] - Execute async operation with a timeout
//! - [`AsyncBridge::run_cancellable`] - Execute async operation with cancellation support
//!
//! # Error Handling
//!
//! All dispatch operations use [`BridgeError`] for structured error reporting.
//! Methods that dispatch to the UI thread log errors instead of panicking when
//! dispatch fails, ensuring the application remains stable.
//!
//! # Testability
//!
//! The [`EventLoopDispatcher`] trait abstracts `slint::invoke_from_event_loop` behind
//! a mockable interface. Use [`set_dispatcher`] to inject a test dispatcher that does
//! not require a running Slint event loop.
//!
//! # Pattern
//!
//! ```rust,ignore
//! use classic_shared_core::AsyncBridge;
//!
//! // In a Slint button callback:
//! AsyncBridge::run_with_ui_update(
//!     async_operation(),  // Runs on Tokio runtime
//!     |result| {          // Runs on Slint event loop
//!         // Update UI with result
//!         window.set_data(result);
//!     }
//! );
//! ```

#[cfg(feature = "gui-bridge")]
use std::future::Future;
#[cfg(feature = "gui-bridge")]
use std::sync::OnceLock;

/// Error type for async bridge operations
///
/// Represents the possible failure modes when coordinating between
/// the Tokio async runtime and the Slint UI event loop.
///
/// # Variants
///
/// - [`Timeout`](BridgeError::Timeout) - Operation exceeded its time limit
/// - [`Cancelled`](BridgeError::Cancelled) - Operation was cancelled via token
/// - [`DispatchFailed`](BridgeError::DispatchFailed) - Could not dispatch to UI thread
#[cfg(feature = "gui-bridge")]
#[derive(Debug, thiserror::Error)]
pub enum BridgeError {
    /// The operation did not complete within the specified duration
    #[error("Operation timed out after {0:?}")]
    Timeout(std::time::Duration),

    /// The operation was cancelled via a cancellation token
    #[error("Operation was cancelled")]
    Cancelled,

    /// Failed to dispatch a callback to the UI event loop
    #[error("Failed to dispatch to UI thread: {0}")]
    DispatchFailed(String),
}

/// Trait abstracting UI-thread dispatch for testability
///
/// This trait wraps the mechanism for invoking closures on the UI event loop.
/// The production implementation ([`SlintDispatcher`]) delegates to
/// `slint::invoke_from_event_loop`, while test implementations can execute
/// closures directly or record them for verification.
///
/// # Examples
///
/// ```rust,ignore
/// use classic_shared_core::{EventLoopDispatcher, BridgeError};
///
/// struct TestDispatcher;
/// impl EventLoopDispatcher for TestDispatcher {
///     fn dispatch(&self, f: Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError> {
///         f(); // Execute immediately in tests
///         Ok(())
///     }
/// }
/// ```
#[cfg(feature = "gui-bridge")]
pub trait EventLoopDispatcher: Send + Sync + 'static {
    /// Dispatch a closure to run on the UI event loop thread
    ///
    /// # Arguments
    ///
    /// * `f` - The closure to invoke on the UI thread
    ///
    /// # Errors
    ///
    /// Returns [`BridgeError::DispatchFailed`] if the event loop is not running
    /// or the closure cannot be dispatched.
    fn dispatch(&self, f: Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError>;
}

/// Production dispatcher using Slint's event loop
///
/// This is the default dispatcher that delegates to `slint::invoke_from_event_loop`.
/// It is automatically used when no custom dispatcher is set via [`set_dispatcher`].
#[cfg(feature = "gui-bridge")]
pub struct SlintDispatcher;

#[cfg(feature = "gui-bridge")]
impl EventLoopDispatcher for SlintDispatcher {
    fn dispatch(&self, f: Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError> {
        slint::invoke_from_event_loop(f).map_err(|e| BridgeError::DispatchFailed(e.to_string()))
    }
}

/// Global dispatcher instance, initialized once at startup
///
/// Defaults to [`SlintDispatcher`] if not explicitly set via [`set_dispatcher`].
#[cfg(feature = "gui-bridge")]
static DISPATCHER: OnceLock<Box<dyn EventLoopDispatcher>> = OnceLock::new();

/// Set the global event loop dispatcher
///
/// Call this once at application startup to configure the dispatch mechanism.
/// In production, you typically do not need to call this (the default
/// [`SlintDispatcher`] is used). In tests, call this with a mock dispatcher
/// before running any bridge operations.
///
/// # Panics
///
/// Panics if the dispatcher has already been set. This enforces the invariant
/// that the dispatcher is configured exactly once.
///
/// # Examples
///
/// ```rust,ignore
/// use classic_shared_core::set_dispatcher;
///
/// // In test setup:
/// set_dispatcher(TestDispatcher);
/// ```
#[cfg(feature = "gui-bridge")]
pub fn set_dispatcher(dispatcher: impl EventLoopDispatcher + 'static) {
    DISPATCHER
        .set(Box::new(dispatcher))
        .unwrap_or_else(|_| panic!("EventLoopDispatcher already set"));
}

/// Get a reference to the global dispatcher, initializing with SlintDispatcher if needed
#[cfg(feature = "gui-bridge")]
fn get_dispatcher() -> &'static dyn EventLoopDispatcher {
    DISPATCHER
        .get_or_init(|| Box::new(SlintDispatcher))
        .as_ref()
}

/// Async bridge for coordinating between Slint event loop and Tokio runtime
///
/// This struct provides static methods for executing async operations from UI callbacks
/// and updating the UI from async contexts. It abstracts the complexity of thread
/// transitions and event loop coordination.
///
/// # Design
///
/// The bridge uses the following pattern:
/// 1. Spawn async operation on shared Tokio runtime (`get_runtime().spawn()`)
/// 2. Await result within the spawned task
/// 3. Invoke callback on Slint event loop via [`EventLoopDispatcher`]
///
/// This ensures:
/// - UI remains responsive (async work on Tokio runtime tasks)
/// - Proper async execution (using shared Tokio runtime)
/// - Safe UI updates (callbacks run on Slint event loop)
/// - Testability (dispatcher can be mocked)
///
/// # Examples
///
/// ## Basic Usage
/// ```rust,ignore
/// use classic_shared_core::AsyncBridge;
///
/// AsyncBridge::run_with_ui_update(
///     perform_backup(category),
///     move |result| {
///         window.set_loading(false);
///         match result {
///             Ok(data) => window.show_success(&data),
///             Err(e) => window.show_error(&e.to_string()),
///         }
///     }
/// );
/// ```
///
/// ## Fire-and-Forget
/// ```rust,ignore
/// use classic_shared_core::AsyncBridge;
///
/// AsyncBridge::spawn_background(async {
///     log_event("User clicked button").await;
/// });
/// ```
#[cfg(feature = "gui-bridge")]
pub struct AsyncBridge;

#[cfg(feature = "gui-bridge")]
impl AsyncBridge {
    /// Execute an async operation and invoke a callback on the Slint event loop
    ///
    /// This is the primary method for running async operations from Slint callbacks.
    /// It spawns a task on the shared Tokio runtime to execute the operation, then
    /// invokes the callback on the Slint event loop to update the UI.
    ///
    /// # Arguments
    ///
    /// * `operation` - The async operation to execute (must be Send + 'static)
    /// * `on_complete` - Callback invoked on UI thread when operation completes
    ///
    /// # Thread Safety Requirements
    ///
    /// Both the `operation` and `on_complete` callback must be `Send + 'static`:
    /// - **All captured variables must implement `Send`**
    /// - Use `Arc` instead of `Rc` for shared references
    /// - Use `Arc<Mutex<T>>` or `Arc<RwLock<T>>` for shared mutable state
    /// - Clone data before capturing if the original is not `Send`
    /// - Slint's `ComponentHandle` and `Weak` handles are `Send`, so they can be captured
    ///
    /// # Error Handling
    ///
    /// If the UI dispatch fails (e.g., the event loop has stopped), the error is
    /// logged and the callback is dropped. The application continues running.
    ///
    /// # Thread Execution
    ///
    /// - `operation` runs as a task on the Tokio runtime
    /// - `on_complete` runs on the main Slint event loop thread
    /// - Both must be Send + 'static to cross thread boundaries
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// use classic_shared_core::AsyncBridge;
    ///
    /// // In a Slint button callback:
    /// let window = window_weak.clone();
    /// AsyncBridge::run_with_ui_update(
    ///     async move {
    ///         tokio::fs::read_to_string("file.txt").await
    ///     },
    ///     move |result| {
    ///         if let Some(w) = window.upgrade() {
    ///             match result {
    ///                 Ok(contents) => w.set_text(contents.into()),
    ///                 Err(e) => w.set_error(e.to_string().into()),
    ///             }
    ///         }
    ///     }
    /// );
    /// ```
    pub fn run_with_ui_update<F, R, C>(operation: F, on_complete: C)
    where
        F: Future<Output = R> + Send + 'static,
        R: Send + 'static,
        C: FnOnce(R) + Send + 'static,
    {
        crate::get_runtime().spawn(async move {
            let result = operation.await;

            if let Err(e) = get_dispatcher().dispatch(Box::new(move || {
                on_complete(result);
            })) {
                log::error!("AsyncBridge dispatch failed in run_with_ui_update: {e}");
            }
        });
    }

    /// Execute an async operation without a callback (fire-and-forget)
    ///
    /// Use this for operations that don't need to update the UI on completion,
    /// such as logging, analytics, or background cleanup tasks.
    ///
    /// # Arguments
    ///
    /// * `operation` - The async operation to execute
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// use classic_shared_core::AsyncBridge;
    ///
    /// AsyncBridge::spawn_background(async {
    ///     // Background logging or cleanup
    ///     log_user_action("button_clicked").await;
    /// });
    /// ```
    pub fn spawn_background<F>(operation: F)
    where
        F: Future<Output = ()> + Send + 'static,
    {
        crate::get_runtime().spawn(operation);
    }

    /// Execute an async operation with a timeout, then dispatch result to UI thread
    ///
    /// Wraps the async operation in [`tokio::time::timeout`]. If the operation completes
    /// within the specified duration, the callback receives `Ok(result)`. If the timeout
    /// elapses first, the callback receives `Err(BridgeError::Timeout(duration))`.
    ///
    /// # Arguments
    ///
    /// * `timeout` - Maximum duration to wait for the operation
    /// * `operation` - The async operation to execute
    /// * `on_complete` - Callback invoked on UI thread with `Ok(result)` or `Err(BridgeError::Timeout)`
    ///
    /// # Error Handling
    ///
    /// - Timeout: Callback receives `Err(BridgeError::Timeout(duration))`
    /// - Dispatch failure: Error is logged and the callback is dropped
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// use classic_shared_core::AsyncBridge;
    /// use std::time::Duration;
    ///
    /// AsyncBridge::run_with_timeout(
    ///     Duration::from_secs(30),
    ///     async { fetch_data().await },
    ///     |result| match result {
    ///         Ok(data) => window.set_data(data),
    ///         Err(e) => window.set_error(e.to_string()),
    ///     }
    /// );
    /// ```
    pub fn run_with_timeout<F, R, C>(timeout: std::time::Duration, operation: F, on_complete: C)
    where
        F: Future<Output = R> + Send + 'static,
        R: Send + 'static,
        C: FnOnce(Result<R, BridgeError>) + Send + 'static,
    {
        crate::get_runtime().spawn(async move {
            let result = match tokio::time::timeout(timeout, operation).await {
                Ok(value) => Ok(value),
                Err(_) => Err(BridgeError::Timeout(timeout)),
            };
            if let Err(e) = get_dispatcher().dispatch(Box::new(move || {
                on_complete(result);
            })) {
                log::error!("AsyncBridge dispatch failed in run_with_timeout: {e}");
            }
        });
    }

    /// Execute an async operation with cancellation support, then dispatch result to UI thread
    ///
    /// Races the async operation against a [`CancellationToken`](tokio_util::sync::CancellationToken).
    /// If the operation completes before cancellation, the callback receives `Some(result)`.
    /// If the token is cancelled first, the callback receives `None`.
    ///
    /// # Arguments
    ///
    /// * `cancel_token` - Token that can be cancelled to abort the operation
    /// * `operation` - The async operation to execute
    /// * `on_complete` - Callback invoked on UI thread with `Some(result)` or `None` (cancelled)
    ///
    /// # Error Handling
    ///
    /// - Cancellation: Callback receives `None`
    /// - Dispatch failure: Error is logged and the callback is dropped
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// use classic_shared_core::AsyncBridge;
    /// use tokio_util::sync::CancellationToken;
    ///
    /// let token = CancellationToken::new();
    /// let cancel_handle = token.clone();
    ///
    /// AsyncBridge::run_cancellable(
    ///     token,
    ///     async { long_running_scan().await },
    ///     |result| match result {
    ///         Some(data) => window.set_results(data),
    ///         None => window.set_status("Cancelled"),
    ///     }
    /// );
    ///
    /// // Later, to cancel:
    /// cancel_handle.cancel();
    /// ```
    pub fn run_cancellable<F, R, C>(
        cancel_token: tokio_util::sync::CancellationToken,
        operation: F,
        on_complete: C,
    ) where
        F: Future<Output = R> + Send + 'static,
        R: Send + 'static,
        C: FnOnce(Option<R>) + Send + 'static,
    {
        crate::get_runtime().spawn(async move {
            let result = tokio::select! {
                value = operation => Some(value),
                () = cancel_token.cancelled() => None,
            };
            if let Err(e) = get_dispatcher().dispatch(Box::new(move || {
                on_complete(result);
            })) {
                log::error!("AsyncBridge dispatch failed in run_cancellable: {e}");
            }
        });
    }

    /// Invoke a function on the Slint event loop from any thread
    ///
    /// This is a low-level utility for directly invoking functions on the Slint
    /// event loop. Most code should use `run_with_ui_update` instead, which provides
    /// a more complete async-to-UI bridge.
    ///
    /// # Arguments
    ///
    /// * `f` - The function to invoke on the UI thread
    ///
    /// # Error Handling
    ///
    /// If the UI dispatch fails, the error is logged and the function is dropped.
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// use classic_shared_core::AsyncBridge;
    ///
    /// // From a background thread:
    /// AsyncBridge::invoke_on_ui_thread(move || {
    ///     window.set_status("Ready".into());
    /// });
    /// ```
    pub fn invoke_on_ui_thread<F>(f: F)
    where
        F: FnOnce() + Send + 'static,
    {
        if let Err(e) = get_dispatcher().dispatch(Box::new(f)) {
            log::error!("AsyncBridge dispatch failed in invoke_on_ui_thread: {e}");
        }
    }
}

#[cfg(test)]
#[cfg(feature = "gui-bridge")]
mod tests {
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
}
