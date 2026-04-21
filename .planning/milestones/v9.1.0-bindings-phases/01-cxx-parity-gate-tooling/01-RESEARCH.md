# Phase 1: CXX Parity Gate Tooling - Research

**Researched:** 2026-04-06
**Domain:** Python source-parsing parity tooling for CXX bridge surface
**Confidence:** HIGH — all findings sourced directly from committed repo files; zero speculative claims

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The gate extracts functions + shared types: `extern "Rust"` function signatures, `extern "C++"` function signatures, shared `struct` definitions (with field names + field types), shared `enum` definitions (with variants), and opaque type declarations (`type Foo;`). Comments, `use` statements, and type aliases are NOT part of the contract.
- **D-02:** Drift comparison is symbol + types: function row matches iff symbol name, ordered argument types, and return type all match. Lifetime annotations, `&`/`&mut`, `Pin<&mut T>` wrapping, and `UniquePtr<T>` are part of the signature and ARE compared. Struct rows match iff ordered `(field_name, field_type)` pairs unchanged. Enum rows match iff ordered variant list unchanged. Doc comments are NOT compared.
- **D-03:** Contract shape: top-level wrapper key `entries` (flat list). Each row: `{ id, rustSymbol, kind: "function" | "struct" | "enum" | "opaque", bridgeModule, sourceFile, signature (kind=function only: serialized arg-types + return-type), fields (kind=struct only: ordered list), variants (kind=enum only: ordered list) }`. No second-binding column.
- **D-04:** No `tier1Mappings`/`tier2*` wrapper keys anywhere in the CXX gate. No Tier-2 concept from birth.
- **D-05:** Committed baseline at `docs/implementation/cxx_api_parity/baseline/parity_contract.json`. Generated artifacts (`rust_api_surface.json`, `cxx_diff_report.json`, `cxx_diff_report.md`, `cxx_gate_report.md`) live in the same `baseline/` directory and are committed.
- **D-06:** Two scripts under `tools/cxx_api_parity/`: `check_parity_gate.py` (read-only diff + `--update-baseline`) and `generate_baseline.py` (standalone bootstrap + shared `parse_cxx_bridge_surface()` helper).
- **D-07:** Both scripts parse `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` for `cxx_build::bridges([...])` array dynamically. No hardcoded list.
- **D-08:** Generated runtime artifacts go to `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` (ephemeral, gitignored). `--update-baseline` copies tracked subset to `docs/implementation/cxx_api_parity/baseline/` via `sync_baseline_artifacts()`.
- **D-09:** Phase 1 gate is strictly file-list-based: parses only files listed in `build.rs`. `src/path.rs` is NOT in `build.rs` and is invisible to Phase 1. Baseline is born GREEN.
- **D-10:** Phase 2 adds `src/path.rs`, `src/constants.rs`, `src/web.rs` to `build.rs`. Gate detects drift; maintainer accepts via `--update-baseline`. No `expected_missing` allowlist, no Tier-2 deferral.
- **D-11:** Cross-crate sibling coverage is NOT part of drift detection.
- **D-12:** The CXX gate has NO `--deferred-registry` argument and NO deferred backlog concept. The script's CLI surface is intentionally narrower than Python's.
- **D-13:** `check_parity_gate.py` writes: `rust_api_surface.json`, `cxx_diff_report.json`, `cxx_diff_report.md`, `cxx_gate_report.md` to `--output-dir` on every run.
- **D-14:** Stale committed-artifact detection: gate exits non-zero if committed baseline artifacts no longer match a fresh source scan.
- **D-15:** Contributor doc at `docs/api/cxx-parity-gate.md`.
- **D-16:** Local invocation: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — pure Python, no PowerShell wrapper.

### Claude's Discretion

- Exact regex/parser strategy inside `parse_cxx_bridge_surface()` (hand-rolled regex vs `syn`-via-shell-out vs small Rust helper binary).
- Exact field-name choices inside the row schema (camelCase recommended to match Python/Node JSON style).
- Whether `parse_cxx_bridge_surface()` is exported from `generate_baseline.py` or lives in a separate `cxx_surface_parser.py` module.
- Test fixtures for the gate itself: `tests/fixtures/` with synthetic bridge source files is recommended.

### Deferred Ideas (OUT OF SCOPE)

- Cross-crate sibling coverage report.
- Doc-comment comparison as part of drift detection.
- Binary ABI checks.
- Cargo test / Rust-native gate implementation.
- `schemars`-based contract generation.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CXXG-01 | New `tools/cxx_api_parity/` Python tool parses every `#[cxx::bridge]` source file enumerated by `classic-cpp-bridge/build.rs` and emits structured surface inventory JSON | §Bridge Syntax Inventory documents all 14 file patterns; §Build.rs Parsing Pattern shows robustness approach |
| CXXG-02 | Committed `tools/cxx_api_parity/parity_contract.json` baseline (NOTE: D-05 overrides REQUIREMENTS.md path — correct path is `docs/implementation/cxx_api_parity/baseline/parity_contract.json`) | §Baseline Artifact Location Pattern documents confirmed path |
| CXXG-03 | `check_parity_gate.py` fails non-zero on baseline drift, missing-from-bridge entries, and orphaned bridge entries | §Script Skeleton documents exit-code semantics; §Validation Architecture maps all failure modes |
| CXXG-04 | Gate script's deferred-registry path is optional from day one (hardcoded-path pattern not repeated) | §No-Deferred-Registry Design confirms by absence; testable as CLI surface check |
| CXXG-05 | Contributor docs at `docs/api/cxx-parity-gate.md` | §Contributor Doc Content documents what must be covered |
</phase_requirements>

---

## Summary

Phase 1 builds a source-only Python parity gate for the CXX bridge (`tools/cxx_api_parity/`), mirroring the established `tools/python_api_parity/` and `tools/node_api_parity/` skeleton verbatim except for the domain-specific parser body and the simpler (no Tier-2, no deferred-registry) contract shape.

The two scripts share a `parse_cxx_bridge_surface()` helper that: (1) reads `build.rs` dynamically to get the 14-file list, (2) parses each file's `#[cxx::bridge(namespace = "...")]` block for `extern "Rust"` functions, shared structs/enums, opaque types, and `extern "C++"` items, and (3) emits a deterministic JSON surface indexed by a stable `id` hash. The gate then diffs this surface against the committed baseline at `docs/implementation/cxx_api_parity/baseline/parity_contract.json` and exits 1 on any drift or stale-artifact condition.

