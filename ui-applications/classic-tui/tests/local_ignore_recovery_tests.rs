//! End-to-end coverage for TUI Local Ignore recovery presentation and continuation ownership.
//!
//! These tests drive the real Rust-owned Crash Log Scan Run contract against isolated installation
//! roots built from the shared cross-language fixture corpus in
//! `tests/fixtures/crash_log_scan_run`. Nothing here reads or mutates the developer's own
//! installation, update cache, or Local Ignore data.
//!
//! The continuation cannot be fabricated, so a real paused run is the only way to prove that the
//! TUI owns it correctly. Each test therefore executes one genuine run, hands the paused result to
//! an `App`, and then exercises exactly one decision path.

use classic_config_core::InstalledYamlDataProvenance;
use classic_scanlog_core::scan_run::contract::{
    self, Cancellation, Configuration, InstalledYamlDataRunDiagnosticKind,
    LocalIgnoreRecoveryDecision, LocalIgnoreRunState, Options, Request, ResumeError, RunResult,
};
use classic_scanlog_core::{CrashLogScanFacts, CrashLogScanRunStatus, TargetedCrashLogScanSource};
use classic_shared_core::{GameId, get_runtime};
use classic_tui::app::{App, AsyncMessage, LastScanRun, Overlay};
use classic_vocabulary::Vocabulary;
use crossterm::event::{Event as TerminalEvent, KeyCode, KeyEvent, KeyModifiers};
use std::path::{Path, PathBuf};

const FIXTURE_ROOT: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/crash_log_scan_run"
);

/// Shared malformed payload from `fixtures.installedYamlData.malformedLocalIgnore` in the manifest.
const MALFORMED_LOCAL_IGNORE: &str = "CLASSIC_Ignore_Fallout4: [unterminated";

/// Copies the shared immutable YAML corpus into an isolated installation root.
fn installation_root() -> tempfile::TempDir {
    let temp = tempfile::tempdir().expect("temp installation root should be created");
    let fixture_root = Path::new(FIXTURE_ROOT);
    for relative in [
        "CLASSIC Data/CLASSIC Ignore.yaml",
        "CLASSIC Data/databases/CLASSIC Main.yaml",
        "CLASSIC Data/databases/CLASSIC Fallout4.yaml",
    ] {
        let target = temp.path().join(relative);
        std::fs::create_dir_all(target.parent().expect("fixture path should have a parent"))
            .expect("fixture directory should be created");
        std::fs::copy(fixture_root.join(relative), &target)
            .expect("shared YAML fixture should be copied");
    }
    temp
}

/// Materializes named Crash Logs from the shared valid-log template.
fn copy_logs(root: &Path, names: &[&str]) -> Vec<PathBuf> {
    let source = Path::new(FIXTURE_ROOT).join("valid-crash.log");
    names
        .iter()
        .map(|name| {
            let target = root.join("Crash Logs").join(name);
            std::fs::create_dir_all(target.parent().expect("log path should have a parent"))
                .expect("fixture log directory should be created");
            std::fs::copy(&source, &target).expect("shared Crash Log fixture should be copied");
            target
        })
        .collect()
}

/// Returns the canonical Local Ignore path inside one isolated installation root.
fn local_ignore_path(root: &Path) -> PathBuf {
    root.join("CLASSIC Data").join("CLASSIC Ignore.yaml")
}

/// Replaces the valid fixture Ignore file with the shared malformed payload.
///
/// Returns the exact bytes written so later assertions can prove the file was left alone.
fn malform_local_ignore(root: &Path) -> Vec<u8> {
    let path = local_ignore_path(root);
    std::fs::write(&path, MALFORMED_LOCAL_IGNORE).expect("malformed fixture should be written");
    std::fs::read(&path).expect("malformed fixture should be readable")
}

/// Builds the run configuration from one explicit installation root.
fn configuration(root: &Path) -> Configuration {
    Configuration {
        installation_root: root.to_path_buf(),
        game: GameId::Fallout4,
        game_version: "auto".to_string(),
        options: Options::new(false, false),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(2),
    }
}

