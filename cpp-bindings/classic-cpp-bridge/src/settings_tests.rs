use super::*;
use serial_test::serial;
use std::{
    io::Write,
    path::{Path, PathBuf},
};
use tempfile::NamedTempFile;

/// Returns one fixture from the repository-level User Settings compatibility corpus.
fn user_settings_fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/fixtures/user_settings_compatibility")
        .join(name)
}

/// Installs one compatibility fixture as canonical User Settings.
fn install_user_settings_fixture(root: &Path, name: &str) {
    let source =
        std::fs::read(user_settings_fixture_path(name)).expect("read User Settings fixture");
    std::fs::write(root.join("CLASSIC Settings.yaml"), &source)
        .expect("install User Settings fixture");
}

#[test]
fn test_user_settings_migration_plan_bridge_maps_flat_plan_without_writing() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "flat_classic_config.yaml");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let before = std::fs::read(&settings_path).unwrap();
    let before_modified = std::fs::metadata(&settings_path)
        .unwrap()
        .modified()
        .unwrap();

    let plan = user_settings_plan_migration(&root.path().display().to_string());

    assert_eq!(plan.status, "planned");
    assert!(plan.required);
    assert!(plan.has_plan);
    assert!(plan.base_revision.starts_with("sha256:"));
    assert_eq!(plan.source_location, "canonical");
    assert!(!plan.has_source_schema_version);
    assert_eq!(plan.target_location, "canonical");
    assert!(plan.has_target_schema_version);
    assert_eq!((plan.target_schema_major, plan.target_schema_minor), (1, 0));
    assert!(plan.has_original_content);
    assert_eq!(plan.original_content, before);
    assert!(plan.has_proposed_content);
    let proposed = String::from_utf8(plan.proposed_content.clone()).unwrap();
    assert!(proposed.contains("schema_version"));
    assert!(proposed.contains("CLASSIC_Settings"));
    assert!(plan.diagnostics.is_empty());
    assert_eq!(plan.changes[0].kind, "schema_version_transition");
    assert!(!plan.changes[0].has_source_path);
    assert!(plan.changes[0].has_target_path);
    assert_eq!(plan.changes[0].target_path, "/schema_version");
    assert!(!plan.changes[0].has_before);
    assert!(plan.changes[0].has_after);
    assert_eq!(plan.changes[0].after, "1.0");
    assert!(
        plan.changes
            .iter()
            .any(|change| change.kind == "field_transition"
                && change.source_path == "/fcx_mode"
                && change.target_path == "/CLASSIC_Settings/FCX Mode")
    );
    assert_eq!(std::fs::read(&settings_path).unwrap(), before);
    assert_eq!(
        std::fs::metadata(&settings_path)
            .unwrap()
            .modified()
            .unwrap(),
        before_modified
    );
}

#[test]
fn test_user_settings_migration_plan_bridge_reverses_entire_plan_in_memory() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "flat_classic_config.yaml");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let before = std::fs::read(&settings_path).unwrap();
    let before_modified = std::fs::metadata(&settings_path)
        .unwrap()
        .modified()
        .unwrap();
    let forward = user_settings_plan_migration(&root.path().display().to_string());

    let reversed = user_settings_reverse_migration_plan(&forward).unwrap();

    assert_eq!(reversed.status, "planned");
    assert_eq!(reversed.required, forward.required);
    assert!(reversed.has_plan);
    assert_eq!(reversed.source_location, forward.target_location);
    assert_eq!(reversed.target_location, forward.source_location);
    assert_eq!(
        (
            reversed.has_source_schema_version,
            reversed.source_schema_major,
            reversed.source_schema_minor,
        ),
        (
            forward.has_target_schema_version,
            forward.target_schema_major,
            forward.target_schema_minor,
        )
    );
    assert_eq!(reversed.original_content, forward.proposed_content);
    assert_eq!(reversed.proposed_content, forward.original_content);
    assert!(reversed.base_revision.starts_with("sha256:"));
    assert_eq!(reversed.base_revision.len(), "sha256:".len() + 64);
    assert_eq!(reversed.changes.len(), forward.changes.len());
    let forward_last = forward.changes.last().unwrap();
    let reverse_first = &reversed.changes[0];
    assert_eq!(reverse_first.kind, forward_last.kind);
    assert_eq!(reverse_first.has_source_path, forward_last.has_target_path);
    assert_eq!(reverse_first.source_path, forward_last.target_path);
    assert_eq!(reverse_first.has_target_path, forward_last.has_source_path);
    assert_eq!(reverse_first.target_path, forward_last.source_path);
    assert_eq!(reverse_first.has_before, forward_last.has_after);
    assert_eq!(reverse_first.before, forward_last.after);
    assert_eq!(reverse_first.has_after, forward_last.has_before);
    assert_eq!(reverse_first.after, forward_last.before);

    let round_trip = user_settings_reverse_migration_plan(&reversed).unwrap();

    assert_eq!(round_trip.base_revision, forward.base_revision);
    assert_eq!(round_trip.source_location, forward.source_location);
    assert_eq!(round_trip.target_location, forward.target_location);
    assert_eq!(round_trip.original_content, forward.original_content);
    assert_eq!(round_trip.proposed_content, forward.proposed_content);
    assert_eq!(round_trip.changes.len(), forward.changes.len());
    for (actual, expected) in round_trip.changes.iter().zip(&forward.changes) {
        assert_eq!(actual.kind, expected.kind);
        assert_eq!(actual.has_source_path, expected.has_source_path);
        assert_eq!(actual.source_path, expected.source_path);
        assert_eq!(actual.has_target_path, expected.has_target_path);
        assert_eq!(actual.target_path, expected.target_path);
        assert_eq!(actual.has_before, expected.has_before);
        assert_eq!(actual.before, expected.before);
        assert_eq!(actual.has_after, expected.has_after);
        assert_eq!(actual.after, expected.after);
    }
    assert_eq!(std::fs::read(&settings_path).unwrap(), before);
    assert_eq!(
        std::fs::metadata(&settings_path)
            .unwrap()
            .modified()
            .unwrap(),
        before_modified
    );
}

#[test]
fn test_user_settings_migration_plan_bridge_maps_location_transition() {
    let root = tempfile::tempdir().unwrap();
    let legacy_dir = root.path().join("CLASSIC Data");
    std::fs::create_dir(&legacy_dir).unwrap();
    let legacy_path = legacy_dir.join("CLASSIC Settings.yaml");
    let before =
        std::fs::read(user_settings_fixture_path("previous_location_nested.yaml")).unwrap();
    std::fs::write(&legacy_path, &before).unwrap();

    let plan = user_settings_plan_migration(&root.path().display().to_string());

    assert_eq!(plan.status, "planned");
    assert!(plan.required);
    assert_eq!(plan.source_location, "legacy");
    assert_eq!(plan.target_location, "canonical");
    assert_eq!(plan.changes[0].kind, "location_transition");
    assert_eq!(
        plan.changes[0].source_path,
        "CLASSIC Data/CLASSIC Settings.yaml"
    );
    assert_eq!(plan.changes[0].target_path, "CLASSIC Settings.yaml");
    assert_eq!(std::fs::read(&legacy_path).unwrap(), before);
    assert!(!root.path().join("CLASSIC Settings.yaml").exists());
}

