//! Logging bridge for CXX FFI.
//!
//! Provides simple log functions that delegate to the `log` crate macros.
//! C++ can call these to emit log messages through Rust's logging infrastructure.

fn log_info(message: &str) {
    log::info!("{}", message);
}

fn log_warning(message: &str) {
    log::warn!("{}", message);
}

fn log_error(message: &str) {
    log::error!("{}", message);
}

fn log_debug(message: &str) {
    log::debug!("{}", message);
}

fn log_trace(message: &str) {
    log::trace!("{}", message);
}

fn init_logging() {
    // Initialize env_logger if not already initialized.
    // Ignore error if already initialized (idempotent).
    let _ = env_logger::try_init();
}

#[cxx::bridge(namespace = "classic::message")]
mod ffi {
    extern "Rust" {
        fn log_info(message: &str);
        fn log_warning(message: &str);
        fn log_error(message: &str);
        fn log_debug(message: &str);
        fn log_trace(message: &str);
        fn init_logging();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_log_info_no_panic() {
        init_logging();
        log_info("test info message");
    }

    #[test]
    fn test_log_warning_no_panic() {
        log_warning("test warning message");
    }

    #[test]
    fn test_log_error_no_panic() {
        log_error("test error message");
    }

    #[test]
    fn test_log_debug_no_panic() {
        log_debug("test debug message");
    }

    #[test]
    fn test_log_trace_no_panic() {
        log_trace("test trace message");
    }

    #[test]
    fn test_init_logging_idempotent() {
        init_logging();
        init_logging();
        init_logging();
    }
}
