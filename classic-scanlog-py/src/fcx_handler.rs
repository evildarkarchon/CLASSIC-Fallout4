//! Python bindings for FcxModeHandler - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::FcxModeHandler;
use pyo3::prelude::*;
use pyo3::types::PyModule;

/// Python wrapper for FcxModeHandler
#[pyclass(name = "FcxModeHandler")]
pub struct PyFcxModeHandler {
    inner: FcxModeHandler,
}

#[pymethods]
impl PyFcxModeHandler {
    /// Create a new instance

    #[new]
    pub fn new(fcx_mode: bool) -> Self {
        Self {
            inner: FcxModeHandler::new(fcx_mode),
        }
    }

    /// Check and update FCX mode state by calling Python code
    ///
    /// This method imports Python modules and runs file checks,
    /// then stores the results in the handler.
    ///
    /// IMPORTANT: This method assumes game paths have already been generated
    /// via game_generate_paths() before being called. This should be done
    /// in the scan executor or orchestrator initialization.
    pub fn check_fcx_mode(&mut self, py: Python<'_>) -> PyResult<()> {
        if !self.inner.fcx_mode {
            // FCX mode disabled - set default messages
            self.inner.set_main_files_result(
                "❌ FCX Mode is disabled, skipping game files check... \n-----\n".to_string()
            );
            self.inner.set_game_files_result(String::new());
            return Ok(());
        }

        // Import and call Python code to perform the checks
        // This is necessary because the checks require complex Python module imports
        let setup_module = PyModule::import(py, "ClassicLib.SetupCoordinator")?;
        let setup_coordinator_class = setup_module.getattr("SetupCoordinator")?;
        let coordinator = setup_coordinator_class.call0()?;

        // Get main files result
        let main_result: String = coordinator
            .call_method0("generate_combined_results")?
            .extract()?;
        self.inner.set_main_files_result(main_result);

        // Try to get game files result (fallback if not available)
        let game_result = match PyModule::import(py, "ClassicLib.ScanGame") {
            Ok(scan_game_module) => {
                match scan_game_module.getattr("generate_game_combined_result") {
                    Ok(scan_game_fn) => {
                        scan_game_fn.call0()?.extract::<String>().unwrap_or_else(|_| {
                            "Game files check not available\n".to_string()
                        })
                    }
                    Err(_) => "Game files check not available\n".to_string()
                }
            }
            Err(_) => "Game files check not available\n".to_string()
        };
        self.inner.set_game_files_result(game_result);

        Ok(())
    }

    /// Set main files check result
    pub fn set_main_files_result(&mut self, result: String) {
        self.inner.set_main_files_result(result);
    }

    /// Set game files check result
    pub fn set_game_files_result(&mut self, result: String) {
        self.inner.set_game_files_result(result);
    }

    /// Generate FCX mode messages
    pub fn get_fcx_messages(&self) -> Vec<String> {
        self.inner.get_fcx_messages().to_list()
    }

    /// Get FCX mode status message
    pub fn get_fcx_status_message(&self) -> String {
        self.inner.get_fcx_status_message()
    }

    /// Check if FCX mode has any results to display
    pub fn has_results(&self) -> bool {
        self.inner.has_results()
    }

    /// Get FCX mode enabled state
    #[getter]
    pub fn fcx_mode(&self) -> bool {
        self.inner.fcx_mode
    }

    /// Set FCX mode enabled state
    #[setter]
    pub fn set_fcx_mode(&mut self, value: bool) {
        self.inner.fcx_mode = value;
    }
}
