"""Load source-owned consumer obligation profiles and derive their coverage."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any

from .schema import (
    ConformanceSchemaError,
    is_stable_machine_id,
    reject_duplicate_json_keys,
)

if TYPE_CHECKING:
    from .packs import MaterializedRun, ValidatedPack

DEFAULT_CONSUMER_OBLIGATIONS_PATH = Path("tests/conformance/consumer-obligations.json")
_CATALOG_PROVENANCE_SEAL = object()
_CONSUMER_COVERAGE_PROVENANCE_SEAL = object()


class ConsumerObligationError(ValueError):
    """Raised when the permanent consumer obligation catalog is untrustworthy."""


@dataclass(frozen=True)
class ConsumerObligation:
    """One independently expected frontend behavior for named pack scenarios."""

    id: str
    scenario_ids: tuple[str, ...]
    _expected_json: str = field(repr=False)

    @classmethod
    def _from_repository(
        cls,
        obligation_id: str,
        scenario_ids: tuple[str, ...],
        expected: Mapping[str, Any],
    ) -> ConsumerObligation:
        """Freeze one trusted expectation as detached canonical JSON."""

        return cls(
            obligation_id,
            scenario_ids,
            json.dumps(
                expected,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    @property
    def expected(self) -> Mapping[str, Any]:
        """Return a fresh expectation copy so callers cannot mutate the oracle."""

        value = json.loads(self._expected_json)
        assert isinstance(value, Mapping)
        return value

    def plan_document(self) -> dict[str, object]:
        """Return the input-only portion handed to a consumer runner."""

        return {"id": self.id, "scenarioIds": list(self.scenario_ids)}

    def document(self) -> dict[str, object]:
        """Return the complete catalog record used by central comparison."""

        return {
            **self.plan_document(),
            "expected": self.expected,
        }


@dataclass(frozen=True)
class ConsumerParticipant:
    """One maintained frontend and its source-derived execution denominator."""

    id: str
    execution_instance_ids: tuple[str, ...]
    source_paths: tuple[Path, ...]
    obligations: tuple[ConsumerObligation, ...]

    def obligation(self, obligation_id: str) -> ConsumerObligation | None:
        """Return the named owned obligation, or ``None`` when it is unowned."""

        return next(
            (item for item in self.obligations if item.id == obligation_id), None
        )


@dataclass(frozen=True)
class ConsumerObligationCatalog(Sequence[tuple[str, ConsumerParticipant]]):
    """Validated repository catalog with provenance unavailable to callers."""

    path: Path
    _items: tuple[tuple[str, ConsumerParticipant], ...]
    _provenance_seal: object | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_repository(
        cls,
        path: Path,
        items: Sequence[tuple[str, ConsumerParticipant]],
    ) -> ConsumerObligationCatalog:
        """Mint a trusted catalog after closed repository validation."""

        catalog = cls(path, tuple(items))
        object.__setattr__(catalog, "_provenance_seal", _CATALOG_PROVENANCE_SEAL)
        return catalog

    @property
    def has_trusted_provenance(self) -> bool:
        """Return whether the central repository loader created this value."""

        return self._provenance_seal is _CATALOG_PROVENANCE_SEAL

    def participant(self, family_id: str, participant_id: str) -> ConsumerParticipant:
        """Return one family participant or fail closed for an unknown identity."""

        match = next(
            (
                participant
                for candidate_family, participant in self._items
                if candidate_family == family_id and participant.id == participant_id
            ),
            None,
        )
        if match is None:
            raise ConsumerObligationError(
                f"consumer {participant_id} is not registered for family {family_id}"
            )
        return match

    def participants(self, family_id: str) -> tuple[ConsumerParticipant, ...]:
        """Return the family consumers in deterministic participant order."""

        return tuple(
            participant
            for candidate_family, participant in self._items
            if candidate_family == family_id
        )

    def __getitem__(
        self, index: int | slice
    ) -> tuple[str, ConsumerParticipant] | tuple[tuple[str, ConsumerParticipant], ...]:
        """Return one catalog entry or a deterministic slice."""

        return self._items[index]

    def __iter__(self) -> Iterator[tuple[str, ConsumerParticipant]]:
        """Iterate family/participant entries in stable identity order."""

        return iter(self._items)

    def __len__(self) -> int:
        """Return the number of registered consumer participants."""

        return len(self._items)


@dataclass(frozen=True)
class ConsumerObligationCoverage:
    """One consumer obligation credited by centrally validated observations."""

    obligation_id: str
    participant_id: str
    evidence_ids: tuple[str, ...]

    def document(self) -> dict[str, object]:
        """Return the stable consumer coverage row."""

        return {
            "obligationId": self.obligation_id,
            "participantId": self.participant_id,
            "evidenceIds": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class ConsumerCoverageFailure:
    """One unresolved source-owned consumer obligation."""

    obligation_id: str
    message: str
    blocking: bool = True

    def document(self) -> dict[str, object]:
        """Return the stable coverage-gap diagnostic."""

        return {
            "kind": "coverage_mapping_gap",
            "obligationId": self.obligation_id,
            "blocking": self.blocking,
            "message": self.message,
        }


@dataclass(frozen=True)
class ConsumerCoverageReport:
    """Source-owned consumer obligations covered by exact prepared receipts."""

    family_id: str
    execution_keys: tuple[tuple[str, str], ...]
    prepared_evidence_digest: str
    obligations: tuple[ConsumerObligationCoverage, ...]
    failures: tuple[ConsumerCoverageFailure, ...]
    _provenance_seal: object | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_derivation(
        cls,
        family_id: str,
        execution_keys: Sequence[tuple[str, str]],
        prepared_evidence_digest: str,
        obligations: Sequence[ConsumerObligationCoverage],
        failures: Sequence[ConsumerCoverageFailure],
    ) -> ConsumerCoverageReport:
        """Mint coverage only after trusted receipt and registry validation."""

        report = cls(
            family_id,
            tuple(sorted(execution_keys)),
            prepared_evidence_digest,
            tuple(sorted(obligations, key=lambda item: item.obligation_id)),
            tuple(sorted(failures, key=lambda item: item.obligation_id)),
        )
        object.__setattr__(
            report,
            "_provenance_seal",
            _CONSUMER_COVERAGE_PROVENANCE_SEAL,
        )
        return report

    @property
    def has_trusted_provenance(self) -> bool:
        """Return whether central derivation created this report."""

        return self._provenance_seal is _CONSUMER_COVERAGE_PROVENANCE_SEAL

    def document(self) -> dict[str, object]:
        """Return deterministic consumer coverage for report aggregation."""

        return {
            "familyId": self.family_id,
            "result": "fail" if self.failures else "pass",
            "executionEvidence": [
                {
                    "participantId": participant_id,
                    "executionInstanceId": execution_instance_id,
                }
                for participant_id, execution_instance_id in self.execution_keys
            ],
            "preparedEvidenceDigest": self.prepared_evidence_digest,
            "obligations": [item.document() for item in self.obligations],
            "failures": [item.document() for item in self.failures],
        }


def _machine_id(value: object, label: str) -> str:
    """Return one stable identifier or raise a catalog diagnostic."""

    if not is_stable_machine_id(value):
        raise ConsumerObligationError(f"{label} must be a stable machine identifier")
    return value


def _unique_ids(
    values: object, label: str, *, nonempty: bool = True
) -> tuple[str, ...]:
    """Validate one ordered, unique stable-identity array."""

    if not isinstance(values, list) or (nonempty and not values):
        raise ConsumerObligationError(f"{label} must be a non-empty array")
    items = tuple(
        _machine_id(value, f"{label}[{index}]") for index, value in enumerate(values)
    )
    if len(items) != len(set(items)):
        raise ConsumerObligationError(f"{label} must contain unique identities")
    return items


def _relative_source_path(repo_root: Path, value: object, label: str) -> Path:
    """Return one existing repository-owned source path in canonical form."""

    if not isinstance(value, str) or not value:
        raise ConsumerObligationError(f"{label} must be a repository-relative path")
    relative = PurePosixPath(value)
    if (
        "\\" in value
        or relative.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or relative.as_posix() != value
        or any(part in {".", ".."} for part in relative.parts)
    ):
        raise ConsumerObligationError(f"{label} must be a canonical relative path")
    try:
        resolved = (repo_root / value).resolve(strict=True)
        resolved.relative_to(repo_root)
    except (OSError, ValueError) as error:
        raise ConsumerObligationError(
            f"{label} must name an existing repository-owned source path"
        ) from error
    return Path(value)


def _canonical_observation(value: object, label: str) -> Mapping[str, Any]:
    """Validate an object observation without floats or non-JSON values."""

    if not isinstance(value, Mapping):
        raise ConsumerObligationError(f"{label} must be an object")

    def visit(item: object, path: str) -> None:
        if isinstance(item, float):
            raise ConsumerObligationError(f"{path} contains a floating-point value")
        if item is None or isinstance(item, (str, bool)) or type(item) is int:
            return
        if isinstance(item, Mapping):
            if not all(isinstance(key, str) for key in item):
                raise ConsumerObligationError(f"{path} contains a non-string key")
            for key, child in item.items():
                visit(child, f"{path}.{key}")
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")
            return
        raise ConsumerObligationError(f"{path} contains a non-canonical JSON value")

    visit(value, label)
    return value


def load_consumer_obligations(
    repo_root: Path,
    path: Path = DEFAULT_CONSUMER_OBLIGATIONS_PATH,
) -> ConsumerObligationCatalog:
    """Load the permanent consumer ownership and expectation registry.

    Every catalog path must resolve beneath ``repo_root`` and every participant,
    execution instance, scenario, and obligation is closed and unique. The
    returned provenance is required before applicability or coverage may trust
    this source.
    """

    root = repo_root.resolve()
    candidate = path if path.is_absolute() else root / path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        document = json.loads(
            resolved.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (
        OSError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        ConformanceSchemaError,
    ) as error:
        raise ConsumerObligationError(
            f"cannot read consumer obligation catalog: {error}"
        ) from error
    if not isinstance(document, Mapping) or set(document) != {
        "schemaVersion",
        "families",
    }:
        raise ConsumerObligationError(
            "consumer obligation catalog must contain only schemaVersion and families"
        )
    if type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1:
        raise ConsumerObligationError("consumer obligation schemaVersion must be 1")
    raw_families = document["families"]
    if not isinstance(raw_families, list):
        raise ConsumerObligationError("consumer obligation families must be an array")

    entries: list[tuple[str, ConsumerParticipant]] = []
    family_ids: list[str] = []
    for family_index, raw_family in enumerate(raw_families):
        family_label = f"consumer family {family_index}"
        if not isinstance(raw_family, Mapping) or set(raw_family) != {
            "familyId",
            "consumers",
        }:
            raise ConsumerObligationError(
                f"{family_label} must contain only familyId and consumers"
            )
        family_id = _machine_id(raw_family["familyId"], f"{family_label} id")
        family_ids.append(family_id)
        raw_consumers = raw_family["consumers"]
        if not isinstance(raw_consumers, list) or not raw_consumers:
            raise ConsumerObligationError(f"{family_label} consumers must be non-empty")
        consumer_ids: list[str] = []
        family_obligation_ids: list[str] = []
        for consumer_index, raw_consumer in enumerate(raw_consumers):
            label = f"{family_label} consumer {consumer_index}"
            if not isinstance(raw_consumer, Mapping) or set(raw_consumer) != {
                "id",
                "executionInstanceIds",
                "sourcePaths",
                "obligations",
            }:
                raise ConsumerObligationError(f"{label} has an invalid closed shape")
            consumer_id = _machine_id(raw_consumer["id"], f"{label} id")
            consumer_ids.append(consumer_id)
            instances = _unique_ids(
                raw_consumer["executionInstanceIds"], f"{label} executionInstanceIds"
            )
            raw_paths = raw_consumer["sourcePaths"]
            if not isinstance(raw_paths, list) or not raw_paths:
                raise ConsumerObligationError(f"{label} sourcePaths must be non-empty")
            source_paths = tuple(
                _relative_source_path(root, value, f"{label} sourcePaths[{index}]")
                for index, value in enumerate(raw_paths)
            )
            if len(source_paths) != len(set(source_paths)):
                raise ConsumerObligationError(f"{label} sourcePaths must be unique")
            raw_obligations = raw_consumer["obligations"]
            if not isinstance(raw_obligations, list) or not raw_obligations:
                raise ConsumerObligationError(f"{label} obligations must be non-empty")
            obligations: list[ConsumerObligation] = []
            for obligation_index, raw_obligation in enumerate(raw_obligations):
                obligation_label = f"{label} obligation {obligation_index}"
                if not isinstance(raw_obligation, Mapping) or set(raw_obligation) != {
                    "id",
                    "scenarioIds",
                    "expected",
                }:
                    raise ConsumerObligationError(
                        f"{obligation_label} has an invalid closed shape"
                    )
                obligations.append(
                    ConsumerObligation._from_repository(
                        _machine_id(raw_obligation["id"], f"{obligation_label} id"),
                        _unique_ids(
                            raw_obligation["scenarioIds"],
                            f"{obligation_label} scenarioIds",
                        ),
                        _canonical_observation(
                            raw_obligation["expected"], f"{obligation_label} expected"
                        ),
                    )
                )
            obligation_ids = [item.id for item in obligations]
            if len(obligation_ids) != len(set(obligation_ids)):
                raise ConsumerObligationError(f"{label} obligation IDs must be unique")
            family_obligation_ids.extend(obligation_ids)
            entries.append(
                (
                    family_id,
                    ConsumerParticipant(
                        consumer_id,
                        instances,
                        source_paths,
                        tuple(obligations),
                    ),
                )
            )
        if len(consumer_ids) != len(set(consumer_ids)):
            raise ConsumerObligationError(f"{family_label} consumer IDs must be unique")
        if len(family_obligation_ids) != len(set(family_obligation_ids)):
            raise ConsumerObligationError(
                f"{family_label} obligation IDs must have exactly one consumer owner"
            )
    if len(family_ids) != len(set(family_ids)):
        raise ConsumerObligationError("consumer family IDs must be unique")
    return ConsumerObligationCatalog._from_repository(
        resolved,
        tuple(sorted(entries, key=lambda item: (item[0], item[1].id))),
    )


def prepare_consumer_run(
    pack: ValidatedPack,
    *,
    participant_id: str,
    execution_instance_id: str,
    artifact_root: Path = Path("tools/binding_compliance/artifacts"),
    catalog: ConsumerObligationCatalog | None = None,
) -> MaterializedRun:
    """Prepare an input-only consumer run from repository-owned source scope.

    Native and cross-platform launchers supply only their registered participant
    and execution instance. The catalog selects source paths and obligation
    profiles, preventing a launcher from narrowing its own denominator.
    """

    from .packs import materialize_run_plan

    trusted_catalog = catalog or load_consumer_obligations(pack.repo_root)
    return materialize_run_plan(
        pack,
        participant_id=participant_id,
        participant_role="consumer",
        execution_instance_id=execution_instance_id,
        consumer_catalog=trusted_catalog,
        artifact_root=artifact_root,
    )


def derive_consumer_coverage(
    pack: Mapping[str, Any],
    catalog: ConsumerObligationCatalog,
    prepared_reports: Sequence[object],
    *,
    scope_participant_id: str | None = None,
    scope_execution_instance_id: str | None = None,
) -> ConsumerCoverageReport:
    """Derive named consumer coverage without entering semantic row coverage.

    Coverage is the intersection of passing obligation observations across the
    source-required execution instances in scope. Runner-authored obligation IDs
    outside the prepared plan were already rejected by receipt validation and
    cannot enter this derivation.
    """

    from .coverage import prepared_report_evidence_digest
    from .receipts import PreparedRunReport

    if not catalog.has_trusted_provenance:
        raise ConsumerObligationError(
            "consumer coverage requires the repository obligation registry"
        )
    family_id = pack.get("familyId")
    if not isinstance(family_id, str):
        raise ConsumerObligationError("validated pack has no family identity")
    raw_declarations = pack.get("consumerObligations")
    if not isinstance(raw_declarations, list):
        raise ConsumerObligationError(
            "validated pack has no consumer obligation inventory"
        )
    declared_ids = {
        item.get("id")
        for item in raw_declarations
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }

    reports: list[PreparedRunReport] = []
    facts_by_execution: dict[tuple[str, str], set[str]] = {}
    for raw_report in prepared_reports:
        if not isinstance(raw_report, PreparedRunReport):
            raise ConsumerObligationError(
                "consumer coverage accepts only centrally validated prepared reports"
            )
        report = raw_report
        if not report.has_trusted_coverage_provenance:
            raise ConsumerObligationError(
                "consumer coverage requires central receipt-validation provenance"
            )
        if report.family_id != family_id:
            raise ConsumerObligationError(
                "prepared consumer report family does not match the catalog"
            )
        if report.participant.get("role") != "consumer":
            raise ConsumerObligationError(
                "semantic adapter receipts cannot grant consumer obligation coverage"
            )
        participant_id = report.participant.get("id")
        execution_instance_id = report.participant.get("executionInstanceId")
        if not isinstance(participant_id, str) or not isinstance(
            execution_instance_id, str
        ):
            raise ConsumerObligationError(
                "prepared consumer report has no execution identity"
            )
        key = (participant_id, execution_instance_id)
        if key in facts_by_execution:
            raise ConsumerObligationError(
                "consumer coverage received duplicate execution evidence"
            )
        reports.append(report)
        facts_by_execution[key] = {
            item.id
            for item in report.obligations
            if item.result == "pass" and not report.failures
        }

    rows: list[ConsumerObligationCoverage] = []
    failures: list[ConsumerCoverageFailure] = []
    selected_keys: set[tuple[str, str]] = set()
    family_participants = catalog.participants(family_id)
    # Registration is family-wide even when execution coverage is scoped. A CLI
    # job must not denominate GUI/TUI receipts, but those catalog-owned IDs are
    # still known registrations rather than missing source ownership.
    registered_ids = {
        obligation.id
        for participant in family_participants
        for obligation in participant.obligations
    }
    for participant in family_participants:
        if scope_participant_id is not None and participant.id != scope_participant_id:
            continue
        instances = tuple(
            instance_id
            for instance_id in participant.execution_instance_ids
            if scope_execution_instance_id is None
            or instance_id == scope_execution_instance_id
        )
        if not instances:
            continue
        required_keys = {(participant.id, instance_id) for instance_id in instances}
        selected_keys.update(required_keys & facts_by_execution.keys())
        selected_obligations = tuple(
            item for item in participant.obligations if item.id in declared_ids
        )
        for obligation in selected_obligations:
            if required_keys and all(
                obligation.id in facts_by_execution.get(key, set())
                for key in required_keys
            ):
                rows.append(
                    ConsumerObligationCoverage(
                        obligation.id, participant.id, obligation.scenario_ids
                    )
                )
            else:
                failures.append(
                    ConsumerCoverageFailure(
                        obligation.id,
                        "consumer obligation lacks passing evidence from every required execution instance",
                    )
                )
    missing_registrations = sorted(declared_ids - registered_ids)
    failures.extend(
        ConsumerCoverageFailure(
            obligation_id,
            "pack consumer obligation has no source-owned coverage registration",
        )
        for obligation_id in missing_registrations
    )
    selected_reports = tuple(
        report
        for report in reports
        if (
            str(report.participant["id"]),
            str(report.participant["executionInstanceId"]),
        )
        in selected_keys
    )
    return ConsumerCoverageReport._from_derivation(
        family_id,
        tuple(selected_keys),
        prepared_report_evidence_digest(selected_reports),
        rows,
        failures,
    )
