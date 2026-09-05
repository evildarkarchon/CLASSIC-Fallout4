"""Validate tracked scenario packs and materialize input-only adapter plans."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any

from .schema import (
    ConformanceSchemaError,
    validate_pack_document,
    validate_run_plan_document,
)

if TYPE_CHECKING:
    from .consumers import ConsumerObligationCatalog

_MACHINE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")
_FIXTURE_REF = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_EXACT_JSON_PATH = re.compile(
    r"^\$(?:(?:\.[A-Za-z_][A-Za-z0-9_-]*)|(?:\[(?:0|[1-9][0-9]*)\]))+$"
)
DEFAULT_PACKS_ROOT = Path("tests/conformance/packs")
_PREPARED_RUN_SEAL = object()


class PackValidationError(ValueError):
    """Raised when a tracked scenario pack violates the common contract."""


class MaterializationError(RuntimeError):
    """Raised when a current validated pack cannot become a fresh run plan."""


@dataclass(frozen=True)
class ValidatedFixture:
    """One declared fixture bound to its repository-owned file."""

    reference: str
    relative_path: str
    resolved_path: Path


@dataclass(frozen=True)
class ValidatedPack:
    """An immutable canonical snapshot of one validated tracked pack."""

    repo_root: Path
    pack_path: Path
    canonical_json: bytes
    fixture_root: Path
    fixtures: tuple[ValidatedFixture, ...]
    expectation_digest: str
    oracle_paths: tuple[Path, ...] = ()

    def document(self) -> dict[str, Any]:
        """Return a detached copy of the validated JSON document."""

        value = json.loads(self.canonical_json)
        if not isinstance(value, dict):  # pragma: no cover - construction invariant
            raise TypeError("validated pack canonical JSON must be an object")
        return value


@dataclass(frozen=True)
class MaterializedRun:
    """Paths and immutable plan content reserved for one fresh adapter launch."""

    artifact_dir: Path
    run_plan_path: Path
    receipt_path: Path
    canonical_json: bytes
    _provenance_seal: object | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_central_preparation(
        cls,
        *,
        artifact_dir: Path,
        run_plan_path: Path,
        receipt_path: Path,
        canonical_json: bytes,
    ) -> MaterializedRun:
        """Create a run only after central materialization or authentication."""

        run = cls(
            artifact_dir=artifact_dir,
            run_plan_path=run_plan_path,
            receipt_path=receipt_path,
            canonical_json=canonical_json,
        )
        object.__setattr__(run, "_provenance_seal", _PREPARED_RUN_SEAL)
        return run

    def document(self) -> dict[str, Any]:
        """Return a detached copy of the materialized input-only run plan."""

        value = json.loads(self.canonical_json)
        if not isinstance(value, dict):  # pragma: no cover - construction invariant
            raise TypeError("materialized run plan JSON must be an object")
        return value

    @property
    def has_trusted_provenance(self) -> bool:
        """Return whether the central engine prepared or reloaded this run."""

        return self._provenance_seal is _PREPARED_RUN_SEAL


@dataclass(frozen=True)
class _SourceFile:
    """One declared source path bound to its current contained file bytes."""

    declared_path: str
    resolved_target: str
    resolved_path: Path


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    """Return an object-shaped value or raise a pack validation diagnostic."""

    if not isinstance(value, Mapping):
        raise PackValidationError(f"{label} must be an object")
    return value


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting ambiguous duplicate member names."""

    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PackValidationError(f"duplicate JSON object key: {key!r}")
        value[key] = item
    return value


def _reject_nonfinite_json_number(token: str) -> None:
    """Reject JSON extensions for NaN and infinity before canonicalization."""

    raise PackValidationError(
        f"floating-point JSON value is forbidden: non-finite token {token}"
    )


def _require_list(value: object, label: str) -> list[Any]:
    """Return a list-shaped value or raise a pack validation diagnostic."""

    if not isinstance(value, list):
        raise PackValidationError(f"{label} must be a list")
    return value


def _validate_machine_identity(value: object, label: str) -> str:
    """Validate and return one stable lowercase machine identifier."""

    if not isinstance(value, str) or _MACHINE_ID.fullmatch(value) is None:
        raise PackValidationError(
            f"{label} must be a stable machine identifier using lowercase "
            "letters, digits, dots, or hyphens"
        )
    return value


def _reject_duplicate_identities(values: list[str], label: str) -> None:
    """Reject duplicate stable identities without collapsing their occurrences."""

    duplicates = sorted(value for value in set(values) if values.count(value) > 1)
    if duplicates:
        raise PackValidationError(
            f"duplicate {label} identities: {', '.join(duplicates)}"
        )


