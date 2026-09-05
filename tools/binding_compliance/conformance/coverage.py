"""Derive executable coverage from trusted family predicates."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .failures import FailureKind
from .schema import ConformanceSchemaError, reject_duplicate_json_keys

if TYPE_CHECKING:
    from .applicability import PolicyException
    from .receipts import PreparedRunReport

_PARITY_CONTRACTS = {
    "cxx": Path("docs/implementation/cxx_api_parity/baseline/parity_contract.json"),
    "node": Path("docs/implementation/node_api_parity/baseline/parity_contract.json"),
    "python": Path(
        "docs/implementation/python_api_parity/baseline/parity_contract.json"
    ),
}
_PARITY_ANALYZERS = {
    "cxx": "cxx-source-parity",
    "node": "node-source-and-declaration-parity",
    "python": "python-source-and-stub-parity",
}
_ROW_COVERAGE_SEAL = object()
_RETAINED_ANALYZER_CATALOG_SEAL = object()


class CoverageDerivationError(ValueError):
    """Raised when family coverage policy cannot produce trustworthy facts."""


@dataclass(frozen=True)
class RetainedAnalyzerCatalog(Mapping[str, str]):
    """Permanent blocking analyzer identities with loader provenance."""

    _entries: tuple[tuple[str, str], ...]
    _provenance_seal: object | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_repository(cls, entries: Mapping[str, str]) -> RetainedAnalyzerCatalog:
        """Create a catalog after permanent-owner validation succeeds."""

        catalog = cls(tuple(sorted(entries.items())))
        object.__setattr__(
            catalog,
            "_provenance_seal",
            _RETAINED_ANALYZER_CATALOG_SEAL,
        )
        return catalog

    @property
    def has_trusted_provenance(self) -> bool:
        """Return whether the permanent catalog loader created this value."""

        return self._provenance_seal is _RETAINED_ANALYZER_CATALOG_SEAL

    def __getitem__(self, key: str) -> str:
        """Return the retained evidence kind for one analyzer identity."""

        return dict(self._entries)[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate retained analyzer identities in deterministic order."""

        return (key for key, _ in self._entries)

    def __len__(self) -> int:
        """Return the number of retained analyzers."""

        return len(self._entries)


def load_retained_analyzer_kinds(repo_root: Path) -> RetainedAnalyzerCatalog:
    """Load retained analyzers whose owners remain blocking repository gates.

    Only the permanent analyzer catalog and its blocking owners are read. The
    diagnostic migration ledger's obligation targets and migration states are
    deliberately not inputs to this trust decision.
    """

    try:
        from ..migration_ledger import (  # type: ignore[import-not-found]
            BASE_ANALYZER_CATALOG,
            BLOCKING_REQUIREMENT_IDS,
        )
    except ImportError:
        from migration_ledger import (  # type: ignore[import-not-found,no-redef]
            BASE_ANALYZER_CATALOG,
            BLOCKING_REQUIREMENT_IDS,
        )

    root = repo_root.resolve()
    analyzer_kinds: dict[str, str] = {}
    for item in BASE_ANALYZER_CATALOG:
        analyzer_id = item.get("id")
        evidence_kind = item.get("evidenceKind")
        requirement_id = item.get("blockingRequirementId")
        workflow = item.get("blockingWorkflow")
        if not isinstance(analyzer_id, str) or analyzer_id in analyzer_kinds:
            raise CoverageDerivationError(
                "retained analyzer catalog has a missing or duplicate identity"
            )
        if evidence_kind not in {"structural", "negative"}:
            raise CoverageDerivationError(
                f"retained analyzer {analyzer_id} has an unsupported evidence kind"
            )
        if (requirement_id is None) == (workflow is None):
            raise CoverageDerivationError(
                f"retained analyzer {analyzer_id} must name exactly one blocking owner"
            )
        if (
            requirement_id is not None
            and requirement_id not in BLOCKING_REQUIREMENT_IDS
        ):
            raise CoverageDerivationError(
                f"retained analyzer {analyzer_id} does not name a blocking requirement"
            )
        if workflow is not None:
            if not isinstance(workflow, Mapping):
                raise CoverageDerivationError(
                    f"retained analyzer {analyzer_id} has a malformed workflow owner"
                )
            workflow_path = workflow.get("path")
            marker = workflow.get("commandMarker")
            if not isinstance(workflow_path, str) or not isinstance(marker, str):
                raise CoverageDerivationError(
                    f"retained analyzer {analyzer_id} has a malformed workflow owner"
                )
            try:
                workflow_text = (root / workflow_path).read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                raise CoverageDerivationError(
                    f"retained analyzer {analyzer_id} cannot read its workflow owner"
                ) from error
            if marker not in workflow_text:
                raise CoverageDerivationError(
                    f"retained analyzer {analyzer_id} lost its blocking workflow command"
                )
        raw_paths = item.get("paths")
        if not isinstance(raw_paths, list) or not raw_paths:
            raise CoverageDerivationError(
                f"retained analyzer {analyzer_id} has no repository evidence paths"
            )
        for raw_path in raw_paths:
            if not isinstance(raw_path, str) or not (root / raw_path).is_file():
                raise CoverageDerivationError(
                    f"retained analyzer {analyzer_id} has a missing evidence path"
                )
        analyzer_kinds[analyzer_id] = evidence_kind
    return RetainedAnalyzerCatalog._from_repository(analyzer_kinds)


