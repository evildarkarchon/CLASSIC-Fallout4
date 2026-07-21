use super::*;

#[test]
fn first_party_installation_root_uses_cwd_when_executable_is_not_beside_data() {
    let executable_layout = tempfile::tempdir().expect("executable layout should be created");
    let cwd_layout = tempfile::tempdir().expect("CWD layout should be created");
    std::fs::create_dir(cwd_layout.path().join("CLASSIC Data"))
        .expect("CWD CLASSIC Data should be created");

    let resolved =
        resolve_native_installation_root(Some(executable_layout.path()), Some(cwd_layout.path()));

    assert_eq!(resolved.as_deref(), Some(cwd_layout.path()));
}

#[test]
fn first_party_installation_root_supports_native_parent_and_install_layouts() {
    let parent_layout = tempfile::tempdir().expect("parent layout should be created");
    let executable_dir = parent_layout.path().join("bin");
    std::fs::create_dir_all(&executable_dir).expect("executable directory should be created");
    std::fs::create_dir(parent_layout.path().join("CLASSIC Data"))
        .expect("parent CLASSIC Data should be created");

    let resolved_parent = resolve_native_installation_root(Some(&executable_dir), None);
    assert_eq!(resolved_parent.as_deref(), Some(parent_layout.path()));

    std::fs::remove_dir(parent_layout.path().join("CLASSIC Data"))
        .expect("parent CLASSIC Data should be removed");
    let install_root = parent_layout.path().join("install");
    std::fs::create_dir_all(install_root.join("CLASSIC Data"))
        .expect("install CLASSIC Data should be created");

    let resolved_install = resolve_native_installation_root(Some(&executable_dir), None);
    assert_eq!(resolved_install.as_deref(), Some(install_root.as_path()));
}

#[test]
fn parse_yaml_data_tag_base_date() {
    assert_eq!(
        parse_yaml_data_tag("yaml-data-v2026.04.17", "yaml-data-v"),
        Some((2026, 4, 17, 0))
    );
}

#[test]
fn parse_yaml_data_tag_single_digit_suffix() {
    assert_eq!(
        parse_yaml_data_tag("yaml-data-v2026.04.17.9", "yaml-data-v"),
        Some((2026, 4, 17, 9))
    );
}

#[test]
fn parse_yaml_data_tag_two_digit_suffix() {
    assert_eq!(
        parse_yaml_data_tag("yaml-data-v2026.04.17.10", "yaml-data-v"),
        Some((2026, 4, 17, 10))
    );
}

#[test]
fn parse_yaml_data_tag_ten_beats_nine_numerically() {
    // Regression for the Codex adversarial review finding: raw string
    // compare would pick `.2` over `.10`; parsed-numeric ordering must
    // rank `.10 > .9 > .2 > <no suffix>`.
    let ten = parse_yaml_data_tag("yaml-data-v2026.04.17.10", "yaml-data-v").unwrap();
    let nine = parse_yaml_data_tag("yaml-data-v2026.04.17.9", "yaml-data-v").unwrap();
    let two = parse_yaml_data_tag("yaml-data-v2026.04.17.2", "yaml-data-v").unwrap();
    let base = parse_yaml_data_tag("yaml-data-v2026.04.17", "yaml-data-v").unwrap();
    assert!(ten > nine);
    assert!(nine > two);
    assert!(two > base);
}

#[test]
fn parse_yaml_data_tag_rejects_wrong_prefix() {
    assert_eq!(
        parse_yaml_data_tag("v9.1.0", "yaml-data-v"),
        None,
        "binary release tags must not match the yaml-data prefix"
    );
}

#[test]
fn parse_yaml_data_tag_rejects_non_numeric_components() {
    assert_eq!(
        parse_yaml_data_tag("yaml-data-vXXXX.04.17", "yaml-data-v"),
        None
    );
    assert_eq!(
        parse_yaml_data_tag("yaml-data-v2026.04.17.rc1", "yaml-data-v"),
        None
    );
}

#[test]
fn parse_yaml_data_tag_rejects_trailing_garbage() {
    assert_eq!(
        parse_yaml_data_tag("yaml-data-v2026.04.17.2.oops", "yaml-data-v"),
        None,
        "extra dotted components must not be silently ignored"
    );
}

