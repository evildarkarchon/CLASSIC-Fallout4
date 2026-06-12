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
    let mut state = MarkdownRenderState::default();

    let parser = Parser::new_ext(markdown, Options::all());
    for event in parser {
        match event {
            Event::Start(Tag::Heading { level, .. }) => {
                state.flush_line();
                state.heading = Some(level);
            }
            Event::End(TagEnd::Heading(_)) => {
                state.flush_line();
                state.heading = None;
            }
            Event::Start(Tag::Paragraph) => {}
            Event::End(TagEnd::Paragraph) => {
                state.flush_line();
            }
            Event::Start(Tag::List(start)) => {
                state
                    .list_stack
                    .push(ListContext::new(start.map(|value| value as usize)));
            }
            Event::End(TagEnd::List(_)) => {
                state.list_stack.pop();
            }
            Event::Start(Tag::Item) => {
                state.flush_line();
                state.pending_list_prefix = Some(list_prefix(&mut state.list_stack));
            }
            Event::End(TagEnd::Item) => {
                state.flush_line();
            }
            Event::Start(Tag::BlockQuote(_)) => {
                state.flush_line();
                state.blockquote_depth = state.blockquote_depth.saturating_add(1);
            }
            Event::End(TagEnd::BlockQuote(_)) => {
                state.flush_line();
                state.blockquote_depth = state.blockquote_depth.saturating_sub(1);
            }
            Event::Start(Tag::CodeBlock(_)) => {
                state.flush_line();
                state.in_code_block = true;
            }
            Event::End(TagEnd::CodeBlock) => {
                state.flush_line();
                state.in_code_block = false;
            }
            Event::Start(Tag::Strong) => state.strong = true,
            Event::End(TagEnd::Strong) => state.strong = false,
            Event::Start(Tag::Emphasis) => state.emphasis = true,
            Event::End(TagEnd::Emphasis) => state.emphasis = false,
            Event::Start(Tag::Link { dest_url, .. }) => {
                state.active_link = Some(ActiveLink::new(dest_url.to_string()));
            }
            Event::End(TagEnd::Link) => {
                state.finalize_link_segment();
                state.active_link = None;
            }
            Event::Rule => {
                state.flush_line();
                state.lines.push(Line::from(Span::styled(
                    "─".repeat(40),
                    Style::default().fg(Color::DarkGray),
                )));
            }
            Event::Text(text) => {
                let base_style = if state.in_code_block {
                    Style::default().bg(Color::Rgb(42, 42, 46))
                } else {
                    inline_style(state.strong, state.emphasis)
                };
                state.push_text(&text, base_style);
            }
            Event::Code(code) => {
                state.push_code(&code);
            }
            Event::SoftBreak => {
                if state.in_code_block {
                    state.flush_line();
                } else {
                    state.push_soft_break_space();
                }
            }
            Event::HardBreak => {
                state.flush_line();
            }
            _ => {}
        }
    }

    state.into_rendered()
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

#[derive(Default)]
struct MarkdownRenderState {
    lines: Vec<Line<'static>>,
    links: Vec<MarkdownLink>,
    current_spans: Vec<Span<'static>>,
    current_col: usize,
    heading: Option<HeadingLevel>,
    list_stack: Vec<ListContext>,
    pending_list_prefix: Option<String>,
    blockquote_depth: usize,
    in_code_block: bool,
    strong: bool,
    emphasis: bool,
    active_link: Option<ActiveLink>,
}

impl MarkdownRenderState {
    fn flush_line(&mut self) {
        flush_line(
            &mut self.lines,
            &mut self.links,
            &mut self.current_spans,
            &mut self.current_col,
            self.heading,
            &mut self.active_link,
        );
    }

    fn finalize_link_segment(&mut self) {
        finalize_link_segment(
            &mut self.links,
            &mut self.active_link,
            self.lines.len(),
            self.current_col,
        );
    }

    fn ensure_prefix(&mut self) {
        ensure_prefix(
            &mut self.current_spans,
            &mut self.current_col,
            &mut self.pending_list_prefix,
            self.blockquote_depth,
        );
    }

    fn push_text(&mut self, text: &str, style: Style) {
        push_text(
            &mut self.lines,
            &mut self.links,
            &mut self.current_spans,
            &mut self.current_col,
            self.heading,
            text,
            style,
            &mut self.pending_list_prefix,
            self.blockquote_depth,
            &mut self.active_link,
        );
    }

    fn push_code(&mut self, code: &str) {
        self.ensure_prefix();
        let style = if self.active_link.is_some() {
            link_style(Style::default().bg(Color::Rgb(42, 42, 46)))
        } else {
            Style::default().bg(Color::Rgb(42, 42, 46))
        };
        let text = code.to_string();
        let text_width = text.chars().count();
        self.current_col = self.current_col.saturating_add(text_width);
        if let Some(link) = self.active_link.as_mut() {
            link.push_label(&text);
            if link.segment_start_col.is_none() {
                link.segment_start_col = Some(self.current_col.saturating_sub(text_width));
            }
        }
        self.current_spans.push(Span::styled(text, style));
    }

    fn push_soft_break_space(&mut self) {
        self.ensure_prefix();
        self.current_col = self.current_col.saturating_add(1);
        if let Some(link) = self.active_link.as_mut() {
            link.push_label(" ");
            if link.segment_start_col.is_none() {
                link.segment_start_col = Some(self.current_col - 1);
            }
        }
        self.current_spans.push(Span::raw(" "));
    }

    fn into_rendered(mut self) -> RenderedMarkdown {
        self.flush_line();
        if self.lines.is_empty() {
            self.lines.push(Line::from(""));
        }
        RenderedMarkdown {
            lines: self.lines,
            links: self.links,
        }
    }
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
    let Some(current) = stack.last_mut() else {
        return "• ".to_string();
    };

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
#[path = "results_markdown_tests.rs"]
mod tests;
