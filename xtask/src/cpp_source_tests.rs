use super::*;

#[test]
fn blanking_keeps_code_and_line_structure() {
    let source =
        "int a = 1; // classic::m::f()\n/* classic::m::g()\n */ call(\"classic::m::h\", 'x');\n";
    let blanked = blank_comments_and_strings(source);
    assert_eq!(blanked.lines().count(), source.lines().count());
    assert_eq!(blanked.len(), source.len());
    assert!(blanked.starts_with("int a = 1;"));
    assert!(blanked.contains("call("));
    assert!(!blanked.contains("classic"));
    assert!(!blanked.contains('x'));
}

#[test]
fn blanking_handles_raw_strings_with_delimiters_and_prefixes() {
    let source =
        "auto s = R\"x(classic::m::f)\" still raw)x\"; auto t = u8R\"(classic::m::g)\"; keep();\n";
    let blanked = blank_comments_and_strings(source);
    assert!(!blanked.contains("classic"));
    assert!(!blanked.contains("raw"));
    assert!(blanked.contains("keep();"));
}

#[test]
fn digit_separators_are_not_character_literals() {
    // Were `'` in 1'000 read as a character literal, it would swallow the call.
    let blanked = blank_comments_and_strings("int n = 1'000'000; classic::m::f();\n");
    assert!(blanked.contains("classic::m::f()"));
}

#[test]
fn line_comment_continues_across_a_trailing_backslash() {
    let blanked = blank_comments_and_strings("// note \\\nclassic::m::f();\nclassic::m::g();\n");
    assert!(!blanked.contains("classic::m::f"));
    assert!(blanked.contains("classic::m::g"));
    assert_eq!(blanked.lines().count(), 3);
}

#[test]
fn escaped_quotes_do_not_end_a_string_early() {
    let blanked =
        blank_comments_and_strings("log(\"say \\\"classic::m::f\\\" now\"); classic::m::g();\n");
    assert!(!blanked.contains("classic::m::f"));
    assert!(blanked.contains("classic::m::g"));
}

#[test]
fn comments_only_mode_keeps_literals_and_line_structure() {
    let source = "auto k = \"CLASSIC_Settings\"; // CLASSIC_Settings\r\n/* x\r\n */ auto u = \"https://e/*x\"; f('/');\r\n";
    let blanked = blank_comments(source);
    assert_eq!(blanked.len(), source.len());
    assert_eq!(blanked.lines().count(), source.lines().count());
    assert_eq!(blanked.matches("CLASSIC_Settings").count(), 1);
    assert!(blanked.contains("auto u = \"https://e/*x\"; f('/');"));
    assert!(blanked.lines().nth(1).unwrap().trim().is_empty());
}

#[test]
fn comments_only_mode_keeps_raw_strings() {
    let source = "auto s = R\"x(a // b)x\"; // gone\n";
    assert_eq!(
        blank_comments(source).trim_end(),
        "auto s = R\"x(a // b)x\";"
    );
}