The 14 source files span three syntactic categories: function-only modules (runtime, perf, markdown, message, registry, update), struct-heavy modules (scangame, database, config, yaml, game, files, scanner), and the types module (opaque-type-only). The scanner module additionally uses `unsafe extern "C++"` with `include!()` and enum declarations with `#[derive(...)]` attributes — the only syntactic outliers across the 14 files.

**Primary recommendation:** Mirror the Python gate skeleton exactly. Write the parser as hand-rolled regex against the `mod ffi { ... }` block content. The bridge modules are syntactically consistent enough that regex extraction is tractable and matches the repo norm established by the Python and Node gates.

**Critical path/baseline location discrepancy:** REQUIREMENTS.md §CXXG-02 says baseline lives at `tools/cxx_api_parity/parity_contract.json`. CONTEXT.md D-05 overrides this with `docs/implementation/cxx_api_parity/baseline/parity_contract.json`. **The planner MUST follow D-05 (CONTEXT.md), not REQUIREMENTS.md.** The REQUIREMENTS.md path is older and was superseded by the architecture decision.

---

## Standard Stack

### Core (no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `re` | stdlib | Regex-based source parsing | Same approach used by both existing parity gates |
| Python stdlib `json` | stdlib | JSON serialization/deserialization | Same approach used by both existing parity gates |
| Python stdlib `pathlib` | stdlib | Path manipulation, cross-platform | Same approach used by both existing parity gates |
| Python stdlib `argparse` | stdlib | CLI argument parsing | Same approach used by both existing parity gates |
| Python stdlib `hashlib` | stdlib | Stable `id` hash generation from symbol+kind+module | Used in `binding_parity_runtime_coverage.py` |
| Python stdlib `shutil` | stdlib | Copy artifacts in `sync_baseline_artifacts()` | Same approach used by both existing parity gates |
| Python stdlib `datetime` | stdlib | `generated_at_utc` timestamp field | Same approach used by both existing parity gates |

**Installation:** No `pip install` needed. All gate scripts use Python stdlib only. Confirmed by reading both existing gate scripts: `re`, `json`, `pathlib`, `argparse`, `shutil`, `operator`, `sys`, `collections.defaultdict`, `datetime` — all stdlib.

**Version verification:** Python 3.12+ required (matches `CLAUDE.md` and CI `setup-python 3.12`). No version check needed for stdlib modules.

### Supporting (shared module already exists)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tools/binding_parity_runtime_coverage.py` | repo-local | Shared `load_json_file()` helper | Do NOT use for CXX gate — CXX gate has no runtime coverage concept (D-04, D-12). `load_json_file()` may be extracted for file-loading utility only. |

**Key finding:** `binding_parity_runtime_coverage.py` lives at `tools/binding_parity_runtime_coverage.py` (not inside a subdirectory). Both Python and Node gate scripts add `tools/` to `sys.path` via `sys.path.append(str(Path(__file__).resolve().parents[1]))` to import it. The CXX gate should follow the same `sys.path` pattern but only import from it if genuinely needed (e.g., the `load_json_file()` function). The runtime coverage machinery (`build_coverage_summary`, `render_coverage_summary_markdown`) is irrelevant to the CXX gate and must NOT be imported.

---

## Architecture Patterns

### Established Script Skeleton (verbatim copy target)

Both `check_parity_gate.py` scripts (Python and Node) follow identical structural patterns that the CXX gate MUST replicate:

```python
#!/usr/bin/env python3
"""Run the CXX parity gate."""
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))  # Add tools/ to path

from generate_baseline import (
    parse_cxx_bridge_surface,   # shared parser helper
    write_json,
)

def artifacts_match(expected: Path, actual: Path) -> bool:
    """JSON: pop generated_at_utc before comparing. Markdown: skip '- Generated:' lines."""
    ...

def sync_baseline_artifacts(output_dir, baseline_output_dir, artifact_names) -> None:
    """shutil.copyfile each artifact into baseline_output_dir."""
    ...

def render_cxx_gate_markdown(diff_report) -> str:
    """'# CXX Parity Gate Report' (no Tier-1 wording)."""
    ...

def main() -> int:
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--repo-root", ...)
    parser.add_argument("--contract", ...)
    parser.add_argument("--output-dir", ...)
    parser.add_argument("--baseline-output-dir", ...)
    parser.add_argument("--update-baseline", action="store_true", ...)
    # NOTE: NO --deferred-registry argument (D-12)
    args = parser.parse_args()
    ...
    if args.update_baseline:
        sync_baseline_artifacts(output_dir, baseline_output_dir, tracked_artifact_names)
    ...
    if drift_count > 0:
        return 1
    if stale_artifacts:
        return 1
    print("CXX parity gate passed.")
    return 0
```

### `artifacts_match()` Implementation (exact pattern)

Sourced directly from both existing gate scripts — the CXX gate MUST replicate this exactly:

```python
def artifacts_match(expected: Path, actual: Path) -> bool:
    if not expected.exists() or not actual.exists():
        return False
    if expected.suffix == ".json":
        expected_payload = json.loads(expected.read_text(encoding="utf-8"))
        actual_payload = json.loads(actual.read_text(encoding="utf-8"))
        expected_payload.pop("generated_at_utc", None)
        actual_payload.pop("generated_at_utc", None)
        return expected_payload == actual_payload
    expected_lines = [
        l for l in expected.read_text(encoding="utf-8").splitlines()
        if not l.startswith("- Generated:")
    ]
    actual_lines = [
        l for l in actual.read_text(encoding="utf-8").splitlines()
        if not l.startswith("- Generated:")
    ]
    return expected_lines == actual_lines
```

### `write_json()` Implementation (exact pattern)

```python
def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
```

Note: `sort_keys=False` — key ordering is controlled by Python dict insertion order, not alphabetic sorting. The planner must ensure that the row builder constructs dicts with deterministic key order.

### `build.rs` Parsing Pattern

The `build.rs` content is:
```rust
#[cfg(windows)]
fn main() {
    cxx_build::bridges([
        "src/types.rs",
        "src/runtime.rs",
        ...
        "src/markdown.rs",
    ])
    .include("include")
    .std("c++17")
    .compile("classic-cpp-bridge");
    ...
}
```

**Regex to extract the file list** (handles the actual multi-line form):
```python
bridges_match = re.search(
    r'cxx_build::bridges\(\s*\[(.*?)\]\s*\)',
    source,
    re.DOTALL
)
# Extract quoted strings from the matched array body:
file_paths = re.findall(r'"([^"]+)"', bridges_match.group(1))
```

This pattern handles:
- Multi-line array (the actual form in `build.rs`)
- Quoted string extraction
- Trailing commas (harmless — `re.findall` extracts only quoted content)
- Whitespace between items

