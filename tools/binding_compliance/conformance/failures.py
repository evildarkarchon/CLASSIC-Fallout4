"""Stable failure kinds for executable conformance evidence."""

from __future__ import annotations

from enum import StrEnum


class FailureKind(StrEnum):
    """Classify conformance failures without depending on diagnostic wording."""

    LOCAL_ENVIRONMENT = "local_environment_failure"
    ADAPTER_COMMAND = "adapter_command_failure"
    MISSING_RECEIPT = "missing_execution_receipt"
    MALFORMED_RECEIPT = "malformed_execution_receipt"
    STALE_RECEIPT = "stale_execution_receipt"
    APPLICABILITY = "applicability_violation"
    COVERAGE_MAPPING = "coverage_mapping_gap"
    NORMALIZATION = "normalization_failure"
    SEMANTIC_MISMATCH = "semantic_conformance_mismatch"
    STRUCTURAL_DRIFT = "structural_contract_drift"
    NEGATIVE_CONTRACT = "negative_contract_violation"
