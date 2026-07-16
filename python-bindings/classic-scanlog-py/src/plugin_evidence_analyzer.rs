//! Python projection of focused semantic Plugin Evidence analysis.

use classic_scanlog_core::{
    PluginEvidenceAnalysisInput as CoreAnalysisInput,
    PluginEvidenceAnalysisResult as CoreAnalysisResult, PluginEvidenceAnalyzer as CoreAnalyzer,
};
use classic_shared::without_gil;
use pyo3::prelude::*;

use crate::crashgen_settings_analyzer::{PyAnalyzerKind, analyzer_error_to_pyerr};

/// Immutable owned input for one aggregate Plugin Evidence analysis call.
#[pyclass(name = "PluginEvidenceAnalysisInput", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyPluginEvidenceAnalysisInput {
    inner: CoreAnalysisInput,
}

#[pymethods]
impl PyPluginEvidenceAnalysisInput {
    /// Creates owned call-stack and plugin facts for one analysis call.
    #[new]
    pub fn new(call_stack: Vec<String>, plugins: Vec<String>) -> Self {
        Self {
            inner: CoreAnalysisInput {
                call_stack,
                plugins,
            },
        }
    }
}

/// Immutable Python view of one typed Plugin Evidence item.
#[pyclass(name = "PluginEvidence", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyPluginEvidence {
    #[pyo3(get)]
    plugin: String,
    #[pyo3(get)]
    occurrences: u32,
}

/// Immutable completed Plugin Evidence analysis result.
#[pyclass(name = "PluginEvidenceAnalysisResult", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyPluginEvidenceAnalysisResult {
    #[pyo3(get)]
    evidence: Vec<PyPluginEvidence>,
}

impl From<CoreAnalysisResult> for PyPluginEvidenceAnalysisResult {
    fn from(value: CoreAnalysisResult) -> Self {
        Self {
            evidence: value
                .evidence
                .into_iter()
                .map(|entry| PyPluginEvidence {
                    plugin: entry.plugin,
                    occurrences: entry.occurrences,
                })
                .collect(),
        }
    }
}

/// Immutable Python handle for repeated concurrent Plugin Evidence analysis.
#[pyclass(name = "PluginEvidenceAnalyzer", frozen)]
#[derive(Debug)]
pub struct PyPluginEvidenceAnalyzer {
    inner: CoreAnalyzer,
}

#[pymethods]
impl PyPluginEvidenceAnalyzer {
    /// Validates and normalizes owned plugin-ignore configuration immediately.
    #[new]
    pub fn new(ignored_plugins: Vec<String>) -> PyResult<Self> {
        let inner = CoreAnalyzer::new(ignored_plugins).map_err(analyzer_error_to_pyerr)?;
        Ok(Self { inner })
    }

    /// Returns the stable kind of this analyzer handle.
    #[getter]
    pub fn kind(&self) -> PyAnalyzerKind {
        PyAnalyzerKind::PluginEvidence
    }

    /// Runs aggregate semantic analysis while releasing the GIL.
    pub fn analyze(
        &self,
        py: Python<'_>,
        input: PyPluginEvidenceAnalysisInput,
    ) -> PyResult<PyPluginEvidenceAnalysisResult> {
        without_gil(py, || self.inner.analyze(input.inner))
            .map(Into::into)
            .map_err(analyzer_error_to_pyerr)
    }
}

/// Registers the Plugin Evidence semantic analyzer family in one Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPluginEvidenceAnalysisInput>()?;
    m.add_class::<PyPluginEvidence>()?;
    m.add_class::<PyPluginEvidenceAnalysisResult>()?;
    m.add_class::<PyPluginEvidenceAnalyzer>()?;
    Ok(())
}

#[cfg(test)]
#[path = "plugin_evidence_analyzer_tests.rs"]
mod tests;
