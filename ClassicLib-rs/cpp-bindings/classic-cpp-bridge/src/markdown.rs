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
mod tests {
    use super::*;

    // ── normalize_report_content tests ──────────────────────────────

    #[test]
    fn test_normalize_star_patterns() {
        let input = "* **SUSPECTS DETECTED!** *\nSome text after";
        let normalized = normalize_report_content(input);
        assert!(
            !normalized.starts_with("* "),
            "Should strip leading asterisk framing: {normalized:?}"
        );
        assert!(
            normalized.contains("**SUSPECTS DETECTED!**"),
            "Should preserve inner bold content: {normalized:?}"
        );
    }

    #[test]
    fn test_normalize_preserves_real_list_items() {
        let input = "* Item one\n* Item two";
        let normalized = normalize_report_content(input);
        assert!(
            normalized.contains("* Item one"),
            "Should NOT strip real list items: {normalized:?}"
        );
    }

    #[test]
    fn test_normalize_indented_separator() {
        let input = "    -----";
        let normalized = normalize_report_content(input);
        assert_eq!(normalized.trim(), "-----");
    }

    #[test]
    fn test_normalize_indented_separator_trailing_whitespace() {
        let input = "    -----  ";
        let normalized = normalize_report_content(input);
        assert_eq!(normalized.trim(), "-----");
    }

    #[test]
    fn test_normalize_thematic_break_before_heading() {
        let input = "-----\n### My Heading";
        let normalized = normalize_report_content(input);
        assert!(
            normalized.contains("-----\n\n### My Heading"),
            "Should insert blank line: {normalized:?}"
        );
    }

    #[test]
    fn test_normalize_three_dash_before_heading() {
        let input = "---\n### My Heading";
        let normalized = normalize_report_content(input);
        assert!(
            normalized.contains("---\n\n### My Heading"),
            "Should insert blank line: {normalized:?}"
        );
    }

    #[test]
    fn test_normalize_star_sub_items_not_stripped() {
        let input = "* - subitem here *";
        let normalized = normalize_report_content(input);
        assert!(
            normalized.contains("* - subitem here *"),
            "Should NOT strip list items with sub-items: {normalized:?}"
        );
    }

    #[test]
    fn test_normalize_preserves_regular_content() {
        let input = "# Title\n\nSome paragraph text\n\n- Item one\n- Item two";
        let normalized = normalize_report_content(input);
        assert!(normalized.contains("# Title"));
        assert!(normalized.contains("Some paragraph text"));
        assert!(normalized.contains("- Item one"));
    }

    // ── normalize_markdown (CXX-exposed wrapper) ────────────────────

    #[test]
    fn test_normalize_markdown_delegates() {
        let input = "    -----";
        let result = normalize_markdown(input);
        assert_eq!(result.trim(), "-----");
    }

    // ── markdown_to_html tests ──────────────────────────────────────

    #[test]
    fn test_html_is_complete_document() {
        let html = markdown_to_html("Hello");
        assert!(html.starts_with("<html>"), "Should start with <html>");
        assert!(html.contains("<head>"), "Should contain <head>");
        assert!(html.contains("<style>"), "Should contain <style>");
        assert!(html.contains("</style>"), "Should close <style>");
        assert!(html.contains("<body>"), "Should contain <body>");
        assert!(html.contains("</body>"), "Should close <body>");
        assert!(html.ends_with("</html>"), "Should end with </html>");
    }

    #[test]
    fn test_html_contains_dark_theme_css() {
        let html = markdown_to_html("Test");
        assert!(html.contains("#e0e0e0"), "Should contain body text color");
        assert!(html.contains("#2a2a2e"), "Should contain code background");
        assert!(html.contains("#555555"), "Should contain hr/border color");
        assert!(html.contains("#4da6ff"), "Should contain link color");
        assert!(html.contains("Consolas"), "Should contain code font");
    }

    #[test]
    fn test_html_heading() {
        let html = markdown_to_html("# Big Heading");
        assert!(html.contains("<h1>Big Heading</h1>"));
    }

    #[test]
    fn test_html_paragraph() {
        let html = markdown_to_html("Just a paragraph.");
        assert!(html.contains("<p>Just a paragraph.</p>"));
    }

    #[test]
    fn test_html_bold() {
        let html = markdown_to_html("**Bold text**");
        assert!(html.contains("<strong>Bold text</strong>"));
    }

