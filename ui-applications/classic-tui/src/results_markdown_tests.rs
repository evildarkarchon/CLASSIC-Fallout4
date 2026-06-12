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
fn captures_exact_link_columns_after_plain_prefix() {
    let rendered = render_markdown("See [CLASSIC](https://example.com) docs");
    let link = &rendered.links[0];

    assert_eq!(link.line_index, 0);
    assert_eq!(link.start_col, 4);
    assert_eq!(link.end_col, 11);
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