#[test]
fn unique_tmp_name_never_repeats_within_a_process() {
    // In-process uniqueness is guaranteed by the AtomicU64 counter; this
    // test protects the guarantee against regressions that might drop the
    // counter in favor of pid+nanos alone.
    let a = unique_tmp_name("CLASSIC Main.yaml");
    let b = unique_tmp_name("CLASSIC Main.yaml");
    assert_ne!(a, b, "back-to-back calls must yield distinct tmp names");
    assert!(a.starts_with("CLASSIC Main.yaml.new."));
    assert!(b.starts_with("CLASSIC Main.yaml.new."));
}

#[test]
fn unique_tmp_name_stays_a_same_directory_sibling() {
    // install_atomic requires the tmp to live in the target's directory,
    // so the unique suffix MUST NOT introduce a path separator.
    let name = unique_tmp_name("CLASSIC Main.yaml");
    assert!(
        !name.contains('/') && !name.contains('\\'),
        "tmp name must be a plain file name, got: {name}"
    );
}

// Path-traversal regression coverage (Codex adversarial review): a
// compromised manifest or binding caller must not be able to write or
// roll back outside the yaml-cache directory. The validator is the
// single choke point, so every boundary case lives here.

#[test]
fn validate_cache_name_accepts_plain_basename() {
    assert!(is_valid_cache_file_name("CLASSIC Main.yaml"));
    assert!(is_valid_cache_file_name("CLASSIC Fallout4.yaml"));
    assert!(is_valid_cache_file_name("file.with.many.dots.yaml"));
}

#[test]
fn validate_cache_name_rejects_empty_or_dot_forms() {
    assert!(!is_valid_cache_file_name(""));
    assert!(!is_valid_cache_file_name("."));
    assert!(!is_valid_cache_file_name(".."));
}

#[test]
fn validate_cache_name_rejects_separators() {
    assert!(!is_valid_cache_file_name("foo/bar.yaml"));
    assert!(!is_valid_cache_file_name("foo\\bar.yaml"));
    assert!(!is_valid_cache_file_name("../etc/passwd"));
    assert!(!is_valid_cache_file_name("..\\Windows\\System32\\cmd.exe"));
}

#[test]
fn validate_cache_name_rejects_absolute_and_drive_paths() {
    // Unix absolute.
    assert!(!is_valid_cache_file_name("/etc/passwd"));
    // Windows absolute and drive-relative variants. On non-Windows
    // hosts the path parser does not split these specially, so the
    // separator/multi-component rules catch them.
    assert!(!is_valid_cache_file_name("C:\\Users\\me\\.bashrc"));
    assert!(!is_valid_cache_file_name("C:/Users/me/.bashrc"));
}

#[test]
fn validate_cache_name_rejects_embedded_nul() {
    assert!(!is_valid_cache_file_name("good.yaml\0evil"));
}

#[test]
fn validate_cache_name_rejects_windows_alternate_data_stream_forms() {
    for name in ["CLASSIC Main.yaml:alt", "foo:bar.yaml"] {
        assert!(
            !is_valid_cache_file_name(name),
            "NTFS stream names must be rejected: {name}"
        );
    }
}

#[test]
fn validate_cache_name_rejects_trailing_dot_or_space() {
    for name in [
        "CLASSIC Main.yaml.",
        "CLASSIC Main.yaml ",
        "CLASSIC Main.yaml. ",
    ] {
        assert!(
            !is_valid_cache_file_name(name),
            "Win32-trimmed suffixes must be rejected: {name}"
        );
    }
}

// Regression coverage (Codex adversarial review, third pass): Windows
// reserves DOS device basenames (`NUL`, `CON`, `COM1`, `LPT1`, ...) at
// the kernel level, so a `<cache_dir>/NUL` join routes at the device
// instead of producing a real file. The validator must refuse those
// on every host, not only when cfg(windows) — the same manifest can be
// validated on Linux CI and then consumed by a Windows client.
#[test]
fn validate_cache_name_rejects_windows_device_basenames() {
    for name in [
        "NUL", "CON", "PRN", "AUX", "COM1", "COM2", "COM9", "LPT1", "LPT9",
    ] {
        assert!(
            !is_valid_cache_file_name(name),
            "bare device name must be rejected: {name}"
        );
    }
}

