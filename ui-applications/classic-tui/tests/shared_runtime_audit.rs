//! Contract audit for the shared Tokio runtime rule (`AGENTS.md` rule 5).
//!
//! Every TUI background workflow — including resuming a Local Ignore recovery continuation — must
//! run on the single runtime owned by `classic_shared_core`. A second runtime would give a resumed
//! run a different scheduler from the scan it continues, so this is pinned here rather than left
//! to review.
//!
//! The checks count spawn sites rather than naming functions, so a new call inside an audited file
//! is covered automatically. `include_str!` needs literal paths, so the file list itself cannot be
//! globbed; `the_audit_covers_every_declared_workflow_module` closes that gap by failing when
//! `app.rs` declares a workflow module this file does not list.

const APP_RS: &str = include_str!("../src/app.rs");
const BACKUP_WORKFLOW_RS: &str = include_str!("../src/app/backup_workflow.rs");
const RESULTS_WORKFLOW_RS: &str = include_str!("../src/app/results_workflow.rs");
const UPDATE_WORKFLOW_RS: &str = include_str!("../src/app/update_workflow.rs");
const EVENT_RS: &str = include_str!("../src/event.rs");
const MAIN_RS: &str = include_str!("../src/main.rs");

/// Returns every TUI source file allowed to dispatch background work.
fn dispatching_sources() -> [(&'static str, &'static str); 6] {
    [
        ("app.rs", APP_RS),
        ("app/backup_workflow.rs", BACKUP_WORKFLOW_RS),
        ("app/results_workflow.rs", RESULTS_WORKFLOW_RS),
        ("app/update_workflow.rs", UPDATE_WORKFLOW_RS),
        ("event.rs", EVENT_RS),
        ("main.rs", MAIN_RS),
    ]
}

#[test]
fn the_tui_never_constructs_its_own_async_runtime() {
    for (name, source) in dispatching_sources() {
        for forbidden in [
            "Runtime::new",
            "runtime::Builder",
            "#[tokio::main]",
            "block_on(",
        ] {
            assert!(
                !source.contains(forbidden),
                "{name} must not use `{forbidden}`; background work belongs on \
                 classic_shared_core::get_runtime()"
            );
        }
    }
}

#[test]
fn every_tui_spawn_targets_the_shared_runtime() {
    for (name, source) in dispatching_sources() {
        let spawns = source.matches(".spawn(").count();
        let shared_spawns = source.matches("get_runtime().spawn(").count();
        assert_eq!(
            spawns, shared_spawns,
            "{name} spawns {spawns} task(s) but only {shared_spawns} target the shared runtime"
        );
    }
}

#[test]
fn the_audit_covers_every_declared_workflow_module() {
    let audited = dispatching_sources();
    for line in APP_RS.lines() {
        let Some(module) = line
            .trim()
            .strip_prefix("mod ")
            .and_then(|rest| rest.strip_suffix(';'))
        else {
            continue;
        };
        // The sibling unit-test module required by AGENTS.md rule 11 is declared the same way but
        // resolves to `app_tests.rs`, not `app/tests.rs`, and dispatches no background work.
        if module == "tests" {
            continue;
        }
        let expected = format!("app/{module}.rs");
        assert!(
            audited.iter().any(|(name, _)| *name == expected),
            "app.rs declares `mod {module};` but `{expected}` is not audited here; add it to \
             dispatching_sources() so its background work stays on the shared runtime"
        );
    }
}

#[test]
fn local_ignore_recovery_resume_is_dispatched_like_every_other_workflow() {
    assert!(
        APP_RS.contains("fn resume_local_ignore_recovery"),
        "the recovery resume seam should stay a named function in app.rs"
    );
    assert!(
        APP_RS.contains("get_runtime().spawn("),
        "app.rs should dispatch its background work through the shared runtime"
    );
}
