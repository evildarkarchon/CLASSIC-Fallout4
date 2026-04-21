"""Focused regression tests for Phase 2 dead code removal."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _import_classic_scanlog():
    if "classic_scanlog" in sys.modules:
        return sys.modules["classic_scanlog"]

    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "python-bindings" / "classic-scanlog-py" / "Cargo.toml"
    subprocess.run(
        [
            "cargo",
            "build",
            "-p",
            "classic-scanlog-py",
            "--manifest-path",
            str(manifest_path),
        ],
        check=True,
        cwd=repo_root,
        env={
            **os.environ,
            "PYO3_PYTHON": str(
                repo_root / "python-bindings" / ".venv" / "Scripts" / "python.exe"
            ),
        },
    )

    target_dir = repo_root / "target" / "debug"
    deps_dir = target_dir / "deps"
    dll_path = target_dir / "classic_scanlog.dll"
    pyd_path = target_dir / "classic_scanlog.pyd"
    shutil.copyfile(dll_path, pyd_path)

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(target_dir))
        os.add_dll_directory(str(deps_dir))

    sys.path.insert(0, str(target_dir))
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
        / "classic-scanlog-py"
        / "src"
        / "gpu_detector.rs"
    ).read_text(encoding="utf-8")

    assert "pub struct PyGpuDetector;" in source
    assert "inner: GpuDetector" not in source
    assert "pub fn new() -> Self {\n        Self\n    }" in source
