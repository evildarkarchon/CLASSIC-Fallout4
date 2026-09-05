"""Type-aware exact comparison for normalized conformance observations."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

_JSON_PATH_TOKEN = re.compile(
    r"(?:\.([A-Za-z_][A-Za-z0-9_-]*))|(?:\[(0|[1-9][0-9]*)\])"
)
_MISSING = object()


class NormalizationError(ValueError):
    """Raised when declared normalization cannot project an observation."""

    def __init__(self, message: str, path: str) -> None:
        """Create one path-attributed normalization diagnostic."""

        super().__init__(message)
        self.path = path


@dataclass(frozen=True)
class ObservationDifference:
    """Describe one stable path where an actual observation differs."""

    path: str
    kind: str


def _path_tokens(path: str) -> tuple[str | int, ...]:
    """Parse one already-validated exact JSONPath into traversal tokens."""

    tokens: list[str | int] = []
    position = 1
    for match in _JSON_PATH_TOKEN.finditer(path, 1):
        if match.start() != position:
            raise NormalizationError("normalization path is invalid", path)
        field, index = match.groups()
        tokens.append(field if field is not None else int(index))
        position = match.end()
    if position != len(path) or not tokens:
        raise NormalizationError("normalization path is invalid", path)
    return tuple(tokens)


def _resolve(value: object, tokens: tuple[str | int, ...], path: str) -> object:
    """Resolve one exact path, returning a sentinel when a member is absent."""

    current = value
    for token in tokens:
        if isinstance(token, str):
            if not isinstance(current, Mapping):
                raise NormalizationError(
                    "normalization field traverses a non-object value", path
                )
            if token not in current:
                return _MISSING
            current = current[token]
        else:
            if not isinstance(current, list):
                raise NormalizationError(
                    "normalization index traverses a non-array value", path
                )
            if token >= len(current):
                return _MISSING
            current = current[token]
    return current


def _remove(value: object, tokens: tuple[str | int, ...], path: str) -> None:
    """Remove one exact declared member when it is present."""

    parent = _resolve(value, tokens[:-1], path) if len(tokens) > 1 else value
    if parent is _MISSING:
        return
    final = next(reversed(tokens))
    if isinstance(final, str):
        if not isinstance(parent, dict):
            raise NormalizationError(
                "normalization exclusion targets a field on a non-object", path
            )
        parent.pop(final, None)
        return
    if not isinstance(parent, list):
        raise NormalizationError(
            "normalization exclusion targets an index on a non-array", path
        )
    if final < len(parent):
        parent.pop(final)


def _exclusion_order(path: str) -> tuple[int, tuple[tuple[str, object], ...]]:
    """Order deep paths and larger array indices first to avoid index drift."""

    tokens = _path_tokens(path)
    comparable = tuple(
        ("field", token) if isinstance(token, str) else ("index", token)
        for token in tokens
    )
    return len(tokens), comparable


def _canonical_sort_key(value: object) -> bytes:
    """Return the schema-defined stable key for one unordered JSON value."""

    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _fixture_relative_path(value: str, fixture_root: Path, path: str) -> str:
    """Project one declared path beneath the fixture root to canonical POSIX form."""

    windows_value = PureWindowsPath(value)
    if windows_value.is_absolute():
        windows_root = PureWindowsPath(str(fixture_root))
        try:
            relative = windows_value.relative_to(windows_root)
        except ValueError as error:
            raise NormalizationError(
                "declared absolute path is outside the prepared fixture root", path
            ) from error
        result = PurePosixPath(*relative.parts)
    else:
        posix_value = PurePosixPath(value)
        if posix_value.is_absolute():
            posix_root = PurePosixPath(fixture_root.as_posix())
            try:
                result = posix_value.relative_to(posix_root)
            except ValueError as error:
                raise NormalizationError(
                    "declared absolute path is outside the prepared fixture root", path
                ) from error
        else:
            normalized = value.replace("\\", "/")
            parts = normalized.split("/")
            if any(part in {"", ".", ".."} for part in parts):
                raise NormalizationError(
                    "declared fixture path must remain beneath the fixture root", path
                )
            return normalized
    if not result.parts or any(part in {"", ".", ".."} for part in result.parts):
        raise NormalizationError(
            "declared fixture path must remain beneath the fixture root", path
        )
    return result.as_posix()


def _normalize_fixture_paths(
    expected: object,
    actual: object,
    fixture_root: Path,
    path: str = "$",
    field_name: str | None = None,
) -> tuple[object, object]:
    """Normalize paired values only at schema-owned ``path`` carrier fields."""

    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) & set(actual)):
            expected[key], actual[key] = _normalize_fixture_paths(
                expected[key],
                actual[key],
                fixture_root,
                _field_path(path, str(key)),
                str(key),
            )
        return expected, actual
    if isinstance(expected, list) and isinstance(actual, list):
        for index in range(min(len(expected), len(actual))):
            expected[index], actual[index] = _normalize_fixture_paths(
                expected[index],
                actual[index],
                fixture_root,
                f"{path}[{index}]",
                field_name,
            )
        return expected, actual
    # The common durable-effect and Display Content schemas reserve ``path`` for
    # path payloads; every other scalar remains exact domain data.
    if (
        field_name == "path"
        and isinstance(expected, str)
        and isinstance(actual, str)
        and (
            PurePosixPath(actual).is_absolute()
            or PureWindowsPath(actual).is_absolute()
            or "\\" in actual
        )
    ):
        return expected, _fixture_relative_path(actual, fixture_root, path)
    return expected, actual


def _remove_optional_empty_file(value: object, path: str, relative_path: str) -> None:
    """Remove at most one declared empty file after validating the checkpoint evidence.

    Unlike an exclusion, this permits only absence or the exact empty regular-file
    carrier; malformed trees and changed file contents remain normalization errors.
    """
    tree = _resolve(value, _path_tokens(path), path)
    if not isinstance(tree, list):
        raise NormalizationError(
            "optional empty file requires a present tree array", path
        )
    matching = []
    for index, entry in enumerate(tree):
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), dict)
            or set(entry["path"]) != {"path"}
            or not isinstance(entry["path"]["path"], str)
            or entry.get("kind") not in ("file", "directory")
        ):
            raise NormalizationError(
                "optional empty file checkpoint has a malformed path carrier", path
            )
        if entry["path"]["path"] == relative_path:
            matching.append(index)
            if entry != {
                "path": {"path": relative_path},
                "kind": "file",
                "bytesHex": "",
            }:
                raise NormalizationError(
                    "optional empty file must be an exact empty regular file", path
                )
    if len(matching) > 1:
        raise NormalizationError(
            "optional empty file checkpoint contains duplicate entries", path
        )
    if matching:
        tree.pop(matching[0])


def normalize_observations(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    normalization: Mapping[str, Any],
    *,
    fixture_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply declared root-path, optional-empty-file, exclusion, and unordered rules."""

    normalized_expected = copy.deepcopy(dict(expected))
    normalized_actual = copy.deepcopy(dict(actual))
    if normalization["rootRelativePaths"]:
        normalized_expected, normalized_actual = _normalize_fixture_paths(
            normalized_expected,
            normalized_actual,
            fixture_root,
        )
        if not isinstance(normalized_expected, dict) or not isinstance(
            normalized_actual, dict
        ):  # pragma: no cover - mapping inputs preserve this invariant
            raise NormalizationError("normalized observations must be objects", "$")
    # Validate optional evidence before broader declared transforms can hide a malformed file.
    for declaration in normalization.get("optionalEmptyFiles", []):
        for observation in (normalized_expected, normalized_actual):
            _remove_optional_empty_file(
                observation, declaration["path"], declaration["relativePath"]
            )
    excluded_paths = [entry["path"] for entry in normalization["excludedPaths"]]
    for path in sorted(excluded_paths, key=_exclusion_order, reverse=True):
        tokens = _path_tokens(path)
        _remove(normalized_expected, tokens, path)
        _remove(normalized_actual, tokens, path)

    for path in normalization["unorderedPaths"]:
        tokens = _path_tokens(path)
        expected_value = _resolve(normalized_expected, tokens, path)
        actual_value = _resolve(normalized_actual, tokens, path)
        for label, value in (("expected", expected_value), ("actual", actual_value)):
            if value is _MISSING:
                continue
            if not isinstance(value, list):
                raise NormalizationError(
                    f"declared unordered path resolves to a non-array {label} value",
                    path,
                )
            value.sort(key=_canonical_sort_key)
    return normalized_expected, normalized_actual


