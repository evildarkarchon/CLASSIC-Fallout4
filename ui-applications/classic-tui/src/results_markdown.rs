use pulldown_cmark::{Event, HeadingLevel, Options, Parser, Tag, TagEnd};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};

#[derive(Clone, Debug)]
pub struct MarkdownLink {
    pub index: usize,
    pub line_index: usize,
    pub start_col: usize,
    pub end_col: usize,
    pub url: String,
    pub label: String,
}

#[derive(Clone, Debug, Default)]
pub struct RenderedMarkdown {
    pub lines: Vec<Line<'static>>,
    pub links: Vec<MarkdownLink>,
}

pub fn render_markdown(markdown: &str) -> RenderedMarkdown {
    let mut lines = Vec::new();
    let mut links: Vec<MarkdownLink> = Vec::new();
    let mut current_spans: Vec<Span<'static>> = Vec::new();
    let mut current_col: usize = 0;

    let mut heading: Option<HeadingLevel> = None;
    let mut list_stack: Vec<ListContext> = Vec::new();
    let mut pending_list_prefix: Option<String> = None;
    let mut blockquote_depth: usize = 0;
    let mut in_code_block = false;
    let mut strong = false;
    let mut emphasis = false;
    let mut active_link: Option<ActiveLink> = None;

    let parser = Parser::new_ext(markdown, Options::all());
    for event in parser {
        match event {
            Event::Start(Tag::Heading { level, .. }) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
                heading = Some(level);
            }
            Event::End(TagEnd::Heading(_)) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
                heading = None;
            }
            Event::Start(Tag::Paragraph) => {}
            Event::End(TagEnd::Paragraph) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
            }
            Event::Start(Tag::List(start)) => {
                list_stack.push(ListContext::new(start.map(|value| value as usize)));
            }
            Event::End(TagEnd::List(_)) => {
                list_stack.pop();
            }
            Event::Start(Tag::Item) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
                pending_list_prefix = Some(list_prefix(&mut list_stack));
            }
            Event::End(TagEnd::Item) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
            }
            Event::Start(Tag::BlockQuote(_)) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
                blockquote_depth = blockquote_depth.saturating_add(1);
            }
            Event::End(TagEnd::BlockQuote(_)) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
                blockquote_depth = blockquote_depth.saturating_sub(1);
            }
            Event::Start(Tag::CodeBlock(_)) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
                in_code_block = true;
            }
            Event::End(TagEnd::CodeBlock) => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
                in_code_block = false;
            }
            Event::Start(Tag::Strong) => strong = true,
            Event::End(TagEnd::Strong) => strong = false,
            Event::Start(Tag::Emphasis) => emphasis = true,
            Event::End(TagEnd::Emphasis) => emphasis = false,
            Event::Start(Tag::Link { dest_url, .. }) => {
                active_link = Some(ActiveLink::new(dest_url.to_string()));
            }
            Event::End(TagEnd::Link) => {
                finalize_link_segment(&mut links, &mut active_link, lines.len(), current_col);
                active_link = None;
            }
            Event::Rule => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
                lines.push(Line::from(Span::styled(
                    "─".repeat(40),
                    Style::default().fg(Color::DarkGray),
                )));
            }
            Event::Text(text) => {
                let base_style = if in_code_block {
                    Style::default().bg(Color::Rgb(42, 42, 46))
                } else {
                    inline_style(strong, emphasis)
                };
                push_text(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &text,
                    base_style,
                    &mut pending_list_prefix,
                    blockquote_depth,
                    &mut active_link,
                );
            }
            Event::Code(code) => {
                ensure_prefix(
                    &mut current_spans,
                    &mut current_col,
                    &mut pending_list_prefix,
                    blockquote_depth,
                );
                let style = if active_link.is_some() {
                    link_style(Style::default().bg(Color::Rgb(42, 42, 46)))
                } else {
                    Style::default().bg(Color::Rgb(42, 42, 46))
                };
                let text = code.to_string();
                current_col = current_col.saturating_add(text.chars().count());
                if let Some(link) = active_link.as_mut() {
                    link.push_label(&text);
                    if link.segment_start_col.is_none() {
                        link.segment_start_col =
                            Some(current_col.saturating_sub(text.chars().count()));
                    }
                }
                current_spans.push(Span::styled(text, style));
            }
            Event::SoftBreak => {
                if in_code_block {
                    flush_line(
                        &mut lines,
                        &mut links,
                        &mut current_spans,
                        &mut current_col,
                        heading,
                        &mut active_link,
                    );
                } else {
                    ensure_prefix(
                        &mut current_spans,
                        &mut current_col,
                        &mut pending_list_prefix,
                        blockquote_depth,
                    );
                    current_col = current_col.saturating_add(1);
                    if let Some(link) = active_link.as_mut() {
                        link.push_label(" ");
                        if link.segment_start_col.is_none() {
                            link.segment_start_col = Some(current_col - 1);
                        }
                    }
                    current_spans.push(Span::raw(" "));
                }
            }
            Event::HardBreak => {
                flush_line(
                    &mut lines,
                    &mut links,
                    &mut current_spans,
                    &mut current_col,
                    heading,
                    &mut active_link,
                );
            }
            _ => {}
        }
    }

    flush_line(
        &mut lines,
        &mut links,
        &mut current_spans,
        &mut current_col,
        heading,
        &mut active_link,
    );

    if lines.is_empty() {
        lines.push(Line::from(""));
    }

    RenderedMarkdown { lines, links }
}

