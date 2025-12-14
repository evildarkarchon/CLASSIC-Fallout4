# Tasks: improve-scanlog-test-coverage

## 1. Infrastructure Setup
- [x] 1.1 Create ScanLog test fixtures in `tests/fixtures/scanlog_fixtures.py`
- [x] 1.2 Create ScanLog test directory structure (`tests/scanlog/parser/`, `orchestrator/`, `executor/`, `pipeline/`)

## 2. Parser Tests
- [x] 2.1 Write parser unit tests in `tests/scanlog/parser/test_parser_unit.py`
- [x] 2.2 Write parser parity tests in `tests/scanlog/parser/test_parser_parity.py`

## 3. Orchestrator Tests
- [x] 3.1 Write OrchestratorCore unit tests in `tests/scanlog/orchestrator/test_orchestrator_unit.py`
- [x] 3.2 Write OrchestratorCore integration tests in `tests/scanlog/orchestrator/test_orchestrator_integration.py`

## 4. Executor Tests
- [x] 4.1 Write ScanLogsExecutor unit tests in `tests/scanlog/executor/test_executor_unit.py`
- [x] 4.2 Write ScanLogsExecutor integration tests in `tests/scanlog/executor/test_executor_integration.py`

## 5. Pipeline Tests
- [x] 5.1 Write pipeline stage tests in `tests/scanlog/pipeline/test_pipeline_stages.py`

## 6. Missing Markers
- [x] 6.1 Add markers to `tests/async_tests/` files
- [x] 6.2 Add markers to `tests/backup/` files
- [x] 6.3 Add markers to `tests/core/` files
- [x] 6.4 Add markers to `tests/game/` files
- [x] 6.5 Add markers to `tests/gui/settings/` files
- [x] 6.6 Add markers to remaining test files

## 7. Validation
- [x] 7.1 Run full test suite validation (`uv run pytest tests/scanlog/ -v`)
- [x] 7.2 Run marker compliance audit
- [x] 7.3 Run OpenSpec validation (`openspec validate improve-scanlog-test-coverage --strict`)
