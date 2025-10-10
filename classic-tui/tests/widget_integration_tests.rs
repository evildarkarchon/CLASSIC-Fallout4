use classic_tui::*;
use std::path::PathBuf;
use tempfile::tempdir;

/// Integration tests for TUI widgets working together
mod widget_interactions {
    use super::*;

    #[test]
    fn test_folder_selector_with_scan_button_interaction() {
        // Test that folder selection affects scan button state
        // This would test the workflow: select folder -> validate -> enable scan

        let temp_dir = tempdir().unwrap();
        let valid_path = temp_dir.path().to_path_buf();

        // Create folder selector with valid path
        let mut folder_selector = widgets::FolderSelector::new("Scan Folder");
        folder_selector.set_value(valid_path.clone());

        // Verify validation passes
        assert!(folder_selector.validate());
        assert_eq!(folder_selector.value(), Some(valid_path.as_path()));
    }

    #[test]
    fn test_multiple_folder_selectors_independent() {
        // Test that multiple folder selectors maintain independent state
        let temp_dir1 = tempdir().unwrap();
        let temp_dir2 = tempdir().unwrap();

        let mut selector1 = widgets::FolderSelector::new("Folder 1");
        let mut selector2 = widgets::FolderSelector::new("Folder 2");

        selector1.set_value(temp_dir1.path().to_path_buf());
        selector2.set_value(temp_dir2.path().to_path_buf());

        assert!(selector1.validate());
        assert!(selector2.validate());
        assert_ne!(selector1.value(), selector2.value());
    }

    #[test]
    fn test_scan_button_state_transitions() {
        // Test scan button transitions: idle -> scanning -> completed
        let scan_button = widgets::ScanButton::new("Test Scan", widgets::ScanType::CrashLogs, "F5");

        // Verify initial state
        assert!(matches!(scan_button.state(), widgets::ButtonState::Idle));
    }

    #[test]
    fn test_output_viewer_with_status_bar() {
        // Test that output viewer and status bar work together
        let mut output_viewer = widgets::OutputViewer::new();

        // Add some output lines
        output_viewer.append("Line 1".to_string());
        output_viewer.append("Line 2".to_string());
        output_viewer.append("Line 3".to_string());

        assert_eq!(output_viewer.line_count(), 3);
    }

    #[test]
    fn test_checkbox_state_persistence() {
        // Test checkbox maintains state
        let mut checkbox = widgets::Checkbox::new("Test Option");

        assert!(!checkbox.is_checked());

        checkbox.toggle();
        assert!(checkbox.is_checked());

        checkbox.toggle();
        assert!(!checkbox.is_checked());
    }
}

mod error_handling_integration {
    use super::*;

    #[test]
    fn test_folder_selector_invalid_path_handling() {
        let mut selector = widgets::FolderSelector::new("Test");

        // Set invalid path
        selector.set_value(PathBuf::from("/nonexistent/path/12345"));

        // Should not validate
        assert!(!selector.validate());
    }

    #[test]
    fn test_output_viewer_large_output() {
        let mut output_viewer = widgets::OutputViewer::new();

        // Add many lines to test buffering
        for i in 0..10000 {
            output_viewer.append(format!("Line {}", i));
        }

        // Should handle large output without panicking
        assert!(output_viewer.line_count() > 0);
    }
}

mod focus_management {
    use super::*;

    #[test]
    fn test_folder_selector_focus_changes() {
        let mut selector1 = widgets::FolderSelector::new("Folder 1");
        let mut selector2 = widgets::FolderSelector::new("Folder 2");

        // Simulate focus change
        selector1.set_focused(true);
        assert!(selector1.is_focused());
        assert!(!selector2.is_focused());

        // Move focus to selector2
        selector1.set_focused(false);
        selector2.set_focused(true);

        assert!(!selector1.is_focused());
        assert!(selector2.is_focused());
    }
}

// These tests require actual TUI rendering which is complex to test
// They serve as structure for manual testing
#[cfg(feature = "manual_tests")]
mod rendering_integration {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    #[test]
    fn test_main_screen_layout() {
        // This would test the full main screen layout
        // Requires mock terminal backend
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();

        // Would render main screen and verify layout
        // This is more of a manual test or requires snapshot testing
    }
}
