//! Rendering helpers: Python `repr` of loaded YAML values and key line lookup.

use super::*;

fn repr_of(yaml: &str) -> String {
    let document = &YamlLoader::load_from_str(yaml).expect("parses")[0];
    py_repr(&document["a"])
}

#[test]
fn values_render_like_python_repr() {
    // Expected strings are what `repr()` printed for ruamel's load of the
    // same YAML under Python 3.14.
    let cases = [
        ("a: 'x'", "'x'"),
        ("a: \"it's\"", "\"it's\""),
        ("a: \"both ' and \\\"\"", "'both \\' and \"'"),
        (
            "a: \"tab\\there\\nnl \\\\ \\u0001 \\u00e9 \\u2028\"",
            "'tab\\there\\nnl \\\\ \\x01 é \\u2028'",
        ),
        ("a: ~", "None"),
        ("a: True", "True"),
        ("a: 9", "9"),
        ("a: 1.10", "1.1"),
        ("a: 1e3", "1000.0"),
        ("a: -1.5", "-1.5"),
        ("a: 1.0e+16", "1e+16"),
        ("a: 0.00001", "1e-05"),
        ("a: 0.0001", "0.0001"),
        ("a: 123456789012345.6", "123456789012345.6"),
        ("a: .inf", "inf"),
        ("a: [1, 'x']", "[1, 'x']"),
        ("a: {b: 1}", "{'b': 1}"),
    ];
    for (yaml, expected) in cases {
        assert_eq!(repr_of(yaml), expected, "{yaml}");
    }
}

#[test]
fn key_lines_are_found_at_top_level_and_under_display() {
    let text = "# comment\nmanifest_version: \"1.0\"\n\"release_tag\": x\ndisplay:\n  title: t\n\n  body: b\nother: 1\n  cta_url: not-display\n";
    assert_eq!(top_level_line(text, "manifest_version"), Some(2));
    assert_eq!(top_level_line(text, "release_tag"), Some(3));
    assert_eq!(top_level_line(text, "title"), None);
    assert_eq!(display_line(text, "title"), 5);
    assert_eq!(display_line(text, "body"), 7);
    // Past the end of the display block: falls back to `display:`.
    assert_eq!(display_line(text, "cta_url"), 4);
}
