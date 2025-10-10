use classic_tui::widgets::*;
use std::path::PathBuf;

/// Tests for the dirty tracking optimization system
/// Ensures widgets correctly track when they need to be redrawn

#[test]
fn test_output_viewer_dirty_tracking() {
    let mut viewer = OutputViewer::new();

    // Starts dirty (needs initial render)
    assert!(viewer.is_dirty());

    // Mark clean
    viewer.mark_clean();
    assert!(!viewer.is_dirty());

    // Append marks dirty
    viewer.append("New line".to_string());
    assert!(viewer.is_dirty());

    viewer.mark_clean();
    assert!(!viewer.is_dirty());

    // Clear marks dirty
    viewer.clear();
    assert!(viewer.is_dirty());

    viewer.mark_clean();

    // Scroll up marks dirty only if it actually changes
    viewer.append("Line 1".to_string());
    viewer.append("Line 2".to_string());
    viewer.append("Line 3".to_string());
    viewer.mark_clean();

    viewer.scroll_up(1);
    assert!(viewer.is_dirty(), "Scroll up should mark dirty");

    viewer.mark_clean();

    // Scroll down marks dirty only if it actually changes
    viewer.scroll_down(1, 10);
    assert!(viewer.is_dirty(), "Scroll down should mark dirty");
}

#[test]
fn test_output_viewer_no_dirty_on_no_change() {
    let mut viewer = OutputViewer::new();
    viewer.mark_clean();

    // Scroll when already at top should not mark dirty
    viewer.scroll_up(5);
    assert!(!viewer.is_dirty(), "Scroll up at top should not mark dirty");

    // Scroll when already at bottom should not mark dirty
    viewer.append("Line".to_string());
    viewer.mark_clean();
    viewer.scroll_down(5, 10);
    assert!(
        !viewer.is_dirty(),
        "Scroll down at bottom should not mark dirty"
    );
}

#[test]
fn test_folder_selector_dirty_tracking() {
    let mut selector = FolderSelector::new("Test Folder");

    // Starts dirty
    assert!(selector.is_dirty());

    // Mark clean
    selector.mark_clean();
    assert!(!selector.is_dirty());

    // Set value marks dirty
    let path = PathBuf::from("C:\\Test");
    selector.set_value(path.clone());
    assert!(selector.is_dirty());

    selector.mark_clean();

    // Set same value again should NOT mark dirty
    selector.set_value(path.clone());
    assert!(
        !selector.is_dirty(),
        "Setting same value should not mark dirty"
    );

    // Different value marks dirty
    selector.set_value(PathBuf::from("C:\\Other"));
    assert!(selector.is_dirty());

    selector.mark_clean();

    // Focus change marks dirty
    selector.set_focused(true);
    assert!(selector.is_dirty(), "Focus change should mark dirty");

    selector.mark_clean();

    // Setting same focus should not mark dirty
    selector.set_focused(true);
    assert!(
        !selector.is_dirty(),
        "Setting same focus should not mark dirty"
    );
}

#[test]
fn test_scan_button_dirty_tracking() {
    let mut button = ScanButton::new("Test Scan", ScanType::CrashLogs, "F5");

    // Starts dirty
    assert!(button.is_dirty());

    // Mark clean
    button.mark_clean();
    assert!(!button.is_dirty());

    // Start scan marks dirty
    button.start_scan();
    assert!(button.is_dirty());

    button.mark_clean();

    // Progress update marks dirty (if >1% change)
    button.update_progress(0.5);
    assert!(button.is_dirty());

    button.mark_clean();

    // Tiny progress change should not mark dirty
    button.update_progress(0.505);
    assert!(
        !button.is_dirty(),
        "Progress change <1% should not mark dirty"
    );

    // Large progress change marks dirty
    button.update_progress(0.6);
    assert!(button.is_dirty(), "Progress change >1% should mark dirty");

    button.mark_clean();

    // Complete marks dirty
    button.complete();
    assert!(button.is_dirty());

    button.mark_clean();

    // Reset marks dirty
    button.reset();
    assert!(button.is_dirty());
}

