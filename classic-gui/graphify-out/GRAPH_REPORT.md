# Graph Report - D:\repos\CLASSIC-Fallout4\classic-gui  (2026-07-28)

## Corpus Check
- Corpus is ~45,069 words - fits in a single context window. You may not need a graph.

## Summary
- 1488 nodes · 2608 edges · 78 communities (75 shown, 3 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 144 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 75
- Community 76

## God Nodes (most connected - your core abstractions)
1. `MainWindow` - 133 edges
2. `SettingsDialog` - 86 edges
3. `ResultsController` - 44 edges
4. `ScanSettingsWiringTests` - 41 edges
5. `ScanController` - 34 edges
6. `GameSetupUserSettingsSnapshot` - 30 edges
7. `ReportListWidget` - 30 edges
8. `MarkdownViewer` - 28 edges
9. `GuiUserSettingsChanges` - 27 edges
10. `GuiUserSettingsSnapshot` - 24 edges

## Surprising Connections (you probably didn't know these)
- `classic_gui_find_qt6` --semantically_similar_to--> `Shared Qt 6 Resolution Policy`  [INFERRED] [semantically similar]
  cmake/qt-policy-check/CMakeLists.txt → CMakeLists.txt
- `SettingsDialogBehaviorTests::cancel_discards_widget_changes_without_writing()` --references--> `SettingsDialog`  [INFERRED]
  tests/test_settingsdialog_behavior.cpp → src/app/settingsdialog.h
- `concurrent_change_surfaces_conflict_and_preserves_newer_values` --references--> `SettingsDialog`  [INFERRED]
  tests/test_settingsdialog_behavior.cpp → src/app/settingsdialog.h
- `formid_add_button_accepts_multiple_files_and_deduplicates_paths` --references--> `SettingsDialog`  [INFERRED]
  tests/test_settingsdialog_behavior.cpp → src/app/settingsdialog.h
- `ok_bootstraps_missing_settings_with_the_selected_vr_executable` --references--> `SettingsDialog`  [INFERRED]
  tests/test_settingsdialog_behavior.cpp → src/app/settingsdialog.h

## Import Cycles
- None detected.

## Communities (78 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (64): QMainWindow, BackupController, FeatureContext, GameFilesController, GuiWindow, Q_OBJECT, QElapsedTimer, QLabel (+56 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (51): QFileSystemWatcher, ReportMetadataWidget, MarkdownViewer, QObject, QString, QStringList, ReportListWidget, SignalHub (+43 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (46): scanner::ScanRunObserver, ScanRunContractDiscoverySource, ScanRunGameId, CrashLogScanLaunchSettings, customScanDirectory, fcxMode, formIdDatabasePaths, formIdValueLookup (+38 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (40): string, registerBundledFonts(), QString, String, toQString(), toRustString(), QString, string (+32 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (44): QComboBox, QSpinBox, Q_OBJECT, QDialog, QLabel, QLineEdit, QListWidget, QPushButton (+36 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (42): QObject, QString, QStringList, ScanRunLocalIgnoreRecoveryChoice, ScanRunLocalIgnoreRecoveryPrompt, SignalHub, ThreadManager, Q_OBJECT (+34 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (41): Q_OBJECT, QObject, ScanSettingsWiringTests, controllers_emit_global_scan_started_signal_on_scan_start, game_files_controller_forwards_game_version_to_worker, game_files_worker_catches_non_standard_exceptions, game_files_worker_forwards_game_version_to_setup_intake, game_files_worker_marks_required_actions_as_attention (+33 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (36): ResultsController, Q_OBJECT, QListWidget, QObject, QString, QStringList, ReportListWidget, findReportList() (+28 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (35): QSet, QString, QStringList, QWidget, Q_OBJECT, QLineEdit, QListWidget, QPushButton (+27 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (32): initializer_list, LogProgressState, ScanRunContractEventKind, ScanRunContractProgressPhase, BatchProgressModel, contributionFor, effectiveConcurrency, m_effectiveConcurrency (+24 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (35): QElapsedTimer, QString, QStringList, QWidget, ScanRunLocalIgnoreYamlDataState, format_elapsed_seconds(), formatUserSettingsDiagnostics(), localIgnoreStateLabel() (+27 more)

### Community 11 - "Community 11"
Cohesion: 0.10
Nodes (32): QString, QStringList, QWidget, SignalHub, applySettingsToWidgets, canCloseDialog, closeEvent, ensureYamlUpdateWorker (+24 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (28): classic_gui_find_qt6, ClassicGui Qt Policy Check Project, ClassicGui Corrosion Rust Bridge, ClassicGui CMake Project, GUI Bundled Version Identity, Shared Qt 6 Resolution Policy, Inter OFL License Document, OFL Redistribution Conditions (+20 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (23): QTemporaryDir, QString, normalizeGameExecutablePath(), Q_OBJECT, QObject, GamePathUtilsTests, emptyRootLeavesExecutableUnchanged, executableOutsideRootUsesDefault (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (26): ScanRunLocalIgnoreRecoveryChoice, localYamlFilePath(), logUpdateCheckFailure(), checkFirstRunPaths, checkForUpdates, connectSignals, initializeControllers, installTargetedDropForwarding (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.19
Nodes (25): GuiSettingsSnapshotDto, applyFormIdDatabases(), applySelection(), optional, QMap, QString, QStringList, string (+17 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (23): QThread, QObject, QString, Q_DISABLE_COPY_MOVE, Q_OBJECT, QObject, QString, ThreadManager (+15 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (23): QObject, QString, SignalHub, ThreadManager, GameFilesController, GameFilesController::GameFilesController(), isScanning, m_scanning (+15 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (24): QObject, QString, Q_OBJECT, QObject, signals, UpdateWorker, checkForUpdates, kClassificationDeprecated (+16 more)

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (20): QRect, QSize, QStyleOptionProgressBar, QCheckBox, AdaptiveProgressBar, AdaptiveProgressBar::AdaptiveProgressBar(), paintEvent, QPaintEvent (+12 more)

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (22): ScanRunContractLogDisposition, ScanRunContractStatus, Q_OBJECT, QObject, ScanRunContractExecutionResult, ScanRunContractLogResult, size_t, executionWithStatus() (+14 more)

### Community 21 - "Community 21"
Cohesion: 0.10
Nodes (23): QString, QWidget, Q_OBJECT, QDialog, QLabel, QPushButton, signals, PapyrusDialog (+15 more)

### Community 22 - "Community 22"
Cohesion: 0.09
Nodes (23): GameSetupUserSettingsSnapshot, classification, commitEligibility, customScanInput, customScanInputOrigin, diagnostics, documentsRoot, documentsRootOrigin (+15 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (21): ScanRunContractDiscoveryResult, ScanRunContractInfrastructureErrorStage, ScanRunContractLogFailureStage, ScanRunContractRunResult, ScanRunInspectedYamlDataFileDto, ScanRunInstalledYamlDataRunDataDto, ScanRunLocalIgnoreResetFailureStage, QString (+13 more)

### Community 24 - "Community 24"
Cohesion: 0.10
Nodes (22): GuiUserSettingsChanges, autoSwitchAfterScan, documentsRoot, fcxMode, formIdDatabases, formIdValueLookup, gameExecutable, gameRoot (+14 more)

### Community 25 - "Community 25"
Cohesion: 0.22
Nodes (21): QTimer, acceptNextQuestion(), closeNextMessageBox(), Q_OBJECT, QByteArray, QObject, QPushButton, QString (+13 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (10): QVector, QListWidget, QString, QStringList, QObject, QSet, QObject, SignalHub::SignalHub() (+2 more)

### Community 27 - "Community 27"
Cohesion: 0.16
Nodes (19): BackupController, backup, BackupController::BackupController(), backupExists, gameRoot, m_gameRoot, m_signalHub, operationError (+11 more)

### Community 28 - "Community 28"
Cohesion: 0.10
Nodes (21): GuiGameSetupSettings, documentsRoot, gameExecutable, gameRoot, iniFolder, managedGame, modsRoot, papyrusLog (+13 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (18): QLineEdit, QString, QWidget, Q_OBJECT, QDialog, QLineEdit, ManualPathDialog, docsPath (+10 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (19): GameSetupPathProposal, kind, path, GameSetupUserSettingsCommitResult, actualRevision, diagnostics, expectedRevision, revision (+11 more)

### Community 31 - "Community 31"
Cohesion: 0.27
Nodes (18): applySelection(), commitUpdate(), optional, QString, string, UserSettingsUpdateDto, GameSetupUserSettings, bootstrap (+10 more)

### Community 32 - "Community 32"
Cohesion: 0.11
Nodes (19): Box, Q_OBJECT, QObject, ScanRunCancellation, ScanRunLocalIgnoreRecoveryPrompt, ScanWorker, cancelled, discoveryCompleted (+11 more)

### Community 33 - "Community 33"
Cohesion: 0.23
Nodes (17): completeSettings(), Q_OBJECT, QByteArray, QObject, QString, GameSetupUserSettingsTests, accepted_paths_commit_as_one_user_settings_update, explicit_bootstrap_commits_rust_defaults (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.25
Nodes (18): containsNativeYamlRecipeDuplication(), Q_OBJECT, QObject, QString, readFile(), YamlUpdateWiringTests, cli_handler_reads_update_check_setting_and_forwards_to_bridge, cli_registers_yaml_update_flags_and_dispatches_before_scan (+10 more)

### Community 35 - "Community 35"
Cohesion: 0.12
Nodes (18): ScanRunInstalledYamlDataRole, ScanRunInstalledYamlDataDiagnosticKind, ScanRunInstalledYamlDataProvenance, ScanRunInstalledYamlDataDiagnosticPresentation, candidate, hasCandidate, hasPath, hasRole (+10 more)

### Community 36 - "Community 36"
Cohesion: 0.11
Nodes (18): Q_OBJECT, QLabel, QPushButton, QWidget, MarkdownViewer, copyAllRequested, kBasePointSize, kZoomMax (+10 more)

### Community 37 - "Community 37"
Cohesion: 0.16
Nodes (16): qint64, QString, QWidget, Q_OBJECT, QLabel, QWidget, ReportMetadataWidget, clear (+8 more)

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (15): QTextEdit, QString, QWidget, ErrorDialog, copyDetails, ErrorDialog::ErrorDialog(), m_copyButton, m_detailsEdit (+7 more)

### Community 39 - "Community 39"
Cohesion: 0.21
Nodes (16): MarkdownViewer, Q_OBJECT, QLabel, QObject, QPushButton, QString, findButtonByText(), findZoomLabel() (+8 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (16): UserSettingsDiagnosticDto, UserSettingsUpdateDiagnosticDto, Vec, vector, diagnosticsFrom(), GuiUserSettingsCommitResult, actualRevision, diagnostics (+8 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (15): onYamlCheckFinished, onYamlRollbackFinished, QStringList, YamlCheckResult, compatibleFileNames, compatibleFileSha256, detail, incompatibleFileNames (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.17
Nodes (11): QObject, QString, QStringList, ScanRunContractEvent, ScanRunLocalIgnoreRecoveryPrompt, eventStatus(), doScan, m_localIgnoreRecoveryPrompt (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.30
Nodes (14): completeSettings(), Q_OBJECT, QByteArray, QObject, QString, GuiUserSettingsTests, accepted_changes_commit_as_one_preservation_aware_update, frontend_transition_retries_once_and_refreshes_the_consumed_snapshot (+6 more)

### Community 44 - "Community 44"
Cohesion: 0.14
Nodes (14): Q_DISABLE_COPY_MOVE, Q_OBJECT, QObject, SignalHub, fileWatchTriggered, gameChanged, public, scanCancelled (+6 more)

### Community 45 - "Community 45"
Cohesion: 0.23
Nodes (12): Q_OBJECT, QObject, MainWindowGeometryTests, crash_scan_status_bar_tracks_scan_statistics, custom_folder_handlers_refresh_results_directories, entering_results_tab_forces_report_reload, first_run_bootstraps_and_updates_local_yaml, first_run_path_detection_treats_invalid_directories_as_unresolved (+4 more)

### Community 46 - "Community 46"
Cohesion: 0.19
Nodes (9): QTextBrowser, QLabel, QWidget, Q_OBJECT, QObject, ReportMetadataWidgetTests, formatFileSize_formats_bytes_kb_and_mb, private (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.21
Nodes (12): GuiFrontendPreferences, autoSwitchAfterScan, windowGeometry, GuiWindowGeometry, height, maximized, width, GuiWindowGeometryChange (+4 more)

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (12): QString, QWidget, applyContentStylesheet, applyZoom, clear, MarkdownViewer::MarkdownViewer(), plainText, setMarkdownContent (+4 more)

### Community 49 - "Community 49"
Cohesion: 0.17
Nodes (11): QObject, QString, GameFilesWorker, doScan, error, finished, GameFilesWorker::GameFilesWorker(), progress (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.17
Nodes (12): quint32, GameSetupUserSettingsIntakeResult, actionCount, documentsRoot, failedChecks, gameExecutable, gameRoot, hasErrors (+4 more)

### Community 51 - "Community 51"
Cohesion: 0.17
Nodes (12): ScanRunTerminalKind, ScanRunTerminalPresentation, cancelled, failed, hasInstalledYamlData, installedYamlData, kind, logs (+4 more)

### Community 52 - "Community 52"
Cohesion: 0.17
Nodes (12): GuiCrashLogScanSettings, customScanInput, fcxMode, formIdDatabases, formIdValueLookup, gameVersion, maxConcurrentScans, moveUnsolvedLogs (+4 more)

### Community 53 - "Community 53"
Cohesion: 0.26
Nodes (10): Q_OBJECT, QObject, ScanWorkerCancellationTests, completed_run_publishes_installed_yaml_data_beyond_terminal_projection, malformed_local_ignore_recovery_resumes_or_cancels_retained_scan_run, malformed_local_ignore_recovery_resumes_or_cancels_retained_scan_run_data, private, requestCancel_alone_emits_no_signals (+2 more)

### Community 54 - "Community 54"
Cohesion: 0.23
Nodes (11): Q_OBJECT, QObject, Vec, makeEntries(), YamlUpdateBridgeTests, private, YamlUpdateBridgeTests::yaml_check_update_disabled_short_circuits(), yaml_data_check_update_disabled_short_circuits (+3 more)

### Community 55 - "Community 55"
Cohesion: 0.20
Nodes (11): QString, quint64, ScanRunLocalIgnoreResetPresentation, backupIdentity, backupPath, localIgnorePath, malformedIdentity, replacementIdentity (+3 more)

### Community 56 - "Community 56"
Cohesion: 0.18
Nodes (11): QStringList, ScanRunLogPresentation, autoscanReport, cancelledBeforeStart, crashLog, discoveryIndex, failed, failures (+3 more)

### Community 57 - "Community 57"
Cohesion: 0.24
Nodes (7): AboutDialog, AboutDialog::AboutDialog(), public, QWidget, Q_OBJECT, QDialog, QPushButton

### Community 58 - "Community 58"
Cohesion: 0.28
Nodes (9): QEvent, QObject, dragEnterEvent, dragMoveEvent, eventFilter, handleTargetedDragEnter, handleTargetedDragMove, QDragEnterEvent (+1 more)

### Community 59 - "Community 59"
Cohesion: 0.31
Nodes (7): FeatureContext, mainWindow, signalHub, threadManager, MainWindow, SignalHub, ThreadManager

### Community 60 - "Community 60"
Cohesion: 0.22
Nodes (9): ScanRunLocalIgnoreYamlDataState, ScanRunInstalledYamlDataPresentation, diagnostics, gameFile, hasLocalIgnoreReset, localIgnoreIdentity, localIgnoreReset, localIgnoreState (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.25
Nodes (8): qsizetype, onYamlApplyFinished, QString, YamlApplyResult, errorMessage, failed, firstFailureReason, installed

### Community 62 - "Community 62"
Cohesion: 0.25
Nodes (7): qttranslations, builtin-baseline, dependencies, description, name, $schema, version

### Community 63 - "Community 63"
Cohesion: 0.25
Nodes (8): GameSetupPathChanges, customScanInput, documentsRoot, gameExecutable, gameRoot, iniFolder, modsRoot, papyrusLog

### Community 64 - "Community 64"
Cohesion: 0.32
Nodes (6): Q_OBJECT, QObject, SignalHubTests, private, scanProgress_signal_carries_expected_payload, scanStarted_signal_is_emitted

### Community 65 - "Community 65"
Cohesion: 0.38
Nodes (4): ConvertTo-TestNameList(), Get-WindowsResourceCompiler(), New-ExactTestNameRegex(), Test-WindowsSdkEnvironment()

### Community 66 - "Community 66"
Cohesion: 0.38
Nodes (6): ScanWorker, ScanRunCancellation, ScanRunObserver, GuiScanRunObserver, m_deliveryFailed, m_progress

### Community 67 - "Community 67"
Cohesion: 0.40
Nodes (6): RememberedPath, onBrowseCustom, onBrowseStaging, onCustomFolderEdited, saveRememberedPath, validateCustomScanFolder

### Community 68 - "Community 68"
Cohesion: 0.40
Nodes (6): acknowledgeTargetedDrop, dropEvent, handleTargetedDrop, onClearTargetedInputs, updateTargetedInputUi, QDropEvent

### Community 69 - "Community 69"
Cohesion: 0.40
Nodes (5): ScanRunInstalledYamlDataDiagnosticKind, ScanRunInstalledYamlDataProvenance, installedYamlDataDiagnosticKindLabel(), installedYamlDataProvenanceLabel(), onScanInstalledYamlDataResolved

### Community 70 - "Community 70"
Cohesion: 0.40
Nodes (5): UserSettingsDiagnosticDto, UserSettingsUpdateDiagnosticDto, Vec, vector, diagnosticsFrom()

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (3): QStringList, TestableSettingsDialog, selectedDatabases

### Community 72 - "Community 72"
Cohesion: 0.50
Nodes (4): GuiWindow, GuiWindowToken, token, window

## Knowledge Gaps
- **465 isolated node(s):** `public`, `public`, `m_iconLabel`, `m_messageLabel`, `m_detailsEdit` (+460 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MainWindow` connect `Community 0` to `Community 67`, `Community 68`, `Community 58`, `Community 69`, `Community 10`, `Community 11`, `Community 46`, `Community 14`, `Community 60`, `Community 19`, `Community 26`, `Community 28`, `Community 29`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Why does `SettingsDialog` connect `Community 4` to `Community 71`, `Community 41`, `Community 11`, `Community 14`, `Community 19`, `Community 25`, `Community 28`, `Community 61`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `SettingsDialog` (e.g. with `SettingsDialogBehaviorTests::cancel_discards_widget_changes_without_writing()` and `concurrent_change_surfaces_conflict_and_preserves_newer_values`) actually correct?**
  _`SettingsDialog` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `public`, `public`, `m_iconLabel` to the rest of the system?**
  _465 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.03653846153846154 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07619738751814223 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.053544494720965306 - nodes in this community are weakly interconnected._