**Robustness requirement:** If the regex fails to find `cxx_build::bridges`, the gate MUST exit non-zero with a diagnostic. No fallback to a hardcoded list (D-07).

**Windows path note:** The `build.rs` uses forward slashes (`"src/types.rs"`) even on Windows. The parser produces `Path(repo_root) / "ClassicLib-rs/cpp-bindings/classic-cpp-bridge" / file_path` to get the absolute path. Do not use `os.path.join` with backslashes.

### CXX Bridge Source Parser Pattern

The `mod ffi { ... }` block extraction approach:

```python
def extract_ffi_block(source: str) -> str | None:
    """Extract content of the #[cxx::bridge] mod ffi block."""
    # Step 1: find namespace
    ns_match = re.search(r'#\[cxx::bridge(?:\(namespace\s*=\s*"([^"]+)"\))?\]', source)
    if not ns_match:
        return None, None
    namespace = ns_match.group(1) or ""
    # Step 2: find 'mod ffi {' and extract balanced braces
    ffi_start = source.find("mod ffi {", ns_match.end())
    if ffi_start == -1:
        return None, namespace
    # Brace-balanced extraction
    depth = 0
    for i, ch in enumerate(source[ffi_start:], ffi_start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return source[ffi_start:i+1], namespace
    return None, namespace
```

Then inside the ffi block, parse each category:

```python
# Opaque types in extern "Rust": type Foo;
OPAQUE_TYPE_RE = re.compile(r'type\s+([A-Za-z0-9_]+)\s*;')

# Shared structs: struct Foo { ... }
STRUCT_RE = re.compile(r'struct\s+([A-Za-z0-9_]+)\s*\{([^}]*)\}', re.DOTALL)

# Shared enums: enum Foo { ... } (may have #[derive(...)] before)
ENUM_RE = re.compile(r'enum\s+([A-Za-z0-9_]+)\s*\{([^}]*)\}', re.DOTALL)

# Functions inside extern "Rust" or extern "C++" blocks
EXTERN_RUST_RE = re.compile(r'extern\s+"Rust"\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.DOTALL)
EXTERN_CPP_RE = re.compile(r'unsafe\s+extern\s+"C\+\+"\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.DOTALL)
FUNCTION_RE = re.compile(r'fn\s+([A-Za-z0-9_]+)\s*\((.*?)\)(?:\s*->\s*([^;{]+))?\s*;', re.DOTALL)
```

### Recommended Project Structure

```
tools/cxx_api_parity/
├── check_parity_gate.py       # Main gate script (CI entry point)
├── generate_baseline.py       # Bootstrap + shared parse_cxx_bridge_surface()
├── README.md                  # One-line pointer to docs/api/cxx-parity-gate.md
└── tests/
    └── fixtures/
        ├── simple_ffi.rs      # extern "Rust" functions only, no structs
        ├── struct_ffi.rs      # shared struct with multiple fields
        ├── enum_ffi.rs        # shared enum with variants + #[derive]
        ├── opaque_ffi.rs      # opaque type declarations
        └── mixed_ffi.rs       # all kinds in one file (scanner-like)

docs/implementation/cxx_api_parity/
└── baseline/
    ├── parity_contract.json   # committed baseline (born green at Phase 1)
    ├── rust_api_surface.json  # committed surface snapshot
    ├── cxx_diff_report.json   # committed diff (all matched at birth)
    ├── cxx_diff_report.md     # committed human-readable diff
    └── cxx_gate_report.md     # committed gate report (pass at birth)

ClassicLib-rs/cpp-bindings/classic-cpp-bridge/
└── parity-artifacts/          # ephemeral, gitignored (needs .gitignore entry)
    └── [same file names, regenerated on each run]

docs/api/
└── cxx-parity-gate.md         # contributor documentation (CXXG-05)
```

### Anti-Patterns to Avoid

- **Importing `build_coverage_summary` or `render_coverage_summary_markdown`** from `binding_parity_runtime_coverage.py` — the CXX gate has no runtime coverage concept.
- **Adding `--deferred-registry` argument** — explicitly forbidden by D-12/CXXG-04.
- **Using `tier1Mappings` as the top-level key** — the CXX contract uses `entries` (D-03/D-04).
- **Hardcoding the 14-file list** — must parse `build.rs` (D-07).
- **Using `sort_keys=True` in `json.dumps()`** — breaks dict-insertion-order stability of existing gates.
- **Outputting to `nul`** — Windows-forbidden per CLAUDE.md.

---

## Bridge Syntax Inventory (All 14 Files)

This section documents every syntactic pattern the parser must handle, with the module that exemplifies each.

### Category 1: Function-only modules (no shared structs/enums)

**`runtime.rs`** — 3 functions, no types:
```rust
#[cxx::bridge(namespace = "classic::runtime")]
mod ffi {
    extern "Rust" {
        fn init_runtime();           // no-arg, no return
        fn shutdown_runtime();       // no-arg, no return
        fn is_runtime_active() -> bool;  // no-arg, bool return
    }
}
```

**`perf.rs`** — 5 functions, no types:
```rust
#[cxx::bridge(namespace = "classic::perf")]
mod ffi {
    extern "Rust" {
        fn perf_record_timing(operation: &str, duration_secs: f64);
        fn perf_get_summary() -> Vec<String>;
        fn perf_clear_metrics();
        fn perf_get_operation_count(operation: &str) -> u32;
        fn perf_get_operation_average(operation: &str) -> f64;
    }
}
```

**`markdown.rs`** — 2 functions, no types:
```rust
#[cxx::bridge(namespace = "classic::markdown")]
mod ffi {
    extern "Rust" {
        fn markdown_to_html(markdown: &str) -> String;
        fn normalize_markdown(input: &str) -> String;
    }
}
```

**`message.rs`** — 8 functions (multi-arg including u32), no types:
```rust
#[cxx::bridge(namespace = "classic::message")]
mod ffi {
    extern "Rust" {
        fn log_info(message: &str);
        fn log_warning(message: &str);
        fn log_error(message: &str);
        fn log_debug(message: &str);
        fn log_trace(message: &str);
        fn log_startup_binding_contract_validated(contract: &str, checked_bindings: u32, correlation_id: &str);
        fn log_startup_binding_contract_failed(contract: &str, missing_binding: &str, failure_type: &str, failure_hint: &str, error: &str, correlation_id: &str);
        fn log_startup_acceleration_status(active_components: u32, total_components: u32, acceleration_level: &str, correlation_id: &str);
        fn init_logging();
    }
}
```

