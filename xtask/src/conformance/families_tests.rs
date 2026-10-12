//! Each family input hook, driven through `validate_inputs`: a clean case
//! passes and each seeded violation is reported.

use std::collections::BTreeMap;

use serde_json::{Value, json};

use super::*;

/// One scenario: action, input (`None` = the sole fixture reference), the
/// sole fixture's JSON (if any) and the expected observation.
struct Case {
    action: &'static str,
    input: Option<Value>,
    fixture: Option<Value>,
    expected: Value,
}

fn case(action: &'static str, fixture: Value) -> Case {
    Case {
        action,
        input: None,
        fixture: Some(fixture),
        expected: json!({}),
    }
}

fn rich(action: &'static str, input: Value) -> Case {
    Case {
        action,
        input: Some(input),
        fixture: None,
        expected: json!({}),
    }
}

/// Runs `family`'s hook over `cases` in a repository at `root`; returns the
/// issue messages.
fn hook_at(root: &RepoRoot, family: &str, cases: Vec<Case>) -> Vec<String> {
    let mut fixtures = BTreeMap::new();
    let mut scenarios = Vec::new();
    for (index, case) in cases.into_iter().enumerate() {
        let reference = format!("f{index}");
        let (input, refs) = match case.input {
            Some(input) => (input, json!([])),
            None => (json!({"fixtureRef": reference}), json!([reference])),
        };
        if let Some(fixture) = case.fixture {
            fixtures.insert(
                reference.clone(),
                Fixture {
                    json: Some(fixture),
                },
            );
        }
        scenarios.push(json!({
            "id": format!("s{index}"),
            "action": case.action,
            "capabilityIds": [case.action],
            "fixtureRefs": refs,
            "input": input,
            "expected": case.expected,
            "normalization": {"rootRelativePaths": false, "unorderedPaths": [], "excludedPaths": []}
        }));
    }
    let pack: Pack = serde_json::from_value(json!({
        "schemaVersion": 1,
        "familyId": family,
        "familyVersion": 1,
        "domainOwner": {"rustCrate": "classic-demo-core"},
        "fixtureRoot": "fixtures",
        "fixtures": {},
        "capabilities": [],
        "scenarios": scenarios,
        "consumerObligations": []
    }))
    .expect("test pack deserializes");
    validate_inputs(&InputContext {
        root,
        pack: &pack,
        fixtures: &fixtures,
    })
    .into_iter()
    .map(|issue| {
        assert_eq!(issue.rule, RULE);
        issue.message
    })
    .collect()
}

fn hook(family: &str, cases: Vec<Case>) -> Vec<String> {
    hook_at(&RepoRoot::new("."), family, cases)
}

#[track_caller]
fn assert_reports(messages: &[String], text: &str) {
    assert!(
        messages.iter().any(|message| message.contains(text)),
        "expected {text:?} in {messages:#?}"
    );
}

#[test]
fn update_services_scripts_stay_local_and_bounded() {
    let script = json!({
        "installedVersion": "8.0.0", "timeoutMs": 1000, "checks": 1,
        "service": {
            "pages": [{"status": 200, "body": "<html/>", "headers": {"ETag": "\"a\""}}],
            "api": [{"status": 200, "body": "[]", "headers": {}}, {"stall": true}]
        }
    });
    let run = |fixture: Value| {
        hook(
            "update-services",
            vec![case("update-services.notification", fixture)],
        )
    };
    assert!(run(script.clone()).is_empty());

    let mut redirect = script.clone();
    redirect["service"]["pages"][0]["headers"] = json!({"Location": "https://example.com"});
    assert_reports(&run(redirect), "cannot redirect or inject headers");
    let mut remote = script.clone();
    remote["service"]["api"][0]["body"] = json!("[{\"assets\": []}]");
    assert_reports(&run(remote), "remote asset URLs are forbidden");
    let mut route = script.clone();
    route["service"]["upload"] = json!([]);
    assert_reports(&run(route), "only the local pages and api routes");
    let mut unbounded = script;
    unbounded["timeoutMs"] = json!(60000);
    assert_reports(&run(unbounded), "must be bounded");
}

#[test]
fn families_without_a_hook_add_no_checks() {
    assert_eq!(input_shape("performance"), InputShape::FixtureRefOnly);
    assert_eq!(input_shape("user-settings"), InputShape::Rich);
    assert!(hook("performance", vec![case("anything", json!({"x": 1}))]).is_empty());
}

