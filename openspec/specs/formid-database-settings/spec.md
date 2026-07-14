# Capability: formid-database-settings

## Purpose

Define how the native GUI edits per-game additional FormID database paths and carries the accepted typed values into Crash Log Scan startup.

## Requirements

### Requirement: Display additional FormID databases per game

The GUI Settings dialog Paths tab SHALL display an "Additional FormID Databases" list of user-managed database paths for the active game, loaded from the typed Crash Log Scan settings group whose canonical persistence path is `CLASSIC_Settings.FormID Databases.<game>`. The built-in Main database is always included at scan time and SHALL NOT appear in this user-managed list.

#### Scenario: List is populated from the active game's settings on open

- **WHEN** the Settings dialog is opened for an active game that has stored additional database paths
- **THEN** each stored path appears as a list entry, and the built-in Main database is not among them

#### Scenario: Reset to defaults clears the user-managed list

- **WHEN** the user resets settings to defaults
- **THEN** the additional FormID databases list is cleared

### Requirement: Add one or more databases in a single dialog action

The "Add..." action SHALL open a multi-select file dialog that lets the user choose one or more database files at once, and SHALL append every chosen file to the list as a separate entry, preserving selection order.

#### Scenario: User selects multiple files

- **WHEN** the user selects two or more files in the Add dialog and confirms
- **THEN** every selected file is appended to the list, in the order selected

#### Scenario: User selects a single file

- **WHEN** the user selects exactly one file in the Add dialog and confirms
- **THEN** that file is appended to the list

#### Scenario: User cancels the Add dialog

- **WHEN** the user dismisses the Add dialog without selecting files
- **THEN** the list is unchanged

### Requirement: Skip duplicate database paths on add

When appending chosen files, the Add action SHALL NOT create a duplicate entry for any file whose normalized path already exists in the list. Duplicate paths SHALL be silently skipped without removing or altering existing entries.

#### Scenario: A selected file is already listed

- **WHEN** the user's selection includes a file whose normalized path matches an existing list entry (case-insensitive)
- **THEN** that file is not added a second time, and the existing entry is unchanged

#### Scenario: Every selected file is already listed

- **WHEN** every file in the user's selection already matches an existing list entry
- **THEN** no new entries are added and the list is unchanged

#### Scenario: Mixed new and duplicate selection

- **WHEN** the user's selection contains some new files and some already-listed files
- **THEN** only the new files are appended; the already-listed files are skipped

### Requirement: Remove a database entry

The "Remove" action SHALL delete the currently selected list entry. When no entry is selected, the action SHALL do nothing.

#### Scenario: Remove with a selected entry

- **WHEN** the user selects a list entry and activates Remove
- **THEN** that entry is removed from the list

#### Scenario: Remove with no selection

- **WHEN** the user activates Remove with no list entry selected
- **THEN** the list is unchanged

### Requirement: Persist the per-game database list on accept

On accept, the dialog SHALL include the complete per-game database map in the same revision-anchored typed User Settings Update as every other selected dialog change. The update SHALL persist the active game's current entries at the canonical key `CLASSIC_Settings.FormID Databases.<game>` as a sequence of path strings, preserve other games' lists, and restore the same list on the next open for that game.

#### Scenario: Save round-trips added databases

- **WHEN** the user adds one or more databases, saves, and reopens the Settings dialog for the same game
- **THEN** the previously added database paths are restored in the list

#### Scenario: Empty list persists as empty

- **WHEN** the user removes all additional databases, saves, and reopens the dialog for the same game
- **THEN** the additional databases list is empty

#### Scenario: Cancel does not persist list edits

- **WHEN** the user changes the additional database list and cancels the Settings dialog
- **THEN** no User Settings Update is committed and the persisted per-game lists are unchanged

#### Scenario: Another invalid selected setting rejects the complete update

- **WHEN** the database list is changed but another field in the same dialog update fails validation
- **THEN** no requested field is committed, including the database list

#### Scenario: Concurrent settings change is not overwritten

- **WHEN** User Settings changes after the dialog snapshot was opened and the user accepts a database-list edit
- **THEN** the dialog reports a revision conflict and the newer persisted document is left unchanged

### Requirement: Carry accepted FormID paths into scan startup

The GUI SHALL select the effective game's FormID database paths from its accepted typed settings snapshot and pass them to Crash Log Scan startup as immutable launch values. Scan launch SHALL NOT reread User Settings or interpret the canonical YAML key through generic settings operations.

#### Scenario: Accepted paths reach the scan request

- **WHEN** a Crash Log Scan starts after a settings snapshot containing additional databases has been accepted
- **THEN** the selected game's paths are present in `ScanRunRequestDto.formid_database_paths` in their configured order

#### Scenario: Other games remain excluded from the run

- **WHEN** the cohesive settings snapshot contains FormID database lists for multiple games
- **THEN** the scan request contains only the effective game's user-managed paths

#### Scenario: Scan workers use the launch snapshot

- **WHEN** the controller dispatches a Crash Log Scan to a worker
- **THEN** the worker receives the immutable typed launch values and does not reopen the User Settings document

### Requirement: Add dialog file filter and title

The Add dialog SHALL offer a database file filter (including database extensions and an all-files option) and SHALL use a plural window title indicating that more than one file may be selected.

#### Scenario: Filter and title presented

- **WHEN** the user opens the Add dialog
- **THEN** the dialog presents a database-extensions file filter plus an all-files option, and its window title is plural ("Select FormID Databases")
