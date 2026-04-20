use super::*;

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

#[test]
fn resolve_installed_from_path_returns_none_for_missing() {
    let tmp = tempfile::TempDir::new().unwrap();
    assert!(resolve_installed_from_path(tmp.path(), "CLASSIC Main.yaml").is_none());
}

#[test]
fn resolve_installed_from_path_returns_none_for_invalid_name() {
    let tmp = tempfile::TempDir::new().unwrap();
    // Even if the traversal resolved to a readable file, the validator
    // must refuse before any fs::read attempt.
    assert!(resolve_installed_from_path(tmp.path(), "../x").is_none());
}

#[test]
fn resolve_installed_from_path_reads_schema_version() {
    let tmp = tempfile::TempDir::new().unwrap();
    let path = tmp.path().join("CLASSIC Main.yaml");
    std::fs::write(&path, "schema_version: \"1.2\"\nother: yes\n").unwrap();

    let (v, sha) = resolve_installed_from_path(tmp.path(), "CLASSIC Main.yaml").unwrap();
    assert_eq!(v, SchemaVersion::new(1, 2));
    // The sha half is what drives content-freshness in classify_manifest;
    // guard the contract here so a refactor that forgets to populate it
    // regresses back to "same-schema data releases are invisible".
    assert_eq!(sha.len(), 64, "sha256 half must be 64 hex chars");
    assert!(sha.chars().all(|c| c.is_ascii_hexdigit()));
}

#[test]
fn resolve_installed_from_path_returns_none_for_missing_header() {
    let tmp = tempfile::TempDir::new().unwrap();
    let path = tmp.path().join("CLASSIC Main.yaml");
    std::fs::write(&path, "game: Fallout4\n").unwrap();

    // Missing `schema_version` header => treat as "unknown installed".
    assert!(resolve_installed_from_path(tmp.path(), "CLASSIC Main.yaml").is_none());
}

#[test]
fn enrich_installed_preserves_explicit_value() {
    let tmp = tempfile::TempDir::new().unwrap();
    // Even though nothing is on disk, an explicit installed value
    // must be passed through untouched.
    let mut set = ClientSchemaSet::new();
    set.insert(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 5)),
    );
    let enriched = enrich_installed(&set, Some(tmp.path()), Some(tmp.path()));
    let entry = enriched.get("CLASSIC Main.yaml").unwrap();
    assert_eq!(entry.installed, Some(SchemaVersion::new(1, 5)));
}

#[test]
fn enrich_installed_fills_from_cache_when_none() {
    let cache_tmp = tempfile::TempDir::new().unwrap();
    let bundled_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        cache_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.3\"\n",
    )
    .unwrap();
    // Bundled carries a distinct (older) version so a missed cache-read
    // would be visible in the output.
    std::fs::write(
        bundled_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.0\"\n",
    )
    .unwrap();

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let enriched =
        enrich_installed(&set, Some(cache_tmp.path()), Some(bundled_tmp.path()));
    let entry = enriched.get("CLASSIC Main.yaml").unwrap();
    assert_eq!(
        entry.installed,
        Some(SchemaVersion::new(1, 3)),
        "cache takes precedence over bundled when both are present"
    );
}

#[test]
fn enrich_installed_falls_back_to_bundled_when_cache_missing() {
    // Regression for the Codex adversarial review finding:
    // a clean install (no cache yet) used to fall through to
    // `installed == None`, which classified every compatible manifest
    // entry as "available" and would have triggered pointless downloads
    // whose `.prev` would rotate out already-current bytes. Bundled must
    // now be consulted when cache is absent.
    let cache_tmp = tempfile::TempDir::new().unwrap();
    let bundled_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        bundled_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.0\"\n",
    )
    .unwrap();

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let enriched =
        enrich_installed(&set, Some(cache_tmp.path()), Some(bundled_tmp.path()));
    let entry = enriched.get("CLASSIC Main.yaml").unwrap();
    assert_eq!(entry.installed, Some(SchemaVersion::new(1, 0)));
}

#[test]
fn enrich_installed_without_cache_reads_bundled_only() {
    // `cache_dir: None` is the `ensure_yaml_cache_dir()` failure branch
    // in `check_yaml_update`. Bundled must still be consulted so clean
    // installs running on a host where the cache dir is unavailable do
    // not re-download matching bundled data.
    let bundled_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        bundled_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.2\"\n",
    )
    .unwrap();

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let enriched = enrich_installed(&set, None, Some(bundled_tmp.path()));
    let entry = enriched.get("CLASSIC Main.yaml").unwrap();
    assert_eq!(entry.installed, Some(SchemaVersion::new(1, 2)));
}

