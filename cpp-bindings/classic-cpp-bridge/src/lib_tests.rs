//! Test-host receipt support for private bridge-owned interface implementations.

use serde_json::{Value, json};
use std::io::Write;
use std::path::Path;

/// Execute input-only fixtures and publish a fresh receipt from the actual owning module.
pub(crate) fn interface_receipt(family: &str, observe: impl Fn(&Value) -> Value) {
    let (Some(plan_path), Some(output_path)) = (
        std::env::var_os("CLASSIC_CONFORMANCE_RUN_PLAN"),
        std::env::var_os("CLASSIC_CONFORMANCE_OUTPUT"),
    ) else {
        return;
    };
    let plan: Value =
        serde_json::from_slice(&std::fs::read(plan_path).expect("read plan")).expect("decode plan");
    assert_eq!(plan["familyId"], family);
    assert_eq!(plan["participant"]["id"], "rust");
    let scenarios = plan["scenarios"].as_array().expect("scenarios").iter().map(|scenario| {
        assert!(scenario.get("expected").is_none(), "adapter plans cannot contain output oracles");
        let reference = scenario["input"]["fixtureRef"].as_str().expect("fixture reference");
        assert_eq!(scenario["fixtureRefs"], json!([reference]));
        let fixture: Value = serde_json::from_slice(&std::fs::read(plan["fixtures"][reference].as_str().expect("fixture path")).expect("read fixture")).expect("decode fixture");
        json!({"id": scenario["id"], "executionStatus": "completed", "capabilityIds": scenario["capabilityIds"], "observation": observe(&fixture), "failure": null})
    }).collect::<Vec<_>>();
    let mut receipt = json!({"runner": {"id": "classic-cpp-bridge-rust-reference", "version": 1, "platform": "windows", "toolchain": "rust"}, "scenarios": scenarios});
    for key in [
        "schemaVersion",
        "familyId",
        "familyVersion",
        "expectationDigest",
        "participant",
        "invocation",
    ] {
        receipt[key] = plan[key].clone();
    }
    let output = Path::new(&output_path);
    let mut temporary = tempfile::NamedTempFile::new_in(output.parent().expect("output parent"))
        .expect("fresh temporary receipt");
    temporary
        .write_all(
            serde_json::to_string(&receipt)
                .expect("encode receipt")
                .as_bytes(),
        )
        .expect("write receipt");
    temporary
        .persist_noclobber(output)
        .expect("publish fresh receipt");
}

/// Encode exact file bytes without UTF-8 replacement or newline normalization.
pub(crate) fn bytes_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// Inventory all actual fixture-owned entries so unexpected writes and deletions are visible.
pub(crate) fn file_snapshot(root: &Path) -> Value {
    let mut pending = vec![root.to_path_buf()];
    let mut files = Vec::new();
    let mut directories = Vec::new();
    while let Some(directory) = pending.pop() {
        for entry in std::fs::read_dir(directory).unwrap() {
            let entry = entry.unwrap();
            let path = entry.path();
            let kind = entry.file_type().unwrap();
            assert!(!kind.is_symlink(), "unexpected fixture symlink");
            let relative = path
                .strip_prefix(root)
                .unwrap()
                .to_string_lossy()
                .replace('\\', "/");
            if kind.is_dir() {
                directories.push(relative);
                pending.push(path);
            } else {
                files.push(
                    json!({"path": relative, "hex": bytes_hex(&std::fs::read(path).unwrap())}),
                );
            }
        }
    }
    directories.sort();
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    json!({"files": files, "directories": directories})
}
