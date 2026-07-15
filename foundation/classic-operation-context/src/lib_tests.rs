use super::{cancellation_requested, scope_cancellation};
use std::sync::Arc;
use std::sync::atomic::AtomicBool;

#[tokio::test]
async fn cancellation_defaults_to_false_outside_a_scope() {
    assert!(!cancellation_requested());
}

#[tokio::test]
async fn cancellation_scope_reads_its_control() {
    let cancellation = Arc::new(AtomicBool::new(true));

    scope_cancellation(Some(cancellation), async {
        assert!(cancellation_requested());
    })
    .await;

    assert!(!cancellation_requested());
}

#[tokio::test]
async fn concurrently_polled_scopes_keep_independent_controls() {
    let cancelled = Arc::new(AtomicBool::new(true));
    let active = Arc::new(AtomicBool::new(false));

    let (cancelled_result, active_result) = tokio::join!(
        scope_cancellation(Some(cancelled), async {
            tokio::task::yield_now().await;
            cancellation_requested()
        }),
        scope_cancellation(Some(active), async {
            tokio::task::yield_now().await;
            cancellation_requested()
        }),
    );

    assert!(cancelled_result);
    assert!(!active_result);
}