#[test]
fn validate_cache_name_rejects_windows_device_names_case_insensitively() {
    for name in ["nul", "Con", "cOm1", "Lpt9", "aux", "prn"] {
        assert!(
            !is_valid_cache_file_name(name),
            "device name variants must be rejected case-insensitively: {name}"
        );
    }
}

#[test]
fn validate_cache_name_rejects_windows_device_names_with_extensions() {
    for name in [
        "NUL.yaml",
        "nul.yaml",
        "CON.txt",
        "com1.log",
        "LPT1.yaml.bak",
        "AUX.json",
    ] {
        assert!(
            !is_valid_cache_file_name(name),
            "device name with extension must be rejected: {name}"
        );
    }
}

#[test]
fn validate_cache_name_allows_device_like_stems_with_extra_chars() {
    // Only the classical 8 reserved names and COM1..9 / LPT1..9 are
    // reserved; similar-looking stems like `NULL`, `COM`, `LPT`,
    // `COM10`, `LPT10` are ordinary filenames on Windows.
    for name in [
        "NULL.yaml",
        "CONFIG.yaml",
        "COMMON.yaml",
        "COM10.yaml",
        "LPT10.yaml",
        "CON_main.yaml",
        "nul_main.yaml",
    ] {
        assert!(
            is_valid_cache_file_name(name),
            "non-reserved stem must be allowed: {name}"
        );
    }
}

#[test]
fn validate_manifest_rejects_case_only_duplicate_file_names() {
    let manifest = YamlManifest {
        manifest_version: 1,
        release_tag: "yaml-data-v2026.04.17".into(),
        published_at: "2026-04-17T00:00:00Z".into(),
        files: vec![
            YamlManifestFile {
                name: "CLASSIC Main.yaml".into(),
                schema_version: "1.0".into(),
                sha256: "a".repeat(64),
                size_bytes: 0,
                min_client_schema: None,
                max_client_schema: None,
                download_url: "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml".into(),
            },
            YamlManifestFile {
                name: "classic main.yaml".into(),
                schema_version: "1.0".into(),
                sha256: "b".repeat(64),
                size_bytes: 0,
                min_client_schema: None,
                max_client_schema: None,
                download_url: "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/download/yaml-data-v2026.04.17/classic%20main.yaml".into(),
            },
        ],
        signatures: Vec::new(),
    };

    let err = validate_manifest(&manifest, "evildarkarchon", "CLASSIC-Fallout4").unwrap_err();
    let msg = err.to_string();
    assert!(
        msg.contains("duplicate entry") && msg.contains("classic main.yaml"),
        "got: {msg}"
    );
}

#[test]
fn ensure_path_in_cache_accepts_same_dir_child() {
    let cache = std::path::PathBuf::from("/tmp/yaml-cache");
    let target = cache.join("CLASSIC Main.yaml");
    assert!(ensure_path_in_cache(&cache, &target).is_ok());
}

#[test]
fn ensure_path_in_cache_rejects_sibling() {
    let cache = std::path::PathBuf::from("/tmp/yaml-cache");
    let sibling = std::path::PathBuf::from("/tmp/yaml-cache-evil/file.yaml");
    // starts_with is component-wise, so the similar prefix does not fool it.
    assert!(ensure_path_in_cache(&cache, &sibling).is_err());
}

/// Entries without installed metadata use compatible cache bytes before an
/// older bundled copy, preventing repeat downloads after an applied update.
#[test]
fn enrich_installed_prefers_cache_over_bundled_fallback() {
    let cache = tempfile::tempdir().expect("isolated cache should be created");
    let bundled = tempfile::tempdir().expect("isolated bundle should be created");
    let cache_path = cache.path().join("CLASSIC Main.yaml");
    std::fs::write(&cache_path, "schema_version: \"1.2\"\ncache: current\n")
        .expect("cache fixture should be written");
    std::fs::write(
        bundled.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.0\"\nbundled: stale\n",
    )
    .expect("bundled fixture should be written");
    let cache_sha256 = classic_file_io_core::FileHasher::hash_file(&cache_path)
        .expect("cache fixture should be hashable");
    let mut current = ClientSchemaSet::new();
    current.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let enriched = enrich_installed(&current, Some(cache.path()), Some(bundled.path()));
    let entry = enriched
        .get("CLASSIC Main.yaml")
        .expect("registered entry should remain present");

    assert_eq!(entry.installed, Some(SchemaVersion::new(1, 2)));
    assert_eq!(
        entry.installed_sha256.as_deref(),
        Some(cache_sha256.as_str())
    );
}

