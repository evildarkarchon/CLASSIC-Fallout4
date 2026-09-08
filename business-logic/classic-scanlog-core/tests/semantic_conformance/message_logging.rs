//! Observe real Rust log records through a host-installed capture sink.

use super::{RunnerResult, invalid, text};
use classic_message_core::{ContractEvent, Logger, Message, MessageType};
use serde_json::{Value, json};
use std::sync::{Mutex, Once};

struct Capture;
static CAPTURE: Capture = Capture;
static INSTALL: Once = Once::new();
static RECORDS: Mutex<Vec<Value>> = Mutex::new(Vec::new());

impl log::Log for Capture {
    /// Enable every level so fixture filters cannot silently hide a required call.
    fn enabled(&self, _metadata: &log::Metadata<'_>) -> bool {
        true
    }

    /// Preserve actual level and formatted message while discarding environment-specific targets.
    fn log(&self, record: &log::Record<'_>) {
        RECORDS.lock().expect("capture lock").push(
            json!({"level": record.level().to_string(), "message": record.args().to_string()}),
        );
    }

    /// Records are captured synchronously, so flushing has no deferred work.
    fn flush(&self) {
        // The in-memory sink has no buffered output to flush.
    }
}

/// Execute public logger and formatter operations against input-only fixture values.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    INSTALL.call_once(|| {
        log::set_logger(&CAPTURE).expect("install conformance host logger");
        log::set_max_level(log::LevelFilter::Trace);
    });
    RECORDS.lock().expect("capture lock").clear();
    classic_message_core::logging::init();
    classic_message_core::logging::init();
    let logger = Logger::new();
    let mut result = json!({});
    match text(&fixture["operation"])?.as_str() {
        "basic" => {
            let messages = &fixture["messages"];
            logger.info(&text(&messages["info"])?);
            logger.warning(&text(&messages["warning"])?);
            logger.error(&text(&messages["error"])?);
            logger.debug(&text(&messages["debug"])?);
        }
        "extended" => {
            logger.trace(&text(&fixture["trace"])?);
            logger.log(log::Level::Info, &text(&fixture["dynamic"])?);
            logger.log_message(
                &Message::new(text(&fixture["message"])?, MessageType::Warning)
                    .with_title(text(&fixture["title"])?)
                    .with_details(text(&fixture["details"])?),
            );
            result = json!({
                "enabled": [logger.is_info_enabled(), logger.is_debug_enabled(), logger.is_trace_enabled(), logger.is_enabled_for(log::Level::Warn)],
                "name": logger.name(),
                "invalidLog": text(&fixture["invalid"])?.parse::<log::Level>().is_err(),
                "invalidEnabled": text(&fixture["invalid"])?.parse::<log::Level>().is_err()
            });
        }
        "startup" => {
            logger.trace(&text(&fixture["trace"])?);
            let correlation = text(&fixture["correlation"])?;
            logger.log_startup_binding_contract_validated(
                &text(&fixture["contract"])?,
                fixture["checked"]
                    .as_u64()
                    .ok_or_else(|| invalid("checked count"))? as usize,
                Some(&correlation),
            );
            logger.log_startup_binding_contract_failed(
                &text(&fixture["contract"])?,
                &text(&fixture["missing"])?,
                &text(&fixture["failureType"])?,
                &text(&fixture["hint"])?,
                &text(&fixture["error"])?,
                Some(&correlation),
            );
            logger.log_startup_acceleration_status(
                fixture["active"]
                    .as_u64()
                    .ok_or_else(|| invalid("active count"))? as usize,
                fixture["total"]
                    .as_u64()
                    .ok_or_else(|| invalid("total count"))? as usize,
                &text(&fixture["acceleration"])?,
                Some(&correlation),
            );
        }
        "format" => {
            if fixture["severity"] != "warning" {
                return Err(invalid("unsupported contract severity").into());
            }
            let mut event = ContractEvent::new(
                text(&fixture["component"])?,
                text(&fixture["event"])?,
                MessageType::Warning,
                text(&fixture["outcome"])?,
            );
            for (key, value) in fixture["context"]
                .as_object()
                .ok_or_else(|| invalid("context missing"))?
            {
                event = event.with_context(key, text(value)?);
            }
            result["formatted"] = classic_message_core::format_contract_event(&event).into();
        }
        _ => return Err(invalid("unsupported logging operation").into()),
    }
    result["records"] = std::mem::take(&mut *RECORDS.lock().expect("capture lock")).into();
    Ok(result)
}
