use super::*;

const SOURCE_ENUM: &str = r#"
pub enum Stage { Read, Write }
impl Vocabulary for Stage {
    fn as_str(self) -> &'static str { match self { Self::Read => "read", Self::Write => "write" } }
}
"#;

const TWIN: &str = r#"
const RECOVERY_REQUIRED_TOKEN: &str = "recovery_required";
pub enum RunStage { Read, Write, Recovery }
impl Vocabulary for RunStage {
    fn as_str(self) -> &'static str {
        match stage_to_source(self) {
            Some(source) => source.as_str(),
            None => RECOVERY_REQUIRED_TOKEN,
        }
    }
}
"#;

fn root_with(files: &[(&str, &str)]) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("temp dir");
    for (path, text) in files {
        let full = dir.path().join(path);
        std::fs::create_dir_all(full.parent().unwrap()).unwrap();
        std::fs::write(full, text).unwrap();
    }
    dir
}

#[test]
fn a_delegating_twin_reuses_source_tokens_and_takes_the_none_fallback() {
    let dir = root_with(&[("a.rs", SOURCE_ENUM), ("b.rs", TWIN)]);
    let root = RepoRoot::new(dir.path());
    let operation = twin("run_stage_label", "RunStage", "b.rs", ("a.rs", "Stage"));
    let tokens = Sources::new(&root)
        .tokens(&operation)
        .expect("tokens resolve");
    assert_eq!(tokens, ["read", "write", "recovery_required"]);
}

#[test]
fn tokens_must_cover_every_variant_once() {
    let duplicate = SOURCE_ENUM.replace("\"write\"", "\"read\"");
    let dir = root_with(&[("a.rs", &duplicate)]);
    let root = RepoRoot::new(dir.path());
    let error = Sources::new(&root)
        .tokens(&op("stage_label", "Stage", "a.rs"))
        .unwrap_err();
    assert!(
        error.contains("lack complete, unique source tokens"),
        "{error}"
    );

    let private = SOURCE_ENUM.replace("pub enum", "enum");
    let dir = root_with(&[("a.rs", &private)]);
    let root = RepoRoot::new(dir.path());
    let error = Sources::new(&root)
        .tokens(&op("stage_label", "Stage", "a.rs"))
        .unwrap_err();
    assert!(error.contains("no `pub enum Stage`"), "{error}");
}
