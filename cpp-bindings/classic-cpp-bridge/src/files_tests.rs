use super::*;

#[test]
fn test_backup_type_from_str() {
    assert!(backup_type_from_str("xse").is_ok());
    assert!(backup_type_from_str("reshade").is_ok());
    assert!(backup_type_from_str("vulkan").is_ok());
    assert!(backup_type_from_str("enb").is_ok());
    assert!(backup_type_from_str("unknown").is_err());
}

#[test]
fn test_backup_manager_new() {
    let _mgr = backup_manager_new("C:\\Games\\Fallout4");
}

#[test]
fn test_file_read_write_round_trip() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("test.txt");
    let path_str = path.to_str().unwrap();

    write_file_string(path_str, "test content").unwrap();
    let content = read_report_file(path_str).unwrap();
    assert_eq!(content.trim(), "test content");
}

#[test]
fn test_discover_report_files_empty_dir() {
    let dir = tempfile::tempdir().unwrap();
    let reports = discover_report_files(dir.path().to_str().unwrap());
    assert!(reports.is_empty());
}

#[test]
fn test_discover_report_files_finds_autoscan() {
    let dir = tempfile::tempdir().unwrap();
    // Create matching and non-matching files
    std::fs::write(dir.path().join("crash-2025-01-01-AUTOSCAN.md"), "report1").unwrap();
    std::fs::write(dir.path().join("crash-2025-01-02-AUTOSCAN.md"), "report2").unwrap();
    std::fs::write(dir.path().join("notes.md"), "not a report").unwrap();
    std::fs::write(dir.path().join("crash.log"), "raw log").unwrap();

    let reports = discover_report_files(dir.path().to_str().unwrap());
    assert_eq!(reports.len(), 2, "Should find exactly 2 AUTOSCAN.md files");
    for r in &reports {
        assert!(r.contains("-AUTOSCAN.md"), "Path should match pattern: {r}");
    }
}

#[test]
fn test_discover_report_files_nonexistent_dir() {
    let reports = discover_report_files("nonexistent_directory_xyz_123");
    assert!(reports.is_empty());
}

#[test]
fn test_read_report_file_round_trip() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("test-AUTOSCAN.md");
    let path_str = path.to_str().unwrap();
    std::fs::write(&path, "# Report\n\nSome content").unwrap();

    let content = read_report_file(path_str).unwrap();
    assert!(content.contains("# Report"));
    assert!(content.contains("Some content"));
}

#[test]
fn test_read_report_file_nonexistent() {
    let result = read_report_file("nonexistent_report_xyz.md");
    assert!(result.is_err());
}
#[test]
fn report_discovery_excludes_directories_with_report_suffix() {
    let directory = tempfile::tempdir().unwrap();
    std::fs::create_dir(directory.path().join("directory-AUTOSCAN.md")).unwrap();
    assert!(discover_report_files(directory.path().to_str().unwrap()).is_empty());
}
#[test]
fn writes_report_discovery_conformance_receipt() {
    crate::tests::interface_receipt("report-discovery", |fixture| {
        let temporary = tempfile::tempdir().unwrap();
        let root = temporary.path();
        for directory in fixture["directories"].as_array().unwrap() {
            std::fs::create_dir_all(root.join(directory.as_str().unwrap())).unwrap();
        }
        for item in fixture["files"].as_array().unwrap() {
            let path = root.join(item["path"].as_str().unwrap());
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(&path, item["content"].as_str().unwrap()).unwrap();
            let time = std::time::UNIX_EPOCH
                + std::time::Duration::from_secs(item["modifiedSeconds"].as_u64().unwrap());
            std::fs::File::options()
                .write(true)
                .open(path)
                .unwrap()
                .set_times(std::fs::FileTimes::new().set_modified(time))
                .unwrap();
        }
        let target = if fixture["missing"].as_bool().unwrap() {
            root.join("missing")
        } else {
            root.to_path_buf()
        };
        let reports = discover_report_files(target.to_str().unwrap())
            .into_iter()
            .map(|path| {
                std::path::Path::new(&path)
                    .strip_prefix(root)
                    .unwrap()
                    .to_string_lossy()
                    .replace('\\', "/")
            })
            .collect::<Vec<_>>();
        let mut observation = crate::tests::file_snapshot(root);
        observation["reports"] = reports.into();
        observation
    });
}
