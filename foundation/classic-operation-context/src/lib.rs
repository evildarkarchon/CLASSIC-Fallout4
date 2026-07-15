//! Workspace-internal context shared by cooperating async operations.
//!
//! This unpublished crate carries operation controls across crate boundaries
//! without turning implementation seams into public binding contracts.

use std::future::Future;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

tokio::task_local! {
    static CANCELLATION: Arc<AtomicBool>;
}

/// Runs a future with an optional, task-local cooperative cancellation flag.
///
/// The scope is restored on every poll, so concurrently polled operation
/// futures retain independent controls even when they share an executor task.
pub async fn scope_cancellation<F>(cancellation: Option<Arc<AtomicBool>>, future: F) -> F::Output
where
    F: Future,
{
    match cancellation {
        Some(cancellation) => CANCELLATION.scope(cancellation, future).await,
        None => future.await,
    }
}

/// Returns whether the current operation scope requested cancellation.
///
/// Code outside a cancellation scope is deliberately treated as uncancelled,
/// preserving the behavior of independently reusable core APIs.
#[must_use]
pub fn cancellation_requested() -> bool {
    CANCELLATION
        .try_with(|cancellation| cancellation.load(Ordering::Acquire))
        .unwrap_or(false)
}

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
