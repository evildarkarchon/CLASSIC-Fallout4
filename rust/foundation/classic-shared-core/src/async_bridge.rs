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
//!
//! # Methods
//!
//! - [`AsyncBridge::run_with_ui_update`] - Execute async operation, update UI with result
//! - [`AsyncBridge::spawn_background`] - Fire-and-forget async operation
//! - [`AsyncBridge::invoke_on_ui_thread`] - Invoke a function on the Slint event loop
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
/// 3. Invoke callback on Slint event loop (`slint::invoke_from_event_loop()`)
///
/// This ensures:
/// - UI remains responsive (async work on Tokio runtime tasks)
/// - Proper async execution (using shared Tokio runtime)
/// - Safe UI updates (callbacks run on Slint event loop)
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
    /// # Common Mistakes
    ///
    /// ❌ **DON'T** use `Rc` (not Send):
    /// ```rust,compile_fail
    /// let data = Rc::new(vec![1, 2, 3]);  // Rc is NOT Send!
    /// AsyncBridge::run_with_ui_update(
    ///     async move { data.len() },  // Compile error!
    ///     |_| {}
    /// );
    /// ```
    ///
    /// ✅ **DO** use `Arc` (is Send):
    /// ```rust,no_run
    /// use std::sync::Arc;
    /// use classic_shared_core::AsyncBridge;
    ///
    /// let data = Arc::new(vec![1, 2, 3]);  // Arc IS Send
    /// let data_clone = Arc::clone(&data);
    /// AsyncBridge::run_with_ui_update(
    ///     async move { data_clone.len() },  // Works!
    ///     |result| { println!("Length: {}", result); }
    /// );
    /// ```
    ///
    /// # Thread Execution
    ///
    /// - `operation` runs as a task on the Tokio runtime
    /// - `on_complete` runs on the main Slint event loop thread
    /// - Both must be Send + 'static to cross thread boundaries
    ///
    /// # Panics
    ///
    /// Panics if unable to invoke the callback on the Slint event loop. This should
    /// never happen in normal operation.
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
        // Performance Optimization: Spawn directly on Tokio runtime instead of using
        // thread pool + block_on. This eliminates thread pool overhead and potential
        // nested runtime issues.
        //
        // Expected impact: 30-50% lower latency (2-5ms reduction), no thread pool overhead
        crate::get_runtime().spawn(async move {
            // Execute async operation
            let result = operation.await;

            // Invoke callback on Slint event loop for UI updates
            slint::invoke_from_event_loop(move || {
                on_complete(result);
            })
            .expect("Failed to invoke callback on Slint event loop");
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
        // Performance Optimization: Spawn directly on Tokio runtime
        // Eliminates thread pool overhead for fire-and-forget operations
        crate::get_runtime().spawn(operation);
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
    /// # Panics
    ///
    /// Panics if unable to invoke the function on the Slint event loop.
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
        slint::invoke_from_event_loop(f).expect("Failed to invoke function on Slint event loop");
    }
}

#[cfg(test)]
#[cfg(feature = "gui-bridge")]
mod tests {
    use super::*;

    #[test]
    fn test_async_bridge_exists() {
        // Basic compile test to ensure the module structure is correct
        // Actual functionality tests require a running Slint event loop
        assert_eq!(
            std::any::type_name::<AsyncBridge>(),
            "classic_shared_core::async_bridge::AsyncBridge"
        );
    }
}