def _validate_identities(pack: Mapping[str, Any]) -> None:
    """Validate every schema-owned stable identity in one pack."""

    _validate_machine_identity(pack.get("familyId"), "familyId")
    domain_owner = _require_mapping(pack.get("domainOwner"), "domainOwner")
    _validate_machine_identity(domain_owner.get("rustCrate"), "domainOwner.rustCrate")
    capabilities = _require_list(pack.get("capabilities"), "capabilities")
    capability_ids: list[str] = []
    for index, value in enumerate(capabilities):
        capability = _require_mapping(value, f"capabilities[{index}]")
        capability_ids.append(
            _validate_machine_identity(
                capability.get("id"), f"capabilities[{index}].id"
            )
        )
        observations = _require_list(
            capability.get("observationFamilies"),
            f"capabilities[{index}].observationFamilies",
        )
        observation_ids: list[str] = []
        for observation_index, observation_id in enumerate(observations):
            observation_ids.append(
                _validate_machine_identity(
                    observation_id,
                    f"capabilities[{index}].observationFamilies[{observation_index}]",
                )
            )
        _reject_duplicate_identities(
            observation_ids, f"capabilities[{index}] observation-family"
        )
    _reject_duplicate_identities(capability_ids, "capability")

    scenarios = _require_list(pack.get("scenarios"), "scenarios")
    scenario_ids: list[str] = []
    for index, value in enumerate(scenarios):
        scenario = _require_mapping(value, f"scenarios[{index}]")
        scenario_ids.append(
            _validate_machine_identity(scenario.get("id"), f"scenarios[{index}].id")
        )
        action = _validate_machine_identity(
            scenario.get("action"), f"scenarios[{index}].action"
        )
        raw_scenario_capability_ids = _require_list(
            scenario.get("capabilityIds"), f"scenarios[{index}].capabilityIds"
        )
        scenario_capability_ids = [
            _validate_machine_identity(
                capability_id,
                f"scenarios[{index}].capabilityIds[{capability_index}]",
            )
            for capability_index, capability_id in enumerate(
                raw_scenario_capability_ids
            )
        ]
        _reject_duplicate_identities(
            scenario_capability_ids, f"scenarios[{index}] capability"
        )
        unknown_capabilities = sorted(
            set(scenario_capability_ids) - set(capability_ids)
        )
        if unknown_capabilities:
            raise PackValidationError(
                f"scenarios[{index}] references unknown capabilities: "
                f"{', '.join(unknown_capabilities)}"
            )
        if action not in scenario_capability_ids:
            raise PackValidationError(
                f"scenarios[{index}] action must name one of its capabilityIds"
            )
    _reject_duplicate_identities(scenario_ids, "scenario")

    obligations = _require_list(pack.get("consumerObligations"), "consumerObligations")
    obligation_ids: list[str] = []
    for index, value in enumerate(obligations):
        obligation = _require_mapping(value, f"consumerObligations[{index}]")
        obligation_ids.append(
            _validate_machine_identity(
                obligation.get("id"), f"consumerObligations[{index}].id"
            )
        )
    _reject_duplicate_identities(obligation_ids, "consumer-obligation")