#[test]
fn test_user_settings_migration_plan_bridge_maps_terminal_outcomes() {
    let current_root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(current_root.path(), "canonical_current_nested.yaml");

    let current = user_settings_plan_migration(&current_root.path().display().to_string());

    assert_eq!(current.status, "not_required");
    assert!(!current.required);
    assert!(!current.has_plan);
    assert!(current.base_revision.is_empty());
    assert!(current.changes.is_empty());
    assert!(!current.has_original_content);
    assert!(!current.has_proposed_content);
    assert!(current.diagnostics.is_empty());

    let future_root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(future_root.path(), "newer_major_schema.yaml");
    let future_path = future_root.path().join("CLASSIC Settings.yaml");
    let before = std::fs::read(&future_path).unwrap();

    let unsupported = user_settings_plan_migration(&future_root.path().display().to_string());

    assert_eq!(unsupported.status, "unsupported");
    assert!(!unsupported.required);
    assert!(!unsupported.has_plan);
    assert!(unsupported.changes.is_empty());
    assert_eq!(unsupported.diagnostics.len(), 1);
    assert_eq!(
        unsupported.diagnostics[0].code,
        "future_major_schema_read_only"
    );
    assert!(!unsupported.diagnostics[0].message.is_empty());
    assert_eq!(std::fs::read(&future_path).unwrap(), before);
}

#[test]
fn test_user_settings_migration_apply_bridge_exposes_receipt_and_restores_explicitly() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "flat_classic_config.yaml");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let original = std::fs::read(&settings_path).unwrap();
    let root_string = root.path().display().to_string();
    let approved = user_settings_plan_migration(&root_string);

    let handle = user_settings_apply_migration(&root_string, &approved).unwrap();
    let outcome = user_settings_migration_apply_outcome(&handle);

    assert_eq!(outcome.status, "applied");
    assert!(outcome.expected_revision.is_empty());
    assert!(outcome.actual_revision.is_empty());
    assert!(outcome.has_receipt);
    assert_eq!(PathBuf::from(&outcome.receipt.source_path), settings_path);
    assert_eq!(
        PathBuf::from(&outcome.receipt.destination_path),
        settings_path
    );
    assert!(PathBuf::from(&outcome.receipt.backup_path).starts_with(root.path()));
    assert_eq!(outcome.receipt.source_location, "canonical");
    assert!(!outcome.receipt.has_source_schema_version);
    assert_eq!(outcome.receipt.target_location, "canonical");
    assert!(outcome.receipt.has_target_schema_version);
    assert_eq!(
        (
            outcome.receipt.target_schema_major,
            outcome.receipt.target_schema_minor,
        ),
        (1, 0)
    );
    assert_eq!(outcome.receipt.backup_revision, approved.base_revision);
    assert!(outcome.receipt.published_revision.starts_with("sha256:"));
    assert_eq!(
        std::fs::read(&outcome.receipt.backup_path).unwrap(),
        original
    );
    assert_eq!(
        std::fs::read(&settings_path).unwrap(),
        approved.proposed_content
    );

    let restored = user_settings_restore_migration(&root_string, &handle).unwrap();

    assert_eq!(restored.status, "restored");
    assert_eq!(restored.revision, approved.base_revision);
    assert!(restored.expected_revision.is_empty());
    assert!(restored.actual_revision.is_empty());
    assert_eq!(std::fs::read(&settings_path).unwrap(), original);
}

#[test]
fn test_user_settings_migration_apply_bridge_maps_stale_revision_as_conflict_data() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "flat_classic_config.yaml");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let root_string = root.path().display().to_string();
    let approved = user_settings_plan_migration(&root_string);
    let changed = b"schema_version: \"1.0\"\nCLASSIC_Settings: {}\n";
    std::fs::write(&settings_path, changed).unwrap();

    let handle = user_settings_apply_migration(&root_string, &approved).unwrap();
    let outcome = user_settings_migration_apply_outcome(&handle);

    assert_eq!(outcome.status, "conflict");
    assert_eq!(outcome.expected_revision, approved.base_revision);
    assert!(outcome.actual_revision.starts_with("sha256:"));
    assert_ne!(outcome.actual_revision, outcome.expected_revision);
    assert!(!outcome.has_receipt);
    assert!(outcome.receipt.backup_path.is_empty());
    assert_eq!(std::fs::read(&settings_path).unwrap(), changed);
    assert!(!root.path().join("CLASSIC Backup").exists());
    assert!(user_settings_restore_migration(&root_string, &handle).is_err());
}

#[test]
fn test_user_settings_migration_apply_bridge_rejects_mutated_proposed_bytes() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "flat_classic_config.yaml");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let original = std::fs::read(&settings_path).unwrap();
    let root_string = root.path().display().to_string();
    let mut approved = user_settings_plan_migration(&root_string);
    approved
        .proposed_content
        .extend_from_slice(b"# unapproved\n");

    let error = user_settings_apply_migration(&root_string, &approved)
        .err()
        .expect("mutated proposed bytes must be rejected");

    assert!(error.starts_with("migration_approval_mismatch:"));
    assert_eq!(std::fs::read(&settings_path).unwrap(), original);
    assert!(!root.path().join("CLASSIC Backup").exists());
}

#[test]
fn test_user_settings_migration_restore_bridge_maps_newer_document_as_conflict_data() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "flat_classic_config.yaml");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let root_string = root.path().display().to_string();
    let approved = user_settings_plan_migration(&root_string);
    let handle = user_settings_apply_migration(&root_string, &approved).unwrap();
    let applied = user_settings_migration_apply_outcome(&handle);
    let changed = b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  FCX Mode: false\n";
    std::fs::write(&settings_path, changed).unwrap();

    let restored = user_settings_restore_migration(&root_string, &handle).unwrap();

    assert_eq!(restored.status, "conflict");
    assert!(restored.revision.is_empty());
    assert_eq!(
        restored.expected_revision,
        applied.receipt.published_revision
    );
    assert!(restored.actual_revision.starts_with("sha256:"));
    assert_ne!(restored.actual_revision, restored.expected_revision);
    assert_eq!(std::fs::read(&settings_path).unwrap(), changed);
}

// ── YAML ops tests (pre-existing) ──────────────────────────────

#[test]
fn test_yaml_ops_new() {
    let ops = yaml_ops_new();
    assert!(!yaml_ops_has_document(&ops));
}

#[test]
fn test_parse_and_dump_round_trip() {
    let mut ops = yaml_ops_new();
    let yaml_str = "game: Fallout4\nversion: 1.10.163\n";
    yaml_ops_parse(&mut ops, yaml_str).unwrap();
    assert!(yaml_ops_has_document(&ops));

    let dumped = yaml_ops_dump(&ops).unwrap();
    assert!(dumped.contains("Fallout4"));
    assert!(dumped.contains("1.10.163"));
}

#[test]
fn test_get_string_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "game: Fallout4\n").unwrap();
    assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "Fallout4");
}

#[test]
fn test_get_string_default_when_missing() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "other: value\n").unwrap();
    assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "default");
}

#[test]
fn test_get_string_no_document() {
    let ops = yaml_ops_new();
    assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "default");
}

#[test]
fn test_get_setting_value_types() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "str_val: hello\nbool_val: true\nint_val: 42\n").unwrap();

    let str_v = yaml_ops_get_setting_value(&ops, "str_val");
    assert_eq!(str_v.value, "hello");
    assert_eq!(str_v.value_type, "string");
    assert!(!str_v.is_null);

    let bool_v = yaml_ops_get_setting_value(&ops, "bool_val");
    assert_eq!(bool_v.value, "true");
    assert_eq!(bool_v.value_type, "bool");

    let int_v = yaml_ops_get_setting_value(&ops, "int_val");
    assert_eq!(int_v.value, "42");
    assert_eq!(int_v.value_type, "integer");
}

