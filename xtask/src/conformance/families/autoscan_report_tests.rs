use serde_json::json;

use super::super::tests::PackRepo;
use super::super::{Stage, normalize_observation};
use super::*;

/// A one-scenario autoscan pack whose report names `template`.
fn pack(template: &str) -> Value {
    json!({
        "schemaVersion": 1,
        "familyId": "autoscan-report",
        "familyVersion": 1,
        "domainOwner": {"rustCrate": "classic-demo-core"},
        "fixtureRoot": "goldens",
        "fixtures": {"log": "input/crash.log"},
        "capabilities": [],
        "scenarios": [{
            "id": "one",
            "action": "autoscan-report.execute",
            "capabilityIds": ["autoscan-report.execute"],
            "fixtureRefs": ["log"],
            "input": {},
            "expected": {
                "semanticInputs": {"fcxMode": true},
                "durableEffects": {"reports": [{"path": "crash-AUTOSCAN.md", "template": template}]}
            },
            "normalization": {"rootRelativePaths": false, "unorderedPaths": [], "excludedPaths": []}
        }],
        "consumerObligations": []
    })
}

fn repo(template: &str) -> PackRepo {
    PackRepo::temp(
        &[
            ("goldens/input/crash.log", b"log"),
            ("goldens/expected.md", b"ab"),
            ("outside.md", b"x"),
        ],
        pack(template),
    )
}

#[test]
fn templates_compile_to_the_golden_byte_identity() {
    let compiled = repo("expected.md").compile().expect("compiles");
    assert_eq!(
        compiled.expected[0]["durableEffects"]["reports"],
        json!([{
            "path": "crash-AUTOSCAN.md",
            "bytesHex": "6162",
            // SHA-256 of "ab".
            "sha256": "fb8e20fc2e4c3f248c60c39bd652f3c1347298bb977b8b4d5903b85055620603",
            "byteLength": 2
        }])
    );
    assert_eq!(compiled.oracles, ["goldens/expected.md"]);
}

#[test]
fn templates_must_be_contained_goldens_that_are_not_inputs() {
    for (template, text) in [
        ("../outside.md", "contained relative path"),
        ("missing.md", "existing regular file"),
        ("input/crash.log", "cannot be an adapter input fixture"),
    ] {
        let error = repo(template).compile().unwrap_err();
        assert!(error.contains(text), "{template}: {error}");
    }
}

/// Real pack: the compiled byte identities recorded from the retired Python
/// engine (the goldens are binary in `.gitattributes`, so their bytes are the
/// same on every checkout).
#[test]
fn the_real_pack_compiles_to_the_python_engine_identities() {
    let compiled = PackRepo::real("autoscan_report")
        .compile()
        .expect("compiles");
    let identities: Vec<(String, u64)> = compiled
        .expected
        .iter()
        .map(|expected| {
            let report = &expected["durableEffects"]["reports"][0];
            assert!(report.get("template").is_none());
            (
                report["sha256"].as_str().unwrap().to_owned(),
                report["byteLength"].as_u64().unwrap(),
            )
        })
        .collect();
    let empty = "ef8c70e937d631b965d470c0e8680c82ecaeda2acc0c1152c5d977beac51fd96";
    let populated = "9b258a5731d425ff27a043ae6bd3e9e33ee56fcb56b9f3dd074c7be824c67b10";
    let fcx = "f5326d5c4a7b82365ff3731dabfc42a29dbf0dbaaf49273af4b5c64d78af99ee";
    let without = "5efae52345961bc07cccae2566d434b6cdec74e3f4ab196ff4adbf97ed4bf756";
    let expected: Vec<(String, u64)> = [
        (empty, 992),
        (populated, 3772),
        (fcx, 2991),
        (without, 3745),
        (without, 3745),
        (without, 3745),
    ]
    .into_iter()
    .map(|(hash, length)| (hash.to_owned(), length))
    .collect();
    assert_eq!(identities, expected);
    let goldens = "tests/fixtures/autoscan_report_goldens/cases";
    assert_eq!(
        compiled.oracles,
        [
            format!("{goldens}/empty/expected.md"),
            format!("{goldens}/populated/expected.md"),
            format!("{goldens}/fcx/expected.md"),
            format!("{goldens}/populated/expected-without-values.md"),
            format!("{goldens}/populated/expected-without-values.md"),
            format!("{goldens}/populated/expected-without-values.md"),
        ]
    );
}