#[test]
fn aux_operations_accept_only_exact_requests() {
    let web = json!({"request": {"url": "u", "path": "p", "params": [["a", "b"]], "suffix": "s"}});
    let routes = json!({"request": {"operation": "game-routes", "game": "Fallout4"}});
    assert!(
        hook(
            "web-operations",
            vec![
                case("web-operations.observe", web.clone()),
                case("web-operations.routes", routes)
            ]
        )
        .is_empty()
    );

    assert_reports(
        &hook(
            "web-operations",
            vec![case("web-operations.parse", web.clone())],
        ),
        "not an auxiliary operation action",
    );
    let mut extra = web.clone();
    extra["expected"] = json!("x");
    assert_reports(
        &hook(
            "web-operations",
            vec![case("web-operations.observe", extra)],
        ),
        "must contain only",
    );
    let mut bad_params = web;
    bad_params["request"]["params"] = json!([["a"]]);
    assert_reports(
        &hook(
            "web-operations",
            vec![case("web-operations.observe", bad_params)],
        ),
        "ordered string pairs",
    );
    assert_reports(
        &hook(
            "web-operations",
            vec![case(
                "web-operations.routes",
                json!({"request": {"operation": "game-routes", "game": "Skyrim"}}),
            )],
        ),
        "web routing fixture",
    );

    let types = json!([
        "texture",
        "mesh",
        "script",
        "plugin",
        "sound",
        "animation",
        "interface",
        "strings",
        "archive",
        "config",
        "other"
    ]);
    let resource = json!({"request": {"path": "a/b.dds", "type": "texture", "validate": ["a/b.dds"], "types": types}, "files": {"a/b.dds": ""}});
    assert!(
        hook(
            "resource-operations",
            vec![case("resource-operations.observe", resource.clone())]
        )
        .is_empty()
    );
    let mut escaping = resource;
    escaping["request"]["validate"] = json!(["../outside"]);
    assert_reports(
        &hook(
            "resource-operations",
            vec![case("resource-operations.observe", escaping)],
        ),
        "inside the fixture workspace",
    );

    let pe = json!({"request": {"operation": "pe-extract", "path": "game/x.exe"}, "files": {"game/x.exe": "4d5a"}});
    assert!(hook("version-pe", vec![case("version-pe.observe", pe.clone())]).is_empty());
    let mut not_hex = pe;
    not_hex["files"]["game/x.exe"] = json!("4D5");
    assert_reports(
        &hook("version-pe", vec![case("version-pe.observe", not_hex)]),
        "lowercase hex",
    );
    assert_reports(
        &hook(
            "version-f4se",
            vec![case(
                "version-f4se.observe",
                json!({"request": {"version": "1"}}),
            )],
        ),
        "must name an extended version operation",
    );
}

/// The controlled registry YAML the xse-folder hook pins by digest is not
/// reproduced here; this stand-in must be rejected for it.
fn xse_fixture(registry: &str) -> Value {
    json!({"registryYaml": registry, "game": "Fallout4", "selectedVersion": "OG", "localYaml": null, "configuredDocs": "configured-docs"})
}

#[test]
fn xse_folder_requires_controlled_inputs() {
    let messages = hook(
        "xse-folder",
        vec![case(
            "xse-folder.resolve",
            xse_fixture("Version_Registry: {}\n"),
        )],
    );
    assert_reports(&messages, "controlled registry metadata");
    assert_reports(
        &messages,
        "expected inventory must preserve the fixture bytes",
    );

    let mut host = xse_fixture("x");
    host["game"] = json!("Skyrim");
    assert_reports(
        &hook("xse-folder", vec![case("xse-folder.resolve", host)]),
        "could consult host discovery",
    );

    let mut derive = xse_fixture("x");
    derive.as_object_mut().unwrap().remove("localYaml");
    derive["gameLocalFacts"] = json!({"docsFolderXse": "C:/host", "rootFolderDocs": null});
    assert_reports(
        &hook("xse-folder", vec![case("xse-folder.derive", derive)]),
        "controlled Game Local facts",
    );

    let mut log = xse_fixture("x");
    log["logFiles"] = json!(["somewhere/else.log"]);
    assert_reports(
        &hook("xse-folder", vec![case("xse-folder.log", log)]),
        "controlled, distinct log files",
    );

    assert_reports(
        &hook(
            "xse-folder",
            vec![
                case("xse-folder.resolve", xse_fixture("a")),
                case("xse-folder.resolve", xse_fixture("b")),
            ],
        ),
        "identical registry bytes",
    );
}

