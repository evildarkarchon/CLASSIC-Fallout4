use super::*;

#[test]
fn entry_line_finds_the_name_line_of_a_ranges_entry_in_any_quoting() {
    let text = "files:\n  - name: \"A.yaml\"\n    min_client_schema: \"1.0\"\n  - name: 'B.yaml'\n  - name: C.yaml\n";

    assert_eq!(entry_line(text, "A.yaml"), 2);
    assert_eq!(entry_line(text, "B.yaml"), 4);
    assert_eq!(entry_line(text, "C.yaml"), 5);
    assert_eq!(entry_line(text, "missing.yaml"), 1);
}
