//! Runtime management bridge for CXX FFI.
//!
//! Exposes the ONE RUNTIME RULE to C++: a single Tokio runtime shared
//! across the entire application via `classic_shared_core::get_runtime()`.

use classic_shared_core::get_runtime;

fn init_runtime() {
    // Force LazyLock initialization by accessing the runtime.
    // This is idempotent — calling it multiple times is safe.
    let _ = get_runtime();
}

fn shutdown_runtime() {
    // The Tokio runtime is owned by a LazyLock and lives for the process lifetime.
    // There is no explicit shutdown; the runtime is dropped when the process exits.
    // This function exists for API symmetry so C++ can express intent.
}

fn is_runtime_active() -> bool {
    // The LazyLock runtime is always active once initialized.
    // We verify by running a trivial task.
    let rt = get_runtime();
    rt.block_on(async { true })
}

#[cxx::bridge(namespace = "classic::runtime")]
mod ffi {
    extern "Rust" {
        /// Initialize the global Tokio runtime (idempotent).
        fn init_runtime();

        /// Signal shutdown intent (no-op; runtime lives for process lifetime).
        fn shutdown_runtime();

        /// Check if the runtime is active and responsive.
        fn is_runtime_active() -> bool;
    }
}

#[cfg(test)]
mod tests {
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
}
