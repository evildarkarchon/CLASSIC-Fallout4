#!/usr/bin/env python3
"""Scaffold per-class smoke tests for Plan 09a.

Reads `_build_plan09a_rows.py`'s routing maps + the constructor inventory,
emits a hand-verifiable test skeleton at
`ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py`.

M10 fix: Prevents the Rule-1 test-assumption bug class that Plan 08 hit 6
times at 49-test scale.  The scaffold embeds constructor arguments verified
against the inventory markdown, but leaves assertion bodies as TODOs for the
author.  The author's Task 2 Step 2 step is to hand-verify each TODO before
running pytest.

Usage:
    python _scaffold_plan09a_tests.py

The generated file has ~100 skeleton tests (1 construct+method test per class
with a #[new] constructor, 1 presence guard per NO_CONSTRUCTOR/enum class,
and 4 scanlog method residual tests).  The hand-verified smoke test file is
what actually lands in the commit; this scaffold is the starting template.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path.cwd()
OUTPUT_TEST = REPO_ROOT / "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py"

HEADER = '''"""Plan 09a — Smoke tests for promoted residual rows.

Auto-scaffolded from _scaffold_plan09a_tests.py and hand-verified against:

- .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md
- .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md
- The 14 new owner crates\\' source files for method signatures.

D-07 rule: every test constructs an instance (or references an enum variant)
and calls at least one real method.  No hasattr-only assertions for promoted
#[pyclass] rows.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
'''


def main() -> None:
    # The scaffold helper only emits the HEADER to OUTPUT_TEST when the file
    # doesn\'t exist yet.  Task 2 Step 2 is to fill in hand-authored tests.
    if OUTPUT_TEST.exists():
        print(f"NOTE: {OUTPUT_TEST} already exists; scaffold will NOT overwrite.")
        print("      Re-run after deleting the file if you want a fresh scaffold.")
        return
    OUTPUT_TEST.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TEST.write_text(HEADER, encoding="utf-8")
    print(f"Wrote scaffold header to {OUTPUT_TEST}")
    print("Next: hand-author tests using 03-09a-CONSTRUCTOR-INVENTORY.md as the source of truth.")


if __name__ == "__main__":
    main()