/// Executes one real Crash Log Scan Run that pauses on the malformed Local Ignore file.
fn paused_run(root: &Path, logs: Vec<PathBuf>, cancellation: &Cancellation) -> RunResult {
    let request = Request::targeted(
        configuration(root),
        TargetedCrashLogScanSource { inputs: logs },
    );
    let result = get_runtime()
        .block_on(contract::execute(request, cancellation, None))
        .expect("malformed Local Ignore is expected result data, not an infrastructure error");
    assert_eq!(
        result.status,
        CrashLogScanRunStatus::LocalIgnoreRecoveryRequired
    );
    result
}

/// Hands one genuinely paused run to a TUI that owns the same cancellation control.
fn app_awaiting_recovery(paused: RunResult, cancellation: Cancellation) -> App {
    let mut app = App::new_for_testing();
    app.scan_cancellation = Some(cancellation);
    app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(paused))));

    assert_eq!(app.active_overlay, Some(Overlay::LocalIgnoreRecovery));
    assert!(
        app.pending_local_ignore_recovery.is_some(),
        "a paused run must retain its continuation in non-cloneable application state"
    );
    app
}

/// One paused-and-awaiting-decision TUI over a fresh isolated installation root.
struct PausedFixture {
    /// Owns the isolated installation root for the lifetime of the test.
    temp: tempfile::TempDir,
    /// Exact malformed bytes written, so a test can prove the file was left untouched.
    malformed: Vec<u8>,
    /// Crash Logs the paused run accepted, in Rust-owned discovery order.
    discovered: Vec<PathBuf>,
    /// The TUI holding the retained continuation.
    app: App,
}

impl PausedFixture {
    /// Reads the current canonical Local Ignore bytes.
    fn local_ignore_bytes(&self) -> Vec<u8> {
        std::fs::read(local_ignore_path(self.temp.path())).expect("Local Ignore should still exist")
    }

    /// Asserts the malformed Local Ignore file is byte-identical to what the run first saw.
    fn assert_local_ignore_untouched(&self) {
        assert_eq!(
            self.local_ignore_bytes(),
            self.malformed,
            "Local Ignore must not be backed up, replaced, or otherwise modified"
        );
    }
}

/// Builds one paused-and-awaiting-decision TUI over a fresh isolated installation root.
fn awaiting_decision(names: &[&str]) -> PausedFixture {
    let temp = installation_root();
    let logs = copy_logs(temp.path(), names);
    let malformed = malform_local_ignore(temp.path());
    let cancellation = Cancellation::new();
    let paused = paused_run(temp.path(), logs, &cancellation);
    let discovered = paused
        .discovery
        .as_ref()
        .expect("a paused run retains completed discovery")
        .accepted_logs
        .clone();
    let app = app_awaiting_recovery(paused, cancellation);

    PausedFixture {
        temp,
        malformed,
        discovered,
        app,
    }
}

/// Drains background messages until one the caller considers terminal has been applied.
fn pump_until(app: &mut App, is_terminal: fn(&AsyncMessage) -> bool) {
    loop {
        let message = get_runtime()
            .block_on(app.async_rx.recv())
            .expect("the App owns its sender, so the channel stays open");
        let terminal = is_terminal(&message);
        app.handle_async_message(message);
        if terminal {
            return;
        }
    }
}

/// Drains background messages until the resumed run reaches its terminal outcome.
fn pump_until_resume_finished(app: &mut App) {
    pump_until(app, |message| {
        matches!(message, AsyncMessage::ScanResumeFinished(_))
    });
}

/// Drains background messages until the initial run reaches its terminal outcome or pause.
fn pump_until_scan_finished(app: &mut App) {
    pump_until(app, |message| {
        matches!(message, AsyncMessage::ScanFinished(_))
    });
}

