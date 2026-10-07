"""Observe fixture-owned XSE log resolution through the Python binding."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

#: The only log files a fixture may create; the central validator freezes the same set.
_CONTROLLED_LOG_FILES = frozenset(
    {
        "configured-docs/F4SE/f4se.log",
        "configured-docs/F4SE/f4sevr.log",
        "local-docs/F4SE/f4se.log",
        "explicit-xse/f4se.log",
    }
)

#: Prefix of the Rust ``XseLogError::Inspect`` message the binding raises as ``OSError``.
_INSPECT_FAILURE = "cannot inspect XSE log "


def observe_xse_log(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Run ``resolve_xse_log_for_scan`` in an owned root and restore the cwd.

    Only the ``xse-folder.log`` capability is bound in Python. The resolver runs
    with the owned root as cwd so the relative fixture folders (and the
    registry's first-use load) resolve inside it; the returned log stays
    root-relative for cross-adapter comparison. Unrelated adapter exceptions
    propagate as execution failures.
    """
    import classic_xse

    if (
        set(fixture)
        != {
            "registryYaml",
            "game",
            "selectedVersion",
            "localYaml",
            "configuredDocs",
            "logFiles",
        }
        or fixture["game"] not in {"Fallout4", "Fallout4VR"}
        or not isinstance(fixture["logFiles"], list)
        or not set(fixture["logFiles"]) <= _CONTROLLED_LOG_FILES
    ):
        raise ValueError("unsupported XSE log fixture")
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(
        prefix="classic-xse-folder-conformance-"
    ) as directory:
        root = Path(directory)
        (root / "CLASSIC Main.yaml").write_bytes(fixture["registryYaml"].encode("utf-8"))
        if fixture["localYaml"] is not None:
            (root / f"CLASSIC {fixture['game']} Local.yaml").write_bytes(
                fixture["localYaml"].encode("utf-8")
            )
        for relative in fixture["logFiles"]:
            log = root / relative
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_bytes(b"")
        try:
            # A family has one dedicated serial runner; identical fixture bytes
            # seed the registry on first public access without consulting
            # installed metadata.
            os.chdir(root)
            try:
                located = classic_xse.resolve_xse_log_for_scan(
                    str(root),
                    fixture["game"],
                    fixture["selectedVersion"],
                    fixture["configuredDocs"] or None,
                )
            except OSError as error:
                # Only the typed operational failure is an observation.
                if not str(error).startswith(_INSPECT_FAILURE):
                    raise
                return {"log": None, "error": "inspect"}
            return {
                "log": None if located is None else located.replace("\\", "/"),
                "error": None,
            }
        finally:
            os.chdir(previous)
