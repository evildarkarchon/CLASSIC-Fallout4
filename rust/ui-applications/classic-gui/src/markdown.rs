//! Markdown parser for CLASSIC report rendering
//!
//! Parses markdown-formatted crash log reports into a flat vector of
//! [`MarkdownBlock`] structs that Slint can iterate and render with
//! type-discriminated conditional visibility.
//!
//! Uses `pulldown-cmark` for CommonMark-compliant parsing.

use pulldown_cmark::{Event, HeadingLevel, Parser, Tag, TagEnd};

/// Block type constant: paragraph (plain text)
pub const BLOCK_PARAGRAPH: i32 = 0;
/// Block type constant: heading (H1-H3)
pub const BLOCK_HEADING: i32 = 1;
/// Block type constant: fenced/indented code block
pub const BLOCK_CODE: i32 = 2;
/// Block type constant: horizontal rule
pub const BLOCK_RULE: i32 = 3;
/// Block type constant: bullet list item
pub const BLOCK_LIST_ITEM: i32 = 4;
/// Block type constant: blockquote
pub const BLOCK_BLOCKQUOTE: i32 = 5;

/// Intermediate representation of a rendered markdown block.
///
/// Each block maps to one visual element in the Slint report viewer.
/// The `block_type` field discriminates which rendering path Slint uses.
#[derive(Clone, Debug, PartialEq)]
pub struct MarkdownBlock {
    /// Type discriminator (see `BLOCK_*` constants)
    pub block_type: i32,
    /// Rendered text content (no markdown syntax)
    pub text: String,
    /// Heading level (1, 2, or 3) -- only meaningful for heading blocks
    pub heading_level: i32,
    /// Whether text is bold
    pub is_bold: bool,
    /// Whether text is italic
    pub is_italic: bool,
    /// Nesting depth for list items (0-based for Slint padding calculation)
    pub indent_level: i32,
    /// Bullet character for list items
    pub bullet_marker: String,
}

impl MarkdownBlock {
    /// Create a heading block (always bold)
    pub fn heading(level: i32, text: &str) -> Self {
        Self {
            block_type: BLOCK_HEADING,
            text: text.to_string(),
            heading_level: level,
            is_bold: true,
            is_italic: false,
            indent_level: 0,
            bullet_marker: String::new(),
        }
    }

    /// Create a paragraph block with optional bold/italic
    pub fn paragraph(text: &str, bold: bool, italic: bool) -> Self {
        Self {
            block_type: BLOCK_PARAGRAPH,
            text: text.to_string(),
            heading_level: 0,
            is_bold: bold,
            is_italic: italic,
            indent_level: 0,
            bullet_marker: String::new(),
        }
    }

    /// Create a code block (monospace with background)
    pub fn code_block(text: &str) -> Self {
        Self {
            block_type: BLOCK_CODE,
            text: text.trim_end_matches('\n').to_string(),
            heading_level: 0,
            is_bold: false,
            is_italic: false,
            indent_level: 0,
            bullet_marker: String::new(),
        }
    }

    /// Create a horizontal rule block (thin visible line)
    pub fn rule() -> Self {
        Self {
            block_type: BLOCK_RULE,
            text: String::new(),
            heading_level: 0,
            is_bold: false,
            is_italic: false,
            indent_level: 0,
            bullet_marker: String::new(),
        }
    }

    /// Create a list item block with depth-based bullet markers
    ///
    /// Depth is 1-based from pulldown-cmark's list nesting:
    /// - depth 1: filled bullet (U+2022)
    /// - depth 2: open circle (U+25E6)
    /// - depth 3+: small square (U+25AA)
    ///
    /// `indent_level` is depth - 1 (0-based for Slint padding calculation).
    pub fn list_item(depth: i32, text: &str, bold: bool) -> Self {
        let marker = match depth {
            1 => "\u{2022}",
            2 => "\u{25E6}",
            _ => "\u{25AA}",
        };
        Self {
            block_type: BLOCK_LIST_ITEM,
            text: text.to_string(),
            heading_level: 0,
            is_bold: bold,
            is_italic: false,
            indent_level: depth - 1,
            bullet_marker: marker.to_string(),
        }
    }

    /// Create a blockquote block (left border bar)
    pub fn blockquote(text: &str, bold: bool) -> Self {
        Self {
            block_type: BLOCK_BLOCKQUOTE,
            text: text.to_string(),
            heading_level: 0,
            is_bold: bold,
            is_italic: false,
            indent_level: 0,
            bullet_marker: String::new(),
        }
    }
}

