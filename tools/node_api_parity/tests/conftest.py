"""Central pytest fixture/conftest for tools/node_api_parity/tests.

Sets sys.path once so test files can use clean imports:
    import generate_baseline
    import check_parity_gate

Mirrors ``tools/python_api_parity/tests/conftest.py`` to keep both parity
test suites on the same bootstrapping convention.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "node_api_parity"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
