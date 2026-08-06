"""Regression guard: regenerating the CXX surface twice must not churn.

``rust_api_surface.json`` is the only cxx artifact that carries a timestamp --
the diff report has none, and both markdown renderers deliberately omit the
``- Generated:`` header (see ``render_diff_markdown``'s docstring). That single
file was still rewritten with a fresh ``generated_at_utc`` on every run, so an
unchanged bridge surface produced a tracked diff whose only content was the
clock.

Unlike the node and python generators, the cxx one preserves against
``--baseline-output-dir`` rather than its own output directory, so these tests
point both at the same scratch directory to stay hermetic.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATE_BASELINE = REPO_ROOT / "tools" / "cxx_api_parity" / "generate_baseline.py"
SURFACE_NAME = "rust_api_surface.json"

#: Deliberately not a valid timestamp, so a leak into real output is obvious.
SENTINEL_STAMP = "SENTINEL-MUST-NOT-BE-REUSED"


def run_generator(scratch_dir: Path) -> None:
    """Generate the surface, preserving against that same scratch directory."""
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATE_BASELINE),
            "--repo-root",
            str(REPO_ROOT),
            "--output-dir",
            str(scratch_dir),
            "--baseline-output-dir",
            str(scratch_dir),
        ],
        capture_output=True,
        text=True,
        # Asserted below instead, so a failure reports the generator's stderr.
        check=False,
    )
    assert result.returncode == 0, (
        f"generate_baseline.py failed ({result.returncode}):\n{result.stderr}"
    )


def test_rerun_produces_byte_identical_surface(tmp_path: Path) -> None:
    """Two consecutive runs must leave the surface byte-for-byte unchanged."""
    scratch = tmp_path / "baseline"

    run_generator(scratch)
    first = (scratch / SURFACE_NAME).read_bytes()

    run_generator(scratch)
    second = (scratch / SURFACE_NAME).read_bytes()

    assert first == second, (
        "Regenerating an unchanged bridge surface rewrote "
        f"{SURFACE_NAME}. A fresh generated_at_utc is the usual cause -- check "
        "that preserve_baseline_generated_at() still runs before the write."
    )


def test_changed_content_still_gets_a_fresh_timestamp(tmp_path: Path) -> None:
    """Preservation must decline when the bridge surface genuinely changed.

    The negative control for the test above: a stabilized timestamp is only
    correct while nothing else moved. Here the previous run's surface is
    doctored to look different, so the next run must reject its sentinel
    timestamp and stamp the current time instead.
    """
    scratch = tmp_path / "baseline"
    run_generator(scratch)

    surface_path = scratch / SURFACE_NAME
    doctored = json.loads(surface_path.read_text(encoding="utf-8"))
    doctored["generated_at_utc"] = SENTINEL_STAMP
    doctored["entries"].append(
        {
            "bridgeModule": "zzz_not_a_real_module",
            "kind": "fn",
            "rustSymbol": "fake_symbol",
        }
    )
    surface_path.write_text(json.dumps(doctored, indent=2) + "\n", encoding="utf-8")

    run_generator(scratch)

    refreshed = json.loads(surface_path.read_text(encoding="utf-8"))
    assert refreshed["generated_at_utc"] != SENTINEL_STAMP, (
        "The regenerated surface reused a timestamp from a payload it does not "
        "match; preservation is firing on changed content."
    )
