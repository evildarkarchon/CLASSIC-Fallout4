//! Logging bridge for CXX FFI.
//!
//! Provides simple log functions that delegate to the `log` crate macros.
//! C++ can call these to emit log messages through Rust's logging infrastructure.

use classic_message_core::logging::{self, Logger};

fn optional_correlation_id(correlation_id: &str) -> Option<&str> {
    let trimmed = correlation_id.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed)
    }
}

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

fn log_startup_binding_contract_validated(
    contract: &str,
    checked_bindings: u32,
    correlation_id: &str,
) {
    let logger = Logger::new();
    logger.log_startup_binding_contract_validated(
        contract,
        checked_bindings as usize,
        optional_correlation_id(correlation_id),
    );
}

fn log_startup_binding_contract_failed(
    contract: &str,
    missing_binding: &str,
    failure_type: &str,
    failure_hint: &str,
    error: &str,
    correlation_id: &str,
) {
    let logger = Logger::new();
    logger.log_startup_binding_contract_failed(
        contract,
        missing_binding,
        failure_type,
        failure_hint,
        error,
        optional_correlation_id(correlation_id),
    );
}

fn log_startup_acceleration_status(
    active_components: u32,
    total_components: u32,
    acceleration_level: &str,
    correlation_id: &str,
) {
    let logger = Logger::new();
    logger.log_startup_acceleration_status(
        active_components as usize,
        total_components as usize,
        acceleration_level,
        optional_correlation_id(correlation_id),
    );
}

fn init_logging() {
    logging::init();
}

#[cxx::bridge(namespace = "classic::message")]
mod ffi {
    extern "Rust" {
        fn log_info(message: &str);
        fn log_warning(message: &str);
        fn log_error(message: &str);
        fn log_debug(message: &str);
        fn log_trace(message: &str);
        fn log_startup_binding_contract_validated(
            contract: &str,
            checked_bindings: u32,
            correlation_id: &str,
        );
        fn log_startup_binding_contract_failed(
            contract: &str,
            missing_binding: &str,
            failure_type: &str,
            failure_hint: &str,
            error: &str,
            correlation_id: &str,
        );
        fn log_startup_acceleration_status(
            active_components: u32,
            total_components: u32,
            acceleration_level: &str,
            correlation_id: &str,
        );
        fn init_logging();
    }
}

#[cfg(test)]
#[path = "message_tests.rs"]
mod tests;