/// Returns the retained run result, failing loudly on any other retained outcome.
fn terminal_result(app: &App) -> &RunResult {
    match app.last_scan_run.as_ref() {
        Some(LastScanRun::Run(result)) => result,
        Some(LastScanRun::Failed(error)) => panic!("unexpected infrastructure failure: {error:?}"),
        Some(LastScanRun::RecoveryFailed(error)) => panic!("unexpected resume failure: {error:?}"),
        None => panic!("no Crash Log Scan Run outcome was retained"),
    }
}

/// Returns the Installed YAML Data of a resumed run, which always reached intake.
fn resumed_installed_yaml_data(
    app: &App,
) -> &classic_scanlog_core::scan_run::contract::InstalledYamlDataRunData {
    terminal_result(app)
        .installed_yaml_data
        .as_ref()
        .expect("a resumed run reached intake")
}

/// Returns every Autoscan Report the run wrote, so report content can be checked directly.
fn autoscan_reports(result: &RunResult) -> Vec<PathBuf> {
    result
        .logs
        .iter()
        .filter_map(|log| log.autoscan_report.clone())
        .collect()
}

/// Presses one unmodified key through the ordinary terminal event path.
fn press(app: &mut App, code: KeyCode) {
    app.handle_event(TerminalEvent::Key(KeyEvent::new(code, KeyModifiers::NONE)));
}

/// Renders the App and flattens the resulting terminal buffer into newline-separated rows.
fn render_to_text(app: &mut App) -> String {
    let mut terminal = ratatui::Terminal::new(ratatui::backend::TestBackend::new(120, 40))
        .expect("test terminal should be created");
    terminal
        .draw(|frame| app.render(frame))
        .expect("overlay should render");

    let buffer = terminal.backend().buffer();
    let area = buffer.area();
    (0..area.height)
        .map(|y| {
            (0..area.width)
                .map(|x| buffer[(x, y)].symbol())
                .collect::<String>()
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Verifies a scan the TUI starts itself reaches recovery from its one canonical installation root.
///
/// Every other test hands the App a paused run built by the test. This one exercises the App's own
/// request construction, so the installation root it identifies is the one actually scanned.
///
/// It uses a Targeted scan deliberately. Standard discovery with no configured Documents root
/// falls back to the real platform Documents folder, which would make this test read the
/// developer's own Crash Logs. Both intents build the same `Configuration` from `classic_root`, so
/// Targeted proves the installation-root claim without leaving the temp tree.
#[test]
fn a_tui_started_scan_reaches_recovery_from_its_own_installation_root() {
    let temp = installation_root();
    let logs = copy_logs(temp.path(), &["crash-01.log"]);
    let malformed = malform_local_ignore(temp.path());

    let mut app = App::new_with_settings_root(temp.path(), None);
    app.start_targeted_crash_scan(logs);
    assert!(
        app.scan_in_progress,
        "the scan should have started; status was: {}",
        app.scan_status
    );

    pump_until_scan_finished(&mut app);

    assert_eq!(
        app.active_overlay,
        Some(Overlay::LocalIgnoreRecovery),
        "a malformed Local Ignore file under the App's own root must pause for a decision"
    );
    assert!(app.pending_local_ignore_recovery.is_some());
    let overlay_text = app.local_ignore_recovery_text();
    assert!(
        overlay_text.contains("Retained discovery: 1 crash log will be scanned once you decide."),
        "overlay text: {overlay_text}"
    );

    app.accept_local_ignore_recovery(LocalIgnoreRecoveryDecision::ProceedWithoutIgnore);
    pump_until_resume_finished(&mut app);

    assert_eq!(
        terminal_result(&app).status,
        CrashLogScanRunStatus::Completed
    );
    assert_eq!(
        resumed_installed_yaml_data(&app).local_ignore_state,
        LocalIgnoreRunState::ProceedWithoutIgnore
    );
    assert_eq!(
        std::fs::read(local_ignore_path(temp.path())).expect("Local Ignore should still exist"),
        malformed
    );
}

/// Verifies a run already cancelled before the pause is never offered a destructive choice.
///
/// Pressing the scan-cancel key while discovery is still running already decided the run. The
/// native CLI refuses to ask in that state, and the TUI matches it: the question is skipped
/// entirely rather than presented to a user who is on their way out.
#[test]
fn cancellation_observed_before_the_pause_skips_the_question_entirely() {
    let temp = installation_root();
    let logs = copy_logs(temp.path(), &["crash-01.log"]);
    let malformed = malform_local_ignore(temp.path());
    let cancellation = Cancellation::new();
    let paused = paused_run(temp.path(), logs, &cancellation);

    // The user hit cancel while the scan was still running; the pause arrives afterwards.
    cancellation.cancel();

    let mut app = App::new_for_testing();
    app.scan_cancellation = Some(cancellation);
    app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(paused))));

    assert_eq!(
        app.active_overlay, None,
        "an already-cancelled run must not be asked to choose"
    );
    assert!(app.pending_local_ignore_recovery.is_none());

    pump_until_resume_finished(&mut app);

    assert_eq!(
        terminal_result(&app).status,
        CrashLogScanRunStatus::Cancelled
    );
    assert_eq!(
        std::fs::read(local_ignore_path(temp.path())).expect("Local Ignore should still exist"),
        malformed
    );
}

