//! Core async bridge utilities for Python-Rust interop.
//!
//! This crate provides helpers for the AsyncBridge, which manages
//! synchronous-to-asynchronous bridging in Python code. The Rust
//! components provide:
//!
//! - Bridge metrics tracking
//! - Runtime coordination (ONE RUNTIME RULE)
//! - Thread-local utilities
//!
//! # Architecture
//!
//! The async bridge operates in a hybrid model:
//! - Python manages asyncio event loops and coroutine execution
//! - Rust provides high-performance metrics and runtime coordination
//!
//! # ONE RUNTIME RULE
//!
//! This crate integrates with `classic-shared-core` to ensure all async
//! operations use the shared global Tokio runtime.

mod metrics;
mod runtime;

pub use metrics::{
    BridgeMetrics, BridgeOperation, clear_bridge_metrics, get_bridge_metrics,
    record_bridge_operation,
};
pub use runtime::{RuntimeInfo, execute_on_runtime, get_runtime_info, is_runtime_available};

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    #[serial]
    fn test_basic_metrics() {
        clear_bridge_metrics();

        record_bridge_operation(BridgeOperation::RunAsync, 0.1, true);
        record_bridge_operation(BridgeOperation::RunAsync, 0.2, true);
        record_bridge_operation(BridgeOperation::RunAsync, 0.15, false);

        let metrics = get_bridge_metrics();
        assert_eq!(metrics.run_async_count, 3);
        assert_eq!(metrics.run_async_success, 2);
        assert_eq!(metrics.run_async_failure, 1);
    }

    #[test]
    fn test_runtime_available() {
        // Should be able to check runtime availability
        let available = is_runtime_available();
        assert!(available); // Should be true in tests
    }
}