#[test]
fn test_get_setting_value_missing() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "a: 1\n").unwrap();
    let missing = yaml_ops_get_setting_value(&ops, "nonexistent");
    assert!(missing.is_null);
    assert_eq!(missing.value_type, "null");
}

#[test]
fn test_set_string_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "game: Fallout4\n").unwrap();
    yaml_ops_set_string_setting(&mut ops, "game", "Skyrim").unwrap();
    assert_eq!(yaml_ops_get_string(&ops, "game", ""), "Skyrim");
}

#[test]
fn test_set_bool_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "enabled: false\n").unwrap();
    yaml_ops_set_bool_setting(&mut ops, "enabled", true).unwrap();
    let val = yaml_ops_get_setting_value(&ops, "enabled");
    assert_eq!(val.value, "true");
    assert_eq!(val.value_type, "bool");
}

#[test]
fn test_get_vec() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "items:\n  - a\n  - b\n  - c\n").unwrap();
    let vec = yaml_ops_get_vec(&ops, "items");
    assert_eq!(vec, vec!["a", "b", "c"]);
}

#[test]
fn test_get_vec_missing() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "other: value\n").unwrap();
    let vec = yaml_ops_get_vec(&ops, "nonexistent");
    assert!(vec.is_empty());
}

#[test]
#[serial]
fn test_cache_management() {
    let ops = yaml_ops_new();
    yaml_ops_clear_cache(&ops); // Clear first to ensure a clean state
    assert_eq!(yaml_ops_cache_size(&ops), 0);
    let stats = yaml_ops_cache_stats(&ops);
    assert_eq!(stats.size, 0);
    assert_eq!(stats.capacity, 128);
    yaml_ops_clear_cache(&ops); // Should not panic on empty cache
}

#[test]
fn test_dump_no_document_error() {
    let ops = yaml_ops_new();
    assert!(yaml_ops_dump(&ops).is_err());
}

#[test]
fn test_save_no_document_error() {
    let ops = yaml_ops_new();
    assert!(yaml_ops_save_file(&ops, "test.yaml").is_err());
}

#[test]
fn test_set_setting_no_document_error() {
    let mut ops = yaml_ops_new();
    assert!(yaml_ops_set_string_setting(&mut ops, "key", "val").is_err());
}

#[test]
fn test_invalid_yaml_parse() {
    let mut ops = yaml_ops_new();
    let result = yaml_ops_load_file(&mut ops, "nonexistent_file_12345.yaml");
    assert!(result.is_err());
}

#[test]
fn test_nested_settings() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(
        &mut ops,
        "settings:\n  fcx_mode: true\n  show_values: false\n",
    )
    .unwrap();
    let fcx = yaml_ops_get_setting_value(&ops, "settings.fcx_mode");
    assert_eq!(fcx.value, "true");
    assert_eq!(fcx.value_type, "bool");
}

#[test]
fn test_set_integer_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "max_scans: 4\n").unwrap();
    yaml_ops_set_integer_setting(&mut ops, "max_scans", 8).unwrap();
    let val = yaml_ops_get_setting_value(&ops, "max_scans");
    assert_eq!(val.value, "8");
    assert_eq!(val.value_type, "integer");
}

#[test]
fn test_set_integer_setting_no_document() {
    let mut ops = yaml_ops_new();
    assert!(yaml_ops_set_integer_setting(&mut ops, "key", 1).is_err());
}

#[test]
fn test_set_vec_setting() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "items:\n  - old\n").unwrap();
    yaml_ops_set_vec_setting(
        &mut ops,
        "items",
        vec!["a".to_string(), "b".to_string(), "c".to_string()],
    )
    .unwrap();
    let vec = yaml_ops_get_vec(&ops, "items");
    assert_eq!(vec, vec!["a", "b", "c"]);
}

#[test]
fn test_set_vec_setting_empty() {
    let mut ops = yaml_ops_new();
    yaml_ops_parse(&mut ops, "items:\n  - old\n").unwrap();
    yaml_ops_set_vec_setting(&mut ops, "items", vec![]).unwrap();
    let vec = yaml_ops_get_vec(&ops, "items");
    assert!(vec.is_empty());
}

#[test]
fn test_set_vec_setting_no_document() {
    let mut ops = yaml_ops_new();
    assert!(yaml_ops_set_vec_setting(&mut ops, "key", vec!["a".to_string()]).is_err());
}

// ── Settings cache ops tests (D-09 — new) ──────────────────────

fn make_settings_yaml(content: &str) -> NamedTempFile {
    let mut file = NamedTempFile::new().unwrap();
    file.write_all(content.as_bytes()).unwrap();
    file.flush().unwrap();
    file
}