**`registry.rs`** — 11 functions, no types:
```rust
#[cxx::bridge(namespace = "classic::registry")]
mod ffi {
    extern "Rust" {
        fn registry_set_string(key: &str, value: String);
        fn registry_get_string(key: &str) -> String;
        fn registry_set_bool(key: &str, value: bool);
        // ... 8 more functions
    }
}
```

**`update.rs`** — 2 functions, 1 struct:
```rust
#[cxx::bridge(namespace = "classic::update")]
mod ffi {
    struct UpdateCheckResult {
        has_update: bool,
        latest_version: String,
        release_notes: String,
        error_message: String,
    }
    extern "Rust" {
        fn github_has_update(current: &str, latest: &str) -> bool;
        fn github_check_for_updates(owner: &str, repo: &str, current_version: &str) -> UpdateCheckResult;
    }
}
```

### Category 2: Opaque-type-only module

**`types.rs`** — 2 opaque types + 11 functions (all functions take `&TypeName` params):
```rust
#[cxx::bridge(namespace = "classic::types")]
mod ffi {
    extern "Rust" {
        type StringMap;      // opaque type declaration
        type StringVecMap;   // opaque type declaration
        fn string_map_get(map: &StringMap, key: &str) -> String;
        fn string_map_contains(map: &StringMap, key: &str) -> bool;
        // ... 9 more functions using &StringMap or &StringVecMap
    }
}
```

### Category 3: Multi-struct modules

**`scangame.rs`** — 2 shared structs, 2 functions, no opaque types:
```rust
#[cxx::bridge(namespace = "classic::scangame")]
mod ffi {
    struct SetupCheckResult {
        combined_output: String,
        has_errors: bool,
        total_checks: u32,
    }
    struct PathDetectionNeeds {
        needs_game_path: bool,
        needs_docs_path: bool,
    }
    extern "Rust" {
        fn run_setup_checks(...) -> SetupCheckResult;
        fn needs_path_detection(...) -> PathDetectionNeeds;
    }
}
```

**`yaml.rs`** — 2 shared structs (`CacheStats`, `YamlValue`), 1 opaque type (`YamlOps`), 14 functions:
```rust
#[cxx::bridge(namespace = "classic::yaml")]
mod ffi {
    struct CacheStats { hits: u64, misses: u64, hit_rate: f64, size: usize, capacity: usize, }
    struct YamlValue { value: String, is_null: bool, value_type: String, }
    extern "Rust" {
        type YamlOps;
        fn yaml_ops_new() -> Box<YamlOps>;
        fn yaml_ops_load_file(ops: &mut YamlOps, path: &str) -> Result<()>;
        // ... 12 more functions, some using &mut YamlOps
    }
}
```

**`database.rs`** — 1 opaque type (`DbPool`), 9 functions including `Result<()>` and `Box<DbPool>` return types:
```rust
#[cxx::bridge(namespace = "classic::database")]
mod ffi {
    extern "Rust" {
        type DbPool;
        fn db_pool_new(game_table: &str, max_connections: u32, cache_ttl_secs: u64) -> Box<DbPool>;
        fn db_pool_initialize(pool: &DbPool, db_paths: &[String]) -> Result<()>;
        fn db_pool_get_entry(pool: &DbPool, formid: &str, plugin: &str) -> String;
        // ... 6 more
    }
}
```

**`config.rs`** — 3 shared structs (`CacheStats`, `YamlDataModSolutionCriteria`, `YamlDataModSolutionEntry`), 1 opaque type (`YamlData`), 33 functions:
```rust
#[cxx::bridge(namespace = "classic::config")]
mod ffi {
    struct CacheStats { hits: u64, misses: u64, hit_rate: f64, size: usize, capacity: usize, }
    struct YamlDataModSolutionCriteria { any: Vec<String>, all: Vec<String>, }
    struct YamlDataModSolutionEntry { id: String, criteria: YamlDataModSolutionCriteria, ... }
    extern "Rust" {
        type YamlData;
        fn yaml_data_load(...) -> Result<Box<YamlData>>;
        fn yaml_data_classic_version(data: &YamlData) -> &str;  // &str return type
        // ... 31 more functions
    }
}
```

**`files.rs`** — 1 shared struct (`CacheStats`, `TargetedResolutionDto`), 3 opaque types, 15 functions including `Result<bool>`, `Result<String>`, `Result<u32>`:
```rust
#[cxx::bridge(namespace = "classic::files")]
mod ffi {
    struct CacheStats { hits: u64, misses: u64, hit_rate: f64, size: usize, capacity: usize, }
    struct TargetedResolutionDto { logs: Vec<String>, rejected_paths: Vec<String>, ... }
    extern "Rust" {
        type CxxBackupManager;
        type CxxGameFilesManager;
        type CxxLogCollector;
        fn backup_manager_new(game_root: &str) -> Box<CxxBackupManager>;
        fn backup_manager_exists(mgr: &CxxBackupManager, backup_type: &str) -> Result<bool>;
        // ... 12 more
    }
}
```

**`game.rs`** — 5 shared structs, 0 opaque types, 11 functions:
```rust
#[cxx::bridge(namespace = "classic::game")]
mod ffi {
    struct VersionInfoDto { id: String, version_string: String, ..., steam_id: u32, is_vr: bool, found: bool, }
    struct XseConfigDto { acronym: String, ..., file_count: u32, found: bool, }
    struct CrashgenConfigDto { version: String, name: String, ..., download_url: String, }
    struct MatchResultDto { matched_id: String, confidence: String, message: String, is_match: bool, }
    struct GameVersionDto { major: u32, minor: u32, patch: u32, build: u32, valid: bool, }
    extern "Rust" {
        fn version_registry_get_by_id(id: &str) -> VersionInfoDto;
        fn version_registry_get_all_ids() -> Vec<String>;
        // ... 9 more
    }
}
```

### Category 4: Complex module with enums, extern "C++", and multiple type categories

