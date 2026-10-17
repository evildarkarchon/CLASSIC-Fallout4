//! Fixture-tree tests for `cargo xtask user-settings-ownership`, driven
//! through `user_settings_ownership::run` (the subcommand seam) and, for the
//! output contract, through the binary.
//!
//! The retired Python suite (`tools/user_settings_ownership/tests`) is the
//! behavioural spec; its cases are folded into the tables below.

mod common;

use std::fs;
use std::process::Command;

use common::FixtureRepo;
use xtask::{Outcome, user_settings_ownership};

/// The source roots the gate requires, all created empty by [`repo`].
const ROOTS: [&str; 6] = [
    "foundation",
    "business-logic",
    "cpp-bindings",
    "classic-cli",
    "classic-gui",
    "ui-applications",
];

/// The User Settings owner crate's source directory.
const OWNER: &str = "business-logic/classic-user-settings-core/src";
/// The compatibility-mirror generator, the only code allowed to read the mirror.
const GENERATOR: &str =
    "business-logic/classic-user-settings-core/src/bin/generate-user-settings-default-mirror";

/// A fixture tree with every source root in place and no sources.
fn repo() -> FixtureRepo {
    let repo = FixtureRepo::empty();
    for root in ROOTS {
        fs::create_dir_all(repo.path().join(root)).expect("create source root");
    }
    repo
}

/// Runs the gate over `repo` and returns its findings rendered as
/// `path:line: rule: message` lines (empty on a pass).
fn findings(repo: &FixtureRepo) -> Vec<String> {
    match user_settings_ownership::run(&repo.root(), user_settings_ownership::Args::default())
        .expect("gate runs")
    {
        Outcome::Pass { .. } => Vec::new(),
        Outcome::Fail { findings, .. } => findings.iter().map(ToString::to_string).collect(),
    }
}

/// One production file per audited language, each outside the owner.
const LANGUAGE_FILES: [&str; 4] = [
    "business-logic/example-core/src/lib.rs",
    "classic-cli/src/bootstrap.cpp",
    "classic-gui/src/settings_view.h",
    "cpp-bindings/classic-cpp-bridge/include/bridge.hpp",
];

/// Every banned per-line pattern as a line of code, with the rule it trips.
const PER_LINE_PATTERNS: [(&str, &str); 14] = [
    (
        "auto mode = yaml.get(\"CLASSIC_Settings.FCX Mode\");",
        "raw-user-settings-key",
    ),
    (
        "auto config = ClassicConfig::load();",
        "legacy-user-settings-type",
    ),
    (
        "auto paths = PathConfig::load();",
        "legacy-user-settings-type",
    ),
    (
        "load(YamlSource::Settings);",
        "legacy-generic-settings-owner",
    ),
    (
        "load(CoreYamlSource::Settings);",
        "legacy-generic-settings-owner",
    ),
    ("load(YamlFile::Settings);", "legacy-generic-settings-owner"),
    (
        "load(CoreYamlFile::Settings);",
        "legacy-generic-settings-owner",
    ),
    (
        "check(SETTINGS_IGNORE_NONE);",
        "legacy-generic-settings-owner",
    ),
    ("check(must_not_be_none);", "legacy-generic-settings-owner"),
    (
        "auto defaults = yaml[\"default_settings\"];",
        "compatibility-mirror-runtime-use",
    ),
    (
        "auto defaults = yaml['default_settings'];",
        "compatibility-mirror-runtime-use",
    ),
    (
        "auto defaults = CLASSIC_Info.default_settings;",
        "compatibility-mirror-runtime-use",
    ),
    // A declaration trips the structural rule and the per-line rule on the
    // same line; the identical findings are reported once.
    ("struct ClassicConfig {};", "legacy-user-settings-type"),
    ("enum PathConfig { A };", "legacy-user-settings-type"),
];

#[test]
fn each_banned_pattern_fails_seeded_in_each_language_and_passes_in_comments() {
    for path in LANGUAGE_FILES {
        for (code, rule) in PER_LINE_PATTERNS {
            let seeded = repo().file(path, &format!("ok();\n{code}\n"));
            assert_eq!(
                findings(&seeded),
                [format!("{path}:2: {rule}: {code}")],
                "seeded `{code}` in {path}"
            );

            let commented = repo().file(
                path,
                &format!("ok(); // {code}\n/* {code}\n   {code} */\nok();\n"),
            );
            assert_eq!(
                findings(&commented),
                Vec::<String>::new(),
                "commented `{code}` in {path}"
            );
        }
    }
}