#[test]
#[serial]
fn test_settings_load_sync() {
    settings_clear_cache();
    let file = make_settings_yaml("key: value\nnumber: 42\n");
    let count = settings_load_sync("t_sync", &file.path().display().to_string()).unwrap();
    assert_eq!(count, 1);
    assert!(settings_is_cached("t_sync"));
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_load_async_blocking() {
    settings_clear_cache();
    let file = make_settings_yaml("key: value\n");
    let count =
        settings_load_async_blocking("t_async", &file.path().display().to_string()).unwrap();
    assert_eq!(count, 1);
    assert!(settings_is_cached("t_async"));
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_load_batch_sync() {
    settings_clear_cache();
    let f1 = make_settings_yaml("a: 1\n");
    let f2 = make_settings_yaml("b: 2\n");
    let paths = vec![
        f1.path().display().to_string(),
        f2.path().display().to_string(),
    ];
    let count = settings_load_batch_sync(paths).unwrap();
    assert_eq!(count, 2);
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_load_batch_async_blocking() {
    settings_clear_cache();
    let f1 = make_settings_yaml("a: 1\n");
    let f2 = make_settings_yaml("b: 2\n");
    let paths = vec![
        f1.path().display().to_string(),
        f2.path().display().to_string(),
    ];
    let count = settings_load_batch_async_blocking(paths).unwrap();
    assert_eq!(count, 2);
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_cache_stats_and_size_on_empty_cache() {
    settings_clear_cache();
    settings_reset_cache_stats();
    let stats = settings_cache_stats();
    assert_eq!(stats.hits, 0);
    assert_eq!(stats.misses, 0);
    assert_eq!(stats.size, 0);
    assert_eq!(stats.capacity, 64);
    assert_eq!(settings_cache_size(), 0);
    assert!(settings_cache_keys().is_empty());
}

#[test]
#[serial]
fn test_settings_is_cached_and_invalidate() {
    settings_clear_cache();
    assert!(!settings_is_cached("nope"));
    assert!(!settings_invalidate("nope"));

    let file = make_settings_yaml("x: 1\n");
    settings_load_sync("inv_key", &file.path().display().to_string()).unwrap();
    assert!(settings_is_cached("inv_key"));
    assert!(settings_invalidate("inv_key"));
    assert!(!settings_is_cached("inv_key"));
    settings_clear_cache();
}

#[test]
#[serial]
fn test_settings_clear_cache_is_idempotent() {
    settings_clear_cache();
    settings_clear_cache();
    assert_eq!(settings_cache_size(), 0);
}

// ── Validator tests (D-09 — new) ───────────────────────────────

#[test]
fn test_settings_validate_value_int_happy() {
    assert!(settings_validate_value("42", "int").unwrap());
    assert!(settings_validate_value("42", "integer").unwrap());
    assert!(!settings_validate_value("abc", "int").unwrap());
}

#[test]
fn test_settings_validate_value_unknown_type_errors() {
    let err = settings_validate_value("42", "quux").unwrap_err();
    assert!(err.contains("unknown setting type"));
}

#[test]
fn test_settings_validate_value_all_canonical_tokens() {
    assert!(settings_validate_value("1", "bool").unwrap());
    assert!(settings_validate_value("1", "boolean").unwrap());
    assert!(settings_validate_value("3.14", "float").unwrap());
    assert!(settings_validate_value("3.14", "double").unwrap());
    assert!(settings_validate_value("/tmp", "path").unwrap());
    assert!(settings_validate_value("anything", "string").unwrap());
    assert!(settings_validate_value("anything", "str").unwrap());
}

#[test]
fn test_settings_validate_value_case_insensitive() {
    assert!(settings_validate_value("42", "INT").unwrap());
    assert!(settings_validate_value("yes", "Bool").unwrap());
}

#[test]
fn test_settings_coerce_value_bool_yes() {
    let out = settings_coerce_value("yes", "bool").unwrap();
    assert_eq!(out.kind, "bool");
    assert!(out.bool_val);
}

#[test]
fn test_settings_coerce_value_path_vs_string_discriminator() {
    let p = settings_coerce_value("/tmp/x", "path").unwrap();
    assert_eq!(p.kind, "path");
    assert_eq!(p.string_val, "/tmp/x");

    let s = settings_coerce_value("/tmp/x", "string").unwrap();
    assert_eq!(s.kind, "string");
    assert_eq!(s.string_val, "/tmp/x");
}

#[test]
fn test_settings_coerce_value_int_and_float() {
    let i = settings_coerce_value("42", "int").unwrap();
    assert_eq!(i.kind, "int");
    assert_eq!(i.int_val, 42);

    let f = settings_coerce_value("3.125", "float").unwrap();
    assert_eq!(f.kind, "float");
    assert!((f.float_val - 3.125).abs() < 1e-9);
}

#[test]
fn test_settings_coerce_value_unknown_type_errors() {
    assert!(settings_coerce_value("42", "list").is_err());
}

#[test]
fn test_user_settings_update_preferences_bridge_is_fail_closed_with_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    let content = "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: invalid\n";
    std::fs::write(root.path().join("CLASSIC Settings.yaml"), content).unwrap();

    let preferences = user_settings_open_update_preferences(&root.path().display().to_string());

    assert!(!preferences.update_check_enabled);
    assert_eq!(preferences.update_check_origin, "degraded_fallback");
    assert_eq!(preferences.source_location, "canonical");
    assert_eq!(preferences.classification, "current");
    assert!(preferences.has_schema_version);
    assert_eq!(preferences.schema_major, 1);
    assert_eq!(preferences.schema_minor, 0);
    assert_eq!(preferences.commit_eligibility, "eligible");
    assert_eq!(preferences.diagnostics.len(), 1);
    assert_eq!(preferences.diagnostics[0].code, "invalid_type_update_check");
    assert!(!preferences.diagnostics[0].message.is_empty());
    assert!(preferences.has_original_content);
    assert_eq!(preferences.original_content, content.as_bytes());
    assert!(preferences.revision.starts_with("sha256:"));
}

#[test]
fn test_user_settings_frontend_state_bridge_maps_canonical_fixture() {
    let root = tempfile::tempdir().expect("create temporary CLASSIC root");
    install_user_settings_fixture(root.path(), "gui_geometry.yaml");

    let frontend = user_settings_open_frontend_state(&root.path().display().to_string());

    assert!(frontend.auto_switch_after_scan);
    assert_eq!(frontend.auto_switch_after_scan_origin, "document");
    assert_eq!(frontend.auto_refresh_interval_ms, 5_000);
    assert_eq!(frontend.auto_refresh_interval_ms_origin, "document");
    assert_eq!(frontend.window_geometry.len(), 4);
    assert_eq!(
        frontend
            .window_geometry
            .iter()
            .map(|geometry| geometry.tab.as_str())
            .collect::<Vec<_>>(),
        vec!["main_tab", "backups_tab", "articles_tab", "results_tab"]
    );

    let main = &frontend.window_geometry[0];
    assert_eq!((main.width, main.height, main.maximized), (705, 641, false));
    assert_eq!(main.width_origin, "document");
    assert_eq!(main.height_origin, "document");
    assert_eq!(main.maximized_origin, "document");

    let backups = &frontend.window_geometry[1];
    assert_eq!(
        (backups.width, backups.height, backups.maximized),
        (750, 580, false)
    );
    let articles = &frontend.window_geometry[2];
    assert_eq!(
        (articles.width, articles.height, articles.maximized),
        (550, 350, false)
    );
    let results = &frontend.window_geometry[3];
    assert_eq!(
        (results.width, results.height, results.maximized),
        (750, 450, true)
    );

    assert_eq!(frontend.tui_active_tab, 0);
    assert_eq!(frontend.tui_active_tab_origin, "default");
    assert_eq!(frontend.tui_results_panel_width, 30);
    assert_eq!(frontend.tui_results_panel_width_origin, "default");
    assert!(!frontend.tui_sort_ascending);
    assert_eq!(frontend.tui_sort_ascending_origin, "default");
    assert_eq!(frontend.classification, "current");
    assert!(frontend.revision.starts_with("sha256:"));
    assert_eq!(frontend.commit_eligibility, "eligible");
    assert!(frontend.diagnostics.is_empty());
}

#[test]
fn test_user_settings_frontend_state_bridge_preserves_invalid_fixture_fallbacks() {
    let root = tempfile::tempdir().expect("create temporary CLASSIC root");
    install_user_settings_fixture(root.path(), "invalid_known_values.yaml");

    let frontend = user_settings_open_frontend_state(&root.path().display().to_string());
    let main = frontend
        .window_geometry
        .iter()
        .find(|geometry| geometry.tab == "main_tab")
        .expect("main-tab geometry");

    assert_eq!((main.width, main.height, main.maximized), (640, 500, false));
    assert_eq!(main.width_origin, "degraded_fallback");
    assert_eq!(main.height_origin, "document");
    assert_eq!(main.maximized_origin, "degraded_fallback");
    assert_eq!(frontend.auto_switch_after_scan_origin, "default");
    assert_eq!(frontend.auto_refresh_interval_ms_origin, "default");
    assert_eq!(frontend.tui_active_tab_origin, "default");
    assert_eq!(frontend.classification, "current");
    assert!(frontend.revision.starts_with("sha256:"));
    assert_eq!(frontend.commit_eligibility, "eligible");

    let diagnostic_codes = frontend
        .diagnostics
        .iter()
        .map(|diagnostic| diagnostic.code.as_str())
        .collect::<Vec<_>>();
    assert!(diagnostic_codes.contains(&"invalid_type_gui_geometry_width"));
    assert!(diagnostic_codes.contains(&"invalid_type_gui_geometry_maximized"));
}

fn empty_user_settings_update() -> ffi::UserSettingsUpdateDto {
    ffi::UserSettingsUpdateDto {
        has_update_check: false,
        update_check: false,
        has_update_source: false,
        update_source: String::new(),
        has_auto_switch_after_scan: false,
        auto_switch_after_scan: false,
        window_geometry_updates: Vec::new(),
        has_tui_remembered_state: false,
        tui_active_tab: 0,
        tui_results_panel_width: 0,
        tui_sort_ascending: false,
        has_managed_game: false,
        managed_game: String::new(),
        has_game_version_selection: false,
        game_version_selection: String::new(),
        has_game_root: false,
        has_game_root_value: false,
        game_root: String::new(),
        has_game_executable: false,
        has_game_executable_value: false,
        game_executable: String::new(),
        has_documents_root: false,
        has_documents_root_value: false,
        documents_root: String::new(),
        has_ini_folder: false,
        has_ini_folder_value: false,
        ini_folder: String::new(),
        has_mods_folder: false,
        has_mods_folder_value: false,
        mods_folder: String::new(),
        has_papyrus_log_path: false,
        has_papyrus_log_path_value: false,
        papyrus_log_path: String::new(),
        has_fcx_mode: false,
        fcx_mode: false,
        has_simplify_logs: false,
        simplify_logs: false,
        has_show_statistics: false,
        show_statistics: false,
        has_formid_value_lookup: false,
        formid_value_lookup: false,
        has_formid_databases: false,
        formid_database_games: Vec::new(),
        formid_database_paths: Vec::new(),
        has_move_unsolved_logs: false,
        move_unsolved_logs: false,
        has_unsolved_logs_destination: false,
        has_unsolved_logs_destination_value: false,
        unsolved_logs_destination: String::new(),
        has_custom_scan_input: false,
        has_custom_scan_input_value: false,
        custom_scan_input: String::new(),
        has_max_concurrent_scans: false,
        max_concurrent_scans: 0,
    }
}

#[test]
fn test_user_settings_game_setup_snapshot_preserves_paths_origins_and_alias_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Managed Game: Fallout4VR\n",
        "  Game Version: VR\n",
        "  Game Folder Path: 'C:\\Games\\Fallout 4 VR'\n",
        "  Game EXE Path: D:/Games/Fallout4VR.exe\n",
        "  Documents Folder Path: C:/Users/Test/Documents/My Games/Fallout4VR\n",
        "  INI Folder Path: C:/Users/Test/Documents/My Games/Fallout4VR\n",
        "  MODS Folder Path: E:/Canonical Mods\n",
        "  Staging Mods Folder: F:/Legacy Mods Alias\n",
        "  SCAN Custom Path: G:/Canonical Crash Logs\n",
        "  Custom Scan Folder: H:/Legacy Scan Alias\n",
        "  Papyrus Log Path: C:/Users/Test/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log\n",
    );
    std::fs::write(root.path().join("CLASSIC Settings.yaml"), content).unwrap();

    let snapshot = user_settings_open_game_setup_settings(&root.path().display().to_string());

    assert_eq!(snapshot.managed_game, "Fallout4VR");
    assert_eq!(snapshot.managed_game_origin, "document");
    assert_eq!(snapshot.game_version_selection, "VR");
    assert_eq!(snapshot.game_version_selection_origin, "document");
    assert!(snapshot.has_game_root);
    assert_eq!(snapshot.game_root, r"C:\Games\Fallout 4 VR");
    assert_eq!(snapshot.game_root_origin, "document");
    assert!(snapshot.has_game_executable);
    assert_eq!(snapshot.game_executable, "D:/Games/Fallout4VR.exe");
    assert_eq!(snapshot.game_executable_origin, "document");
    assert!(snapshot.has_documents_root);
    assert_eq!(
        snapshot.documents_root,
        "C:/Users/Test/Documents/My Games/Fallout4VR"
    );
    assert_eq!(snapshot.documents_root_origin, "document");
    assert!(snapshot.has_ini_folder);
    assert_eq!(
        snapshot.ini_folder,
        "C:/Users/Test/Documents/My Games/Fallout4VR"
    );
    assert_eq!(snapshot.ini_folder_origin, "document");
    assert!(snapshot.has_mods_root);
    assert_eq!(snapshot.mods_root, "E:/Canonical Mods");
    assert_eq!(snapshot.mods_root_origin, "document");
    assert!(snapshot.has_custom_scan_input);
    assert_eq!(snapshot.custom_scan_input, "G:/Canonical Crash Logs");
    assert_eq!(snapshot.custom_scan_input_origin, "document");
    assert!(snapshot.has_papyrus_log);
    assert_eq!(
        snapshot.papyrus_log,
        "C:/Users/Test/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log"
    );
    assert_eq!(snapshot.papyrus_log_origin, "document");
    assert_eq!(snapshot.classification, "current");
    assert_eq!(snapshot.commit_eligibility, "eligible");
    assert!(snapshot.revision.starts_with("sha256:"));
    let diagnostic_codes = snapshot
        .diagnostics
        .iter()
        .map(|diagnostic| diagnostic.code.as_str())
        .collect::<Vec<_>>();
    assert_eq!(
        diagnostic_codes,
        vec![
            "canonical_alias_conflict_mods_folder",
            "canonical_alias_conflict_custom_scan_folder",
        ],
        "Game Setup diagnostics must precede shared Crash Log Scan diagnostics"
    );
}

#[test]
fn test_user_settings_crash_log_scan_snapshot_is_typed_and_preserves_origins() {
    let root = tempfile::tempdir().unwrap();
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Game Version: NextGen\n",
        "  FCX Mode: true\n",
        "  Simplify Logs: false\n",
        "  Show Statistics: true\n",
        "  Show FormID Values: true\n",
        "  Move Unsolved Logs: false\n",
        "  Unsolved Logs Destination: D:/CLASSIC/Unsolved\n",
        "  SCAN Custom Path: E:/Crash Logs\n",
        "  Custom Scan Folder: C:/Conflicting Alias\n",
        "  Max Concurrent Scans: 6\n",
        "  FormID Databases:\n",
        "    Fallout4:\n",
        "      - databases/Fallout4.db\n",
        "      - D:/Databases/Community.db\n",
    );
    std::fs::write(root.path().join("CLASSIC Settings.yaml"), content).unwrap();

    let snapshot = user_settings_open_crash_log_scan_settings(&root.path().display().to_string());

    assert!(snapshot.fcx_mode);
    assert_eq!(snapshot.fcx_mode_origin, "document");
    assert!(!snapshot.simplify_logs);
    assert_eq!(snapshot.simplify_logs_origin, "document");
    assert!(snapshot.show_statistics);
    assert!(snapshot.formid_value_lookup);
    assert_eq!(snapshot.formid_database_games, vec!["Fallout4"]);
    assert_eq!(snapshot.formid_database_paths.len(), 2);
    assert_eq!(snapshot.formid_database_paths[0].game, "Fallout4");
    assert_eq!(
        snapshot.formid_database_paths[0].path,
        "databases/Fallout4.db"
    );
    assert_eq!(snapshot.formid_databases_origin, "document");
    assert!(!snapshot.move_unsolved_logs);
    assert!(snapshot.has_unsolved_logs_destination);
    assert_eq!(snapshot.unsolved_logs_destination, "D:/CLASSIC/Unsolved");
    assert!(snapshot.has_custom_scan_input);
    assert_eq!(snapshot.custom_scan_input, "E:/Crash Logs");
    assert_eq!(snapshot.game_version_selection, "NextGen");
    assert_eq!(snapshot.game_version_selection_origin, "document");
    assert_eq!(snapshot.max_concurrent_scans, 6);
    assert_eq!(snapshot.max_concurrent_scans_origin, "document");
    assert_eq!(snapshot.classification, "current");
    assert_eq!(snapshot.commit_eligibility, "eligible");
    assert!(snapshot.revision.starts_with("sha256:"));
    assert_eq!(snapshot.diagnostics.len(), 1);
    assert_eq!(
        snapshot.diagnostics[0].code,
        "canonical_alias_conflict_custom_scan_folder"
    );
}