#[test]
fn test_checkbox_dirty_tracking() {
    let mut checkbox = Checkbox::new("Test Option", false);

    // Starts dirty
    assert!(checkbox.is_dirty());

    // Mark clean
    checkbox.mark_clean();
    assert!(!checkbox.is_dirty());

    // Toggle marks dirty
    checkbox.toggle();
    assert!(checkbox.is_dirty());

    checkbox.mark_clean();

    // Set same value should not mark dirty
    checkbox.set_checked(true);
    assert!(
        !checkbox.is_dirty(),
        "Setting same value should not mark dirty"
    );

    // Set different value marks dirty
    checkbox.set_checked(false);
    assert!(checkbox.is_dirty());

    checkbox.mark_clean();

    // Focus change marks dirty
    checkbox.set_focused(true);
    assert!(checkbox.is_dirty());

    checkbox.mark_clean();

    // Same focus should not mark dirty
    checkbox.set_focused(true);
    assert!(!checkbox.is_dirty());
}

#[test]
fn test_status_bar_dirty_tracking() {
    let mut status = StatusBar::new();

    // Starts dirty
    assert!(status.is_dirty());

    // Mark clean
    status.mark_clean();
    assert!(!status.is_dirty());

    // Set message marks dirty
    status.set_message("Test message");
    assert!(status.is_dirty());

    status.mark_clean();

    // Set same message should not mark dirty
    status.set_message("Test message");
    assert!(
        !status.is_dirty(),
        "Setting same message should not mark dirty"
    );

    // Clear message marks dirty
    status.clear_message();
    assert!(status.is_dirty());

    status.mark_clean();

    // Clear already empty should not mark dirty
    status.clear_message();
    assert!(
        !status.is_dirty(),
        "Clearing empty message should not mark dirty"
    );

    // Set key hints marks dirty
    status.set_key_hints("New hints");
    assert!(status.is_dirty());

    status.mark_clean();

    // Set same hints should not mark dirty
    status.set_key_hints("New hints");
    assert!(!status.is_dirty());
}

#[test]
fn test_dirty_tracking_optimization_efficiency() {
    // Verify that dirty tracking reduces unnecessary renders
    let mut viewer = OutputViewer::new();
    let mut renders_needed = 0;

    // Initial state
    if viewer.is_dirty() {
        renders_needed += 1;
        viewer.mark_clean();
    }

    // 100 no-op operations
    for _ in 0..100 {
        viewer.scroll_up(0); // No actual scroll
        if viewer.is_dirty() {
            renders_needed += 1;
            viewer.mark_clean();
        }
    }

    // Should only need initial render (1 render total)
    assert_eq!(
        renders_needed, 1,
        "No-op operations should not trigger renders"
    );

    // Now make real changes
    for i in 0..10 {
        viewer.append(format!("Line {}", i));
        if viewer.is_dirty() {
            renders_needed += 1;
            viewer.mark_clean();
        }
    }

    // Should have rendered 1 initial + 10 appends = 11 total
    assert_eq!(
        renders_needed, 11,
        "Each real change should trigger exactly one render"
    );
}

#[test]
fn test_multiple_widgets_dirty_coordination() {
    // Test that multiple widgets can independently track dirty state
    let mut viewer = OutputViewer::new();
    let mut button = ScanButton::new("Test", ScanType::CrashLogs, "F5");
    let mut selector = FolderSelector::new("Test");

    // All start dirty
    assert!(viewer.is_dirty());
    assert!(button.is_dirty());
    assert!(selector.is_dirty());

    // Clean all
    viewer.mark_clean();
    button.mark_clean();
    selector.mark_clean();

    // Change only viewer
    viewer.append("Test".to_string());
    assert!(viewer.is_dirty(), "Viewer should be dirty");
    assert!(!button.is_dirty(), "Button should still be clean");
    assert!(!selector.is_dirty(), "Selector should still be clean");

    viewer.mark_clean();

    // Change only button
    button.start_scan();
    assert!(!viewer.is_dirty(), "Viewer should still be clean");
    assert!(button.is_dirty(), "Button should be dirty");
    assert!(!selector.is_dirty(), "Selector should still be clean");

    button.mark_clean();

    // Change only selector
    selector.set_value(PathBuf::from("C:\\Test"));
    assert!(!viewer.is_dirty(), "Viewer should still be clean");
    assert!(!button.is_dirty(), "Button should still be clean");
    assert!(selector.is_dirty(), "Selector should be dirty");
}
