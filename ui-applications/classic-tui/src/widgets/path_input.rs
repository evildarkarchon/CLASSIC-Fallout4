use ratatui::Frame;
use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::style::Style;
use ratatui::text::Line;
use ratatui::widgets::{Block, BorderType, Borders, Paragraph};

use crate::theme;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PathValidationState {
    Default,
    Valid,
    Invalid,
}

pub struct PathInputProps<'a> {
    pub label: &'a str,
    pub value: &'a str,
    pub focused_input: bool,
    pub focused_browse: bool,
    pub validation: PathValidationState,
}

#[derive(Default)]
pub struct PathInputAreas {
    pub input: Rect,
    pub browse: Rect,
}

pub fn render_path_input(
    frame: &mut Frame<'_>,
    area: Rect,
    props: &PathInputProps<'_>,
) -> PathInputAreas {
    let [label_area, row_area] =
        Layout::vertical([Constraint::Length(1), Constraint::Length(2)]).areas(area);

    frame.render_widget(
        Paragraph::new(Line::from(props.label).style(Style::default().fg(theme::TEXT_MUTED))),
        label_area,
    );

    let [input_area, browse_area] =
        Layout::horizontal([Constraint::Min(20), Constraint::Length(14)]).areas(row_area);

    let border_color = if props.focused_input {
        theme::BORDER_FOCUS
    } else {
        match props.validation {
            PathValidationState::Default => theme::BORDER_DEFAULT,
            PathValidationState::Valid => theme::BORDER_VALID,
            PathValidationState::Invalid => theme::BORDER_INVALID,
        }
    };

    let input = Paragraph::new(props.value)
        .style(
            Style::default()
                .fg(theme::TEXT_PRIMARY)
                .bg(theme::BG_PRIMARY),
        )
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(border_color)),
        );
    frame.render_widget(input, input_area);

    let browse_border = if props.focused_browse {
        theme::BORDER_FOCUS
    } else {
        theme::BORDER_DEFAULT
    };
    let browse = Paragraph::new("Browse")
        .style(
            Style::default()
                .fg(theme::TEXT_PRIMARY)
                .bg(theme::BG_SURFACE),
        )
        .centered()
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(browse_border)),
        );
    frame.render_widget(browse, browse_area);

    PathInputAreas {
        input: input_area,
        browse: browse_area,
    }
}
