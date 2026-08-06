"""Regression guard: regenerating the Python baseline twice must not churn.

``generate_baseline.py`` defaults ``--output-dir`` to the tracked baseline
directory, so every artifact it writes lands directly in git. Before
``preserve_baseline_generated_at_all`` was wired in, each rerun stamped a fresh
``generated_at_utc`` and re-rendered the ``- Generated:`` markdown headers from
it, producing a commit-sized diff whose only content was the clock.

The gate never caught this because its comparator ignores the timestamp on both
sides -- and its own partial preservation covered only the two report payloads,
leaving both surface manifests to churn on every run. These tests assert the
stronger property the baselines actually need: two runs against unchanged
sources produce byte-identical files, timestamp included.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATE_BASELINE = REPO_ROOT / "tools" / "python_api_parity" / "generate_baseline.py"

#: Deliberately not a valid timestamp, so a leak into real output is obvious.
SENTINEL_STAMP = "SENTINEL-MUST-NOT-BE-REUSED"


def run_generator(output_dir: Path) -> None:
    """Invoke the baseline generator, writing every artifact to ``output_dir``."""
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATE_BASELINE),
            "--repo-root",
            str(REPO_ROOT),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        # Asserted below instead, so a failure reports the generator's stderr.
        check=False,
    )
    assert result.returncode == 0, (
        f"generate_baseline.py failed ({result.returncode}):\n{result.stderr}"
    )


def digest_dir(directory: Path) -> dict[str, str]:
    """Map each generated file name to a SHA-256 digest of its exact bytes."""
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def test_rerun_produces_byte_identical_artifacts(tmp_path: Path) -> None:
    """Two consecutive runs must leave every artifact byte-for-byte unchanged."""
    output_dir = tmp_path / "baseline"

    run_generator(output_dir)
    first = digest_dir(output_dir)
    assert first, "generator produced no artifacts"

    run_generator(output_dir)
    second = digest_dir(output_dir)

    churned = sorted(name for name in first if first[name] != second.get(name))
    assert not churned, (
        "Regenerating unchanged sources rewrote these artifacts: "
        f"{', '.join(churned)}. A fresh generated_at_utc is the usual cause -- "
        "check that preserve_baseline_generated_at_all() covers every payload."
    )


def test_changed_content_still_gets_a_fresh_timestamp(tmp_path: Path) -> None:
    """Preservation must decline when the surface genuinely changed.

    The negative control for the test above: a stabilized timestamp is only
    correct while nothing else moved. Here the previous run's surface is
    doctored to look different, so the next run must reject its sentinel
    timestamp and stamp the current time instead -- otherwise the baseline
    would permanently record when the file was *first* generated rather than
    when the API last changed.
    """
    output_dir = tmp_path / "baseline"
    run_generator(output_dir)

    surface_path = output_dir / "rust_api_surface.json"
    doctored = json.loads(surface_path.read_text(encoding="utf-8"))
    doctored["generated_at_utc"] = SENTINEL_STAMP
    # An extra top-level key is enough to make the payloads differ, and stays
    # correct if the surface schema's own field names ever change.
    doctored["__injected_drift__"] = True
    surface_path.write_text(json.dumps(doctored, indent=2) + "\n", encoding="utf-8")

    run_generator(output_dir)

    refreshed = json.loads(surface_path.read_text(encoding="utf-8"))
    assert refreshed["generated_at_utc"] != SENTINEL_STAMP, (
        "The regenerated surface reused a timestamp from a payload it does not "
        "match; preservation is firing on changed content."
    )
