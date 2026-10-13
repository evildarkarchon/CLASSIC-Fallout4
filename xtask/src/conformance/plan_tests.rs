//! Run plans: input-only content, canonical writing, and authentication of a
//! plan read back against the current tree.

use super::super::tests::Demo;
use super::*;

#[test]
fn a_plan_is_input_only_and_bound_to_its_sources() {
    let demo = Demo::new();
    let (_, prepared, _) = demo.prepare();
    let plan = demo.rust_plan(&prepared);
    let text = String::from_utf8(canonical_bytes(&plan)).unwrap();
    assert!(!text.contains("\"expected\""), "{text}");
    assert_eq!(plan["sourcePaths"], json!(["runner/demo.rs"]));
    assert_eq!(plan["participant"]["role"], "semantic-adapter");
    assert_eq!(plan["scenarios"].as_array().unwrap().len(), 2);
    let fixture = std::path::PathBuf::from(plan["fixtures"]["one"].as_str().unwrap());
    assert!(fixture.is_absolute() && fixture.is_file(), "{fixture:?}");
    assert!(!plan["fixtureRoot"].as_str().unwrap().starts_with(r"\\?\"));
    let identity = plan["invocation"]["sourceIdentity"].as_str().unwrap();
    assert!(
        super::super::receipt::is_source_identity(identity),
        "{identity}"
    );
    assert!(super::super::receipt::is_sha256(
        &prepared.expectation_digest
    ));
    assert_eq!(
        plan["invocation"]["runPlanDigest"].as_str().unwrap(),
        run_plan_digest(&plan)
    );

    // Two invocations differ only in their identity.
    let again = demo.rust_plan(&prepared);
    assert_ne!(plan["invocation"]["id"], again["invocation"]["id"]);
    assert_eq!(
        plan["invocation"]["sourceIdentity"],
        again["invocation"]["sourceIdentity"]
    );
}

#[test]
fn a_cxx_plan_carries_only_its_selected_scenarios() {
    let demo = Demo::new();
    let (loaded, prepared, applicability) = demo.prepare();
    let cxx = applicability
        .executions(&loaded.pack)
        .into_iter()
        .find(|execution| execution.participant == "cxx")
        .expect("demo enrols cxx");
    assert_eq!(cxx.evidence, ["first"]);
    let plan = build(
        &demo.root,
        &prepared,
        &PlanRequest {
            participant: "cxx".into(),
            role: Role::SemanticAdapter,
            instance: cxx.instance,
            source_paths: vec!["runner".into()],
            payload: Payload::Scenarios(cxx.evidence),
        },
    )
    .unwrap();
    let ids: Vec<&str> = plan["scenarios"]
        .as_array()
        .unwrap()
        .iter()
        .map(|scenario| scenario["id"].as_str().unwrap())
        .collect();
    assert_eq!(ids, ["first"]);
}

#[test]
fn source_paths_must_exist_inside_the_repository() {
    let demo = Demo::new();
    let (_, prepared, _) = demo.prepare();
    for paths in [
        vec!["missing.rs"],
        vec!["../outside"],
        vec!["runner", "runner"],
    ] {
        let request = PlanRequest {
            participant: "rust".into(),
            role: Role::SemanticAdapter,
            instance: "rust".into(),
            source_paths: paths.iter().map(|path| (*path).to_owned()).collect(),
            payload: Payload::Scenarios(vec!["first".into()]),
        };
        assert!(build(&demo.root, &prepared, &request).is_err(), "{paths:?}");
    }
}

#[test]
fn a_written_plan_reloads_only_while_it_and_its_sources_are_unchanged() {
    let demo = Demo::new();
    let (_, prepared, _) = demo.prepare();
    let plan = demo.rust_plan(&prepared);
    let written = write(&demo.root.join("artifacts"), &plan).unwrap();
    assert!(written.run_plan.ends_with("run_plan.json"));
    assert!(
        !written.receipt.exists(),
        "the receipt path is only reserved"
    );
    assert_eq!(
        std::fs::read(&written.run_plan).unwrap(),
        canonical_bytes(&plan)
    );
    let expected = |_: &PlanParticipant| {
        Ok((
            Payload::Scenarios(vec!["first".into(), "second".into()]),
            None,
        ))
    };
    assert!(reload(&demo.root, &prepared, &written.run_plan, expected).is_ok());

    // Narrowing the plan breaks the pack-owned payload.
    let narrowed = |_: &PlanParticipant| Ok((Payload::Scenarios(vec!["first".into()]), None));
    let error = reload(&demo.root, &prepared, &written.run_plan, narrowed).unwrap_err();
    assert!(error.contains("scenarios"), "{error}");

    // Editing a participant source changes the source identity.
    std::fs::write(demo.root.join("runner/demo.rs"), "// changed\n").unwrap();
    let error = reload(&demo.root, &prepared, &written.run_plan, expected).unwrap_err();
    assert!(error.contains("source identity"), "{error}");
    std::fs::write(demo.root.join("runner/demo.rs"), "// runner\n").unwrap();

    // Tampering with the plan itself breaks its digest.
    let mut tampered = plan.clone();
    tampered["sourcePaths"] = json!(["runner"]);
    std::fs::write(&written.run_plan, canonical_bytes(&tampered)).unwrap();
    let error = reload(&demo.root, &prepared, &written.run_plan, expected).unwrap_err();
    assert!(error.contains("digest"), "{error}");

    // Non-canonical bytes are refused before anything else.
    std::fs::write(&written.run_plan, serde_json::to_vec_pretty(&plan).unwrap()).unwrap();
    let error = reload(&demo.root, &prepared, &written.run_plan, expected).unwrap_err();
    assert!(error.contains("canonical"), "{error}");
}

#[test]
fn uuids_are_version_4_and_distinct() {
    let first = uuid_v4();
    let second = uuid_v4();
    assert_ne!(first, second);
    for uuid in [first, second] {
        assert_eq!(uuid.len(), 36);
        assert_eq!(&uuid[14..15], "4", "{uuid}");
        assert!(matches!(&uuid[19..20], "8" | "9" | "a" | "b"), "{uuid}");
    }
}

#[test]
fn native_paths_drop_the_windows_verbatim_prefix() {
    assert_eq!(native(Path::new(r"\\?\C:\repo\x")), r"C:\repo\x");
    assert_eq!(
        native(Path::new(r"\\?\UNC\server\share\x")),
        r"\\server\share\x"
    );
    assert_eq!(native(Path::new("/tmp/x")), "/tmp/x");
}
