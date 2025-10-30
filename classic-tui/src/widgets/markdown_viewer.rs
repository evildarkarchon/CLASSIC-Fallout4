//! Markdown rendering for terminal with URL detection and link support.
//!
//! This module provides markdown-to-terminal rendering using pulldown-cmark,
//! with URL detection, styling, and interactive link opening capabilities.

use pulldown_cmark::{Event, Options, Parser, Tag, TagEnd};
use ratatui::{
    style::{Color, Modifier, Style},
    text::{Line, Span},
};

/// A rendered markdown document with styled lines and extracted URLs.
#[derive(Debug, Clone)]
pub struct RenderedMarkdown {
    /// Styled lines ready for terminal display
    pub lines: Vec<Line<'static>>,
    /// Detected URLs with their line numbers
    pub urls: Vec<DetectedUrl>,
}

/// A URL detected in the markdown content.
#[derive(Debug, Clone)]
pub struct DetectedUrl {
    /// The URL string
    pub url: String,
    /// Line number where the URL appears (0-indexed)
    ///
    /// Reserved for future URL navigation feature that allows jumping to specific lines.
    #[allow(dead_code)]
    pub line_number: usize,
    /// Display text for the URL
    pub display_text: String,
}

/// Markdown renderer with terminal-friendly styling.
pub struct MarkdownRenderer {
    /// Current line being built
    current_line: Vec<Span<'static>>,
    /// Completed lines
    lines: Vec<Line<'static>>,
    /// Detected URLs
    urls: Vec<DetectedUrl>,
    /// Current heading level (for styling)
    heading_level: Option<usize>,
    /// Currently inside code block
    in_code_block: bool,
    /// Currently inside emphasis
    in_emphasis: bool,
    /// Currently inside strong emphasis
    in_strong: bool,
    /// Currently inside a link
    in_link: bool,
    /// Current link URL being accumulated
    current_link_url: Option<String>,
    /// Current link text being accumulated
    current_link_text: String,
}

impl MarkdownRenderer {
    /// Create a new markdown renderer.
    pub fn new() -> Self {
        Self {
            current_line: Vec::new(),
            lines: Vec::new(),
            urls: Vec::new(),
            heading_level: None,
            in_code_block: false,
            in_emphasis: false,
            in_strong: false,
            in_link: false,
            current_link_url: None,
            current_link_text: String::new(),
        }
    }

    /// Render markdown text to styled terminal lines with URL detection.
    ///
    /// # Arguments
    ///
    /// * `markdown` - Raw markdown text
    ///
    /// # Returns
    ///
    /// Returns a `RenderedMarkdown` containing styled lines and detected URLs.
    ///
    /// # Examples
    ///
    /// ```no_run
    /// use classic_tui::widgets::markdown_viewer::MarkdownRenderer;
    ///
    /// let renderer = MarkdownRenderer::new();
    /// let markdown = "# Heading\n\nSome text with [link](https://example.com)";
    /// let rendered = renderer.render(markdown);
    ///
    /// println!("Found {} URLs", rendered.urls.len());
    /// ```
    pub fn render(mut self, markdown: &str) -> RenderedMarkdown {
        let options = Options::empty();
        let parser = Parser::new_ext(markdown, options);

        for event in parser {
            self.handle_event(event);
        }

        // Flush any remaining content
        self.finish_line();

        RenderedMarkdown {
            lines: self.lines,
            urls: self.urls,
        }
    }

    /// Handle a single markdown parse event.
    fn handle_event(&mut self, event: Event) {
        match event {
            Event::Start(tag) => self.handle_start_tag(tag),
            Event::End(tag_end) => self.handle_end_tag(tag_end),
            Event::Text(text) => self.handle_text(&text),
            Event::Code(code) => self.handle_code(&code),
            Event::SoftBreak | Event::HardBreak => self.finish_line(),
            Event::Rule => {
                self.finish_line();
                self.current_line.push(Span::styled(
                    "─".repeat(60),
                    Style::default().fg(Color::DarkGray),
                ));
                self.finish_line();
            }
            _ => {}
        }
    }

    /// Handle opening tags.
    fn handle_start_tag(&mut self, tag: Tag) {
        match tag {
            Tag::Heading { level, .. } => {
                self.heading_level = Some(level as usize);
            }
            Tag::Paragraph => {
                // Start a new paragraph (blank line before it)
                if !self.lines.is_empty() && !self.current_line.is_empty() {
                    self.finish_line();
                }
            }
            Tag::CodeBlock(_) => {
                self.in_code_block = true;
                self.finish_line();
            }
            Tag::Emphasis => {
                self.in_emphasis = true;
            }
            Tag::Strong => {
                self.in_strong = true;
            }
            Tag::Link { dest_url, .. } => {
                self.in_link = true;
                self.current_link_url = Some(dest_url.to_string());
                self.current_link_text.clear();
            }
            Tag::List(_) => {
                self.finish_line();
            }
            Tag::Item => {
                // Add bullet point
                self.current_line.push(Span::styled(
                    "• ",
                    Style::default().fg(Color::Yellow),
                ));
            }
            _ => {}
        }
    }

