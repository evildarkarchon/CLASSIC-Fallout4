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
# TASK 1 — PY CLASS / FUNCTION INDEX BUILDERS
# ============================================================================

# Regex helpers
PYCLASS_ATTR_RE = re.compile(r'#\[pyclass(?:\s*\([^)]*\))?\]')
NAME_ATTR_RE = re.compile(r'name\s*=\s*"([^"]+)"')
STRUCT_OR_ENUM_RE = re.compile(r'pub\s+(struct|enum)\s+(\w+)')
PYFUNCTION_ATTR_RE = re.compile(r'#\[pyfunction[^\]]*\]\s*(?:pub\s+)?fn\s+(\w+)')


def build_py_class_index(owner: str) -> dict[str, tuple[str, str, str]]:
    """Walk classic-<owner>-py/src/*.rs for #[pyclass] declarations.

    Returns {py_class_name: (submodule, rust_struct_name, rel_file)}.
    submodule = source file stem (e.g. "ba2" for ba2.rs, "lib" for lib.rs).
    """
    owner_dir = REPO_ROOT / f"ClassicLib-rs/python-bindings/classic-{owner.replace('_', '-')}-py/src"
    if not owner_dir.exists():
        return {}
    idx: dict[str, tuple[str, str, str]] = {}
    for rs_file in sorted(owner_dir.rglob("*.rs")):
        text = rs_file.read_text(encoding="utf-8", errors="ignore")
        # Find every #[pyclass(...)] attribute followed (after some attrs) by a struct/enum
        # Scan line-by-line, accumulating attribute span then the next struct/enum.
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            if "#[pyclass" in lines[i]:
                attr_block = []
                j = i
                while j < len(lines):
                    attr_block.append(lines[j])
                    # Capture continuation: keep reading until we hit the struct/enum
                    if STRUCT_OR_ENUM_RE.search(lines[j]):
                        break
                    j += 1
                    # Safety bound
                    if j - i > 20:
                        break
                attr_text = "\n".join(attr_block)
                name_m = NAME_ATTR_RE.search(attr_text)
                struct_m = STRUCT_OR_ENUM_RE.search(attr_text)
                if struct_m:
                    rust_struct_name = struct_m.group(2)
                    py_name = name_m.group(1) if name_m else rust_struct_name
                    submodule = rs_file.stem
                    rel_file = str(rs_file.relative_to(REPO_ROOT)).replace("\\", "/")
                    if py_name not in idx:
                        idx[py_name] = (submodule, rust_struct_name, rel_file)
                i = j + 1
            else:
                i += 1
    return idx


def build_py_function_index(owner: str) -> dict[str, tuple[str, str, str]]:
    """Walk classic-<owner>-py/src/*.rs for #[pyfunction] declarations.

    Returns {py_function_name: (submodule, rust_function_name, rel_file)}.
    The "rust_function_name" is the `fn <name>` identifier; PyO3 may rename via
    #[pyo3(name = "…")] attr but for simplicity we assume the bare fn name is
    also the Python name (matches repo convention except in a few renamed cases
    like database's py_get_default_cache_ttl -> get_default_cache_ttl).
    """
    owner_dir = REPO_ROOT / f"ClassicLib-rs/python-bindings/classic-{owner.replace('_', '-')}-py/src"
    if not owner_dir.exists():
        return {}
    idx: dict[str, tuple[str, str, str]] = {}
    for rs_file in sorted(owner_dir.rglob("*.rs")):
        text = rs_file.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'#\[pyfunction[^\]]*\](?:\s*#\[[^\]]*\])*\s*(?:pub\s+)?fn\s+(\w+)', text):
            fn_name = m.group(1)
            # If there is an inline pyo3 rename, use it
            attr_start = text.rfind("#[pyfunction", 0, m.start() + 1)
            attr_slice = text[attr_start:m.start() + 20]
            rename = re.search(r'#\[pyo3\(name\s*=\s*"([^"]+)"\)\]', attr_slice)
            py_name = rename.group(1) if rename else fn_name
            submodule = rs_file.stem
            rel_file = str(rs_file.relative_to(REPO_ROOT)).replace("\\", "/")
            if py_name not in idx:
                idx[py_name] = (submodule, fn_name, rel_file)
    return idx


