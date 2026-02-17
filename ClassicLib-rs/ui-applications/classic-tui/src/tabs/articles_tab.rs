use ratatui::Frame;
use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::widgets::{Block, BorderType, Borders, Paragraph};

use crate::theme;

#[derive(Clone, Copy)]
pub struct ArticleLink {
    pub label: &'static str,
    pub url: &'static str,
}

pub const ARTICLE_LINKS: [ArticleLink; 9] = [
    ArticleLink {
        label: "BUFFOUT 4 INSTALLATION",
        url: "https://www.nexusmods.com/fallout4/articles/3115",
    },
    ArticleLink {
        label: "FALLOUT 4 SETUP TIPS",
        url: "https://www.nexusmods.com/fallout4/articles/4141",
    },
    ArticleLink {
        label: "IMPORTANT PATCHES LIST",
        url: "https://www.nexusmods.com/fallout4/articles/3769",
    },
    ArticleLink {
        label: "BUFFOUT 4 NEXUS",
        url: "https://www.nexusmods.com/fallout4/mods/47359",
    },
    ArticleLink {
        label: "CLASSIC NEXUS",
        url: "https://www.nexusmods.com/fallout4/mods/56255",
    },
    ArticleLink {
        label: "CLASSIC GITHUB",
        url: "https://github.com/evildarkarchon/CLASSIC-Fallout4",
    },
    ArticleLink {
        label: "DDS TEXTURE SCANNER",
        url: "https://www.nexusmods.com/fallout4/mods/71588",
    },
    ArticleLink {
        label: "BETHINI PIE",
        url: "https://www.nexusmods.com/site/mods/631",
    },
    ArticleLink {
        label: "WRYE BASH",
        url: "https://www.nexusmods.com/fallout4/mods/20032",
    },
];

#[derive(Default)]
pub struct ArticlesClickAreas {
    pub cells: [Rect; 9],
}

pub struct ArticlesTabRenderData {
    pub selected: usize,
}

pub fn render_articles_tab(
    frame: &mut Frame<'_>,
    content_area: Rect,
    data: &ArticlesTabRenderData,
) -> ArticlesClickAreas {
    let [
        title_area,
        _spacer1,
        row1,
        _spacer2,
        row2,
        _spacer3,
        row3,
        hint_area,
    ] = Layout::vertical([
        Constraint::Length(1),
        Constraint::Length(1),
        Constraint::Length(5),
        Constraint::Length(1),
        Constraint::Length(5),
        Constraint::Length(1),
        Constraint::Length(5),
        Constraint::Min(1),
    ])
    .areas(content_area);

    frame.render_widget(
        Paragraph::new("USEFUL RESOURCES & LINKS")
            .style(
                Style::default()
                    .fg(theme::TEXT_PRIMARY)
                    .add_modifier(Modifier::BOLD),
            )
            .centered(),
        title_area,
    );

    let row_areas = [row1, row2, row3];
    let mut click_areas = ArticlesClickAreas::default();

    for (row, row_area) in row_areas.iter().enumerate() {
        let [cell0, cell1, cell2] = Layout::horizontal([
            Constraint::Ratio(1, 3),
            Constraint::Ratio(1, 3),
            Constraint::Ratio(1, 3),
        ])
        .spacing(1)
        .areas(*row_area);

        let cells = [cell0, cell1, cell2];
        for (col, cell) in cells.iter().enumerate() {
            let index = row * 3 + col;
            let article = ARTICLE_LINKS[index];
            let selected = data.selected == index;

            let border_color = if selected {
                theme::ACCENT_BLUE
            } else {
                theme::BORDER_DEFAULT
            };

            let widget = Paragraph::new(split_label(article.label))
                .style(Style::default().fg(theme::TEXT_PRIMARY))
                .centered()
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .border_type(BorderType::Rounded)
                        .border_style(Style::default().fg(border_color))
                        .style(Style::default().bg(theme::BG_SURFACE)),
                );

            frame.render_widget(widget, *cell);
            click_areas.cells[index] = *cell;
        }
    }

    frame.render_widget(
        Paragraph::new("Press Enter or click to open in browser")
            .style(Style::default().fg(theme::TEXT_MUTED)),
        hint_area,
    );

    click_areas
}

fn split_label(label: &str) -> String {
    match label.rsplit_once(' ') {
        Some((left, right)) if left.len() > 5 => format!("{left}\n{right}"),
        _ => label.to_string(),
    }
}
