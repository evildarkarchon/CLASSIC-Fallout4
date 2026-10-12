//! Launching participants: the command table and the process runner.
//!
//! `conformance run` never hard-codes how a participant runs. It takes a
//! [`CommandTable`] (which command runs a participant for a family, which
//! source paths that command's receipt is bound to, and its timeout) and a
//! runner that executes one [`Launch`] and returns its [`Attempt`]. The real
//! runner is [`spawn`] over [`CommandTable::repository`]; tests pass their own
//! table and a fake runner that writes receipts without spawning anything.
//!
//! The repository table keeps the existing participant runners unchanged
//! (same commands, same environment variables, and they skip when the
//! variables are absent):
//!
//! - **rust** and **tui** run their `cargo test` targets (1200 s timeout).
//!   The two interface families whose Rust runners live in the
//!   `classic-cpp-bridge` library tests run through `tools/enter_vs_dev_shell.ps1`.
//! - **cxx**, **cli** and **gui** run the build wrappers with
//!   `-Test -TestOnly -CTestName <test>` (AGENTS.md rule 9; 15 min timeout),
//!   so the wrapper reuses the build an earlier step made.

use std::collections::BTreeMap;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use super::receipt::FailureKind;
use super::report::ScopedFailure;

/// Timeout of the cargo-test participants (rust, tui).
pub const CARGO_TIMEOUT: Duration = Duration::from_secs(1200);
/// Timeout of the CTest participants (cxx, cli, gui).
pub const CTEST_TIMEOUT: Duration = Duration::from_secs(15 * 60);

/// Plan and receipt variables of semantic adapters (rust, cxx).
pub const SEMANTIC_ENV: (&str, &str) =
    ("CLASSIC_CONFORMANCE_RUN_PLAN", "CLASSIC_CONFORMANCE_OUTPUT");
/// Plan and receipt variables of consumers (cli, gui, tui).
pub const CONSUMER_ENV: (&str, &str) = (
    "CLASSIC_CONSUMER_CONFORMANCE_RUN_PLAN",
    "CLASSIC_CONSUMER_CONFORMANCE_OUTPUT",
);

/// Output fragments (lowercase) that mean a wrapper failed for want of a local
/// toolchain or environment prerequisite rather than a conformance problem.
const LOCAL_ENVIRONMENT_MARKERS: [&str; 13] = [
    "vcpkg_root environment variable is not set",
    "could not find vs dev shell",
    "missing required tool:",
    "missing required environment:",
    "build prerequisites are missing",
    "could not locate a visual studio installation",
    "vs dev shell initialization completed, but",
    "cmake was unable to find a build program corresponding to \"ninja\"",
    "could not find toolchain file:",
    "could not resolve link.exe from cmake_linker",
    "resolved linker is not an msvc-compatible linker",
    "no cmake_cxx_compiler could be found",
    "the c++ compiler is not able to compile a simple test program",
];

/// How one participant runs one family.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParticipantCommand {
    /// The program, resolved on `PATH`.
    pub program: String,
    /// Its arguments.
    pub args: Vec<String>,
    /// Repo-relative paths whose bytes the receipt is bound to (semantic
    /// adapters only; consumers take theirs from the obligation catalog).
    pub source_paths: Vec<String>,
    /// How long the command may run before its process tree is killed.
    pub timeout: Duration,
    /// Whether a non-zero exit may be a missing local prerequisite (the build
    /// wrappers print recognizable messages for those).
    pub wrapper: bool,
}

/// `(participant, family)` to the command that runs it.
type Lookup = dyn Fn(&str, &str) -> Option<ParticipantCommand>;

/// Which command runs a participant for a family: `(participant, family)` to
/// a command, or `None` when the participant has no runner for the family.
pub struct CommandTable {
    lookup: Box<Lookup>,
}

impl CommandTable {
    /// A table backed by `lookup(participant, family)`.
    pub fn new(lookup: impl Fn(&str, &str) -> Option<ParticipantCommand> + 'static) -> Self {
        Self {
            lookup: Box::new(lookup),
        }
    }

    /// The command for `participant` in `family`.
    pub fn command(&self, participant: &str, family: &str) -> Option<ParticipantCommand> {
        (self.lookup)(participant, family)
    }

