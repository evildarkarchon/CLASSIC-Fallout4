use super::*;

#[test]
fn test_log_warning_no_panic() {
    init_logging();
    log_warning("test warning message");
}

#[test]
fn test_init_logging_delegates_to_core_and_is_idempotent() {
    init_logging();
    classic_message_core::logging::init();
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
