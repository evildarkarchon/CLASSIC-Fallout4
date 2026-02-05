---
phase: quick-001
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - rust/business-logic/classic-registry-core/src/keys.rs
  - rust/business-logic/classic-registry-core/src/registry.rs
  - rust/business-logic/classic-yaml-core/src/lib.rs
  - rust/business-logic/classic-yaml-core/src/merge.rs
  - rust/foundation/classic-shared-py/src/indexmap_utils.rs
autonomous: true

must_haves:
  truths:
    - "cargo doc --workspace --no-deps produces zero warnings"
    - "All doc links resolve correctly"
    - "All code examples are valid or properly marked"
  artifacts:
    - path: "rust/business-logic/classic-registry-core/src/keys.rs"
      provides: "Fixed doc link references"
    - path: "rust/business-logic/classic-yaml-core/src/lib.rs"
      provides: "Fixed empty code blocks and HTML escaping"
  key_links: []
---

<objective>
Fix all Rust documentation warnings in the workspace.

Purpose: Ensure clean cargo doc output with zero warnings, improving code quality and documentation correctness.

Output: All documentation warnings resolved across classic-registry-core, classic-yaml-core, and classic-shared-py crates.
</objective>

<context>
Current warnings from `cargo doc --workspace --no-deps`:

**classic-registry-core (5 warnings):**
- Unresolved link to `Fallout4Version` in keys.rs:68, 88 and registry.rs:263, 296
- Unresolved link to `GAME_VERSION` in keys.rs:110

**classic-yaml-core (9 warnings):**
- Empty Rust code blocks in lib.rs:576, 608, 676, 832, 877 (placeholder examples)
- URL not a hyperlink in merge.rs:3, 49 (bare http://yaml.org URLs)
- Unclosed HTML tag `<String>` in lib.rs:1368, 1371

**classic-shared-py (1 warning):**
- Unclosed HTML tag `<String>` in indexmap_utils.rs:162
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix unresolved doc links in classic-registry-core</name>
  <files>
    rust/business-logic/classic-registry-core/src/keys.rs
    rust/business-logic/classic-registry-core/src/registry.rs
  </files>
  <action>
Fix doc link references that don't resolve:

1. In keys.rs (lines 68, 88, 110):
   - Replace `[`Fallout4Version`]` with backtick-escaped version: `` `Fallout4Version` `` (no brackets, just backticks)
   - Replace `[`GAME_VERSION`]` with `` `GAME_VERSION` `` or `[`Keys::GAME_VERSION`]` if the link should work
   - The Fallout4Version type is in classic-constants-core, not in scope for intra-doc links

2. In registry.rs (lines 263, 296):
   - Same fix: replace `[`Fallout4Version`]` with `` `Fallout4Version` ``

The pattern: When referencing types not in the current crate's public API, use backticks without brackets to render as code without attempting link resolution.
  </action>
  <verify>
Run: `cd rust && cargo doc -p classic-registry-core --no-deps 2>&1 | grep -i warning`
Expected: No output (zero warnings)
  </verify>
  <done>classic-registry-core produces zero documentation warnings</done>
</task>

<task type="auto">
  <name>Task 2: Fix documentation issues in classic-yaml-core</name>
  <files>
    rust/business-logic/classic-yaml-core/src/lib.rs
    rust/business-logic/classic-yaml-core/src/merge.rs
  </files>
  <action>
Fix three categories of warnings:

1. **Empty code blocks** (lib.rs lines 576, 608, 676, 832, 877):
   Each has pattern:
   ```rust,ignore
   // This example uses placeholder types
   ```

   Either:
   - Remove the empty code block entirely and the "# Example" header if no example is needed
   - OR replace with actual working examples
   - OR change to `text` block instead of `rust,ignore` if keeping placeholder text

   Recommended: Remove the empty placeholder blocks since they add no value.

2. **Bare URLs** (merge.rs lines 3, 49):
   Change `http://yaml.org/type/merge.html` to `<http://yaml.org/type/merge.html>` with angle brackets to make them proper hyperlinks.

3. **Unclosed HTML tags** (lib.rs lines 1368, 1371):
   The text `Vec<String>` is being interpreted as HTML. Escape the angle brackets:
   - Change `Vec<String>` to `` `Vec<String>` `` (wrap in backticks)
   - This renders it as code and prevents HTML interpretation
  </action>
  <verify>
Run: `cd rust && cargo doc -p classic-yaml-core --no-deps 2>&1 | grep -i warning`
Expected: No output (zero warnings)
  </verify>
  <done>classic-yaml-core produces zero documentation warnings</done>
</task>

<task type="auto">
  <name>Task 3: Fix HTML tag warning in classic-shared-py</name>
  <files>
    rust/foundation/classic-shared-py/src/indexmap_utils.rs
  </files>
  <action>
Fix the unclosed HTML tag warning at line 162:

The doc comment contains `Vec<String>` which rustdoc interprets as an HTML tag.

Solution: Wrap in backticks to render as code:
- Change any `Vec<String>` in doc comments to `` `Vec<String>` ``

Check the surrounding context for any other instances of generic types in doc comments that need escaping.
  </action>
  <verify>
Run: `cd rust && cargo doc -p classic-shared-py --no-deps 2>&1 | grep -i warning`
Expected: No output (zero warnings)
  </verify>
  <done>classic-shared-py produces zero documentation warnings</done>
</task>

</tasks>

<verification>
Run full workspace documentation build:
```bash
cd rust && cargo doc --workspace --no-deps 2>&1 | grep -i warning
```

Expected: No warning lines in output.

Alternative full check:
```bash
cd rust && cargo doc --workspace --no-deps 2>&1 | grep -c warning
```
Expected: 0
</verification>

<success_criteria>
- `cargo doc --workspace --no-deps` produces zero warnings
- All 15 documentation warnings (5 + 9 + 1) are resolved
- Documentation content remains accurate and useful
- No new warnings introduced
</success_criteria>

<output>
After completion, verify with `cargo doc --workspace --no-deps` and confirm zero warnings.
</output>