def build_rust_symbol_set(owner: str) -> set[str]:
    """Return the set of real Rust symbols declared in the owner's core crate."""
    rust_surface = json.loads(RUST_SURFACE_PATH.read_text(encoding="utf-8"))
    return {
        s["symbol"]
        for s in rust_surface["symbols"]
        if s.get("owner_module") == owner
        and s["symbol"] not in PARSER_GARBAGE_RUST_SYMBOLS
    }


# ============================================================================
# TASK 1 — ROW BUILDERS
# ============================================================================

def _make_row(
    owner: str,
    row_id: str,
    rust_symbol: str,
    py_module: str,
    py_export_path: str | None,
    rust_crate: str,
    py_kind: str,
) -> dict:
    return {
        "id": row_id,
        "tier": "tier1",
        "ownerModule": owner,
        "rustCrate": rust_crate,
        "rustSymbol": rust_symbol,
        "pythonModule": py_module,
        "pythonExportPath": py_export_path,
        "pythonKind": py_kind,
    }


def build_owner_rows(
    owner: str,
    inventory: list[dict],
    py_surface_by_mod: dict[tuple[str, str], dict],
    already_covered_rust_symbols: set[str],
) -> tuple[list[dict], int]:
    """Build all tier1 rows for an owner given its residual inventory.

    Returns (rows, dedup_savings).
    """
    py_module = OWNER_TO_PY_MODULE[owner]
    rust_crate = OWNER_TO_RUST_CRATE[owner]
    class_idx = build_py_class_index(owner)
    function_idx = build_py_function_index(owner)
    rust_symbol_set = build_rust_symbol_set(owner)

    # Build submodule -> primary-class-anchor index from the PyClass discovery.
    # Used for Pitfall 2 fallback: free functions whose core equivalent isn't
    # exported from the -core crate anchor on the nearest Python class in the
    # same -py source file.
    submodule_to_anchor: dict[str, str] = {}
    for py_class_name, (sub, rust_struct, _rel) in class_idx.items():
        if sub in submodule_to_anchor:
            continue
        # Prefer a rust-surface-present anchor
        if py_class_name in rust_symbol_set:
            submodule_to_anchor[sub] = py_class_name
        elif rust_struct in rust_symbol_set:
            submodule_to_anchor[sub] = rust_struct
        else:
            # Use the Py* name even if not in core (last resort; most callers
            # will have a core-surface class elsewhere for this submodule).
            submodule_to_anchor[sub] = py_class_name

    def fallback_anchor_for_sub(sub: str) -> str | None:
        """Return a Rust-surface-present anchor for the given submodule or None."""
        if sub in submodule_to_anchor:
            cand = submodule_to_anchor[sub]
            if cand in rust_symbol_set:
                return cand
        # Scan the submodule's py source file for rust_symbols that DO exist in core
        owner_dir = REPO_ROOT / f"ClassicLib-rs/python-bindings/classic-{owner.replace('_', '-')}-py/src"
        rs_file = owner_dir / f"{sub}.rs"
        if not rs_file.exists():
            return None
        text = rs_file.read_text(encoding="utf-8", errors="ignore")
        # Find "use classic_<owner>_core::..." lines and pick the first symbol
        # present in rust_symbol_set.
        for m in re.finditer(r'use\s+classic_\w+_core\w*::(\w+(?:::\w+)*)', text):
            path = m.group(1)
            leaf = path.split("::")[-1]
            if leaf in rust_symbol_set:
                return leaf
        return None

    # Partition inventory
    py_classes: list[dict] = []
    py_methods: list[dict] = []
    py_functions: list[dict] = []
    rust_only: list[dict] = []
    for r in inventory:
        if r["gap_type"] == "rust_unmapped":
            rust_only.append(r)
            continue
        pep = r.get("python_export_path") or ""
        if "." in pep:
            py_methods.append(r)
            continue
        # Top-level python_unmapped: distinguish class vs function by surface kind
        kind = r.get("kind") or "?"
        # Surface kind is the authoritative classifier
        surface_info = py_surface_by_mod.get((py_module, pep))
        surface_kind = surface_info.get("kind") if surface_info else kind
        if surface_kind == "class":
            py_classes.append(r)
        elif surface_kind == "function":
            py_functions.append(r)
        else:
            # Unknown — treat as function by default
            py_functions.append(r)

    rows: list[dict] = []

    def emit(row: dict, covered_symbol: str) -> None:
        rows.append(row)
        already_covered_rust_symbols.add(covered_symbol)

    # Helper for finding the rust anchor for a py class
    def find_rust_anchor_for_class(py_class_name: str) -> tuple[str, str]:
        """Return (submodule, rust_symbol) for a Python class residual.

        Pitfall 2 rule: rustSymbol MUST resolve inside the -core crate's
        rust_api_surface. When the Python class has no same-name core symbol,
        fall back to the nearest submodule anchor.
        """
        # Prefer same-name rust symbol (e.g. BackupManager in classic-path-core)
        if py_class_name in rust_symbol_set:
            if py_class_name in class_idx:
                return (class_idx[py_class_name][0], py_class_name)
            return ("lib", py_class_name)
        # Query class_idx for submodule info
        sub_hint = "lib"
        if py_class_name in class_idx:
            sub_hint = class_idx[py_class_name][0]
        # Fallback: nearest anchor in the same submodule that exists in core
        fb = fallback_anchor_for_sub(sub_hint)
        if fb is not None:
            return (sub_hint, fb)
        # Last fallback: iterate all submodule anchors and pick the first core-visible one
        for sub, cand in submodule_to_anchor.items():
            if cand in rust_symbol_set:
                return (sub, cand)
        # Absolute last fallback: use the class name as-is (will hit Pitfall 2)
        return (sub_hint, py_class_name)

    # ----- Python class rows -----
    py_class_to_route: dict[str, tuple[str, str]] = {}  # py_class -> (sub, rust_symbol)
    for r in py_classes:
        py_class = r.get("python_export_path") or ""
        sub, rust_sym = find_rust_anchor_for_class(py_class)
        py_class_to_route[py_class] = (sub, rust_sym)
        row_id = f"{owner}.{sub}.{py_class}"
        py_kind = "class"
        row = _make_row(owner, row_id, rust_sym, py_module, py_class, rust_crate, py_kind)
        emit(row, rust_sym)

    # Also populate py_class_to_route for classes whose methods are residuals
    # but whose class row is already tier1 (not in inventory top-level).
    for r in py_methods:
        pep = r.get("python_export_path") or ""
        py_class = pep.split(".")[0]
        if py_class not in py_class_to_route:
            sub, rust_sym = find_rust_anchor_for_class(py_class)
            py_class_to_route[py_class] = (sub, rust_sym)

    # ----- Python method rows -----
    for r in py_methods:
        pep = r.get("python_export_path") or ""
        py_class = pep.split(".")[0]
        sub, rust_sym = py_class_to_route[py_class]
        row_id = f"{owner}.{sub}.{pep}"
        py_kind = r.get("kind") or "method"
        row = _make_row(owner, row_id, rust_sym, py_module, pep, rust_crate, py_kind)
        rows.append(row)
        # Methods inherit the class's rust symbol; don't mark additional dedup

    # ----- Python function rows -----
    for r in py_functions:
        py_fn = r.get("python_export_path") or ""
        # Discover the py source file (submodule) hosting this wrapper function
        if py_fn in function_idx:
            sub, rust_fn_name, _ = function_idx[py_fn]
        else:
            # Handle database-style rename (py_get_default_cache_ttl -> get_default_cache_ttl)
            py_renamed = f"py_{py_fn}"
            if py_renamed in function_idx:
                sub, rust_fn_name, _ = function_idx[py_renamed]
            else:
                sub, rust_fn_name = "lib", py_fn

        # Pitfall 2 check: if the rust symbol isn't in the -core surface, fall
        # back to a submodule anchor class that IS in the surface.
        if rust_fn_name not in rust_symbol_set:
            anchor = fallback_anchor_for_sub(sub)
            if anchor is not None:
                rust_fn_name = anchor
            # else leave as-is; caller reports Pitfall 2 and plan stops.

        row_id = f"{owner}.{sub}.{py_fn}"
        py_kind = r.get("kind") or "function"
        row = _make_row(owner, row_id, rust_fn_name, py_module, py_fn, rust_crate, py_kind)
        emit(row, rust_fn_name)

    # ----- Rust-only proxy rows (with same-row-dedup) -----
    dedup_savings = 0
    # Build a list of py function rows we just emitted (for fallback anchoring
    # in owners like version/registry that have no classes).
    py_function_row_exports = [r["pythonExportPath"] for r in rows if r["pythonKind"] == "function"]
    # Also build an index of ALL python surface exports for this owner (as a
    # last resort when neither classes nor functions exist yet).
    all_surface_exports = [
        e for e in py_surface_by_mod.values() if e["module"] == py_module
    ]

    for r in rust_only:
        rs = r.get("rust_symbol") or ""
        if not rs or rs in EXCLUDED_RUST_SYMBOLS or rs in PARSER_GARBAGE_RUST_SYMBOLS:
            continue
        if rs in already_covered_rust_symbols:
            dedup_savings += 1
            continue
        # Find anchor for pairing
        anchor_kind = "class"
        anchor_export = None
        sub = "lib"

        # Preference 1: a Python class with the same name (e.g. DocsPathFinder)
        if rs in py_class_to_route:
            sub, _ = py_class_to_route[rs]
            anchor_export = rs
        # Preference 2: A class whose rust anchor is the bare symbol
        elif any(r2 == rs for _, r2 in py_class_to_route.values()):
            match = next(cl for cl, (_, r2) in py_class_to_route.items() if r2 == rs)
            sub, _ = py_class_to_route[match]
            anchor_export = match
        # Preference 3: The first Python class of this owner
        elif py_class_to_route:
            first_class = next(iter(py_class_to_route))
            anchor_export = first_class
            sub = py_class_to_route[first_class][0]
        # Preference 4: The first Python function emitted in this plan
        elif py_function_row_exports:
            anchor_export = py_function_row_exports[0]
            anchor_kind = "function"
            sub = "lib"
        # Preference 5: The first Python export from the surface (covers owners
        # that have no residuals but do have pre-existing surface entries).
        elif all_surface_exports:
            fallback = all_surface_exports[0]
            anchor_export = fallback["export_path"]
            anchor_kind = fallback.get("kind") or "class"
            sub = "lib"
        else:
            # Absolute last resort: use rs as the anchor (will hit parity gate error)
            anchor_export = rs
            sub = "lib"

        row_id = f"{owner}.{sub}.{rs}@rust"
        row = _make_row(
            owner,
            row_id,
            rs,
            py_module,
            anchor_export,
            rust_crate,
            anchor_kind,
        )
        emit(row, rs)

    return rows, dedup_savings


