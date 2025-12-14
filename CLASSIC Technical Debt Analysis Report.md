 CLASSIC Technical Debt Analysis Report

  Executive Summary

  | Metric                   | Value                                | Risk Level |
  |--------------------------|--------------------------------------|------------|
  | Total Python Source      | ~40,000 lines (ClassicLib)           | -          |
  | Total Rust Source        | ~25,000 lines (business logic)       | -          |
  | Test Coverage            | 267 files, 78,644 lines, 85% minimum | ✅ Good    |
  | Type Ignore Comments     | 124                                  | ⚠️ Medium  |
  | Broad Exception Catches  | 50                                   | ⚠️ Medium  |
  | AsyncBridge Misuse Sites | 32 imports (should be ~5-10)         | 🔴 High    |
  | Outdated Dependencies    | 2 (pefile, syrupy)                   | ✅ Low     |

  Overall Debt Score: Medium - Well-architected project with isolated pockets of debt.

  ---
  1. Technical Debt Inventory

  1.1 Code Debt - Large Files (God Classes)

  | File                              | Lines | Issue                              |
  |-----------------------------------|-------|------------------------------------|
  | integration/factory.py            | 998   | 21 factory functions - mega-module |
  | rust/file_io_rust.py              | 931   | Mixed fallback + wrapper logic     |
  | rust/report_rust.py               | 895   | Duplicate Python fallback code     |
  | ScanLog/OrchestratorCore.py       | 872   | Complex orchestration logic        |
  | ResourceLoader.py                 | 867   | 5+ resource path strategies        |
  | RustAcceleration.py               | 841   | Legacy acceleration detection      |
  | AsyncBridge.py                    | 776   | Singleton pattern complexity       |
  | Interface/ResultsViewerWidgets.py | 766   | GUI mega-widget                    |

  Impact: Each large file requires ~30% more time to understand and modify safely.

  1.2 Code Debt - Duplicate Implementations

  Location: ClassicLib/ScanLog/AsyncUtil.py (492 lines) vs ClassicLib/rust/database_rust.py (495 lines)

  Both contain:
  - DatabasePoolManager class
  - AsyncDatabasePool class
  - Nearly identical interfaces

  Cost:
  - Bug fixes require updating 2 locations
  - Estimated: 4 hours/bug fix overhead
  - Risk of behavioral drift between implementations

  1.3 Architecture Debt - AsyncBridge Overuse

  Per project documentation (08-memories.md):
  AsyncBridge is ONLY for GUI workers (Qt threads) and testing. Production CLI code MUST use async-first pattern.

  Current State: 32 files import AsyncBridge
  Expected: 5-10 files (GUI workers + test utilities)
  Violation: ~22 files misusing AsyncBridge in non-GUI contexts

  Impact:
  - Creates unnecessary event loops
  - Performance overhead in CLI code
  - Violates documented architecture

  1.4 Testing Debt - Large Test Files

  | Test File                                 | Lines | Issue                      |
  |-------------------------------------------|-------|----------------------------|
  | test_hybrid_orchestrator.py               | 1,300 | Too many tests in one file |
  | test_update_network_comprehensive_unit.py | 1,237 | Needs splitting            |
  | test_data_volume_stress.py                | 1,073 | Stress test mega-file      |
  | test_error_recovery_stress.py             | 967   | Could be modularized       |

  Impact: Slow test runs, hard to isolate failures

  1.5 Type Safety Debt

  | Issue                          | Count | Impact                     |
  |--------------------------------|-------|----------------------------|
  | # type: ignore comments        | 124   | Reduced type safety        |
  | Broad except Exception         | 50    | Silent failures            |
  | pass statements                | 25    | Incomplete implementations |
  | Dynamic code (globals(), eval) | 12    | Hard to analyze            |

  1.6 Documentation Debt

  TODO/FIXME Comments (3 found):
  ClassicLib/ScanGame/Config.py:
    # TODO: Check if this needs to raise or return an error message
    # TODO: Useful for checking how many INIs found

  ClassicLib/ScanGame/ScanModInis.py:
    # TODO: Maybe return a message that no ini files were found?

  1.7 Dependency Debt

  | Package | Current  | Latest    | Risk                             |
  |---------|----------|-----------|----------------------------------|
  | pefile  | 2023.2.7 | 2024.8.26 | Pinned to avoid breaking changes |
  | syrupy  | 4.8.0    | 5.0.0     | Minor version bump               |

  Note: Minimal dependency debt - well maintained.

  ---
  2. Impact Assessment

  2.1 Development Velocity Impact

  | Debt Item                    | Time Impact                 | Monthly Cost |
  |------------------------------|-----------------------------|--------------|
  | Factory.py mega-module       | +2 hrs/change               | 8 hrs        |
  | Duplicate DatabasePool       | +4 hrs/bug fix              | 4 hrs        |
  | Large test files             | +1 hr/failure investigation | 6 hrs        |
  | AsyncBridge cleanup overhead | +1 hr/refactor              | 4 hrs        |

  Estimated Monthly Velocity Loss: 22 hours (~0.5 dev-week)

  2.2 Quality Impact

  | Debt Item                  | Bug Risk            | Severity |
  |----------------------------|---------------------|----------|
  | Broad exception catches    | Silent failures     | Medium   |
  | Type ignore bypasses       | Runtime errors      | Medium   |
  | Incomplete implementations | Unexpected behavior | Low      |

  2.3 Risk Assessment Matrix

  | Risk                               | Probability | Impact | Priority |
  |------------------------------------|-------------|--------|----------|
  | AsyncBridge misuse causing bugs    | Medium      | High   | P1       |
  | Factory.py becoming unmaintainable | High        | Medium | P2       |
  | Database pool behavior drift       | Low         | High   | P2       |
  | Type errors in production          | Medium      | Medium | P3       |

  ---
  3. Prioritized Remediation Roadmap

  Phase 1: Quick Wins (Week 1-2)

  1. Split factory.py into domain modules
  Before: integration/factory.py (998 lines, 21 functions)
  After:
    - integration/factory/file_io.py
    - integration/factory/parsers.py
    - integration/factory/analyzers.py
    - integration/factory/utilities.py
  - Effort: 8 hours
  - Benefit: 50% easier navigation, testable units
  - ROI: Immediate productivity gain

  2. Consolidate DatabasePool implementations
  # Create unified abstraction
  class DatabasePoolFactory:
      @staticmethod
      def create(use_rust: bool = True) -> AsyncDatabasePool:
          if use_rust and RUST_AVAILABLE:
              return RustDatabasePool(...)
          return PythonDatabasePool(...)
  - Effort: 12 hours
  - Benefit: Single source of truth
  - ROI: 4 hours saved per bug fix

  3. Address TODO comments
  - Convert to GitHub issues or resolve
  - Effort: 2 hours
  - Benefit: Clean codebase, tracked work

  Phase 2: Medium-Term (Month 1-2)

  4. AsyncBridge Audit
  - Review all 32 import sites
  - Remove from non-GUI code paths
  - Refactor CLI to async-first pattern
  - Effort: 20 hours
  - Benefit: Performance + architecture compliance

  5. Reduce type: ignore comments
  - Target: Reduce from 124 to <50
  - Fix underlying type issues
  - Effort: 16 hours
  - Benefit: Catch bugs at development time

  6. Split large test files
  - Break files >800 lines into logical modules
  - Target: Max 500 lines per test file
  - Effort: 8 hours
  - Benefit: Faster CI, easier debugging

  Phase 3: Long-Term (Quarter 2)

  7. Interface module refactoring
  - ResultsViewerWidgets.py (766 lines) -> smaller components
  - Reduce mixin complexity
  - Effort: 40 hours
  - Benefit: Testable GUI components

  8. ResourceLoader simplification
  - Document all 5 resource loading paths
  - Consolidate where possible
  - Effort: 16 hours
  - Benefit: Reduced maintenance burden

  ---
  4. Prevention Strategy

  4.1 Quality Gates (Already Strong)

  Current gates in pyproject.toml:
  [tool.pytest.ini_options]
  fail_under = 85  # Coverage minimum ✅

  4.2 Recommended Additions

  File Size Limits (add to Ruff):
  [tool.ruff.lint]
  select = [
      "C901",  # McCabe complexity
  ]
  mccabe.max-complexity = 12

  Suggested Pre-commit Hook:
  - id: check-file-size
    name: Check file size
    entry: python -c "import sys; sys.exit(1 if any(len(open(f).readlines()) > 600 for f in sys.argv[1:]) else 0)"
    files: '\.py$'

  4.3 Debt Budget

  | Metric              | Current   | Target    | Action             |
  |---------------------|-----------|-----------|--------------------|
  | Max file size       | 998 lines | 600 lines | Split large files  |
  | Type ignores        | 124       | <50       | Fix types          |
  | Broad exceptions    | 50        | <20       | Use specific types |
  | AsyncBridge imports | 32        | <10       | Audit + remove     |

  ---
  5. Positive Findings (No Debt)

  | Area                         | Status                                |
  |------------------------------|---------------------------------------|
  | Rust architecture separation | ✅ Excellent - core/py split enforced |
  | .pyi stub files              | ✅ All bindings have stubs            |
  | Test organization            | ✅ 267 files, domain-driven           |
  | CI/CD pipeline               | ✅ Multi-stage with timeouts          |
  | Documentation standards      | ✅ Google-style enforced              |
  | One Runtime Rule             | ✅ Properly implemented               |
  | Python/Rust boundary         | ✅ Clean separation                   |

  ---
  6. ROI Summary

  | Investment               | Hours  | Annual Savings | Payback  |
  |--------------------------|--------|----------------|----------|
  | Split factory.py         | 8      | 48 hrs         | 1 month  |
  | Consolidate DatabasePool | 12     | 24 hrs         | 6 months |
  | AsyncBridge audit        | 20     | 36 hrs         | 7 months |
  | Type safety fixes        | 16     | 24 hrs         | 8 months |
  | Total                    | 56 hrs | 132 hrs        | 5 months |

  ---
  7. Recommendations

  Immediate Actions (This Sprint)

  1. Create GitHub issues for 3 TODO comments
  2. Begin factory.py split (can be incremental)
  3. Document AsyncBridge valid use cases

  Next Sprint

  1. Complete factory.py modularization
  2. Consolidate DatabasePool implementations
  3. Start AsyncBridge audit

  Ongoing

  1. Monitor file sizes in code review
  2. Reduce type ignores with each PR
  3. Convert broad exceptions incrementally

● The analysis is complete. The CLASSIC codebase is generally well-architected with strong foundations in Rust/Python separation, comprehensive testing (267 test files, 78K lines), and enforced documentation standards.

  Top 3 Priority Items:
  1. Split factory.py (998 lines → 4 modules) - Highest impact quick win
  2. Consolidate DatabasePool - Eliminate duplicate implementations
  3. AsyncBridge audit - 32 imports need review, ~22 likely violations

  The estimated payback for addressing the identified debt is ~5 months, with 132 hours annual savings from a 56-hour investment.