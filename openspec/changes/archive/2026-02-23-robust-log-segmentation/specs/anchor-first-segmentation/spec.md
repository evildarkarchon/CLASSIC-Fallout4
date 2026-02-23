## ADDED Requirements

### Requirement: Game-output anchors define all segment boundaries
The segmentation engine SHALL identify segment boundaries exclusively using game-output anchor markers. The following markers SHALL be the only boundary anchors recognized: `SYSTEM SPECS:`, `PROBABLE CALL STACK:`, `MODULES:`, `PLUGINS:`, `REGISTERS:`, `STACK:`. Crashgen-owned bracket headers (e.g., `[Compatibility]`, `[Patches]`) SHALL NOT be required for boundary detection and SHALL NOT gate segment collection.

#### Scenario: Log with known settings header segments correctly
- **WHEN** a crash log contains `[Compatibility]` before `SYSTEM SPECS:`
- **THEN** the settings segment contains all lines between the start of the log and `SYSTEM SPECS:` (exclusive)

#### Scenario: Log with unknown settings header segments correctly
- **WHEN** a crash log contains an unrecognized bracket header (e.g., `[NewForkHeader]`) before `SYSTEM SPECS:`
- **THEN** the settings segment contains all lines between the start of the log and `SYSTEM SPECS:` (exclusive), identical to a log with a known header

#### Scenario: Log with no settings header segments correctly
- **WHEN** a crash log has no bracket header before `SYSTEM SPECS:`
- **THEN** the settings segment contains whatever lines precede `SYSTEM SPECS:`, which may be empty

#### Scenario: Anchor detection is whitespace-insensitive
- **WHEN** a game-output anchor line has leading whitespace (e.g., `\tSYSTEM SPECS:`)
- **THEN** the anchor is detected and the segment boundary is applied correctly

---

### Requirement: Segmentation produces a named segment map
The segmentation engine SHALL return a named map with the following fixed keys: `settings`, `system`, `callstack`, `modules`, `xse_modules`, `plugins`, `registers`, `stack_dump`. All keys SHALL always be present in the output. If the corresponding anchor is absent from the log, the value SHALL be an empty list.

#### Scenario: All sections present
- **WHEN** a crash log contains all game-output anchor markers
- **THEN** all named keys in the output map contain the lines from their respective sections (excluding the anchor lines themselves)

#### Scenario: Missing section produces empty list
- **WHEN** a crash log is missing the `REGISTERS:` anchor
- **THEN** `registers` in the output map is an empty list and no error is raised

#### Scenario: No positional index access
- **WHEN** the orchestrator retrieves the callstack content
- **THEN** it accesses the map by key `callstack`, not by integer index

---

### Requirement: XSE modules sub-section is detected by position
Within the content between `MODULES:` and `PLUGINS:`, the engine SHALL detect a crashgen-owned sub-header as the boundary between `modules` (DLL list) and `xse_modules` (script extender plugins). A sub-header is any line whose trimmed content starts with `[` or matches the pattern `ALL-CAPS-WORD(S):` followed by nothing or only whitespace. Lines before the sub-header belong to `modules`; lines from the sub-header onward (exclusive) belong to `xse_modules`.

#### Scenario: F4SE PLUGINS sub-header splits modules correctly
- **WHEN** the MODULES section contains DLL lines followed by `F4SE PLUGINS:` followed by XSE plugin lines
- **THEN** `modules` contains the DLL lines and `xse_modules` contains the XSE plugin lines

#### Scenario: Unknown XSE sub-header splits modules correctly
- **WHEN** the MODULES section contains a sub-header not previously known (e.g., `NEWMOD PLUGINS:`)
- **THEN** `modules` contains lines before the sub-header and `xse_modules` contains lines after

#### Scenario: No sub-header leaves xse_modules empty
- **WHEN** the MODULES section contains no sub-header line
- **THEN** `modules` contains all lines and `xse_modules` is an empty list

---

### Requirement: Settings section bracket header is captured as metadata
If a crashgen-owned bracket header (e.g., `[Compatibility]`, `[Patches]`) is present in the settings section, the engine SHALL capture it as a `settings_header` metadata field alongside the named segment map. This field is for display and registry lookup purposes only.

#### Scenario: Known header is captured
- **WHEN** a log contains `[Compatibility]` as the first non-empty line before `SYSTEM SPECS:`
- **THEN** `settings_header` is `"[Compatibility]"` (trimmed)

#### Scenario: Unknown header is captured without error
- **WHEN** a log contains `[UnknownHeader]` as the first bracket line before `SYSTEM SPECS:`
- **THEN** `settings_header` is `"[UnknownHeader]"` and no error is raised

#### Scenario: No header leaves field absent or empty
- **WHEN** no bracket line exists before `SYSTEM SPECS:`
- **THEN** `settings_header` is an empty string or absent from metadata

---

### Requirement: Incomplete log detection uses named segment presence
The engine SHALL classify a log as incomplete when the `plugins` segment is empty (no lines). Classification SHALL use the named map key, not a positional index.

#### Scenario: Empty plugins segment triggers incomplete classification
- **WHEN** the `plugins` named segment is empty
- **THEN** the log is classified as incomplete

#### Scenario: Non-empty plugins segment is not incomplete
- **WHEN** the `plugins` named segment contains at least one line
- **THEN** the log is not classified as incomplete on that basis
