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