/// Verifies every offered decision is actually drawn, not clipped out of the overlay.
///
/// The choice lines are long enough to wrap, so a body that overflows the overlay height would
/// silently hide the Cancel option — an offer the user cannot see is not an offer.
#[test]
fn every_recovery_choice_is_visible_in_the_rendered_overlay() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    let text = render_to_text(&mut fixture.app);

    assert!(
        text.contains("Local Ignore Recovery Required"),
        "rendered frame:\n{text}"
    );
    for marker in [
        "[P] Proceed Without Ignore",
        "[R] Reset To Default",
        "[Esc] or [C] Cancel",
    ] {
        assert!(
            text.contains(marker),
            "`{marker}` was clipped out of the overlay.\nrendered frame:\n{text}"
        );
    }
}

/// Verifies scrolling reaches the diagnostics below the choices without answering the question.
#[test]
fn recovery_overlay_scrolling_reveals_diagnostics_without_answering() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    press(&mut fixture.app, KeyCode::PageDown);

    assert!(fixture.app.local_ignore_recovery_scroll > 0);
    assert!(
        fixture.app.pending_local_ignore_recovery.is_some(),
        "scrolling must not answer the recovery question"
    );
    let text = render_to_text(&mut fixture.app);
    let parse_failure = InstalledYamlDataRunDiagnosticKind::Parse.label();
    assert!(
        text.contains(parse_failure),
        "diagnostics should be reachable by scrolling.\nrendered frame:\n{text}"
    );

    press(&mut fixture.app, KeyCode::Home);
    assert_eq!(fixture.app.local_ignore_recovery_scroll, 0);
    fixture.assert_local_ignore_untouched();
}

/// Verifies no unoffered key can answer the question, so nothing implies a destructive default.
#[test]
fn recovery_overlay_ignores_keys_that_were_not_offered() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    // Enter is deliberately unbound here: elsewhere in the TUI it confirms, and confirming by
    // reflex must never be able to authorize a durable Local Ignore reset.
    for code in [
        KeyCode::Enter,
        KeyCode::Char('y'),
        KeyCode::Char('n'),
        KeyCode::Char('x'),
        KeyCode::Backspace,
        KeyCode::Tab,
        KeyCode::F(5),
    ] {
        press(&mut fixture.app, code);
        assert!(
            fixture.app.pending_local_ignore_recovery.is_some(),
            "{code:?} must not answer the recovery question"
        );
        assert_eq!(
            fixture.app.active_overlay,
            Some(Overlay::LocalIgnoreRecovery)
        );
    }

    assert!(!fixture.app.scan_in_progress);
    fixture.assert_local_ignore_untouched();
}