#[test]
fn a_generic_yaml_enum_cannot_regain_a_settings_variant() {
    for path in LANGUAGE_FILES {
        for name in ["YamlSource", "CoreYamlSource", "YamlFile", "CoreYamlFile"] {
            let seeded = repo().file(
                path,
                &format!("ok();\npub enum {name} {{\n    Main,\n    Settings,\n}}\n"),
            );
            assert_eq!(
                findings(&seeded),
                [format!(
                    "{path}:2: legacy-generic-settings-owner: pub enum {name} {{"
                )],
                "{name} in {path}"
            );

            let clean = repo().file(
                path,
                &format!("pub enum {name} {{\n    Main,\n    // Settings,\n    Game,\n}}\n"),
            );
            assert_eq!(findings(&clean), Vec::<String>::new(), "{name} in {path}");
        }
    }
}

#[test]
fn the_owner_may_interpret_raw_keys_but_not_restore_legacy_models_or_read_the_mirror() {
    let path = format!("{OWNER}/document.rs");
    let allowed = repo().file(
        &path,
        "let key = \"CLASSIC_Settings\";\nlet c = ClassicConfig::retired();\nlet s = YamlSource::Settings;\n",
    );
    assert_eq!(findings(&allowed), Vec::<String>::new());

    for (code, rule) in [
        ("pub struct ClassicConfig;", "legacy-user-settings-type"),
        ("trait PathConfig {}", "legacy-user-settings-type"),
        ("type ClassicConfig = u8;", "legacy-user-settings-type"),
        (
            "let defaults = yaml[\"default_settings\"].clone();",
            "compatibility-mirror-runtime-use",
        ),
    ] {
        let seeded = repo().file(&path, &format!("{code}\n"));
        assert_eq!(
            findings(&seeded),
            [format!("{path}:1: {rule}: {code}")],
            "{code}"
        );
    }

    let multi_line = repo().file(
        &path,
        "pub enum YamlSource {\n    Main,\n    Settings,\n}\n",
    );
    assert_eq!(
        findings(&multi_line),
        [format!(
            "{path}:1: legacy-generic-settings-owner: pub enum YamlSource {{"
        )]
    );
}

#[test]
fn only_the_generator_may_read_the_compatibility_mirror() {
    let generator = repo().file(
        &format!("{GENERATOR}/mirror.rs"),
        "let defaults = yaml[\"default_settings\"].clone();\n",
    );
    assert_eq!(findings(&generator), Vec::<String>::new());
}

#[test]
fn tests_build_output_other_languages_and_xtask_are_not_audited() {
    let violation = "let mode = yaml.get(\"CLASSIC_Settings\");\n";
    let mut skipped = repo();
    for path in [
        "xtask/src/user_settings_ownership.rs",
        "tools/check.rs",
        "cpp-bindings/classic-cpp-bridge/tests/settings.rs",
        "business-logic/example-core/src/lib_tests.rs",
        "classic-cli/target/debug/build/out.rs",
        "classic-cli/build/generated.h",
        "classic-gui/build-msvc/generated.h",
        "classic-gui/install/include/settings.hpp",
        "classic-gui/installer-staging/settings.hpp",
        "ui-applications/dist/bundle.rs",
        "ui-applications/node_modules/pkg/lib.rs",
        "ui-applications/.venv/lib.rs",
        "classic-cli/src/__tests__/settings.cpp",
        "classic-cli/src/legacy.py",
        "classic-cli/src/legacy.ts",
        "classic-cli/src/legacy.cc",
    ] {
        skipped = skipped.file(path, violation);
    }
    assert_eq!(findings(&skipped), Vec::<String>::new());
}

#[test]
fn files_named_like_install_or_build_prefixes_are_still_audited() {
    // The Python check applied the `install`/`build-` prefix exclusion to file
    // names too, which silently skipped production files such as
    // `installation_root.rs`. Only directories are excluded by prefix now.
    let repo = repo()
        .file(
            "business-logic/classic-config-core/src/installation_root.rs",
            "let k = \"CLASSIC_Settings\";\n",
        )
        .file(
            "classic-cli/src/build-info.h",
            "auto k = \"CLASSIC_Settings\";\n",
        );
    assert_eq!(
        findings(&repo),
        [
            "business-logic/classic-config-core/src/installation_root.rs:1: raw-user-settings-key: let k = \"CLASSIC_Settings\";",
            "classic-cli/src/build-info.h:1: raw-user-settings-key: auto k = \"CLASSIC_Settings\";",
        ]
    );
}

/// Expected findings as `(line, rule, message)` for one fixture file.
type Expected = &'static [(usize, &'static str, &'static str)];