#[test]
fn enrich_installed_clean_install_classified_as_up_to_date() {
    // End-to-end companion for `enrich_installed_falls_back_to_bundled_when_cache_missing`:
    // prove that a clean install whose bundled copy matches the
    // manifest's advertised *content* is classified as `UpToDate` rather
    // than `UpdateAvailable`. This is the observable guarantee the
    // bundled fallback must provide to the native frontends.
    //
    // The manifest's `sha256` must equal the bundled file's real sha,
    // because content identity is the freshness signal (see the
    // `classify_manifest` rustdoc). A placeholder sha would make this
    // test assert the *opposite* of what finding #1 fixed.
    let cache_tmp = tempfile::TempDir::new().unwrap();
    let bundled_tmp = tempfile::TempDir::new().unwrap();
    let bundled_path = bundled_tmp.path().join("CLASSIC Main.yaml");
    std::fs::write(&bundled_path, "schema_version: \"1.0\"\n").unwrap();
    let bundled_sha = FileHasher::hash_file(&bundled_path).unwrap();

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let enriched =
        enrich_installed(&set, Some(cache_tmp.path()), Some(bundled_tmp.path()));
    let manifest = YamlManifest {
        manifest_version: 1,
        release_tag: "yaml-data-v2026.04.17".into(),
        published_at: "2026-04-17T00:00:00Z".into(),
        files: vec![YamlManifestFile {
            name: "CLASSIC Main.yaml".into(),
            schema_version: "1.0".into(),
            sha256: bundled_sha,
            size_bytes: 0,
            min_client_schema: None,
            max_client_schema: None,
            download_url: "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml".into(),
        }],
        signatures: Vec::new(),
    };

    let status = classify_manifest(manifest, &enriched).unwrap();
    match status {
        YamlUpdateStatus::UpToDate { .. } => {}
        other => panic!(
            "clean install with bundled at the advertised content must be UpToDate, got {other:?}"
        ),
    }
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

/// Regression for Codex adversarial review finding: "Installed-version
/// detection uses a relative bundled path, so clean installs can be
/// misreported as needing an update". The helper must never return a
/// relative path — it either resolves from the exe directory (absolute)
/// or returns `None`, never a bare `"CLASSIC Data/databases"` that would
/// be joined against whatever cwd the process happened to inherit.
#[test]
fn resolve_bundled_yaml_dir_never_returns_a_relative_path() {
    match resolve_bundled_yaml_dir() {
        None => {
            // Acceptable: `current_exe()` can fail in exotic environments.
            // The `enrich_installed` path treats `None` as "skip bundled
            // lookup", which is what we want on such hosts.
        }
        Some(p) => assert!(
            p.is_absolute(),
            "resolved bundled dir must be absolute (derived from current_exe), got: {}",
            p.display()
        ),
    }
}

/// Regression for Codex adversarial review finding: with both sources
/// unavailable, `enrich_installed` must leave `installed == None` rather
/// than probing any relative fallback. Previously `bundled_dir` was
/// `&Path` and always resolved to the cwd-relative `CLASSIC Data/databases`.
#[test]
fn enrich_installed_without_any_source_leaves_installed_none() {
    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let enriched = enrich_installed(&set, None, None);
    let entry = enriched.get("CLASSIC Main.yaml").unwrap();
    assert!(
        entry.installed.is_none(),
        "no cache and no bundled source must leave installed as None instead of probing cwd"
    );
}

/// Regression for Codex adversarial review finding: a downgraded client
/// whose cache still holds an incompatible higher-MAJOR file must NOT
/// record that version as `installed` — the runtime loader refuses the
/// cache copy and actually serves the bundled lower version, so an
/// enrichment that mirrors the cache bytes would classify a compatible
/// manifest as "not newer" and suppress a real update.
#[test]
fn enrich_installed_skips_incompatible_cache_and_uses_bundled() {
    let cache_tmp = tempfile::TempDir::new().unwrap();
    let bundled_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        cache_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"2.0\"\n",
    )
    .unwrap();
    std::fs::write(
        bundled_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.0\"\n",
    )
    .unwrap();

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let enriched =
        enrich_installed(&set, Some(cache_tmp.path()), Some(bundled_tmp.path()));
    let entry = enriched.get("CLASSIC Main.yaml").unwrap();
    assert_eq!(
        entry.installed,
        Some(SchemaVersion::new(1, 0)),
        "incompatible cache must be skipped so bundled reports as installed"
    );
}