SCANLOG_METHOD_RESIDUALS = [
    # (parent_class, method_name, submodule, parent_rust_symbol)
    ("CrashgenVersion", "to_tuple", "version", "CrashgenVersion"),
    ("LogParser", "find_errors", "parser", "LogParser"),
    ("PatternMatcher", "find_all", "parser", "PatternMatcher"),
    ("PatternMatcher", "has_match", "parser", "PatternMatcher"),
]


def build_scanlog_method_rows(contract: dict, py_surface_by_mod: dict[tuple[str, str], dict]) -> list[dict]:
    """Build tier1 rows for the 4 scanlog method residuals.

    Uses the existing scanlog parent class rows' rustSymbol/rustCrate as anchors.
    """
    rows = []
    existing_ids = {m["id"] for m in contract["tier1Mappings"]}
    for parent, method, submodule, parent_rust in SCANLOG_METHOD_RESIDUALS:
        row_id = f"scanlog.{submodule}.{parent}.{method}"
        if row_id in existing_ids:
            continue
        py_export = f"{parent}.{method}"
        row = {
            "id": row_id,
            "tier": "tier1",
            "ownerModule": "scanlog",
            "rustCrate": "classic-scanlog-core",
            "rustSymbol": parent_rust,
            "pythonModule": "classic_scanlog",
            "pythonExportPath": py_export,
            "pythonKind": "method",
        }
        rows.append(row)
    return rows


