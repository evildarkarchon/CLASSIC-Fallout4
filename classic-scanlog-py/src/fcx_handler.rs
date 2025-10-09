//! Python bindings for FcxModeHandler - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::FcxModeHandler;
use pyo3::prelude::*;

/// Python wrapper for FcxModeHandler
#[pyclass(name = "FcxModeHandler")]
pub struct PyFcxModeHandler {
    inner: FcxModeHandler,
}

#[pymethods]
impl PyFcxModeHandler {
    #[new]
    pub fn new(fcx_mode: bool) -> Self {
        Self {
            inner: FcxModeHandler::new(fcx_mode),
        }
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
