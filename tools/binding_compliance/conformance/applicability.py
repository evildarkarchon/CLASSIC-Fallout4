"""Reviewed policy exceptions for narrow conformance applicability."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from .schema import (
    ConformanceSchemaError,
    is_stable_machine_id,
    reject_duplicate_json_keys,
)

DEFAULT_POLICY_EXCEPTIONS_PATH = Path("tests/conformance/policy_exceptions.json")


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
) -> tuple[PolicyException, ...]:
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
    return tuple(sorted(exceptions, key=lambda exception: exception.id))


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
