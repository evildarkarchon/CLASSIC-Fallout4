"""Focused regression tests for Phase 2 dead code removal."""

from __future__ import annotations

import importlib
from pathlib import Path


def _import_classic_scanlog():
    """Import the installed facade; the one wheel must be rebuilt first.

    The former fallback built a private `classic-scanlog-py` extension;
    that crate is now a module of the one adapter wheel (#259), and a
    separately built image would not share its native state.
    """
    return importlib.import_module("classic_scanlog")


def test_gpu_detector_binding_is_stateless_and_repeatable() -> None:
    classic_scanlog = _import_classic_scanlog()

    detector_a = classic_scanlog.GpuDetector()
    detector_b = classic_scanlog.GpuDetector()
    segment = [
        "GPU #1: Nvidia GeForce RTX 4070",
        "GPU #2: Intel UHD Graphics",
    ]

    info_a = detector_a.extract_gpu_info(segment)
    info_b = detector_b.extract_gpu_info(segment)

    assert info_a.to_dict() == info_b.to_dict()
    assert info_a.manufacturer == "Nvidia"
    assert info_b.manufacturer == "Nvidia"
    assert info_a.rival == info_b.rival
    assert info_a.secondary == info_b.secondary


def test_gpu_detector_binding_source_stays_unit_struct() -> None:
    source = (
            Path(__file__).resolve().parents[1]
            / "classic-python-bindings"
            / "src"
            / "classic_scanlog"
            / "gpu_detector.rs"
    ).read_text(encoding="utf-8")

    assert "pub struct PyGpuDetector;" in source
    assert "inner: GpuDetector" not in source
    assert "pub fn new() -> Self {\n        Self\n    }" in source
