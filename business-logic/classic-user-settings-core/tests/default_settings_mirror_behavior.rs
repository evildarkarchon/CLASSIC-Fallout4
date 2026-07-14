//! Behavioral checks for the developer-facing User Settings default-mirror generator.

use std::path::Path;
use std::process::{Command, Output};

use classic_settings_core::{Yaml, parse_yaml_content};

/// Runs the checked-in mirror generator against an isolated repository-shaped root.
fn run_generator(repo_root: &Path, check: bool) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_generate-user-settings-default-mirror"));
    command.arg("--repo-root").arg(repo_root);
    if check {
        command.arg("--check");
    }
    command.output().expect("run default-mirror generator")
}

#[test]
fn generation_is_idempotent_and_check_rejects_default_drift() {
    let root = tempfile::tempdir().expect("create temporary repository root");
    let databases = root.path().join("CLASSIC Data/databases");
    std::fs::create_dir_all(&databases).expect("create YAML Data directory");
    let main_yaml = databases.join("CLASSIC Main.yaml");
    std::fs::write(
        &main_yaml,
        concat!(
            "schema_version: \"2.1\"\n",
            "CLASSIC_Info:\n",
            "  default_settings: |\n",
            "    stale: true\n",
            "\n",
            "  default_localyaml: |\n",
            "    Game_Info: {}\n",
        ),
    )
    .expect("write stale compatibility mirror");

    let generated = run_generator(root.path(), false);
    assert!(
        generated.status.success(),
        "generation failed: {}",
        String::from_utf8_lossy(&generated.stderr)
    );
    let first = std::fs::read(&main_yaml).expect("read generated mirror");
    assert!(
        String::from_utf8_lossy(&first).contains("  Update Check: true"),
        "generated mirror must contain the Rust-owned Update Check default"
    );

    let regenerated = run_generator(root.path(), false);
    assert!(regenerated.status.success());
    let second = std::fs::read(&main_yaml).expect("read regenerated mirror");
    assert_eq!(second, first, "a second generation must be byte-identical");

    let fresh = run_generator(root.path(), true);
    assert!(
        fresh.status.success(),
        "freshness check failed: {}",
        String::from_utf8_lossy(&fresh.stderr)
    );

    let drifted = String::from_utf8(first)
        .expect("generated YAML Data must be UTF-8")
        .replacen("  Update Check: true", "  Update Check: false", 1);
    std::fs::write(&main_yaml, drifted).expect("write drifted compatibility mirror");

    let stale = run_generator(root.path(), true);
    assert!(
        !stale.status.success(),
        "drift must fail the freshness check"
    );
}

/// Expected YAML type and value for one canonical Rust-owned setting.
enum ExpectedDefault {
    Bool(bool),
    Integer(i64),
    String(&'static str),
    Null,
    EmptyMapping,
}

/// Returns one parsed node at a canonical path without applying YAML type coercion.
fn node_at<'a>(document: &'a Yaml, path: &[&str]) -> &'a Yaml {
    path.iter().fold(document, |node, label| &node[*label])
}

/// Asserts the exact YAML type and value declared independently by the behavior contract.
fn assert_default(document: &Yaml, path: &[&str], expected: ExpectedDefault) {
    let actual = node_at(document, path);
    let matches = match expected {
        ExpectedDefault::Bool(expected) => {
            matches!(actual, Yaml::Boolean(actual) if *actual == expected)
        }
        ExpectedDefault::Integer(expected) => {
            matches!(actual, Yaml::Integer(actual) if *actual == expected)
        }
        ExpectedDefault::String(expected) => actual.as_str() == Some(expected),
        ExpectedDefault::Null => matches!(actual, Yaml::Null),
        ExpectedDefault::EmptyMapping => {
            matches!(actual, Yaml::Hash(mapping) if mapping.is_empty())
        }
    };
    assert!(
        matches,
        "unexpected default at {}: {actual:?}",
        path.join(".")
    );
}