def _reject_floating_point_values(value: object, location: str = "$") -> None:
    """Reject floats recursively so common JSON stays cross-language canonical."""

    if isinstance(value, float):
        raise PackValidationError(
            f"floating-point JSON value is forbidden at {location}; "
            "use an integer or explicitly formatted string"
        )
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_floating_point_values(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_floating_point_values(child, f"{location}[{index}]")


def _validate_relative_posix_path(value: object, label: str) -> str:
    """Validate one canonical relative path written with POSIX separators."""

    if not isinstance(value, str) or not value:
        raise PackValidationError(f"{label} must be a non-empty relative fixture path")
    path = PurePosixPath(value)
    if (
        value == "."
        or "\\" in value
        or path.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or path.as_posix() != value
        or any(part in {".", ".."} for part in path.parts)
    ):
        raise PackValidationError(
            f"{label} must be a canonical relative fixture path without traversal"
        )
    return value


def _validate_fixtures(
    pack: Mapping[str, Any], repo_root: Path
) -> tuple[Path, tuple[ValidatedFixture, ...]]:
    """Resolve declared fixtures and prove that every file stays under its root."""

    fixture_root_value = _validate_relative_posix_path(
        pack.get("fixtureRoot"), "fixtureRoot"
    )
    try:
        fixture_root = (repo_root / fixture_root_value).resolve(strict=True)
        fixture_root.relative_to(repo_root)
    except (OSError, ValueError) as error:
        raise PackValidationError(
            "fixtureRoot must resolve to a repository-owned directory"
        ) from error
    if not fixture_root.is_dir():
        raise PackValidationError("fixtureRoot must resolve to a directory")

    declarations = _require_mapping(pack.get("fixtures"), "fixtures")
    resolved: list[ValidatedFixture] = []
    seen_paths: set[str] = set()
    for reference, raw_path in declarations.items():
        if not isinstance(reference, str) or _FIXTURE_REF.fullmatch(reference) is None:
            raise PackValidationError(
                f"fixture reference {reference!r} must be a stable alias"
            )
        relative_path = _validate_relative_posix_path(raw_path, f"fixtures.{reference}")
        if relative_path in seen_paths:
            raise PackValidationError(
                f"fixture path {relative_path!r} is declared more than once"
            )
        seen_paths.add(relative_path)
        try:
            fixture_path = (fixture_root / relative_path).resolve(strict=True)
            fixture_path.relative_to(fixture_root)
        except (OSError, ValueError) as error:
            raise PackValidationError(
                f"fixture {reference!r} must resolve beneath fixtureRoot"
            ) from error
        if not fixture_path.is_file():
            raise PackValidationError(f"fixture {reference!r} must resolve to a file")
        resolved.append(ValidatedFixture(reference, relative_path, fixture_path))

    declared_refs = set(declarations)
    scenarios = _require_list(pack.get("scenarios"), "scenarios")
    for index, value in enumerate(scenarios):
        scenario = _require_mapping(value, f"scenarios[{index}]")
        fixture_refs = _require_list(
            scenario.get("fixtureRefs"), f"scenarios[{index}].fixtureRefs"
        )
        if not all(isinstance(reference, str) for reference in fixture_refs):
            raise PackValidationError(
                f"scenarios[{index}].fixtureRefs must contain fixture aliases"
            )
        duplicates = sorted(
            reference
            for reference in set(fixture_refs)
            if fixture_refs.count(reference) > 1
        )
        if duplicates:
            raise PackValidationError(
                f"scenarios[{index}] contains duplicate fixture references: "
                f"{', '.join(duplicates)}"
            )
        undeclared = sorted(set(fixture_refs) - declared_refs)
        if undeclared:
            raise PackValidationError(
                f"scenarios[{index}] references undeclared fixtures: "
                f"{', '.join(undeclared)}"
            )
    resolved.sort(key=lambda fixture: (fixture.relative_path, fixture.reference))
    return fixture_root, tuple(resolved)


def _validate_normalization_path(value: object, label: str) -> str:
    """Return one exact non-root JSON path without wildcard operations."""

    if not isinstance(value, str) or _EXACT_JSON_PATH.fullmatch(value) is None:
        raise PackValidationError(
            f"normalization {label} must be one exact JSON path without "
            "wildcards, recursive descent, or root-wide selection"
        )
    return value


def _validate_normalization(pack: Mapping[str, Any]) -> None:
    """Validate every scenario's narrow, rationale-bearing normalization rules."""

    scenarios = _require_list(pack.get("scenarios"), "scenarios")
    for index, value in enumerate(scenarios):
        scenario = _require_mapping(value, f"scenarios[{index}]")
        normalization = _require_mapping(
            scenario.get("normalization"), f"scenarios[{index}].normalization"
        )
        if not isinstance(normalization.get("rootRelativePaths"), bool):
            raise PackValidationError(
                f"normalization for scenarios[{index}] needs boolean rootRelativePaths"
            )
        unordered_values = _require_list(
            normalization.get("unorderedPaths"),
            f"scenarios[{index}].normalization.unorderedPaths",
        )
        unordered = [
            _validate_normalization_path(
                path, f"scenarios[{index}].unorderedPaths[{path_index}]"
            )
            for path_index, path in enumerate(unordered_values)
        ]
        if len(unordered) != len(set(unordered)):
            raise PackValidationError(
                f"normalization for scenarios[{index}] contains duplicate "
                "unordered paths"
            )

        excluded_values = _require_list(
            normalization.get("excludedPaths"),
            f"scenarios[{index}].normalization.excludedPaths",
        )
        excluded: list[str] = []
        for path_index, value in enumerate(excluded_values):
            exclusion = _require_mapping(
                value,
                f"scenarios[{index}].normalization.excludedPaths[{path_index}]",
            )
            if set(exclusion) != {"path", "rationale"}:
                raise PackValidationError(
                    f"normalization exclusion {path_index} for scenarios[{index}] "
                    "must contain only path and rationale"
                )
            path = _validate_normalization_path(
                exclusion.get("path"),
                f"scenarios[{index}].excludedPaths[{path_index}]",
            )
            rationale = exclusion.get("rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                raise PackValidationError(
                    f"normalization exclusion {path!r} for scenarios[{index}] "
                    "requires a non-empty rationale"
                )
            excluded.append(path)
        if len(excluded) != len(set(excluded)):
            raise PackValidationError(
                f"normalization for scenarios[{index}] contains duplicate "
                "excluded paths"
            )
        overlap = sorted(set(unordered) & set(excluded))
        if overlap:
            raise PackValidationError(
                f"normalization paths cannot be both unordered and excluded: "
                f"{', '.join(overlap)}"
            )


def _digest_frame(digest: Any, tag: bytes, payload: bytes) -> None:
    """Add one type-tagged, length-prefixed byte frame to a SHA-256 digest."""

    digest.update(len(tag).to_bytes(8, "big"))
    digest.update(tag)
    digest.update(len(payload).to_bytes(8, "big"))
    digest.update(payload)


def _expectation_digest(
    canonical_pack: bytes,
    fixtures: tuple[ValidatedFixture, ...],
    oracle_sources: tuple[tuple[str, bytes], ...] = (),
) -> str:
    """Hash canonical content, input fixtures, and any separate authored oracle."""

    digest = hashlib.sha256()
    _digest_frame(digest, b"contract", b"classic-conformance-expectation-v1")
    _digest_frame(digest, b"pack", canonical_pack)
    for relative_path, oracle_bytes in oracle_sources:
        _digest_frame(digest, b"oracle-path", relative_path.encode("utf-8"))
        _digest_frame(digest, b"oracle-bytes", oracle_bytes)
    for fixture in fixtures:
        _digest_frame(digest, b"fixture-path", fixture.relative_path.encode("utf-8"))
        try:
            fixture_bytes = fixture.resolved_path.read_bytes()
        except OSError as error:
            raise PackValidationError(
                f"cannot read declared fixture {fixture.reference!r}: {error}"
            ) from error
        _digest_frame(digest, b"fixture-bytes", fixture_bytes)
    return f"sha256:{digest.hexdigest()}"


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    """Serialize a validated common document using the canonical JSON contract."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _run_git(repo_root: Path, arguments: Sequence[str]) -> bytes:
    """Run one read-only Git query needed to bind current source identity."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = (
            error.stderr.decode("utf-8", errors="replace").strip()
            if isinstance(error, subprocess.CalledProcessError) and error.stderr
            else str(error)
        )
        raise MaterializationError(
            f"cannot compute current source identity with git: {detail}"
        ) from error
    return completed.stdout


