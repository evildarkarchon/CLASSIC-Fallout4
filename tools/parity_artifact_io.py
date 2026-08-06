#!/usr/bin/env python3
"""Timestamp-stability helpers shared by the binding parity baseline tools.

Every parity generator stamps a wall-clock ``generated_at_utc`` into the JSON
payloads it writes, and the markdown renderers echo that value back out as a
``- Generated:`` header line. The baselines under
``docs/implementation/*_api_parity/baseline/`` are tracked by git, so a rerun
that finds no API change at all still rewrites those files with a fresh
timestamp and produces a diff whose only content is the clock.

That churn is invisible to the gates -- every comparator in this module (and the
per-tool copies it replaces) already treats the timestamp as noise -- but it is
very visible to reviewers, and it buries genuine API changes under no-op commits
in ``git log -p`` and ``git blame`` on the baselines.

:func:`preserve_baseline_generated_at` closes the gap. Before a write, it
re-reads the committed baseline and, when the regenerated payload is identical
apart from the timestamp, copies the committed timestamp forward. The subsequent
write is then byte-identical and git sees nothing. Preserving the JSON timestamp
also stabilizes the derived markdown for free, because the renderers read
``payload['generated_at_utc']`` rather than calling the clock themselves.

The timestamp is deliberately treated as an OPAQUE string throughout. The cxx
tools stamp second-granularity ``%Y-%m-%dT%H:%M:%SZ`` while the node and python
tools stamp microsecond ``datetime.now(UTC).isoformat()``; nothing here may
assume, parse, or normalize either format.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

#: Top-level JSON key carrying the generation timestamp.
GENERATED_AT_KEY = "generated_at_utc"

#: Markdown header-line prefix carrying the generation timestamp.
GENERATED_AT_MARKDOWN_PREFIX = "- Generated:"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with the stable formatting every parity artifact uses.

    ``indent=2``, insertion order preserved (``sort_keys=False``), and a
    trailing newline. Key order is meaningful here -- the generators build
    payloads in a deliberate order and the committed baselines record it, so
    sorting would rewrite every tracked file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def stable_id_hash(values: list[str]) -> str:
    """Return an order-independent SHA-256 over a list of contract IDs.

    Sorting before hashing is what makes the digest stable: callers pass IDs in
    whatever order they collected them, and the same set must always hash the
    same or the coverage summaries would churn.
    """
    joined = "\n".join(sorted(values))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def sync_baseline_artifacts(
    output_dir: Path,
    baseline_output_dir: Path,
    artifact_names: tuple[str, ...],
) -> None:
    """Copy generated artifacts into the checked-in baseline directory.

    Artifacts absent from ``output_dir`` are skipped rather than raising. Not
    every gate writes every tracked artifact on every path -- the cxx gate
    leaves ``cxx_gate_report.md`` to a later step -- and a refresh should not
    abort partway through on an artifact this run legitimately did not produce.
    The staleness check that follows is what reports a genuinely missing file.
    """
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    for name in artifact_names:
        src = output_dir / name
        if not src.exists():
            continue
        shutil.copyfile(src, baseline_output_dir / name)


def payloads_match_ignoring_generated_at(
    expected_payload: dict[str, Any], actual_payload: dict[str, Any]
) -> bool:
    """Return whether two JSON artifact payloads differ only by timestamp.

    Both payloads are shallow-copied before the key is dropped, so the caller's
    dictionaries are left untouched. A shallow copy is sufficient because
    ``generated_at_utc`` only ever appears at the top level.
    """
    expected = dict(expected_payload)
    actual = dict(actual_payload)
    expected.pop(GENERATED_AT_KEY, None)
    actual.pop(GENERATED_AT_KEY, None)
    return expected == actual


def markdown_matches_ignoring_generated_at(
    expected_text: str, actual_text: str
) -> bool:
    """Return whether two markdown artifacts differ only by their header timestamp."""
    expected_lines = [
        line
        for line in expected_text.splitlines()
        if not line.startswith(GENERATED_AT_MARKDOWN_PREFIX)
    ]
    actual_lines = [
        line
        for line in actual_text.splitlines()
        if not line.startswith(GENERATED_AT_MARKDOWN_PREFIX)
    ]
    return expected_lines == actual_lines


def artifacts_match(expected: Path, actual: Path) -> bool:
    """Return whether two artifact files match, ignoring generation timestamps.

    ``.json`` files are compared as parsed payloads with ``generated_at_utc``
    dropped; anything else is compared line-wise with ``- Generated:`` lines
    filtered out. A missing file on either side is reported as a mismatch.

    Raises ``json.JSONDecodeError`` if a ``.json`` artifact is unparseable --
    a corrupt tracked baseline is a real problem and should surface loudly
    rather than be silently reported as ordinary staleness.
    """
    if not expected.exists() or not actual.exists():
        return False
    if expected.suffix == ".json":
        expected_payload = json.loads(expected.read_text(encoding="utf-8"))
        actual_payload = json.loads(actual.read_text(encoding="utf-8"))
        return payloads_match_ignoring_generated_at(expected_payload, actual_payload)

    return markdown_matches_ignoring_generated_at(
        expected.read_text(encoding="utf-8"),
        actual.read_text(encoding="utf-8"),
    )


def preserve_baseline_generated_at(
    baseline_path: Path, generated_payload: dict[str, Any]
) -> None:
    """Reuse the committed baseline timestamp when regenerated content is unchanged.

    Mutates ``generated_payload`` in place, replacing its freshly stamped
    ``generated_at_utc`` with the one already committed at ``baseline_path``, but
    only when the two payloads are otherwise identical. When the content really
    did change, the fresh timestamp is left alone so the new baseline records
    when the change was actually observed.

    This is a pure write-stability optimization, never a correctness mechanism,
    so an absent, unreadable, or malformed baseline is treated as "nothing to
    preserve" rather than an error -- the caller still writes a valid artifact
    with its fresh timestamp, and the downstream staleness check reports the
    mismatch with an actionable message.
    """
    try:
        baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Missing, unreadable, or non-JSON baseline: fall through with the fresh
        # timestamp. ValueError covers json.JSONDecodeError, which subclasses it.
        return

    if not isinstance(baseline_payload, dict):
        return
    if not payloads_match_ignoring_generated_at(baseline_payload, generated_payload):
        return

    generated_at = baseline_payload.get(GENERATED_AT_KEY)
    if isinstance(generated_at, str):
        generated_payload[GENERATED_AT_KEY] = generated_at


def preserve_baseline_generated_at_all(
    baseline_dir: Path, payloads: dict[str, dict[str, Any]]
) -> None:
    """Apply :func:`preserve_baseline_generated_at` across a set of artifacts.

    ``payloads`` maps each artifact's file name within ``baseline_dir`` to the
    freshly generated payload that is about to be written for it. Each payload
    is mutated in place.
    """
    for name, payload in payloads.items():
        preserve_baseline_generated_at(baseline_dir / name, payload)
