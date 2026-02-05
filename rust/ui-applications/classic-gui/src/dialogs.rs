//! File dialog wrappers
//!
//! Provides async folder browsing using native OS dialogs via rfd.

use rfd::AsyncFileDialog;

/// Open a folder picker dialog and return the selected path
///
/// # Arguments
/// * `title` - Dialog title shown in the title bar
/// * `start_dir` - Initial directory to show (optional)
///
/// # Returns
/// The selected folder path as a string, or None if cancelled
pub async fn browse_folder(title: &str, start_dir: Option<&str>) -> Option<String> {
    let mut dialog = AsyncFileDialog::new().set_title(title);

    if let Some(dir) = start_dir {
        if !dir.is_empty() {
            dialog = dialog.set_directory(dir);
        }
    }

    dialog
        .pick_folder()
        .await
        .map(|handle| handle.path().to_string_lossy().to_string())
}
