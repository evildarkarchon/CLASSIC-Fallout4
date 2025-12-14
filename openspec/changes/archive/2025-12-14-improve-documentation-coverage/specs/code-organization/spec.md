# code-organization Specification Delta

## ADDED Requirements

### Requirement: Python Docstring Returns Completeness
All public Python functions and methods with non-None return type annotations SHALL include a `Returns:` section in their Google-style docstring.

#### Scenario: Function with typed return has Returns section
- **GIVEN** a public function with a return type annotation other than `None`
- **WHEN** the function has a docstring
- **THEN** the docstring MUST include a `Returns:` section describing the return value
- **AND** the description MUST match the declared return type

#### Scenario: Function returning None exempted
- **GIVEN** a public function with return type `None` or no return annotation
- **WHEN** the function has a docstring
- **THEN** a `Returns:` section is NOT required

#### Scenario: Private methods exempted
- **GIVEN** a method or function whose name starts with underscore (`_`)
- **WHEN** the function has a docstring
- **THEN** a `Returns:` section is NOT required (but recommended for complex logic)

### Requirement: Rust Documentation Warning-Free Build
Running `cargo doc --workspace --no-deps` SHALL produce zero documentation warnings. All public Rust items MUST have valid documentation that passes rustdoc validation.

#### Scenario: Doc build produces no warnings
- **WHEN** `cargo doc --workspace --no-deps` is executed
- **THEN** the command SHALL complete with zero warnings
- **AND** CI pipeline SHALL fail if any documentation warnings are present

#### Scenario: HTML tags escaped in doc comments
- **GIVEN** a doc comment containing angle brackets (e.g., `<GAME>`, `<String>`)
- **WHEN** the text is not intended as HTML
- **THEN** the angle brackets MUST be escaped using backticks: `` `GAME` ``, `` `String` ``

#### Scenario: Intra-doc links resolve or are escaped
- **GIVEN** a doc comment containing square bracket notation (e.g., `[SomeType]`)
- **WHEN** the referenced item does not exist in scope
- **THEN** the brackets MUST be escaped: `\[SomeType\]`
- **OR** the link MUST be corrected to reference an existing item