/// A caller-provided digest remains authoritative even when no installed
/// schema version accompanies it and fallback files are available.
#[test]
fn enrich_installed_preserves_explicit_digest_without_version() {
    let bundled = tempfile::tempdir().expect("isolated bundle should be created");
    std::fs::write(
        bundled.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.0\"\nbundled: data\n",
    )
    .expect("bundled fixture should be written");
    let explicit_sha256 = "a".repeat(64);
    let mut current = ClientSchemaSet::new();
    current.insert_with_sha256(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        None,
        Some(explicit_sha256.clone()),
    );

    let enriched = enrich_installed(&current, None, Some(bundled.path()));
    let entry = enriched
        .get("CLASSIC Main.yaml")
        .expect("registered entry should remain present");

    assert_eq!(entry.installed, None);
    assert_eq!(entry.installed_sha256, Some(explicit_sha256));
}

#[test]
fn client_schema_bounds_accept_when_absent() {
    let entry = YamlManifestFile {
        name: "CLASSIC Main.yaml".into(),
        schema_version: "1.0".into(),
        sha256: "a".repeat(64),
        size_bytes: 0,
        min_client_schema: None,
        max_client_schema: None,
        download_url: "https://github.com/x/y/releases/download/t/f".into(),
    };
    let ce = ClientSchemaEntry {
        accepted: SchemaCompat::new(1, 0),
        installed: None,
        installed_sha256: None,
    };
    assert!(check_client_schema_bounds(&entry, &ce).is_ok());
}

/// Overlap semantics (not point-in-interval): a client that reads
/// `(1, 0)..(1, ∞)` overlaps a file range of `[1.3, ∞)`, so the file
/// must be accepted even though the client's *floor* sits below
/// `min_client_schema`. The old point-based check rejected this
/// scenario, silently suppressing valid updates as soon as
/// publishers tried to narrow releases with `min_client_schema`.
#[test]
fn client_schema_bounds_accept_when_floor_below_min_but_range_overlaps() {
    let mut entry = YamlManifestFile {
        name: "CLASSIC Main.yaml".into(),
        schema_version: "1.5".into(),
        sha256: "a".repeat(64),
        size_bytes: 0,
        min_client_schema: Some("1.3".into()),
        max_client_schema: None,
        download_url: "https://github.com/x/y/releases/download/t/f".into(),
    };
    let ce = ClientSchemaEntry {
        accepted: SchemaCompat::new(1, 0),
        installed: None,
        installed_sha256: None,
    };
    assert!(
        check_client_schema_bounds(&entry, &ce).is_ok(),
        "client (1,0) overlaps file [1.3, ∞); bounds must accept"
    );

    // Client already above the min is also accepted (degenerate case
    // where the point-based check would also have accepted).
    let ce_hi = ClientSchemaEntry {
        accepted: SchemaCompat::new(1, 3),
        installed: None,
        installed_sha256: None,
    };
    assert!(check_client_schema_bounds(&entry, &ce_hi).is_ok());

    // Malformed bound surfaces as an error regardless of range math.
    entry.min_client_schema = Some("not a version".into());
    assert!(check_client_schema_bounds(&entry, &ce_hi).is_err());
}

/// True non-overlap branch: client's sole major is below the file's
/// `min_client_schema` major. The client reads only major `0`; the
/// file covers `[1.0, …]`. No minor of `0` intersects that range.
#[test]
fn client_schema_bounds_reject_when_client_major_below_min_major() {
    let entry = YamlManifestFile {
        name: "CLASSIC Main.yaml".into(),
        schema_version: "1.0".into(),
        sha256: "a".repeat(64),
        size_bytes: 0,
        min_client_schema: Some("1.0".into()),
        max_client_schema: None,
        download_url: "https://github.com/x/y/releases/download/t/f".into(),
    };
    let ce = ClientSchemaEntry {
        accepted: SchemaCompat::new(0, 9),
        installed: None,
        installed_sha256: None,
    };
    let err = check_client_schema_bounds(&entry, &ce).unwrap_err();
    assert!(
        err.contains("min_client_schema") && err.contains("major 0"),
        "got: {err}"
    );
}

