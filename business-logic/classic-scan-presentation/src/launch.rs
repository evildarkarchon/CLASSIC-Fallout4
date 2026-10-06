//! Display Content for Crash Log Scan Launch diagnostics (ADR-0007, ADR-0009).
//!
//! A launch reports non-fatal facts beside the request it builds: the User Settings
//! diagnostics it surfaced while opening User Settings, and each saved game-specific value
//! the game-differs rule withheld. This module decides what those say, so every frontend
//! shows the same lines and keeps only Display Layout.

use crate::display::{DisplayLine, DisplaySegment, DisplaySeverity};
use classic_scan_launch::{CrashLogScanLaunchDiagnostic, SavedGameSpecificValue};
use classic_vocabulary::Vocabulary;

use DisplaySegment::{Emphasis, Label, Name, Text};
use DisplaySeverity::{Notice, Warning};

/// Renders every launch diagnostic, one line each, in the order the launch reported them.
#[must_use]
pub fn render_launch_diagnostics(diagnostics: &[CrashLogScanLaunchDiagnostic]) -> Vec<DisplayLine> {
    diagnostics.iter().map(render_launch_diagnostic).collect()
}

/// Renders one launch diagnostic as a single display line.
///
/// - A User Settings diagnostic reads as a warning carrying its free-text message, because
///   it means the saved document could not be used as written.
/// - A saved value the game-differs rule withheld reads as a notice naming both games: the
///   scan is still the one the user asked for, it just ignores the managed game's value.
///
/// Machine codes never appear in a line; they stay on the typed diagnostic (rule 5 of the
/// crate contract).
#[must_use]
pub fn render_launch_diagnostic(diagnostic: &CrashLogScanLaunchDiagnostic) -> DisplayLine {
    match diagnostic {
        CrashLogScanLaunchDiagnostic::UserSettings(settings_diagnostic) => DisplayLine::new(
            Warning,
            vec![
                Label(diagnostic.kind().label()),
                Text("-"),
                Emphasis(settings_diagnostic.message().to_string()),
            ],
        ),
        CrashLogScanLaunchDiagnostic::SavedValueNotApplied {
            value,
            managed_game,
            target_game,
        } => {
            let mut segments = vec![
                Label(diagnostic.kind().label()),
                Text("- this scan targets"),
                Name(target_game.display_name().to_string()),
                Text("but saved settings belong to the managed game"),
                Name(managed_game.display_name().to_string()),
            ];
            // Only the game version is replaced rather than dropped, so only it says what
            // the scan uses instead.
            if *value == SavedGameSpecificValue::GameVersion {
                segments.push(Text("- the game version is detected automatically"));
            }
            DisplayLine::new(Notice, segments)
        }
    }
}
