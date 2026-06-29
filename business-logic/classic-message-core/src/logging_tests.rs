use super::*;
use serial_test::serial;
use std::sync::atomic::{AtomicUsize, Ordering};

struct CountingLogger;

static COUNTING_LOGGER: CountingLogger = CountingLogger;
static LOGGED_MESSAGES: AtomicUsize = AtomicUsize::new(0);

impl log::Log for CountingLogger {
    fn enabled(&self, _metadata: &log::Metadata<'_>) -> bool {
        true
    }

    fn log(&self, record: &log::Record<'_>) {
        if self.enabled(record.metadata()) {
            LOGGED_MESSAGES.fetch_add(1, Ordering::SeqCst);
        }
    }

    fn flush(&self) {}
}

#[test]
fn test_logger_name() {
    let logger = Logger::new();
    assert_eq!(logger.name(), "CLASSIC");
    assert_eq!(Logger::LOGGER_NAME, "CLASSIC");
}

#[test]
fn test_default_logger() {
    let logger = Logger::default();
    assert_eq!(logger.name(), "CLASSIC");
}

#[test]
fn test_logger_methods_compile() {
    // These tests just verify that the methods compile and don't panic
    // Actual logging output depends on the log crate configuration
    let logger = Logger::new();

    logger.info("Info message");
    logger.warning("Warning message");
    logger.error("Error message");
    logger.debug("Debug message");
    logger.trace("Trace message");
    logger.log(log::Level::Info, "Log message");
}

#[test]
fn test_log_message() {
    let logger = Logger::new();
    let msg = Message::new("Test content", MessageType::Info)
        .with_title("Test Title")
        .with_details("Test details");

    // This just verifies it compiles and doesn't panic
    logger.log_message(&msg);
}

#[test]
fn test_is_enabled_checks() {
    let logger = Logger::new();

    // These return values depend on the log configuration,
    // but the methods should not panic
    let _ = logger.is_enabled_for(log::Level::Info);
    let _ = logger.is_info_enabled();
    let _ = logger.is_debug_enabled();
    let _ = logger.is_trace_enabled();
}

#[test]
fn test_format_contract_event_required_fields() {
    let event = ContractEvent::new(
        "integration.startup",
        EVENT_STARTUP_BINDING_CONTRACT_VALIDATED,
        MessageType::Info,
        "success",
    )
    .with_context("contract", "startup_all")
    .with_context("checked_bindings", "29");

    let formatted = format_contract_event(&event);
    assert!(formatted.contains("event=classic.startup.binding_contract.validated"));
    assert!(formatted.contains("severity=info"));
    assert!(formatted.contains("component=integration.startup"));
    assert!(formatted.contains("outcome=success"));
    assert!(formatted.contains("contract=startup_all"));
    assert!(formatted.contains("checked_bindings=29"));
}

#[test]
fn test_format_contract_event_redacts_sensitive_fields() {
    let event = ContractEvent::new(
        "integration.startup",
        EVENT_STARTUP_BINDING_CONTRACT_FAILED,
        MessageType::Error,
        "failure",
    )
    .with_context("api_key", "secret-token")
    .with_context(
        "install_path",
        r"C:\Users\alice\Documents\My Games\Fallout4",
    );

    let formatted = format_contract_event(&event);
    assert!(formatted.contains("api_key=[REDACTED]"));
    assert!(formatted.contains("install_path=<path-redacted>"));
}

#[test]
fn test_contract_severity_mapping_for_warning_and_debug() {
    let warning_event = ContractEvent::new(
        "integration.startup",
        EVENT_STARTUP_BINDING_CONTRACT_VALIDATED,
        MessageType::Warning,
        "success",
    );
    let debug_event = ContractEvent::new(
        "integration.startup",
        EVENT_STARTUP_BINDING_CONTRACT_VALIDATED,
        MessageType::Debug,
        "success",
    );

    assert!(format_contract_event(&warning_event).contains("severity=warning"));
    assert!(format_contract_event(&debug_event).contains("severity=debug"));
}

#[test]
fn test_startup_contract_helpers_compile() {
    let logger = Logger::new();
    logger.log_startup_binding_contract_validated("startup_all", 29, Some("corr-1"));
    logger.log_startup_binding_contract_failed(
        "startup_all",
        "classic_yaml.YamlOperations",
        "import",
        "Rebuild and reinstall Rust bindings with `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1`.",
        "No module named 'classic_yaml'",
        None,
    );
    logger.log_startup_acceleration_status(5, 5, "MANDATORY", None);
}

#[test]
#[serial]
fn test_init_is_opt_in_idempotent_and_does_not_replace_existing_logger() {
    let _logger = Logger::new();
    log::set_logger(&COUNTING_LOGGER)
        .expect("Logger::new and crate import must not install the global logger");
    log::set_max_level(log::LevelFilter::Trace);

    init();
    init();
    init_with_filter("trace");

    let before = LOGGED_MESSAGES.load(Ordering::SeqCst);
    log::info!(target: Logger::LOGGER_NAME, "counted by existing logger");
    assert_eq!(LOGGED_MESSAGES.load(Ordering::SeqCst), before + 1);
}