/// True non-overlap branch: same top major, but the client's floor
/// is above the file's ceiling minor. The client's minor range is
/// `[10, ∞)`, the file's is `[_, 5]` — disjoint.
#[test]
fn client_schema_bounds_reject_when_floor_above_max_minor_in_shared_major() {
    let entry = YamlManifestFile {
        name: "CLASSIC Main.yaml".into(),
        schema_version: "1.0".into(),
        sha256: "a".repeat(64),
        size_bytes: 0,
        min_client_schema: None,
        max_client_schema: Some("1.5".into()),
        download_url: "https://github.com/x/y/releases/download/t/f".into(),
    };
    let ce = ClientSchemaEntry {
        accepted: SchemaCompat::new(1, 10),
        installed: None,
        installed_sha256: None,
    };
    let err = check_client_schema_bounds(&entry, &ce).unwrap_err();
    assert!(
        err.contains("max_client_schema") && err.contains("1.10"),
        "got: {err}"
    );
}

#[test]
fn client_schema_bounds_reject_inverted_interval() {
    let entry = YamlManifestFile {
        name: "CLASSIC Main.yaml".into(),
        schema_version: "1.7".into(),
        sha256: "a".repeat(64),
        size_bytes: 0,
        min_client_schema: Some("1.10".into()),
        max_client_schema: Some("1.5".into()),
        download_url: "https://github.com/x/y/releases/download/t/f".into(),
    };
    let ce = ClientSchemaEntry {
        accepted: SchemaCompat::new(1, 7),
        installed: None,
        installed_sha256: None,
    };
    let err = check_client_schema_bounds(&entry, &ce).unwrap_err();
    assert!(
        err.contains("inverted")
            && err.contains("min_client_schema 1.10")
            && err.contains("max_client_schema 1.5"),
        "got: {err}"
    );
}

// ---------------------------------------------------------------------------
// approved_file_sha_map validation
// ---------------------------------------------------------------------------

#[test]
fn approved_file_sha_map_rejects_mismatched_lengths() {
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into()],
        file_sha256: vec![],
    };
    let err = approved_file_sha_map(&approved).unwrap_err();
    let msg = format!("{err}");
    assert!(
        msg.contains("1 file names") && msg.contains("0 file digests"),
        "got: {msg}"
    );
}

#[test]
fn approved_file_sha_map_rejects_invalid_digest() {
    for bad_digest in ["not-hex", &"a".repeat(63), &"a".repeat(65)] {
        let approved = ApprovedUpdate {
            release_tag: "yaml-data-v2026.04.17".into(),
            file_names: vec!["CLASSIC Main.yaml".into()],
            file_sha256: vec![bad_digest.into()],
        };
        let err = approved_file_sha_map(&approved).unwrap_err();
        let msg = format!("{err}");
        assert!(
            msg.contains("digest for `CLASSIC Main.yaml` is not 64 hex chars"),
            "for digest '{bad_digest}', got: {msg}"
        );
    }
}

#[test]
fn approved_file_sha_map_rejects_duplicate_names() {
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into(), "CLASSIC Main.yaml".into()],
        file_sha256: vec!["a".repeat(64), "b".repeat(64)],
    };
    let err = approved_file_sha_map(&approved).unwrap_err();
    let msg = format!("{err}");
    assert!(
        msg.contains("duplicate approved file `CLASSIC Main.yaml`"),
        "got: {msg}"
    );
}

#[test]
fn approved_file_sha_map_accepts_valid() {
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into(), "CLASSIC Fallout4.yaml".into()],
        file_sha256: vec!["a".repeat(64), "b".repeat(64)],
    };
    let map = approved_file_sha_map(&approved).unwrap();
    assert_eq!(map.len(), 2);
    assert_eq!(map.get("CLASSIC Main.yaml"), Some(&"a".repeat(64).as_str()));
    assert_eq!(
        map.get("CLASSIC Fallout4.yaml"),
        Some(&"b".repeat(64).as_str())
    );
}

