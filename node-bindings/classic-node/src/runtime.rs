//! Shared-runtime helpers for NAPI async adapters.
//!
//! NAPI exports are already async Rust functions. These helpers keep the
//! handoff to CLASSIC's process-wide Tokio runtime explicit and preserve each
//! call site's existing error mapping.

use std::future::Future;

/// Spawn a fallible future on the shared CLASSIC runtime and map both join and
/// domain errors through call-site-provided mappers.
pub(crate) async fn spawn_result<F, T, E, J, C>(
    future: F,
    map_join_error: J,
    map_core_error: C,
) -> napi::Result<T>
where
    F: Future<Output = Result<T, E>> + Send + 'static,
    T: Send + 'static,
    E: Send + 'static,
    J: FnOnce(tokio::task::JoinError) -> napi::Error,
    C: FnOnce(E) -> napi::Error,
{
    let handle = classic_shared_core::get_runtime().handle().clone();
    handle
        .spawn(future)
        .await
        .map_err(map_join_error)?
        .map_err(map_core_error)
}
