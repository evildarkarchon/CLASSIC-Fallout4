use super::*;

#[test]
fn test_init_runtime_idempotent() {
    // Calling init multiple times should not panic
    init_runtime();
    init_runtime();
    init_runtime();
}

#[test]
fn test_runtime_is_active() {
    init_runtime();
    assert!(is_runtime_active());
}

#[test]
fn test_shutdown_is_noop() {
    init_runtime();
    shutdown_runtime();
    // Runtime should still be active after "shutdown"
    assert!(is_runtime_active());
}

#[test]
fn test_block_on_works() {
    init_runtime();
    let result = get_runtime().block_on(async { 42 });
    assert_eq!(result, 42);
}