/// Verifies the advertised Proceed key applies exactly the operation-scoped decision.
#[test]
fn recovery_overlay_proceed_key_applies_the_operation_scoped_decision() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    press(&mut fixture.app, KeyCode::Char('p'));
    pump_until_resume_finished(&mut fixture.app);

    assert_eq!(
        resumed_installed_yaml_data(&fixture.app).local_ignore_state,
        LocalIgnoreRunState::ProceedWithoutIgnore
    );
    fixture.assert_local_ignore_untouched();
}

/// Verifies the advertised Reset key applies the durable decision.
#[test]
fn recovery_overlay_reset_key_applies_the_durable_decision() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    press(&mut fixture.app, KeyCode::Char('R'));
    pump_until_resume_finished(&mut fixture.app);

    assert_eq!(
        resumed_installed_yaml_data(&fixture.app).local_ignore_state,
        LocalIgnoreRunState::ResetToDefault
    );
    assert_ne!(fixture.local_ignore_bytes(), fixture.malformed);
}

/// Verifies Escape dismisses the question without mutation or analysis.
#[test]
fn recovery_overlay_escape_key_cancels_without_mutation() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    press(&mut fixture.app, KeyCode::Esc);
    pump_until_resume_finished(&mut fixture.app);

    assert_eq!(
        terminal_result(&fixture.app).status,
        CrashLogScanRunStatus::Cancelled
    );
    fixture.assert_local_ignore_untouched();
}

/// Verifies the pre-decision overlay presents Rust-owned facts and every offered outcome.
///
/// The Installed YAML Data facts are asserted through the Display Labels core owns rather than
/// through the sentences around them. Restating that prose here would be a second copy of wording
/// pinned in `classic-scan-presentation`, which is the drift this consolidation removes — what the
/// TUI has to prove is that the facts arrive, not that it can repeat them.
#[test]
fn recovery_overlay_presents_retained_discovery_and_installation_diagnostics() {
    let fixture = awaiting_decision(&["crash-01.log", "crash-02.log"]);
    let text = fixture.app.local_ignore_recovery_text();

    assert!(
        text.contains("Retained discovery: 2 crash logs will be scanned once you decide."),
        "overlay text: {text}"
    );
    for label in [
        InstalledYamlDataProvenance::Bundled.label(),
        LocalIgnoreRunState::RecoveryRequired.label(),
        InstalledYamlDataRunDiagnosticKind::Parse.label(),
    ] {
        assert!(
            text.contains(label),
            "`{label}` is missing.\noverlay text: {text}"
        );
    }
    assert!(
        text.contains("[P] Proceed Without Ignore"),
        "overlay text: {text}"
    );
    assert!(
        text.contains("[R] Reset To Default"),
        "overlay text: {text}"
    );
    assert!(text.contains("[Esc] or [C] Cancel"), "overlay text: {text}");
}

/// Verifies Proceed Without Ignore resumes the same discovery and leaves the malformed file alone.
#[test]
fn proceed_without_ignore_resumes_the_retained_discovery_without_mutation() {
    let mut fixture = awaiting_decision(&["crash-01.log", "crash-02.log"]);

    fixture
        .app
        .accept_local_ignore_recovery(LocalIgnoreRecoveryDecision::ProceedWithoutIgnore);

    assert!(
        fixture.app.pending_local_ignore_recovery.is_none(),
        "accepting a decision must move the continuation out of application state"
    );
    assert_eq!(fixture.app.active_overlay, None);
    assert!(fixture.app.scan_in_progress);

    pump_until_resume_finished(&mut fixture.app);

    let result = terminal_result(&fixture.app);
    assert_eq!(result.status, CrashLogScanRunStatus::Completed);
    assert_eq!(
        result
            .discovery
            .as_ref()
            .expect("resume retains the original discovery")
            .accepted_logs,
        fixture.discovered,
        "resume must reuse the discovered set rather than rediscovering"
    );
    assert_eq!(result.succeeded, 2);

    let installed = resumed_installed_yaml_data(&fixture.app);
    assert_eq!(
        installed.local_ignore_state,
        LocalIgnoreRunState::ProceedWithoutIgnore
    );
    assert!(
        installed.local_ignore_reset.is_none(),
        "proceeding must not perform a durable reset"
    );
    fixture.assert_local_ignore_untouched();
}

