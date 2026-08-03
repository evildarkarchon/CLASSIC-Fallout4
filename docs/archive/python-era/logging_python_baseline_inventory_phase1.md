# Python Logging Baseline Inventory (Phase 1)

This inventory captures the Python behavior that defines parity expectations for phase 1 of `replicate-python-logging-standards`.

## Source Baseline

- `ClassicLib/Utils/logging_utils.py`
- `ClassicLib/messaging/backends/log_backend.py`
- `ClassicLib/support/setup.py`
- `ClassicLib/integration/factory_internal/detection.py`

## Baseline Patterns

- **Logger topology**
  - Main logger and root logger are configured together.
  - File handler defaults to `INFO`; console handler is `WARNING+`.
  - Debug mode upgrades file handlers to `DEBUG`.
- **Severity translation in message backend**
  - `INFO` and `SUCCESS` map to Python `logging.INFO`.
  - `WARNING` maps to `logging.WARNING`.
  - `ERROR` and `CRITICAL` map to error-grade severities.
  - `DEBUG` and `PROGRESS` map to `logging.DEBUG`.
- **Startup diagnostics style**
  - Startup emits explicit readiness and acceleration status lines.
  - Binding failures are logged with actionable remediation text.
  - Validation operates on the `startup_all` Rust binding contract.
- **Formatting behavior**
  - Message formatting strips emojis from content/details.
  - Details are preserved as additional context.
- **Resilience behavior**
  - File-handler setup failure degrades to console-only logging.
  - Startup binding checks fail fast when required modules are unavailable.

## Canonical Event Candidates Extracted from Baseline

- `classic.startup.binding_contract.validated`
  - Trigger: required startup Rust contract validates.
  - Severity: `info`.
  - Required fields: `event`, `severity`, `component`, `outcome`.
  - Typical context: `contract`, `checked_bindings`.
- `classic.startup.binding_contract.failed`
  - Trigger: required startup Rust contract fails import/init.
  - Severity: `error`.
  - Required fields: `event`, `severity`, `component`, `outcome`.
  - Typical context: `contract`, `missing_binding`, `failure_type`, `failure_hint`, `error`.
- `classic.startup.acceleration.status`
  - Trigger: startup acceleration status summary is emitted.
  - Severity: `info`.
  - Required fields: `event`, `severity`, `component`, `outcome`.
  - Typical context: `active_components`, `total_components`, `acceleration_level`.

## Baseline Severity Matrix (Python)

| Python message type | Python logging level | Contract severity |
| --- | --- | --- |
| `Info` | `INFO` | `info` |
| `Success` | `INFO` | `info` |
| `Warning` | `WARNING` | `warning` |
| `Error` | `ERROR` | `error` |
| `Critical` | `CRITICAL` | `error` |
| `Debug` | `DEBUG` | `debug` |
| `Progress` | `DEBUG` | `debug` |

## Redaction Baseline Observations

- Existing baseline already strips emoji in log formatting.
- Structured secret/path redaction is not yet centralized in Python v1 baseline.
- Phase 1 introduces a shared redaction policy and Rust helper implementation consumed by Rust-first surfaces.