def _validate_display_segment(segment: object, path: str) -> None:
    """Validate one frozen kind/text/path/count display carrier."""

    if not isinstance(segment, Mapping) or set(segment) != {
        "kind",
        "text",
        "path",
        "count",
    }:
        raise NormalizationError(
            "display segment must contain exactly kind, text, path, and count",
            path,
        )
    kind = segment["kind"]
    text = segment["text"]
    segment_path = segment["path"]
    count = segment["count"]
    if not isinstance(kind, str) or kind not in {
        "text",
        "label",
        "count",
        "path",
        "name",
        "emphasis",
    }:
        raise NormalizationError("display segment kind is unsupported", f"{path}.kind")
    if not isinstance(text, str):
        raise NormalizationError(
            "display segment text must be a string", f"{path}.text"
        )
    if not isinstance(segment_path, str):
        raise NormalizationError(
            "display segment path must be a string", f"{path}.path"
        )
    if type(count) is not int or count < 0:
        raise NormalizationError(
            "display segment count must be a non-negative integer", f"{path}.count"
        )
    if kind == "path":
        relative = PurePosixPath(segment_path)
        if (
            not segment_path
            or text
            or count != 0
            or "\\" in segment_path
            or relative.is_absolute()
            or PureWindowsPath(segment_path).is_absolute()
            or any(part in {".", ".."} for part in relative.parts)
        ):
            raise NormalizationError(
                "path display segment must use only its canonical relative path payload",
                path,
            )
    elif kind == "count":
        if not text or segment_path:
            raise NormalizationError(
                "count display segment must use only its text and count payloads", path
            )
    elif not text or segment_path or count != 0:
        raise NormalizationError(
            "textual display segment must use only its text payload", path
        )