def _lexical_repository_path(repo_root: Path, candidate: Path) -> tuple[str, Path]:
    """Return a declared relative path and its contained resolved target.

    Raises ``MaterializationError`` when the path is absent or either its lexical
    identity or resolved target escapes the repository.
    """

    lexical = Path(os.path.abspath(candidate))
    try:
        declared = lexical.relative_to(repo_root).as_posix()
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repo_root)
    except (OSError, ValueError) as error:
        raise MaterializationError(
            f"source input must resolve beneath repository root: {candidate}"
        ) from error
    return declared, resolved


def _source_inputs(
    pack: ValidatedPack, source_paths: Sequence[Path]
) -> tuple[tuple[str, ...], tuple[_SourceFile, ...]]:
    """Expand every declared source root into contained current file inputs.

    Raises ``MaterializationError`` when a declared root is absent, escapes the
    repository, or does not resolve to a file or directory.
    """

    candidates = [pack.pack_path]
    candidates.extend(pack.oracle_paths)
    candidates.extend(fixture.resolved_path for fixture in pack.fixtures)
    candidates.extend(
        path if path.is_absolute() else pack.repo_root / path for path in source_paths
    )
    declared_roots: set[str] = set()
    files: dict[str, _SourceFile] = {}
    for candidate in candidates:
        declared_root, resolved_root = _lexical_repository_path(
            pack.repo_root, candidate
        )
        declared_roots.add(declared_root)
        if resolved_root.is_file():
            paths = (candidate,)
        elif resolved_root.is_dir():
            paths = tuple(path for path in candidate.rglob("*") if path.is_file())
        else:
            raise MaterializationError(
                f"source input must resolve to a file or directory: {candidate}"
            )
        for path in paths:
            declared_path, resolved_path = _lexical_repository_path(
                pack.repo_root, path
            )
            resolved_target = resolved_path.relative_to(pack.repo_root).as_posix()
            files[declared_path] = _SourceFile(
                declared_path=declared_path,
                resolved_target=resolved_target,
                resolved_path=resolved_path,
            )
    return tuple(sorted(declared_roots)), tuple(files[path] for path in sorted(files))


def _source_identity(pack: ValidatedPack, source_paths: Sequence[Path]) -> str:
    """Return current commit plus declared participant-input content digest.

    Raises ``MaterializationError`` when Git cannot identify the current commit
    or any declared input cannot be contained, expanded, or read.
    """

    revision = (
        _run_git(pack.repo_root, ("rev-parse", "--verify", "HEAD"))
        .decode("ascii")
        .strip()
    )
    if re.fullmatch(r"[0-9a-fA-F]{40,64}", revision) is None:
        raise MaterializationError("git returned an invalid current revision identity")

    declared_roots, source_files = _source_inputs(pack, source_paths)
    digest = hashlib.sha256()
    _digest_frame(digest, b"contract", b"classic-conformance-source-v1")
    for declared_root in declared_roots:
        _digest_frame(digest, b"source-root", declared_root.encode("utf-8"))
    for source_file in source_files:
        try:
            content = source_file.resolved_path.read_bytes()
        except OSError as error:
            raise MaterializationError(
                f"cannot bind source input {source_file.declared_path!r}: {error}"
            ) from error
        _digest_frame(digest, b"source-path", source_file.declared_path.encode("utf-8"))
        _digest_frame(
            digest, b"source-target", source_file.resolved_target.encode("utf-8")
        )
        _digest_frame(digest, b"source-bytes", content)
    return f"git:{revision.lower()}:sha256:{digest.hexdigest()}"


