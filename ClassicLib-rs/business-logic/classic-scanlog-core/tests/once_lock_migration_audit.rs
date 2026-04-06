//! Contract audit for the Phase 7 RecordScanner dependency exit.

const RECORD_SCANNER_RS: &str = include_str!("../src/record_scanner.rs");
const CARGO_TOML: &str = include_str!("../Cargo.toml");
const API_DOC: &str = include_str!("../../../../docs/api/classic-scanlog-core.md");

#[test]
fn record_scanner_and_docs_exit_direct_once_cell_usage() {
    assert!(
        RECORD_SCANNER_RS.contains("OnceLock"),
        "record_scanner.rs should migrate its per-instance caches to std::sync::OnceLock"
    );
    assert!(
        RECORD_SCANNER_RS.contains("get_or_init"),
        "record_scanner.rs should preserve lazy per-instance matcher construction"
    );
    assert!(
        !RECORD_SCANNER_RS.contains("once_cell::sync::OnceCell"),
        "record_scanner.rs should no longer import once_cell::sync::OnceCell"
    );
    assert!(
        !CARGO_TOML.contains("once_cell"),
        "classic-scanlog-core/Cargo.toml should drop the direct once_cell dependency"
    );
    assert!(
        API_DOC.contains("OnceLock"),
        "classic-scanlog-core API guide should describe the std OnceLock cache behavior"
    );
    assert!(
        !API_DOC.contains("once_cell"),
        "classic-scanlog-core API guide should stop describing once_cell internals"
    );
}