/// End-to-end guard: the "incompatible cache + compatible bundled"
/// scenario plus a compatible `1.1` manifest entry must classify as
/// `UpdateAvailable` — because the runtime is really serving `1.0` from
/// bundled. Before the fix the cached `2.0` would masquerade as
/// `installed`, suppressing the update.
#[test]
fn enrich_installed_incompatible_cache_does_not_suppress_real_update() {
    let cache_tmp = tempfile::TempDir::new().unwrap();
    let bundled_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        cache_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"2.0\"\n",
    )
    .unwrap();
    std::fs::write(
        bundled_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.0\"\n",
    )
    .unwrap();

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let enriched =
        enrich_installed(&set, Some(cache_tmp.path()), Some(bundled_tmp.path()));
    let manifest = YamlManifest {
        manifest_version: 1,
        release_tag: "yaml-data-v2026.04.18".into(),
        published_at: "2026-04-18T00:00:00Z".into(),
        files: vec![YamlManifestFile {
            name: "CLASSIC Main.yaml".into(),
            schema_version: "1.1".into(),
            sha256: "a".repeat(64),
            size_bytes: 0,
            min_client_schema: None,
            max_client_schema: None,
            download_url: "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/download/yaml-data-v2026.04.18/CLASSIC%20Main.yaml".into(),
        }],
        signatures: Vec::new(),
    };

    let status = classify_manifest(manifest, &enriched).unwrap();
    match status {
        YamlUpdateStatus::UpdateAvailable {
            compatible_files, ..
        } => {
            assert_eq!(compatible_files.len(), 1);
            assert_eq!(compatible_files[0].schema_version, "1.1");
        }
        other => panic!(
            "compatible 1.1 manifest vs bundled 1.0 + incompatible cached 2.0 must be UpdateAvailable, got {other:?}"
        ),
    }
}

/// `resolve_cache_installed` must follow the self_heal rule: when the
/// canonical cache file is missing, read `.prev` (what the runtime
/// loader would promote on the next startup).
#[test]
fn resolve_cache_installed_reads_prev_when_canonical_missing() {
    let cache_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        cache_tmp.path().join("CLASSIC Main.yaml.prev"),
        "schema_version: \"1.0\"\n",
    )
    .unwrap();

    let compat = SchemaCompat::new(1, 0);
    let (v, sha) =
        resolve_cache_installed(cache_tmp.path(), "CLASSIC Main.yaml", &compat).unwrap();
    assert_eq!(v, SchemaVersion::new(1, 0));
    assert_eq!(sha.len(), 64);
}

/// When canonical cache file exists, `.prev` must be ignored even if it
/// would otherwise be compatible — the runtime's self_heal is a strict
/// no-op when canonical is present, and this helper must match.
#[test]
fn resolve_cache_installed_ignores_prev_when_canonical_present() {
    let cache_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        cache_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.2\"\n",
    )
    .unwrap();
    std::fs::write(
        cache_tmp.path().join("CLASSIC Main.yaml.prev"),
        "schema_version: \"1.0\"\n",
    )
    .unwrap();

    let compat = SchemaCompat::new(1, 0);
    let (v, _sha) =
        resolve_cache_installed(cache_tmp.path(), "CLASSIC Main.yaml", &compat).unwrap();
    assert_eq!(
        v,
        SchemaVersion::new(1, 2),
        "canonical must win over `.prev` when present"
    );
}

/// When canonical cache is missing and `.prev` is itself incompatible,
/// the helper must return `None` (not the incompatible version) so the
/// caller falls through to bundled.
#[test]
fn resolve_cache_installed_skips_incompatible_prev() {
    let cache_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        cache_tmp.path().join("CLASSIC Main.yaml.prev"),
        "schema_version: \"2.0\"\n",
    )
    .unwrap();

    let compat = SchemaCompat::new(1, 0);
    assert!(
        resolve_cache_installed(cache_tmp.path(), "CLASSIC Main.yaml", &compat).is_none()
    );
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
    let cache_tmp = tempfile::TempDir::new().unwrap();
    std::fs::write(
        cache_tmp.path().join("CLASSIC Main.yaml"),
        "schema_version: \"1.0\"\nsuspects:\n  - old_entry\n",
    )
    .unwrap();

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);
    let enriched = enrich_installed(&set, Some(cache_tmp.path()), None);

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

    let status = classify_manifest(manifest, &enriched).unwrap();
    match status {
        YamlUpdateStatus::UpdateAvailable { compatible_files, .. } => {
            assert_eq!(compatible_files.len(), 1);
            assert_eq!(compatible_files[0].schema_version, "1.0");
        }
        other => panic!(
            "same-schema content churn must classify as UpdateAvailable, got {other:?}"
        ),
    }
}

/// Inverse of the freshness regression: when the manifest's sha256 matches
/// the installed file's bytes exactly, the file MUST classify as up-to-date
/// even if a previous schema_version comparison would have said "newer".
/// This locks in the symmetric contract: content identity is the authority,
/// schema_version is only the fallback when we have no sha to compare.
#[test]
fn classify_treats_matching_sha_as_up_to_date_even_when_schema_bumped() {
    let cache_tmp = tempfile::TempDir::new().unwrap();
    let installed_path = cache_tmp.path().join("CLASSIC Main.yaml");
    let installed_body = "schema_version: \"1.0\"\n";
    std::fs::write(&installed_path, installed_body).unwrap();
    let installed_sha = FileHasher::hash_file(&installed_path).unwrap();

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);
    let enriched = enrich_installed(&set, Some(cache_tmp.path()), None);

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

    let status = classify_manifest(manifest, &enriched).unwrap();
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
