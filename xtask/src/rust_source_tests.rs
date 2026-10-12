use super::*;

#[test]
fn find_enum_searches_inline_modules_and_skips_other_items() {
    let file = parse_file(
        "x.rs",
        "struct Event;\nmod outer {\n    mod inner {\n        pub enum Event { A, B }\n    }\n}\n",
    )
    .unwrap();

    let found = find_enum(&file, "Event").expect("nested enum");

    assert_eq!(found.ident.span().start().line, 4);
    assert_eq!(found.variants.len(), 2);
    assert!(find_enum(&file, "Missing").is_none());
}

#[test]
fn parse_errors_name_the_path_and_line() {
    let Err(error) = parse_file("src/bad.rs", "fn ok() {}\nfn broken( {}\n") else {
        panic!("broken source parsed");
    };
    assert!(
        error
            .to_string()
            .starts_with("src/bad.rs:2: cannot parse Rust source: "),
        "{error}"
    );
}
