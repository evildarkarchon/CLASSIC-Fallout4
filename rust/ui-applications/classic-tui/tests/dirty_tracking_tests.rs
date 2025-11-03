//! Tests for the dirty tracking optimization system.
//!
//! These tests ensure widgets correctly track when they need to be redrawn,
//! which is essential for efficient terminal rendering.

use classic_tui::widgets::*;

/// Tests for the dirty tracking optimization system
/// Ensures widgets correctly track when they need to be redrawn

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

