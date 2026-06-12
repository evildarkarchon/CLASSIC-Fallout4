"""Central pytest fixture/conftest for tools/python_api_parity/tests.

Sets sys.path once so test files can use clean imports:
    from generate_baseline import RUST_TARGET_CRATES
    from check_parity_gate import validate_contract_rust_symbols

This replaces per-file sys.path.insert pollution that would conflict
with package-style imports elsewhere in the repo.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "python_api_parity"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
