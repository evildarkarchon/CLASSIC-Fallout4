//! Markdown-to-HTML bridge for CXX FFI.
//!
//! Converts CLASSIC crash report markdown into a complete HTML document
//! with inline dark-theme CSS, suitable for rendering in QTextBrowser.
//!
//! Includes normalization logic ported from the Slint GUI's `markdown.rs`
//! to handle CLASSIC report quirks that break standard CommonMark parsing.

use pulldown_cmark::{Options, Parser, html::push_html};

// ── Dark-theme CSS (PRD §2.8) ─────────────────────────────────────

/// Inline CSS for QTextBrowser dark-theme rendering.
///
/// Design constraints from PRD §2.8:
/// - Body: 13px, color #e0e0e0, background transparent
/// - H1: 22px bold, H2: 18px bold, H3: 15px bold (default text color, NO colored headers)
/// - pre/code: 12px Consolas, background #2a2a2e, border-radius 4px, padding 8px
/// - code (inline): same font, background #2a2a2e, border-radius 3px, padding 2px 4px
/// - hr: 1px solid #555555
/// - blockquote: border-left 3px solid #555555, italic, padding-left 8px
/// - ul/ol list items: standard bullets
/// - a (links): color #4da6ff (readable blue on dark)
/// - NO teal headers, NO colored boxes, NO orange inline code
const DARK_THEME_CSS: &str = r#"
body {
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
    color: #e0e0e0;
    background: transparent;
    margin: 4px;
    line-height: 1.5;
}
h1 {
    font-size: 22px;
    font-weight: bold;
    margin: 12px 0 8px 0;
}
h2 {
    font-size: 18px;
    font-weight: bold;
    margin: 10px 0 6px 0;
}
h3 {
    font-size: 15px;
    font-weight: bold;
    margin: 8px 0 4px 0;
}
h4, h5, h6 {
    font-size: 13px;
    font-weight: bold;
    margin: 6px 0 4px 0;
}
p {
    margin: 4px 0;
}
pre {
    font-family: Consolas, monospace;
    font-size: 12px;
    background-color: #2a2a2e;
    border-radius: 4px;
    padding: 8px;
    margin: 4px 0;
    white-space: pre-wrap;
    word-wrap: break-word;
}
code {
    font-family: Consolas, monospace;
    font-size: 12px;
    background-color: #2a2a2e;
    border-radius: 3px;
    padding: 2px 4px;
}
pre code {
    padding: 0;
    background: none;
    border-radius: 0;
}
hr {
    border: none;
    border-top: 1px solid #555555;
    margin: 8px 0;
}
blockquote {
    border-left: 3px solid #555555;
    padding-left: 8px;
    margin: 4px 0;
    font-style: italic;
}
ul, ol {
    margin: 4px 0;
    padding-left: 20px;
}
li {
    margin: 2px 0;
}
a {
    color: #4da6ff;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
"#;

// ── Normalization (ported from classic-gui/src/markdown.rs) ────────

/// Normalize CLASSIC report content for CommonMark-compliant parsing.
///
/// CLASSIC reports use patterns that break standard markdown parsers:
/// - `* text *` patterns where the leading `*` is parsed as a list bullet
///   instead of decorative framing text
/// - Indented `-----` (4+ spaces) that becomes a code block instead of a
///   thematic break separator
/// - `-----` (thematic breaks) immediately before headings with no blank line,
///   which can prevent heading recognition
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
        let is_thematic_break = trimmed == "---"
            || trimmed == "-----"
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

// ── Public bridge functions ────────────────────────────────────────

/// Normalize CLASSIC report markdown for CommonMark-compliant parsing.
///
/// Exposed via CXX so C++ can normalize markdown content before any
/// processing, if needed independently of `markdown_to_html`.
fn normalize_markdown(input: &str) -> String {
    normalize_report_content(input)
}

/// Convert markdown to a complete HTML document with inline dark-theme CSS.
///
/// The output is a self-contained HTML document suitable for
/// `QTextBrowser::setHtml()`. Includes:
/// - CLASSIC report normalization (star framing, indented breaks, etc.)
/// - CommonMark parsing via pulldown-cmark
/// - Complete `<html>` wrapper with inline `<style>` block
fn markdown_to_html(markdown: &str) -> String {
    let normalized = normalize_report_content(markdown);
    let parser = Parser::new_ext(&normalized, Options::empty());

    let mut html_body = String::new();
    push_html(&mut html_body, parser);

    let mut document = String::with_capacity(DARK_THEME_CSS.len() + html_body.len() + 128);
    document.push_str("<html><head><style>");
    document.push_str(DARK_THEME_CSS);
    document.push_str("</style></head><body>");
    document.push_str(&html_body);
    document.push_str("</body></html>");
    document
}

#[cxx::bridge(namespace = "classic::markdown")]
mod ffi {
    extern "Rust" {
        fn markdown_to_html(markdown: &str) -> String;
        fn normalize_markdown(input: &str) -> String;
    }
}

#[cfg(test)]
#[path = "markdown_tests.rs"]
mod tests;