#[test]
fn checked_in_mirror_is_fresh_and_covers_every_canonical_known_setting() {
    let repo_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let fresh = run_generator(&repo_root, true);
    assert!(
        fresh.status.success(),
        "checked-in mirror is stale: {}",
        String::from_utf8_lossy(&fresh.stderr)
    );

    let main_yaml =
        std::fs::read_to_string(repo_root.join("CLASSIC Data/databases/CLASSIC Main.yaml"))
            .expect("read checked-in CLASSIC Main.yaml");
    let mut outer = parse_yaml_content("checked-in CLASSIC Main.yaml", &main_yaml)
        .expect("parse checked-in CLASSIC Main.yaml");
    let outer_document = outer.remove(0);
    let mirror = outer_document["CLASSIC_Info"]["default_settings"]
        .as_str()
        .expect("default_settings must remain a literal scalar");
    let mut documents =
        parse_yaml_content("checked-in default_settings", mirror).expect("parse default mirror");
    let document = documents.remove(0);

    assert_eq!(document["schema_version"].as_str(), Some("1.0"));
    let expected = [
        (
            &["CLASSIC_Settings", "Managed Game"][..],
            ExpectedDefault::String("Fallout 4"),
        ),
        (
            &["CLASSIC_Settings", "Update Check"][..],
            ExpectedDefault::Bool(true),
        ),
        (
            &["CLASSIC_Settings", "Game Version"][..],
            ExpectedDefault::String("auto"),
        ),
        (
            &["CLASSIC_Settings", "Game Folder Path"][..],
            ExpectedDefault::Null,
        ),
        (
            &["CLASSIC_Settings", "Game EXE Path"][..],
            ExpectedDefault::Null,
        ),
        (
            &["CLASSIC_Settings", "Documents Folder Path"][..],
            ExpectedDefault::Null,
        ),
        (
            &["CLASSIC_Settings", "MODS Folder Path"][..],
            ExpectedDefault::Null,
        ),
        (
            &["CLASSIC_Settings", "SCAN Custom Path"][..],
            ExpectedDefault::Null,
        ),
        (
            &["CLASSIC_Settings", "Papyrus Log Path"][..],
            ExpectedDefault::Null,
        ),
        (
            &["CLASSIC_Settings", "FCX Mode"][..],
            ExpectedDefault::Bool(false),
        ),
        (
            &["CLASSIC_Settings", "Simplify Logs"][..],
            ExpectedDefault::Bool(false),
        ),
        (
            &["CLASSIC_Settings", "Show Statistics"][..],
            ExpectedDefault::Bool(false),
        ),
        (
            &["CLASSIC_Settings", "Show FormID Values"][..],
            ExpectedDefault::Bool(false),
        ),
        (
            &["CLASSIC_Settings", "FormID Databases"][..],
            ExpectedDefault::EmptyMapping,
        ),
        (
            &["CLASSIC_Settings", "Move Unsolved Logs"][..],
            ExpectedDefault::Bool(true),
        ),
        (
            &["CLASSIC_Settings", "Unsolved Logs Destination"][..],
            ExpectedDefault::Null,
        ),
        (
            &["CLASSIC_Settings", "Max Concurrent Scans"][..],
            ExpectedDefault::Integer(0),
        ),
        (
            &["UI", "preferences", "auto_switch_after_scan"][..],
            ExpectedDefault::Bool(true),
        ),
        (
            &["UI", "preferences", "auto_refresh_interval_ms"][..],
            ExpectedDefault::Integer(5_000),
        ),
        (
            &["UI", "window_geometry", "main_tab", "maximized"][..],
            ExpectedDefault::Bool(false),
        ),
        (
            &["UI", "window_geometry", "main_tab", "width"][..],
            ExpectedDefault::Integer(640),
        ),
        (
            &["UI", "window_geometry", "main_tab", "height"][..],
            ExpectedDefault::Integer(500),
        ),
        (
            &["UI", "window_geometry", "backups_tab", "maximized"][..],
            ExpectedDefault::Bool(false),
        ),
        (
            &["UI", "window_geometry", "backups_tab", "width"][..],
            ExpectedDefault::Integer(750),
        ),
        (
            &["UI", "window_geometry", "backups_tab", "height"][..],
            ExpectedDefault::Integer(580),
        ),
        (
            &["UI", "window_geometry", "articles_tab", "maximized"][..],
            ExpectedDefault::Bool(false),
        ),
        (
            &["UI", "window_geometry", "articles_tab", "width"][..],
            ExpectedDefault::Integer(550),
        ),
        (
            &["UI", "window_geometry", "articles_tab", "height"][..],
            ExpectedDefault::Integer(350),
        ),
        (
            &["UI", "window_geometry", "results_tab", "maximized"][..],
            ExpectedDefault::Bool(false),
        ),
        (
            &["UI", "window_geometry", "results_tab", "width"][..],
            ExpectedDefault::Integer(750),
        ),
        (
            &["UI", "window_geometry", "results_tab", "height"][..],
            ExpectedDefault::Integer(450),
        ),
        (
            &["UI", "tui", "active_tab"][..],
            ExpectedDefault::Integer(0),
        ),
        (
            &["UI", "tui", "results_panel_width"][..],
            ExpectedDefault::Integer(30),
        ),
        (
            &["UI", "tui", "sort_ascending"][..],
            ExpectedDefault::Bool(false),
        ),
    ];
    for (path, default) in expected {
        assert_default(&document, path, default);
    }
}

#[test]
fn generation_preserves_crlf_and_every_byte_outside_the_mirror() {
    let root = tempfile::tempdir().expect("create temporary repository root");
    let databases = root.path().join("CLASSIC Data/databases");
    std::fs::create_dir_all(&databases).expect("create YAML Data directory");
    let main_yaml = databases.join("CLASSIC Main.yaml");
    let prefix = "# retained prefix\r\nschema_version: \"2.2\"\r\nCLASSIC_Info:\r\n  default_settings: |\r\n";
    let suffix = "\r\n  default_localyaml: |\r\n    retained: exactly\r\n# retained suffix\r\n";
    std::fs::write(&main_yaml, format!("{prefix}    stale: true\r\n{suffix}"))
        .expect("write CRLF fixture");

    let generated = run_generator(root.path(), false);
    assert!(
        generated.status.success(),
        "CRLF generation failed: {}",
        String::from_utf8_lossy(&generated.stderr)
    );
    let content = std::fs::read_to_string(main_yaml).expect("read generated CRLF fixture");
    assert!(content.starts_with(prefix));
    assert!(content.ends_with(suffix));
    assert!(!content.replace("\r\n", "").contains('\n'));
}