# ============================================================================
# TASK 1 DRIVER
# ============================================================================

def main_task1() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    py_surface = json.loads(PY_SURFACE_PATH.read_text(encoding="utf-8"))
    py_surface_by_mod: dict[tuple[str, str], dict] = {
        (e["module"], e["export_path"]): e for e in py_surface["exports"]
    }

    # Compute inventory fresh from live gaps (don't re-read markdown)
    residuals = load_residuals()
    inventory, blockers = classify_residuals(residuals)
    if blockers:
        print(f"BLOCKED: {len(blockers)} residuals cannot be routed. Re-run Task 0 to see BLOCKERS.md.", file=sys.stderr)
        return 1

    existing_ids = {m["id"] for m in contract["tier1Mappings"]}
    existing_by_owner_count = defaultdict(int)
    for m in contract["tier1Mappings"]:
        existing_by_owner_count[m.get("ownerModule", "?")] += 1

    already_covered_rust_symbols: set[str] = set()
    # Seed with existing file_io and shared rust symbols so we don't duplicate
    # Plan 08 entries when Plan 09a routing spans owners.
    for m in contract["tier1Mappings"]:
        already_covered_rust_symbols.add(m.get("rustSymbol", ""))

    new_rows: list[dict] = []
    per_owner_count: dict[str, int] = {}
    total_dedup = 0

    for owner in OWNER_ORDER:
        owner_inv = inventory.get(owner, [])
        # Important: only consider rust symbols covered BY THIS PLAN for dedup
        # (pre-existing rows are handled by ID-collision check at commit time).
        # But we still need to track cross-owner dedup within Plan 09a.
        rows, dedup = build_owner_rows(
            owner=owner,
            inventory=owner_inv,
            py_surface_by_mod=py_surface_by_mod,
            already_covered_rust_symbols=already_covered_rust_symbols,
        )
        per_owner_count[owner] = len(rows)
        total_dedup += dedup
        new_rows.extend(rows)

    # 4 scanlog method residuals
    scanlog_rows = build_scanlog_method_rows(contract, py_surface_by_mod)
    new_rows.extend(scanlog_rows)
    per_owner_count["scanlog_methods"] = len(scanlog_rows)

    # Validations
    new_ids = [r["id"] for r in new_rows]
    if len(set(new_ids)) != len(new_ids):
        from collections import Counter as C
        dupes = [k for k, v in C(new_ids).items() if v > 1]
        raise RuntimeError(f"Duplicate IDs inside new_rows: {dupes[:10]}")
    collisions = [i for i in new_ids if i in existing_ids]
    if collisions:
        raise RuntimeError(f"ID collisions with existing contract ({len(collisions)}): {collisions[:10]}")

    # Sort new rows by ID and splice in
    new_rows.sort(key=lambda r: r["id"])
    contract["tier1Mappings"].extend(new_rows)
    contract["tier1Mappings"].sort(key=lambda r: r["id"])

    CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    print(f"Added {len(new_rows)} new tier1 rows; cross-owner dedup saved {total_dedup} rows")
    print("Per-owner counts:")
    for owner in OWNER_ORDER:
        print(f"  {owner}: +{per_owner_count.get(owner, 0)} (was {existing_by_owner_count.get(owner, 0)})")
    print(f"  scanlog_methods: +{per_owner_count.get('scanlog_methods', 0)}")
    print(f"Total tier1Mappings: {len(contract['tier1Mappings'])}")

    # Invariant checks
    file_io_count = sum(1 for m in contract["tier1Mappings"] if m.get("ownerModule") == "file_io")
    shared_count = sum(1 for m in contract["tier1Mappings"] if m.get("ownerModule") == "shared")
    assert file_io_count == 95, f"file_io count drift: expected 95, got {file_io_count}"
    assert shared_count == 61, f"shared count drift: expected 61, got {shared_count}"
    fcx_count = sum(1 for m in contract["tier1Mappings"] if m.get("rustSymbol") == "GLOBAL_FCX_HANDLER")
    assert fcx_count == 0, f"GLOBAL_FCX_HANDLER must NOT be in tier1Mappings (R9); got {fcx_count}"
    print("Invariants verified: file_io=95, shared=61, GLOBAL_FCX_HANDLER=0.")
    return 0


