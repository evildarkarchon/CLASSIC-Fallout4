//! Shared-runtime helpers for CXX bridge adapters.
//!
//! Keep these helpers private to the Rust bridge crate. They centralize the
//! synchronous adapter pattern without changing the public `#[cxx::bridge]`
//! API surface.

use std::fmt::Display;
use std::future::Future;

/// Run a future on the process-wide CLASSIC Tokio runtime.
///
/// Use this only from synchronous CXX adapter functions. Async Rust code should
/// await directly, and UI callers should avoid invoking blocking bridge calls on
/// event-loop threads for long-running work.
pub(crate) fn block_on<F>(future: F) -> F::Output
where
    F: Future,
{
    classic_shared_core::get_runtime().block_on(future)
}

/// Run a fallible future on the shared runtime and map its error to `String`.
///
/// This preserves the existing CXX bridge convention of returning
/// `Result<T, String>` while making the runtime handoff explicit and reusable.
pub(crate) fn block_on_result<F, T, E>(future: F) -> Result<T, String>
where
    F: Future<Output = Result<T, E>>,
    E: Display,
{
    block_on(future).map_err(|error| error.to_string())
}
