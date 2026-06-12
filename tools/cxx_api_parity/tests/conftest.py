"""Shared pytest fixtures for the CXX parity gate tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Absolute path to the repo root (parents[3] from this file)."""
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def fixture_dir() -> Path:
    """Absolute path to tools/cxx_api_parity/tests/fixtures/."""
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fake_build_rs_text() -> str:
    """Synthetic build.rs text referencing the 5 fixture files."""
    return (
        '#[cfg(windows)]\n'
        'fn main() {\n'
        '    cxx_build::bridges([\n'
        '        "src/simple.rs",\n'
        '        "src/struct_ffi.rs",\n'
        '        "src/enum_ffi.rs",\n'
        '        "src/opaque_ffi.rs",\n'
        '        "src/mixed_ffi.rs",\n'
        '    ])\n'
        '    .include("include")\n'
        '    .std("c++17")\n'
        '    .compile("fake-bridge");\n'
        '}\n'
        '\n'
        '#[cfg(not(windows))]\n'
        'fn main() {}\n'
    )
