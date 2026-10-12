//! The repository command table and attempt classification, plus the real
//! process runner on a trivial command.

use super::*;

fn launch_for(command: ParticipantCommand) -> Launch {
    Launch {
        family_id: "demo".into(),
        participant: "cxx".into(),
        instance: "windows-msvc".into(),
        command,
        working_dir: std::env::temp_dir(),
        env: BTreeMap::new(),
        run_plan: PathBuf::from("run_plan.json"),
        receipt: PathBuf::from("receipt.json"),
    }
}

#[test]
fn rust_and_tui_run_their_cargo_tests() {
    let table = CommandTable::repository(Compiler::Msvc, "default");
    let semantic = table.command(Participant::Rust, "performance").unwrap();
    assert_eq!(semantic.program, "cargo");
    assert_eq!(
        semantic.args,
        [
            "test",
            "-p",
            "classic-scanlog-core",
            "--test",
            "semantic_conformance",
            "--",
            "--nocapture"
        ]
    );
    assert_eq!(semantic.timeout, Duration::from_secs(1200));
    assert!(semantic.source_paths.contains(&LAUNCHER.to_owned()));

    let scan = table.command(Participant::Rust, "autoscan-report").unwrap();
    assert!(
        scan.args
            .contains(&"writes_scan_run_conformance_receipt".to_owned())
    );
    let settings = table.command(Participant::Rust, "user-settings").unwrap();
    assert!(settings.args.contains(&"compatibility_contract".to_owned()));
    let launch = table
        .command(Participant::Rust, "crash-log-scan-launch")
        .unwrap();
    assert!(
        launch
            .args
            .contains(&"writes_launch_conformance_receipt".to_owned())
    );

    let bridge = table
        .command(Participant::Rust, "report-discovery")
        .unwrap();
    assert_eq!(bridge.program, "pwsh");
    assert!(
        bridge
            .args
            .contains(&"tools/enter_vs_dev_shell.ps1".to_owned())
    );
    assert!(
        bridge
            .args
            .last()
            .unwrap()
            .contains("files::tests::writes_report_discovery_conformance_receipt")
    );

    let service = table.command(Participant::Rust, "update-services").unwrap();
    assert!(
        service
            .source_paths
            .contains(&"xtask/src/conformance/update_service.rs".to_owned())
    );

    let tui = table.command(Participant::Tui, "user-settings").unwrap();
    assert!(tui.args.contains(&"--ignored".to_owned()));
    assert!(
        tui.source_paths.is_empty(),
        "consumer sources come from the catalog"
    );
}

#[test]
fn native_participants_run_the_build_wrappers_test_only() {
    let table = CommandTable::repository(Compiler::ClangCl, "ci-system-qt");
    for (participant, script, test) in [
        (
            Participant::Cxx,
            "classic-cli/build_cli.ps1",
            "classic-cxx-conformance",
        ),
        (
            Participant::Cli,
            "classic-cli/build_cli.ps1",
            "classic-cli-consumer-conformance",
        ),
        (
            Participant::Gui,
            "classic-gui/build_gui.ps1",
            "classic-gui-consumer-conformance",
        ),
    ] {
        let command = table.command(participant, "user-settings").unwrap();
        assert_eq!(command.program, "pwsh");
        let args = command.args.join(" ");
        assert!(
            args.contains(&format!(
                "-File {script} -Test -TestOnly -CTestName {test} -Compiler clang-cl"
            )),
            "{args}"
        );
        assert_eq!(command.timeout, Duration::from_secs(900));
        assert!(command.wrapper);
    }
    assert!(
        table
            .command(Participant::Gui, "user-settings")
            .unwrap()
            .args
            .ends_with(&["-Preset".to_owned(), "ci-system-qt".to_owned()])
    );
    // A participant xtask does not know (a retired binding) has no command.
    assert!(Participant::from_id("node").is_none());
    let cxx = table.command(Participant::Cxx, "user-settings").unwrap();
    assert!(
        cxx.source_paths
            .contains(&"cpp-bindings/classic-cpp-bridge/src/settings.rs".to_owned())
    );
}

#[test]
fn attempts_classify_their_own_failures() {
    let command = CommandTable::repository(Compiler::Msvc, "default")
        .command(Participant::Cxx, "demo")
        .unwrap();
    let launch = launch_for(command);
    assert!(Attempt::exited(0).failures(&launch).is_empty());
    assert!(Attempt::exited(0).succeeded());

    let kinds = |attempt: Attempt| -> Vec<&'static str> {
        attempt
            .failures(&launch)
            .iter()
            .map(|failure| failure.kind.as_str())
            .collect()
    };
    assert_eq!(kinds(Attempt::exited(1)), ["adapter_command_failure"]);
    let missing_toolchain = Attempt {
        stderr: "ERROR: VCPKG_ROOT environment variable is not set".into(),
        ..Attempt::exited(1)
    };
    assert_eq!(kinds(missing_toolchain), ["local_environment_failure"]);
    let timed_out = Attempt {
        timed_out: true,
        ..Attempt::default()
    };
    assert_eq!(kinds(timed_out), ["adapter_command_failure"]);
    let not_started = Attempt {
        launch_error: Some("program not found".into()),
        ..Attempt::default()
    };
    assert_eq!(kinds(not_started), ["local_environment_failure"]);

    // Only the wrappers' prerequisite messages count as environment failures.
    let mut cargo = launch_for(
        CommandTable::repository(Compiler::Msvc, "default")
            .command(Participant::Rust, "demo")
            .unwrap(),
    );
    cargo.participant = "rust".into();
    let output = Attempt {
        stdout: "could not find vs dev shell".into(),
        ..Attempt::exited(101)
    };
    assert_eq!(output.failures(&cargo)[0].kind, FailureKind::AdapterCommand);
}

#[test]
fn spawn_captures_output_and_exit_codes() {
    let command = ParticipantCommand {
        program: "git".into(),
        args: vec!["--version".into()],
        source_paths: Vec::new(),
        timeout: Duration::from_secs(60),
        wrapper: false,
    };
    let attempt = spawn(&launch_for(command.clone()));
    assert!(attempt.succeeded(), "{attempt:?}");
    assert!(attempt.stdout.starts_with("git version"), "{attempt:?}");

    let failing = ParticipantCommand {
        args: vec!["no-such-git-command".into()],
        ..command.clone()
    };
    let attempt = spawn(&launch_for(failing));
    assert_ne!(attempt.exit_code, Some(0));
    assert!(!attempt.stderr.is_empty());

    let missing = ParticipantCommand {
        program: "xtask-no-such-program".into(),
        ..command
    };
    let attempt = spawn(&launch_for(missing));
    assert!(attempt.launch_error.is_some(), "{attempt:?}");
}

#[test]
fn spawn_kills_a_command_that_outlives_its_timeout() {
    let (program, args) = if cfg!(windows) {
        (
            "ping",
            vec!["-n".to_owned(), "30".to_owned(), "127.0.0.1".to_owned()],
        )
    } else {
        ("sleep", vec!["30".to_owned()])
    };
    let command = ParticipantCommand {
        program: program.into(),
        args,
        source_paths: Vec::new(),
        timeout: Duration::from_secs(1),
        wrapper: false,
    };
    let started = Instant::now();
    let attempt = spawn(&launch_for(command));
    assert!(attempt.timed_out, "{attempt:?}");
    assert_eq!(attempt.exit_code, None);
    assert!(
        started.elapsed() < Duration::from_secs(20),
        "{:?}",
        started.elapsed()
    );
}