    /// The repository's participant runners. `compiler` (`msvc` or
    /// `clang-cl`) selects the CXX, CLI and GUI wrapper build; `preset` is the
    /// GUI wrapper's preset.
    pub fn repository(compiler: &str, preset: &str) -> Self {
        let (compiler, preset) = (compiler.to_owned(), preset.to_owned());
        Self::new(move |participant, family| {
            repository_command(participant, family, &compiler, &preset)
        })
    }
}

fn strings(items: &[&str]) -> Vec<String> {
    items.iter().map(|item| (*item).to_owned()).collect()
}

/// The table behind [`CommandTable::repository`].
fn repository_command(
    participant: &str,
    family: &str,
    compiler: &str,
    preset: &str,
) -> Option<ParticipantCommand> {
    let cargo = |args: &[&str], sources: Vec<String>| ParticipantCommand {
        program: "cargo".into(),
        args: strings(args),
        source_paths: sources,
        timeout: CARGO_TIMEOUT,
        wrapper: false,
    };
    let wrapper = |script: &str, test: &str, extra: &[&str], sources: Vec<String>| {
        let mut args = strings(&["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script]);
        args.extend(strings(&[
            "-Test",
            "-TestOnly",
            "-CTestName",
            test,
            "-Compiler",
            compiler,
        ]));
        args.extend(strings(extra));
        ParticipantCommand {
            program: "pwsh".into(),
            args,
            source_paths: sources,
            timeout: CTEST_TIMEOUT,
            wrapper: true,
        }
    };
    let with_launcher = |mut sources: Vec<String>| {
        // The table itself decides how participants run, so its bytes are
        // part of every receipt's source identity.
        sources.push(LAUNCHER.into());
        sources
    };
    match participant {
        "rust" => Some(match family {
            "crash-log-scan-run" | "autoscan-report" => cargo(
                &[
                    "test",
                    "-p",
                    "classic-scan-presentation",
                    "--test",
                    "scan_run_conformance",
                    "--",
                    "--exact",
                    "writes_scan_run_conformance_receipt",
                    "--nocapture",
                ],
                with_launcher(scan_run_sources(&[
                    "business-logic/classic-scan-presentation/tests/scan_run_conformance.rs",
                    "business-logic/classic-scan-presentation/Cargo.toml",
                ])),
            ),
            "crash-log-scan-launch" => cargo(
                &[
                    "test",
                    "-p",
                    "classic-scan-launch",
                    "--test",
                    "launch_conformance",
                    "--",
                    "--exact",
                    "writes_launch_conformance_receipt",
                    "--nocapture",
                ],
                with_launcher(scan_run_sources(&[
                    "business-logic/classic-scan-launch/tests/launch_conformance.rs",
                    "business-logic/classic-scan-launch/Cargo.toml",
                ])),
            ),
            "user-settings" => cargo(
                &[
                    "test",
                    "-p",
                    "classic-user-settings-core",
                    "--test",
                    "compatibility_contract",
                    "--test",
                    "open_conformance",
                    "--",
                    "--nocapture",
                ],
                with_launcher(strings(&[
                    "business-logic/classic-user-settings-core/tests/open_conformance.rs",
                    "business-logic/classic-user-settings-core/tests/open_conformance/defaults.rs",
                    "business-logic/classic-user-settings-core/tests/compatibility_contract.rs",
                    "business-logic/classic-user-settings-core/src",
                    "business-logic/classic-user-settings-core/Cargo.toml",
                ])),
            ),
            "markdown-rendering" | "report-discovery" => {
                let test = if family == "markdown-rendering" {
                    "markdown::tests::writes_markdown_conformance_receipt"
                } else {
                    "files::tests::writes_report_discovery_conformance_receipt"
                };
                let mut sources = semantic_sources(family);
                sources.extend(strings(&[
                    "cpp-bindings/classic-cpp-bridge/src",
                    "cpp-bindings/classic-cpp-bridge/Cargo.toml",
                    "cpp-bindings/classic-cpp-bridge/build.rs",
                    "tools/enter_vs_dev_shell.ps1",
                ]));
                ParticipantCommand {
                    program: "pwsh".into(),
                    args: vec![
                        "-NoProfile".into(),
                        "-ExecutionPolicy".into(),
                        "Bypass".into(),
                        "-File".into(),
                        "tools/enter_vs_dev_shell.ps1".into(),
                        "-WorkingDirectory".into(),
                        ".".into(),
                        "-Command".into(),
                        format!(
                            "cargo test -p classic-cpp-bridge --lib {test} -- --exact --nocapture"
                        ),
                    ],
                    source_paths: with_launcher(sources),
                    timeout: CARGO_TIMEOUT,
                    wrapper: false,
                }
            }
            _ => cargo(
                &[
                    "test",
                    "-p",
                    "classic-scanlog-core",
                    "--test",
                    "semantic_conformance",
                    "--",
                    "--nocapture",
                ],
                with_launcher(semantic_sources(family)),
            ),
        }),
        "tui" => Some(cargo(
            &[
                "test",
                "-p",
                "classic-tui",
                "--test",
                "scan_run_consumer_conformance",
                "--",
                "--ignored",
                "--exact",
                "writes_tui_scan_run_consumer_receipt",
                "--nocapture",
            ],
            Vec::new(),
        )),
        "cxx" => Some(wrapper(
            "classic-cli/build_cli.ps1",
            "classic-cxx-conformance",
            &[],
            with_launcher(cxx_sources(family)),
        )),
        "cli" => Some(wrapper(
            "classic-cli/build_cli.ps1",
            "classic-cli-consumer-conformance",
            &[],
            Vec::new(),
        )),
        "gui" => Some(wrapper(
            "classic-gui/build_gui.ps1",
            "classic-gui-consumer-conformance",
            &["-Preset", preset],
            Vec::new(),
        )),
        _ => None,
    }
}

/// This module: the command table every repository receipt is bound to.
const LAUNCHER: &str = "xtask/src/conformance/launch.rs";

/// The scan-run owners every scan-run, autoscan and launch receipt depends
/// on, plus `own` (the runner and its manifest).
///
/// A Crash Log Scan Run composes scanlog's run engine, config's Installed
/// YAML Data, scangame's intake and XSE derivation, database lookups, the
/// presentation crate's Display Content, Crash Log Scan Launch and the User
/// Settings it reads; binding all of them keeps a receipt from certifying an
/// owner whose current bytes it never ran.
fn scan_run_sources(own: &[&str]) -> Vec<String> {
    let mut sources = strings(own);
    for owner in [
        "classic-scanlog-core",
        "classic-config-core",
        "classic-database-core",
        "classic-scangame-core",
        "classic-scan-presentation",
        "classic-scan-launch",
        "classic-user-settings-core",
    ] {
        sources.push(format!("business-logic/{owner}/src"));
    }
    sources
}

/// The sources of the shared semantic runner (`classic-scanlog-core`'s
/// `semantic_conformance` test) and the cores it drives. The controlled
/// update service joins them for the two families that use it.
fn semantic_sources(family: &str) -> Vec<String> {
    let mut sources = strings(&[
        "business-logic/classic-scanlog-core/tests/semantic_conformance.rs",
        "business-logic/classic-scanlog-core/tests/semantic_conformance",
        "tools/binding_compliance/platform_path_oracle.ps1",
        "business-logic/classic-scanlog-core/Cargo.toml",
        "CLASSIC Data/databases/CLASSIC Main.yaml",
        "foundation/classic-vocabulary/src",
        "foundation/classic-shared-core/src",
    ]);
    for owner in [
        "classic-xse-core",
        "classic-registry-core",
        "classic-web-core",
        "classic-resource-core",
        "classic-update-core",
        "classic-scanlog-core",
        "classic-database-core",
        "classic-version-registry-core",
        "classic-scangame-core",
        "classic-config-core",
        "classic-user-settings-core",
        "classic-durable-publication",
        "classic-file-io-core",
        "classic-path-core",
        "classic-message-core",
    ] {
        sources.push(format!("business-logic/{owner}/src"));
    }
    if super::update_service::FAMILIES.contains(&family) {
        sources.push("xtask/src/conformance/update_service.rs".into());
    }
    sources
}

/// The native CXX runner and the bridge and cores behind `family`.
fn cxx_sources(family: &str) -> Vec<String> {
    let mut sources = strings(&[
        // Directory expansion fingerprints newly included helpers.
        "classic-cli/tests/conformance",
        "foundation/classic-shared-core/src/yaml",
        "business-logic/classic-registry-core/src",
        "business-logic/classic-web-core/src",
        "business-logic/classic-update-core/src",
        "business-logic/classic-xse-core/src",
        "foundation/classic-vocabulary/src",
        "business-logic/classic-durable-publication/src",
        "classic-cli/CMakeLists.txt",
        "classic-cli/build_cli.ps1",
        "classic-cli/vcpkg.json",
        "cpp-bindings/classic-cpp-bridge/src/scanner.rs",
        "cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_run_observer.h",
        "business-logic/classic-scanlog-core/src/scan_run",
        "business-logic/classic-scan-presentation/src",
    ]);
    match family {
        "user-settings" => sources.extend(strings(&[
            "cpp-bindings/classic-cpp-bridge/src/settings.rs",
            "business-logic/classic-user-settings-core/src",
        ])),
        "crash-log-scan-launch" => sources.extend(strings(&[
            "cpp-bindings/classic-cpp-bridge/src/scanner",
            "business-logic/classic-scan-launch/src",
            "business-logic/classic-user-settings-core/src",
        ])),
        _ => sources.extend(strings(&[
            "cpp-bindings/classic-cpp-bridge/src",
            "business-logic/classic-scanlog-core/src",
            "business-logic/classic-database-core/src",
            "business-logic/classic-version-registry-core/src",
            "business-logic/classic-scangame-core/src",
            "business-logic/classic-config-core/src",
            "business-logic/classic-user-settings-core/src",
            "business-logic/classic-file-io-core/src",
            "business-logic/classic-resource-core/src",
            "business-logic/classic-path-core/src",
            "foundation/classic-shared-core/src",
        ])),
    }
    // Overlapping roots (a directory and a file inside it) would be declared
    // twice; keep the first of each.
    let mut seen = std::collections::BTreeSet::new();
    sources.retain(|source| seen.insert(source.clone()));
    sources
}

/// One participant invocation, ready to run.
#[derive(Debug, Clone)]
pub struct Launch {
    /// The family being run.
    pub family_id: String,
    /// The participant.
    pub participant: String,
    /// The execution instance.
    pub instance: String,
    /// What to run.
    pub command: ParticipantCommand,
    /// The working directory (the repository root).
    pub working_dir: PathBuf,
    /// Variables added to the inherited environment.
    pub env: BTreeMap<String, String>,
    /// The written run plan.
    pub run_plan: PathBuf,
    /// Where the participant must write its receipt.
    pub receipt: PathBuf,
}

/// What happened when a [`Launch`] ran.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Attempt {
    /// The exit code, when the process exited on its own.
    pub exit_code: Option<i32>,
    /// Whether the timeout killed the process tree.
    pub timed_out: bool,
    /// Why the process could not start, if it did not.
    pub launch_error: Option<String>,
    /// Captured standard output.
    pub stdout: String,
    /// Captured standard error.
    pub stderr: String,
}

impl Attempt {
    /// An attempt that exited with `code` and printed nothing.
    pub fn exited(code: i32) -> Self {
        Self {
            exit_code: Some(code),
            ..Self::default()
        }
    }

    /// Whether the command started, finished in time and exited 0.
    pub fn succeeded(&self) -> bool {
        self.exit_code == Some(0) && !self.timed_out && self.launch_error.is_none()
    }

    /// The `attempt.json` document.
    pub(crate) fn document(&self, launch: &Launch) -> serde_json::Value {
        let mut command = vec![launch.command.program.clone()];
        command.extend(launch.command.args.iter().cloned());
        serde_json::json!({
            "schemaVersion": 1,
            "participantId": launch.participant,
            "executionInstanceId": launch.instance,
            "command": command,
            "workingDirectory": ".",
            "timeoutSeconds": launch.command.timeout.as_secs(),
            "exitCode": self.exit_code,
            "timedOut": self.timed_out,
            "launchError": self.launch_error,
            "stdout": self.stdout,
            "stderr": self.stderr,
        })
    }

    /// The attempt's own failures: a command that could not start, timed
    /// out or exited non-zero.
    pub(crate) fn failures(&self, launch: &Launch) -> Vec<ScopedFailure> {
        let at = |kind, message: String| {
            ScopedFailure::at(kind, &launch.participant, &launch.instance, message)
        };
        let mut failures = Vec::new();
        if let Some(error) = &self.launch_error {
            failures.push(at(
                FailureKind::LocalEnvironment,
                format!("the conformance command could not start: {error}"),
            ));
        }
        if self.timed_out {
            failures.push(at(
                FailureKind::AdapterCommand,
                format!(
                    "the conformance command timed out after {} s",
                    launch.command.timeout.as_secs()
                ),
            ));
        }
        if let Some(code) = self.exit_code.filter(|code| *code != 0) {
            let output = format!("{}\n{}", self.stdout, self.stderr).to_lowercase();
            let local = launch.command.wrapper
                && LOCAL_ENVIRONMENT_MARKERS
                    .iter()
                    .any(|marker| output.contains(marker));
            failures.push(if local {
                at(
                    FailureKind::LocalEnvironment,
                    "the conformance command failed because local toolchain or environment prerequisites were unavailable".into(),
                )
            } else {
                at(
                    FailureKind::AdapterCommand,
                    format!("the conformance command exited with code {code}"),
                )
            });
        }
        failures
    }
}

/// Runs `launch` as a child process: output captured, bounded by the
/// command's timeout, and its whole process tree killed on expiry so no
/// descendant can write a receipt after validation starts.
pub fn spawn(launch: &Launch) -> Attempt {
    let mut command = Command::new(&launch.command.program);
    command
        .args(&launch.command.args)
        .current_dir(&launch.working_dir)
        .envs(&launch.env)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // CREATE_NEW_PROCESS_GROUP: the tree can be killed as a unit.
        command.creation_flags(0x0000_0200);
    }
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    let mut child = match command.spawn() {
        Ok(child) => child,
        Err(error) => {
            return Attempt {
                launch_error: Some(error.to_string()),
                ..Attempt::default()
            };
        }
    };
    // Drain both pipes on their own threads so a verbose build cannot fill
    // one and deadlock before the timeout.
    let drain = |pipe: Option<Box<dyn Read + Send>>| {
        std::thread::spawn(move || {
            let mut bytes = Vec::new();
            if let Some(mut pipe) = pipe {
                // A read error leaves what was captured so far.
                let _ = pipe.read_to_end(&mut bytes);
            }
            String::from_utf8_lossy(&bytes).into_owned()
        })
    };
    let stdout = drain(
        child
            .stdout
            .take()
            .map(|pipe| Box::new(pipe) as Box<dyn Read + Send>),
    );
    let stderr = drain(
        child
            .stderr
            .take()
            .map(|pipe| Box::new(pipe) as Box<dyn Read + Send>),
    );
    let deadline = Instant::now() + launch.command.timeout;
    let mut timed_out = false;
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break Some(status),
            Ok(None) if Instant::now() >= deadline => {
                timed_out = true;
                kill_tree(child.id());
                // The tree kill normally ended it; this covers a platform
                // where it could not.
                let _ = child.kill();
                break child.wait().ok();
            }
            Ok(None) => std::thread::sleep(Duration::from_millis(100)),
            Err(_) => break None,
        }
    };
    Attempt {
        exit_code: if timed_out {
            None
        } else {
            status.and_then(|status| status.code())
        },
        timed_out,
        launch_error: None,
        stdout: stdout.join().unwrap_or_default(),
        stderr: stderr.join().unwrap_or_default(),
    }
}

/// Kills the process tree rooted at `pid`.
fn kill_tree(pid: u32) {
    #[cfg(windows)]
    let mut command = {
        let mut command = Command::new("taskkill");
        command.args(["/PID", &pid.to_string(), "/T", "/F"]);
        command
    };
    #[cfg(not(windows))]
    let mut command = {
        // The child leads its own process group, so the negative PID names
        // the whole group.
        let mut command = Command::new("kill");
        command.args(["-KILL", &format!("-{pid}")]);
        command
    };
    // Failure here means the tree already exited; `Child::kill` follows.
    let _ = command.stdout(Stdio::null()).stderr(Stdio::null()).status();
}

/// The repository-relative rendering of `path` when it is under `root`.
pub(crate) fn display(root: &Path, path: &Path) -> String {
    crate::RepoRoot::new(root).relative(path)
}

#[cfg(test)]
#[path = "launch_tests.rs"]
mod tests;
