use super::*;

fn finding(path: &str, line: usize) -> Finding {
    Finding {
        path: path.to_owned(),
        line,
        rule: "orphan-export",
        message: "classic::m::f has no production caller".to_owned(),
    }
}

#[test]
fn finding_renders_as_path_line_rule_message() {
    assert_eq!(
        finding("cpp-bindings/classic-cpp-bridge/src/m.rs", 12).to_string(),
        "cpp-bindings/classic-cpp-bridge/src/m.rs:12: orphan-export: classic::m::f has no production caller"
    );
}

#[test]
fn finding_constructors_fill_every_field() {
    assert_eq!(
        Finding::new(
            "cpp-bindings/classic-cpp-bridge/src/m.rs",
            12,
            "orphan-export",
            "classic::m::f has no production caller",
        ),
        finding("cpp-bindings/classic-cpp-bridge/src/m.rs", 12)
    );
    // A whole-file finding points at line 1.
    assert_eq!(
        Finding::file(
            "a.rs",
            "orphan-export",
            String::from("classic::m::f has no production caller")
        ),
        finding("a.rs", 1)
    );
}

#[test]
fn outcome_without_findings_is_a_pass_with_the_pass_summary() {
    let outcome = Outcome::from_findings(Vec::new(), "all good".into(), "bad".into());
    assert_eq!(
        outcome,
        Outcome::Pass {
            summary: "all good".into(),
            report: None,
        }
    );
}

#[test]
fn outcome_with_findings_sorts_them_by_path_then_line() {
    let outcome = Outcome::from_findings(
        vec![finding("b.rs", 1), finding("a.rs", 9), finding("a.rs", 2)],
        "all good".into(),
        "bad".into(),
    );
    assert_eq!(
        outcome,
        Outcome::Fail {
            findings: vec![finding("a.rs", 2), finding("a.rs", 9), finding("b.rs", 1)],
            summary: "bad".into(),
        }
    );
}