#[test]
fn test_user_settings_gui_snapshot_opens_every_typed_group_at_one_revision() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "canonical_current_nested.yaml");

    let snapshot = user_settings_open_gui_settings(&root.path().display().to_string());

    assert_eq!(snapshot.update_preferences.update_source, "GitHub");
    assert!(snapshot.frontend_state.auto_switch_after_scan);
    assert_eq!(
        snapshot.update_preferences.revision,
        snapshot.crash_log_scan.revision
    );
    assert_eq!(
        snapshot.crash_log_scan.revision,
        snapshot.game_setup.revision
    );
    assert_eq!(
        snapshot.game_setup.revision,
        snapshot.frontend_state.revision
    );
}

#[test]
fn test_user_settings_gui_published_defaults_do_not_require_a_root() {
    let defaults = user_settings_gui_published_defaults();

    assert_eq!(defaults.update_preferences.classification, "missing");
    assert_eq!(defaults.update_preferences.revision, "missing");
    assert!(defaults.update_preferences.update_check_enabled);
    assert_eq!(defaults.update_preferences.update_source, "GitHub");
    assert_eq!(defaults.crash_log_scan.game_version_selection, "auto");
    assert!(defaults.crash_log_scan.move_unsolved_logs);
    assert_eq!(defaults.crash_log_scan.max_concurrent_scans, 0);
    assert!(defaults.frontend_state.auto_switch_after_scan);
    assert!(!defaults.game_setup.has_game_root);
    assert!(!defaults.game_setup.has_game_executable);
}

