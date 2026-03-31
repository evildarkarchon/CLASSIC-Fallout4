## Purpose

Define the maintained `Mods_SOLU` configuration contract as an ordered structured entry format that preserves YAML order, supports grouped detection criteria with exceptions, drives report rendering from explicit fields, and remains visible through binding-facing APIs.

## Requirements

### Requirement: Mods_SOLU entries use a structured ordered schema
`Mods_SOLU` SHALL be represented as an ordered sequence of structured entries instead of a `mapping[string] -> string`. Each entry SHALL include a stable `id`, a `criteria` group, a readable `name`, and a `description`, and MAY include an `exceptions` list. The loaded representation SHALL preserve YAML order so report output remains deterministic.

#### Scenario: Structured entries preserve order and fields
- **WHEN** the YAML `Mods_SOLU` section contains multiple structured entries with `id`, `criteria`, `name`, `description`, and optional `exceptions`
- **THEN** configuration loading exposes the same entries in YAML order with those fields preserved as structured data

### Requirement: Mods_SOLU criteria support grouped any/all matching with exceptions
Each `Mods_SOLU` entry SHALL define `criteria` as exactly one grouped matcher: `any` or `all`. Each criterion item SHALL be matched case-insensitively as a substring against plugin filenames. An `any` matcher SHALL report the entry when at least one listed criterion matches an installed plugin. An `all` matcher SHALL report the entry only when every listed criterion matches at least one installed plugin. If an entry defines `exceptions`, the entry SHALL NOT be reported when any exception substring matches an installed plugin filename.

#### Scenario: Any criteria match reports an entry
- **WHEN** a `Mods_SOLU` entry defines `criteria.any` with multiple substrings and at least one of them matches an installed plugin filename
- **THEN** the entry is considered detected

#### Scenario: All criteria require every substring
- **WHEN** a `Mods_SOLU` entry defines `criteria.all` with multiple substrings and one or more listed substrings are absent from installed plugin filenames
- **THEN** the entry is not considered detected

#### Scenario: Exception suppresses an otherwise valid match
- **WHEN** a `Mods_SOLU` entry's criteria match installed plugins but one of its `exceptions` substrings also matches an installed plugin filename
- **THEN** the entry is not reported

### Requirement: Mods_SOLU report entries use explicit name and description fields
When a `Mods_SOLU` entry is detected, report generation SHALL use the structured `name` as the displayed mod title and the structured `description` as the body content. The report pipeline SHALL NOT infer the title by splitting the first line from a free-form warning blob.

#### Scenario: Structured fields render without first-line parsing
- **WHEN** a detected `Mods_SOLU` entry includes a `name` and a multi-line `description`
- **THEN** the report displays the `name` as the entry title and the `description` as the body without deriving either field from line splitting rules

### Requirement: Binding-facing config APIs expose structured Mods_SOLU entries
Binding-facing configuration surfaces for `YamlDataCore` SHALL expose `Mods_SOLU` as structured ordered entries rather than as separate key/value collections. Each exposed entry SHALL include `id`, grouped `criteria`, `exceptions`, `name`, and `description` so non-Rust consumers can inspect the same structured data used by report generation.

#### Scenario: Structured Mods_SOLU entries are visible outside Rust core
- **WHEN** Node, Python, or C++ consumers read `Mods_SOLU` from loaded configuration data
- **THEN** they receive structured entries with the same ids, criteria groups, exceptions, names, descriptions, and ordering as the YAML source