@dataclass(frozen=True)
class CoveragePredicate:
    """One family-owned fact predicate over a normalized observation.

    ``matches`` receives only the centrally normalized actual observation. The
    trusted scenario action is matched separately, so receipt runner metadata,
    test names, selector hashes, and migration state cannot influence the fact.
    """

    id: str
    capability_id: str
    action: str
    observation_family: str
    rust_symbols: tuple[str, ...]
    matches: Callable[[Mapping[str, Any]], bool]
    binding_obligation_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FamilyCoveragePolicy:
    """The executable fact predicates owned by one scenario family."""

    family_id: str
    predicates: tuple[CoveragePredicate, ...]


@dataclass(frozen=True)
class SourceParityRow:
    """One occurrence from a live CXX, Node, or Python parity inventory."""

    obligation_id: str
    participant_id: str
    mapping_origin: str
    rust_crate: str | None
    rust_symbol: str | None
    artifact: str
    locator: str
    required_evidence_kind: str = "runtime"
    retained_analyzer_id: str | None = None


def load_source_parity_rows(repo_root: Path) -> tuple[SourceParityRow, ...]:
    """Load every live parity-row occurrence with canonical Rust metadata.

    Repeated IDs receive the same occurrence suffix used by the migration
    ledger, so coverage accounting cannot collapse two source obligations into
    one set member. Raises ``CoverageDerivationError`` when an artifact is not a
    trustworthy closed row inventory.
    """

    root = repo_root.resolve()
    rows: list[SourceParityRow] = []
    for participant_id, relative_path in _PARITY_CONTRACTS.items():
        try:
            document = json.loads(
                (root / relative_path).read_text(encoding="utf-8"),
                object_pairs_hook=reject_duplicate_json_keys,
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ConformanceSchemaError,
        ) as error:
            raise CoverageDerivationError(
                f"cannot read source parity artifact {relative_path.as_posix()}: {error}"
            ) from error
        if not isinstance(document, Mapping):
            raise CoverageDerivationError(
                f"source parity artifact {relative_path.as_posix()} must be an object"
            )
        row_key = "entries" if participant_id == "cxx" else "tier1Mappings"
        raw_rows = document.get(row_key)
        if not isinstance(raw_rows, list):
            raise CoverageDerivationError(
                f"source parity artifact {relative_path.as_posix()} has no {row_key} array"
            )
        raw_ids = [
            raw_row.get("id") if isinstance(raw_row, Mapping) else None
            for raw_row in raw_rows
        ]
        totals = Counter(raw_ids)
        occurrences: Counter[object] = Counter()
        for index, raw_row in enumerate(raw_rows):
            if not isinstance(raw_row, Mapping):
                raise CoverageDerivationError(
                    f"{relative_path.as_posix()}:{row_key}[{index}] must be an object"
                )
            row_id = raw_row.get("id")
            if not isinstance(row_id, str) or not row_id:
                raise CoverageDerivationError(
                    f"{relative_path.as_posix()}:{row_key}[{index}] has no stable id"
                )
            occurrences[row_id] += 1
            occurrence_suffix = (
                f":occurrence:{occurrences[row_id]}" if totals[row_id] > 1 else ""
            )
            if participant_id == "cxx":
                binding_only = isinstance(raw_row.get("unmappedReason"), str)
                mapping_origin = "binding_only" if binding_only else "canonical_rust"
                rust_symbol = raw_row.get("coreRustSymbol")
                # Opaque transports and foreign C++ callbacks have no public
                # executable Rust operation; only the retained declaration
                # analyzer can prove their shape without inventing behavior.
                declaration_only = binding_only and (
                    raw_row.get("kind") != "function"
                    or raw_row.get("blockOrigin") == "C++"
                )
                required_evidence_kind = "structural" if declaration_only else "runtime"
            else:
                binding_only = isinstance(raw_row.get("unmappedReason"), str)
                if participant_id == "node":
                    # A Rust-side row without a Node export remains a rust-only
                    # source obligation; treating it as a binding mapping would
                    # fabricate Node applicability.
                    mapping_origin = (
                        "binding_only"
                        if binding_only
                        else "canonical_rust"
                        if raw_row.get("nodeExport")
                        else "rust_only"
                    )
                    # TypeScript erases these declaration shapes at runtime, so
                    # their blocking source/declaration analyzer is the only
                    # evidence owner that can honestly prove them.
                    required_evidence_kind = (
                        "structural"
                        if raw_row.get("nodeKind")
                        in {"interface", "type", "const_enum"}
                        else "runtime"
                    )
                else:
                    # Python parity emits only public binding rows or canonical
                    # Rust mappings; it has no separate rust-only row category.
                    mapping_origin = (
                        "binding_only" if binding_only else "canonical_rust"
                    )
                    required_evidence_kind = "runtime"
                rust_symbol = raw_row.get("rustSymbol")
            rust_crate = raw_row.get("rustCrate")
            rows.append(
                SourceParityRow(
                    obligation_id=(
                        f"parity:{participant_id}:{row_id}{occurrence_suffix}"
                    ),
                    participant_id=participant_id,
                    mapping_origin=mapping_origin,
                    rust_crate=rust_crate if isinstance(rust_crate, str) else None,
                    rust_symbol=rust_symbol if isinstance(rust_symbol, str) else None,
                    artifact=relative_path.as_posix(),
                    locator=f"/{row_key}/{index}#id={row_id}",
                    required_evidence_kind=required_evidence_kind,
                    retained_analyzer_id=(
                        _PARITY_ANALYZERS[participant_id]
                        if required_evidence_kind != "runtime"
                        else None
                    ),
                )
            )
    return tuple(rows)


