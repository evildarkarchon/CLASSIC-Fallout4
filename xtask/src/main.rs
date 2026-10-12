//! `cargo xtask <command>`: thin `clap` front end over the `xtask` library.
//!
//! Exit codes: 0 pass, 1 failed check or operational failure, 2 usage error
//! (clap exits with 2 on its own for bad arguments).

use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand};
use xtask::{Outcome, RepoRoot, cxx_bridge_gate, user_settings_ownership};

/// CLASSIC repository tooling.
///
/// Exit codes: 0 pass, 1 failed check or operational failure, 2 usage error.
/// Findings are printed to stderr as `path:line: rule: message`, followed by a
/// summary; a pass prints `OK: <summary>` to stdout.
#[derive(Debug, Parser)]
#[command(name = "xtask", bin_name = "cargo xtask", version)]
struct Cli {
    /// Repository root to inspect. Defaults to the directory that contains
    /// the `xtask/` crate.
    #[arg(long, global = true, value_name = "DIR")]
    repo_root: Option<PathBuf>,

    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Fail on CXX bridge exports that no CLI or GUI production source calls.
    ///
    /// Parses every `#[cxx::bridge]` module in cpp-bindings/classic-cpp-bridge/src
    /// and scans the .cpp/.h/.hpp files under classic-cli/src and
    /// classic-gui/src. A function survives only when production code names it
    /// as `classic::<module>::name` or `<alias>::name` (with
    /// `namespace <alias> = classic::<module>;`). Types survive only when a
    /// surviving function reaches them. Any other reference to a bridge
    /// namespace (for example `using namespace classic::<module>;`) fails as an
    /// unsupported reference form.
    CxxBridgeGate(cxx_bridge_gate::Args),
    /// Fail when anything but classic-user-settings-core interprets User
    /// Settings.
    ///
    /// Audits production .rs/.cpp/.h/.hpp files under foundation,
    /// business-logic, cpp-bindings, classic-cli, classic-gui and
    /// ui-applications (test, build and dependency directories and
    /// *_tests.rs files are skipped; xtask/ is never audited). Fails on raw
    /// `CLASSIC_Settings` keys outside the owner, on the retired
    /// `ClassicConfig`/`PathConfig` models or a `Settings` variant on a
    /// generic YAML enum, and on runtime reads of the `default_settings`
    /// compatibility mirror outside its generator. Comments are ignored;
    /// string literals are audited.
    UserSettingsOwnership(user_settings_ownership::Args),
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let result = RepoRoot::discover(cli.repo_root).and_then(|root| match cli.command {
        Command::CxxBridgeGate(args) => cxx_bridge_gate::run(&root, args),
        Command::UserSettingsOwnership(args) => user_settings_ownership::run(&root, args),
    });
    match result {
        Ok(outcome) => render(outcome),
        Err(error) => {
            eprintln!("error: {error:#}");
            ExitCode::FAILURE
        }
    }
}

/// Prints `outcome` per the output contract and returns its exit code.
fn render(outcome: Outcome) -> ExitCode {
    match outcome {
        Outcome::Pass { summary } => {
            println!("OK: {summary}");
            ExitCode::SUCCESS
        }
        Outcome::Fail { findings, summary } => {
            for finding in &findings {
                eprintln!("{finding}");
            }
            eprintln!("{summary}");
            ExitCode::FAILURE
        }
    }
}