#[test]
fn test_user_settings_gui_preferences_round_trip_through_one_typed_update() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "canonical_current_nested.yaml");
    let root_string = root.path().display().to_string();
    let mut update = empty_user_settings_update();
    update.has_update_source = true;
    update.update_source = "Both".to_string();
    update.has_auto_switch_after_scan = true;
    update.auto_switch_after_scan = false;

    let preview = user_settings_preview_update(&root_string, &update);

    assert!(preview.accepted);
    assert_eq!(
        preview
            .accepted_fields
            .iter()
            .map(|field| (field.field_path.as_str(), field.value_kind.as_str()))
            .collect::<Vec<_>>(),
        vec![
            ("/CLASSIC_Settings/Update Source", "string"),
            ("/UI/preferences/auto_switch_after_scan", "bool"),
        ]
    );
    let committed =
        user_settings_commit_update(&root_string, &preview.base_revision, &update).unwrap();
    assert_eq!(committed.status, "committed");

    let reopened = user_settings_open_gui_settings(&root_string);
    assert_eq!(reopened.update_preferences.update_source, "Both");
    assert!(!reopened.frontend_state.auto_switch_after_scan);
}

#[test]
fn test_user_settings_tui_remembered_state_round_trips_as_one_transition() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "unknown_entries.yaml");
    let root_string = root.path().display().to_string();
    let mut update = empty_user_settings_update();
    update.has_tui_remembered_state = true;
    update.tui_active_tab = 2;
    update.tui_results_panel_width = 42;
    update.tui_sort_ascending = true;

    let preview = user_settings_preview_update(&root_string, &update);

    assert!(preview.accepted);
    assert_eq!(
        preview
            .accepted_fields
            .iter()
            .map(|field| {
                (
                    field.field_path.as_str(),
                    field.value_kind.as_str(),
                    field.bool_value,
                    field.u32_value,
                )
            })
            .collect::<Vec<_>>(),
        vec![
            ("/UI/tui/active_tab", "u32", false, 2),
            ("/UI/tui/results_panel_width", "u32", false, 42),
            ("/UI/tui/sort_ascending", "bool", true, 0),
        ]
    );

    let committed =
        user_settings_commit_update(&root_string, &preview.base_revision, &update).unwrap();
    assert_eq!(committed.status, "committed");

    let reopened = user_settings_open_frontend_state(&root_string);
    assert_eq!(reopened.tui_active_tab, 2);
    assert_eq!(reopened.tui_results_panel_width, 42);
    assert!(reopened.tui_sort_ascending);
}

#[test]
fn test_legacy_tui_state_import_reports_verified_receipt_and_coded_errors() {
    let root = tempfile::tempdir().unwrap();
    install_user_settings_fixture(root.path(), "unknown_entries.yaml");
    let legacy_path = root.path().join("state.json");
    std::fs::write(
        &legacy_path,
        br#"{"active_tab":3,"results_panel_width":48,"sort_ascending":true}"#,
    )
    .unwrap();

    let handle = user_settings_import_legacy_tui_state(
        &root.path().display().to_string(),
        &legacy_path.display().to_string(),
    )
    .unwrap();
    let outcome = user_settings_legacy_tui_import_outcome(&handle);

    assert_eq!(outcome.status, "applied");
    assert_eq!(outcome.source_path, legacy_path.display().to_string());
    assert_eq!(outcome.source_revision, outcome.backup_revision);
    assert!(outcome.published_settings_revision.starts_with("sha256:"));
    assert!(std::path::Path::new(&outcome.backup_path).exists());

    let restored =
        user_settings_restore_legacy_tui_import(&root.path().display().to_string(), &handle)
            .unwrap();
    assert_eq!(restored.status, "restored");
    assert!(restored.revision.starts_with("sha256:"));

    let conflict_handle = user_settings_import_legacy_tui_state(
        &root.path().display().to_string(),
        &legacy_path.display().to_string(),
    )
    .unwrap();
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let mut newer_content = std::fs::read_to_string(&settings_path).unwrap();
    newer_content.push_str("\n# concurrent frontend edit\n");
    std::fs::write(&settings_path, newer_content).unwrap();

    let conflict = user_settings_restore_legacy_tui_import(
        &root.path().display().to_string(),
        &conflict_handle,
    )
    .unwrap();
    assert_eq!(conflict.status, "conflict");
    assert!(conflict.expected_revision.starts_with("sha256:"));
    assert!(conflict.actual_revision.starts_with("sha256:"));

    std::fs::write(&legacy_path, b"{").unwrap();
    let error = match user_settings_import_legacy_tui_state(
        &root.path().display().to_string(),
        &legacy_path.display().to_string(),
    ) {
        Ok(_) => panic!("invalid legacy JSON must fail before returning a receipt handle"),
        Err(error) => error,
    };
    assert!(error.starts_with("legacy_tui_state_parse_failed:"));
}

#[test]
fn test_legacy_tui_state_import_maps_every_non_applied_outcome() {
    let no_source =
        legacy_tui_state_import_outcome_dto(&CoreLegacyTuiStateImportOutcome::NoLegacySource);
    assert_eq!(no_source.status, "no_legacy_source");

    let migration = legacy_tui_state_import_outcome_dto(
        &CoreLegacyTuiStateImportOutcome::RequiresSettingsMigration {
            classification: DocumentClassification::Unversioned,
            revision: Revision::Missing,
        },
    );
    assert_eq!(migration.status, "requires_settings_migration");
    assert_eq!(migration.classification, "unversioned");
    assert_eq!(migration.revision, "missing");

    let untrusted = legacy_tui_state_import_outcome_dto(
        &CoreLegacyTuiStateImportOutcome::UntrustedSettingsBase {
            classification: DocumentClassification::Malformed,
            revision: Revision::Unavailable,
        },
    );
    assert_eq!(untrusted.status, "untrusted_settings_base");
    assert_eq!(untrusted.classification, "malformed");
    assert_eq!(untrusted.revision, "unavailable");

    let settings_conflict =
        legacy_tui_state_import_outcome_dto(&CoreLegacyTuiStateImportOutcome::SettingsConflict {
            expected_revision: Revision::Missing,
            actual_revision: Revision::Unavailable,
        });
    assert_eq!(settings_conflict.status, "settings_conflict");
    assert_eq!(settings_conflict.expected_revision, "missing");
    assert_eq!(settings_conflict.actual_revision, "unavailable");

    let legacy_conflict = legacy_tui_state_import_outcome_dto(
        &CoreLegacyTuiStateImportOutcome::LegacySourceConflict {
            expected_revision: Revision::Unavailable,
            actual_revision: Revision::Missing,
        },
    );
    assert_eq!(legacy_conflict.status, "legacy_source_conflict");
    assert_eq!(legacy_conflict.expected_revision, "unavailable");
    assert_eq!(legacy_conflict.actual_revision, "missing");
}