#[test]
fn comment_markers_inside_literals_and_rust_syntax_do_not_hide_code() {
    let rust = "business-logic/example-core/src/lib.rs";
    let cpp = "classic-cli/src/main.cpp";
    let cases: [(&str, &str, Expected); 9] = [
        // A `//` inside a string is not a comment, so the key after it counts.
        (
            rust,
            "let u = \"https://x\"; let k = \"CLASSIC_Settings\";\n",
            &[(
                1,
                "raw-user-settings-key",
                "let u = \"https://x\"; let k = \"CLASSIC_Settings\";",
            )],
        ),
        (
            cpp,
            "auto u = \"/*\";\nauto k = \"CLASSIC_Settings\";\n",
            &[(2, "raw-user-settings-key", "auto k = \"CLASSIC_Settings\";")],
        ),
        // Attributes and preprocessor lines are code.
        (
            rust,
            "#[serde(rename = \"CLASSIC_Settings\")]\nstruct S;\n",
            &[(
                1,
                "raw-user-settings-key",
                "#[serde(rename = \"CLASSIC_Settings\")]",
            )],
        ),
        (
            cpp,
            "#define KEY \"CLASSIC_Settings\"\n",
            &[(
                1,
                "raw-user-settings-key",
                "#define KEY \"CLASSIC_Settings\"",
            )],
        ),
        // Rust lifetimes are not character literals.
        (rust, "fn f<'a>(x: &'a str) {} // ClassicConfig\n", &[]),
        (
            rust,
            "fn f(x: &'static str) {} // it's ClassicConfig\n",
            &[],
        ),
        // Rust block comments nest.
        (
            rust,
            "/* outer /* inner */ ClassicConfig */\nfn ok() {}\n",
            &[],
        ),
        // Raw strings may hold quotes and comment markers.
        (
            rust,
            "let s = r#\"a \"//\" b\"#; let k = \"CLASSIC_Settings\";\n",
            &[(
                1,
                "raw-user-settings-key",
                "let s = r#\"a \"//\" b\"#; let k = \"CLASSIC_Settings\";",
            )],
        ),
        // Multi-line Rust strings keep their content as code.
        (
            rust,
            "let s = \"first\nCLASSIC_Settings\"; // note\n",
            &[(2, "raw-user-settings-key", "CLASSIC_Settings\";")],
        ),
    ];
    for (path, source, expected) in cases {
        let expected: Vec<String> = expected
            .iter()
            .map(|(line, rule, message)| format!("{path}:{line}: {rule}: {message}"))
            .collect();
        assert_eq!(findings(&repo().file(path, source)), expected, "{source}");
    }
}

#[test]
fn every_finding_is_collected_and_sorted() {
    let repo = repo()
        .file("classic-gui/src/b.cpp", "auto k = \"CLASSIC_Settings\";\n")
        .file(
            "classic-cli/src/a.cpp",
            "ok();\nauto c = ClassicConfig::load(\"CLASSIC_Settings\");\n",
        );
    assert_eq!(
        findings(&repo),
        [
            "classic-cli/src/a.cpp:2: legacy-user-settings-type: auto c = ClassicConfig::load(\"CLASSIC_Settings\");",
            "classic-cli/src/a.cpp:2: raw-user-settings-key: auto c = ClassicConfig::load(\"CLASSIC_Settings\");",
            "classic-gui/src/b.cpp:1: raw-user-settings-key: auto k = \"CLASSIC_Settings\";",
        ]
    );
}

#[test]
fn a_missing_source_root_is_an_operational_failure() {
    let repo = FixtureRepo::empty().file("classic-cli/src/main.cpp", "ok();\n");
    let error =
        user_settings_ownership::run(&repo.root(), user_settings_ownership::Args::default())
            .expect_err("missing roots must not pass");
    assert!(error.to_string().contains("foundation"), "{error:#}");
}

/// Runs the built binary as `cargo xtask --repo-root <repo> user-settings-ownership`.
fn run_binary(repo: &FixtureRepo) -> (Option<i32>, String, String) {
    let output = Command::new(env!("CARGO_BIN_EXE_xtask"))
        .args([
            "--repo-root",
            repo.path().to_str().unwrap(),
            "user-settings-ownership",
        ])
        .output()
        .expect("run the xtask binary");
    let text = |bytes: &[u8]| String::from_utf8_lossy(bytes).replace("\r\n", "\n");
    (
        output.status.code(),
        text(&output.stdout),
        text(&output.stderr),
    )
}

#[test]
fn the_binary_prints_ok_on_a_pass_and_findings_on_stderr_on_a_failure() {
    let clean = repo().file("classic-cli/src/main.cpp", "int main() { return 0; }\n");
    assert_eq!(
        run_binary(&clean),
        (
            Some(0),
            "OK: user-settings-ownership: User Settings has one owner (1 production files audited)\n"
                .to_owned(),
            String::new()
        )
    );

    let seeded = clean.file("classic-gui/src/a.h", "auto k = \"CLASSIC_Settings\";\n");
    assert_eq!(
        run_binary(&seeded),
        (
            Some(1),
            String::new(),
            "classic-gui/src/a.h:1: raw-user-settings-key: auto k = \"CLASSIC_Settings\";\n\
             user-settings-ownership: 1 finding(s) (2 production files audited)\n"
                .to_owned()
        )
    );
}