#[test]
fn installation_paths_locate_stays_in_the_owned_tree() {
    let locate = |placements: Value| json!({"operation": "locate", "executableDir": "tree/build/bin", "workingDir": "tree/work", "classicDataIn": placements});
    let directories = json!([
        "tree",
        "tree/build",
        "tree/build/bin",
        "tree/work",
        "tree/work/CLASSIC Data"
    ]);
    let mut good = case("installation-paths.locate", locate(json!(["tree/work"])));
    good.expected = json!({"directories": directories});
    assert!(hook("installation-paths", vec![good]).is_empty());

    let mut wrong_tree = case("installation-paths.locate", locate(json!(["tree/work"])));
    wrong_tree.expected = json!({"directories": ["tree"]});
    assert_reports(
        &hook("installation-paths", vec![wrong_tree]),
        "exactly the tree the locate inputs create",
    );

    assert_reports(
        &hook(
            "installation-paths",
            vec![case(
                "installation-paths.locate",
                locate(json!(["C:/Users"])),
            )],
        ),
        "only be placed, once each, in a locator candidate",
    );
    let mut outside = locate(json!([]));
    outside["executableDir"] = json!("C:/Program Files");
    assert_reports(
        &hook(
            "installation-paths",
            vec![case("installation-paths.locate", outside)],
        ),
        "inside the owned tree",
    );

    let inspect = json!({"gamePath": "game", "docsPath": "docs", "registryYaml": "x", "files": {"game/Fallout4.exe": "owned executable marker"}});
    assert_reports(
        &hook(
            "installation-paths",
            vec![case("installation-paths.inspect", inspect)],
        ),
        "controlled registry metadata",
    );
    assert_reports(
        &hook(
            "installation-paths",
            vec![case(
                "installation-paths.inspect",
                json!({"gamePath": "C:/Games", "docsPath": "docs", "registryYaml": "x", "files": {}}),
            )],
        ),
        "owned cache directories",
    );
}

#[test]
fn settings_load_candidates_have_exact_shapes() {
    let load =
        json!({"files": {"a.yaml": "x: 1"}, "request": {"single": "a.yaml", "batch": ["a.yaml"]}});
    assert!(
        hook(
            "settings-load",
            vec![case("settings-load.execute", load.clone())]
        )
        .is_empty()
    );
    let mut escaping = load;
    escaping["request"]["single"] = json!("../a.yaml");
    assert_reports(
        &hook(
            "settings-load",
            vec![case("settings-load.execute", escaping)],
        ),
        "contained single path",
    );

    let yaml = json!({"kind": "yaml", "content": "", "updates": {"name": "n", "ready": true, "size": 1, "values": ["v"]}, "updateOrder": ["name", "ready", "size", "values"]});
    assert!(
        hook(
            "settings-yaml",
            vec![case("settings-yaml.execute", yaml.clone())]
        )
        .is_empty()
    );
    let mut reordered = yaml.clone();
    reordered["updateOrder"] = json!(["size", "name", "ready", "values"]);
    assert_reports(
        &hook(
            "settings-yaml",
            vec![case("settings-yaml.execute", reordered)],
        ),
        "explicit common order",
    );
    let mut untyped = yaml;
    untyped["updates"]["ready"] = json!("yes");
    assert_reports(
        &hook(
            "settings-yaml",
            vec![case("settings-yaml.execute", untyped)],
        ),
        "ready (bool)",
    );
    assert_reports(
        &hook(
            "settings-yaml",
            vec![case("settings-load.execute", json!({}))],
        ),
        "must use the settings-yaml.execute action",
    );

    let batch = json!({"kind": "yaml-batch", "content": "", "keys": ["k"], "updates": {"k": "v"}});
    assert!(
        hook(
            "settings-yaml-batch",
            vec![case("settings-yaml-batch.execute", batch.clone())]
        )
        .is_empty()
    );
    let mut numeric = batch;
    numeric["updates"]["k"] = json!(1);
    assert_reports(
        &hook(
            "settings-yaml-batch",
            vec![case("settings-yaml-batch.execute", numeric)],
        ),
        "updates: {string: string}",
    );
}

