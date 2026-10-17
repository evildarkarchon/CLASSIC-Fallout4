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

/// The oracle files recorded from the retired Python engine.
#[test]
fn the_real_packs_name_their_rust_sources_as_oracles() {
    let config = super::super::tests::PackRepo::real("config_vocabulary")
        .compile()
        .expect("config vocabulary compiles");
    assert_eq!(config.oracles, [CONFIG]);
    let scan = super::super::tests::PackRepo::real("scan_run_vocabulary")
        .compile()
        .expect("scan-run vocabulary compiles");
    assert_eq!(scan.oracles, [CONFIG, PUBLICATION, SCAN]);
    // The authored labels are the expectations, unchanged.
    assert_eq!(
        scan.expected[0]["entries"][0],
        json!({"token": "cache_unavailable", "label": "update cache unavailable", "rejected": false})
    );
}

/// Seeds one defect into a scenario's authored `entries`.
type EntriesSeed = fn(&mut Value);

#[test]
fn authored_labels_must_cover_every_token_and_reject_the_unknown_one() {
    let seeds: [(&str, EntriesSeed); 5] = [
        ("drops the unknown token", |entries| {
            entries.as_array_mut().unwrap().pop();
        }),
        ("blanks a label", |entries| entries[0]["label"] = json!("")),
        ("accepts the unknown token", |entries| {
            let last = entries.as_array().unwrap().len() - 1;
            entries[last]["rejected"] = json!(false);
        }),
        ("reorders tokens", |entries| {
            entries.as_array_mut().unwrap().swap(0, 1);
        }),
        ("adds a member", |entries| entries[0]["extra"] = json!(1)),
    ];
    for (seed, mutate) in seeds {
        let repo = super::super::tests::PackRepo::real("config_vocabulary")
            .edit(|pack| mutate(&mut pack["scenarios"][0]["expected"]["entries"]));
        let error = repo.compile().unwrap_err();
        assert!(
            error.contains("InstalledYamlDataProvenance oracle lacks complete labels"),
            "{seed}: {error}"
        );
    }
}
