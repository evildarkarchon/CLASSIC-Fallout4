## ADDED Requirements

### Requirement: Test File Size Limits

Test files SHALL be kept under 500 lines to ensure maintainability, fast failure isolation, and efficient parallel execution.

#### Scenario: Maximum file size enforcement
- **WHEN** creating or modifying a test file
- **THEN** the file SHOULD NOT exceed 500 lines of code
- **AND** files approaching 400 lines SHOULD be considered for splitting

#### Scenario: Splitting strategy for large files
- **WHEN** a test file exceeds 500 lines
- **THEN** the file MUST be split into focused modules
- **AND** each new file SHOULD contain tests for a single logical concern
- **AND** file names MUST clearly indicate the test scope

#### Scenario: Class-per-file guideline
- **WHEN** organizing test classes
- **THEN** each test file SHOULD contain 1-3 related test classes
- **AND** classes exceeding 200 lines SHOULD be considered for extraction
- **AND** shared fixtures MUST be extracted to `tests/fixtures/`

#### Scenario: Naming convention for split files
- **WHEN** splitting a large test file
- **THEN** new files MUST follow the pattern `test_<component>_<aspect>.py`
- **AND** examples include:
  - `test_update_version_parsing.py` - Version parsing tests
  - `test_update_github_api.py` - GitHub API tests
  - `test_stress_formid_volume.py` - FormID volume stress tests