#[test]
fn approved_file_sha_map_accepts_uppercase_hex() {
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into()],
        file_sha256: vec!["A".repeat(64)],
    };
    let map = approved_file_sha_map(&approved).unwrap();
    assert_eq!(map.get("CLASSIC Main.yaml"), Some(&"A".repeat(64).as_str()));
}

/// Regression for Codex adversarial review finding: update detection must
/// be keyed to actual data freshness, not to `schema_version`. A release
/// that ships new crash suspects / mod conflicts / FormID fixes keeps the
/// structural `schema_version` stable but changes bytes — those changes
/// MUST still classify as `UpdateAvailable`. The previous rule
/// (`manifest_version > installed`) silently suppressed every such
/// release.
#[test]
fn classify_detects_same_schema_content_churn_as_update_available() {
    let mut set = ClientSchemaSet::new();
    set.insert_with_sha256(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 0)),
        Some("a".repeat(64)),
    );

    // Manifest advertises the *same* schema_version 1.0 but a different
    // sha256 — i.e. a content-only data release. Prior to the content
    // freshness fix this entry would have been skipped because
    // `manifest_version > installed` was false.
    let manifest = YamlManifest {
        manifest_version: 1,
        release_tag: "yaml-data-v2026.04.18".into(),
        published_at: "2026-04-18T00:00:00Z".into(),
        files: vec![YamlManifestFile {
            name: "CLASSIC Main.yaml".into(),
            schema_version: "1.0".into(),
            sha256: "b".repeat(64),
            size_bytes: 0,
            min_client_schema: None,
            max_client_schema: None,
            download_url:
                "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/download/yaml-data-v2026.04.18/CLASSIC%20Main.yaml".into(),
        }],
        signatures: Vec::new(),
    };

    let status = classify_manifest(manifest, &set).unwrap();
    match status {
        YamlUpdateStatus::UpdateAvailable {
            compatible_files, ..
        } => {
            assert_eq!(compatible_files.len(), 1);
            assert_eq!(compatible_files[0].schema_version, "1.0");
        }
        other => {
            panic!("same-schema content churn must classify as UpdateAvailable, got {other:?}")
        }
    }
}

/// Inverse of the freshness regression: when the manifest's sha256 matches
/// the installed file's bytes exactly, the file MUST classify as up-to-date
/// even if a previous schema_version comparison would have said "newer".
/// This locks in the symmetric contract: content identity is the authority,
/// schema_version is only the fallback when we have no sha to compare.
#[test]
fn classify_treats_matching_sha_as_up_to_date_even_when_schema_bumped() {
    let installed_sha = "a".repeat(64);
    let mut set = ClientSchemaSet::new();
    set.insert_with_sha256(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 0)),
        Some(installed_sha.clone()),
    );

    // Manifest declares a higher schema_version AND the same content sha
    // — this is the "publisher bumped the declared schema but the bytes
    // are unchanged" edge case. Content identity beats the schema
    // comparison, so we should still be UpToDate.
    let manifest = YamlManifest {
        manifest_version: 1,
        release_tag: "yaml-data-v2026.04.18".into(),
        published_at: "2026-04-18T00:00:00Z".into(),
        files: vec![YamlManifestFile {
            name: "CLASSIC Main.yaml".into(),
            schema_version: "1.5".into(),
            sha256: installed_sha,
            size_bytes: 0,
            min_client_schema: None,
            max_client_schema: None,
            download_url:
                "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/download/yaml-data-v2026.04.18/CLASSIC%20Main.yaml".into(),
        }],
        signatures: Vec::new(),
    };

    let status = classify_manifest(manifest, &set).unwrap();
    assert!(
        matches!(status, YamlUpdateStatus::UpToDate { .. }),
        "identical sha256 must short-circuit to UpToDate regardless of schema bump"
    );
}

