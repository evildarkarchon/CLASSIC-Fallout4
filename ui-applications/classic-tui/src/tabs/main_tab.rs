use ratatui::Frame;
use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, BorderType, Borders, Paragraph};

use crate::theme;
use crate::widgets::path_input::{
    PathInputAreas, PathInputProps, PathValidationState, render_path_input,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MainFocus {
    StagingInput,
    StagingBrowse,
    CustomInput,
    CustomBrowse,
    ScanCrash,
    ScanGame,
    About,
    Help,
    Settings,
    OpenLogs,
    CheckUpdates,
    Papyrus,
}

impl MainFocus {
    pub fn next(self) -> Self {
        match self {
            Self::StagingInput => Self::StagingBrowse,
            Self::StagingBrowse => Self::CustomInput,
            Self::CustomInput => Self::CustomBrowse,
            Self::CustomBrowse => Self::ScanCrash,
            Self::ScanCrash => Self::ScanGame,
            Self::ScanGame => Self::About,
            Self::About => Self::Help,
            Self::Help => Self::Settings,
            Self::Settings => Self::OpenLogs,
            Self::OpenLogs => Self::CheckUpdates,
            Self::CheckUpdates => Self::Papyrus,
            Self::Papyrus => Self::StagingInput,
        }
    }

    pub fn prev(self) -> Self {
        match self {
            Self::StagingInput => Self::Papyrus,
            Self::StagingBrowse => Self::StagingInput,
            Self::CustomInput => Self::StagingBrowse,
            Self::CustomBrowse => Self::CustomInput,
            Self::ScanCrash => Self::CustomBrowse,
            Self::ScanGame => Self::ScanCrash,
            Self::About => Self::ScanGame,
            Self::Help => Self::About,
            Self::Settings => Self::Help,
            Self::OpenLogs => Self::Settings,
            Self::CheckUpdates => Self::OpenLogs,
            Self::Papyrus => Self::CheckUpdates,
        }
    }
}

pub struct MainTabRenderData<'a> {
    pub staging_mods: &'a str,
    pub custom_scan: &'a str,
    pub focus: MainFocus,
    pub scan_in_progress: bool,
    pub update_checking: bool,
    pub papyrus_active: bool,
    pub staging_validation: PathValidationState,
    pub custom_validation: PathValidationState,
}

#[derive(Default)]
pub struct MainClickAreas {
    pub staging_input: Rect,
    pub staging_browse: Rect,
    pub custom_input: Rect,
    pub custom_browse: Rect,
    pub scan_crash: Rect,
    pub scan_game: Rect,
    pub about: Rect,
    pub help: Rect,
    pub settings: Rect,
    pub open_logs: Rect,
    pub check_updates: Rect,
    pub papyrus: Rect,
}

