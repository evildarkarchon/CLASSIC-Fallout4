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
#[path = "runtime_tests.rs"]
mod tests;