/// Verifies Reset To Default resumes with a byte-exact backup and reports it in run details.
#[test]
fn reset_to_default_resumes_with_a_durable_byte_exact_backup() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    fixture
        .app
        .accept_local_ignore_recovery(LocalIgnoreRecoveryDecision::ResetToDefault);
    pump_until_resume_finished(&mut fixture.app);

    assert_eq!(
        terminal_result(&fixture.app).status,
        CrashLogScanRunStatus::Completed
    );

    let installed = resumed_installed_yaml_data(&fixture.app);
    assert_eq!(
        installed.local_ignore_state,
        LocalIgnoreRunState::ResetToDefault
    );
    let reset = installed
        .local_ignore_reset
        .as_ref()
        .expect("a successful reset retains durable metadata");
    assert_eq!(
        std::fs::read(&reset.backup_path).expect("the verified backup should exist"),
        fixture.malformed,
        "the backup must preserve the user's malformed bytes exactly"
    );
    assert_eq!(
        reset.malformed_identity.sha256_hex(),
        reset.backup_identity.sha256_hex()
    );
    assert_ne!(
        fixture.local_ignore_bytes(),
        fixture.malformed,
        "reset must publish the retained selected-Main defaults"
    );

    let details = fixture.app.scan_run_summary_text();
    assert!(
        details.contains("Local Ignore: reset to default"),
        "run details: {details}"
    );
    assert!(
        details.contains("Local Ignore backup:"),
        "run details: {details}"
    );
    // `Local Ignore reset`, not `local ignore reset`: the diagnostic kind's Display Label carries
    // the glossary capitalization of a domain term, which is the wording the CLI and the GUI
    // already assert. The TUI held the lower-cased copy, which is the drift adopting the core
    // vocabulary removes.
    assert!(
        details.contains("Local Ignore reset"),
        "run details: {details}"
    );

    // Installation and recovery diagnostics are run-level operational metadata only.
    let reports = autoscan_reports(terminal_result(&fixture.app));
    assert!(
        !reports.is_empty(),
        "a completed run writes Autoscan Reports"
    );
    for report in reports {
        let text = std::fs::read_to_string(&report).expect("Autoscan Report should be readable");
        assert!(
            !text.contains("Installed YAML Data:"),
            "Autoscan Report {} must not carry installation diagnostics",
            report.display()
        );
        assert!(
            !text.contains("Local Ignore reset"),
            "Autoscan Report {} must not carry recovery diagnostics",
            report.display()
        );
    }
}

/// Verifies cancelling while awaiting a decision performs no mutation and no analysis.
#[test]
fn cancelling_the_recovery_decision_mutates_and_analyzes_nothing() {
    let mut fixture = awaiting_decision(&["crash-01.log", "crash-02.log"]);

    fixture.app.cancel_local_ignore_recovery();
    pump_until_resume_finished(&mut fixture.app);

    let result = terminal_result(&fixture.app);
    assert_eq!(result.status, CrashLogScanRunStatus::Cancelled);
    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 0);
    assert!(
        autoscan_reports(result).is_empty(),
        "cancellation before the decision analyzes nothing"
    );
    for log in &fixture.discovered {
        let report = log.with_file_name(format!(
            "{}-AUTOSCAN.md",
            log.file_name()
                .expect("fixture log has a file name")
                .to_string_lossy()
        ));
        assert!(
            !report.exists(),
            "no Autoscan Report should be written for {}",
            log.display()
        );
    }
    fixture.assert_local_ignore_untouched();
}

