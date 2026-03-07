## ADDED Requirements

### Requirement: Per-crashgen registry is the single source of settings configuration
The system SHALL maintain a per-crashgen registry keyed by crashgen name. Each registry entry SHALL declare: `display_section` (string, the bracket header name used by this crashgen, for display only), `ignore_keys` (list of settings keys to exclude from disabled-settings checks), and `checks` (list of named check identifiers to run for this crashgen). The registry SHALL include a `default` entry that applies to any crashgen not explicitly registered.

#### Scenario: Known crashgen resolves its entry
- **WHEN** the parsed crashgen name is `"Buffout 4"`
- **THEN** the registry returns the `"Buffout 4"` entry including its ignore_keys and checks list

#### Scenario: Unknown crashgen falls back to default
- **WHEN** the parsed crashgen name does not match any registry key
- **THEN** the registry returns the `default` entry

#### Scenario: Name lookup is case-insensitive and whitespace-normalized
- **WHEN** the parsed crashgen name differs from the registry key only in whitespace or case (e.g., `"buffout4"` vs `"Buffout 4"`)
- **THEN** the correct registry entry is returned

---

### Requirement: check_disabled_settings runs for every crashgen
The system SHALL run `check_disabled_settings()` for every crash log regardless of which crashgen produced it, including crashgens not in the registry. `check_disabled_settings()` SHALL use the `ignore_keys` list from the resolved registry entry (which is empty for the `default` entry).

#### Scenario: Known crashgen with ignore list
- **WHEN** a Buffout 4 log is analyzed and its registry entry has `ignore_keys: [F4EE, Achievements, ...]`
- **THEN** `check_disabled_settings()` runs and skips those keys when flagging disabled settings

#### Scenario: Unknown crashgen with empty ignore list
- **WHEN** a log from an unregistered crashgen is analyzed
- **THEN** `check_disabled_settings()` runs with an empty ignore list, flagging all disabled settings

#### Scenario: Addictol with its own ignore list
- **WHEN** an Addictol log is analyzed and the Addictol registry entry has its own `ignore_keys`
- **THEN** `check_disabled_settings()` uses Addictol's ignore list, not Buffout 4's

---

### Requirement: Named checks run only for explicitly registered crashgens
The system SHALL run each named check (e.g., `achievements`, `memory_management`, `archive_limit`, `looksmenu`) only for crashgens that list it in their `checks` registry entry. No named check SHALL run for a crashgen that does not register it, including the `default` entry.

#### Scenario: Buffout 4 named checks run
- **WHEN** a Buffout 4 log is analyzed and the registry entry lists `checks: [achievements, memory_management, archive_limit, looksmenu]`
- **THEN** all four named checks are executed

#### Scenario: Addictol named checks do not run
- **WHEN** an Addictol log is analyzed and the registry entry lists `checks: []`
- **THEN** no named checks run; only `check_disabled_settings()` executes

#### Scenario: Default entry produces no named checks
- **WHEN** a log from an unregistered crashgen is analyzed
- **THEN** no named checks run; only `check_disabled_settings()` executes

---

### Requirement: Registry is configurable via YAML without code changes
The registry SHALL be driven by YAML configuration in `CLASSIC Fallout4.yaml` (and equivalent game-specific YAML files). Adding a new crashgen entry, updating its ignore list, or assigning existing named checks to it SHALL require only a YAML change. Implementing a new named check SHALL require a code change.

#### Scenario: New crashgen entry added via YAML
- **WHEN** a new crashgen entry is added to the YAML registry with an `ignore_keys` list and `checks: []`
- **THEN** logs from that crashgen use the new entry without any code deployment

#### Scenario: Existing named check assigned to new crashgen
- **WHEN** an already-implemented named check (e.g., `achievements`) is added to a new crashgen's `checks` list in YAML
- **THEN** that check runs for the new crashgen without any code change

---

### Requirement: display_section is metadata only and does not affect analysis
The `display_section` field in a registry entry (e.g., `"[Compatibility]"`, `"[Patches]"`) SHALL be used only for constructing human-readable report output. It SHALL NOT affect segmentation, settings key parsing, or check routing.

#### Scenario: Report output uses display_section
- **WHEN** a settings check produces a warning for a Buffout 4 log
- **THEN** the warning message references `[Compatibility]` from the registry entry's `display_section`

#### Scenario: display_section change does not affect checks
- **WHEN** a registry entry's `display_section` is changed
- **THEN** all checks and ignore behavior remain identical