**`scanner.rs`** — most complex module. Unique patterns:
```rust
#[cxx::bridge(namespace = "classic::scanner")]
mod ffi {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]   // ATTRIBUTE before enum
    enum BatchProgressEventKind {
        Queued = 0,      // discriminant values
        Started = 1,
        Phase = 2,
        Completed = 3,
        Failed = 4,
    }
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum BatchProgressPhase {
        Setup = 0,
        Parse = 1,
        Analyze = 2,
        Finalize = 3,
    }
    struct BatchProgressEvent {
        completed: u32, total: u32, input_index: u32, log_path: String,
        event_kind: BatchProgressEventKind,   // FIELD TYPE = ENUM from same bridge
        phase: BatchProgressPhase,
        success: bool,
    }
    struct ScanResult { ... }
    struct BatchScanResult { ... }
    struct PapyrusStatsDto { dumps: u32, ..., dumps_stacks_ratio: f64, }

    unsafe extern "C++" {                           // C++ IMPORT (not Rust export)
        include!("classic_cxx_bridge/scan_progress_callback.h");
        type ScanBatchProgressCallback;             // C++ opaque type
        fn on_batch_progress(self: &ScanBatchProgressCallback, event: &BatchProgressEvent);
    }

    extern "Rust" {
        type FullScanConfig;
        type Orchestrator;
        type CxxPapyrusAnalyzer;
        fn build_full_scan_config(...) -> Result<Box<FullScanConfig>>;
        fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>>;
        fn orchestrator_process_logs_batch_with_progress(
            orch: &Orchestrator,
            log_paths: &[String],
            max_concurrent: u32,
            callback: &ScanBatchProgressCallback,  // C++ type used as Rust fn param
        ) -> Vec<BatchScanResult>;
        fn papyrus_start_monitoring(analyzer: &mut CxxPapyrusAnalyzer) -> Result<()>;
        // ...
    }
}
```

**Parser must handle:**
- `#[derive(...)]` attributes before `enum` — strip attributes, keep enum body
- Enum variants with explicit discriminant values (`Queued = 0`)
- `unsafe extern "C++"` block with `include!()` macro and C++ opaque types
- C++ types appearing as parameter types in `extern "Rust"` functions
- `&mut TypeName` parameter bindings (mutable reference to opaque type)
- `Result<Box<TypeName>>` return types
- `Vec<StructName>` return types (struct from same bridge)
- Multi-line function signatures (scanner has the longest signatures)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization with stable key order | Custom serializer | `json.dumps(payload, indent=2, sort_keys=False)` | dict insertion order in Python 3.7+ is stable; `sort_keys=False` matches existing gate behavior |
| Stale-artifact comparison | Byte-level file diff | `artifacts_match()` with `generated_at_utc` pop | `generated_at_utc` differs on every run; popping it before compare is the established pattern |
| Argument parsing | Custom arg parser | `argparse` with same arg names as Python gate | Muscle memory reuse; CI invocation is the same pattern |
| File list extraction from `build.rs` | `exec()`-based Rust eval | `re.search(r'cxx_build::bridges\(...\)')` regex | Source-only; no Rust build required |
| Baseline copying | `shutil.move()` | `sync_baseline_artifacts()` with `shutil.copyfile()` | Copies, does not delete; matches Python/Node gate behavior |

**Key insight:** The entire gate is stdlib-only Python. The only "complex" part is the CXX bridge block parser — and that complexity is confined to `parse_cxx_bridge_surface()` in `generate_baseline.py`.

---

## Common Pitfalls

### Pitfall 1: Parsing `mod ffi { ... }` Content Without Brace Balancing

**What goes wrong:** Using `re.search(r'mod ffi \{(.*?)\}', source, re.DOTALL)` fails on any struct with nested braces (`YamlDataModSolutionEntry` has a nested `criteria: YamlDataModSolutionCriteria` field that itself is a struct). The non-greedy `.*?` stops at the first `}`.

**How to avoid:** Use a brace-depth counter to find the balanced close brace of `mod ffi {`. Do NOT rely on regex alone for the outer ffi block boundary. Once the outer block is extracted as a flat string, regex is fine for parsing individual items (structs, enums, functions) since they have predictable structure.

**Warning signs:** Parser returns incomplete ffi block content; functions defined after the first struct are missing from the surface.

### Pitfall 2: Missing Functions Inside `extern "C++"` Block

**What goes wrong:** The scanner module has an `unsafe extern "C++"` block containing the `ScanBatchProgressCallback` type and `on_batch_progress` function. A parser that only looks for `extern "Rust"` misses the C++ exports entirely.

**How to avoid:** Parse BOTH `extern "Rust" { ... }` and `unsafe extern "C++" { ... }` blocks. Assign `kind` based on which block the item came from. The contract schema (D-03) says `kind: "function"` for functions regardless of block origin — use `rustSymbol` vs a separate `cxxSymbol` field, or add a `extern` field (`"Rust"` vs `"C++"`).

**Note from D-01:** `extern "C++"` items ARE part of the contract. The `ScanBatchProgressCallback` type and `on_batch_progress` function in `scanner.rs` must appear in the baseline.

### Pitfall 3: Struct Field Parsing Loses Nested Struct Field Types

**What goes wrong:** `YamlDataModSolutionEntry` in `config.rs` has `criteria: YamlDataModSolutionCriteria` where the field type is another struct from the same bridge. A field-type regex that only matches simple types (`String`, `bool`, `u32`, `Vec<String>`) produces an empty or incorrect field type for this field.

**How to avoid:** The field type regex must accept arbitrary non-comma, non-newline content: `r'(\w+)\s*:\s*([^,\n]+)'`. This captures compound types including `Vec<...>`, nested struct references, and primitive types.

### Pitfall 4: Enum Variants with Discriminants

**What goes wrong:** `BatchProgressEventKind` in `scanner.rs` uses `Queued = 0, Started = 1, ...` form. A naive variant parser that splits on commas produces `["Queued = 0", "Started = 1", ...]` instead of `["Queued", "Started", ...]`.

**How to avoid:** Strip the `= N` suffix from each variant after splitting: `variant.split("=")[0].strip()`. This gives the canonical variant name without the discriminant.

### Pitfall 5: `#[derive(...)]` Attributes Contaminate Enum/Struct Names

**What goes wrong:** The scanner module uses `#[derive(Debug, Clone, Copy, PartialEq, Eq)]` immediately before each enum. A regex that scans the whole ffi block for `enum (\w+)` may match `Eq` or produce incorrect group captures if the attribute is on the same line as the enum declaration.

**How to avoid:** Strip all `#[...]` attribute lines before running the enum/struct name regex. Or anchor the regex to `^\s*enum\s+` after splitting on newlines. The attribute is always on its own line.

### Pitfall 6: `build.rs` Has `#[cfg(windows)]` Guard

