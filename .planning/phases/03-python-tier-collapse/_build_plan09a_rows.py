#!/usr/bin/env python3
"""Build Plan 09a residual promotion contract rows (multi-owner helper).

Plan 09a enrolls 14 new owner modules + 4 scanlog method residuals as
tier1-gated in one atomic plan. The helper generalizes the Plan 08 template
(_build_plan08_rows.py) to N owners with:

- C1 FIX: find_wrapper has THREE branches keyed on gap shape:
    (1) gap_type == 'rust_unmapped'  -> skip wrapper check (uses @rust proxy)
    (2) '.' in python_export_path    -> verify OUTER class wrapper exists
    (3) top-level python_unmapped    -> verify #[pyclass]/#[pyfunction] exists
- C2 FIX: contractIdsHash is computed via IMPORTED _stable_id_hash (full 64-char SHA-256)
- R3: EXCLUDED_OWNERS = {"file_io", "shared"} (Plan 08 owns these)
- R9: EXCLUDED_RUST_SYMBOLS = {"GLOBAL_FCX_HANDLER"} (LazyLock static; not tier1-promotable)
- Plan 08 same-row-dedup rule: already_covered_rust_symbols tracked across ALL owners
- Plan 08 @rust proxy pattern: rust-only symbols paired with nearest Python anchor class

Invocations:
    python _build_plan09a_rows.py              # Task 0 driver (inventory + projection)
    python _build_plan09a_rows.py --task 1     # Task 1 driver (row authoring)
    python _build_plan09a_rows.py --task 3     # Task 3 driver (registry selectors)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path.cwd()
PHASE_DIR = REPO_ROOT / ".planning/phases/03-python-tier-collapse"
DIFF_PATH = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_diff_report.json"
CONTRACT_PATH = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_contract.json"
PY_SURFACE_PATH = REPO_ROOT / "docs/implementation/python_api_parity/baseline/python_api_surface.json"
RUST_SURFACE_PATH = REPO_ROOT / "docs/implementation/python_api_parity/baseline/rust_api_surface.json"
REGISTRY_PATH = REPO_ROOT / "ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json"

# Import _stable_id_hash from live tooling (C2 fix — do NOT reimplement)
sys.path.insert(0, str(REPO_ROOT / "tools"))
from binding_parity_runtime_coverage import _stable_id_hash  # noqa: E402

EXCLUDED_OWNERS = {"file_io", "shared"}          # R3: Plan 08 owns these
EXCLUDED_RUST_SYMBOLS = {"GLOBAL_FCX_HANDLER"}   # R9: LazyLock static, not tier1-promotable

# Parser-garbage exclusions (pre-existing generate_baseline.py bug picks up Rust
# comment text when parsing `pub use ... {` blocks with inline comments; see
# classic-path-core/src/lib.rs L74-80).  These are NOT real Rust symbols.
PARSER_GARBAGE_RUST_SYMBOLS = {
    "// Boolean convenience wrappers drive_exists",
    "// Permission and accessibility checks is_valid_executable_path",
}

OWNER_TO_PY_MODULE = {
    "scangame": "classic_scangame",
    "path": "classic_path",
    "constants": "classic_constants",
    "message": "classic_message",
    "database": "classic_database",
    "resource": "classic_resource",
    "xse": "classic_xse",
    "settings": "classic_settings",
    "yaml": "classic_yaml",
    "registry": "classic_registry",
    "web": "classic_web",
    "version": "classic_version",
    "perf": "classic_perf",
    "update": "classic_update",
    "scanlog": "classic_scanlog",
}

OWNER_TO_RUST_CRATE = {
    "scangame": "classic-scangame-core",
    "path": "classic-path-core",
    "constants": "classic-constants-core",
    "message": "classic-message-core",
    "database": "classic-database-core",
    "resource": "classic-resource-core",
    "xse": "classic-xse-core",
    "settings": "classic-settings-core",
    "yaml": "classic-yaml-core",
    "registry": "classic-registry-core",
    "web": "classic-web-core",
    "version": "classic-version-core",
    "perf": "classic-perf-core",
    "update": "classic-update-core",
    "scanlog": "classic-scanlog-core",
}

OWNER_ORDER = [
    "scangame", "path", "constants", "message", "database", "resource",
    "xse", "settings", "yaml", "registry", "web", "version", "perf", "update",
]


# ============================================================================
# THREE-BRANCH WRAPPER CHECK (C1 FIX)
# ============================================================================

def find_wrapper(owner: str, residual: dict) -> tuple[bool, str]:
    """Three-branch wrapper check keyed on gap shape.

    BRANCH 1: rust_unmapped -> skip wrapper check (uses @rust proxy)
    BRANCH 2: python_unmapped with '.' in export path -> verify OUTER class wrapper
    BRANCH 3: python_unmapped with no dot -> verify top-level #[pyclass]/#[pyfunction]

    Returns (found, reason).
    """
    gap_type = residual.get("gap_type")
    owner_dir = REPO_ROOT / f"ClassicLib-rs/python-bindings/classic-{owner.replace('_', '-')}-py/src"
    if not owner_dir.exists():
        return (False, "no_py_crate_dir")

    # BRANCH 1: rust_unmapped -> skip wrapper check entirely (uses @rust proxy)
    if gap_type == "rust_unmapped":
        rs = residual.get("rust_symbol") or ""
        if rs in PARSER_GARBAGE_RUST_SYMBOLS:
            return (False, "parser_garbage_excluded")
        return (True, "rust_unmapped_uses_rust_proxy")

    py_export_path = residual.get("python_export_path") or ""

    # BRANCH 2: method residual (has dot in export path) -> verify class wrapper
    if "." in py_export_path:
        class_name = py_export_path.split(".")[0]
        candidates = [
            f'name = "{class_name}"',
            f"pub struct Py{class_name}",
            f"pub struct {class_name}",
            f"pub enum Py{class_name}",
            f"pub enum {class_name}",
        ]
        for rs in owner_dir.rglob("*.rs"):
            text = rs.read_text(encoding="utf-8", errors="ignore")
            if any(c in text for c in candidates):
                return (True, f"class_wrapper_found:{rs.name}")
        return (False, f"class_wrapper_not_found:{class_name}")

    # BRANCH 3: top-level residual (class or function) -> bare-name search
    top_level = py_export_path or residual.get("python_export") or residual.get("rust_symbol") or ""
    top_level_bare = top_level.split(".")[-1]
    candidates_sym = [
        f'name = "{top_level_bare}"',
        f"pub struct Py{top_level_bare}",
        f"pub struct {top_level_bare}",
        f"pub enum Py{top_level_bare}",
        f"pub enum {top_level_bare}",
    ]
    for rs_file in owner_dir.rglob("*.rs"):
        text = rs_file.read_text(encoding="utf-8", errors="ignore")
        if any(c in text for c in candidates_sym):
            return (True, f"top_level_wrapper_found:{rs_file.name}")
        # Function fallback: #[pyfunction] followed by fn <bare>
        if "#[pyfunction]" in text and f"fn {top_level_bare}" in text:
            return (True, f"top_level_fn_found:{rs_file.name}")

    # BRANCH 3b: .pyi stub-only class (TypedDict / Protocol / plain class)
    # Some owner modules expose type-hint-only classes via the .pyi stub whose
    # runtime identity is a plain dict/callable — see SettingsCacheStats and
    # YamlCacheStats which are `class X(TypedDict):` in classic_settings.pyi /
    # classic_yaml.pyi and do not correspond to any #[pyclass].  These are
    # legitimate surface exports recorded by the python parser at
    # classic-*-py/classic_*.pyi; treat the stub declaration itself as the
    # "wrapper" because the contract row points at the stub file, not a Rust
    # type.
    pyi_dir = owner_dir.parent  # one level up from src/ to the crate root
    for pyi_file in pyi_dir.glob("*.pyi"):
        text = pyi_file.read_text(encoding="utf-8", errors="ignore")
        # Match `class SettingsCacheStats(TypedDict):` or `class X(Protocol):`
        if re.search(rf"^class\s+{re.escape(top_level_bare)}\s*[\(:]", text, re.MULTILINE):
            return (True, f"pyi_stub_class_found:{pyi_file.name}")

    return (False, f"top_level_wrapper_not_found:{top_level_bare}")


# ============================================================================
# RESIDUAL LOADING
# ============================================================================

def load_residuals() -> list[dict]:
    diff = json.loads(DIFF_PATH.read_text(encoding="utf-8"))
    return [
        g for g in diff["gaps"]
        if g["tier"] == "tier2"
        and g["owner_module"] not in EXCLUDED_OWNERS
        and not (g["gap_type"] == "rust_unmapped" and g.get("rust_symbol") in EXCLUDED_RUST_SYMBOLS)
    ]


def classify_residuals(residuals: list[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
    """Partition residuals into {owner: [residuals]} inventory and blockers list."""
    inventory: dict[str, list[dict]] = defaultdict(list)
    blockers: list[dict] = []
    for r in residuals:
        owner = r["owner_module"]
        found, reason = find_wrapper(owner, r)
        if found:
            rc = dict(r)
            rc["_wrapper_reason"] = reason
            inventory[owner].append(rc)
        else:
            # Parser garbage isn't a real blocker — filter silently
            if reason == "parser_garbage_excluded":
                continue
            blockers.append({**r, "_block_reason": reason})
    return dict(inventory), blockers


def write_blockers(blockers: list[dict]) -> Path:
    out = PHASE_DIR / "03-09a-BLOCKERS.md"
    lines = [
        "# Plan 09a — Wrapper-less Residual Blockers",
        "",
        f"**{len(blockers)} residuals have no resolvable wrapper after the three-branch check.**",
        "",
        "## Blockers grouped by owner",
        "",
    ]
    by_owner: dict[str, list[dict]] = defaultdict(list)
    for b in blockers:
        by_owner[b["owner_module"]].append(b)
    for owner in sorted(by_owner):
        lines.append(f"### {owner} ({len(by_owner[owner])} residuals)")
        lines.append("")
        for b in by_owner[owner]:
            sym = b.get("rust_symbol") or b.get("python_export_path") or b.get("python_export") or "?"
            lines.append(f"- `{sym}` ({b['gap_type']}, kind={b.get('kind','?')}, reason={b['_block_reason']})")
        lines.append("")
    lines.extend([
        "## Remediation options",
        "",
        "1. **Add the missing -py wrapper manually** in the owner's src/ tree, then re-run Plan 09a Task 0.",
        "2. **Add the symbol to EXCLUDED_RUST_SYMBOLS** in _build_plan09a_rows.py IF genuinely internal; MUST cite a STATE.md / CONTEXT.md decision.",
        "3. **Split a wrapper-authoring subtask** into a new plan before Plan 09a resumes.",
        "",
        "Plan 09a will NOT proceed to Task 1 until either this file is empty OR every blocker is resolved.",
    ])
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_inventory(inventory: dict[str, list[dict]]) -> Path:
    out = PHASE_DIR / "03-09a-RESIDUAL-INVENTORY.md"
    total = sum(len(v) for v in inventory.values())
    lines = [
        "# Plan 09a — Residual Promotion Inventory",
        "",
        "**Source:** `parity_diff_report.json::gaps` after Task 0 Step 1 baseline refresh",
        f"**Total residuals:** {total} (after R9 GLOBAL_FCX_HANDLER exclusion + R3 file_io/shared exclusion + parser-garbage filter)",
        f"**Owners:** {len(inventory)}",
        "",
        "## Per-owner counts",
        "",
    ]
    for owner in sorted(inventory):
        lines.append(f"- `{owner}` — {len(inventory[owner])} residuals")
    lines.extend(["", "## Per-owner residual lists", ""])
    for owner in sorted(inventory):
        lines.append(f"### {owner} ({len(inventory[owner])})")
        lines.append("")
        for r in inventory[owner]:
            sym = r.get("rust_symbol") or r.get("python_export_path") or r.get("python_export") or "?"
            gt = r.get("gap_type", "?")
            kind = r.get("kind", "?")
            reason = r.get("_wrapper_reason", "?")
            lines.append(f"- `{sym}` ({gt}, kind={kind}, wrapper={reason})")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ============================================================================
# TASK 0 DRIVER
# ============================================================================

def main_task0() -> int:
    residuals = load_residuals()
    print(f"Loaded {len(residuals)} residuals from live parity_diff_report.json::gaps")

    inventory, blockers = classify_residuals(residuals)
    if blockers:
        out = write_blockers(blockers)
        print(f"BLOCKED: wrote {out} with {len(blockers)} blockers. Stopping.")
        return 1

    out = write_inventory(inventory)
    total = sum(len(v) for v in inventory.values())
    print(f"OK: wrote {out} with {total} residuals across {len(inventory)} owners.")
    return 0


# ============================================================================
# TASK 1 DRIVER (stub — implemented in Task 1 step)
# ============================================================================

def main_task1() -> int:
    print("Task 1 driver not yet implemented in this scaffold; see Task 1 step.")
    return 1


# ============================================================================
# TASK 3 DRIVER (stub — implemented in Task 3 step)
# ============================================================================

def main_task3() -> int:
    print("Task 3 driver not yet implemented in this scaffold; see Task 3 step.")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=int, default=0, help="Which task driver to run (0/1/3)")
    args = parser.parse_args()
    if args.task == 0:
        sys.exit(main_task0())
    elif args.task == 1:
        sys.exit(main_task1())
    elif args.task == 3:
        sys.exit(main_task3())
    else:
        print(f"Unknown task: {args.task}", file=sys.stderr)
        sys.exit(1)