pub fn render_markdown_lines(markdown: &str) -> Vec<Line<'static>> {
    render_markdown(markdown).lines
}

#[derive(Clone)]
struct ListContext {
    ordered: bool,
    next_number: usize,
}

impl ListContext {
    fn new(start: Option<usize>) -> Self {
        Self {
            ordered: start.is_some(),
            next_number: start.unwrap_or(1),
        }
    }
}

#[derive(Clone)]
struct ActiveLink {
    url: String,
    label: String,
    segment_start_col: Option<usize>,
}

impl ActiveLink {
    fn new(url: String) -> Self {
        Self {
            url,
            label: String::new(),
            segment_start_col: None,
        }
    }

    fn push_label(&mut self, text: &str) {
        self.label.push_str(text);
    }
}

fn list_prefix(stack: &mut [ListContext]) -> String {
    if stack.is_empty() {
        return "• ".to_string();
    }

    let depth = stack.len();
    let indent = "  ".repeat(depth.saturating_sub(1));
    let current = stack.last_mut().expect("list stack not empty");

    if current.ordered {
        let number = current.next_number;
        current.next_number = current.next_number.saturating_add(1);
        format!("{indent}{number}. ")
    } else {
        let bullet = match depth {
            1 => "• ",
            2 => "◦ ",
            _ => "■ ",
        };
        format!("{indent}{bullet}")
    }
}

fn inline_style(strong: bool, emphasis: bool) -> Style {
    let mut style = Style::default();
    if strong {
        style = style.add_modifier(Modifier::BOLD);
    }
    if emphasis {
        style = style.add_modifier(Modifier::ITALIC);
    }
    style
}

fn link_style(base: Style) -> Style {
    base.fg(Color::Rgb(0, 120, 212))
        .add_modifier(Modifier::UNDERLINED)
}

fn heading_style(level: HeadingLevel) -> Style {
    match level {
        HeadingLevel::H1 => Style::default()
            .fg(Color::Cyan)
            .add_modifier(Modifier::BOLD),
        HeadingLevel::H2 => Style::default()
            .fg(Color::White)
            .add_modifier(Modifier::BOLD),
        HeadingLevel::H3 => Style::default()
            .fg(Color::Gray)
            .add_modifier(Modifier::BOLD),
        _ => Style::default().add_modifier(Modifier::BOLD),
    }
}