**What goes wrong:** The actual file list is inside `#[cfg(windows)] fn main()`. A parser that looks for `cxx_build::bridges` globally finds it (it's not conditional at the text level), but a strict parser that also requires `#[cfg(windows)]` context may get confused.

**How to avoid:** Parse `cxx_build::bridges([...])` globally with `re.DOTALL`. The `#[cfg(not(windows))]` variant of `main()` does NOT call `cxx_build::bridges()`, so the regex will only match the one call that contains the file list. No conditional parsing is needed.

### Pitfall 7: `parity-artifacts/` Is Not Yet Gitignored for the Bridge Crate

**What goes wrong:** Running the gate creates `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` which then appears as untracked in `git status`, polluting every subsequent status check.

**How to avoid:** Phase 1 must add `parity-artifacts/` to a `.gitignore` file at `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/.gitignore` OR append the path to `ClassicLib-rs/.gitignore`. Verified: the root `.gitignore` has no `parity-artifacts/` entry. The Node binding has `parity-artifacts/` in `ClassicLib-rs/node-bindings/classic-node/.gitignore`. The Python binding's parity-artifacts ARE committed (not gitignored). For CXX (D-08), parity-artifacts are ephemeral/gitignored — follow the Node pattern, not the Python pattern.

---

## `build.rs` Parser Robustness Cases

The actual `build.rs` content was read directly. Summary of cases the parser encounters:

| Case | Actual Content | Parser Requirement |
|------|---------------|-------------------|
| Multi-line array | 14 entries, one per line | `re.DOTALL` on the array body |
| Quoted string paths | `"src/types.rs"` | `re.findall(r'"([^"]+)"', body)` |
| Trailing comma on last entry | `"src/markdown.rs",` (has trailing comma) | `findall` handles this — extracts strings, ignores commas |
| `#[cfg(windows)]` wrapper | Entire call inside `#[cfg(windows)] fn main()` | Regex finds the call regardless; no parsing of cfg guards |
| Method chain after `]` | `.include("include").std("c++17").compile(...)` | Stop at `]` — the array ends there |
| `#[cfg(not(windows))]` second `main` | No `cxx_build::bridges` call | `re.search` finds only the one occurrence |
| Comments inside array | None present in current `build.rs` | Robustness: strip `//` line comments before parsing if ever needed |

---

## Gitignore Coverage Analysis

**Finding:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` is NOT currently covered by any `.gitignore` entry. Phase 1 MUST add it.

**Recommended approach:** Add a `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/.gitignore` file (matching the Node pattern) with content:
```
parity-artifacts/
```

**Alternative:** Append `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` to `ClassicLib-rs/.gitignore`. Either approach works; the local `.gitignore` approach matches the Node convention.

**Python parity-artifacts:** These ARE committed to git (verified: `git ls-files` shows 8 files tracked). The Python gate commits both `ClassicLib-rs/python-bindings/parity-artifacts/` files AND `docs/implementation/python_api_parity/baseline/` files.

**CXX pattern:** Per D-08, parity-artifacts in `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` are ephemeral/gitignored. The committed set lives only in `docs/implementation/cxx_api_parity/baseline/`. This differs from Python but matches the architecture decision.

---

## Baseline Artifact Location: ROADMAP.md vs CONTEXT.md

**ROADMAP.md** success criterion 3 states the baseline lives at `tools/cxx_api_parity/cxx_baseline_surface.json`.

**CONTEXT.md D-05** (which supersedes the roadmap) states the baseline lives at `docs/implementation/cxx_api_parity/baseline/parity_contract.json`.

**Resolution:** The planner MUST use `docs/implementation/cxx_api_parity/baseline/parity_contract.json` per D-05. The ROADMAP.md path is an earlier iteration. The CONTEXT.md is the authoritative locked decision.

---

## Existing Test Fixture Patterns

No `tools/python_api_parity/tests/` or `tools/node_api_parity/tests/` directory exists in the repo. The existing gates have no test fixtures. Phase 1 is the first parity gate to add tests.

**Recommended fixture approach** (Claude's discretion area from CONTEXT.md):

Create `tools/cxx_api_parity/tests/fixtures/` with minimal synthetic `.rs` files:
- `simple_ffi.rs`: one `#[cxx::bridge]` block, two functions in `extern "Rust"`, no types
- `struct_ffi.rs`: one shared struct with 3 fields + one function returning it
- `enum_ffi.rs`: one `#[derive(Debug)]` enum with 3 variants (no discriminants) + one variant with discriminants
- `opaque_ffi.rs`: one opaque type + two accessor functions
- `mixed_ffi.rs`: enum + struct + opaque type + `unsafe extern "C++"` type + extern Rust functions (mirrors scanner complexity)
- `fake_build.rs`: fake `build.rs` content with `cxx_build::bridges([...])` pointing to the fixture files

Test file `tools/cxx_api_parity/tests/test_parser.py` runs via the existing python-bindings venv: `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py`. **No venv at repo root** — the python-bindings venv is the only Python venv in the repo and is hand-managed via `ClassicLib-rs/python-bindings/requirements-ci.txt`.

---

## Contributor Doc Content (CXXG-05)

`docs/api/cxx-parity-gate.md` must document:

1. **How to run locally:** `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
2. **How to refresh the baseline after an intentional change:** `python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline && git add docs/implementation/cxx_api_parity/baseline/ && git commit -m "Docs: refresh CXX parity baseline"`
3. **How to bootstrap from scratch:** `python tools/cxx_api_parity/generate_baseline.py --repo-root .`
4. **What the contract row schema means:** describe each field (`id`, `rustSymbol`, `kind`, `bridgeModule`, `sourceFile`, `signature`/`fields`/`variants`)
5. **The relationship to `build.rs`:** single source of truth for which bridge files are gated; adding a new file to `build.rs` makes it visible to the gate on the next run
6. **The ephemeral vs committed artifact distinction:** `parity-artifacts/` is gitignored; `docs/implementation/cxx_api_parity/baseline/` is committed
7. **What CI does:** cxx-parity-gate job in `ci-cpp.yml` runs before `cli-tests` and `gui-tests`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python/Node gates with Tier-2 deferred backlog | CXX gate born single-tier, no Tier-2 concept | Phase 1 (this phase) establishes new pattern | No deferred-registry trap; born green |
| ROADMAP.md path `tools/cxx_api_parity/cxx_baseline_surface.json` | D-05 path `docs/implementation/cxx_api_parity/baseline/parity_contract.json` | During Context gathering (2026-04-06) | Planner must use D-05 path exclusively |
| No CXX surface gate | Phase 1 establishes gate | This milestone | All future bridge changes are gated |

---

## Runtime State Inventory

Step 2.5 SKIPPED: This is a new-file-creation phase with no rename/refactor/migration component. No runtime state to inventory.

---

## Environment Availability

Step 2.6: Phase 1 is purely code/config changes (Python scripts, JSON files, one `.gitignore` addition). No external build tools required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Gate scripts | Assumed (CI uses `setup-python 3.12`) | 3.12 | — |
| pytest 9.x | Gate tests | Already installed in `ClassicLib-rs/python-bindings/.venv` from `requirements-ci.txt` | — | If venv missing: `cd ClassicLib-rs/python-bindings && uv venv && uv pip install -r requirements-ci.txt` |

**No blocking dependencies.**

---

## Validation Architecture

`workflow.nyquist_validation: true` in `.planning/config.json` — this section is REQUIRED.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x (existing, from `ClassicLib-rs/python-bindings/.venv`; installed via `requirements-ci.txt`) |
| Config file | None detected for `tools/` — needs `tools/cxx_api_parity/tests/` directory. No `pyproject.toml` at repo root; **no venv allowed at repo root**. |
| Quick run command | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/ -q` |
| Full suite command | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CXXG-01 | `parse_cxx_bridge_surface()` extracts functions from `extern "Rust"` | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_extern_rust_functions -x` | ❌ Wave 0 |
| CXXG-01 | `parse_cxx_bridge_surface()` extracts shared structs with fields | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_shared_structs -x` | ❌ Wave 0 |
| CXXG-01 | `parse_cxx_bridge_surface()` extracts enums with variants (including discriminants) | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_enums -x` | ❌ Wave 0 |
| CXXG-01 | `parse_cxx_bridge_surface()` extracts opaque types | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_opaque_types -x` | ❌ Wave 0 |
| CXXG-01 | `parse_cxx_bridge_surface()` handles `unsafe extern "C++"` block | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_extern_cpp -x` | ❌ Wave 0 |
| CXXG-01 | `parse_build_rs_file_list()` extracts file list from multi-line `cxx_build::bridges([...])` | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_build_rs -x` | ❌ Wave 0 |
| CXXG-01 | `parse_build_rs_file_list()` exits non-zero if `cxx_build::bridges` not found | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::test_build_rs_missing_bridges -x` | ❌ Wave 0 |
| CXXG-01 | Parser produces deterministic JSON (sorted entries, stable id hashes) | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::test_deterministic_output -x` | ❌ Wave 0 |
| CXXG-02 | Generated baseline at `docs/implementation/cxx_api_parity/baseline/parity_contract.json` exists after `generate_baseline.py` run | integration | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::test_baseline_file_exists -x` | ❌ Wave 0 |
| CXXG-02 | Baseline contains all 14 bridge modules | integration | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::test_baseline_covers_14_modules -x` | ❌ Wave 0 |
| CXXG-03 | `check_parity_gate.py` exits 0 on unchanged source (born green) | integration/smoke | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_passes_on_unchanged_source -x` | ❌ Wave 0 |
| CXXG-03 | `check_parity_gate.py` exits 1 when a function is added to a bridge file (not in baseline) | drift detection | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_fails_on_added_function -x` | ❌ Wave 0 |
| CXXG-03 | `check_parity_gate.py` exits 1 when a function is removed from a bridge file | drift detection | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_fails_on_removed_function -x` | ❌ Wave 0 |
| CXXG-03 | `check_parity_gate.py` exits 1 when a struct field is renamed | drift detection | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_fails_on_struct_field_rename -x` | ❌ Wave 0 |
| CXXG-03 | `check_parity_gate.py` exits 1 when committed baseline artifacts are stale | stale-artifact | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_fails_on_stale_artifact -x` | ❌ Wave 0 |
| CXXG-04 | `check_parity_gate.py` has no `--deferred-registry` argument | CLI surface | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::test_no_deferred_registry_arg -x` | ❌ Wave 0 |
| CXXG-04 | Gate exits cleanly (pass or fail for drift, never crash) with minimal args | smoke | `python tools/cxx_api_parity/check_parity_gate.py --repo-root . --help` exits 0 | ❌ Wave 0 |

### Parser Determinism Guarantees

For the freshness gate (D-14) to work, `parse_cxx_bridge_surface()` MUST produce byte-identical JSON output on repeated runs against an unchanged source tree. The following properties must be deterministic:

| Property | How to Guarantee |
|----------|-----------------|
| Entry order | Sort `entries` list by `(bridgeModule, kind, rustSymbol)` before serializing |
| `id` field | `hashlib.sha256(f"{rustSymbol}:{kind}:{bridgeModule}".encode()).hexdigest()[:16]` — deterministic hash |
| `fields` list order | Preserve declaration order from source (regex extraction order = source order) |
| `variants` list order | Preserve declaration order from source |
| `signature` normalization | Normalize whitespace: `re.sub(r'\s+', ' ', sig).strip()` — collapse internal whitespace |
| JSON key order | Fix by always building row dicts with the same key insertion order in code |
| `generated_at_utc` | Present in root object but excluded from `artifacts_match()` comparison |

### Drift Detection Cases (must be testable)

| Case | How Gate Detects It | Exit Code |
|------|--------------------|-----------| 
| Function added to bridge file | Symbol in fresh surface, not in baseline `entries` | 1 |
| Function removed from bridge file | Symbol in baseline `entries`, not in fresh surface | 1 |
| Function signature changed | Symbol found in both but `signature` field differs | 1 |
| Struct field renamed | Symbol found in both but `fields` list differs | 1 |
| Struct field type changed | Symbol found in both but `fields` list item type differs | 1 |
| New struct added | Symbol in fresh surface `kind=struct`, not in baseline | 1 |
| Struct removed | Symbol in baseline `kind=struct`, not in fresh surface | 1 |
| Enum variant added | Symbol found in both `kind=enum` but `variants` list differs | 1 |
| New opaque type added | Symbol in fresh surface `kind=opaque`, not in baseline | 1 |
| New bridge file added to `build.rs` | All symbols from new file absent from baseline | 1 |
| Committed baseline stale | `artifacts_match(baseline/file, parity-artifacts/file)` returns False | 1 |

### Exit Code Semantics

| Exit Code | Meaning | Condition |
|-----------|---------|-----------|
| 0 | Gate passed | Fresh surface matches baseline; no stale artifacts |
| 1 | Drift detected | `drift_count > 0` (missing or changed entries) |
| 1 | Stale artifacts | `stale_artifacts` list non-empty |
| 1 | Parser error | `build.rs` parse failed; gate cannot enumerate files |
| 1 | Missing baseline | `parity_contract.json` not found at `--contract` path |

CI can distinguish "drift" from "stale" from "error" by reading stdout (the gate prints a diagnostic line before returning 1). All non-zero exits block the `cli-tests` and `gui-tests` jobs.

### `--deferred-registry` Absence Test

The CXXG-04 requirement (no deferred-registry trap) is testable by inspecting the gate's argparse definition:

```python
# Test: verify --deferred-registry is NOT a registered argument
import subprocess, sys
result = subprocess.run(
    [sys.executable, "tools/cxx_api_parity/check_parity_gate.py", "--help"],
    capture_output=True, text=True
)
assert "--deferred-registry" not in result.stdout
assert result.returncode == 0
```

### Freshness Check Semantics

The freshness check in `check_parity_gate.py` compares the committed baseline artifacts against a fresh run. The comparison logic:

1. Run `parse_cxx_bridge_surface()` against current source
2. Generate fresh artifacts into `parity-artifacts/`
3. For each artifact in `tracked_artifact_names`:
   - If `.json`: pop `generated_at_utc` from both and compare with `==`
   - If `.md`: skip lines starting with `- Generated:` before comparing
4. If any artifact differs: append to `stale_artifacts` list
5. If `stale_artifacts` non-empty: exit 1

This means the committed baseline JSON must be byte-identical to a fresh parse (modulo timestamp) when the source is unchanged. The parser determinism guarantees above are what make this possible.

### Wave 0 Gaps

All test files and fixtures need to be created in Wave 0 before implementation:

- [ ] `tools/cxx_api_parity/tests/__init__.py` — makes tests directory a package
- [ ] `tools/cxx_api_parity/tests/test_parser.py` — covers CXXG-01 parser unit tests
- [ ] `tools/cxx_api_parity/tests/test_gate.py` — covers CXXG-02, CXXG-03, CXXG-04
- [ ] `tools/cxx_api_parity/tests/fixtures/simple_ffi.rs` — minimal extern "Rust" fixture
- [ ] `tools/cxx_api_parity/tests/fixtures/struct_ffi.rs` — shared struct fixture
- [ ] `tools/cxx_api_parity/tests/fixtures/enum_ffi.rs` — enum with #[derive] and discriminants
- [ ] `tools/cxx_api_parity/tests/fixtures/opaque_ffi.rs` — opaque type fixture
- [ ] `tools/cxx_api_parity/tests/fixtures/mixed_ffi.rs` — scanner-like complex fixture
- [ ] `tools/cxx_api_parity/tests/fixtures/fake_build.rs` — fake build.rs for unit tests

---

## Open Questions

1. **`kind` field value for `extern "C++"` items**
   - What we know: D-03 specifies `kind: "function" | "struct" | "enum" | "opaque"` for `extern "Rust"` items. The scanner's `unsafe extern "C++"` block has `ScanBatchProgressCallback` (a C++ type) and `on_batch_progress` (a C++ function).
   - What's unclear: Should C++ items use a separate `kind` value (`"cxx_type"`, `"cxx_function"`) or the same kind values but with an additional `extern: "C++"` field?
   - Recommendation: Add a `blockOrigin: "Rust" | "C++"` field (or `extern: "Rust" | "C++"`) so the planner can distinguish them without changing the kind taxonomy. Default `"Rust"` for all `extern "Rust"` items.

2. **`include!()` macro in `unsafe extern "C++"` block**
   - What we know: `include!("classic_cxx_bridge/scan_progress_callback.h")` appears inside the `unsafe extern "C++"` block. It's not a function or type declaration.
   - What's unclear: Should the gate record the `include!()` as a contract item?
   - Recommendation: Ignore `include!(...)` lines during parsing. They are file inclusion directives, not API declarations. Only parse `type` and `fn` lines inside the block.

---

## Sources

### Primary (HIGH confidence)

All findings sourced directly from committed repo files — no external research needed.

- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` — confirmed 14-file list, multi-line array form, `#[cfg(windows)]` wrapper
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/types.rs` — opaque type + function-accessor pattern
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` — minimal shared struct pattern
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/runtime.rs` — function-only, no types
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` — most complex: enums with `#[derive]` + discriminants, `unsafe extern "C++"` block, multi-arg functions
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` — `Box<T>` and `Result<()>` return types
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` — nested struct field types, `&str` return type, 33 functions
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs` — `&mut YamlOps` pattern, `Result<String>` return
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` — function-only, 11 functions
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/files.rs` — 3 opaque types, `Result<bool>`, `Result<u32>` variants
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/perf.rs` — function-only, no types
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/markdown.rs` — simplest function-only module
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/message.rs` — function-only, multi-param including u32
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/update.rs` — simple struct + 2 functions
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` — 5 structs, 11 functions, no opaque types
- `tools/python_api_parity/check_parity_gate.py` — argparse layout, `artifacts_match()`, `sync_baseline_artifacts()`, exit-code semantics, stale-artifact detection (verbatim)
- `tools/python_api_parity/generate_baseline.py` — `parse_rust_surface()` helper, `write_json()`, `render_diff_markdown()` patterns
- `tools/node_api_parity/check_parity_gate.py` — cross-check confirms identical structural skeleton
- `tools/node_api_parity/generate_baseline.py` — `RUST_TARGET_CRATES` dict pattern
- `tools/binding_parity_runtime_coverage.py` — location confirmed at `tools/` root; `load_json_file()` signature; `sys.path.append` pattern for import
- `.gitignore` — confirmed no `parity-artifacts/` entry at root
- `ClassicLib-rs/node-bindings/classic-node/.gitignore` — confirmed `parity-artifacts/` pattern in local gitignore
- `ClassicLib-rs/python-bindings/parity-artifacts/` — confirmed committed (8 tracked files via `git ls-files`)
- `docs/implementation/python_api_parity/baseline/` — confirmed committed baseline directory with 8 files
- `.planning/config.json` — confirmed `workflow.nyquist_validation: true`
- `.planning/phases/01-cxx-parity-gate-tooling/01-CONTEXT.md` — 16 locked decisions, Claude's discretion areas, deferred ideas

---

## Metadata

**Confidence breakdown:**
- Bridge syntax patterns: HIGH — all 14 files read directly
- Script skeleton structure: HIGH — Python and Node gate scripts read verbatim
- `build.rs` parsing: HIGH — file read directly, regex approach verified
- Gitignore gaps: HIGH — `.gitignore` read directly, git ls-files run
- Baseline artifact location discrepancy: HIGH — both ROADMAP.md and CONTEXT.md read directly; D-05 is authoritative
- Test infrastructure: MEDIUM — no existing tests in `tools/` to mirror; test layout is planner's discretion area

**Research date:** 2026-04-06
**Valid until:** Stable (bridge source files and Python gate skeleton change only with deliberate phase work — no fast-moving external dependencies)
