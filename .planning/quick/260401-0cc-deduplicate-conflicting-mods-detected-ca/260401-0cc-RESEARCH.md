# Quick Task: Deduplicate "Conflicting mods detected" Header - Research

**Researched:** 2026-03-31
**Domain:** classic-scanlog-core / mod_detector.rs
**Confidence:** HIGH

## Summary

The `[!] CAUTION : Conflicting mods detected` header string is pushed inside the `for entry in entries` loop at line 444 of `mod_detector.rs`, causing it to repeat for every detected conflict pair. The fix is to move it before the loop, emitting it once only if at least one conflict is found.

**Primary recommendation:** Use a `header_emitted` boolean flag (or collect conflicts first, then prepend header if non-empty) to emit the header exactly once.

## Bug Location

**File:** `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`
**Function:** `detect_mods_double()` (line 407-459)
**Bug:** Line 444 -- `lines.push("[!] CAUTION : Conflicting mods detected\n".to_string())` is inside the `for entry in entries` loop body (lines 439-456), so it repeats per conflict.

### Current code (lines 439-456):

```rust
for entry in entries {
    let a_lower = entry.mod_a.to_lowercase();
    let b_lower = entry.mod_b.to_lowercase();

    if mods_present.contains(&a_lower) && mods_present.contains(&b_lower) {
        lines.push("[!] CAUTION : Conflicting mods detected\n".to_string());  // BUG: repeated
        lines.push(format!(
            "{} :: CONFLICTS WITH : {}\n",
            entry.name_a, entry.name_b
        ));
        lines.push(format!("    {}\n", entry.description));
        lines.push(format!("    {}\n", entry.fix));
        if let Some(link) = &entry.link {
            lines.push(format!("    Link: {}\n", link));
        }
        lines.push("    -----\n\n".to_string());
    }
}
```

## Callers

| Caller | File | How it uses the output |
|--------|------|------------------------|
| `OrchestratorCore::analyze_log` | `orchestrator.rs:1322-1332` | Wraps non-empty output with `generate_mod_check_header("May Conflict With Each Other")` section header, then appends as `ReportFragment::from_lines(conflict_lines)` |
| `FormIDAnalyzerCore::detect_mods_conflicts` | `formid_analyzer.rs:518-523` | Thin delegation wrapper; returns `Vec<String>` directly. Not called from production orchestrator. |
| Python binding `detect_mods_double` | `python-bindings/classic-scanlog-py/src/mod_detector.rs:37-70` | Thin PyO3 wrapper; delegates to `classic_scanlog_core::detect_mods_double()`, returns `Vec<String>` |

**Key observation:** The orchestrator already adds a section-level header (`### Checking For Mods That May Conflict With Each Other`). The per-conflict `[!] CAUTION` header is a per-entry annotation. With the fix, it will appear once at the top of the conflict list, before any individual conflict detail blocks.

## Existing Tests That Touch This Code

All tests are in `mod_detector.rs` inline `#[cfg(test)] mod tests` (starting line 752).

| Test | What it asserts | Impact of fix |
|------|----------------|---------------|
| `test_detect_mods_double_empty` | Result is empty | No impact |
| `test_detect_mods_double_no_conflict` | Result is empty (only one mod present) | No impact |
| `test_detect_mods_double_conflict_detected` | `output.contains("CAUTION")` and `output.contains("CONFLICTS WITH")` | Still passes -- header still present, just once |
| `test_detect_mods_double_case_insensitive` | Result is non-empty | No impact |
| `test_detect_mods_double_with_link` | Contains link URL | No impact |

**No test asserts on the count of CAUTION headers.** All assertions use `contains()` which remains true whether the header appears once or N times. The existing tests will pass without modification.

**New test needed:** A test with multiple conflict entries (2+ conflicts detected simultaneously) that asserts the CAUTION header appears exactly once.

## Recommended Fix

**Approach: `header_emitted` flag pattern** -- simplest, no structural change to the loop.

```rust
let mut header_emitted = false;
for entry in entries {
    let a_lower = entry.mod_a.to_lowercase();
    let b_lower = entry.mod_b.to_lowercase();

    if mods_present.contains(&a_lower) && mods_present.contains(&b_lower) {
        if !header_emitted {
            lines.push("[!] CAUTION : Conflicting mods detected\n".to_string());
            header_emitted = true;
        }
        lines.push(format!(
            "{} :: CONFLICTS WITH : {}\n",
            entry.name_a, entry.name_b
        ));
        lines.push(format!("    {}\n", entry.description));
        lines.push(format!("    {}\n", entry.fix));
        if let Some(link) = &entry.link {
            lines.push(format!("    Link: {}\n", link));
        }
        lines.push("    -----\n\n".to_string());
    }
}
```

**Why not "collect then prepend":** The flag approach preserves the current single-pass structure. A collect-then-prepend approach would work too but requires an intermediate buffer or `Vec::insert(0, ...)` which is O(n) on the vec.

## Documentation Updates Needed

The docstring at lines 361-366 says:

> Each conflict report includes:
> - "[!] CAUTION : Conflicting mods detected" header

This should be updated to clarify the header appears once at the top of the section, not per conflict.

## Project Constraints (from CLAUDE.md)

- Test commands: `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- Formatting: `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml`
- Clippy: `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings`
- Commit prefix: `Fix:` (this is a bug fix)
- Never output to `nul` on Windows
- When writing tests, verify the APIs of what is being tested

## Validation

Run after fix:
```bash
cargo test --manifest-path ClassicLib-rs/Cargo.toml -p classic-scanlog-core -- detect_mods_double
```

## Sources

### Primary (HIGH confidence)
- Direct source code inspection of `mod_detector.rs` lines 340-459 and 1045-1127
- Direct source code inspection of `orchestrator.rs` lines 1318-1333
- Direct source code inspection of `formid_analyzer.rs` lines 518-523
