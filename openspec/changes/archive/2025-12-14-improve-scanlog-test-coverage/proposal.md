# Proposal: improve-scanlog-test-coverage

## Summary

Address critical test coverage gap in the ScanLog package (currently 11% coverage) and add missing pytest markers to 67 test files across the codebase. This improves production reliability, enables selective test execution, and brings the project closer to the 90%+ coverage target specified in the test-suite spec.

## Problem Statement

A comprehensive code review identified two HIGH severity testing issues:

### 1. ScanLog Package Critical Coverage Gap (11%)

The ScanLog package contains 18 production modules but only 2 test files:
- `tests/scanlog/test_fcx_handler.py`
- `tests/scanlog/test_config_file_cache.py`

**Critical untested modules:**
- `Parser.py` - Core crash log parsing with Rust acceleration (150x speedup)
- `OrchestratorCore.py` - Async orchestration for crash log processing
- `ScanLogsExecutor.py` - Main executor for CLI/GUI scanning
- `pipeline/*.py` - Async pipeline components
- `FormIDAnalyzer.py` / `FormIDAnalyzerCore.py` - Form ID analysis
- `ReportGenerator.py` - Report generation logic
- `DetectMods.py` - Mod detection from crash logs
- `SuspectScanner.py` - Suspect file scanning
- `RecordScanner.py` - Record data scanning

### 2. Missing Test Markers (67 Files)

67 test files (29% of 229 total) lack required pytest markers, violating the "Required Marker System" requirement in the test-suite spec. This prevents:
- Selective test execution by type (`-m unit`, `-m integration`)
- Proper CI categorization
- Performance test isolation

## Scope

### In Scope
- Add comprehensive tests for ScanLog package modules
- Add missing pytest markers to 67 test files
- Create new fixture modules for ScanLog testing
- Update test-suite spec with ScanLog-specific requirements

### Out of Scope
- Splitting large test files (separate change proposal)
- Refactoring production ScanLog code
- Adding tests for other packages (focus on ScanLog)

## Spec Changes

### test-suite Spec Modifications

1. **NEW Requirement: ScanLog Test Coverage**
   - Minimum 70% coverage for ScanLog package
   - Required test files for core modules (Parser, OrchestratorCore, Executor)
   - Fixture requirements for crash log test data

2. **MODIFIED Requirement: Required Marker System**
   - Add enforcement scenario for marker compliance checking
   - Add marker audit tooling requirement

## Success Criteria

1. ScanLog package coverage increases from 11% to 70%+
2. All 67 files have appropriate markers
3. Tests pass with `uv run pytest -n auto`
4. No regression in existing test suite

## Estimated Effort

- **ScanLog tests**: 3-4 days
- **Missing markers**: 1 day
- **Fixtures and infrastructure**: 0.5 days

**Total**: 4-5 days

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| ScanLog has complex async patterns | Use existing async_fixtures.py patterns |
| Rust acceleration complicates testing | Test both Rust and Python paths using existing parity patterns |
| Large scope may introduce instability | Add tests incrementally with CI validation |

## Dependencies

- Existing `tests/fixtures/` infrastructure
- Mock crash log data in `tests/fixtures/data_fixtures.py`
- Rust integration test patterns from `tests/rust_integration/`