pub fn render_main_tab(
    frame: &mut Frame<'_>,
    content_area: Rect,
    data: &MainTabRenderData<'_>,
) -> MainClickAreas {
    let [
        paths_area,
        _spacer1,
        scan_buttons_area,
        _spacer2,
        utility_row1,
        utility_row2,
        papyrus_area,
    ] = Layout::vertical([
        Constraint::Length(6),
        Constraint::Fill(1),
        Constraint::Length(3),
        Constraint::Fill(1),
        Constraint::Length(3),
        Constraint::Length(1),
        Constraint::Length(3),
    ])
    .areas(content_area);

    let [mods_area, custom_area] =
        Layout::vertical([Constraint::Length(3), Constraint::Length(3)]).areas(paths_area);

    let mods_areas: PathInputAreas = render_path_input(
        frame,
        mods_area,
        &PathInputProps {
            label: "Staging Mods Folder:",
            value: data.staging_mods,
            focused_input: data.focus == MainFocus::StagingInput,
            focused_browse: data.focus == MainFocus::StagingBrowse,
            validation: data.staging_validation,
        },
    );

    let custom_areas: PathInputAreas = render_path_input(
        frame,
        custom_area,
        &PathInputProps {
            label: "Custom Scan Folder:",
            value: data.custom_scan,
            focused_input: data.focus == MainFocus::CustomInput,
            focused_browse: data.focus == MainFocus::CustomBrowse,
            validation: data.custom_validation,
        },
    );

    let [scan_crash_area, scan_game_area, _] = Layout::horizontal([
        Constraint::Length(20),
        Constraint::Length(20),
        Constraint::Fill(1),
    ])
    .areas(scan_buttons_area);

    let scan_crash_label = if data.scan_in_progress {
        "CANCEL"
    } else {
        "SCAN CRASH LOGS"
    };
    let scan_game_label = if data.scan_in_progress {
        "SCANNING..."
    } else {
        "SCAN GAME FILES"
    };

    render_button(
        frame,
        scan_crash_area,
        scan_crash_label,
        data.focus == MainFocus::ScanCrash,
        true,
    );
    render_button(
        frame,
        scan_game_area,
        scan_game_label,
        data.focus == MainFocus::ScanGame,
        true,
    );

    let [about_area, help_area, settings_area, logs_area, update_area] = Layout::horizontal([
        Constraint::Ratio(1, 5),
        Constraint::Ratio(1, 5),
        Constraint::Ratio(1, 5),
        Constraint::Ratio(1, 5),
        Constraint::Ratio(1, 5),
    ])
    .areas(utility_row1);

    render_button(
        frame,
        about_area,
        "About",
        data.focus == MainFocus::About,
        false,
    );
    render_button(
        frame,
        help_area,
        "Help",
        data.focus == MainFocus::Help,
        false,
    );
    render_button(
        frame,
        settings_area,
        "Settings",
        data.focus == MainFocus::Settings,
        false,
    );
    render_button(
        frame,
        logs_area,
        "Open Crash Logs",
        data.focus == MainFocus::OpenLogs,
        false,
    );
    render_button(
        frame,
        update_area,
        if data.update_checking {
            "CHECKING..."
        } else {
            "Check Updates"
        },
        data.focus == MainFocus::CheckUpdates,
        false,
    );

    let papyrus_label = if data.papyrus_active {
        "STOP PAPYRUS MONITORING                                      [ON]"
    } else {
        "START PAPYRUS MONITORING                                     [OFF]"
    };
    render_button(
        frame,
        papyrus_area,
        papyrus_label,
        data.focus == MainFocus::Papyrus,
        data.papyrus_active,
    );

    let _ = utility_row2;

    MainClickAreas {
        staging_input: mods_areas.input,
        staging_browse: mods_areas.browse,
        custom_input: custom_areas.input,
        custom_browse: custom_areas.browse,
        scan_crash: scan_crash_area,
        scan_game: scan_game_area,
        about: about_area,
        help: help_area,
        settings: settings_area,
        open_logs: logs_area,
        check_updates: update_area,
        papyrus: papyrus_area,
    }
}

fn render_button(frame: &mut Frame<'_>, area: Rect, label: &str, focused: bool, primary: bool) {
    let (fg, bg, border) = if primary {
        (
            ratatui::style::Color::White,
            theme::ACCENT_BLUE,
            theme::ACCENT_BLUE,
        )
    } else if focused {
        (theme::TEXT_PRIMARY, theme::BG_ELEVATED, theme::BORDER_FOCUS)
    } else {
        (
            theme::TEXT_PRIMARY,
            theme::BG_SURFACE,
            theme::BORDER_DEFAULT,
        )
    };

    let paragraph =
        Paragraph::new(Line::from(label).style(Style::default().add_modifier(Modifier::BOLD)))
            .centered()
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(border))
                    .style(Style::default().bg(bg).fg(fg)),
            );
    frame.render_widget(paragraph, area);
}

#[cfg(test)]
mod tests {
    use super::MainFocus;

    #[test]
    fn main_focus_next_wraps_to_start() {
        let mut focus = MainFocus::StagingInput;
        for _ in 0..11 {
            focus = focus.next();
        }
        assert_eq!(focus.next(), MainFocus::StagingInput);
    }

    #[test]
    fn main_focus_prev_wraps_to_end() {
        assert_eq!(MainFocus::StagingInput.prev(), MainFocus::Papyrus);
    }
}