/// An expected observation whose one report holds `text`.
fn expected(fcx_mode: bool, text: &str) -> Map<String, Value> {
    let data = text.as_bytes();
    json!({
        "executionRoot": "{{EXECUTION_ROOT}}",
        "semanticInputs": {"fcxMode": fcx_mode},
        "durableEffects": {"reports": [{
            "path": "r.md",
            "bytesHex": digest::hex(data),
            "sha256": digest::sha256_hex(data),
            "byteLength": data.len()
        }]}
    })
    .as_object()
    .cloned()
    .unwrap()
}

fn observed(root: &str) -> Map<String, Value> {
    json!({"executionRoot": root}).as_object().cloned().unwrap()
}

/// The expanded report text.
fn expanded(fcx_mode: bool, text: &str, root: &str) -> Result<String, NormalizationError> {
    let (expected, _) = normalize_observation(
        "autoscan-report",
        "autoscan-report.execute",
        Stage::BeforeDeclared,
        expected(fcx_mode, text),
        observed(root),
    )?;
    assert_eq!(expected["executionRoot"], json!(root));
    let report = &expected["durableEffects"]["reports"][0];
    let data = decode_hex(report["bytesHex"].as_str().unwrap()).unwrap();
    assert_eq!(report["byteLength"], json!(data.len()));
    assert_eq!(report["sha256"], json!(digest::sha256_hex(&data)));
    Ok(String::from_utf8(data).unwrap())
}

/// Expected expansions were recorded from Python's `pathlib` (the retired
/// expander's renderer).
#[test]
fn fcx_tokens_expand_with_the_observed_root() {
    let text = "{{FCX_GAME_ROOT}}|{{FCX_DOCUMENTS_ROOT}}|{{PATH_SEPARATOR}}";
    for (root, rendered) in [
        (
            r"C:\Temp\run",
            r"C:\Temp\run\fcx-game|C:\Temp\run\fcx-documents|\",
        ),
        (
            "C:/Temp//run/./",
            r"C:\Temp\run\fcx-game|C:\Temp\run\fcx-documents|\",
        ),
        (r"c:\", r"c:\fcx-game|c:\fcx-documents|\"),
        (
            r"\\host\share\run",
            r"\\host\share\run\fcx-game|\\host\share\run\fcx-documents|\",
        ),
        (
            r"\\host\share",
            r"\\host\share\fcx-game|\\host\share\fcx-documents|\",
        ),
        ("//net/run", r"\\net\run\fcx-game|\\net\run\fcx-documents|\"),
        ("/tmp/run/", "/tmp/run/fcx-game|/tmp/run/fcx-documents|/"),
        ("/", "/fcx-game|/fcx-documents|/"),
    ] {
        assert_eq!(
            expanded(true, text, root).as_deref(),
            Ok(rendered),
            "{root}"
        );
    }
    // Outside FCX mode the expected bytes are kept as authored.
    assert_eq!(expanded(false, text, "/tmp").as_deref(), Ok(text));
}

/// The real FCX-mode golden, expanded at a Windows and a POSIX root; the
/// identities were recorded from the retired Python expander.
#[test]
fn the_real_fcx_golden_expands_like_the_python_engine() {
    let compiled = PackRepo::real("autoscan_report")
        .compile()
        .expect("compiles");
    for (root, sha256, length) in [
        (
            r"C:\Temp\run",
            "7f9d69d9acc2e02c7963082b36b46edbe5e85f5e64886d438b6301232ac061e5",
            2961,
        ),
        (
            "/tmp/run",
            "ac50590c4dc35231d56691b9c5ef567265413a1a093cff59c07129c7051ad4ea",
            2940,
        ),
    ] {
        let (expected, _) = normalize_observation(
            "autoscan-report",
            "autoscan-report.execute",
            Stage::BeforeDeclared,
            compiled.expected[2].clone(),
            observed(root),
        )
        .expect("expands");
        let report = &expected["durableEffects"]["reports"][0];
        assert_eq!(report["sha256"], json!(sha256), "{root}");
        assert_eq!(report["byteLength"], json!(length), "{root}");
    }
}

#[test]
fn malformed_execution_roots_are_normalization_failures() {
    // Incomplete UNC roots are rejected rather than rendered as pathlib's
    // drive-only oddities (a deliberate deviation; see `RootPath`).
    for root in [
        "",
        "relative/run",
        "C:relative",
        "/tmp/../etc",
        "/tmp/{x}",
        "/tmp\nx",
        "//tmp",
        "///tmp",
        r"\\host",
    ] {
        let error = expanded(true, "x", root).unwrap_err();
        assert_eq!(error.path, "$.executionRoot", "{root:?}");
    }
    let error = normalize_observation(
        "autoscan-report",
        "autoscan-report.execute",
        Stage::BeforeDeclared,
        expected(true, "x"),
        Map::new(),
    )
    .unwrap_err();
    assert_eq!(error.path, "$.executionRoot");
}
