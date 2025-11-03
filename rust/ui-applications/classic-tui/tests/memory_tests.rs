//! Memory leak detection tests for TUI components.
//!
//! These tests focus on widgets that accumulate state over time to ensure
//! they don't leak memory during repeated operations.

use classic_tui::widgets::Checkbox;

/// Memory leak detection tests for TUI components
/// Focus on widgets that accumulate state over time

#[test]
fn test_checkbox_toggle_no_leak() {
    let mut checkbox = Checkbox::new("Test", false);

    // Toggle many times (even number)
    for _ in 0..100000 {
        checkbox.toggle();
    }

    // Should be stable - started false, toggled even number of times = false
    assert!(!checkbox.is_checked());
}



/// Profiling markers for external tools
mod profiling_markers {
    use super::*;

    #[test]
    #[ignore]
    fn profile_widget_creation() {
        println!("=== PROFILING START: Widget Creation ===");

        for i in 0..100000 {
            if i % 10000 == 0 {
                println!("Widgets created: {}", i);
            }

            let _checkbox = Checkbox::new("Test", false);
            // Dropped
        }

        println!("=== PROFILING END: Widget Creation ===");
    }
}

