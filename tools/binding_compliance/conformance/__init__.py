"""Executable cross-adapter conformance lifecycle primitives."""

from .applicability import (
    ApplicabilityMatrix,
    ApplicableParticipant,
    PolicyException,
    PolicyExceptionCatalog,
    PolicyExceptionError,
    derive_applicability,
    load_policy_exceptions,
)
from .command import ConformanceCommandError, build_shadow_report_from_receipts
from .coverage import (
    CoverageDerivationError,
    CoverageFailure,
    CoveragePredicate,
    FamilyCoveragePolicy,
    RetainedAnalyzerCatalog,
    RowCoverage,
    RowCoverageReport,
    SourceParityRow,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
    prepared_report_evidence_digest,
)
from .failures import FailureKind
from .packs import (
    MaterializationError,
    MaterializedRun,
    PackValidationError,
    ValidatedPack,
    discover_pack_paths,
    load_and_validate_pack,
    load_prepared_run,
    materialize_run_plan,
)
from .receipts import PreparedRunReport, ReceiptFailure, validate_prepared_run
from .reports import (
    ReportScopeError,
    RequiredExecution,
    ScopedConformanceReport,
    ScopedReportFailure,
    build_scoped_report,
)
from .schema import validate_conformance_report_document

__all__ = [
    "ApplicabilityMatrix",
    "ApplicableParticipant",
    "ConformanceCommandError",
    "CoverageDerivationError",
    "CoverageFailure",
    "CoveragePredicate",
    "FailureKind",
    "FamilyCoveragePolicy",
    "MaterializationError",
    "MaterializedRun",
    "PackValidationError",
    "PolicyException",
    "PolicyExceptionCatalog",
    "PolicyExceptionError",
    "PreparedRunReport",
    "ReceiptFailure",
    "ReportScopeError",
    "RequiredExecution",
    "RetainedAnalyzerCatalog",
    "RowCoverage",
    "RowCoverageReport",
    "ScopedConformanceReport",
    "ScopedReportFailure",
    "SourceParityRow",
    "ValidatedPack",
    "build_scoped_report",
    "build_shadow_report_from_receipts",
    "derive_applicability",
    "derive_row_coverage",
    "discover_pack_paths",
    "load_and_validate_pack",
    "load_policy_exceptions",
    "load_prepared_run",
    "load_retained_analyzer_kinds",
    "load_source_parity_rows",
    "materialize_run_plan",
    "prepared_report_evidence_digest",
    "validate_conformance_report_document",
    "validate_prepared_run",
]
