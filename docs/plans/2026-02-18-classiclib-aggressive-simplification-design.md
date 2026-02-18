# CLASSIC Aggressive Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Aggressively simplify `ClassicLib/` internals (factory/yaml/resources/setup/legacy wrappers) while preserving entry-point behavior and PySide6 GUI thread safety.

**Architecture:** Keep public APIs and entry points stable, but move complexity behind internal facades. Use an explicit async runtime boundary: GUI workers keep `asyncio.run(...)` in QThreads, sync GUI code may use bridge adapters, CLI/TUI remain async-first. Refactor in small, test-gated commits.

**Tech Stack:** Python 3.12, PySide6/QThread, asyncio, pytest/pytest-qt, Rust-backed extension modules via existing integration layer.

---

### Task 1: Lock In Entry-Point + GUI Contracts
- Create tests for entrypoint symbol stability and worker runtime contracts.

### Task 2: Introduce Async Runtime Boundary Module
- Add a dedicated runtime boundary helper module in `ClassicLib/core/`.

### Task 3: Migrate GUI/Support Sync Adapters to Boundary
- Replace direct bridge calls in sync adapters with boundary helpers.

### Task 4: Split `integration/factory.py` into Internal Modules
- Preserve `factory.py` as public facade and move internals to submodules.

### Task 5: YAML Stack Simplification
- Make async core authoritative and keep sync API as thin adapter.

### Task 6: Unify `support/resources.py` Sync/Async Strategy Engine
- Consolidate duplicated sync/async path cache logic.

### Task 7: Setup Bootstrap Deduplication
- Remove duplicate default settings bootstrap flow.

### Task 8: Legacy DB Path Consolidation
- Delegate legacy DB utilities to unified database layer where possible.

### Task 9: Full Regression and Stability Gate
- Run full targeted integration and CI-like test suite.
