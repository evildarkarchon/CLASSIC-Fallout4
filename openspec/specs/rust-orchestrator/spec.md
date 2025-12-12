# rust-orchestrator Specification

## Purpose
TBD - created by archiving change add-rust-orchestrator-parity. Update Purpose after archive.
## Requirements
### Requirement: Report Generation Parity
The Rust orchestrator MUST generate identical report output to Python OrchestratorCore, including headers, footers, error sections, and section separators.

#### Scenario: Report output matches Python
- **WHEN** a crash log is processed by Rust orchestrator
- **THEN** the generated report lines MUST be byte-for-byte identical to Python OrchestratorCore output

### Requirement: Version Checking
The Rust orchestrator MUST check crashgen version and generate version warnings when outdated.

#### Scenario: Outdated version detected
- **WHEN** crashgen version is older than latest known version
- **THEN** the report MUST include a version warning message

### Requirement: Settings Validation Integration
The Rust orchestrator MUST integrate SettingsValidator for crashgen settings analysis (memory settings, achievements, archive limit, looksmenu).

#### Scenario: Settings issues detected
- **WHEN** crashgen settings contain configuration issues
- **THEN** the report MUST include appropriate warnings from SettingsValidator

### Requirement: Record Scanner Integration
The Rust orchestrator MUST integrate RecordScanner for named record detection in crash callstacks.

#### Scenario: Named record found
- **WHEN** callstack contains known record patterns
- **THEN** the report MUST include matched record information

### Requirement: FCX Mode Support
The Rust orchestrator MUST support FCX mode configuration checking for detecting game configuration issues.

#### Scenario: FCX mode enabled
- **WHEN** fcx_mode is True in AnalysisConfig
- **THEN** configuration issue detection MUST be performed

### Requirement: Database Pool Support
The Rust orchestrator MUST support optional database pool for async FormID lookups to retrieve editor IDs.

#### Scenario: Database pool available
- **WHEN** database pool is attached via with_database_pool()
- **THEN** FormID lookups MUST resolve editor IDs from database

### Requirement: LoadOrder File Support
The Rust orchestrator MUST support loadorder.txt for plugin list override.

#### Scenario: LoadOrder file exists
- **WHEN** loadorder.txt exists in crash log directory
- **THEN** plugins MUST be loaded from loadorder.txt instead of crash log

### Requirement: FOLON Detection
The Rust orchestrator MUST detect FOLON (Fallout: London) by checking for londonworldspace.esm and use appropriate mod database.

#### Scenario: FOLON detected
- **WHEN** londonworldspace.esm is found in plugins
- **THEN** mods_core_folon database MUST be used for mod detection

### Requirement: Statistics Tracking
Rust AnalysisResult MUST include scanned, incomplete, failed counters and trigger_scan_failed flag for parity with Python.

#### Scenario: Statistics populated
- **WHEN** crash log processing completes
- **THEN** AnalysisResult MUST contain accurate scanned/incomplete/failed counts

### Requirement: Context Manager Support
The Rust orchestrator MUST support async_enter and async_exit methods for resource initialization and cleanup.

#### Scenario: Context manager lifecycle
- **WHEN** async_enter is called
- **THEN** database pool MAY be initialized from provided paths

### Requirement: Feature Completeness Detection
The Rust orchestrator MUST expose is_feature_complete() method for capability detection.

#### Scenario: Feature complete check
- **WHEN** is_feature_complete() is called
- **THEN** it MUST return True if plugin_analyzer and suspect_scanner are both available

### Requirement: Batch Report Writing
The Rust orchestrator MUST support write_reports_batch for concurrent report file writing.

#### Scenario: Batch reports written
- **WHEN** write_reports_batch is called with report data
- **THEN** reports MUST be written concurrently to files with -AUTOSCAN.md suffix