/// Parse a markdown string into a flat vector of [`MarkdownBlock`]s.
///
/// Uses pulldown-cmark with default CommonMark options. Each block
/// corresponds to one visual element in the Slint report viewer.
///
/// Inline formatting is flattened to block level: a paragraph containing
/// `**bold**` text becomes a bold paragraph. This matches the CLASSIC
/// report format where bold/italic is used at the line level.
pub fn parse_markdown(source: &str) -> Vec<MarkdownBlock> {
    let parser = Parser::new(source);
    let mut blocks = Vec::new();
    let mut current_text = String::new();
    let mut heading_level: i32 = 0;
    let mut in_strong = false;
    let mut in_emphasis = false;
    let mut in_list_item = false;
    let mut list_depth: i32 = 0;
    let mut in_blockquote = false;

    for event in parser {
        match event {
            Event::Start(Tag::Heading { level, .. }) => {
                heading_level = match level {
                    HeadingLevel::H1 => 1,
                    HeadingLevel::H2 => 2,
                    HeadingLevel::H3 => 3,
                    _ => 4,
                };
            }
            Event::End(TagEnd::Heading(_)) => {
                blocks.push(MarkdownBlock::heading(heading_level, &current_text));
                current_text.clear();
                in_strong = false;
                in_emphasis = false;
            }
            Event::Start(Tag::Paragraph) => {}
            Event::End(TagEnd::Paragraph) => {
                if !current_text.is_empty() {
                    if in_blockquote {
                        blocks.push(MarkdownBlock::blockquote(&current_text, in_strong));
                    } else if in_list_item {
                        // Paragraph inside a list item -- accumulate text for the item
                        // Don't push yet; the Item end event will handle it
                    } else {
                        blocks.push(MarkdownBlock::paragraph(
                            &current_text, in_strong, in_emphasis,
                        ));
                        current_text.clear();
                    }
                    if !in_list_item {
                        current_text.clear();
                        in_strong = false;
                        in_emphasis = false;
                    }
                }
            }
            Event::Start(Tag::CodeBlock(_)) => {}
            Event::End(TagEnd::CodeBlock) => {
                blocks.push(MarkdownBlock::code_block(&current_text));
                current_text.clear();
            }
            Event::Start(Tag::Strong) => {
                in_strong = true;
            }
            Event::End(TagEnd::Strong) => {
                // stays bold for the duration of the block
            }
            Event::Start(Tag::Emphasis) => {
                in_emphasis = true;
            }
            Event::End(TagEnd::Emphasis) => {
                // stays italic for the duration of the block
            }
            Event::Start(Tag::List(_)) => {
                list_depth += 1;
            }
            Event::End(TagEnd::List(_)) => {
                list_depth -= 1;
            }
            Event::Start(Tag::Item) => {
                in_list_item = true;
            }
            Event::End(TagEnd::Item) => {
                if !current_text.is_empty() {
                    blocks.push(MarkdownBlock::list_item(
                        list_depth, &current_text, in_strong,
                    ));
                    current_text.clear();
                }
                in_list_item = false;
                in_strong = false;
                in_emphasis = false;
            }
            Event::Start(Tag::BlockQuote(_)) => {
                in_blockquote = true;
            }
            Event::End(TagEnd::BlockQuote(_)) => {
                if !current_text.is_empty() {
                    blocks.push(MarkdownBlock::blockquote(&current_text, in_strong));
                    current_text.clear();
                    in_strong = false;
                }
                in_blockquote = false;
            }
            Event::Rule => {
                blocks.push(MarkdownBlock::rule());
            }
            Event::Text(text) => {
                current_text.push_str(&text);
            }
            Event::Code(code) => {
                // Inline code -- append with backtick markers since Slint Text
                // cannot do partial background highlighting
                current_text.push('`');
                current_text.push_str(&code);
                current_text.push('`');
            }
            Event::SoftBreak => {
                current_text.push(' ');
            }
            Event::HardBreak => {
                current_text.push('\n');
            }
            _ => {
                // Ignore: HTML events, footnotes, images, table events, metadata
            }
        }
    }

    blocks
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heading_h1() {
        let blocks = parse_markdown("# Hello");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_HEADING);
        assert_eq!(blocks[0].text, "Hello");
        assert_eq!(blocks[0].heading_level, 1);
        assert!(blocks[0].is_bold);
    }

    #[test]
    fn test_heading_h3() {
        let blocks = parse_markdown("### Section");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_HEADING);
        assert_eq!(blocks[0].text, "Section");
        assert_eq!(blocks[0].heading_level, 3);
        assert!(blocks[0].is_bold);
    }

    #[test]
    fn test_paragraph() {
        let blocks = parse_markdown("Hello world");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_PARAGRAPH);
        assert_eq!(blocks[0].text, "Hello world");
        assert!(!blocks[0].is_bold);
        assert!(!blocks[0].is_italic);
    }

    #[test]
    fn test_bold_paragraph() {
        let blocks = parse_markdown("**Bold text**");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_PARAGRAPH);
        assert!(blocks[0].is_bold);
        assert_eq!(blocks[0].text, "Bold text");
    }

    #[test]
    fn test_italic_paragraph() {
        let blocks = parse_markdown("*Italic text*");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_PARAGRAPH);
        assert!(blocks[0].is_italic);
        assert_eq!(blocks[0].text, "Italic text");
    }

    #[test]
    fn test_code_block() {
        let blocks = parse_markdown("```\nsome code\nmore code\n```");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_CODE);
        assert_eq!(blocks[0].text, "some code\nmore code");
    }

    #[test]
    fn test_horizontal_rule() {
        let blocks = parse_markdown("---");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_RULE);
        assert!(blocks[0].text.is_empty());
    }

    #[test]
    fn test_bullet_list() {
        let blocks = parse_markdown("- Item one\n- Item two");
        assert_eq!(blocks.len(), 2);
        assert_eq!(blocks[0].block_type, BLOCK_LIST_ITEM);
        assert_eq!(blocks[0].text, "Item one");
        assert_eq!(blocks[0].bullet_marker, "\u{2022}");
        assert_eq!(blocks[0].indent_level, 0);
        assert_eq!(blocks[1].block_type, BLOCK_LIST_ITEM);
        assert_eq!(blocks[1].text, "Item two");
    }

    #[test]
    fn test_blockquote() {
        let blocks = parse_markdown("> Some quote");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_BLOCKQUOTE);
        assert_eq!(blocks[0].text, "Some quote");
    }

    #[test]
    fn test_mixed_content() {
        let input = "# Title\n\nSome text\n\n---\n\n- Item A\n- Item B";
        let blocks = parse_markdown(input);

        // heading, paragraph, rule, 2 list items = 5
        assert_eq!(blocks.len(), 5);
        assert_eq!(blocks[0].block_type, BLOCK_HEADING);
        assert_eq!(blocks[1].block_type, BLOCK_PARAGRAPH);
        assert_eq!(blocks[2].block_type, BLOCK_RULE);
        assert_eq!(blocks[3].block_type, BLOCK_LIST_ITEM);
        assert_eq!(blocks[4].block_type, BLOCK_LIST_ITEM);
    }

    #[test]
    fn test_empty_input() {
        let blocks = parse_markdown("");
        assert!(blocks.is_empty());
    }

    #[test]
    fn test_inline_code() {
        let blocks = parse_markdown("Use `my_function()` here");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_PARAGRAPH);
        assert_eq!(blocks[0].text, "Use `my_function()` here");
    }

    #[test]
    fn test_blockquote_bold() {
        let blocks = parse_markdown("> **Bold quote**");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_BLOCKQUOTE);
        assert!(blocks[0].is_bold);
        assert_eq!(blocks[0].text, "Bold quote");
    }

    // ---- Additional coverage tests ----

    #[test]
    fn test_heading_h2() {
        let blocks = parse_markdown("## Subsection");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].heading_level, 2);
        assert_eq!(blocks[0].text, "Subsection");
    }

    #[test]
    fn test_heading_h4_maps_to_level_4() {
        let blocks = parse_markdown("#### Deep heading");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].heading_level, 4);
        assert_eq!(blocks[0].text, "Deep heading");
    }

    #[test]
    fn test_nested_list() {
        let input = "- Item 1\n  - Sub-item A\n  - Sub-item B\n- Item 2";
        let blocks = parse_markdown(input);
        // Should have outer and inner list items
        assert!(blocks.len() >= 3, "Expected at least 3 items, got {}", blocks.len());
        // First item at depth 1
        assert_eq!(blocks[0].block_type, BLOCK_LIST_ITEM);
    }

    #[test]
    fn test_bold_list_item() {
        let input = "- **Bold item**";
        let blocks = parse_markdown(input);
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_LIST_ITEM);
        assert!(blocks[0].is_bold);
        assert_eq!(blocks[0].text, "Bold item");
    }

    #[test]
    fn test_soft_break_becomes_space() {
        // A soft break (single newline in paragraph) becomes a space
        let input = "Line one\nLine two";
        let blocks = parse_markdown(input);
        assert_eq!(blocks.len(), 1);
        assert!(blocks[0].text.contains("Line one"));
        assert!(blocks[0].text.contains("Line two"));
    }

    #[test]
    fn test_hard_break_becomes_newline() {
        // Two spaces followed by newline = hard break
        let input = "Line one  \nLine two";
        let blocks = parse_markdown(input);
        assert_eq!(blocks.len(), 1);
        assert!(blocks[0].text.contains('\n'), "Hard break should become newline");
    }

    #[test]
    fn test_multiple_paragraphs() {
        let input = "Paragraph one\n\nParagraph two\n\nParagraph three";
        let blocks = parse_markdown(input);
        assert_eq!(blocks.len(), 3);
        for block in &blocks {
            assert_eq!(block.block_type, BLOCK_PARAGRAPH);
        }
    }

    #[test]
    fn test_code_block_trailing_newline_trimmed() {
        let blocks = parse_markdown("```\ncode line\n```");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, BLOCK_CODE);
        assert!(!blocks[0].text.ends_with('\n'), "Trailing newline should be trimmed");
    }

    #[test]
    fn test_markdown_block_constructors() {
        // Test heading constructor
        let h = MarkdownBlock::heading(2, "Title");
        assert_eq!(h.block_type, BLOCK_HEADING);
        assert_eq!(h.heading_level, 2);
        assert!(h.is_bold);
        assert!(!h.is_italic);
        assert_eq!(h.indent_level, 0);

        // Test paragraph constructor
        let p = MarkdownBlock::paragraph("text", true, true);
        assert_eq!(p.block_type, BLOCK_PARAGRAPH);
        assert!(p.is_bold);
        assert!(p.is_italic);

        // Test code_block constructor
        let c = MarkdownBlock::code_block("fn main() {}\n");
        assert_eq!(c.block_type, BLOCK_CODE);
        assert_eq!(c.text, "fn main() {}"); // trailing newline trimmed

        // Test rule constructor
        let r = MarkdownBlock::rule();
        assert_eq!(r.block_type, BLOCK_RULE);
        assert!(r.text.is_empty());

        // Test list_item constructor at various depths
        let l1 = MarkdownBlock::list_item(1, "Level 1", false);
        assert_eq!(l1.bullet_marker, "\u{2022}");
        assert_eq!(l1.indent_level, 0);

        let l2 = MarkdownBlock::list_item(2, "Level 2", false);
        assert_eq!(l2.bullet_marker, "\u{25E6}");
        assert_eq!(l2.indent_level, 1);

        let l3 = MarkdownBlock::list_item(3, "Level 3", true);
        assert_eq!(l3.bullet_marker, "\u{25AA}");
        assert_eq!(l3.indent_level, 2);
        assert!(l3.is_bold);

        // Test blockquote constructor
        let bq = MarkdownBlock::blockquote("Quote", false);
        assert_eq!(bq.block_type, BLOCK_BLOCKQUOTE);
        assert!(!bq.is_bold);
    }

    #[test]
    fn test_multiple_horizontal_rules() {
        let input = "---\n\n---\n\n---";
        let blocks = parse_markdown(input);
        assert_eq!(blocks.len(), 3);
        for block in &blocks {
            assert_eq!(block.block_type, BLOCK_RULE);
        }
    }

    #[test]
    fn test_block_constants_distinct() {
        let types = [BLOCK_PARAGRAPH, BLOCK_HEADING, BLOCK_CODE, BLOCK_RULE, BLOCK_LIST_ITEM, BLOCK_BLOCKQUOTE];
        for (i, a) in types.iter().enumerate() {
            for (j, b) in types.iter().enumerate() {
                if i != j {
                    assert_ne!(a, b, "Block type constants should be distinct");
                }
            }
        }
    }

    #[test]
    fn test_bold_and_italic_paragraph() {
        // Bold and italic combined
        let blocks = parse_markdown("***Bold italic***");
        assert_eq!(blocks.len(), 1);
        assert!(blocks[0].is_bold);
        assert!(blocks[0].is_italic);
    }

    #[test]
    fn test_blockquote_multiline() {
        let input = "> Line one\n> Line two";
        let blocks = parse_markdown(input);
        assert!(!blocks.is_empty());
        assert_eq!(blocks[0].block_type, BLOCK_BLOCKQUOTE);
    }

    #[test]
    fn test_markdown_block_equality() {
        let a = MarkdownBlock::paragraph("text", false, false);
        let b = MarkdownBlock::paragraph("text", false, false);
        assert_eq!(a, b);

        let c = MarkdownBlock::paragraph("text", true, false);
        assert_ne!(a, c);
    }
}