#[test]
fn client_schema_bounds_reject_client_above_max() {
    let entry = YamlManifestFile {
        name: "CLASSIC Main.yaml".into(),
        schema_version: "1.0".into(),
        sha256: "a".repeat(64),
        size_bytes: 0,
        min_client_schema: None,
        max_client_schema: Some("1.0".into()),
        download_url: "https://github.com/x/y/releases/download/t/f".into(),
    };
    // Client at floor 2.0 is above the file's 1.0 max.
    let ce = ClientSchemaEntry {
        accepted: SchemaCompat::new(2, 0),
        installed: None,
        installed_sha256: None,
    };
    let err = check_client_schema_bounds(&entry, &ce).unwrap_err();
    assert!(err.contains("above"), "got: {err}");
}

#[test]
fn yaml_data_pages_url_uses_client_owner_and_repo() {
    let client =
        GithubClient::with_base_url("test-owner", "test-repo", "http://localhost", None).unwrap();

    assert_eq!(
        build_yaml_data_pages_url(&client),
        "https://test-owner.github.io/test-repo/yaml-data/manifest-latest.json"
    );
}

#[test]
fn yaml_data_tag_prefix_matches_publish_namespace() {
    assert_eq!(YAML_DATA_TAG_PREFIX, "yaml-data-v");
}

#[test]
fn yaml_data_rollback_targets_follow_config_metadata() {
    let targets = yaml_data_rollback_targets();
    assert_eq!(
        targets,
        vec![
            "CLASSIC Main.yaml".to_string(),
            "CLASSIC Fallout4.yaml".to_string()
        ]
    );
    assert!(
        !targets.iter().any(|target| target.contains("Ignore")),
        "Local Ignore YAML Data must never participate in update rollback"
    );
}

#[test]
fn local_ignore_remains_unclassifiable_even_when_a_generic_caller_registers_it() {
    let file = YamlManifestFile {
        name: "classic ignore.yaml".to_string(),
        schema_version: "1.0".to_string(),
        sha256: "a".repeat(64),
        size_bytes: 1,
        min_client_schema: None,
        max_client_schema: None,
        download_url: "https://github.com/owner/repo/releases/download/tag/classic%20ignore.yaml"
            .to_string(),
    };
    let manifest = YamlManifest {
        manifest_version: 1,
        release_tag: "yaml-data-v2026.07.18".to_string(),
        published_at: "2026-07-18T12:00:00Z".to_string(),
        files: vec![file],
        signatures: Vec::new(),
    };
    let mut current = ClientSchemaSet::new();
    current.insert("classic ignore.yaml", SchemaCompat::new(1, 0), None);

    let status = classify_manifest(manifest, &current).expect("classification should complete");
    let YamlUpdateStatus::UpToDate {
        incompatible_files, ..
    } = status
    else {
        panic!("Local Ignore must never classify as update-eligible");
    };
    assert_eq!(incompatible_files.len(), 1);
    assert!(incompatible_files[0].reason.contains("user-owned"));
}

#[tokio::test]
async fn local_ignore_is_refused_before_install_network_or_disk_work() {
    let cache = tempfile::tempdir().expect("isolated cache should be created");
    let client = GithubClient::with_base_url("owner", "repo", "http://localhost", None)
        .expect("test client should be created");
    let entry = YamlManifestFile {
        name: "CLASSIC Ignore.yaml".to_string(),
        schema_version: "1.0".to_string(),
        sha256: "a".repeat(64),
        size_bytes: 1,
        min_client_schema: None,
        max_client_schema: None,
        download_url: "https://github.com/owner/repo/releases/download/tag/CLASSIC%20Ignore.yaml"
            .to_string(),
    };

    let failure = install_one(&client, &entry, cache.path(), "tag")
        .await
        .expect_err("Local Ignore installation must be refused");
    assert!(matches!(
        failure,
        FileInstallOutcome::Failed { reason, .. } if reason.contains("user-owned")
    ));
    assert!(
        std::fs::read_dir(cache.path())
            .expect("cache should remain readable")
            .next()
            .is_none(),
        "refusal must happen before creating an install artifact"
    );
}

#[test]
fn local_ignore_is_refused_before_rollback_cache_resolution() {
    let error = rollback_yaml_update("ClAsSiC IgNoRe.YaMl")
        .expect_err("Local Ignore rollback must be refused case-insensitively");
    assert!(error.to_string().contains("user-owned"));
}
