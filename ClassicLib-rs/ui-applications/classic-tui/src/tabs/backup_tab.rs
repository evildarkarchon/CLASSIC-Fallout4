use ratatui::Frame;
use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, BorderType, Borders, Paragraph};

use crate::theme;

const TYPE_WIDTH: u16 = 20;
const STATUS_WIDTH: u16 = 12;
const ACTION_WIDTH: u16 = 10;

#[derive(Clone, Copy, Default)]
pub struct BackupActionArea {
    pub backup: Rect,
    pub restore: Rect,
    pub remove: Rect,
}

#[derive(Default)]
pub struct BackupClickAreas {
    pub rows: [Rect; 4],
    pub actions: [BackupActionArea; 4],
    pub open_backups: Rect,
}

pub struct BackupTabRenderData {
    pub selected_row: usize,
    pub exists: [bool; 4],
}

pub fn render_backup_tab(
    frame: &mut Frame<'_>,
    content_area: Rect,
    data: &BackupTabRenderData,
) -> BackupClickAreas {
    let [title_area, subtitle_area, table_area, _spacer, open_area] = Layout::vertical([
        Constraint::Length(1),
        Constraint::Length(1),
        Constraint::Length(8),
        Constraint::Fill(1),
        Constraint::Length(3),
    ])
    .areas(content_area);

    frame.render_widget(
        Paragraph::new("BACKUP / RESTORE / REMOVE")
            .style(
                Style::default()
                    .fg(theme::TEXT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )
            .centered(),
        title_area,
    );
    frame.render_widget(
        Paragraph::new("Manage backups for game modification files.")
            .style(Style::default().fg(theme::TEXT_MUTED)),
        subtitle_area,
    );

    let table_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(theme::BORDER_DEFAULT));
    let table_inner = table_block.inner(table_area);
    frame.render_widget(table_block, table_area);

    let mut click_areas = BackupClickAreas::default();

    let header = format!(
        "{:<20} {:<12} {:<10} {:<10} {:<10}",
        "Type", "Status", "Backup", "Restore", "Remove"
    );
    frame.render_widget(
        Paragraph::new(header).style(
            Style::default()
                .fg(theme::TEXT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        ),
        Rect::new(table_inner.x, table_inner.y, table_inner.width, 1),
    );

    let names = ["Script Extender", "ReShade", "Vulkan", "ENB"];
    for (row, name) in names.iter().enumerate() {
        let exists = data.exists[row];
        let status = if exists { "✓ Exists" } else { "○ None" };
        let restore = if exists { "[Restore]" } else { "-" };
        let remove = if exists { "[Remove]" } else { "-" };
        let line = format!(
            "{:<20} {:<12} {:<10} {:<10} {:<10}",
            name, status, "[Backup]", restore, remove
        );
        let row_area = Rect::new(
            table_inner.x,
            table_inner.y + 1 + row as u16,
            table_inner.width,
            1,
        );
        let style = if data.selected_row == row {
            Style::default()
                .bg(theme::BG_ELEVATED)
                .fg(theme::TEXT_PRIMARY)
        } else {
            Style::default().fg(theme::TEXT_PRIMARY)
        };
        frame.render_widget(Paragraph::new(line).style(style), row_area);

        click_areas.rows[row] = row_area;
        click_areas.actions[row] = BackupActionArea {
            backup: action_rect(table_inner, row_area.y, TYPE_WIDTH + 1 + STATUS_WIDTH + 1),
            restore: action_rect(
                table_inner,
                row_area.y,
                TYPE_WIDTH + 1 + STATUS_WIDTH + 1 + ACTION_WIDTH + 1,
            ),
            remove: action_rect(
                table_inner,
                row_area.y,
                TYPE_WIDTH + 1 + STATUS_WIDTH + 1 + ACTION_WIDTH + 1 + ACTION_WIDTH + 1,
            ),
        };
    }

    let open_button = Paragraph::new(Line::from("OPEN CLASSIC BACKUPS"))
        .centered()
        .style(
            Style::default()
                .fg(theme::TEXT_PRIMARY)
                .add_modifier(Modifier::BOLD),
        )
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(theme::BORDER_DEFAULT)),
        );
    frame.render_widget(open_button, open_area);

    click_areas.open_backups = open_area;
    click_areas
}

fn action_rect(inner: Rect, y: u16, x_offset: u16) -> Rect {
    if inner.width <= x_offset {
        return Rect::default();
    }
    let width = inner.width.saturating_sub(x_offset).min(ACTION_WIDTH);
    Rect::new(inner.x + x_offset, y, width, 1)
}
