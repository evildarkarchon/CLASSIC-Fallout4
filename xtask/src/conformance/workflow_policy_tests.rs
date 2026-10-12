use super::*;

const WORKFLOW: &str = "on:\n  workflow_call:\n\njobs:\n  lint:\n    runs-on: windows-latest\n    steps:\n      - uses: actions/checkout@v6\n\n      - name: Check\n        run: |\n          one\n          two\n  test:\n    steps: []\n";

fn workflow(text: &str) -> Workflow {
    let dir = tempfile::tempdir().expect("temp dir");
    let path = dir.path().join(CI_RUST);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(&path, text).unwrap();
    Workflow::load(&RepoRoot::new(dir.path()), CI_RUST)
        .expect("readable")
        .expect("valid workflow")
}

#[test]
fn findings_resolve_to_job_and_step_lines() {
    let workflow = workflow(WORKFLOW);
    assert_eq!(workflow.finding("/jobs/lint", String::new()).line, 5);
    assert_eq!(
        workflow.finding("/jobs/lint/steps/0", String::new()).line,
        8
    );
    assert_eq!(
        workflow.finding("/jobs/lint/steps/1", String::new()).line,
        10
    );
    assert_eq!(workflow.finding("/jobs/test", String::new()).line, 14);
    // An unknown node falls back to its nearest recorded ancestor.
    assert_eq!(
        workflow.finding("/jobs/lint/steps/9", String::new()).line,
        7
    );
}

#[test]
fn workflow_expressions_stay_plain_strings() {
    let workflow = workflow(
        "jobs:\n  a:\n    if: ${{ !cancelled() }}\n    needs: [x, y]\n    timeout-minutes: 360\n",
    );
    let job = &workflow.yaml["jobs"]["a"];
    assert_eq!(text(&job["if"]), Some(NOT_CANCELLED));
    assert_eq!(job["timeout-minutes"].as_i64(), Some(360));
    assert_eq!(job["needs"].as_vec().map(Vec::len), Some(2));
}

#[test]
fn duplicate_keys_and_bad_yaml_are_findings() {
    let dir = tempfile::tempdir().expect("temp dir");
    let path = dir.path().join(CI_RUST);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(&path, "jobs:\n  a: {}\n  a: {}\n").unwrap();
    let finding = Workflow::load(&RepoRoot::new(dir.path()), CI_RUST)
        .expect("readable")
        .err()
        .expect("duplicate keys are rejected");
    assert!(finding.message.contains("duplicated key"), "{finding}");
    assert!(
        Workflow::load(&RepoRoot::new(dir.path()), CI_CPP)
            .unwrap()
            .is_err()
    );
}

#[test]
fn presets_are_read_from_command_tokens() {
    assert_eq!(
        presets("pwsh build_gui.ps1 -Test -Preset ci-system-qt -TestOnly"),
        ["ci-system-qt"]
    );
    assert!(presets("pwsh build_gui.ps1 -Test").is_empty());
}