@dataclass(frozen=True)
class RowCoverage:
    """The one honest evidence disposition assigned to a source parity row."""

    obligation_id: str
    participant_id: str
    mapping_origin: str
    capability_id: str | None
    evidence_kind: str
    evidence_ids: tuple[str, ...]

    def document(self) -> dict[str, object]:
        """Return the stable machine-readable row disposition."""

        return {
            "obligationId": self.obligation_id,
            "participantId": self.participant_id,
            "mappingOrigin": self.mapping_origin,
            "capabilityId": self.capability_id,
            "evidenceKind": self.evidence_kind,
            "evidenceIds": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class CoverageFailure:
    """One uncovered or dishonestly classified source parity row."""

    obligation_id: str
    message: str
    blocking: bool

    def document(self) -> dict[str, object]:
        """Return the stable coverage-mapping failure record."""

        return {
            "kind": FailureKind.COVERAGE_MAPPING.value,
            "obligationId": self.obligation_id,
            "blocking": self.blocking,
            "message": self.message,
        }


@dataclass(frozen=True)
class RowCoverageReport:
    """Source-row dispositions and fail-closed coverage gaps for one family."""

    family_id: str
    rows: tuple[RowCoverage, ...]
    failures: tuple[CoverageFailure, ...]
    execution_keys: tuple[tuple[str, str], ...]
    prepared_evidence_digest: str
    _derivation_seal: object | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_derivation(
        cls,
        family_id: str,
        *,
        prepared_reports: Sequence[PreparedRunReport] = (),
        rows: Sequence[RowCoverage] = (),
        failures: Sequence[CoverageFailure] = (),
    ) -> RowCoverageReport:
        """Create a report at the central source-row derivation boundary."""

        execution_keys = tuple(
            sorted(
                (
                    str(report.participant.get("id")),
                    str(report.participant.get("executionInstanceId")),
                )
                for report in prepared_reports
            )
        )
        report = cls(
            family_id,
            tuple(rows),
            tuple(failures),
            execution_keys,
            prepared_report_evidence_digest(prepared_reports),
        )
        object.__setattr__(report, "_derivation_seal", _ROW_COVERAGE_SEAL)
        return report

    @property
    def has_trusted_provenance(self) -> bool:
        """Return whether central source-row derivation created this report."""

        return self._derivation_seal is _ROW_COVERAGE_SEAL

    def document(self) -> dict[str, object]:
        """Return a deterministic row-coverage report document."""

        ordered_rows = sorted(self.rows, key=lambda row: row.obligation_id)
        ordered_failures = sorted(
            self.failures, key=lambda failure: failure.obligation_id
        )
        return {
            "familyId": self.family_id,
            "result": "fail" if ordered_failures else "pass",
            "executionEvidence": [
                {
                    "participantId": participant_id,
                    "executionInstanceId": execution_instance_id,
                }
                for participant_id, execution_instance_id in self.execution_keys
            ],
            "preparedEvidenceDigest": self.prepared_evidence_digest,
            "rows": [row.document() for row in ordered_rows],
            "failures": [failure.document() for failure in ordered_failures],
        }


def prepared_report_evidence_digest(
    prepared_reports: Sequence[PreparedRunReport],
) -> str:
    """Bind row coverage to the exact centrally validated report set."""

    payload = [
        report.document()
        for report in sorted(
            prepared_reports,
            key=lambda item: (
                str(item.participant.get("id")),
                str(item.participant.get("executionInstanceId")),
                str(item.invocation.get("id")),
            ),
        )
    ]
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def derive_observed_fact_ids(
    pack: Mapping[str, Any],
    scenario: Mapping[str, Any],
    normalized_observation: Mapping[str, Any],
    policy: FamilyCoveragePolicy,
) -> tuple[str, ...]:
    """Return facts proved by one trusted action and normalized observation.

    Raises ``CoverageDerivationError`` when policy references a capability,
    observation family, or Rust symbol outside the validated scenario pack, or
    when a predicate does not return a boolean result.
    """

    if policy.family_id != pack["familyId"]:
        raise CoverageDerivationError(
            "coverage policy family does not match the validated scenario pack"
        )

    capabilities = {capability["id"]: capability for capability in pack["capabilities"]}
    scenario_capability_ids = frozenset(scenario["capabilityIds"])
    fact_ids: list[str] = []
    seen_fact_ids: set[str] = set()
    for predicate in policy.predicates:
        if predicate.id in seen_fact_ids:
            raise CoverageDerivationError(
                f"duplicate family coverage predicate id: {predicate.id}"
            )
        seen_fact_ids.add(predicate.id)
        capability = capabilities.get(predicate.capability_id)
        if capability is None:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} references an unknown capability"
            )
        if predicate.observation_family not in capability["observationFamilies"]:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} references an undeclared observation family"
            )
        unknown_symbols = sorted(
            set(predicate.rust_symbols) - set(capability["rustSymbols"])
        )
        if unknown_symbols:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} references undeclared Rust symbols: "
                + ", ".join(unknown_symbols)
            )
        if (
            predicate.capability_id not in scenario_capability_ids
            or predicate.action != scenario["action"]
        ):
            continue
        try:
            matched = predicate.matches(normalized_observation)
        except Exception as error:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} could not evaluate: {error}"
            ) from error
        if type(matched) is not bool:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} must return a boolean"
            )
        if matched:
            fact_ids.append(predicate.id)
    return tuple(sorted(fact_ids))