#[test]
fn user_settings_inputs_follow_their_action() {
    let staged = json!([{"fixtureRef": "doc", "path": "CLASSIC Settings.yaml"}]);
    let open =
        json!({"installationData": staged, "observationFields": ["game_version", "update_check"]});
    let update = json!({
        "installationData": staged, "installationRootExists": true, "previewMode": "update",
        "requestedUpdate": {"/CLASSIC_Settings/Update Check": false}, "commit": true, "externalEdit": null
    });
    let migrate = json!({
        "installationData": staged, "apply": true, "restore": false,
        "beforeApply": {"kind": "external-edit", "fixtureRef": "doc", "path": "CLASSIC Data/CLASSIC Settings.yaml"},
        "beforeRestore": {"kind": "remove-backup"}
    });
    assert!(
        hook(
            "user-settings",
            vec![
                rich("user-settings.open", open.clone()),
                rich("user-settings.update", update.clone()),
                rich("user-settings.migrate", migrate.clone()),
                rich("user-settings.defaults", json!({})),
            ]
        )
        .is_empty()
    );

    let mut unsorted = open;
    unsorted["observationFields"] = json!(["update_check", "game_version"]);
    assert_reports(
        &hook("user-settings", vec![rich("user-settings.open", unsorted)]),
        "sorted, unique",
    );
    let mut preview = update.clone();
    preview["previewMode"] = json!("dry-run");
    assert_reports(
        &hook("user-settings", vec![rich("user-settings.update", preview)]),
        "previewMode",
    );
    let mut leaked = update;
    leaked["expectedView"] = json!({});
    assert_reports(
        &hook("user-settings", vec![rich("user-settings.update", leaked)]),
        "must contain exactly",
    );
    let mut control = migrate;
    control["beforeApply"] =
        json!({"kind": "external-edit", "fixtureRef": "doc", "path": "../elsewhere.yaml"});
    assert_reports(
        &hook(
            "user-settings",
            vec![rich("user-settings.migrate", control)],
        ),
        "supported settings location",
    );
    assert_reports(
        &hook(
            "user-settings",
            vec![rich("user-settings.reset", json!({}))],
        ),
        "unsupported User Settings action",
    );
    assert_reports(
        &hook(
            "user-settings",
            vec![rich(
                "user-settings.legacy-import",
                json!({"installationData": staged}),
            )],
        ),
        "stages exactly CLASSIC Settings.yaml and state.json",
    );
}

#[test]
fn scan_run_and_launch_inputs_are_closed_requests() {
    let run = json!({
        "game": "fallout4", "gameVersion": "auto", "intent": "standard", "maxConcurrent": 0,
        "showFormidValues": false, "simplifyLogs": false, "formidDatabasePaths": [],
        "installationData": [{"fixtureRef": "main", "path": "CLASSIC Data/databases/CLASSIC Main.yaml"}],
        "observedPaths": [{"path": "Unsolved Logs"}]
    });
    assert!(
        hook(
            "crash-log-scan-run",
            vec![rich("scan-run.execute", run.clone())]
        )
        .is_empty()
    );
    let mut unknown = run.clone();
    unknown["answers"] = json!([]);
    assert_reports(
        &hook(
            "autoscan-report",
            vec![rich("autoscan-report.execute", unknown)],
        ),
        "unknown members",
    );
    let mut escaping = run.clone();
    escaping["observedPaths"] = json!([{"path": "../outside"}]);
    assert_reports(
        &hook(
            "crash-log-scan-run",
            vec![rich("scan-run.execute", escaping)],
        ),
        "canonical relative paths",
    );
    let mut missing = run;
    missing.as_object_mut().unwrap().remove("game");
    assert_reports(
        &hook(
            "crash-log-scan-run",
            vec![rich("scan-run.execute", missing)],
        ),
        "missing",
    );

    let launch = json!({"settingsFixtureRef": "s", "intent": "standard", "targetedInputs": [], "overrides": {}, "files": []});
    assert!(
        hook(
            "crash-log-scan-launch",
            vec![rich("crash-log-scan-launch.prepare", launch.clone())]
        )
        .is_empty()
    );
    let mut extra = launch;
    extra["expected"] = json!({});
    assert_reports(
        &hook(
            "crash-log-scan-launch",
            vec![rich("crash-log-scan-launch.prepare", extra)],
        ),
        "launch input must be exactly",
    );
}