def _validate_display_line(line: object, path: str) -> None:
    """Validate one severity plus ordered-segment display carrier."""

    if not isinstance(line, Mapping) or set(line) != {"severity", "segments"}:
        raise NormalizationError(
            "display line must contain exactly severity and segments", path
        )
    severity = line["severity"]
    if not isinstance(severity, str) or severity not in {
        "info",
        "notice",
        "warning",
        "failure",
        "success",
    }:
        raise NormalizationError(
            "display line severity is unsupported", f"{path}.severity"
        )
    segments = line["segments"]
    if not isinstance(segments, list):
        raise NormalizationError(
            "display line segments must be an ordered array", f"{path}.segments"
        )
    for index, segment in enumerate(segments):
        _validate_display_segment(segment, f"{path}.segments[{index}]")


def validate_display_content_carriers(
    expected: object,
    actual: object,
    path: str = "$",
    *,
    display_context: bool = False,
) -> None:
    """Validate actual display carriers at locations established by the oracle.

    The frozen ``segments`` member or explicit ``displayContent`` container marks
    a carrier candidate. The container context catches lines missing ``segments``
    while a domain record elsewhere may independently use ``severity``.
    """

    if display_context:
        if isinstance(expected, list):
            if not isinstance(actual, list):
                raise NormalizationError(
                    "display content must be an ordered array of line objects", path
                )
            for index, line in enumerate(expected):
                _validate_display_line(line, f"{path}[{index}]")
            for index, line in enumerate(actual):
                _validate_display_line(line, f"{path}[{index}]")
        else:
            _validate_display_line(expected, path)
            _validate_display_line(actual, path)
        return
    if isinstance(expected, Mapping):
        if "segments" in expected:
            _validate_display_line(expected, path)
            _validate_display_line(actual, path)
            return
        if not isinstance(actual, Mapping):
            return
        for key in sorted(set(expected) & set(actual)):
            validate_display_content_carriers(
                expected[key],
                actual[key],
                _field_path(path, str(key)),
                display_context=display_context or key == "displayContent",
            )
        return
    if isinstance(expected, list) and isinstance(actual, list):
        for index in range(min(len(expected), len(actual))):
            validate_display_content_carriers(
                expected[index],
                actual[index],
                f"{path}[{index}]",
                display_context=display_context,
            )


def _field_path(parent: str, field: str) -> str:
    """Append one object field using the contract's exact JSONPath spelling."""

    return f"{parent}.{field}"


def exact_differences(
    expected: object, actual: object, path: str = "$"
) -> tuple[ObservationDifference, ...]:
    """Return every exact structural difference in deterministic path order.

    Python considers booleans and integers equal, so scalar types are compared
    before values to preserve the cross-language JSON contract.
    """

    if type(expected) is not type(actual):
        return (ObservationDifference(path, "type_mismatch"),)
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        differences: list[ObservationDifference] = []
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            differences.append(
                ObservationDifference(_field_path(path, str(key)), "missing_field")
            )
        for key in sorted(actual_keys - expected_keys):
            differences.append(
                ObservationDifference(_field_path(path, str(key)), "extra_field")
            )
        for key in sorted(expected_keys & actual_keys):
            differences.extend(
                exact_differences(
                    expected[key], actual[key], _field_path(path, str(key))
                )
            )
        return tuple(differences)
    if isinstance(expected, list) and isinstance(actual, list):
        differences = []
        shared_length = min(len(expected), len(actual))
        for index in range(shared_length):
            differences.extend(
                exact_differences(expected[index], actual[index], f"{path}[{index}]")
            )
        for index in range(shared_length, len(expected)):
            differences.append(
                ObservationDifference(f"{path}[{index}]", "missing_element")
            )
        for index in range(shared_length, len(actual)):
            differences.append(
                ObservationDifference(f"{path}[{index}]", "extra_element")
            )
        return tuple(differences)
    if expected != actual:
        return (ObservationDifference(path, "value_mismatch"),)
    return ()
