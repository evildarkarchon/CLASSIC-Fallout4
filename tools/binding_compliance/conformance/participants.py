"""Load the central semantic participant catalog (``participants.json``).

Every family is Rust-only by default. A family that enrols another semantic
participant (today only ``cxx``) lists the capability IDs that participant
must cover; a scenario applies to it when the scenario's ``action`` is one of
those capabilities. Scenario packs never choose their own participants, and
consumers (CLI, GUI, TUI) stay in ``consumer-obligations.json``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .schema import (
    ConformanceSchemaError,
    is_stable_machine_id,
    reject_duplicate_json_keys,
)

DEFAULT_PARTICIPANTS_PATH = Path("tests/conformance/participants.json")
# Rust is implicit (it owns every capability) and consumers live in the
# consumer obligation catalog, so the only enrollable participant is CXX.
ENROLLABLE_PARTICIPANTS = frozenset({"cxx"})
_PARTICIPANT_CATALOG_SEAL = object()


class ParticipantCatalogError(ValueError):
    """Raised when the participant catalog is absent, malformed, or untrusted."""


@dataclass(frozen=True)
class ParticipantCatalog:
    """Repository-owned semantic participant enrolments with loader provenance."""

    _families: tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...]
    _provenance_seal: object | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_repository(
        cls,
        families: Mapping[str, Mapping[str, tuple[str, ...]]],
    ) -> ParticipantCatalog:
        """Create a catalog only after repository-owned source validation."""

        catalog = cls(
            tuple(
                (family_id, tuple(sorted(enrolments.items())))
                for family_id, enrolments in sorted(families.items())
            )
        )
        object.__setattr__(catalog, "_provenance_seal", _PARTICIPANT_CATALOG_SEAL)
        return catalog

    @property
    def has_trusted_provenance(self) -> bool:
        """Return whether the central repository loader created this catalog."""

        return self._provenance_seal is _PARTICIPANT_CATALOG_SEAL

    @property
    def family_ids(self) -> tuple[str, ...]:
        """Return every family that enrols a non-Rust participant, sorted."""

        return tuple(family_id for family_id, _ in self._families)

    def enrolments(self, family_id: str) -> dict[str, tuple[str, ...]]:
        """Return participant ID to enrolled capability IDs for one family.

        An unlisted family returns an empty mapping, meaning Rust-only.
        """

        for candidate, enrolments in self._families:
            if candidate == family_id:
                return dict(enrolments)
        return {}


def _machine_id(value: object, label: str) -> str:
    """Return one stable identity or raise a catalog diagnostic."""

    if not is_stable_machine_id(value):
        raise ParticipantCatalogError(f"{label} must be a stable machine identifier")
    return value


def _sorted_unique_ids(value: object, label: str) -> tuple[str, ...]:
    """Validate a non-empty, sorted, duplicate-free list of stable identities."""

    if not isinstance(value, list) or not value:
        raise ParticipantCatalogError(f"{label} must be non-empty")
    ids = tuple(
        _machine_id(item, f"{label}[{index}]") for index, item in enumerate(value)
    )
    # Canonical order keeps review diffs of enrolment changes minimal and exact.
    if list(ids) != sorted(set(ids)):
        raise ParticipantCatalogError(f"{label} must be sorted and unique")
    return ids


def load_participants(
    repo_root: Path,
    path: Path = DEFAULT_PARTICIPANTS_PATH,
) -> ParticipantCatalog:
    """Load the closed participant catalog that drives semantic applicability.

    The catalog must resolve beneath ``repo_root``; duplicate JSON keys,
    unknown fields, unknown participants, unsorted or duplicate identities and
    empty enrolments are rejected. Capability IDs are checked against each pack
    by ``derive_applicability``, which has the pack in hand.

    Raises ``ParticipantCatalogError`` when the source cannot be trusted.
    """

    root = repo_root.resolve()
    candidate = path if path.is_absolute() else root / path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise ParticipantCatalogError(
            "participant catalog must be repository-owned"
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
        raise ParticipantCatalogError(
            f"cannot read participant catalog: {error}"
        ) from error
    if not isinstance(document, Mapping) or set(document) != {
        "schemaVersion",
        "families",
    }:
        raise ParticipantCatalogError(
            "participant catalog must contain only schemaVersion and families"
        )
    if type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1:
        raise ParticipantCatalogError("participant catalog schemaVersion must be 1")
    raw_families = document["families"]
    if not isinstance(raw_families, list):
        raise ParticipantCatalogError("participant catalog families must be an array")

    families: dict[str, dict[str, tuple[str, ...]]] = {}
    family_order: list[str] = []
    for index, raw_family in enumerate(raw_families):
        label = f"participant family {index}"
        if not isinstance(raw_family, Mapping) or "familyId" not in raw_family:
            raise ParticipantCatalogError(f"{label} must name its familyId")
        family_id = _machine_id(raw_family["familyId"], f"{label} familyId")
        family_order.append(family_id)
        enrolments: dict[str, tuple[str, ...]] = {}
        for participant_id, raw_enrolment in raw_family.items():
            if participant_id == "familyId":
                continue
            if participant_id not in ENROLLABLE_PARTICIPANTS:
                raise ParticipantCatalogError(
                    f"{label} names unknown participant {participant_id}"
                )
            if not isinstance(raw_enrolment, Mapping) or set(raw_enrolment) != {
                "capabilityIds"
            }:
                raise ParticipantCatalogError(
                    f"{label} {participant_id} must contain only capabilityIds"
                )
            enrolments[participant_id] = _sorted_unique_ids(
                raw_enrolment["capabilityIds"],
                f"{label} {participant_id} capabilityIds",
            )
        if not enrolments:
            raise ParticipantCatalogError(
                f"{label} must enrol at least one participant; omit Rust-only families"
            )
        families[family_id] = enrolments
    if family_order != sorted(set(family_order)):
        raise ParticipantCatalogError(
            "participant catalog families must be sorted and unique by familyId"
        )
    return ParticipantCatalog._from_repository(families)