    /// Handle closing tags.
    fn handle_end_tag(&mut self, tag_end: TagEnd) {
        match tag_end {
            TagEnd::Heading(_) => {
                self.finish_line();
                self.heading_level = None;
            }
            TagEnd::Paragraph => {
                self.finish_line();
            }
            TagEnd::CodeBlock => {
                self.in_code_block = false;
                self.finish_line();
            }
            TagEnd::Emphasis => {
                self.in_emphasis = false;
            }
            TagEnd::Strong => {
                self.in_strong = false;
            }
            TagEnd::Link => {
                if let Some(url) = self.current_link_url.take() {
                    let display_text = if self.current_link_text.is_empty() {
                        url.clone()
                    } else {
                        self.current_link_text.clone()
                    };

                    // Record the URL
                    self.urls.push(DetectedUrl {
                        url: url.clone(),
                        line_number: self.lines.len(),
                        display_text: display_text.clone(),
                    });

                    // Add styled link span
                    self.current_line.push(Span::styled(
                        format!("[{}]", display_text),
                        Style::default()
                            .fg(Color::Blue)
                            .add_modifier(Modifier::UNDERLINED),
                    ));
                }
                self.in_link = false;
                self.current_link_text.clear();
            }
            TagEnd::Item => {
                self.finish_line();
            }
            _ => {}
        }
    }

    /// Handle text content.
    fn handle_text(&mut self, text: &str) {
        if self.in_link {
            // Accumulate link text for later
            self.current_link_text.push_str(text);
            return;
        }

        let style = self.get_current_style();
        self.current_line
            .push(Span::styled(text.to_string(), style));
    }

    /// Handle inline code.
    fn handle_code(&mut self, code: &str) {
        self.current_line.push(Span::styled(
            format!("`{}`", code),
            Style::default()
                .fg(Color::Green)
                .add_modifier(Modifier::BOLD),
        ));
    }

    /// Get the current text style based on context.
    fn get_current_style(&self) -> Style {
        let mut style = Style::default();

        if let Some(level) = self.heading_level {
            style = style.fg(Color::Cyan).add_modifier(Modifier::BOLD);
            if level == 1 {
                style = style.add_modifier(Modifier::UNDERLINED);
            }
        } else if self.in_code_block {
            style = style.fg(Color::Green);
        } else if self.in_strong {
            style = style.add_modifier(Modifier::BOLD);
        } else if self.in_emphasis {
            style = style.add_modifier(Modifier::ITALIC);
        }

        style
    }

    /// Finish the current line and add it to lines.
    fn finish_line(&mut self) {
        if !self.current_line.is_empty() || self.heading_level.is_some() {
            let line = Line::from(std::mem::take(&mut self.current_line));
            self.lines.push(line);
        } else if self.in_code_block {
            // Preserve empty lines in code blocks
            self.lines.push(Line::from(""));
        }
    }
}

impl Default for MarkdownRenderer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_markdown() {
        let renderer = MarkdownRenderer::new();
        let markdown = "# Heading\n\nSome **bold** and *italic* text.";
        let rendered = renderer.render(markdown);

        assert!(!rendered.lines.is_empty());
        assert_eq!(rendered.urls.len(), 0);
    }

    #[test]
    fn test_link_detection() {
        let renderer = MarkdownRenderer::new();
        let markdown = "Check [this link](https://example.com) for more info.";
        let rendered = renderer.render(markdown);

        assert_eq!(rendered.urls.len(), 1);
        assert_eq!(rendered.urls[0].url, "https://example.com");
        assert_eq!(rendered.urls[0].display_text, "this link");
    }

    #[test]
    fn test_multiple_links() {
        let renderer = MarkdownRenderer::new();
        let markdown = "[Link 1](https://example.com/1)\n[Link 2](https://example.com/2)";
        let rendered = renderer.render(markdown);

        assert_eq!(rendered.urls.len(), 2);
        assert_eq!(rendered.urls[0].url, "https://example.com/1");
        assert_eq!(rendered.urls[1].url, "https://example.com/2");
    }

    #[test]
    fn test_code_blocks() {
        let renderer = MarkdownRenderer::new();
        let markdown = "```rust\nfn main() {\n    println!(\"Hello\");\n}\n```";
        let rendered = renderer.render(markdown);

        assert!(!rendered.lines.is_empty());
    }

    #[test]
    fn test_lists() {
        let renderer = MarkdownRenderer::new();
        let markdown = "- Item 1\n- Item 2\n- Item 3";
        let rendered = renderer.render(markdown);

        assert_eq!(rendered.lines.len(), 3);
    }
}
