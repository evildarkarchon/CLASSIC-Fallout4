## ADDED Requirements

### Requirement: Type Ignore Comments Must Use Specific Error Codes
All `# type: ignore` comments in production code SHALL include specific mypy/pyright error codes. Bare `# type: ignore` comments without error codes are prohibited.

#### Scenario: Type ignore with specific error code
- **WHEN** a type ignore comment is necessary
- **THEN** the comment MUST include at least one specific error code
- **AND** the format SHALL be `# type: ignore[error-code]` or `# type: ignore[code1, code2]`

#### Scenario: Bare type ignore rejected
- **WHEN** code contains a bare `# type: ignore` without error codes
- **THEN** static analysis SHALL report an error
- **AND** CI pipeline SHALL fail until specific error codes are added

#### Scenario: Multiple error codes documented
- **WHEN** a line triggers multiple type errors that must be ignored
- **THEN** all error codes SHALL be listed: `# type: ignore[arg-type, return-value]`

### Requirement: Type Ignore Comments Require Justification for Non-Trivial Cases
Type ignore comments for complex cases (attr-defined, union-attr, no-any-return) SHALL include a brief comment explaining why the ignore is necessary.

#### Scenario: Complex type ignore with explanation
- **WHEN** a type ignore uses error codes `[attr-defined]`, `[union-attr]`, or `[no-any-return]`
- **THEN** the comment SHOULD include a brief explanation
- **AND** the format MAY be `# type: ignore[attr-defined]  # Qt signal type`

#### Scenario: Simple type ignore without explanation
- **WHEN** a type ignore uses straightforward error codes like `[assignment]` for conditional imports
- **THEN** no additional explanation is required

### Requirement: Broad Exception Handlers Limited to Specific Contexts
The use of `except Exception` (or bare `except:`) SHALL be limited to specific contexts: GUI thread workers, top-level entry points, and cleanup operations. All other exception handlers MUST use specific exception types.

#### Scenario: GUI worker uses broad exception handler
- **WHEN** a Qt worker thread handles exceptions
- **THEN** `except Exception` MAY be used
- **AND** the handler MUST include `# noqa: BLE001` comment
- **AND** the handler SHOULD log the exception before handling

#### Scenario: Top-level entry point uses broad exception handler
- **WHEN** `CLASSIC_Interface.py` or `CLASSIC_ScanLogs.py` main function handles exceptions
- **THEN** `except Exception` MAY be used for graceful shutdown
- **AND** the exception MUST be logged with full traceback

#### Scenario: Business logic uses specific exception types
- **WHEN** exception handling is needed in business logic (ScanLog, FileIO, Database)
- **THEN** specific exception types MUST be used (e.g., `FileNotFoundError`, `ValueError`, `RustYamlError`)
- **AND** `except Exception` SHALL NOT be used

#### Scenario: Rust fallback with specific exception hierarchy
- **WHEN** code catches Rust extension exceptions
- **THEN** specific Rust exception types SHOULD be caught first (e.g., `RustYamlError`, `RustScanlogError`)
- **AND** only after specific Rust exceptions MAY a broader handler be used with documentation

### Requirement: Pass Statements Must Have Explicit Purpose
All `pass` statements in production code SHALL either be replaced with proper implementations or include a comment explaining their purpose.

#### Scenario: Abstract method placeholder
- **WHEN** a method is intended to be abstract but not using ABC
- **THEN** `raise NotImplementedError("Subclass must implement")` SHALL be used instead of `pass`

#### Scenario: Intentional no-operation
- **WHEN** a `pass` statement represents an intentional no-op (e.g., empty except handler that swallows errors)
- **THEN** a comment MUST explain why no action is needed
- **AND** the format SHALL be `pass  # Intentionally empty: <reason>`

#### Scenario: Incomplete implementation
- **WHEN** a `pass` statement represents incomplete code
- **THEN** it SHALL be replaced with a proper implementation
- **OR** include a TODO comment with issue reference: `pass  # TODO(#123): Implement X`

### Requirement: Dynamic Code Patterns Must Be Documented
Use of dynamic code execution patterns (`globals()`, `eval()`, `exec()`) in production code SHALL be documented and justified.

#### Scenario: Globals usage for feature detection
- **WHEN** `globals()` is used to check for available functions (e.g., Rust module detection)
- **THEN** the usage MUST include a comment explaining the pattern
- **AND** alternative approaches (e.g., `hasattr()`, try/except import) SHOULD be considered

#### Scenario: Eval/exec prohibited
- **WHEN** production code needs dynamic execution
- **THEN** `eval()` and `exec()` SHALL NOT be used
- **AND** alternatives like `getattr()`, dispatch tables, or plugin systems SHALL be used instead
