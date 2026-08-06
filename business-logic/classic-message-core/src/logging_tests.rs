use super::*;
use serial_test::serial;
use std::sync::atomic::{AtomicUsize, Ordering};

/// The one message [`CountingLogger`] tallies.
///
/// A sentinel rather than a target, because every `Logger` method logs with
/// `target: self.name` — the same `"CLASSIC"` this test would filter on — so the
/// target cannot tell this test's record apart from a sibling's.
const COUNTED_MESSAGE: &str = "counted by the pre-existing global logger";

struct CountingLogger;

static COUNTING_LOGGER: CountingLogger = CountingLogger;
static LOGGED_MESSAGES: AtomicUsize = AtomicUsize::new(0);

impl log::Log for CountingLogger {
    fn enabled(&self, _metadata: &log::Metadata<'_>) -> bool {
        true
    }

    fn log(&self, record: &log::Record<'_>) {
        // Counting every record would make this a running tally of whatever the
        // whole test binary logs, not of what the test below emitted.
        // `log::set_logger` installs process-wide and `init` deliberately keeps
        // the existing logger, so from the moment this logger is installed it
        // receives every sibling test's output too — and those siblings run
        // concurrently, on other threads. Matching one sentinel keeps the count
        // owned by the test that produces it.
        if self.enabled(record.metadata()) && record.args().to_string() == COUNTED_MESSAGE {
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
// `#[serial]` orders this against other `#[serial]` tests only, and it is the
// only one in this module — so it buys nothing here and must not be mistaken
// for protection. What makes the count below sound is the sentinel in
// `CountingLogger::log`, not this attribute. Kept so that a future test which
// also installs a global logger is ordered against this one, since
// `log::set_logger` succeeds at most once per process and the `expect` below
// would otherwise fail depending on which test ran first.
#[serial]
fn test_init_is_opt_in_idempotent_and_does_not_replace_existing_logger() {
    let _logger = Logger::new();
    log::set_logger(&COUNTING_LOGGER)
        .expect("Logger::new and crate import must not install the global logger");
    log::set_max_level(log::LevelFilter::Trace);

    init();
    init();
    init_with_filter("trace");

    // Read before emitting rather than assuming zero: this logger stays
    // installed for the rest of the process, so the assertion is about the
    // delta this call causes, not about an absolute total.
    let before = LOGGED_MESSAGES.load(Ordering::SeqCst);
    log::info!(target: Logger::LOGGER_NAME, "{}", COUNTED_MESSAGE);
    assert_eq!(LOGGED_MESSAGES.load(Ordering::SeqCst), before + 1);
}
