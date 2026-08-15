"""Reviewed policy exceptions for narrow conformance applicability."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

from .coverage import SourceParityRow
from .schema import (
    ConformanceSchemaError,
    is_stable_machine_id,
    reject_duplicate_json_keys,
)

DEFAULT_POLICY_EXCEPTIONS_PATH = Path("tests/conformance/policy_exceptions.json")
_POLICY_EXCEPTION_CATALOG_SEAL = object()


class PolicyExceptionError(ValueError):
    """Raised when the reviewed applicability catalog is absent or malformed."""


@dataclass(frozen=True)
class PolicyException:
    """One reviewed exception scoped to one participant and capability."""

    id: str
    capability_id: str
    participant_id: str
    rationale: str
    policy_page: str


@dataclass(frozen=True)
class PolicyExceptionCatalog(Sequence[PolicyException]):
    """Reviewed repository policy exceptions with central loader provenance."""

    _items: tuple[PolicyException, ...]
    _provenance_seal: object | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_repository(
        cls, items: Sequence[PolicyException]
    ) -> PolicyExceptionCatalog:
        """Create a catalog only after repository-owned source validation."""

        catalog = cls(tuple(items))
        object.__setattr__(catalog, "_provenance_seal", _POLICY_EXCEPTION_CATALOG_SEAL)
        return catalog

    @property
    def has_trusted_provenance(self) -> bool:
        """Return whether the central repository loader created this catalog."""

        return self._provenance_seal is _POLICY_EXCEPTION_CATALOG_SEAL

    def __getitem__(
        self, index: int | slice
    ) -> PolicyException | tuple[PolicyException, ...]:
        """Return one reviewed exception or a deterministic catalog slice."""

        return self._items[index]

    def __iter__(self) -> Iterator[PolicyException]:
        """Iterate reviewed exceptions in stable identity order."""

        return iter(self._items)

    def __len__(self) -> int:
        """Return the number of reviewed exceptions."""

        return len(self._items)


@dataclass(frozen=True)
class ApplicableParticipant:
    """One source-derived participant and its exact scenario denominator."""

    id: str
    role: str
    execution_instance_ids: tuple[str, ...]
    capability_ids: tuple[str, ...]
    scenario_ids: tuple[str, ...]

    def document(self) -> dict[str, object]:
        """Return the stable machine-readable applicability record."""

        return {
            "id": self.id,
            "role": self.role,
            "executionInstanceIds": list(self.execution_instance_ids),
            "capabilityIds": list(self.capability_ids),
            "scenarioIds": list(self.scenario_ids),
        }


@dataclass(frozen=True)
class ApplicabilityMatrix:
    """The centrally derived participants required by one scenario family."""

    participants: tuple[ApplicableParticipant, ...]

    def document(self) -> dict[str, object]:
        """Return applicability in deterministic participant order."""

        return {
            "participants": [
                participant.document() for participant in self.participants
            ]
        }


DEFAULT_EXECUTION_INSTANCES: Mapping[str, tuple[str, ...]] = {
    "rust": ("rust",),
    "cxx": ("windows-clang-cl", "windows-msvc"),
    "node": ("node",),
    "python": ("python",),
}


def derive_applicability(
    pack: Mapping[str, object],
    parity_rows: tuple[SourceParityRow, ...],
    *,
    execution_instances: Mapping[str, tuple[str, ...]] = DEFAULT_EXECUTION_INSTANCES,
    policy_exceptions: Sequence[PolicyException] = (),
) -> ApplicabilityMatrix:
    """Derive semantic-adapter applicability from canonical source mappings.

    Rust owns every canonical capability. Other semantic adapters participate
    only when their live parity inventory maps the pack's Rust crate and at
    least one symbol of the capability. Caller-authored run-plan identities are
    deliberately not inputs to this decision.
    """

    owner = pack.get("domainOwner")
    if not isinstance(owner, Mapping) or not isinstance(owner.get("rustCrate"), str):
        raise PolicyExceptionError("validated pack has no canonical Rust owner")
    rust_crate = owner["rustCrate"]
    raw_capabilities = pack.get("capabilities")
    raw_scenarios = pack.get("scenarios")
    raw_consumer_obligations = pack.get("consumerObligations")
    if not isinstance(raw_capabilities, list) or not isinstance(raw_scenarios, list):
        raise PolicyExceptionError("validated pack has no capability inventory")
    if not isinstance(raw_consumer_obligations, list):
        raise PolicyExceptionError(
            "validated pack has no consumer obligation inventory"
        )
    if raw_consumer_obligations:
        # Consumer applicability needs a permanent source-derived ownership
        # registry. Until one exists, failing closed prevents a semantic-adapter
        # denominator from being mislabeled repository-complete.
        raise PolicyExceptionError(
            "consumer obligations require a source-derived consumer obligation registry"
        )

    capabilities: dict[str, frozenset[str]] = {}
    for capability in raw_capabilities:
        if not isinstance(capability, Mapping):
            raise PolicyExceptionError("validated pack capability must be an object")
        capability_id = capability.get("id")
        symbols = capability.get("rustSymbols")
        if not isinstance(capability_id, str) or not isinstance(symbols, list):
            raise PolicyExceptionError("validated pack capability is malformed")
        capabilities[capability_id] = frozenset(
            symbol for symbol in symbols if isinstance(symbol, str)
        )

    exception_scopes: set[tuple[str, str]] = set()
    for exception in policy_exceptions:
        if exception.participant_id not in execution_instances:
            raise PolicyExceptionError(
                f"policy exception {exception.id} references an unknown participant"
            )
        if exception.capability_id not in capabilities:
            raise PolicyExceptionError(
                f"policy exception {exception.id} references an unknown capability"
            )
        scope = (exception.participant_id, exception.capability_id)
        if scope in exception_scopes:
            raise PolicyExceptionError(
                "duplicate policy exception scope: "
                f"{exception.participant_id}/{exception.capability_id}"
            )
        exception_scopes.add(scope)

    participant_capabilities: dict[str, set[str]] = {
        "rust": set(capabilities),
    }
    for row in parity_rows:
        if (
            row.mapping_origin != "canonical_rust"
            or row.rust_crate != rust_crate
            or row.rust_symbol is None
        ):
            continue
        for capability_id, symbols in capabilities.items():
            if row.rust_symbol in symbols:
                participant_capabilities.setdefault(row.participant_id, set()).add(
                    capability_id
                )

    participants: list[ApplicableParticipant] = []
    for participant_id, capability_ids in sorted(participant_capabilities.items()):
        instances = execution_instances.get(participant_id)
        if not instances:
            raise PolicyExceptionError(
                f"applicable participant {participant_id} has no execution instances"
            )
        scenario_ids: list[str] = []
        for scenario in raw_scenarios:
            if not isinstance(scenario, Mapping):
                raise PolicyExceptionError("validated pack scenario must be an object")
            scenario_id = scenario.get("id")
            action = scenario.get("action")
            if (
                isinstance(scenario_id, str)
                and isinstance(action, str)
                and action in capability_ids
            ):
                scenario_ids.append(scenario_id)
        if not scenario_ids:
            continue
        participants.append(
            ApplicableParticipant(
                id=participant_id,
                role="semantic-adapter",
                execution_instance_ids=tuple(sorted(instances)),
                capability_ids=tuple(sorted(capability_ids)),
                scenario_ids=tuple(scenario_ids),
            )
        )
    return ApplicabilityMatrix(tuple(participants))


def _machine_id(value: object, label: str) -> str:
    """Return one stable exception identity or raise a catalog diagnostic."""

    if not is_stable_machine_id(value):
        raise PolicyExceptionError(f"{label} must be a stable machine identifier")
    return value


def _policy_page(repo_root: Path, value: object, label: str) -> str:
    """Validate that an exception cites one existing repository policy page."""

    if not isinstance(value, str) or not value:
        raise PolicyExceptionError(f"{label} must be a repository-relative path")
    relative = PurePosixPath(value)
    if (
        "\\" in value
        or relative.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or relative.as_posix() != value
        or any(part in {".", ".."} for part in relative.parts)
    ):
        raise PolicyExceptionError(f"{label} must be a canonical relative path")
    try:
        resolved = (repo_root / value).resolve(strict=True)
        resolved.relative_to(repo_root)
    except (OSError, ValueError) as error:
        raise PolicyExceptionError(
            f"{label} must name an existing repository-owned policy page"
        ) from error
    if not resolved.is_file():
        raise PolicyExceptionError(f"{label} must name a policy file")
    return value


def load_policy_exceptions(
    repo_root: Path,
    path: Path = DEFAULT_POLICY_EXCEPTIONS_PATH,
) -> PolicyExceptionCatalog:
    """Load the closed reviewed exception catalog in deterministic ID order.

    The catalog and every cited policy page must resolve beneath ``repo_root``.
    Raises ``PolicyExceptionError`` when the exception source cannot be trusted.
    """

    root = repo_root.resolve()
    candidate = path if path.is_absolute() else root / path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise PolicyExceptionError(
            "policy exception catalog must be repository-owned"
        ) from error

    try:
        document = json.loads(
            resolved.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ConformanceSchemaError,
    ) as error:
        raise PolicyExceptionError(
            f"cannot read policy exception catalog: {error}"
        ) from error
    if not isinstance(document, Mapping) or set(document) != {
        "schemaVersion",
        "exceptions",
    }:
        raise PolicyExceptionError(
            "policy exception catalog must contain only schemaVersion and exceptions"
        )
    if type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1:
        raise PolicyExceptionError("policy exception schemaVersion must be 1")
    raw_exceptions = document["exceptions"]
    if not isinstance(raw_exceptions, list):
        raise PolicyExceptionError(
            "policy exception catalog exceptions must be an array"
        )

    exceptions: list[PolicyException] = []
    for index, raw_exception in enumerate(raw_exceptions):
        label = f"policy exception {index}"
        if not isinstance(raw_exception, Mapping) or set(raw_exception) != {
            "id",
            "capabilityId",
            "participantId",
            "rationale",
            "policyPage",
        }:
            raise PolicyExceptionError(
                f"{label} must contain only the reviewed exception fields"
            )
        rationale = raw_exception["rationale"]
        if not isinstance(rationale, str) or not rationale.strip():
            raise PolicyExceptionError(f"{label} rationale must be non-empty")
        exceptions.append(
            PolicyException(
                id=_machine_id(raw_exception["id"], f"{label} id"),
                capability_id=_machine_id(
                    raw_exception["capabilityId"], f"{label} capabilityId"
                ),
                participant_id=_machine_id(
                    raw_exception["participantId"], f"{label} participantId"
                ),
                rationale=rationale,
                policy_page=_policy_page(
                    root, raw_exception["policyPage"], f"{label} policyPage"
                ),
            )
        )
    ids = [exception.id for exception in exceptions]
    duplicates = sorted(value for value in set(ids) if ids.count(value) > 1)
    if duplicates:
        raise PolicyExceptionError(
            f"duplicate policy exception identities: {', '.join(duplicates)}"
        )
    return PolicyExceptionCatalog._from_repository(
        tuple(sorted(exceptions, key=lambda exception: exception.id))
    )


def exception_matches(
    exception: PolicyException,
    *,
    participant_id: str,
    capability_ids: list[str],
) -> bool:
    """Return whether one exception exactly covers the reported obligation."""

    return exception.participant_id == participant_id and capability_ids == [
        exception.capability_id
    ]
