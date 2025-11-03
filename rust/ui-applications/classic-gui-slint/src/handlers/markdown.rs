// Markdown loading and rendering handler
//
// This module handles loading markdown files and converting them to
// formatted text for display in the Slint UI with Fluent Design styling.

use anyhow::{Context, Result};
use pulldown_cmark::{Event, Options, Parser, Tag, TagEnd};
use std::fs;
use std::path::Path;

/// Markdown content with metadata for display
#[derive(Debug, Clone)]
pub struct MarkdownContent {
    /// Formatted markdown text for display
    pub text: String,

    /// Original markdown source (for clipboard copy)
    #[allow(dead_code)]
    pub source: String,

    /// File metadata
    pub filename: String,
    pub file_size: String,
    pub display_date: String,
}

/// Load and parse a markdown file
///
/// Reads the markdown file, parses it with pulldown-cmark, and converts it
/// to formatted text suitable for display in Slint with proper styling.
///
/// # Arguments
/// * `path` - Path to the markdown file
///
/// # Returns
/// * `Ok(MarkdownContent)` - Successfully loaded and parsed markdown
/// * `Err(anyhow::Error)` - Failed to load or parse markdown
pub fn load_markdown(path: &Path) -> Result<MarkdownContent> {
    tracing::info!("Loading markdown: {}", path.display());

    // Read file with UTF-8 encoding
    let source = fs::read_to_string(path)
        .with_context(|| format!("Failed to read markdown file: {}", path.display()))?;

    // Get file metadata
    let metadata = path
        .metadata()
        .with_context(|| format!("Failed to read file metadata: {}", path.display()))?;

    let filename = path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("Unknown")
        .to_string();

    let file_size = format_file_size(metadata.len());
    let display_date = format_system_time(metadata.modified()?);

    // Parse markdown and convert to formatted text
    let text = parse_markdown_to_text(&source)?;

    tracing::debug!(
        "Loaded markdown: {} bytes, {} characters formatted",
        metadata.len(),
        text.len()
    );

    Ok(MarkdownContent {
        text,
        source,
        filename,
        file_size,
        display_date,
    })
}

/// Parse markdown source and convert to formatted plain text
///
/// Converts markdown elements to plain text with basic formatting:
/// - Headings get proper spacing and size markers
/// - Code blocks get monospace markers
/// - Lists get proper indentation
/// - Links show URL in parentheses
///
/// This is a simplified renderer for Slint's Text component.
/// For full rich text rendering, we'd need to use Slint's custom rendering.
fn parse_markdown_to_text(source: &str) -> Result<String> {
    let mut options = Options::empty();
    options.insert(Options::ENABLE_TABLES);
    options.insert(Options::ENABLE_FOOTNOTES);
    options.insert(Options::ENABLE_STRIKETHROUGH);
    options.insert(Options::ENABLE_TASKLISTS);

    let parser = Parser::new_ext(source, options);
    let mut output = String::new();
    let mut in_code_block = false;
    let mut in_heading = false;
    let mut heading_level = 0;
    let mut list_depth: usize = 0;

    for event in parser {
        match event {
            Event::Start(tag) => match tag {
                Tag::Heading { level, .. } => {
                    in_heading = true;
                    heading_level = level as usize;
                    output.push('\n');
                }
                Tag::CodeBlock(_) => {
                    in_code_block = true;
                    output.push_str("\n━━━ CODE ━━━\n");
                }
                Tag::List(_) => {
                    list_depth += 1;
                    output.push('\n');
                }
                Tag::Item => {
                    output.push_str(&"  ".repeat(list_depth.saturating_sub(1)));
                    output.push_str("• ");
                }
                Tag::Paragraph => {
                    if !output.ends_with('\n') {
                        output.push('\n');
                    }
                }
                Tag::BlockQuote(_) => {
                    output.push_str("\n┃ ");
                }
                _ => {}
            },
            Event::End(tag_end) => match tag_end {
                TagEnd::Heading(_) => {
                    if in_heading {
                        in_heading = false;
                        output.push_str(&"\n".repeat(if heading_level <= 2 { 2 } else { 1 }));
                    }
                }
                TagEnd::CodeBlock => {
                    in_code_block = false;
                    output.push_str("━━━━━━━━━━━━\n");
                }
                TagEnd::List(_) => {
                    list_depth = list_depth.saturating_sub(1);
                    output.push('\n');
                }
                TagEnd::Paragraph => {
                    output.push('\n');
                }
                _ => {}
            },
            Event::Text(text) => {
                if in_code_block {
                    // Code blocks: preserve formatting
                    output.push_str(&text);
                } else if in_heading {
                    // Headings: uppercase for emphasis
                    output.push_str(&text.to_uppercase());
                } else {
                    // Normal text
                    output.push_str(&text);
                }
            }
            Event::Code(code) => {
                output.push('`');
                output.push_str(&code);
                output.push('`');
            }
            Event::SoftBreak => {
                output.push(' ');
            }
            Event::HardBreak => {
                output.push('\n');
            }
            Event::Rule => {
                output.push_str("\n─────────────────────────────────────────\n\n");
            }
            _ => {}
        }
    }

    // Clean up excessive newlines
    let cleaned = output
        .lines()
        .map(|line| line.trim_end())
        .collect::<Vec<_>>()
        .join("\n")
        .trim()
        .to_string();

    Ok(cleaned)
}

/// Format a file size for display
///
/// Converts bytes to a human-readable string with appropriate units (B, KB, MB, GB)
fn format_file_size(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;

    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} B", bytes)
    }
}

/// Format a SystemTime for display
///
/// Converts a SystemTime to a human-readable string like "2025-10-11 14:30"
fn format_system_time(time: std::time::SystemTime) -> String {
    use std::time::UNIX_EPOCH;

    match time.duration_since(UNIX_EPOCH) {
        Ok(duration) => {
            let secs = duration.as_secs();
            let datetime = chrono::DateTime::from_timestamp(secs as i64, 0);

            match datetime {
                Some(dt) => dt.format("%Y-%m-%d %H:%M").to_string(),
                None => "Unknown".to_string(),
            }
        }
        Err(_) => "Unknown".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple_markdown() {
        let markdown = "# Heading\n\nSome text with **bold** and *italic*.";
        let result = parse_markdown_to_text(markdown).unwrap();

        assert!(result.contains("HEADING"));
        assert!(result.contains("Some text"));
    }

    #[test]
    fn test_parse_code_block() {
        let markdown = "```rust\nfn main() {\n    println!(\"Hello\");\n}\n```";
        let result = parse_markdown_to_text(markdown).unwrap();

        assert!(result.contains("CODE"));
        assert!(result.contains("fn main()"));
    }

    #[test]
    fn test_parse_list() {
        let markdown = "- Item 1\n- Item 2\n  - Nested item";
        let result = parse_markdown_to_text(markdown).unwrap();

        assert!(result.contains("•"));
        assert!(result.contains("Item 1"));
    }

    #[test]
    fn test_format_file_size() {
        assert_eq!(format_file_size(500), "500 B");
        assert_eq!(format_file_size(1024), "1.00 KB");
        assert_eq!(format_file_size(1536), "1.50 KB");
        assert_eq!(format_file_size(1048576), "1.00 MB");
        assert_eq!(format_file_size(1073741824), "1.00 GB");
    }
}
