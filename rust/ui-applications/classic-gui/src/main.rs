//! CLASSIC GUI - Application entry point
//!
//! Initializes the Slint GUI application and runs the event loop.
//! Uses the global Tokio runtime from classic-shared-core (ONE RUNTIME RULE).

slint::include_modules!();

use classic_shared_core::get_runtime;

fn main() {
    // Initialize global Tokio runtime before Slint event loop
    // This ensures ONE RUNTIME RULE compliance
    let _ = get_runtime();

    // Create main window
    let window = MainWindow::new().expect("Failed to create main window");

    // Run Slint event loop (blocks until window closes)
    window.run().expect("Failed to run application");
}
