use ratatui::style::Color;

pub const BG_PRIMARY: Color = Color::Rgb(30, 30, 30);
pub const BG_SURFACE: Color = Color::Rgb(45, 45, 45);
pub const BG_ELEVATED: Color = Color::Rgb(60, 60, 60);

pub const TEXT_PRIMARY: Color = Color::Rgb(224, 224, 224);
pub const TEXT_MUTED: Color = Color::Rgb(136, 136, 136);

pub const ACCENT_BLUE: Color = Color::Rgb(0, 120, 212);
pub const SUCCESS: Color = Color::Rgb(46, 125, 50);
pub const ERROR: Color = Color::Rgb(255, 107, 107);

pub const BORDER_DEFAULT: Color = Color::Rgb(85, 85, 85);
pub const BORDER_FOCUS: Color = ACCENT_BLUE;
pub const BORDER_VALID: Color = SUCCESS;
pub const BORDER_INVALID: Color = ERROR;
