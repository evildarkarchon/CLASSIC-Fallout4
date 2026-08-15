"""Executable cross-adapter conformance lifecycle primitives."""

from .applicability import (
    PolicyException,
    PolicyExceptionError,
    load_policy_exceptions,
)
from .failures import FailureKind
from .packs import (
    MaterializationError,
    MaterializedRun,
    PackValidationError,
    ValidatedPack,
    discover_pack_paths,
    load_and_validate_pack,
    materialize_run_plan,
)
from .receipts import PreparedRunReport, ReceiptFailure, validate_prepared_run

__all__ = [
    "FailureKind",
    "MaterializationError",
    "MaterializedRun",
    "PackValidationError",
    "PolicyException",
    "PolicyExceptionError",
    "PreparedRunReport",
    "ReceiptFailure",
    "ValidatedPack",
    "discover_pack_paths",
    "load_and_validate_pack",
    "load_policy_exceptions",
    "materialize_run_plan",
    "validate_prepared_run",
]
