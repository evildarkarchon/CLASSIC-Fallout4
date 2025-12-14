# Change: Refactor Large Files (God Classes)

## Why

Seven files in the codebase exceed 750 lines, creating "God Classes" that mix multiple responsibilities. Each large file requires ~30% more time to understand and modify safely, increasing bug risk and slowing development velocity.

## What Changes

### Target Files (by priority)

| File | Lines | Refactoring Strategy |
|------|-------|---------------------|
| `rust/file_io_rust.py` | 931 | Extract fallback logic to separate module |
| `rust/report_rust.py` | 895 | Split 4 classes into separate files |
| `ScanLog/OrchestratorCore.py` | 872 | Extract pipeline stages to submodules |
| `ResourceLoader.py` | 867 | Extract path strategies to strategy pattern |
| `RustAcceleration.py` | 841 | Extract metrics/workload to separate modules |
| `AsyncBridge.py` | 776 | Extract helper functions to utils module |
| `Interface/ResultsViewerWidgets.py` | 766 | Split mega-widget into component widgets |

### Refactoring Principles

1. **Logical separation** - Group by responsibility, not arbitrary line limits
2. **One class per file** - Align with existing project convention
3. **Preserve APIs** - All public interfaces remain unchanged
4. **Factory pattern alignment** - Integrate with `ClassicLib/integration/factory/`

## Impact

- Affected specs: `code-organization`
- Affected code: 7 files totaling 5,948 lines
- Risk: Medium (extensive changes, but well-tested codebase)
- Benefit: Improved maintainability, faster onboarding, reduced bug density
