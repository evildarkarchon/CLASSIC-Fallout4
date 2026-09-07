"""Frozen phase-one dispositions for class methods retaining their existing tests.

These selectors are migration ownership, never semantic evidence. Unknown new
operations remain in central coverage derivation and therefore fail closed.
"""

from __future__ import annotations

from ..coverage import SourceParityRow

# Only operations already present in the retained parity contracts belong here.
# Keep participant and class identity explicit: similarly named unrelated methods
# must never inherit a disposition from this phase-one migration.
_RETAINED = {
    ("file-operations", "classic-file-io-core", "FileIOCore", "python"): frozenset(
        {
            "append_file",
            "clear_cache",
            "file_exists",
            "get_file_info",
            "get_file_size",
            "py_read_multiple_files",
            "py_walk_directory",
            "py_write_multiple_files",
            "read_bytes",
            "read_dds_header",
            "read_dds_headers_batch",
            "read_file_mmap",
            "read_lines",
            "stream_lines",
            "stream_lines_sync",
            "write_bytes",
            "write_lines",
        }
    ),
    ("message-operations", "classic-message-core", "Message", "python"): frozenset(
        {
            "__init__",
            "set_content",
            "set_details",
            "set_msg_type",
            "set_target",
            "set_title",
            "with_title",
        }
    ),
    # PathHandler's current Python contract is an aggregate class carrier only;
    # normalize/join/batch are exercised, and no unexecuted method rows are exempt.
    ("path-normalization", "classic-shared-core", "PathHandler", "python"): frozenset(),
}


def is_retained_operation(family_id: str, row: SourceParityRow) -> bool:
    """Identify a previously known deferred method without granting runtime credit."""
    return (
        row.mapping_origin == "canonical_rust"
        and row.runtime_operation
        in _RETAINED.get(
            (family_id, row.rust_crate, row.rust_symbol, row.participant_id),
            frozenset(),
        )
    )
