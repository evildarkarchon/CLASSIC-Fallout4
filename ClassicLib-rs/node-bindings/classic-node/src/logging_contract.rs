//! Internal Node logging-contract adapter for startup diagnostics.
//!
//! This keeps startup/dependency-readiness parity aligned with the Python/Rust
//! contract without exposing additional public NAPI APIs.

use classic_message_core::logging::Logger;
use std::sync::Once;

static STARTUP_DIAGNOSTICS_EMITTED: Once = Once::new();

fn resolve_correlation_id(explicit: Option<&str>) -> Option<String> {
    if let Some(value) = explicit {
        let trimmed = value.trim();
        if !trimmed.is_empty() {
            return Some(trimmed.to_string());
        }
    }

    std::env::var("CLASSIC_CORRELATION_ID")
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

pub(crate) fn emit_node_runtime_startup_diagnostics(
    available: bool,
    thread_count: u32,
    correlation_id: Option<&str>,
) {
    STARTUP_DIAGNOSTICS_EMITTED.call_once(|| {
        let logger = Logger::new();
        let resolved_correlation_id = resolve_correlation_id(correlation_id);
        let correlation_id_ref = resolved_correlation_id.as_deref();

        if available {
            logger.log_startup_binding_contract_validated("classic-node.runtime.startup", 1, correlation_id_ref);
            logger.log_startup_acceleration_status(
                usize::from(thread_count > 0),
                1,
                "MANDATORY",
                correlation_id_ref,
            );
        } else {
            logger.log_startup_binding_contract_failed(
                "classic-node.runtime.startup",
                "classic_shared_core::get_runtime",
                "runtime_init",
                "Ensure the Node process can initialize the shared CLASSIC runtime and retry startup.",
                "Node runtime unavailable during startup diagnostics.",
                correlation_id_ref,
            );
        }
    });
}
