use classic_scan_presentation::DisplaySeverity;
use ratatui::style::Color;

pub const BG_PRIMARY: Color = Color::Rgb(30, 30, 30);
pub const BG_SURFACE: Color = Color::Rgb(45, 45, 45);
pub const BG_ELEVATED: Color = Color::Rgb(60, 60, 60);

pub const TEXT_PRIMARY: Color = Color::Rgb(224, 224, 224);
pub const TEXT_MUTED: Color = Color::Rgb(136, 136, 136);

pub const ACCENT_BLUE: Color = Color::Rgb(0, 120, 212);
pub const SUCCESS: Color = Color::Rgb(46, 125, 50);
pub const ERROR: Color = Color::Rgb(255, 107, 107);

/// A line worth noticing where nothing went wrong: a rejected input, a cancelled log, a hint.
pub const NOTICE: Color = Color::Rgb(120, 170, 255);
/// A line that is wrong or incomplete without having failed outright.
pub const WARNING: Color = Color::Rgb(255, 183, 77);
/// A completed line, brightened from [`SUCCESS`] so it stays legible as body text.
///
/// `SUCCESS` is tuned for a border against the surface background, where a dark green reads as
/// deliberate. The same green as foreground text on that background is close to unreadable, so the
/// text form is a separate value rather than a reuse that would quietly cost legibility.
pub const SUCCESS_TEXT: Color = Color::Rgb(129, 199, 132);

pub const BORDER_DEFAULT: Color = Color::Rgb(85, 85, 85);
pub const BORDER_FOCUS: Color = ACCENT_BLUE;
pub const BORDER_VALID: Color = SUCCESS;
pub const BORDER_INVALID: Color = ERROR;

/// Maps a core display severity onto this frontend's palette.
///
/// Core says only how gravely a line should read and never names a colour, so this mapping is
/// Display Layout and lives here with the rest of the palette. A CLI mapping every severity to
/// plain text is equally correct; nothing about the wording changes either way.
pub const fn severity_color(severity: DisplaySeverity) -> Color {
    match severity {
        DisplaySeverity::Info => TEXT_PRIMARY,
        DisplaySeverity::Notice => NOTICE,
        DisplaySeverity::Warning => WARNING,
        DisplaySeverity::Failure => ERROR,
        DisplaySeverity::Success => SUCCESS_TEXT,
    }
}