def _declared_participant_source_paths(
    pack: ValidatedPack, source_paths: Sequence[Path]
) -> tuple[str, ...]:
    """Return canonical repository-relative runner/source roots for revalidation."""

    declared = [
        _lexical_repository_path(
            pack.repo_root,
            path if path.is_absolute() else pack.repo_root / path,
        )[0]
        for path in source_paths
    ]
    if len(declared) != len(set(declared)):
        raise MaterializationError(
            "materialization source paths must name unique repository roots"
        )
    return tuple(sorted(declared))


def _run_plan_digest(plan_without_digest: Mapping[str, Any]) -> str:
    """Hash every plan field except the self-referential digest field itself."""

    digest = hashlib.sha256()
    _digest_frame(digest, b"contract", b"classic-conformance-run-plan-v1")
    _digest_frame(digest, b"plan", _canonical_json(plan_without_digest))
    return f"sha256:{digest.hexdigest()}"


def discover_pack_paths(
    repo_root: Path, packs_root: Path = DEFAULT_PACKS_ROOT
) -> tuple[Path, ...]:
    """Return repository-owned JSON pack paths in deterministic relative order.

    A missing pack root yields an empty result so the generic engine can land
    before the first domain pack. Existing roots and discovered symlinks must
    remain contained beneath the repository. Raises ``PackValidationError``
    when an existing discovery root or JSON pack escapes that boundary.
    """

    root = repo_root.resolve()
    candidate = packs_root if packs_root.is_absolute() else root / packs_root
    if not candidate.exists():
        return ()
    try:
        resolved_root = candidate.resolve(strict=True)
        resolved_root.relative_to(root)
    except (OSError, ValueError) as error:
        raise PackValidationError(
            f"pack discovery root must resolve beneath repository root: {packs_root}"
        ) from error
    if not resolved_root.is_dir():
        raise PackValidationError("pack discovery root must be a directory")

    discovered: list[Path] = []
    for candidate_path in resolved_root.rglob("*.json"):
        try:
            resolved_path = candidate_path.resolve(strict=True)
            resolved_path.relative_to(resolved_root)
        except (OSError, ValueError) as error:
            raise PackValidationError(
                f"discovered pack must resolve beneath pack root: {candidate_path}"
            ) from error
        if resolved_path.is_file():
            discovered.append(resolved_path)
    return tuple(sorted(discovered, key=lambda path: path.relative_to(root).as_posix()))


def _create_artifact_directory(
    artifact_root: Path,
    participant_id: str,
    execution_instance_id: str,
    invocation_id: str,
) -> Path:
    """Create a fresh invocation directory without following an escaping component.

    Raises ``MaterializationError`` when a component escapes, is not a directory,
    already exists at invocation scope, or cannot be created.
    """

    try:
        artifact_root.mkdir(parents=True, exist_ok=True)
        resolved_root = artifact_root.resolve(strict=True)
    except OSError as error:
        raise MaterializationError(
            f"artifact root cannot be created: {artifact_root}"
        ) from error
    parent = resolved_root
    for component in (participant_id, execution_instance_id):
        candidate = parent / component
        try:
            if candidate.is_symlink() or candidate.is_junction():
                raise MaterializationError(
                    f"artifact identity component cannot be a redirect: {candidate}"
                )
            candidate.mkdir(exist_ok=True)
            # Recheck after creation so a concurrent replacement cannot redirect
            # one participant's invocation into another participant's subtree.
            if candidate.is_symlink() or candidate.is_junction():
                raise MaterializationError(
                    f"artifact identity component cannot be a redirect: {candidate}"
                )
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(resolved_root)
        except (OSError, ValueError) as error:
            raise MaterializationError(
                f"artifact component must stay beneath artifact root: {candidate}"
            ) from error
        if not resolved.is_dir():
            raise MaterializationError(
                f"artifact component must be a directory: {candidate}"
            )
        parent = resolved
    invocation_dir = parent / invocation_id
    try:
        invocation_dir.mkdir(exist_ok=False)
        resolved_invocation = invocation_dir.resolve(strict=True)
        resolved_invocation.relative_to(resolved_root)
    except (OSError, ValueError) as error:
        raise MaterializationError(
            "fresh artifact directory already exists, escapes the artifact root, "
            f"or cannot be created: {invocation_dir}"
        ) from error
    return resolved_invocation


