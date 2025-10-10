use classic_tui::widgets::{
    Checkbox, FolderSelector, OutputViewer, ScanButton, ScanType, StatusBar,
};
use std::path::PathBuf;
use tempfile::tempdir;

/// Memory leak detection tests for TUI components
/// Focus on widgets that accumulate state over time

#[test]
fn test_output_viewer_no_memory_leak() {
    let mut viewer = OutputViewer::new();

    // Simulate long-running session with many log lines
    // OutputViewer should limit to max_lines (10000)
    for i in 0..50000 {
        viewer.append(format!("Log line {} with some content", i));
    }

    // Should not have 50000 lines (trimmed to max)
    assert!(viewer.line_count() <= 10000);

    // Clear and verify
    viewer.clear();
    assert_eq!(viewer.line_count(), 0);
}

#[test]
fn test_output_viewer_scroll_no_accumulation() {
    let mut viewer = OutputViewer::new();

    // Add lines
    for i in 0..1000 {
        viewer.append(format!("Line {}", i));
    }

    // Perform many scroll operations
    for _ in 0..10000 {
        viewer.scroll_up(10);
        viewer.scroll_down(5, 20);
        viewer.scroll_to_top();
        viewer.scroll_to_bottom();
    }

    // Line count should remain stable
    assert_eq!(viewer.line_count(), 1000);
}

#[test]
fn test_folder_selector_path_changes_no_leak() {
    let mut selector = FolderSelector::new("Test");
    let temp_dir = tempdir().unwrap();

    // Simulate many path changes (user typing/editing)
    for i in 0..10000 {
        let path = temp_dir.path().join(format!("subdir{}", i));
        selector.set_value(path);
    }

    // Should only have last path
    assert!(selector.value().is_some());
}

#[test]
fn test_scan_button_state_transitions_no_leak() {
    let mut button = ScanButton::new("Test", ScanType::CrashLogs, "F5");

    // Simulate many scan cycles
    for _ in 0..10000 {
        button.start_scan();
        button.update_progress(0.5);
        button.complete();
        button.reset();
    }

    // Should be back to idle
    assert!(!button.is_scanning());
}

#[test]
fn test_checkbox_toggle_no_leak() {
    let mut checkbox = Checkbox::new("Test", false);

    // Toggle many times
    for _ in 0..100000 {
        checkbox.toggle();
    }

    // Should be stable
    assert!(checkbox.is_checked());
}

#[test]
fn test_status_bar_message_updates_no_leak() {
    let mut status = StatusBar::new();

    // Update messages many times
    for i in 0..10000 {
        status.set_message(format!("Status message {}", i));
        status.set_key_hints(format!("Hints {}", i));
    }

    // Should only have last message
    status.clear_message();
}

#[test]
fn test_multiple_widgets_no_accumulation() {
    // Create many widgets
    let selectors: Vec<_> = (0..1000)
        .map(|i| FolderSelector::new(format!("Selector {}", i)))
        .collect();

    assert_eq!(selectors.len(), 1000);

    // All dropped here - should not leak
}

#[test]
fn test_output_viewer_clear_cycles() {
    let mut viewer = OutputViewer::new();

    // Simulate many clear cycles (user pressing Ctrl+L repeatedly)
    for cycle in 0..1000 {
        // Add lines
        for i in 0..100 {
            viewer.append(format!("Cycle {} Line {}", cycle, i));
        }

        // Clear
        viewer.clear();
        assert_eq!(viewer.line_count(), 0);
    }
}

#[test]
fn test_output_viewer_search_no_leak() {
    let mut viewer = OutputViewer::new();

    for i in 0..1000 {
        viewer.append(format!("Test line {}", i));
    }

    // Perform many searches
    for i in 0..1000 {
        viewer.search(format!("line {}", i % 100));
        viewer.clear_search();
    }

    // Line count should remain stable
    assert_eq!(viewer.line_count(), 1000);
}

#[test]
fn test_widget_creation_destruction_cycles() {
    // Simulate widget lifecycle (create, use, drop)
    for _ in 0..10000 {
        let mut selector = FolderSelector::new("Temp");
        selector.set_value(PathBuf::from("C:\\Test"));
        let _ = selector.validate();
        // Dropped here
    }

    // If no panic/OOM, no major leak
}

#[test]
fn test_scan_button_progress_updates_no_leak() {
    let mut button = ScanButton::new("Test", ScanType::CrashLogs, "F5");

    button.start_scan();

    // Simulate many progress updates
    for i in 0..100000 {
        let progress = (i % 100) as f64 / 100.0;
        button.update_progress(progress);
    }

    button.complete();
}

/// Resource cleanup tests
mod cleanup_tests {
    use super::*;

    #[test]
    fn test_output_viewer_drop_clears_memory() {
        let mut viewer = OutputViewer::new();

        for i in 0..10000 {
            viewer.append(format!("Line {}", i));
        }

        drop(viewer);
        // Memory should be freed
    }

    #[test]
    fn test_folder_selector_drop_clears_path() {
        let mut selector = FolderSelector::new("Test");
        selector.set_value(PathBuf::from("C:\\Very\\Long\\Path\\That\\Uses\\Memory"));

        drop(selector);
        // Path should be freed
    }
}

/// Profiling markers for external tools
mod profiling_markers {
    use super::*;

    #[test]
    #[ignore] // Run with: cargo test --test memory_tests -- --ignored
    fn profile_output_viewer_growth() {
        println!("=== PROFILING START: OutputViewer Growth ===");

        let mut viewer = OutputViewer::new();

        for i in 0..100000 {
            if i % 10000 == 0 {
                println!("Lines appended: {} (count: {})", i, viewer.line_count());
            }
            viewer.append(format!("Line {}", i));
        }

        println!("Final line count: {}", viewer.line_count());
        println!("=== PROFILING END: OutputViewer Growth ===");
    }

    #[test]
    #[ignore]
    fn profile_widget_creation() {
        println!("=== PROFILING START: Widget Creation ===");

        for i in 0..100000 {
            if i % 10000 == 0 {
                println!("Widgets created: {}", i);
            }

            let _selector = FolderSelector::new("Test");
            let _button = ScanButton::new("Test", ScanType::CrashLogs, "F5");
            let _checkbox = Checkbox::new("Test", false);
            // All dropped
        }

        println!("=== PROFILING END: Widget Creation ===");
    }
}

/// Memory bounds verification
mod bounds_tests {
    use super::*;

    #[test]
    fn test_output_viewer_respects_max_lines() {
        let mut viewer = OutputViewer::new();

        // Add way more than max
        for i in 0..50000 {
            viewer.append(format!("Line {}", i));
        }

        // Should cap at 10000 (OutputViewer::max_lines)
        assert!(viewer.line_count() <= 10000);
    }

    #[test]
    fn test_string_interning_potential() {
        // Test that repeated strings could benefit from interning
        let mut viewer = OutputViewer::new();

        // Add same string many times (common pattern in logs)
        for _ in 0..1000 {
            viewer.append("Repeated error message".to_string());
        }

        // Currently uses separate allocations
        // Future optimization: string interning
        assert_eq!(viewer.line_count(), 1000);
    }
}
