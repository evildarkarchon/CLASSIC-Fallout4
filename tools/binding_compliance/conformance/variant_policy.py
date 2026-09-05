"""Trusted Crash Log Scan Run variant-to-evidence policy."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class VariantEvidenceTarget:
    """One concrete executable fact or retained analyzer for a Rust variant."""

    scenario_id: str | None
    assertion_id: str
    retained_analyzer_id: str | None = None


def _runtime(scenario_id: str, assertion_id: str) -> VariantEvidenceTarget:
    """Build one executable variant target backed by a required scenario fact."""

    return VariantEvidenceTarget(scenario_id, assertion_id)


def _retained(analyzer_id: str) -> VariantEvidenceTarget:
    """Build one irreducibly structural variant target."""

    return VariantEvidenceTarget(None, analyzer_id, analyzer_id)


_CONTRACT = "scan-run-contract-validator"
_RESET_INTERNAL = "scan-run-local-ignore-reset-internal-faults"
_FAILURE_INTERNAL = "scan-run-structured-failure-internal-faults"

CRASH_LOG_SCAN_RUN_VARIANT_TARGETS = MappingProxyType(
    {
        "request.standard": _runtime("standard-happy-path", "scan-run.discovery"),
        "request.targeted": _runtime("targeted-happy-path", "scan-run.discovery"),
        "event.discovery_completed": _runtime("standard-happy-path", "scan-run.events"),
        "event.effective_concurrency_selected": _runtime(
            "standard-happy-path", "scan-run.events"
        ),
        "event.log_queued": _runtime("standard-happy-path", "scan-run.events"),
        "event.log_started": _runtime("standard-happy-path", "scan-run.events"),
        "event.log_phase": _runtime("standard-happy-path", "scan-run.events"),
        "event.log_finished": _runtime("standard-happy-path", "scan-run.events"),
        "run_status.completed": _runtime("standard-happy-path", "scan-run.status"),
        "run_status.no_crash_logs_found": _retained(_CONTRACT),
        "run_status.setup_failed": _retained(_CONTRACT),
        "run_status.cancelled_before_discovery": _runtime(
            "pre-discovery-cancelled", "scan-run.lifecycle.pre-discovery-status"
        ),
        "run_status.cancelled": _runtime(
            "admitted-durable-cancelled", "scan-run.lifecycle.admitted-status"
        ),
        "run_status.local_ignore_recovery_required": _runtime(
            "proceed-without-ignore-recovery", "scan-run.recovery.initial-prompt"
        ),
        "discovery_source.standard": _runtime(
            "standard-happy-path", "scan-run.discovery"
        ),
        "discovery_source.targeted": _runtime(
            "targeted-happy-path", "scan-run.discovery"
        ),
        "log_disposition.succeeded": _runtime(
            "standard-happy-path", "scan-run.log-outcomes"
        ),
        "log_disposition.failed": _runtime(
            "report-write-failure", "scan-run.failure.report-write"
        ),
        "log_disposition.cancelled_before_start": _runtime(
            "post-discovery-queued-cancelled",
            "scan-run.lifecycle.queued-cancellation",
        ),
        "log_failure_stage.analysis": _retained(_FAILURE_INTERNAL),
        "log_failure_stage.report_write": _runtime(
            "report-write-failure", "scan-run.failure.report-write"
        ),
        "log_failure_stage.unsolved_logs_finalization": _runtime(
            "unsolved-logs-finalization-failure",
            "scan-run.failure.unsolved-logs-finalization",
        ),
        "infrastructure_error_stage.request_validation": _runtime(
            "request-validation-failure", "scan-run.failure.request-validation"
        ),
        "infrastructure_error_stage.discovery": _runtime(
            "discovery-failure", "scan-run.failure.discovery"
        ),
        "infrastructure_error_stage.intake": _runtime(
            "intake-failure", "scan-run.failure.intake"
        ),
        "infrastructure_error_stage.formid_database_access": _retained(
            _FAILURE_INTERNAL
        ),
        "infrastructure_error_stage.initialization": _retained(_FAILURE_INTERNAL),
        "infrastructure_error_stage.internal_invariant": _retained(_FAILURE_INTERNAL),
        "unsolved_logs_intent.leave_in_place": _runtime(
            "standard-happy-path", "scan-run.log-outcomes"
        ),
        "unsolved_logs_intent.move_to_configured_or_default": _runtime(
            "unsolved-logs-finalization-failure",
            "scan-run.failure.unsolved-logs-finalization",
        ),
        "unsolved_logs_intent.move_to_custom": _retained(_CONTRACT),
        "progress_phase.setup": _runtime("standard-happy-path", "scan-run.events"),
        "progress_phase.parse": _runtime("standard-happy-path", "scan-run.events"),
        "progress_phase.analyze": _runtime("standard-happy-path", "scan-run.events"),
        "progress_phase.finalize": _runtime("standard-happy-path", "scan-run.events"),
        "installed_yaml_data_role.main": _runtime(
            "standard-happy-path", "scan-run.installed-yaml-data"
        ),
        "installed_yaml_data_role.game": _runtime(
            "standard-happy-path", "scan-run.installed-yaml-data"
        ),
        "installed_yaml_data_provenance.updated": _retained(_CONTRACT),
        "installed_yaml_data_provenance.previous": _retained(_CONTRACT),
        "installed_yaml_data_provenance.bundled": _runtime(
            "standard-happy-path", "scan-run.installed-yaml-data"
        ),
        "installed_yaml_data_diagnostic_kind.cache_unavailable": _retained(_CONTRACT),
        "installed_yaml_data_diagnostic_kind.missing": _retained(_CONTRACT),
        "installed_yaml_data_diagnostic_kind.read": _retained(_CONTRACT),
        "installed_yaml_data_diagnostic_kind.invalid_utf8": _retained(_CONTRACT),
        "installed_yaml_data_diagnostic_kind.parse": _runtime(
            "proceed-without-ignore-recovery",
            "scan-run.recovery.initial-retained-snapshot",
        ),
        "installed_yaml_data_diagnostic_kind.invalid_schema": _retained(_CONTRACT),
        "installed_yaml_data_diagnostic_kind.incompatible_schema": _retained(_CONTRACT),
        "installed_yaml_data_diagnostic_kind.invalid_role_data": _retained(_CONTRACT),
        "installed_yaml_data_diagnostic_kind.local_ignore_generated": _runtime(
            "generated-local-ignore", "scan-run.generated.installed-yaml-data"
        ),
        "installed_yaml_data_diagnostic_kind.local_ignore_reset": _runtime(
            "reset-to-default-recovery", "scan-run.recovery.reset-to-default"
        ),
        "local_ignore_yaml_data_state.existing": _runtime(
            "standard-happy-path", "scan-run.installed-yaml-data"
        ),
        "local_ignore_yaml_data_state.generated": _runtime(
            "generated-local-ignore", "scan-run.generated.installed-yaml-data"
        ),
        "local_ignore_yaml_data_state.recovery_required": _runtime(
            "proceed-without-ignore-recovery", "scan-run.recovery.initial-prompt"
        ),
        "local_ignore_yaml_data_state.proceed_without_ignore": _runtime(
            "proceed-without-ignore-recovery",
            "scan-run.recovery.proceed-without-ignore",
        ),
        "local_ignore_yaml_data_state.reset_to_default": _runtime(
            "reset-to-default-recovery", "scan-run.recovery.reset-to-default"
        ),
        "local_ignore_recovery_decision.proceed_without_ignore": _runtime(
            "proceed-without-ignore-recovery",
            "scan-run.recovery.proceed-without-ignore",
        ),
        "local_ignore_recovery_decision.reset_to_default": _runtime(
            "reset-to-default-recovery", "scan-run.recovery.reset-to-default"
        ),
        "resume_error_kind.continuation_consumed": _runtime(
            "proceed-without-ignore-recovery",
            "scan-run.recovery.proceed-replay-rejected",
        ),
        "resume_error_kind.local_ignore_reset_conflict": _runtime(
            "reset-intervening-change-conflict", "scan-run.recovery.reset-conflict"
        ),
        "resume_error_kind.local_ignore_reset_backup_failure": _runtime(
            "reset-operational-failure",
            "scan-run.recovery.reset-operational-failure",
        ),
        "resume_error_kind.local_ignore_reset_replacement_failure": _retained(
            _RESET_INTERNAL
        ),
        "resume_error_kind.local_ignore_reset_durability_unknown": _retained(
            _RESET_INTERNAL
        ),
        "resume_error_kind.infrastructure": _runtime(
            "reset-operational-failure",
            "scan-run.recovery.reset-operational-failure",
        ),
        "recovery_continuation.retained_snapshot": _runtime(
            "proceed-without-ignore-recovery",
            "scan-run.recovery.initial-retained-snapshot",
        ),
        "recovery_continuation.single_use": _runtime(
            "proceed-without-ignore-recovery",
            "scan-run.recovery.proceed-replay-rejected",
        ),
        "recovery_continuation.pre_resume_cancelled": _runtime(
            "reset-pre-cancelled", "scan-run.recovery.reset-pre-cancelled"
        ),
        "recovery_continuation.reset_success": _runtime(
            "reset-to-default-recovery", "scan-run.recovery.reset-to-default"
        ),
        "recovery_continuation.reset_conflict": _runtime(
            "reset-intervening-change-conflict", "scan-run.recovery.reset-conflict"
        ),
        "recovery_continuation.reset_operational_failure": _runtime(
            "reset-operational-failure",
            "scan-run.recovery.reset-operational-failure",
        ),
        "recovery_continuation.reset_post_critical_cancelled": _runtime(
            "reset-post-critical-cancelled",
            "scan-run.recovery.reset-post-critical-cancelled",
        ),
        "cancellation_seam.pre_discovery": _runtime(
            "pre-discovery-cancelled",
            "scan-run.lifecycle.pre-discovery-cancellation",
        ),
        "cancellation_seam.post_discovery_queued": _runtime(
            "post-discovery-queued-cancelled",
            "scan-run.lifecycle.queued-cancellation",
        ),
        "cancellation_seam.admitted": _runtime(
            "admitted-durable-cancelled",
            "scan-run.lifecycle.admitted-cancellation",
        ),
    }
)
"""Exact source-variant partition into executable facts or retained analyzers."""