/// A config vocabulary source with the three enums the config resolvers use.
const CONFIG_SOURCE: &str = r#"
pub enum InstalledYamlDataProvenance { Updated, Bundled }
impl Vocabulary for InstalledYamlDataProvenance {
    fn as_str(self) -> &'static str {
        match self { Self::Updated => "updated", Self::Bundled => "bundled" }
    }
}
pub enum InstalledYamlDataDiagnosticKind { Missing }
impl Vocabulary for InstalledYamlDataDiagnosticKind {
    fn as_str(self) -> &'static str { match self { Self::Missing => "missing" } }
}
pub enum LocalIgnoreYamlDataState { Existing, Generated }
impl Vocabulary for LocalIgnoreYamlDataState {
    fn as_str(self) -> &'static str {
        match self { Self::Existing => "existing", Self::Generated => "generated" }
    }
}
"#;

#[test]
fn vocabulary_inputs_carry_exactly_the_source_tokens() {
    let dir = tempfile::tempdir().expect("temp dir");
    let source = dir
        .path()
        .join("business-logic/classic-config-core/src/installed_yaml_data.rs");
    std::fs::create_dir_all(source.parent().unwrap()).unwrap();
    std::fs::write(&source, CONFIG_SOURCE).unwrap();
    let root = RepoRoot::new(dir.path());
    let input = |operation: &str, tokens: &[&str]| {
        rich(
            "vocabulary.resolve",
            json!({"operation": operation, "tokens": tokens}),
        )
    };
    let complete = || {
        vec![
            input(
                "installed_yaml_data_provenance_label",
                &["updated", "bundled", "not_a_real_token"],
            ),
            input(
                "scan_run_installed_yaml_data_provenance_label",
                &["updated", "bundled", "not_a_real_token"],
            ),
            input(
                "installed_yaml_data_diagnostic_kind_label",
                &["missing", "not_a_real_token"],
            ),
            input(
                "local_ignore_yaml_data_state_label",
                &["existing", "generated", "not_a_real_token"],
            ),
        ]
    };
    assert_eq!(
        hook_at(&root, "config-vocabulary", complete()),
        Vec::<String>::new()
    );

    let mut stale = complete();
    stale[2] = input("installed_yaml_data_diagnostic_kind_label", &["missing"]);
    assert_reports(
        &hook_at(&root, "config-vocabulary", stale),
        "source tokens followed by not_a_real_token",
    );

    let mut missing = complete();
    missing.pop();
    assert_reports(
        &hook_at(&root, "config-vocabulary", missing),
        "every public resolver exactly once",
    );

    std::fs::write(
        &source,
        CONFIG_SOURCE.replace("Self::Bundled => \"bundled\"", ""),
    )
    .unwrap();
    assert_reports(
        &hook_at(&root, "config-vocabulary", complete()),
        "lack complete, unique source tokens",
    );
}

/// A pack plus the repository it lives in, for driving the expectation
/// compilers. Shared with the family modules' own sibling tests.
pub(super) struct PackRepo {
    /// Keeps a temporary repository alive (`None` for the real repository).
    _dir: Option<tempfile::TempDir>,
    pub root: RepoRoot,
    pub pack: Pack,
    pub fixtures: BTreeMap<String, Fixture>,
}

impl PackRepo {
    /// A temporary repository holding `files` (repo-relative path, bytes) and
    /// `pack`.
    pub fn temp(files: &[(&str, &[u8])], pack: Value) -> Self {
        let dir = tempfile::tempdir().expect("temp dir");
        for (path, bytes) in files {
            let full = dir.path().join(path);
            std::fs::create_dir_all(full.parent().expect("parent")).expect("create dir");
            std::fs::write(full, bytes).expect("write file");
        }
        let root = RepoRoot::new(dir.path().canonicalize().expect("canonical temp dir"));
        Self::with(Some(dir), root, pack)
    }

    /// The real repository's pack in `tests/conformance/packs/<directory>`.
    pub fn real(directory: &str) -> Self {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .expect("xtask lives in the repository")
            .canonicalize()
            .expect("canonical repository root");
        let root = RepoRoot::new(root);
        let text = std::fs::read_to_string(
            root.join(&format!("tests/conformance/packs/{directory}/v1.json")),
        )
        .expect("read real pack");
        Self::with(
            None,
            root,
            serde_json::from_str(&text).expect("real pack JSON"),
        )
    }

