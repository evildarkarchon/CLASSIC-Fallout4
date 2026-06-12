## ADDED Requirements

### Requirement: Shippable YAML files declare a schema_version header

Every YAML file that CLASSIC distributes as data (currently `CLASSIC Main.yaml` and `CLASSIC Fallout4.yaml`; future additions follow the same rule) SHALL carry a root-level `schema_version` field whose value is a string of the form `MAJOR.MINOR` where both components are non-negative base-10 integers.

#### Scenario: Valid schema_version present

- **WHEN** a shippable YAML file contains `schema_version: "1.3"` at the document root
- **THEN** the loader parses the value into a `SchemaVersion { major: 1, minor: 3 }` struct
- **AND** the load succeeds

#### Scenario: schema_version missing

- **WHEN** a shippable YAML file is loaded without any `schema_version` field
- **THEN** the loader returns a typed `YamlSchemaError::Missing` error
- **AND** no partial parse result is returned to callers

#### Scenario: schema_version malformed

- **WHEN** a shippable YAML file contains `schema_version: "1"` or `schema_version: "1.3.2"` or `schema_version: "v1.3"`
- **THEN** the loader returns a typed `YamlSchemaError::Malformed` error identifying the file and the offending value

### Requirement: Client declares accepted schema ranges per file family

Each client build SHALL expose, for every shippable file family (e.g., `MAIN_YAML`, `GAME_FALLOUT4_YAML`), a compile-time-visible `SchemaCompat { accepted_major: u32, minimum_minor: u32 }` constant that specifies which schema versions it can safely parse.

#### Scenario: File compatible with client

- **WHEN** a YAML file reports `schema_version: "2.5"` and the client's `SchemaCompat` for that file family is `{ accepted_major: 2, minimum_minor: 4 }`
- **THEN** `schema_compat_check(file, compat)` returns `Compatibility::Compatible`

#### Scenario: File major does not match client

- **WHEN** a YAML file reports `schema_version: "3.0"` and the client's `SchemaCompat` for that file family is `{ accepted_major: 2, minimum_minor: 4 }`
- **THEN** `schema_compat_check` returns `Compatibility::IncompatibleMajor { file_major: 3, client_accepted_major: 2 }`

#### Scenario: File minor below client minimum

- **WHEN** a YAML file reports `schema_version: "2.2"` and the client's `SchemaCompat` is `{ accepted_major: 2, minimum_minor: 4 }`
- **THEN** `schema_compat_check` returns `Compatibility::IncompatibleMinor { file_minor: 2, client_minimum_minor: 4 }`

### Requirement: Loader enforces compatibility gate before merging

The shippable-YAML loader in `classic-config-core` SHALL call `schema_compat_check` before merging any document into the in-memory config state and SHALL refuse incompatible documents without mutating the config.

#### Scenario: Incompatible cached file is ignored, bundled file wins

- **WHEN** a cached `<cache>/CLASSIC Fallout4.yaml` has `schema_version: "3.0"` but the client accepts major `2`
- **AND** the bundled `CLASSIC Data/databases/CLASSIC Fallout4.yaml` has `schema_version: "2.5"` and the client accepts major `2`, minor `>= 3`
- **THEN** the loader logs a warning identifying the rejected cached file
- **AND** loads the bundled file
- **AND** does not delete the incompatible cached file

#### Scenario: Both cached and bundled files incompatible

- **WHEN** neither the cached nor the bundled file satisfies `schema_compat_check`
- **THEN** the loader returns a typed `YamlLoadError::NoCompatibleSource { file_name, candidates }` listing every candidate and why it was rejected

### Requirement: Additive schema changes bump MINOR, breaking changes bump MAJOR

Authors of shippable YAML files SHALL increment only the MINOR component when adding optional fields that existing clients can ignore, and SHALL increment MAJOR (resetting MINOR to 0) when removing, renaming, or changing the shape or required semantics of any existing field.

#### Scenario: Optional field addition

- **WHEN** a contributor adds a new optional top-level key `Suspects_Networking` to `CLASSIC Fallout4.yaml`
- **THEN** the file's `schema_version` is bumped from `"1.3"` to `"1.4"`
- **AND** clients declaring `SchemaCompat { accepted_major: 1, minimum_minor: 3 }` still load the file

#### Scenario: Breaking rename

- **WHEN** a contributor renames `Mods_FREQ` to `Mod_Frequency_Hints` in `CLASSIC Fallout4.yaml`
- **THEN** the file's `schema_version` is bumped from `"1.4"` to `"2.0"`
- **AND** clients declaring `SchemaCompat { accepted_major: 1, minimum_minor: X }` refuse to load the file
