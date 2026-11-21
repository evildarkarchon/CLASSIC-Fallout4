use super::*;
use classic_shared_core::get_runtime;
use tempfile::tempdir;

#[test]
fn simplified_log_path_adds_the_simple_suffix_before_the_extension() {
    let directory = Path::new("C:/CLASSIC/Simplified Logs");

    assert_eq!(
        simplified_log_path(
            directory,
            Path::new("C:/CLASSIC/Crash Logs/crash-2024-06-05-08-20-22.log")
        ),
        directory.join("crash-2024-06-05-08-20-22-simple.log")
    );
    assert_eq!(
        simplified_log_path(directory, Path::new("D:/picked/crash-no-extension")),
        directory.join("crash-no-extension-simple")
    );
}

#[test]
fn simplified_logs_directory_sits_beside_crash_logs_in_the_installation_root() {
    let root = Path::new("C:/CLASSIC");

    let directory = simplified_logs_directory(root);

    assert_eq!(directory, root.join("Simplified Logs"));
    assert!(!directory.starts_with(root.join("Crash Logs")));
}

#[test]
fn is_inside_simplified_logs_matches_the_folder_and_its_contents_only() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();
    let simplified = simplified_logs_directory(root);
    let nested = simplified.join("nested");
    std::fs::create_dir_all(&nested).expect("simplified fixture folders should be created");
    let copy = simplified.join("crash-a-simple.log");
    std::fs::write(&copy, "copy").expect("simplified copy fixture should be written");
    let crash_logs = root.join("Crash Logs");
    std::fs::create_dir_all(&crash_logs).expect("crash logs fixture should be created");

    assert!(is_inside_simplified_logs(root, &simplified));
    assert!(is_inside_simplified_logs(root, &nested));
    assert!(is_inside_simplified_logs(root, &copy));
    // A path that walks out and back in through `..` is still the same folder.
    assert!(is_inside_simplified_logs(
        root,
        &crash_logs.join("..").join("Simplified Logs")
    ));
    assert!(!is_inside_simplified_logs(root, root));
    assert!(!is_inside_simplified_logs(root, &crash_logs));
}

#[test]
fn is_inside_simplified_logs_is_false_when_the_folder_does_not_exist() {
    let temp = tempdir().expect("tempdir should succeed");
    let root = temp.path();

    assert!(!is_inside_simplified_logs(
        root,
        &simplified_logs_directory(root)
    ));
}

#[test]
fn write_simplified_log_creates_the_folder_and_replaces_an_existing_copy() {
    let temp = tempdir().expect("tempdir should succeed");
    let directory = simplified_logs_directory(temp.path());
    let crash_log = temp.path().join("Crash Logs").join("crash-write.log");
    let file_io = FileIOCore::default();

    let first = get_runtime()
        .block_on(write_simplified_log(
            &file_io,
            &directory,
            &crash_log,
            &["first".to_string(), "pass".to_string()],
        ))
        .expect("the first copy should be written");
    let second = get_runtime()
        .block_on(write_simplified_log(
            &file_io,
            &directory,
            &crash_log,
            &["second".to_string()],
        ))
        .expect("a rescan should replace the copy");

    assert_eq!(first, directory.join("crash-write-simple.log"));
    assert_eq!(second, first);
    assert_eq!(
        std::fs::read_to_string(&second).expect("copy should be readable"),
        "second\n"
    );
    assert!(
        !crash_log.exists(),
        "writing a copy must never create or touch the Crash Log"
    );
}
