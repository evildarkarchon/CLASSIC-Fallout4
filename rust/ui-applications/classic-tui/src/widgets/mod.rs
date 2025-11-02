/// Custom checkbox widget for TUI
pub mod checkbox;

/// Error dialog widget with clipboard support
pub mod error_dialog;

/// Interactive folder picker widget
pub mod folder_picker;

/// Markdown rendering for terminal with URL detection
pub mod markdown_viewer;

/// Update notification banner widget
pub mod update_notification;

pub use checkbox::Checkbox;
pub use error_dialog::{ErrorDialog, ErrorSeverity};
pub use folder_picker::{FolderPicker, FolderPickerState};
pub use markdown_viewer::{DetectedUrl, MarkdownRenderer, RenderedMarkdown};
pub use update_notification::UpdateNotification;
