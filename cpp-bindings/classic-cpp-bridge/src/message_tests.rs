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

#[test]
fn test_startup_contract_helpers_no_panic() {
    init_logging();
    log_startup_binding_contract_validated("cpp_startup", 3, "corr-123");
    log_startup_binding_contract_failed(
        "cpp_startup",
        "classic::runtime::init_runtime",
        "runtime_init",
        "Rebuild Rust bridge and verify runtime prerequisites.",
        "runtime init failed",
        "corr-123",
    );
    log_startup_acceleration_status(1, 1, "MANDATORY", "corr-123");
}