def materialize_run_plan(
    pack: ValidatedPack,
    *,
    participant_id: str,
    participant_role: str,
    execution_instance_id: str,
    source_paths: Sequence[Path] = (),
    consumer_catalog: ConsumerObligationCatalog | None = None,
    artifact_root: Path = Path("tools/binding_compliance/artifacts"),
) -> MaterializedRun:
    """Materialize one fresh input-only adapter plan in a clean artifact path.

    ``source_paths`` names the participant and runner inputs whose declared path
    identities and current bytes join the current commit in ``sourceIdentity``.
    The returned receipt path is reserved but remains absent so an earlier
    execution can never satisfy this launch. Raises ``MaterializationError`` for
    stale validation, invalid launch identity, source inspection failure, or any
    pre-existing or escaping artifact target.
    """

    for value, label in (
        (participant_id, "participant id"),
        (execution_instance_id, "execution-instance id"),
    ):
        try:
            _validate_machine_identity(value, label)
        except PackValidationError as error:
            raise MaterializationError(str(error)) from error
    if participant_role not in {"semantic-adapter", "consumer"}:
        raise MaterializationError(
            "participant role must be semantic-adapter or consumer"
        )
    if participant_role == "semantic-adapter" and not source_paths:
        raise MaterializationError(
            "materialization requires relevant participant or runner source paths"
        )
    if participant_role == "consumer":
        if source_paths:
            raise MaterializationError(
                "consumer source paths come only from the repository obligation registry"
            )
        if consumer_catalog is None or not consumer_catalog.has_trusted_provenance:
            raise MaterializationError(
                "consumer materialization requires the repository obligation registry"
            )
        try:
            consumer = consumer_catalog.participant(
                str(pack.document()["familyId"]), participant_id
            )
        except ValueError as error:
            raise MaterializationError(str(error)) from error
        if execution_instance_id not in consumer.execution_instance_ids:
            raise MaterializationError(
                f"execution instance {execution_instance_id} is not registered for consumer {participant_id}"
            )
        try:
            catalog_path = consumer_catalog.path.relative_to(pack.repo_root)
        except ValueError as error:  # pragma: no cover - loader containment invariant
            raise MaterializationError(
                "consumer obligation registry must stay beneath the repository root"
            ) from error
        source_paths = (catalog_path, *consumer.source_paths)

    current = load_and_validate_pack(pack.repo_root, pack.pack_path)
    if (
        current.canonical_json != pack.canonical_json
        or current.expectation_digest != pack.expectation_digest
    ):
        raise MaterializationError(
            "validated pack or declared fixture changed before materialization"
        )

    declared_source_paths = _declared_participant_source_paths(pack, source_paths)
    source_identity = _source_identity(
        pack, tuple(Path(path) for path in declared_source_paths)
    )
    invocation_id = str(uuid.uuid4())
    pack_document = pack.document()
    scenarios = [
        {
            "id": scenario["id"],
            "action": scenario["action"],
            "capabilityIds": scenario["capabilityIds"],
            "fixtureRefs": scenario["fixtureRefs"],
            "input": scenario["input"],
            "normalization": scenario["normalization"],
        }
        for scenario in pack_document["scenarios"]
    ]
    plan: dict[str, Any] = {
        "schemaVersion": 1,
        "familyId": pack_document["familyId"],
        "familyVersion": pack_document["familyVersion"],
        "expectationDigest": pack.expectation_digest,
        "fixtureRoot": str(pack.fixture_root),
        "fixtures": {
            fixture.reference: str(fixture.resolved_path)
            for fixture in sorted(pack.fixtures, key=lambda item: item.reference)
        },
        "sourcePaths": list(declared_source_paths),
        "participant": {
            "id": participant_id,
            "role": participant_role,
            "executionInstanceId": execution_instance_id,
        },
        "invocation": {
            "id": invocation_id,
            "sourceIdentity": source_identity,
        },
    }
    if participant_role == "semantic-adapter":
        plan["scenarios"] = scenarios
    else:
        declared_obligation_ids = {
            item["id"] for item in pack_document["consumerObligations"]
        }
        obligations = [
            obligation.plan_document()
            for obligation in consumer.obligations
            if obligation.id in declared_obligation_ids
        ]
        if not obligations:
            raise MaterializationError(
                f"consumer {participant_id} owns no obligations selected by the pack"
            )
        plan["obligations"] = obligations
    plan["invocation"]["runPlanDigest"] = _run_plan_digest(plan)
    try:
        validate_run_plan_document(plan)
    except ConformanceSchemaError as error:  # pragma: no cover - construction invariant
        raise MaterializationError(str(error)) from error
    canonical_plan = _canonical_json(plan)

    artifact_candidate = (
        artifact_root if artifact_root.is_absolute() else pack.repo_root / artifact_root
    )
    try:
        resolved_artifact_root = artifact_candidate.resolve(strict=False)
        resolved_artifact_root.relative_to(pack.repo_root)
    except (OSError, ValueError) as error:
        raise MaterializationError(
            "artifact root must resolve beneath repository root"
        ) from error
    artifact_dir = _create_artifact_directory(
        resolved_artifact_root,
        participant_id,
        execution_instance_id,
        invocation_id,
    )

    run_plan_path = artifact_dir / "run_plan.json"
    receipt_path = artifact_dir / "receipt.json"
    temporary_path = artifact_dir / ".run_plan.tmp"
    try:
        with temporary_path.open("xb") as output:
            output.write(canonical_plan)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, run_plan_path)
    except OSError as error:
        # This directory belongs only to this failed invocation; leave no stale plan.
        temporary_path.unlink(missing_ok=True)
        run_plan_path.unlink(missing_ok=True)
        try:
            artifact_dir.rmdir()
        except OSError:
            # Preserve the primary write failure if external interference left files.
            pass
        raise MaterializationError(f"cannot write fresh run plan: {error}") from error
    return MaterializedRun._from_central_preparation(
        artifact_dir=artifact_dir,
        run_plan_path=run_plan_path,
        receipt_path=receipt_path,
        canonical_json=canonical_plan,
    )


