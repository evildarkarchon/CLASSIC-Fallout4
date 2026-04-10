---
phase: 01-cxx-parity-gate-tooling
plan: 01
subsystem: tooling
tags: [cxx, parity-gate, parser, python, regex, tdd]

# Dependency graph
requires:
  - phase: 01-cxx-parity-gate-tooling
    provides: 01-CONTEXT.md decisions D-01..D-07; 01-RESEARCH.md parser patterns and pitfalls
provides:
  - tools/cxx_api_parity/ Python package scaffolding (__init__.py, tests/__init__.py)
  - tools/cxx_api_parity/generate_baseline.py — parse_cxx_bridge_surface() + parse_build_rs_file_list() + extract_ffi_block() + write_json() + CLI entrypoint
  - tools/cxx_api_parity/tests/ — conftest.py and 9 pytest unit tests covering all 7 syntactic pitfalls
  - 6 fixture .rs files (simple, struct, enum, opaque, mixed, fake_build) covering every CXX bridge syntactic pattern in the real 14-file surface
  - Verified parser produces 202-entry deterministic JSON over the real 14-file bridge surface
affects: [01-02 (gate scripts wrap this parser), 01-03 (CI integration), 02 cxx-bridge-narrowing-closure (uses gate as acceptance criterion)]

# Tech tracking
tech-stack:
  added: [pure stdlib Python (re, hashlib, json, argparse) — no new third-party deps]
  patterns:
    - "Regex + brace-counter hybrid parser (regex finds candidates, brace counter resolves balanced bodies)"
    - "Top-level comma split helper (_split_top_level_commas) for compound type field parsing"
    - "Deterministic JSON output: sorted entries + sha256[:16] ids + stable dict insertion order"
    - "TDD with synthetic fixture .rs files reflecting every real-world bridge syntactic pattern"

key-files:
  created:
    - tools/cxx_api_parity/__init__.py
    - tools/cxx_api_parity/generate_baseline.py
    - tools/cxx_api_parity/tests/__init__.py
    - tools/cxx_api_parity/tests/conftest.py
    - tools/cxx_api_parity/tests/test_parser.py
    - tools/cxx_api_parity/tests/fixtures/simple_ffi.rs
    - tools/cxx_api_parity/tests/fixtures/struct_ffi.rs
    - tools/cxx_api_parity/tests/fixtures/enum_ffi.rs
    - tools/cxx_api_parity/tests/fixtures/opaque_ffi.rs
    - tools/cxx_api_parity/tests/fixtures/mixed_ffi.rs
    - tools/cxx_api_parity/tests/fixtures/fake_build.rs
  modified: []

key-decisions:
  - "Use regex + balanced-brace counter hybrid (NOT pure regex) so nested struct field blocks and extern blocks do not break parser; matches the parser pattern in 01-RESEARCH.md."
  - "Skip struct/enum names that fall inside extern blocks (via pre-computed extern_spans) so cxx shared types and extern items do not get cross-attributed."
  - "Strip include!() macros via _INCLUDE_MACRO_RE BEFORE function/opaque scanning so include!(\"foo.h\") inside unsafe extern \"C++\" never becomes a contract row (Pitfall 7)."
  - "Strip enum discriminants by splitting each variant on '=' (Pitfall 4)."
  - "Strip top-level #[derive(...)] attribute LINES (not bracket-internal content) before struct/enum name regex (Pitfall 5)."
  - "Use sha256(f'{rustSymbol}:{kind}:{bridgeModule}')[:16] for the deterministic id field per RESEARCH.md line 808."
  - "Sort entries by (bridgeModule, kind, rustSymbol) for byte-identical output across runs (Determinism Guarantee)."
  - "When fixture filename and intended bridgeModule differ (mixed_ffi.rs -> bridgeModule 'mixed'), the synthetic build.rs in the test installs the fixture file at src/<bridgeModule>.rs so the documented 'bridgeModule = filename stem' rule keeps holding."

patterns-established:
  - "Synthetic bridge crate per test: each test creates a tmp_path/bridge/{build.rs, src/<file>.rs} layout, writes a single-file cxx_build::bridges([...]) call, then invokes parse_cxx_bridge_surface(tmp_path, 'bridge'). This isolates each parser unit test from every other test and from the real 14-file surface."
  - "All output dicts constructed with the SAME key insertion order (id -> rustSymbol -> kind -> bridgeModule -> sourceFile -> blockOrigin -> [signature|fields|variants]) so JSON output is deterministic across runs."

