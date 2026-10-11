//! The `cargo xtask` binary's output and exit-code contract: 0 pass with
//! `OK: <summary>` on stdout, 1 failure with `path:line: rule: message`
//! findings then a summary on stderr, 2 usage error.

mod common;

use std::process::{Command, Output};

use common::FixtureRepo;

const BRIDGE: &str = r#"#[cxx::bridge(namespace = "classic::m")]
mod ffi {
    extern "Rust" {
        fn used() -> i32;
        fn unused() -> i32;
    }
}
"#;

fn xtask(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_xtask"))
        .args(args)
        .output()
        .expect("run the xtask binary")
}

fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).replace("\r\n", "\n")
}

#[test]
fn help_lists_the_cxx_bridge_gate_subcommand() {
    let output = xtask(&["--help"]);
    assert_eq!(output.status.code(), Some(0));
    assert!(text(&output.stdout).contains("cxx-bridge-gate"));
}

#[test]
fn a_usage_error_exits_with_2() {
    assert_eq!(xtask(&["no-such-command"]).status.code(), Some(2));
    assert_eq!(xtask(&[]).status.code(), Some(2));
}

#[test]
fn a_pass_prints_ok_on_stdout_and_exits_0() {
    let repo = FixtureRepo::cxx().bridge("m.rs", BRIDGE).cli(
        "a.cpp",
        "int f() { return classic::m::used() + classic::m::unused(); }\n",
    );
    let root = repo.path().to_str().unwrap();

    let output = xtask(&["--repo-root", root, "cxx-bridge-gate"]);

    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        text(&output.stdout),
        "OK: cxx-bridge-gate: every export has a production caller \
         (2 exports in 1 bridge modules, 1 frontend files scanned)\n"
    );
    assert_eq!(text(&output.stderr), "");
}

#[test]
fn a_failure_prints_findings_then_a_summary_on_stderr_and_exits_1() {
    let repo = FixtureRepo::cxx().bridge("m.rs", BRIDGE).cli(
        "a.cpp",
        "using namespace classic::m;\nint f() { return classic::m::used(); }\n",
    );
    let root = repo.path().to_str().unwrap();

    // `--repo-root` is global, so it may also follow the subcommand.
    let output = xtask(&["cxx-bridge-gate", "--repo-root", root]);

    assert_eq!(output.status.code(), Some(1));
    assert_eq!(text(&output.stdout), "");
    let stderr = text(&output.stderr);
    let lines: Vec<&str> = stderr.lines().collect();
    assert_eq!(lines.len(), 3, "{stderr}");
    assert!(
        lines[0].starts_with("classic-cli/src/a.cpp:1: unsupported-reference-form: "),
        "{stderr}"
    );
    assert!(
        lines[1].starts_with("cpp-bindings/classic-cpp-bridge/src/m.rs:5: orphan-export: "),
        "{stderr}"
    );
    assert_eq!(
        lines[2],
        "cxx-bridge-gate: 1 orphan export(s), 1 unsupported reference form(s) \
         (2 exports in 1 bridge modules, 1 frontend files scanned)"
    );
}

#[test]
fn an_operational_failure_exits_1() {
    let repo = FixtureRepo::empty();
    let root = repo.path().to_str().unwrap();

    let output = xtask(&["--repo-root", root, "cxx-bridge-gate"]);

    assert_eq!(output.status.code(), Some(1));
    assert!(text(&output.stderr).starts_with("error: "));
}