def load_prepared_run(
    pack: ValidatedPack,
    run_plan_path: Path,
    *,
    receipt_path: Path | None = None,
    consumer_catalog: ConsumerObligationCatalog | None = None,
) -> MaterializedRun:
    """Reload and authenticate one repository-owned materialized run plan.

    This is the receipt-only CLI boundary used after a native launcher exits.
    It validates the closed plan, its digest, current pack-owned fields, source
    revision, and sibling artifact paths before minting trusted provenance.
    """

    root = pack.repo_root.resolve()
    candidate = run_plan_path if run_plan_path.is_absolute() else root / run_plan_path
    try:
        resolved_plan = candidate.resolve(strict=True)
        resolved_plan.relative_to(root)
    except (OSError, ValueError) as error:
        raise MaterializationError(
            "prepared run plan must resolve beneath the repository root"
        ) from error
    if not resolved_plan.is_file():
        raise MaterializationError("prepared run plan must resolve to a file")
    try:
        canonical_plan = resolved_plan.read_bytes()
        value = json.loads(
            canonical_plan,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json_number,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, PackValidationError) as error:
        raise MaterializationError(f"cannot read prepared run plan: {error}") from error
    if not isinstance(value, Mapping):
        raise MaterializationError("run plan must be an object")
    plan = value
    try:
        validate_run_plan_document(plan)
    except ConformanceSchemaError as error:
        raise MaterializationError(str(error)) from error
    try:
        _reject_floating_point_values(plan)
    except PackValidationError as error:
        raise MaterializationError(str(error)) from error
    if canonical_plan != _canonical_json(plan):
        raise MaterializationError("prepared run plan is not canonical JSON")

    pack_document = pack.document()
    expected_scenarios = [
        {
            "id": scenario["id"],
            "action": scenario["action"],
            "capabilityIds": scenario["capabilityIds"],
            "fixtureRefs": scenario["fixtureRefs"],
            "input": scenario["input"],
            "normalization": scenario["normalization"],
        }
        for scenario in pack_document["scenarios"]
    ]
    expected_pack_fields: dict[str, Any] = {
        "schemaVersion": 1,
        "familyId": pack_document["familyId"],
        "familyVersion": pack_document["familyVersion"],
        "expectationDigest": pack.expectation_digest,
        "fixtureRoot": str(pack.fixture_root),
        "fixtures": {
            fixture.reference: str(fixture.resolved_path)
            for fixture in sorted(pack.fixtures, key=lambda item: item.reference)
        },
    }
    if plan["participant"]["role"] == "semantic-adapter":
        expected_pack_fields["scenarios"] = expected_scenarios
    else:
        if consumer_catalog is None or not consumer_catalog.has_trusted_provenance:
            raise MaterializationError(
                "consumer run plan requires the repository obligation registry"
            )
        try:
            consumer = consumer_catalog.participant(
                str(pack_document["familyId"]), str(plan["participant"]["id"])
            )
        except ValueError as error:
            raise MaterializationError(str(error)) from error
        if (
            plan["participant"]["executionInstanceId"]
            not in consumer.execution_instance_ids
        ):
            raise MaterializationError(
                "consumer execution instance is no longer source-applicable"
            )
        declared_obligation_ids = {
            item["id"] for item in pack_document["consumerObligations"]
        }
        expected_pack_fields["obligations"] = [
            obligation.plan_document()
            for obligation in consumer.obligations
            if obligation.id in declared_obligation_ids
        ]
        try:
            catalog_path = consumer_catalog.path.relative_to(pack.repo_root)
        except ValueError as error:  # pragma: no cover - loader containment invariant
            raise MaterializationError(
                "consumer obligation registry must stay beneath the repository root"
            ) from error
        expected_pack_fields["sourcePaths"] = list(
            _declared_participant_source_paths(
                pack, (catalog_path, *consumer.source_paths)
            )
        )
    mismatches = sorted(
        key
        for key, expected in expected_pack_fields.items()
        if plan.get(key) != expected
    )
    if mismatches:
        raise MaterializationError(
            "prepared run plan no longer matches the current tracked pack: "
            + ", ".join(mismatches)
        )

    invocation = plan["invocation"]
    run_plan_digest = invocation.get("runPlanDigest")
    plan_without_digest = dict(plan)
    invocation_without_digest = dict(invocation)
    invocation_without_digest.pop("runPlanDigest", None)
    plan_without_digest["invocation"] = invocation_without_digest
    if run_plan_digest != _run_plan_digest(plan_without_digest):
        raise MaterializationError(
            "prepared run plan digest does not match its content"
        )
    raw_source_paths = plan["sourcePaths"]
    try:
        source_paths = tuple(
            Path(_validate_relative_posix_path(path, f"sourcePaths[{index}]"))
            for index, path in enumerate(raw_source_paths)
        )
        expected_source_identity = _source_identity(pack, source_paths)
    except (PackValidationError, MaterializationError) as error:
        raise MaterializationError(str(error)) from error
    if invocation.get("sourceIdentity") != expected_source_identity:
        raise MaterializationError(
            "prepared run plan source identity does not match current declared inputs"
        )

    artifact_dir = resolved_plan.parent
    receipt_candidate = receipt_path or artifact_dir / "receipt.json"
    if not receipt_candidate.is_absolute():
        receipt_candidate = root / receipt_candidate
    try:
        resolved_receipt = receipt_candidate.resolve(strict=False)
        resolved_receipt.relative_to(root)
    except (OSError, ValueError) as error:
        raise MaterializationError(
            "prepared receipt path must stay beneath the repository root"
        ) from error
    if resolved_receipt.parent != artifact_dir:
        raise MaterializationError(
            "prepared receipt must be a sibling of its immutable run plan"
        )
    return MaterializedRun._from_central_preparation(
        artifact_dir=artifact_dir,
        run_plan_path=resolved_plan,
        receipt_path=resolved_receipt,
        canonical_json=canonical_plan,
    )


