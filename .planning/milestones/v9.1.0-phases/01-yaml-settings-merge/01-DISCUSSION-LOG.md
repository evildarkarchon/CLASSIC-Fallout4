# Phase 1: YAML -> Settings Merge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 01-yaml-settings-merge
**Areas discussed:** Module layout, CacheStats collision, Re-export strategy, Binding crate fate, Test & bench migration, API doc consolidation, Parity gate timing, Python pyi stub update, Binding test updates, Cross-reference cleanup, Git history strategy

---

## Module layout

| Option | Description | Selected |
|--------|-------------|----------|
| New submodules | Add yaml_ops.rs and yaml_merge.rs alongside existing modules | ✓ |
| Merge into existing | Fold yaml-core's code into existing loader.rs and cache.rs | |
| Single yaml module | All yaml-core code as one yaml.rs or yaml/ directory | |

**User's choice:** New submodules (Recommended)
**Notes:** Keeps existing settings-core modules untouched, clear separation of absorbed code.

---

## Error type handling

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both, re-export both | YamlError in yaml_ops.rs, SettingsError in error.rs, both at crate root | ✓ |
| Merge into one error enum | Combine all variants into single SettingsError | |
| YamlError wraps into SettingsError | Add YamlError variant to SettingsError, type alias for compat | |

**User's choice:** Keep both, re-export both (Recommended)
**Notes:** Zero churn for consumers since error type names don't change.

---

## CacheStats collision

| Option | Description | Selected |
|--------|-------------|----------|
| Prefix: YamlCacheStats | Rename yaml-core's to YamlCacheStats, keep settings-core's as CacheStats | ✓ |
| Prefix both | YamlCacheStats and SettingsCacheStats | |
| Module-qualified access | Keep both named CacheStats, don't re-export both at root | |

**User's choice:** Prefix: YamlCacheStats (Recommended)
**Notes:** Surviving crate (settings-core) owns the unprefixed name.

---

## Re-export strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Flat re-export at crate root | All yaml-core types re-exported from classic_settings_core root | ✓ |
| Submodule: yaml:: | Expose as classic_settings_core::yaml::* | |
| Both (flat + submodule) | Re-export at root AND make yaml modules public | |

**User's choice:** Flat re-export at crate root (Recommended)
**Notes:** Minimal migration churn -- consumers just swap crate name in use statements.

---

## Python binding fate

| Option | Description | Selected |
|--------|-------------|----------|
| Keep crate, update dep | classic-yaml-py stays, changes dep to settings-core | |
| Rename to classic-settings-py | Rename crate and Python module | ✓ (initial) |
| Fold into settings-py (new crate) | Create new unified crate | |

**Follow-up:** Discovered classic-settings-py already exists. Refined to: fold yaml-py into existing settings-py.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, fold into existing settings-py | Add yaml ops into settings-py, delete yaml-py | ✓ |
| Keep yaml-py separate, just update dep | Minimal change, import classic_yaml stays | |

**User's choice:** Fold into existing settings-py
**Notes:** Python module name becomes classic_settings. Consumers migrate from `import classic_yaml` to `import classic_settings`.

---

## Python module name

| Option | Description | Selected |
|--------|-------------|----------|
| classic_settings | Standard naming, breaks existing classic_yaml imports | ✓ |
| classic_yaml (keep name) | PyO3 name override, crate/module name mismatch | |

**User's choice:** classic_settings

---

## Node binding modules

| Option | Description | Selected |
|--------|-------------|----------|
| Merge yaml.rs into settings.rs | One binding module for one Rust crate | ✓ |
| Keep yaml.rs, just update imports | Less churn, naming mismatch | |

**User's choice:** Merge yaml.rs into settings.rs

---

## C++ bridge modules

| Option | Description | Selected |
|--------|-------------|----------|
| Keep yaml.rs, update imports only | Minimal churn, classic::yaml namespace stays | |
| Rename to settings.rs | Namespace changes to classic::settings | ✓ |

**User's choice:** Rename to settings.rs
**Notes:** User additionally requested: "Add bindings for the entire classic-settings-core crate to the C++ bridge" to close the parity gap with Python/Node.

---

## C++ bridge scope expansion

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, defer new bindings | Phase 1 stays structural, new coverage goes to backlog | |
| Include new bindings in Phase 1 | Also add bridge functions for settings-core cache/validators | ✓ |

**User's choice:** Include new bindings in Phase 1

---

## Test & bench migration

| Option | Description | Selected |
|--------|-------------|----------|
| Move as-is, update imports | Create tests/ and benches/ in settings-core, move files | ✓ |
| Merge tests into inline modules | Fold into #[cfg(test)] blocks | |
| You decide | Claude picks | |

**User's choice:** Move as-is, update imports (Recommended)

---

## API doc consolidation

| Option | Description | Selected |
|--------|-------------|----------|
| Merge into settings-core doc | Consolidate content, delete yaml doc | ✓ |
| Delete yaml doc, don't merge | Just delete, settings doc stays as-is | |
| You decide | Claude picks | |

**User's choice:** Merge into settings-core doc (Recommended)

---

## Parity gate timing

| Option | Description | Selected |
|--------|-------------|----------|
| Regenerate in Phase 1 | All 3 baselines regenerated at end of Phase 1 | ✓ |
| Defer all to Phase 4 | Don't regenerate until all merges land | |
| CXX only in Phase 1 | Only CXX baseline, Python/Node deferred | |

**User's choice:** Regenerate in Phase 1 (Recommended)

---

## Python pyi stub update

| Option | Description | Selected |
|--------|-------------|----------|
| Merge into classic_settings.pyi | Add yaml stubs to settings stub, delete yaml stub | ✓ |
| You decide | Claude picks | |

**User's choice:** Merge into classic_settings.pyi (Recommended)

---

## Binding test updates

| Option | Description | Selected |
|--------|-------------|----------|
| Merge test files | Fold yaml.spec.ts into settings.spec.ts, update Python imports | ✓ |
| Keep yaml.spec.ts, update imports | Separate file stays, naming mismatch | |
| You decide | Claude picks | |

**User's choice:** Merge test files (Recommended)

---

## Cross-reference cleanup scope

| Option | Description | Selected |
|--------|-------------|----------|
| Active docs only | ~15 files: CLAUDE.md, docs/api/*.md, ROADMAP, REQUIREMENTS, etc. | ✓ |
| All 68 files | Update everything including archived milestone plans | |
| Active + skill files | Active docs plus .claude/skills/ and .gemini/skills/ | |

**User's choice:** Active docs only (Recommended)
**Notes:** Archived milestone plans are historical snapshots, should not be rewritten.

---

## Git history strategy

| Option | Description | Selected |
|--------|-------------|----------|
| git mv where possible | Use git mv for rename tracking, content edits in separate commit | ✓ |
| Fresh file creation | Create new files, copy content, delete old | |
| You decide | Claude picks | |

**User's choice:** git mv where possible (Recommended)
**Notes:** Separate commits: first git mv (rename tracking), then content edits (import changes, CacheStats rename).

---

## Claude's Discretion

- Workspace Cargo.toml dependency cleanup when removing yaml-core
- Cargo feature flag deduplication (both crates have `dhat-heap`)
- Internal import organization within moved files
- Exact ordering of operations within each commit
- Any mechanical details not covered by the 15 decisions above

## Deferred Ideas

None -- all ideas raised during discussion were resolved as decisions or folded into Phase 1 scope.
