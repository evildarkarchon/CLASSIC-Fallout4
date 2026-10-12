"""Executable cross-adapter conformance lifecycle primitives."""

from .applicability import (
    ApplicabilityMatrix,
    ApplicableParticipant,
    PolicyException,
    PolicyExceptionCatalog,
    PolicyExceptionError,
    derive_applicability,
    derive_semantic_participants,
    load_policy_exceptions,
)
from .command import ConformanceCommandError, build_conformance_report_from_receipts
from .consumers import (
    ConsumerCoverageFailure,
    ConsumerCoverageReport,
    ConsumerObligation,
    ConsumerObligationCatalog,
    ConsumerObligationCoverage,
    ConsumerObligationError,
    ConsumerParticipant,
    derive_consumer_coverage,
    load_consumer_obligations,
    prepare_consumer_run,
    prepared_report_evidence_digest,
)
from .coverage import (
    CoverageDerivationError,
    CoveragePredicate,
    FamilyCoveragePolicy,
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
from .participants import (
    ParticipantCatalog,
    ParticipantCatalogError,
    load_participants,
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
    "ConsumerCoverageFailure",
    "ConsumerCoverageReport",
    "ConsumerObligation",
    "ConsumerObligationCatalog",
    "ConsumerObligationCoverage",
    "ConsumerObligationError",
    "ConsumerParticipant",
    "CoverageDerivationError",
    "CoveragePredicate",
    "FailureKind",
    "FamilyCoveragePolicy",
    "MaterializationError",
    "MaterializedRun",
    "PackValidationError",
    "ParticipantCatalog",
    "ParticipantCatalogError",
    "PolicyException",
    "PolicyExceptionCatalog",
    "PolicyExceptionError",
    "PreparedRunReport",
    "ReceiptFailure",
    "ReportScopeError",
    "RequiredExecution",
    "ScopedConformanceReport",
    "ScopedReportFailure",
    "ValidatedPack",
    "build_conformance_report_from_receipts",
    "build_scoped_report",
    "derive_applicability",
    "derive_consumer_coverage",
    "derive_semantic_participants",
    "discover_pack_paths",
    "load_and_validate_pack",
    "load_consumer_obligations",
    "load_participants",
    "load_policy_exceptions",
    "load_prepared_run",
    "materialize_run_plan",
    "prepare_consumer_run",
    "prepared_report_evidence_digest",
    "validate_conformance_report_document",
    "validate_prepared_run",
]