fn ensure_prefix(
    current_spans: &mut Vec<Span<'static>>,
    current_col: &mut usize,
    pending_list_prefix: &mut Option<String>,
    blockquote_depth: usize,
) {
    if current_spans.is_empty() {
        if blockquote_depth > 0 {
            let quote_prefix = "│ ".repeat(blockquote_depth);
            *current_col = current_col.saturating_add(quote_prefix.chars().count());
            current_spans.push(Span::styled(
                quote_prefix,
                Style::default().fg(Color::DarkGray),
            ));
        }
        if let Some(prefix) = pending_list_prefix.take() {
            *current_col = current_col.saturating_add(prefix.chars().count());
            current_spans.push(Span::raw(prefix));
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn push_text(
    lines: &mut Vec<Line<'static>>,
    links: &mut Vec<MarkdownLink>,
    current_spans: &mut Vec<Span<'static>>,
    current_col: &mut usize,
    heading: Option<HeadingLevel>,
    text: &str,
    style: Style,
    pending_list_prefix: &mut Option<String>,
    blockquote_depth: usize,
    active_link: &mut Option<ActiveLink>,
) {
    let parts: Vec<&str> = text.split('\n').collect();
    for (index, part) in parts.iter().enumerate() {
        if index > 0 {
            flush_line(
                lines,
                links,
                current_spans,
                current_col,
                heading,
                active_link,
            );
        }

        if part.is_empty() {
            continue;
        }

        ensure_prefix(
            current_spans,
            current_col,
            pending_list_prefix,
            blockquote_depth,
        );

        let text_style = if active_link.is_some() {
            link_style(style)
        } else {
            style
        };

        let value = (*part).to_string();
        let value_width = value.chars().count();

        if let Some(link) = active_link.as_mut() {
            if link.segment_start_col.is_none() {
                link.segment_start_col = Some(*current_col);
            }
            link.push_label(&value);
        }

        *current_col = current_col.saturating_add(value_width);
        current_spans.push(Span::styled(value, text_style));
    }
}

fn finalize_link_segment(
    links: &mut Vec<MarkdownLink>,
    active_link: &mut Option<ActiveLink>,
    line_index: usize,
    current_col: usize,
) {
    let Some(link) = active_link.as_mut() else {
        return;
    };

    let Some(start_col) = link.segment_start_col.take() else {
        return;
    };

    if current_col <= start_col {
        return;
    }

    links.push(MarkdownLink {
        index: links.len(),
        line_index,
        start_col,
        end_col: current_col,
        url: link.url.clone(),
        label: link.label.trim().to_string(),
    });
}

fn flush_line(
    lines: &mut Vec<Line<'static>>,
    links: &mut Vec<MarkdownLink>,
    current_spans: &mut Vec<Span<'static>>,
    current_col: &mut usize,
    heading: Option<HeadingLevel>,
    active_link: &mut Option<ActiveLink>,
) {
    finalize_link_segment(links, active_link, lines.len(), *current_col);

    if current_spans.is_empty() {
        *current_col = 0;
        return;
    }

    if let Some(level) = heading {
        let mut text = String::new();
        for span in current_spans.iter() {
            text.push_str(span.content.as_ref());
        }
        if matches!(level, HeadingLevel::H1) {
            text = text.to_ascii_uppercase();
        }
        lines.push(Line::from(Span::styled(text, heading_style(level))));
        current_spans.clear();
        *current_col = 0;
        return;
    }

    lines.push(Line::from(std::mem::take(current_spans)));
    *current_col = 0;
}

#[cfg(test)]
mod tests {
    use super::{render_markdown, render_markdown_lines};

    #[test]
    fn renders_ordered_and_unordered_lists() {
        let md = "1. first\n2. second\n   - child\n4. fourth";
        let lines = render_markdown_lines(md);
        let text = lines
            .iter()
            .map(|line| line.to_string())
            .collect::<Vec<_>>()
            .join("\n");

        assert!(text.contains("1. first"));
        assert!(text.contains("2. second"));
        assert!(text.contains("◦ child"));
        assert!(text.contains("fourth"));
        assert!(text.contains(". fourth"));
    }

    #[test]
    fn captures_links_with_positions() {
        let rendered = render_markdown("See [CLASSIC](https://example.com) docs");
        assert_eq!(rendered.links.len(), 1);
        let link = &rendered.links[0];
        assert_eq!(link.url, "https://example.com");
        assert_eq!(link.label, "CLASSIC");
        assert!(link.end_col > link.start_col);
    }

    #[test]
    fn renders_headings_lists_quotes_and_code() {
        let md = "# Title\n## Section\n- item one\n  - sub item\n> quoted\n```\ncode\n```";
        let lines = render_markdown_lines(md);
        let text = lines
            .iter()
            .map(|line| line.to_string())
            .collect::<Vec<_>>()
            .join("\n");

        assert!(text.contains("TITLE"));
        assert!(text.contains("Section"));
        assert!(text.contains("• item one"));
        assert!(text.contains("◦ sub item"));
        assert!(text.contains("│ quoted"));
        assert!(text.contains("code"));
    }

    #[test]
    fn renders_horizontal_rule() {
        let lines = render_markdown_lines("---");
        let text = lines
            .iter()
            .map(|line| line.to_string())
            .collect::<Vec<_>>()
            .join("\n");
        assert!(text.contains("────"));
    }
}