requirements-completed: [CXXG-01]

# Metrics
duration: 6min
completed: 2026-04-07
---

# Phase 01 Plan 01: TDD Parser for CXX Bridge Surface Summary

**Pure-stdlib Python parser extracts every extern Rust function, shared struct (with ordered fields), shared enum (with discriminants stripped), opaque type, and unsafe extern "C++" item from any `#[cxx::bridge]` source file enumerated by build.rs, producing a 202-entry deterministic surface inventory across the real 14-file bridge crate.**

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | RED — scaffolding + fixtures + 9 failing parser tests | f1737c74 | 11 created (package + 6 fixtures + conftest + test_parser.py + stub generate_baseline.py) |
| 2 | GREEN — implement parse_cxx_bridge_surface + helpers | a5a398c3 | 2 modified (generate_baseline.py implementation; test_parser.py inline test bug fix) |

## Parser Architecture

```
parse_cxx_bridge_surface(repo_root, bridge_crate_rel)
  -> read build.rs -> parse_build_rs_file_list() -> [files]
  -> for each file: read source -> extract_ffi_block() -> ffi body
  -> _parse_ffi_body(ffi_body, bridgeModule, sourceFile):
       _find_top_level_blocks("struct") -> _parse_struct_fields() -> struct rows
       _find_top_level_blocks("enum") -> _parse_enum_variants() -> enum rows
       _find_extern_blocks() -> per block:
         strip include!() macros
         _OPAQUE_TYPE_RE.finditer() -> opaque rows
         _FUNCTION_RE.finditer() -> _parse_function_signature() -> function rows
  -> sort by (bridgeModule, kind, rustSymbol)
  -> { generated_at_utc, entries: [...] }
```

The parser uses regex to find candidate matches (extern block opening, struct/enum keywords, function signatures, opaque type declarations) but always falls back to a brace-depth counter (`_find_balanced_block`) for any item that contains a balanced `{ ... }` body. This is the pattern explicitly recommended in 01-RESEARCH.md §"CXX Bridge Source Parser Pattern" because pure-regex parsing of nested braces is unsound.

## Pitfalls Handled (from 01-RESEARCH.md §Common Pitfalls)

| # | Pitfall | Handling |
|---|---------|----------|
| 1 | `mod ffi { ... }` brace balancing | `extract_ffi_block()` uses a brace-depth counter starting at the `{` after `mod ffi`, walks until depth returns to zero. |
| 2 | `extern "C++"` items parsed alongside `extern "Rust"` items | `_find_extern_blocks()` finds both pattern types and tags each block with `blockOrigin="Rust"` or `"C++"` for downstream attribution. |
| 3 | Compound struct field types (`Vec<String>`, nested struct refs) | `_split_top_level_commas()` is angle-bracket aware, so `tags: Vec<String>` survives; `_normalize_ws` collapses whitespace inside the type string. Real-bridge sample: `BatchProgressEvent.fields[0]` = `{name: "completed", type: "u32"}`. |
| 4 | Enum variants with discriminants (`Queued = 0` -> `Queued`) | `_parse_enum_variants` splits each variant on `=` and keeps only the LHS; the resulting name is then validated with `^[A-Za-z_][A-Za-z0-9_]*$` so non-identifier garbage is rejected. |
| 5 | `#[derive(...)]` lines contaminating struct/enum name regex | `_ATTR_LINE_RE` strips entire `#[ ... ]` lines (whole-line match anchored with `^` and `\r?\n`) before the struct/enum scan. The test asserts no `Debug`/`Clone`/`Copy`/`PartialEq`/`Eq` rows ever appear in the output. |
| 6 | `build.rs` `#[cfg(windows)]` wrapper | `_BRIDGES_RE` is a single re.search with re.DOTALL — it finds the `cxx_build::bridges([...])` call regardless of where it sits in the file. |
| 7 | `include!("...")` is NOT a contract row | `_INCLUDE_MACRO_RE.sub("")` runs BEFORE the opaque-type and function scans inside each extern block body. The `test_parse_extern_cpp` test asserts no row's `rustSymbol` contains `"fake_header"` or `"include"`. |

## Real 14-File Bridge Surface Counts

After Task 2, `python tools/cxx_api_parity/generate_baseline.py --repo-root .` produces 202 entries across all 14 modules:

| bridgeModule | entries |
|--------------|---------|
| config       | 47      |
| files        | 28      |
| scanner      | 26      |
| game         | 19      |
| yaml         | 19      |
| registry     | 14      |
| types        | 13      |
| database     | 10      |
| message      | 9       |
| perf         | 5       |
| scangame     | 4       |
| markdown     | 2       |
| runtime      | 3       |
| update       | 3       |

Kind breakdown: 169 functions, 19 structs, 12 opaque types, 2 enums.

This is a SANITY SIGNAL for Plan 02 — the Plan 02 baseline commit should produce the same totals (modulo any subsequent bridge edits). All 14 modules from `build.rs` are represented; no module returned zero entries.

## Real-Surface Edge Cases Confirmed

The fixtures already cover every syntactic pattern the parser actually encountered when run against the real 14 files. No fixture-uncovered surprises were found in the real surface scan:

- `BatchProgressEventKind` (scanner.rs): enum with discriminants 0..4 — variants correctly stripped to `["Queued","Started","Phase","Completed","Failed"]`.
- `BatchProgressEvent` (scanner.rs): struct with compound field types and an enum field reference — fields preserved in order.
- `ScanBatchProgressCallback` + `on_batch_progress` (scanner.rs): C++ opaque type + C++ function inside `unsafe extern "C++" { ... }` block — both correctly tagged `blockOrigin="C++"`.
- `YamlData` (config.rs): opaque type inside extern Rust block — correctly emitted with no signature/fields/variants keys.
- `config` module's 47 entries (largest in the bridge): nested struct field types referencing other DTOs (e.g. `criteria: YamlDataModSolutionCriteria`) parse without contamination.

## Determinism Verification

`parse_cxx_bridge_surface()` was called twice against the real bridge surface in succession; after popping `generated_at_utc` from each payload, the two dicts compared equal. First/last entries by sort order:

- First: `('config', 'function', 'reset_settings_cache_stats')`
- Last: `('yaml', 'struct', 'YamlValue')`

The id field for every row matches `sha256(f"{rustSymbol}:{kind}:{bridgeModule}".encode())[:16]` (verified by `test_deterministic_output`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture path mismatch in `test_parse_extern_cpp` and `test_parse_mixed_ffi_complete_inventory`**

- **Found during:** Task 2 (running pytest after writing the parser implementation)
- **Issue:** The plan's verbatim test code installed the `mixed_ffi.rs` fixture at `src/mixed_ffi.rs` inside the synthetic bridge crate, which made the parser return rows with `bridgeModule="mixed_ffi"` (the filename stem). But both tests assert tuples like `("mixed", "opaque", "ScanProgressCallback")` — they expect `bridgeModule="mixed"` (matching the fixture's `namespace = "classic::mixed"`). This is a contradiction with the documented "bridgeModule = filename stem" rule that the parser otherwise correctly implements (and which the determinism test relies on).
- **Fix:** Changed both failing tests to install the `mixed_ffi.rs` fixture at `src/mixed.rs` inside the synthetic bridge crate. This keeps the "filename stem" rule intact AND makes the test assertions work. No parser logic was changed.
- **Files modified:** `tools/cxx_api_parity/tests/test_parser.py` (2 hunks)
- **Commit:** a5a398c3 (folded into the GREEN commit)

### Out-of-Scope Discoveries

None. The plan exactly matched the real-world bridge surface — the fixtures covered every syntactic pattern that occurred in the 202-entry real-surface scan.

## Authentication Gates

None.

## Self-Check: PASSED

- Created files exist (verified post-commit):
  - `tools/cxx_api_parity/__init__.py` FOUND
  - `tools/cxx_api_parity/generate_baseline.py` FOUND
  - `tools/cxx_api_parity/tests/__init__.py` FOUND
  - `tools/cxx_api_parity/tests/conftest.py` FOUND
  - `tools/cxx_api_parity/tests/test_parser.py` FOUND
  - `tools/cxx_api_parity/tests/fixtures/{simple,struct,enum,opaque,mixed,fake_build}_ffi.rs` (6 fixtures) FOUND — note: fake_build.rs not _ffi.rs
- Commits exist on current branch:
  - `f1737c74` (RED) FOUND
  - `a5a398c3` (GREEN) FOUND
- All 9 parser unit tests PASS in 0.06s
- Real 14-file bridge produces 202 deterministic entries across all 14 modules