#[test]
fn test_user_settings_window_geometry_update_round_trips_with_canonical_fields() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings: {}\n",
        "UI:\n",
        "  window_geometry:\n",
        "    results_tab:\n",
        "      maximized: false\n",
        "      width: 750\n",
        "      height: 450\n",
        "    future_tab:\n",
        "      layout: ultrawide\n",
        "  community_frontend:\n",
        "    theme: amber\n",
    );
    std::fs::write(&settings_path, content).unwrap();
    let root_string = root.path().display().to_string();
    let mut update = empty_user_settings_update();
    update.window_geometry_updates = vec![ffi::UserSettingsWindowGeometryUpdateDto {
        tab: "results_tab".to_string(),
        maximized: true,
        width: 1280,
        height: 720,
    }];

    let preview = user_settings_preview_update(&root_string, &update);

    assert!(preview.accepted);
    assert!(preview.diagnostics.is_empty());
    assert_eq!(
        preview
            .accepted_fields
            .iter()
            .map(|field| {
                (
                    field.field_path.as_str(),
                    field.value_kind.as_str(),
                    field.bool_value,
                    field.u32_value,
                )
            })
            .collect::<Vec<_>>(),
        vec![
            ("/UI/window_geometry/results_tab/maximized", "bool", true, 0,),
            ("/UI/window_geometry/results_tab/width", "u32", false, 1280,),
            ("/UI/window_geometry/results_tab/height", "u32", false, 720,),
        ]
    );

    let committed =
        user_settings_commit_update(&root_string, &preview.base_revision, &update).unwrap();
    assert_eq!(committed.status, "committed");

    let reopened = user_settings_open_frontend_state(&root_string);
    let results = reopened
        .window_geometry
        .iter()
        .find(|geometry| geometry.tab == "results_tab")
        .expect("Results geometry should remain in the typed frontend projection");
    assert!(results.maximized);
    assert_eq!(results.width, 1280);
    assert_eq!(results.height, 720);

    let persisted = std::fs::read_to_string(settings_path).unwrap();
    assert!(persisted.contains("future_tab:"));
    assert!(persisted.contains("layout: ultrawide"));
    assert!(persisted.contains("community_frontend:"));
    assert!(persisted.contains("theme: amber"));
}

#[test]
fn test_user_settings_window_geometry_update_rejects_unknown_tab_token() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let content = "schema_version: \"1.0\"\nCLASSIC_Settings: {}\n";
    std::fs::write(&settings_path, content).unwrap();
    let root_string = root.path().display().to_string();
    let revision = user_settings_open_frontend_state(&root_string).revision;
    let mut update = empty_user_settings_update();
    update.window_geometry_updates = vec![ffi::UserSettingsWindowGeometryUpdateDto {
        tab: "settings_dialog".to_string(),
        maximized: false,
        width: 800,
        height: 600,
    }];

    let preview = user_settings_preview_update(&root_string, &update);

    assert!(!preview.accepted);
    assert_eq!(preview.diagnostics.len(), 1);
    assert_eq!(preview.diagnostics[0].field_path, "/UI/window_geometry");
    assert_eq!(preview.diagnostics[0].code, "invalid_enum_gui_window");
    let committed = user_settings_commit_update(&root_string, &revision, &update).unwrap();
    assert_eq!(committed.status, "rejected");
    assert_eq!(committed.diagnostics[0].code, "invalid_enum_gui_window");
    assert_eq!(std::fs::read(&settings_path).unwrap(), content.as_bytes());
}

#[test]
fn test_user_settings_window_geometry_update_preserves_dimension_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let content = "schema_version: \"1.0\"\nCLASSIC_Settings: {}\n";
    std::fs::write(&settings_path, content).unwrap();
    let mut update = empty_user_settings_update();
    update.window_geometry_updates = vec![ffi::UserSettingsWindowGeometryUpdateDto {
        tab: "main_tab".to_string(),
        maximized: false,
        width: 0,
        height: -1,
    }];

    let preview = user_settings_preview_update(&root.path().display().to_string(), &update);

    assert!(!preview.accepted);
    assert_eq!(
        preview
            .diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.field_path.as_str(), diagnostic.code.as_str()))
            .collect::<Vec<_>>(),
        vec![
            (
                "/UI/window_geometry/main_tab/width",
                "invalid_range_gui_geometry_width",
            ),
            (
                "/UI/window_geometry/main_tab/height",
                "invalid_range_gui_geometry_height",
            ),
        ]
    );
    assert_eq!(std::fs::read(&settings_path).unwrap(), content.as_bytes());
}

#[test]
fn test_user_settings_update_preview_maps_all_game_setup_fields() {
    let root = tempfile::tempdir().unwrap();
    let content = "schema_version: \"1.0\"\nCLASSIC_Settings: {}\n";
    std::fs::write(root.path().join("CLASSIC Settings.yaml"), content).unwrap();
    let mut update = empty_user_settings_update();
    update.has_managed_game = true;
    update.managed_game = "Fallout4VR".to_string();
    update.has_game_root = true;
    update.has_game_root_value = true;
    update.game_root = r"C:\Games\Fallout 4 VR".to_string();
    update.has_game_executable = true;
    update.has_game_executable_value = true;
    update.game_executable = "D:/Games/Fallout4VR.exe".to_string();
    update.has_documents_root = true;
    update.has_documents_root_value = true;
    update.documents_root = "C:/Users/Test/Documents/My Games/Fallout4VR".to_string();
    update.has_ini_folder = true;
    update.has_ini_folder_value = true;
    update.ini_folder = "C:/Users/Test/Documents/My Games/Fallout4VR".to_string();
    update.has_mods_folder = true;
    update.has_mods_folder_value = true;
    update.mods_folder = "E:/Mod Staging/Fallout4VR".to_string();
    update.has_papyrus_log_path = true;
    update.has_papyrus_log_path_value = true;
    update.papyrus_log_path =
        "C:/Users/Test/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log".to_string();

    let preview = user_settings_preview_update(&root.path().display().to_string(), &update);

    assert!(preview.accepted);
    assert!(preview.diagnostics.is_empty());
    assert_eq!(
        preview
            .accepted_fields
            .iter()
            .map(|field| (field.field_path.as_str(), field.value_kind.as_str()))
            .collect::<Vec<_>>(),
        vec![
            ("/CLASSIC_Settings/Managed Game", "string"),
            ("/CLASSIC_Settings/Game Folder Path", "optional_string"),
            ("/CLASSIC_Settings/Game EXE Path", "optional_string"),
            ("/CLASSIC_Settings/Documents Folder Path", "optional_string"),
            ("/CLASSIC_Settings/INI Folder Path", "optional_string"),
            ("/CLASSIC_Settings/MODS Folder Path", "optional_string"),
            ("/CLASSIC_Settings/Papyrus Log Path", "optional_string"),
        ]
    );
    assert_eq!(preview.accepted_fields[0].string_value, "Fallout4VR");
    assert_eq!(
        preview
            .accepted_fields
            .iter()
            .skip(1)
            .map(|field| field.string_value.as_str())
            .collect::<Vec<_>>(),
        vec![
            r"C:\Games\Fallout 4 VR",
            "D:/Games/Fallout4VR.exe",
            "C:/Users/Test/Documents/My Games/Fallout4VR",
            "C:/Users/Test/Documents/My Games/Fallout4VR",
            "E:/Mod Staging/Fallout4VR",
            "C:/Users/Test/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log",
        ]
    );
    assert!(
        preview
            .accepted_fields
            .iter()
            .all(|field| field.has_string_value)
    );
}