def load_and_validate_pack(repo_root: Path, pack_path: Path) -> ValidatedPack:
    """Load one repository-owned scenario pack and validate its stable identities.

    Returns a canonical immutable snapshot suitable for later digesting and
    materialization. Raises ``PackValidationError`` when the pack cannot be read
    as a repository-owned JSON object or violates the closed pack, fixture,
    identity, reference, number, or normalization contract.
    """

    root = repo_root.resolve()
    candidate = pack_path if pack_path.is_absolute() else root / pack_path
    try:
        resolved_pack = candidate.resolve(strict=True)
        resolved_pack.relative_to(root)
    except (OSError, ValueError) as error:
        raise PackValidationError(
            f"tracked pack must resolve beneath repository root: {pack_path}"
        ) from error
    try:
        value = json.loads(
            resolved_pack.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json_number,
        )
    except (OSError, json.JSONDecodeError) as error:
        raise PackValidationError(
            f"cannot read tracked pack {pack_path}: {error}"
        ) from error
    pack = _require_mapping(value, "pack")
    try:
        validate_pack_document(pack)
    except ConformanceSchemaError as error:
        raise PackValidationError(str(error)) from error
    _reject_floating_point_values(pack)
    _validate_identities(pack)
    fixture_root, fixtures = _validate_fixtures(pack, root)
    _validate_normalization(pack)
    oracle_paths: tuple[Path, ...] = ()
    oracle_sources: tuple[tuple[str, bytes], ...] = ()
    if pack["familyId"] == "user-settings":
        from .families.user_settings import compile_compatibility_expectations

        # The oracle is a central source dependency, never an adapter input fixture.
        try:
            oracle_path = (fixture_root / "expectations.json").resolve(strict=True)
            oracle_path.relative_to(fixture_root)
            oracle_bytes = oracle_path.read_bytes()
            oracle = json.loads(
                oracle_bytes,
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_nonfinite_json_number,
            )
            if any(fixture.resolved_path == oracle_path for fixture in fixtures):
                raise ValueError(
                    "User Settings oracle cannot be an adapter input fixture"
                )
            pack = compile_compatibility_expectations(pack, oracle)
            _reject_floating_point_values(pack)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise PackValidationError(
                f"invalid User Settings compatibility oracle: {error}"
            ) from error
        oracle_paths = (oracle_path,)
        oracle_sources = ((oracle_path.relative_to(root).as_posix(), oracle_bytes),)
    canonical = json.dumps(
        pack,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    expectation_digest = _expectation_digest(canonical, fixtures, oracle_sources)
    return ValidatedPack(
        repo_root=root,
        pack_path=resolved_pack,
        canonical_json=canonical,
        fixture_root=fixture_root,
        fixtures=fixtures,
        expectation_digest=expectation_digest,
        oracle_paths=oracle_paths,
    )
