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

/// Normalize CLASSIC report content for CommonMark-compliant parsing.
///
/// CLASSIC reports use patterns that break standard markdown parsers:
/// - `* text *` patterns where the leading `*` is parsed as a list bullet marker
///   instead of decorative framing text
/// - Indented `-----` (4+ spaces) that becomes a code block instead of a
///   thematic break separator
/// - `-----` (thematic breaks) immediately before headings with no blank line,
///   which can prevent heading recognition in some contexts
///
/// This function normalizes these patterns before passing to pulldown-cmark.
fn normalize_report_content(source: &str) -> String {
    let mut lines: Vec<String> = Vec::new();

    for line in source.lines() {
        let trimmed = line.trim();

        // Convert indented ----- to regular thematic break.
        // In CommonMark, 4+ space indent makes it an indented code block.
        if trimmed == "-----" && line.starts_with(' ') {
            lines.push("-----".to_string());
            continue;
        }

        // Also handle indented ----- with trailing whitespace (e.g. "    -----  ")
        if trimmed.chars().all(|c| c == '-') && trimmed.len() >= 3 && line.starts_with(' ') {
            lines.push(trimmed.to_string());
            continue;
        }

        // Remove standalone * text * framing patterns that aren't real list items.
        // In CLASSIC reports, lines like:
        //   * **SUSPECTS DETECTED!** *
        //   * COULDN'T FIND ANY PLUGIN SUSPECTS *
        // use outer asterisks as decorative framing. CommonMark parses the leading
        // `*` as a list bullet marker, which is wrong. We strip the framing
        // asterisks and keep only the inner content.
        if trimmed.starts_with("* ") && trimmed.ends_with(" *") && !trimmed.starts_with("* -") {
            let inner = &trimmed[2..trimmed.len() - 2];
            if !inner.is_empty() {
                lines.push(inner.to_string());
                continue;
            }
        }

        lines.push(line.to_string());
    }

    // Ensure blank lines before headings that follow thematic breaks.
    // Pattern: "-----\n### Heading" -> "-----\n\n### Heading"
    // Without the blank line, some content combinations can prevent
    // the heading from being recognized.
    let mut result = Vec::new();
    for (i, line) in lines.iter().enumerate() {
        result.push(line.clone());

        // If this line is a thematic break and the next line is a heading,
        // insert a blank line between them
        let trimmed = line.trim();
        let is_thematic_break = trimmed == "---" || trimmed == "-----"
            || (trimmed.chars().all(|c| c == '-') && trimmed.len() >= 3);
        if is_thematic_break && i + 1 < lines.len() {
            let next_trimmed = lines[i + 1].trim();
            if next_trimmed.starts_with("### ")
                || next_trimmed.starts_with("## ")
                || next_trimmed.starts_with("# ")
            {
                result.push(String::new());
            }
        }
    }

    result.join("\n")
}