def predicates_for_facts(
    policy: FamilyCoveragePolicy, fact_ids: Sequence[str]
) -> tuple[CoveragePredicate, ...]:
    """Return policy predicates for centrally derived fact IDs.

    This lookup is intentionally policy-owned; callers cannot introduce a fact
    identity that was not emitted by ``derive_observed_fact_ids``.
    """

    requested = set(fact_ids)
    return tuple(
        predicate for predicate in policy.predicates if predicate.id in requested
    )


def derive_row_coverage(
    pack: Mapping[str, Any],
    parity_rows: Sequence[SourceParityRow],
    policy: FamilyCoveragePolicy,
    prepared_reports: Sequence[PreparedRunReport],
    *,
    scope_participant_id: str | None = None,
    retained_analyzers: RetainedAnalyzerCatalog | None = None,
    policy_exceptions: Sequence[PolicyException] = (),
) -> RowCoverageReport:
    """Classify every live parity-row occurrence from centrally derived facts.

    Runtime credit comes only from fact IDs emitted by family predicates in a
    central ``PreparedRunReport``. Structural and negative ownership is derived
    from live source-row shape and checked against the permanent blocking
    analyzer catalog. Reviewed exceptions match participant and capability
    exactly. The diagnostic migration ledger is not an input, and every
    uncovered selected row is a blocking ``coverage_mapping_gap``. Participant
    scopes validate policy selectors against the complete source inventory,
    then classify only that participant's denominator.
    """

    # Import locally to keep receipt validation free to import predicate types
    # while still rejecting caller-authored report dictionaries at this boundary.
    from .receipts import PreparedRunReport

    if policy.family_id != pack.get("familyId"):
        raise CoverageDerivationError(
            "coverage policy family does not match the validated scenario pack"
        )
    owner = pack.get("domainOwner")
    if not isinstance(owner, Mapping) or not isinstance(owner.get("rustCrate"), str):
        raise CoverageDerivationError("validated pack has no canonical Rust owner")
    rust_crate = owner["rustCrate"]
    raw_capabilities = pack.get("capabilities")
    if not isinstance(raw_capabilities, list):
        raise CoverageDerivationError("validated pack has no capability inventory")
    capabilities: dict[str, frozenset[str]] = {}
    for raw_capability in raw_capabilities:
        if not isinstance(raw_capability, Mapping):
            raise CoverageDerivationError("validated pack capability must be an object")
        capability_id = raw_capability.get("id")
        symbols = raw_capability.get("rustSymbols")
        if not isinstance(capability_id, str) or not isinstance(symbols, list):
            raise CoverageDerivationError("validated pack capability is malformed")
        capabilities[capability_id] = frozenset(
            symbol for symbol in symbols if isinstance(symbol, str)
        )

    predicates: dict[str, CoveragePredicate] = {}
    for predicate in policy.predicates:
        if predicate.id in predicates:
            raise CoverageDerivationError(
                f"duplicate family coverage predicate id: {predicate.id}"
            )
        symbols = capabilities.get(predicate.capability_id)
        if symbols is None:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} references an unknown capability"
            )
        if set(predicate.rust_symbols) - symbols:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} references undeclared Rust symbols"
            )
        predicates[predicate.id] = predicate

    facts_by_execution: dict[tuple[str, str], set[str]] = {}
    for report in prepared_reports:
        if not isinstance(report, PreparedRunReport):
            raise CoverageDerivationError(
                "row coverage accepts only centrally validated PreparedRunReport objects"
            )
        if not report.has_trusted_coverage_provenance:
            raise CoverageDerivationError(
                "row coverage requires provenance from central receipt validation"
            )
        if report.family_id != policy.family_id:
            raise CoverageDerivationError(
                "prepared report family does not match the coverage policy"
            )
        participant_id = report.participant.get("id")
        participant_role = report.participant.get("role")
        execution_instance_id = report.participant.get("executionInstanceId")
        if not isinstance(participant_id, str) or not isinstance(
            execution_instance_id, str
        ):
            raise CoverageDerivationError(
                "prepared report has no validated execution identity"
            )
        if participant_role != "semantic-adapter":
            raise CoverageDerivationError(
                "consumer receipts cannot grant semantic parity-row coverage"
            )
        execution_key = (participant_id, execution_instance_id)
        if execution_key in facts_by_execution:
            raise CoverageDerivationError(
                "row coverage received duplicate prepared execution evidence"
            )
        execution_facts = facts_by_execution.setdefault(execution_key, set())
        if report.failures:
            continue
        for scenario in report.scenarios:
            if scenario.result != "pass":
                continue
            unknown_facts = set(scenario.observed_fact_ids) - predicates.keys()
            if unknown_facts:
                raise CoverageDerivationError(
                    "prepared report contains a fact outside the family policy: "
                    + ", ".join(sorted(unknown_facts))
                )
            execution_facts.update(scenario.observed_fact_ids)

    facts_by_participant: dict[str, set[str]] = {}
    execution_facts_by_participant: dict[str, list[set[str]]] = {}
    for (participant_id, _), fact_ids in facts_by_execution.items():
        execution_facts_by_participant.setdefault(participant_id, []).append(fact_ids)
    for participant_id, instance_fact_sets in execution_facts_by_participant.items():
        # A participant-wide row claim is only as strong as its weakest required
        # execution instance; one compiler/toolchain cannot speak for another.
        facts_by_participant[participant_id] = set.intersection(*instance_fact_sets)

    explicit_predicates_by_row: dict[str, tuple[CoveragePredicate, ...]] = {}
    explicit_row_ids = {
        obligation_id
        for predicate in policy.predicates
        for obligation_id in predicate.binding_obligation_ids
    }
    live_row_ids = {row.obligation_id for row in parity_rows}
    missing_explicit_rows = sorted(explicit_row_ids - live_row_ids)
    if missing_explicit_rows:
        raise CoverageDerivationError(
            "coverage predicates reference missing source parity rows: "
            + ", ".join(missing_explicit_rows)
        )
    for row_id in explicit_row_ids:
        explicit_predicates_by_row[row_id] = tuple(
            predicate
            for predicate in policy.predicates
            if row_id in predicate.binding_obligation_ids
        )

    selected_parity_rows = tuple(
        row
        for row in parity_rows
        if scope_participant_id is None or row.participant_id == scope_participant_id
    )

    if retained_analyzers is not None and (
        not isinstance(retained_analyzers, RetainedAnalyzerCatalog)
        or not retained_analyzers.has_trusted_provenance
    ):
        raise CoverageDerivationError(
            "row coverage requires retained analyzers from the permanent repository catalog"
        )
    if policy_exceptions:
        from .applicability import PolicyExceptionCatalog

        if (
            not isinstance(policy_exceptions, PolicyExceptionCatalog)
            or not policy_exceptions.has_trusted_provenance
        ):
            raise CoverageDerivationError(
                "row coverage requires policy exceptions from the reviewed repository catalog"
            )
    trusted_analyzers = retained_analyzers or {}
    row_results: list[RowCoverage] = []
    failures: list[CoverageFailure] = []
    for row in selected_parity_rows:
        canonical_capability_ids = tuple(
            candidate_id
            for candidate_id, symbols in sorted(capabilities.items())
            if row.mapping_origin == "canonical_rust"
            and row.rust_crate == rust_crate
            and row.rust_symbol in symbols
        )
        explicit_predicates = explicit_predicates_by_row.get(row.obligation_id, ())
        if not canonical_capability_ids and not explicit_predicates:
            # Each family owns only its canonical rows plus binding-only rows it
            # names explicitly; unrelated repository rows belong to other packs.
            continue

        if (
            row.mapping_origin == "canonical_rust"
            and explicit_predicates
            and not canonical_capability_ids
        ):
            failures.append(
                CoverageFailure(
                    row.obligation_id,
                    "explicit row selector escapes the pack's canonical Rust mapping",
                    True,
                )
            )
            continue

        explicit_capability_ids = {
            predicate.capability_id for predicate in explicit_predicates
        }
        candidate_capability_ids = (
            set(canonical_capability_ids) | explicit_capability_ids
        )
        matching_exceptions = tuple(
            exception
            for exception in policy_exceptions
            if exception.participant_id == row.participant_id
            and exception.capability_id in candidate_capability_ids
        )
        if len(matching_exceptions) > 1:
            failures.append(
                CoverageFailure(
                    row.obligation_id,
                    "source parity row matches multiple reviewed policy exceptions",
                    True,
                )
            )
            continue
        if matching_exceptions:
            exception = matching_exceptions[0]
            row_results.append(
                RowCoverage(
                    row.obligation_id,
                    row.participant_id,
                    row.mapping_origin,
                    exception.capability_id,
                    "policy-exception",
                    (exception.id,),
                )
            )
            continue

        if row.required_evidence_kind in {"structural", "negative"}:
            analyzer_id = row.retained_analyzer_id
            if (
                analyzer_id is not None
                and trusted_analyzers.get(analyzer_id) == row.required_evidence_kind
            ):
                capability_id = (
                    next(iter(candidate_capability_ids))
                    if len(candidate_capability_ids) == 1
                    else None
                )
                row_results.append(
                    RowCoverage(
                        row.obligation_id,
                        row.participant_id,
                        row.mapping_origin,
                        capability_id,
                        row.required_evidence_kind,
                        (analyzer_id,),
                    )
                )
                continue
            failures.append(
                CoverageFailure(
                    row.obligation_id,
                    f"{row.required_evidence_kind} row has no matching trusted retained analyzer",
                    True,
                )
            )
            continue
        if row.required_evidence_kind != "runtime":
            failures.append(
                CoverageFailure(
                    row.obligation_id,
                    "unsupported source-derived evidence classification: "
                    + row.required_evidence_kind,
                    True,
                )
            )
            continue

        participant_facts = facts_by_participant.get(row.participant_id, set())
        covering_fact_ids = tuple(
            sorted(
                fact_id
                for fact_id in participant_facts
                if (
                    (row.obligation_id in predicates[fact_id].binding_obligation_ids)
                    if predicates[fact_id].binding_obligation_ids
                    else (
                        predicates[fact_id].capability_id in canonical_capability_ids
                        and row.rust_symbol in predicates[fact_id].rust_symbols
                    )
                )
            )
        )
        covering_capability_ids = {
            predicates[fact_id].capability_id for fact_id in covering_fact_ids
        }
        if len(covering_capability_ids) > 1:
            failures.append(
                CoverageFailure(
                    row.obligation_id,
                    "source parity row has executable facts for multiple capabilities",
                    True,
                )
            )
            continue
        if covering_fact_ids:
            capability_id = next(iter(covering_capability_ids))
            row_results.append(
                RowCoverage(
                    row.obligation_id,
                    row.participant_id,
                    row.mapping_origin,
                    capability_id,
                    "executable",
                    covering_fact_ids,
                )
            )
            continue

        message = (
            "source parity row maps ambiguously to multiple pack capabilities"
            if len(candidate_capability_ids) > 1
            else "source parity row lacks predicate-derived executable coverage"
        )
        failures.append(CoverageFailure(row.obligation_id, message, True))

    return RowCoverageReport._from_derivation(
        str(pack["familyId"]),
        prepared_reports=prepared_reports,
        rows=tuple(row_results),
        failures=tuple(failures),
    )
