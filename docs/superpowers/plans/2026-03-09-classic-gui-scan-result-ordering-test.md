# classic-gui scan result ordering test Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real Qt runtime test that proves `ScanWorker` maps completion-order batch results back to original GUI rows using `result.input_index`.

**Architecture:** Introduce a narrow test seam that covers the multi-log batch execution path in `ScanWorker` without changing normal production behavior. Use a test subclass or injected path to supply fake completion-order batch outcomes, then assert emitted Qt signals preserve completion-order emission while correlating indices and fallback paths from the original `QStringList`.

**Tech Stack:** C++20, Qt 6 / QtTest, `classic-gui`, CXX bridge-facing DTOs or a narrow local batch-outcome wrapper, PowerShell build wrapper `classic-gui/build_gui.ps1`

---

## Chunk 1: Worker Seam And Runtime Test

### Task 1: Add a narrow batch-execution seam

**Files:**
- Modify: `classic-gui/src/workers/scanworker.h`
- Modify: `classic-gui/src/workers/scanworker.cpp`
- Modify: `classic-gui/tests/CMakeLists.txt`
- Test: `classic-gui/tests/test_scanworker_batch_result_ordering.cpp`

- [ ] **Step 1: Write the failing runtime test**

Create `classic-gui/tests/test_scanworker_batch_result_ordering.cpp` with a test-local `TestScanWorker` subclass that expects to override a narrow multi-log execution seam and return fake completion-order results.

```cpp
struct BatchExecutionRequest {
    QStringList logPaths;
    QString yamlRoot;
    QString yamlData;
    QString game;
    QString gameVersion;
    bool showFormIdValues;
    bool fcxMode;
    bool simplifyLogs;
    uint32_t maxConcurrentScans;
};

class TestScanWorker final : public ScanWorker {
    Q_OBJECT
public:
    using ScanWorker::ScanWorker;

protected:
    QList<BatchExecutionOutcome> executeBatchScan(const BatchExecutionRequest& request) override {
        Q_UNUSED(request);
        return {
            makeOutcome(/*inputIndex=*/2, /*success=*/true, /*logPath=*/""),
            makeOutcome(/*inputIndex=*/0, /*success=*/true, /*logPath=*/"C:/tmp/log0.log"),
            makeOutcome(/*inputIndex=*/1, /*success=*/false, /*logPath=*/"")
        };
    }
};
```

The first test should build a `QStringList` such as `{"A.log", "B.log", "C.log"}`, run `doScan(...)` in multi-log mode, capture `logScanned(int, bool, QString)` via `QSignalSpy`, and assert:

- three `logScanned(...)` emissions occur
- emission order matches fake result order
- emitted indices are `2`, `0`, `1`
- empty result paths fall back to `logPaths[input_index]`

- [ ] **Step 2: Register the new test target**

Modify `classic-gui/tests/CMakeLists.txt` to add the new Qt test target.

```cmake
add_classic_gui_qt_test(classic-gui-test-scanworker-batch-ordering
    test_scanworker_batch_result_ordering.cpp
    ${CMAKE_SOURCE_DIR}/src/workers/scanworker.cpp
    ${CMAKE_SOURCE_DIR}/src/workers/scanprogressmodel.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-scanworker-batch-ordering)
```

- [ ] **Step 3: Run the test suite to verify the new test fails for the right reason**

Run:

```powershell
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

Expected: the new test target fails to compile or link because `ScanWorker` does not yet expose the overridable/injectable multi-log execution seam the test expects.

- [ ] **Step 4: Implement the minimal seam in `ScanWorker`**

Refactor `ScanWorker` so the multi-log branch delegates through one narrow seam that covers the current config/orchestrator/batch execution path. Keep the single-log path unchanged.

Use a small local request/outcome shape if that keeps tests independent from hard-to-construct bridge containers.

```cpp
struct BatchExecutionOutcome {
    quint32 inputIndex;
    bool success;
    QString logPath;
    QStringList reportLines;
};

class ScanWorker : public QObject {
    // ...
protected:
    virtual QList<BatchExecutionOutcome> executeBatchScan(const BatchExecutionRequest& request);
};
```

Implementation requirements:

- production path still calls `build_full_scan_config(...)`, `orchestrator_new(...)`, and `orchestrator_process_logs_batch_with_progress(...)`
- result iteration still follows returned completion order
- emitted `logScanned(...)` uses `result.inputIndex` for row identity
- empty `logPath` still falls back to the original `QStringList` row
- report-writing and unsolved-log behavior remain unchanged for production callers

- [ ] **Step 5: Re-run the GUI test suite**

Run:

```powershell
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

Expected: the new Qt test passes, existing `classic-gui` tests still pass, and there is no regression in the scan-progress model or wiring tests.

- [ ] **Step 6: Verify the specific contract in the new test output**

Run a focused CTest invocation if the generated build tree is available; otherwise re-use the wrapper output and confirm the target name is present.

Preferred run:

```powershell
ctest --test-dir classic-gui/build --output-on-failure -R classic-gui-test-scanworker-batch-ordering
```

Expected: one passing test target proving completion-order emission with `input_index`-based row correlation.

- [ ] **Step 7: Do not commit unless the user explicitly requests it**

Repo policy for this session: leave changes uncommitted unless the user later asks for a commit.

---

## Chunk 2: Post-change Review

### Task 2: Sanity-check nearby docs and test boundaries

**Files:**
- Review: `docs/api/classic-gui-scan-result-ordering.md`
- Review: `docs/api/classic-gui-scan-progress-consumer.md`
- Review: `docs/api/classic-cpp-bridge-scan-progress-callback.md`

- [ ] **Step 1: Re-read the nearby docs after implementation**

Confirm the new runtime test matches the currently documented contract:

- completion-order batch results are not re-sorted
- `input_index` is the stable original-row key
- Results-tab ordering stays a file-discovery concern

- [ ] **Step 2: Update docs only if implementation changed the documented contract**

If the test required changing the contract, update the affected page(s) in the same change. If the test only validates the documented behavior, leave docs unchanged.

- [ ] **Step 3: Final verification**

Run:

```powershell
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
git diff -- classic-gui/src/workers/scanworker.h classic-gui/src/workers/scanworker.cpp classic-gui/tests/CMakeLists.txt classic-gui/tests/test_scanworker_batch_result_ordering.cpp docs/api/classic-gui-scan-result-ordering.md docs/api/classic-gui-scan-progress-consumer.md docs/api/classic-cpp-bridge-scan-progress-callback.md
```

Expected: GUI tests pass and the diff is limited to the worker seam, the new Qt test, and any doc updates that were actually needed.
