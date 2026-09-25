"""Narrow coverage of public text I/O results and isolated filesystem effects."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _files(value: object) -> bool:
    """Require a sorted, unique inventory of exact UTF-8 durable file contents."""
    return (
        isinstance(value, list)
        and all(
            isinstance(item, Mapping)
            and set(item) == {"path", "content"}
            and isinstance(item["path"], str)
            and bool(item["path"])
            and not item["path"].startswith("/")
            and ":" not in item["path"]
            and "\\" not in item["path"]
            and all(part not in {"", ".", ".."} for part in item["path"].split("/"))
            and isinstance(item["content"], str)
            for item in value
        )
        and [item["path"] for item in value] == sorted({item["path"] for item in value})
    )


def _observed(operation: str, outcome: str, observation: Mapping[str, Any]) -> bool:
    """Derive success, empty result and failure facts without reading fixture oracles."""
    if (
        set(observation)
        != (
            {"operation", "path", "content", "error", "beforeFiles", "files"}
            | ({"similarity"} if operation == "read-text" else set())
        )
        or observation["operation"] != operation
        or not _files(observation["beforeFiles"])
        or not _files(observation["files"])
        or not _files([{"path": observation["path"], "content": ""}])
    ):
        return False
    if operation == "read-text" and observation["similarity"] != [
        "1.000000",
        "0.000000",
        "0.500000",
    ]:
        return False
    path = observation["path"]
    before = {item["path"]: item["content"] for item in observation["beforeFiles"]}
    after = {item["path"]: item["content"] for item in observation["files"]}
    if outcome == "failure":
        return (
            observation["error"] == "io_error"
            and observation["content"] is None
            and before == after
            and path not in after
        )
    if observation["error"] is not None:
        return False
    if operation == "read-text":
        return (
            before == after
            and path in after
            and observation["content"] == after[path]
            and (bool(after[path]) if outcome == "nonempty" else after[path] == "")
        )
    return (
        observation["content"] is None
        and path in after
        and {key: value for key, value in before.items() if key != path}
        == {key: value for key, value in after.items() if key != path}
        and (
            (path not in before)
            if outcome == "created"
            else (path in before and before[path] != after[path])
        )
    )


FILE_OPERATIONS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "file-operations",
    tuple(
        CoveragePredicate(
            id=f"{operation}-{outcome}",
            capability_id=f"file-operations.{operation}",
            action=f"file-operations.{operation}",
            observation_family="file-effects",
            rust_symbols=(
                "FileIOCore",
                "read_file",
                "calculate_similarity",
                "similarity_ratio",
            )
            if operation == "read-text"
            else ("FileIOCore", "write_file"),
            matches=partial(_observed, operation, outcome),
            runtime_operations=(
                None,
                "__init__",
                "read_file",
                "readFile",
                "read_file_with_encoding",
                "read_report_file",
                "calculate_file_similarity",
                "read_bytes",
                "read_lines",
                "read_file_mmap",
                "stream_lines",
                "stream_lines_sync",
                "file_exists",
                "get_file_size",
                "get_file_info",
                "clear_cache",
                "py_read_multiple_files",
                "py_walk_directory",
            )
            if operation == "read-text"
            else (
                "write_file",
                "writeFile",
                "write_file_string",
                *(
                    ("write_bytes", "append_file", "py_write_multiple_files")
                    if outcome != "failure"
                    else ()
                ),
                *(("write_lines",) if outcome == "created" else ()),
            ),
        )
        for operation, outcomes in (
            ("read-text", ("nonempty", "empty", "failure")),
            ("write-text", ("created", "replaced", "failure")),
        )
        for outcome in outcomes
    )
    + (
        # The Python inventory maps stream wrappers to LogCollector. Explicit
        # selectors retain the unrelated collection/move operations as gaps.
        CoveragePredicate(
            id="read-stream-carriers",
            capability_id="file-operations.streams",
            action="file-operations.read-text",
            observation_family="file-effects",
            rust_symbols=("LogCollector",),
            matches=partial(_observed, "read-text", "nonempty"),
            binding_obligation_ids=(
                "parity:python:file_io.log_collection.PyLineStreamer",
                "parity:python:file_io.log_collection.PyLineStreamer.__aiter__",
                "parity:python:file_io.log_collection.PyLineStreamer.__anext__",
                "parity:python:file_io.log_collection.PySyncLineStreamer",
                "parity:python:file_io.log_collection.PySyncLineStreamer.__iter__",
                "parity:python:file_io.log_collection.PySyncLineStreamer.__next__",
            ),
            runtime_operations=(
                None,
                "PyLineStreamer.__aiter__",
                "PyLineStreamer.__anext__",
                "PySyncLineStreamer.__iter__",
                "PySyncLineStreamer.__next__",
            ),
        ),
    ),
)