# ============================================================================
# TASK 3 DRIVER
# ============================================================================

def main_task3() -> int:
    """Update runtime_coverage_registry.json with 14 new tier1 selectors + wave10 + retire tier2 entry."""
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    # 14 new tier1 selectors (one per newly-enrolled owner)
    NEW_OWNERS = [
        "scangame", "path", "constants", "message", "database", "resource",
        "xse", "settings", "yaml", "registry", "web", "version", "perf", "update",
    ]

    for owner in NEW_OWNERS:
        ids = sorted(
            m["id"] for m in contract["tier1Mappings"]
            if m.get("ownerModule") == owner and m.get("tier") == "tier1"
        )
        if not ids:
            raise RuntimeError(
                f"Owner {owner} has no tier1Mappings after Task 1; check routing"
            )
        computed_hash = _stable_id_hash(ids)  # Full 64-char SHA-256 (C2 fix)
        assert len(computed_hash) == 64, f"hash length must be 64, got {len(computed_hash)}"
        entry = {
            "coverageId": f"python-tier1-{owner}",
            "classification": "runtime_verified",
            "verificationMode": "direct_call",
            "ownerModule": owner,
            "tier": "tier1",
            "contractSelector": {"ownerModule": owner, "tier": "tier1"},
            "contractCount": len(ids),
            "contractIdsHash": computed_hash,
            "testSuite": "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py",
            "testCaseId": f"{owner}-residuals-smoke",
        }
        # Replace if exists, else append
        registry["entries"] = [
            e for e in registry["entries"] if e.get("coverageId") != entry["coverageId"]
        ]
        registry["entries"].append(entry)
        print(f"  {entry['coverageId']}: count={len(ids)}, hash={computed_hash[:16]}...")

    # L15 R8 precedent: separate selector for scanlog method residuals
    # (do NOT mutate python-tier1-scanlog's testSuite)
    scanlog_method_ids = sorted(
        m["id"] for m in contract["tier1Mappings"]
        if m.get("ownerModule") == "scanlog" and any(
            m["id"].endswith(suffix)
            for suffix in (".to_tuple", ".find_errors", ".find_all", ".has_match")
        )
    )
    if scanlog_method_ids:
        wave10_hash = _stable_id_hash(scanlog_method_ids)
        wave10_entry = {
            "coverageId": "python-tier1-scanlog-wave10-residuals",
            "classification": "runtime_verified",
            "verificationMode": "direct_call",
            "ownerModule": "scanlog",
            "tier": "tier1",
            "contractSelector": None,  # explicit list, not selector-based
            "contractCount": len(scanlog_method_ids),
            "contractIdsHash": wave10_hash,
            "contractIds": scanlog_method_ids,
            "testSuite": "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py",
            "testCaseId": "scanlog-method-residuals",
        }
        registry["entries"] = [
            e for e in registry["entries"]
            if e.get("coverageId") != wave10_entry["coverageId"]
        ]
        registry["entries"].append(wave10_entry)
        print(f"  python-tier1-scanlog-wave10-residuals: count={len(scanlog_method_ids)}, hash={wave10_hash[:16]}...")

    # M12: Retire python-tier2-scanlog-runtime — all 4 methods are now tier1 via
    # python-tier1-scanlog-wave10-residuals
    before = len(registry["entries"])
    registry["entries"] = [
        e for e in registry["entries"]
        if e.get("coverageId") != "python-tier2-scanlog-runtime"
    ]
    after = len(registry["entries"])
    if before != after:
        print("  retired: python-tier2-scanlog-runtime (M12)")

    # Preserve Plan 08's python-tier1-shared and python-tier1-file_io UNCHANGED
    shared_entry = next(
        (e for e in registry["entries"] if e.get("coverageId") == "python-tier1-shared"),
        None,
    )
    fileio_entry = next(
        (e for e in registry["entries"] if e.get("coverageId") == "python-tier1-file_io"),
        None,
    )
    assert shared_entry is not None and shared_entry.get("contractCount") == 61, \
        "python-tier1-shared must remain count=61"
    assert fileio_entry is not None and fileio_entry.get("contractCount") == 95, \
        "python-tier1-file_io must remain count=95"
    assert len(shared_entry["contractIdsHash"]) == 64, "Plan 08 shared hash length must remain 64"
    assert len(fileio_entry["contractIdsHash"]) == 64, "Plan 08 file_io hash length must remain 64"
    print(f"  Plan 08 integrity: shared={shared_entry['contractCount']}, file_io={fileio_entry['contractCount']}")

    # python-tier1-scanlog needs its hash recomputed because the 4 method
    # residuals join its tier1 ID pool via the contractSelector match.
    scanlog_ids = sorted(
        m["id"] for m in contract["tier1Mappings"]
        if m.get("ownerModule") == "scanlog" and m.get("tier") == "tier1"
    )
    scanlog_entry = next(
        (e for e in registry["entries"] if e.get("coverageId") == "python-tier1-scanlog"),
        None,
    )
    if scanlog_entry is not None:
        scanlog_entry["contractCount"] = len(scanlog_ids)
        scanlog_entry["contractIdsHash"] = _stable_id_hash(scanlog_ids)
        assert len(scanlog_entry["contractIdsHash"]) == 64
        print(f"  python-tier1-scanlog (updated): count={len(scanlog_ids)}, hash={scanlog_entry['contractIdsHash'][:16]}...")

    REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    print(f"Updated runtime_coverage_registry.json with {len(NEW_OWNERS) + 1} new/updated selectors, retired tier2 stale entry")
    return 0


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