/// Verifies closing the overlay is an explicit cancel rather than an abandoned continuation.
#[test]
fn closing_the_recovery_overlay_cancels_explicitly() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    fixture.app.close_overlay();

    assert!(fixture.app.pending_local_ignore_recovery.is_none());
    assert_eq!(fixture.app.active_overlay, None);

    pump_until_resume_finished(&mut fixture.app);

    assert_eq!(
        terminal_result(&fixture.app).status,
        CrashLogScanRunStatus::Cancelled
    );
    fixture.assert_local_ignore_untouched();
}

/// Verifies the retained continuation is consumed exactly once at the TUI seam.
#[test]
fn the_retained_continuation_is_consumed_exactly_once() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    fixture
        .app
        .accept_local_ignore_recovery(LocalIgnoreRecoveryDecision::ProceedWithoutIgnore);
    // A second key press finds nothing to resume: the continuation left with the first decision,
    // so the destructive choice cannot be applied on top of the one the user actually made.
    fixture
        .app
        .accept_local_ignore_recovery(LocalIgnoreRecoveryDecision::ResetToDefault);
    fixture.app.cancel_local_ignore_recovery();

    pump_until_resume_finished(&mut fixture.app);

    assert_eq!(
        terminal_result(&fixture.app).status,
        CrashLogScanRunStatus::Completed
    );
    let installed = resumed_installed_yaml_data(&fixture.app);
    assert_eq!(
        installed.local_ignore_state,
        LocalIgnoreRunState::ProceedWithoutIgnore,
        "only the first accepted decision may take effect"
    );
    assert!(installed.local_ignore_reset.is_none());
    fixture.assert_local_ignore_untouched();
    assert!(
        fixture.app.async_rx.try_recv().is_err(),
        "no second resume should have been spawned"
    );
}

/// Verifies a reset conflict raised while deciding is typed and leaves the newer file intact.
#[test]
fn a_reset_conflict_is_presented_without_overwriting_newer_local_ignore_state() {
    let mut fixture = awaiting_decision(&["crash-01.log"]);

    // The user repairs the file in another editor before answering the question.
    let repaired = b"CLASSIC_Ignore_Fallout4:\n  - RepairedByHand.esp\n";
    std::fs::write(local_ignore_path(fixture.temp.path()), repaired)
        .expect("repaired Local Ignore should be written");

    fixture
        .app
        .accept_local_ignore_recovery(LocalIgnoreRecoveryDecision::ResetToDefault);
    pump_until_resume_finished(&mut fixture.app);

    let details = fixture.app.scan_run_summary_text();
    match fixture.app.last_scan_run.as_ref() {
        Some(LastScanRun::RecoveryFailed(error)) => {
            assert_eq!(error.kind().as_str(), "local_ignore_reset_conflict");
            // Both identities must survive into the overlay, because comparing them is the whole
            // action available to a user whose file changed while they were deciding. Asserted as
            // the digests themselves rather than as the sentences around them: the prose belongs to
            // `classic-scan-presentation` and is pinned there.
            let ResumeError::LocalIgnoreResetConflict(conflict) = error else {
                panic!("the conflict kind must carry conflict data, got {error:?}");
            };
            let expected = conflict.expected_identity.sha256_hex();
            let actual = conflict
                .actual_identity
                .as_ref()
                .expect("the repaired file must have been observed")
                .sha256_hex();
            assert_ne!(expected, actual, "the fixture must produce a real conflict");
            assert!(details.contains(&expected), "run details: {details}");
            assert!(details.contains(&actual), "run details: {details}");
        }
        other => panic!("expected a typed reset conflict, got {other:?}"),
    }

    assert!(
        details.contains("Your Local Ignore file was not replaced."),
        "run details: {details}"
    );
    // A typed recovery failure is actionable and must not expire into a generic ready status.
    assert!(fixture.app.status_clear_at.is_none());
    assert_eq!(
        fixture.local_ignore_bytes(),
        repaired,
        "a conflict must leave the newer bytes authoritative"
    );
}