    fn with(dir: Option<tempfile::TempDir>, root: RepoRoot, pack: Value) -> Self {
        let pack: Pack = serde_json::from_value(pack).expect("pack deserializes");
        let fixtures = pack
            .fixtures
            .keys()
            .map(|reference| (reference.clone(), Fixture { json: None }))
            .collect();
        Self {
            _dir: dir,
            root,
            pack,
            fixtures,
        }
    }

    /// The compiler context over this pack.
    pub fn context(&self) -> InputContext<'_> {
        InputContext {
            root: &self.root,
            pack: &self.pack,
            fixtures: &self.fixtures,
        }
    }

    /// The compiled expectations, or the compiler's issue message.
    pub fn compile(&self) -> Result<Compiled, String> {
        compile_expectations(&self.context()).map_err(|issue| {
            assert_eq!(issue.rule, EXPECTATION_RULE);
            issue.message
        })
    }

    /// Mutates the pack through its JSON form (for seeding oracle
    /// disagreements into a real pack).
    pub fn edit(mut self, mutate: impl FnOnce(&mut Value)) -> Self {
        let mut value = pack_json(&self.pack);
        mutate(&mut value);
        self.pack = serde_json::from_value(value).expect("edited pack deserializes");
        self
    }
}

/// `pack` as JSON (the schema structs only deserialize, so this rebuilds the
/// members the compilers read).
fn pack_json(pack: &Pack) -> Value {
    let scenarios: Vec<Value> = pack
        .scenarios
        .iter()
        .map(|scenario| {
            let normalization = &scenario.normalization;
            let mut rules = json!({
                "rootRelativePaths": normalization.root_relative_paths,
                "unorderedPaths": normalization.unordered_paths,
                "excludedPaths": normalization.excluded_paths.iter().map(|exclusion| json!({
                    "path": exclusion.path, "rationale": exclusion.rationale
                })).collect::<Vec<_>>(),
            });
            if let Some(files) = &normalization.optional_empty_files {
                rules["optionalEmptyFiles"] = files
                    .iter()
                    .map(|file| {
                        json!({
                            "path": file.path,
                            "relativePath": file.relative_path,
                            "rationale": file.rationale,
                        })
                    })
                    .collect();
            }
            json!({
                "id": scenario.id,
                "action": scenario.action,
                "capabilityIds": scenario.capability_ids,
                "fixtureRefs": scenario.fixture_refs,
                "input": scenario.input,
                "expected": scenario.expected,
                "normalization": rules,
            })
        })
        .collect();
    json!({
        "schemaVersion": pack.schema_version,
        "familyId": pack.family_id,
        "familyVersion": pack.family_version,
        "domainOwner": {"rustCrate": pack.domain_owner.rust_crate},
        "fixtureRoot": pack.fixture_root,
        "fixtures": pack.fixtures,
        "capabilities": [],
        "scenarios": scenarios,
        "consumerObligations": []
    })
}

#[test]
fn families_without_a_compiler_keep_their_authored_expectations() {
    let repo = PackRepo::real("performance");
    let compiled = repo.compile().expect("identity compile");
    assert!(compiled.oracles.is_empty());
    let authored: Vec<_> = repo
        .pack
        .scenarios
        .iter()
        .map(|scenario| scenario.expected.clone())
        .collect();
    assert_eq!(compiled.expected, authored);
}

#[test]
fn normalization_is_identity_for_families_and_stages_without_an_arm() {
    let expected = json!({"a": 1}).as_object().cloned().unwrap();
    let actual = json!({"a": 2}).as_object().cloned().unwrap();
    for (family, action, stage) in [
        ("performance", "performance.observe", Stage::BeforeDeclared),
        ("performance", "performance.observe", Stage::AfterDeclared),
        (
            "autoscan-report",
            "autoscan-report.execute",
            Stage::AfterDeclared,
        ),
        (
            "user-settings",
            "user-settings.update",
            Stage::BeforeDeclared,
        ),
        ("user-settings", "user-settings.open", Stage::AfterDeclared),
    ] {
        assert_eq!(
            normalize_observation(family, action, stage, expected.clone(), actual.clone()),
            Ok((expected.clone(), actual.clone())),
            "{family} {action} {stage:?}"
        );
    }
}