#[test]
fn test_user_settings_bootstrap_preview_is_explicit_and_does_not_write() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let update = empty_user_settings_update();

    let preview = user_settings_preview_bootstrap(&root.path().display().to_string(), &update);

    assert!(preview.accepted);
    assert_eq!(preview.base_revision, "missing");
    assert!(preview.diagnostics.is_empty());
    assert!(
        !settings_path.exists(),
        "previewing the explicit bootstrap must not create User Settings"
    );
}

#[test]
fn test_user_settings_bootstrap_preview_commits_only_through_explicit_bootstrap_seam() {
    let root = tempfile::tempdir().unwrap();
    let root_string = root.path().display().to_string();
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    let update = empty_user_settings_update();
    let preview = user_settings_preview_bootstrap(&root_string, &update);
    assert!(preview.accepted);

    let ordinary =
        user_settings_commit_update(&root_string, &preview.base_revision, &update).unwrap();
    assert_eq!(ordinary.status, "rejected");
    assert!(
        !settings_path.exists(),
        "ordinary commit must not create missing User Settings"
    );

    let committed =
        user_settings_commit_bootstrap(&root_string, &preview.base_revision, &update).unwrap();

    assert_eq!(committed.status, "committed");
    assert!(committed.revision.starts_with("sha256:"));
    let content = std::fs::read_to_string(settings_path).expect("bootstrapped User Settings");
    assert!(
        content.contains("schema_version: '1.0'") || content.contains("schema_version: \"1.0\"")
    );
    assert!(
        content.contains("CLASSIC_Settings:"),
        "bootstrap commit should render Rust-owned published defaults"
    );
}

#[test]
fn test_user_settings_update_preview_accepts_only_requested_fields_without_writing() {
    let root = tempfile::tempdir().unwrap();
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Update Check: true\n",
        "  Game Version: auto\n",
        "  FCX Mode: false\n",
        "  Simplify Logs: false\n",
        "  Show Statistics: false\n",
        "  Show FormID Values: false\n",
        "  Move Unsolved Logs: true\n",
        "  SCAN Custom Path: null\n",
        "  Custom Scan Folder: D:/Legacy Alias\n",
        "  Max Concurrent Scans: 0\n",
        "  FormID Databases: {}\n",
    );
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(&settings_path, content).unwrap();
    let mut update = empty_user_settings_update();
    update.has_fcx_mode = true;
    update.fcx_mode = true;
    update.has_formid_databases = true;
    update.formid_database_games = vec!["Fallout4".to_string()];
    update.formid_database_paths = vec![ffi::FormIdDatabasePathDto {
        game: "Fallout4".to_string(),
        path: "databases/Replacement.db".to_string(),
    }];
    update.has_game_version_selection = true;
    update.game_version_selection = "Original".to_string();
    update.has_max_concurrent_scans = true;
    update.max_concurrent_scans = 8;

    let preview = user_settings_preview_update(&root.path().display().to_string(), &update);

    assert!(preview.accepted);
    assert!(preview.base_revision.starts_with("sha256:"));
    assert!(preview.diagnostics.is_empty());
    assert_eq!(preview.accepted_fields.len(), 4);
    assert_eq!(
        preview
            .accepted_fields
            .iter()
            .map(|field| field.field_path.as_str())
            .collect::<Vec<_>>(),
        vec![
            "/CLASSIC_Settings/Game Version",
            "/CLASSIC_Settings/FCX Mode",
            "/CLASSIC_Settings/FormID Databases",
            "/CLASSIC_Settings/Max Concurrent Scans",
        ]
    );
    assert_eq!(preview.accepted_fields[0].value_kind, "string");
    assert_eq!(preview.accepted_fields[0].string_value, "Original");
    assert_eq!(preview.accepted_fields[1].value_kind, "bool");
    assert!(preview.accepted_fields[1].bool_value);
    assert_eq!(preview.accepted_fields[2].value_kind, "formid_databases");
    assert_eq!(preview.formid_database_games, vec!["Fallout4"]);
    assert_eq!(preview.formid_database_paths.len(), 1);
    assert_eq!(preview.formid_database_paths[0].game, "Fallout4");
    assert_eq!(
        preview.formid_database_paths[0].path,
        "databases/Replacement.db"
    );
    assert_eq!(preview.accepted_fields[3].value_kind, "u32");
    assert_eq!(preview.accepted_fields[3].u32_value, 8);
    assert_eq!(std::fs::read(&settings_path).unwrap(), content.as_bytes());
}

#[test]
fn test_user_settings_update_preview_rejects_all_fields_with_specific_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Update Check: true\n",
        "  Game Version: auto\n",
        "  FCX Mode: false\n",
        "  Simplify Logs: false\n",
        "  Show Statistics: false\n",
        "  Show FormID Values: false\n",
        "  Move Unsolved Logs: true\n",
        "  SCAN Custom Path: null\n",
        "  Max Concurrent Scans: 0\n",
        "  FormID Databases: {}\n",
    );
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(&settings_path, content).unwrap();
    let mut update = empty_user_settings_update();
    update.has_simplify_logs = true;
    update.simplify_logs = true;
    update.has_game_version_selection = true;
    update.game_version_selection = "AE".to_string();
    update.has_custom_scan_input = true;
    update.has_custom_scan_input_value = true;
    update.custom_scan_input = "relative/logs".to_string();
    update.has_max_concurrent_scans = true;
    update.max_concurrent_scans = 33;

    let preview = user_settings_preview_update(&root.path().display().to_string(), &update);

    assert!(!preview.accepted);
    assert!(preview.base_revision.is_empty());
    assert!(preview.accepted_fields.is_empty());
    assert_eq!(preview.diagnostics.len(), 3);
    assert_eq!(
        preview
            .diagnostics
            .iter()
            .map(|diagnostic| diagnostic.field_path.as_str())
            .collect::<Vec<_>>(),
        vec![
            "/CLASSIC_Settings/Game Version",
            "/CLASSIC_Settings/SCAN Custom Path",
            "/CLASSIC_Settings/Max Concurrent Scans",
        ]
    );
    assert!(
        preview
            .diagnostics
            .iter()
            .all(|diagnostic| diagnostic.has_field_path)
    );
    assert_eq!(std::fs::read(&settings_path).unwrap(), content.as_bytes());
}

#[test]
fn test_user_settings_commit_update_requires_the_accepted_base_revision() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(
        &settings_path,
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Unsolved Logs Destination: null\n",
    )
    .unwrap();
    let mut update = empty_user_settings_update();
    update.has_unsolved_logs_destination = true;
    update.has_unsolved_logs_destination_value = true;
    update.unsolved_logs_destination = "D:/CLASSIC/Unsolved".to_string();
    let root_string = root.path().display().to_string();
    let preview = user_settings_preview_update(&root_string, &update);
    assert!(preview.accepted);

    let committed =
        user_settings_commit_update(&root_string, &preview.base_revision, &update).unwrap();

    assert_eq!(committed.status, "committed");
    assert!(committed.revision.starts_with("sha256:"));
    assert!(committed.diagnostics.is_empty());

    let stale = user_settings_commit_update(&root_string, &preview.base_revision, &update).unwrap();

    assert_eq!(stale.status, "conflict");
    assert_eq!(stale.expected_revision, preview.base_revision);
    assert_eq!(stale.actual_revision, committed.revision);
    assert!(stale.diagnostics.is_empty());
}
