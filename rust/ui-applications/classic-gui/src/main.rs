//! CLASSIC GUI - Application entry point
//!
//! Initializes the Slint GUI application and runs the event loop.
//! Uses the global Tokio runtime from classic-shared-core (ONE RUNTIME RULE).

slint::include_modules!();

use std::sync::Arc;

use classic_shared_core::{get_runtime, AsyncBridge};
use tokio_util::sync::CancellationToken;

use classic_gui::ScanWindowProperties;

// Implement ScanWindowProperties for the generated MainWindow
impl ScanWindowProperties for MainWindow {
    fn set_scan_progress(&self, value: f32) {
        self.set_scan_progress(value);
    }

    fn set_scan_status(&self, value: slint::SharedString) {
        self.set_scan_status(value);
    }

    fn set_scan_in_progress(&self, value: bool) {
        self.set_scan_in_progress(value);
    }
}

/// Application state shared between callbacks
struct AppState {
    /// Cancellation token for current scan operation
    cancel_token: Option<CancellationToken>,
}

fn main() {
    // Initialize global Tokio runtime before Slint event loop
    // This ensures ONE RUNTIME RULE compliance
    let _ = get_runtime();

    // Create main window
    let window = MainWindow::new().expect("Failed to create main window");

    // Set up callbacks
    setup_callbacks(&window);

    // Run Slint event loop (blocks until window closes)
    window.run().expect("Failed to run application");
}

fn setup_callbacks(window: &MainWindow) {
    // Shared state for cancellation
    // Using Arc<parking_lot::Mutex> for thread-safe mutable access
    let state = Arc::new(parking_lot::Mutex::new(AppState {
        cancel_token: None,
    }));

    // Start scan callback
    {
        let window_weak = window.as_weak();
        let state = Arc::clone(&state);

        window.on_start_scan(move || {
            let window_weak = window_weak.clone();

            // Create new cancellation token
            let cancel_token = CancellationToken::new();

            // Store token for cancel button
            {
                let mut state = state.lock();
                state.cancel_token = Some(cancel_token.clone());
            }

            // Set UI to scanning state
            if let Some(w) = window_weak.upgrade() {
                w.set_scan_in_progress(true);
                w.set_scan_progress(0.0);
                w.set_scan_status("Starting scan...".into());
            }

            // Spawn async scan operation
            AsyncBridge::run_with_ui_update(
                classic_gui::simulate_scan(window_weak.clone(), cancel_token),
                move |result| {
                    match result {
                        Ok(_msg) => {
                            // Success is already handled in simulate_scan
                            // This callback is for any final cleanup
                        }
                        Err(_e) => {
                            // Error already shown in UI by simulate_scan
                            // Future: show modal error dialog here
                        }
                    }
                },
            );
        });
    }

    // Cancel scan callback
    {
        let state = Arc::clone(&state);

        window.on_cancel_scan(move || {
            let state = state.lock();
            if let Some(ref token) = state.cancel_token {
                token.cancel();
            }
        });
    }
}
