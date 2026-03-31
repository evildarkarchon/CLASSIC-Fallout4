## ADDED Requirements

### Requirement: Batch scan progress reflects in-flight work
The batch crash-log scan workflow SHALL report user-visible progress from monotonic in-flight work states rather than from completed-log counts alone.

#### Scenario: Long-running logs continue batch progress before completion
- **WHEN** a batch scan has active logs that remain in progress for materially longer than other logs in the batch
- **THEN** the reported batch progress SHALL continue to advance based on those logs reaching defined work states before they fully complete

#### Scenario: Completed logs still advance terminal progress
- **WHEN** an individual log completes successfully or fails terminally
- **THEN** the batch progress model SHALL advance to reflect that completed work without decreasing previously reported progress

### Requirement: Batch scan exposes coarse per-log lifecycle states
The batch scan workflow SHALL expose a stable coarse-grained lifecycle for each log sufficient to distinguish queued, active, and terminal work during GUI scans.

#### Scenario: Queued logs are distinguishable from running logs
- **WHEN** a batch scan begins with more discovered logs than active worker slots
- **THEN** the progress reporting surface SHALL distinguish logs that are waiting to start from logs that are actively being processed

#### Scenario: Running logs publish monotonic phase updates
- **WHEN** an active log moves through the defined scan lifecycle
- **THEN** each emitted state transition SHALL be monotonic and SHALL NOT move the log back to an earlier phase

#### Scenario: Failed logs publish terminal state
- **WHEN** an active log fails during any scan phase
- **THEN** the progress reporting surface SHALL publish a terminal failed state for that log and continue reporting overall batch progress for the remaining logs

### Requirement: GUI progress presentation communicates long-tail work clearly
The GUI crash-log scan presentation SHALL communicate batch progress in a way that does not imply a frozen scan solely because no log has completed recently, while preserving a simple log-focused status presentation.

#### Scenario: Mid-batch heavy logs do not appear frozen
- **WHEN** the active worker set is dominated by a small number of heavier logs in the middle of a batch
- **THEN** the GUI progress presentation SHALL continue to indicate active work and SHALL NOT rely only on whole-log completions to update the visible percent complete

#### Scenario: Status text remains simple
- **WHEN** the GUI displays batch scan progress
- **THEN** the status presentation SHALL be allowed to remain focused on overall progress and the current log name without exposing detailed internal lifecycle categories to the user
