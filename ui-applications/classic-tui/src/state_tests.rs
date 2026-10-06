use std::path::PathBuf;

use super::InstallationRootNotFound;

// Which folder is the Installation Root is decided by `classic_config_core::locate_installation_root`
// and covered by its own tests; the TUI only owns what it tells the user when there is none.

#[test]
fn missing_installation_root_message_names_classic_data_and_both_search_starts() {
    let not_found = InstallationRootNotFound {
        executable_dir: Some(PathBuf::from("C:/Tools/CLASSIC/bin")),
        working_dir: Some(PathBuf::from("C:/Users/player")),
    };

    let message = not_found.to_string();

    assert!(message.starts_with("CLASSIC Data not found"), "{message}");
    assert!(message.contains("C:/Tools/CLASSIC/bin"), "{message}");
    assert!(message.contains("C:/Users/player"), "{message}");
}

#[test]
fn missing_installation_root_message_reports_unavailable_search_starts() {
    let not_found = InstallationRootNotFound {
        executable_dir: None,
        working_dir: None,
    };

    let message = not_found.to_string();

    assert!(message.starts_with("CLASSIC Data not found"), "{message}");
    assert_eq!(message.matches("(unavailable)").count(), 2, "{message}");
}