/// Parse a markdown string into a flat vector of [`MarkdownBlock`]s.
///
/// Uses pulldown-cmark with default CommonMark options. Each block
/// corresponds to one visual element in the Slint report viewer.
///
/// Inline formatting is flattened to block level: a paragraph containing
/// `**bold**` text becomes a bold paragraph. This matches the CLASSIC
/// report format where bold/italic is used at the line level.
///
/// Report content is normalized before parsing to handle CLASSIC-specific
/// patterns that break CommonMark (see [`normalize_report_content`]).
pub fn parse_markdown(source: &str) -> Vec<MarkdownBlock> {
    let normalized = normalize_report_content(source);
    let parser = Parser::new(&normalized);
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

    #[test]
    fn test_full_report_all_sections_present() {
        // Content extracted from real CLASSIC crash report:
        // Crash Logs/crash-2025-08-25-08-22-24-AUTOSCAN.md
        // Includes all the problematic patterns that break CommonMark parsing:
        // 1. "-----" thematic break immediately before "###" heading with no blank line
        // 2. "* text *" patterns parsed as emphasis markers
        // 3. Indented "    -----" treated as code block
        //
        // IMPORTANT: The exact whitespace patterns from the real report are preserved.
        // Lines 47-48: "-----\n### Checking For Mods..." (no blank line)
        // Lines 54-55: "    -----  \n### Checking for Important Mods" (indented separator)
        // Line 29: "* **SUSPECTS...** *" (star-wrapped text)
        // Line 74: "* COULDN'T FIND... *" (star-wrapped text)
        let report = "# crash-2025-08-25-08-22-24.log\n\
**AUTOSCAN REPORT GENERATED BY CLASSIC v8.2.0**\n\
\n\
> **FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR**\n\
\n\
---\n\
\n\
### Error Information\n\
\n\
**Main Error:** Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF68919FECE\n\
\n\
---\n\
\n\
### Checking for Known Crash Messages, Errors and Suspects\n\
\n\
- **Checking for NPC Pathing Crash (D)............................. SUSPECT FOUND! > Severity : 3** \n\
\n\
-----\n\
- **Checking for NPC Pathing Crash (S)............................. SUSPECT FOUND! > Severity : 3** \n\
\n\
-----\n\
* **ONE OR MORE SUSPECTS DETECTED! CHECK LOG ABOVE FOR MORE INFORMATION!** *\n\
\n\
---\n\
\n\
* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n\
\n\
[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\
\n\
### Checking for Settings-related Issues\n\
\n\
✔️ Achievements parameter is correctly configured in your Buffout 4 settings! \n\
\n\
-----\n\
✔️ ArchiveLimit parameter is correctly configured in your Buffout 4 settings! \n\
\n\
-----\n\
✔️ F4EE (Looks Menu) parameter is correctly configured in your Buffout 4 settings! \n\
\n\
-----\n\
### Checking For Mods That HAVE SOLUTIONS\n\
\n\
**[!] FOUND : [74] Looks Menu Customization Compendium**\n\
\n\
    - If you are getting broken hair colors, install this mod and make sure it loads after LMCC.  \n\
      Mod Link: https://www.nexusmods.com/fallout4/mods/18287?tab=files  \n\
    -----  \n\
### Checking for Important Mods\n\
\n\
\n\
✔️ Canary Save File Monitor is installed!\n\
\n\
\n\
✔️ High FPS Physics Fix is installed!\n\
\n\
### Checking for Plugin-related Errors\n\
\n\
* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\
\n\
### Checking for Named Records\n\
\n\
- (void* -> x-cell-og.dll+000BACC) | 2\n\
- (void* -> x-cell-og.dll+000BB7A) | 1\n\
\n\
---\n\
\n\
### End of Report\n\
\n\
Generated by CLASSIC v8.2.0";

        let blocks = parse_markdown(report);

        // Collect all heading texts
        let headings: Vec<&str> = blocks
            .iter()
            .filter(|b| b.block_type == BLOCK_HEADING)
            .map(|b| b.text.as_str())
            .collect();

        assert!(headings.iter().any(|h| h.contains("Error Information")),
            "Missing 'Error Information'. Headings found: {:?}", headings);
        assert!(headings.iter().any(|h| h.contains("Crash Messages")),
            "Missing 'Crash Messages'. Headings found: {:?}", headings);
        assert!(headings.iter().any(|h| h.contains("Settings-related")),
            "Missing 'Settings-related'. Headings found: {:?}", headings);
        assert!(headings.iter().any(|h| h.contains("HAVE SOLUTIONS")),
            "Missing 'HAVE SOLUTIONS'. Headings found: {:?}", headings);
        assert!(headings.iter().any(|h| h.contains("Important Mods")),
            "Missing 'Important Mods'. Headings found: {:?}", headings);
        assert!(headings.iter().any(|h| h.contains("Plugin-related Errors")),
            "Missing 'Plugin-related Errors'. Headings found: {:?}", headings);
        assert!(headings.iter().any(|h| h.contains("Named Records")),
            "Missing 'Named Records'. Headings found: {:?}", headings);
        assert!(headings.iter().any(|h| h.contains("End of Report")),
            "Missing 'End of Report'. Headings found: {:?}", headings);

        // Verify star-wrapped patterns are NOT parsed as list items.
        // Lines like "* SUSPECTS DETECTED! *" should be paragraphs, not list items.
        // The leading * is not a bullet marker -- it's decorative framing text.
        let star_pattern_blocks: Vec<&MarkdownBlock> = blocks
            .iter()
            .filter(|b| {
                b.text.contains("SUSPECTS DETECTED")
                    || b.text.contains("COULDN'T FIND ANY PLUGIN")
                    || b.text.contains("FCX MODE IS DISABLED")
            })
            .collect();

        for block in &star_pattern_blocks {
            assert_ne!(block.block_type, BLOCK_LIST_ITEM,
                "Star-wrapped text should NOT be a list item: {:?}", block.text);
            assert!(!block.text.ends_with(" *") && !block.text.ends_with("*"),
                "Star-wrapped text should NOT have trailing asterisk: {:?}", block.text);
        }

        // Verify indented "    -----" is treated as a thematic break, not code block
        let code_blocks: Vec<&MarkdownBlock> = blocks
            .iter()
            .filter(|b| b.block_type == BLOCK_CODE)
            .collect();
        for cb in &code_blocks {
            assert!(!cb.text.trim().starts_with("-----"),
                "Indented ----- should be a thematic break, not code: {:?}", cb.text);
        }
    }

    #[test]
    fn test_normalize_star_patterns() {
        // Star-framed text should be stripped of framing asterisks
        let input = "* **SUSPECTS DETECTED!** *\nSome text after";
        let normalized = normalize_report_content(input);
        assert!(!normalized.starts_with("* "),
            "Should strip leading asterisk framing: {:?}", normalized);
        assert!(normalized.contains("**SUSPECTS DETECTED!**"),
            "Should preserve inner bold content: {:?}", normalized);

        // Verify it doesn't break real list items
        let list_input = "* Item one\n* Item two";
        let list_normalized = normalize_report_content(list_input);
        assert!(list_normalized.contains("* Item one"),
            "Should NOT strip real list items: {:?}", list_normalized);
    }

    #[test]
    fn test_normalize_thematic_break_before_heading() {
        let input = "-----\n### My Heading";
        let normalized = normalize_report_content(input);
        assert!(normalized.contains("-----\n\n### My Heading"),
            "Should add blank line between thematic break and heading: {:?}", normalized);
    }

    #[test]
    fn test_normalize_indented_separator() {
        let input = "    -----";
        let normalized = normalize_report_content(input);
        assert_eq!(normalized.trim(), "-----",
            "Indented separator should be unindented: {:?}", normalized);
    }

    #[test]
    fn test_normalize_indented_separator_with_trailing_whitespace() {
        // Real report pattern: "    -----  " (4 spaces + 5 dashes + trailing spaces)
        let input = "    -----  ";
        let normalized = normalize_report_content(input);
        assert_eq!(normalized.trim(), "-----",
            "Indented separator with trailing whitespace should be unindented: {:?}", normalized);
    }

    #[test]
    fn test_normalize_preserves_regular_content() {
        // Regular markdown content should pass through unchanged
        let input = "# Title\n\nSome paragraph text\n\n- Item one\n- Item two\n\n---\n\n### Section";
        let normalized = normalize_report_content(input);
        assert!(normalized.contains("# Title"), "Should preserve headings");
        assert!(normalized.contains("Some paragraph text"), "Should preserve paragraphs");
        assert!(normalized.contains("- Item one"), "Should preserve list items");
    }

    #[test]
    fn test_normalize_three_dash_before_heading() {
        // Standard --- thematic break before heading should also get blank line
        let input = "---\n### My Heading";
        let normalized = normalize_report_content(input);
        assert!(normalized.contains("---\n\n### My Heading"),
            "Should add blank line between --- and heading: {:?}", normalized);
    }

    #[test]
    fn test_normalize_star_pattern_not_matching_list_with_sub_items() {
        // "* - subitem" should NOT be treated as star framing
        let input = "* - subitem here *";
        let normalized = normalize_report_content(input);
        assert!(normalized.contains("* - subitem here *"),
            "Should NOT strip list items with sub-items: {:?}", normalized);
    }
}