    #[test]
    fn test_html_italic() {
        let html = markdown_to_html("*Italic text*");
        assert!(html.contains("<em>Italic text</em>"));
    }

    #[test]
    fn test_html_code_block() {
        let html = markdown_to_html("```\nsome code\n```");
        assert!(html.contains("<pre><code>"));
        assert!(html.contains("some code"));
        assert!(html.contains("</code></pre>"));
    }

    #[test]
    fn test_html_inline_code() {
        let html = markdown_to_html("Use `my_func()` here");
        assert!(html.contains("<code>my_func()</code>"));
    }

    #[test]
    fn test_html_horizontal_rule() {
        let html = markdown_to_html("---");
        assert!(html.contains("<hr />"));
    }

    #[test]
    fn test_html_bullet_list() {
        let html = markdown_to_html("- Item A\n- Item B");
        assert!(html.contains("<ul>"));
        assert!(html.contains("<li>Item A</li>"));
        assert!(html.contains("<li>Item B</li>"));
        assert!(html.contains("</ul>"));
    }

    #[test]
    fn test_html_blockquote() {
        let html = markdown_to_html("> A quote");
        assert!(html.contains("<blockquote>"));
        assert!(html.contains("A quote"));
        assert!(html.contains("</blockquote>"));
    }

    #[test]
    fn test_html_link() {
        let html = markdown_to_html("[Nexus](https://nexusmods.com)");
        assert!(html.contains("<a href=\"https://nexusmods.com\">Nexus</a>"));
    }

    #[test]
    fn test_html_empty_input() {
        let html = markdown_to_html("");
        assert!(html.starts_with("<html>"));
        assert!(html.ends_with("</html>"));
        // Body should be empty (just CSS + wrapper)
        assert!(html.contains("<body></body>"));
    }

    #[test]
    fn test_html_normalization_applied() {
        // Star-framed text should NOT become a list item in the HTML output
        let html = markdown_to_html("* **SUSPECTS DETECTED!** *");
        assert!(
            !html.contains("<li>"),
            "Star-framed text should not produce list items: {html}"
        );
        assert!(
            html.contains("<strong>SUSPECTS DETECTED!</strong>"),
            "Inner bold content should be preserved: {html}"
        );
    }

    #[test]
    fn test_html_indented_separator_becomes_hr() {
        let html = markdown_to_html("    -----");
        assert!(
            html.contains("<hr />"),
            "Indented ----- should become <hr>: {html}"
        );
        assert!(
            !html.contains("<pre><code>-----"),
            "Indented ----- should NOT become code block: {html}"
        );
    }

    #[test]
    fn test_html_heading_after_thematic_break() {
        let html = markdown_to_html("-----\n### Section Title");
        assert!(
            html.contains("<h3>Section Title</h3>"),
            "Heading after thematic break should be recognized: {html}"
        );
    }

    #[test]
    fn test_html_full_report_structure() {
        // Minimal CLASSIC-style report covering all element types
        let report = "\
# crash-2025-test-AUTOSCAN.md
**AUTOSCAN REPORT GENERATED BY CLASSIC v9.0.0**

> **FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR**

---

### Error Information

**Main Error:** Unhandled exception at 0x7FF68919FECE

-----
* **ONE OR MORE SUSPECTS DETECTED!** *

### Checking for Mods

- **[!] FOUND : [74] Looks Menu**

    - Install this mod to fix the issue.
      Mod Link: https://www.nexusmods.com/fallout4/mods/18287
    -----
### Important Mods

* COULDN'T FIND ANY PLUGIN SUSPECTS *

### End of Report

Generated by CLASSIC v9.0.0";

        let html = markdown_to_html(report);

        // All headings rendered
        assert!(html.contains("<h1>"));
        assert!(html.contains("<h3>Error Information</h3>"));
        assert!(html.contains("<h3>Checking for Mods</h3>"));
        assert!(html.contains("<h3>Important Mods</h3>"));
        assert!(html.contains("<h3>End of Report</h3>"));

        // Structural elements
        assert!(html.contains("<hr />"), "Should have horizontal rules");
        assert!(html.contains("<blockquote>"), "Should have blockquote");
        assert!(html.contains("<strong>"), "Should have bold text");
        assert!(html.contains("<ul>"), "Should have list");

        // Star-framed patterns normalized
        assert!(
            html.contains("SUSPECTS DETECTED!"),
            "Suspects text should be present"
        );
    }
}
