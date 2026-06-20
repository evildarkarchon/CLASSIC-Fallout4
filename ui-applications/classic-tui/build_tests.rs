use super::extract_classic_info_version;

fn yaml_with_version(version: &str) -> String {
    format!("CLASSIC_Info:\n  version: {version}\n")
}

#[test]
fn extract_classic_info_version_rejects_leading_zero_components() {
    for bad in [
        "v01.2.3", "v1.02.3", "v1.2.03", "01.2.3", "1.02.3", "1.2.03",
    ] {
        let err = extract_classic_info_version(&yaml_with_version(bad))
            .expect_err("leading-zero component must be rejected");

        assert!(
            err.contains("leading zero"),
            "reason must name the leading-zero rule for `{bad}`, got: {err}",
        );
    }
}

#[test]
fn extract_classic_info_version_rejects_components_outside_u32_range() {
    for bad in ["v4294967296.0.0", "v1.4294967296.0", "v1.0.4294967296"] {
        let err = extract_classic_info_version(&yaml_with_version(bad))
            .expect_err("out-of-range component must be rejected");

        assert!(
            err.contains("32-bit"),
            "reason must name the 32-bit range rule for `{bad}`, got: {err}",
        );
    }
}

#[test]
fn extract_classic_info_version_accepts_valid_zero_and_max_components() {
    for good in ["v0.0.0", "v9.0.1", "v4294967295.0.0"] {
        let version = extract_classic_info_version(&yaml_with_version(good))
            .unwrap_or_else(|err| panic!("valid version `{good}` should extract: {err}"));

        assert_eq!(version, good.trim_start_matches('v'));
    }
}
