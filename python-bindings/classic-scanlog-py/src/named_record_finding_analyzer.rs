//! Python projection of focused semantic Named Record Finding analysis.

use classic_scanlog_core::{
    NamedRecordFindingAnalysisInput as CoreAnalysisInput,
    NamedRecordFindingAnalysisResult as CoreAnalysisResult,
    NamedRecordFindingAnalyzer as CoreAnalyzer,
};
use classic_shared::without_gil;
use pyo3::prelude::*;

use crate::crashgen_settings_analyzer::{PyAnalyzerKind, analyzer_error_to_pyerr};

/// Immutable owned input for one aggregate Named Record Finding analysis call.
#[pyclass(name = "NamedRecordFindingAnalysisInput", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyNamedRecordFindingAnalysisInput {
    inner: CoreAnalysisInput,
}

#[pymethods]
impl PyNamedRecordFindingAnalysisInput {
    /// Creates owned Crash Log lines for one analysis call.
    #[new]
    pub fn new(crash_lines: Vec<String>) -> Self {
        Self {
            inner: CoreAnalysisInput { crash_lines },
        }
    }
}

/// Immutable Python view of one distinct Named Record Finding.
#[pyclass(name = "NamedRecordFinding", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyNamedRecordFinding {
    #[pyo3(get)]
    record: String,
    #[pyo3(get)]
    occurrences: u32,
}

/// Immutable completed Named Record Finding analysis result.
#[pyclass(name = "NamedRecordFindingAnalysisResult", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyNamedRecordFindingAnalysisResult {
    #[pyo3(get)]
    findings: Vec<PyNamedRecordFinding>,
}

impl From<CoreAnalysisResult> for PyNamedRecordFindingAnalysisResult {
    fn from(value: CoreAnalysisResult) -> Self {
        Self {
            findings: value
                .findings
                .into_iter()
                .map(|finding| PyNamedRecordFinding {
                    record: finding.record,
                    occurrences: finding.occurrences,
                })
                .collect(),
        }
    }
}

/// Immutable Python handle for repeated concurrent Named Record Finding analysis.
#[pyclass(name = "NamedRecordFindingAnalyzer", frozen)]
#[derive(Debug)]
pub struct PyNamedRecordFindingAnalyzer {
    inner: CoreAnalyzer,
}

#[pymethods]
impl PyNamedRecordFindingAnalyzer {
    /// Validates configuration and compiles matcher state immediately.
    #[new]
    pub fn new(target_records: Vec<String>, ignored_records: Vec<String>) -> PyResult<Self> {
        let inner =
            CoreAnalyzer::new(target_records, ignored_records).map_err(analyzer_error_to_pyerr)?;
        Ok(Self { inner })
    }

    /// Returns the stable kind of this analyzer handle.
    #[getter]
    pub fn kind(&self) -> PyAnalyzerKind {
        PyAnalyzerKind::NamedRecordFinding
    }

    /// Runs aggregate semantic analysis while releasing the GIL.
    pub fn analyze(
        &self,
        py: Python<'_>,
        input: PyNamedRecordFindingAnalysisInput,
    ) -> PyResult<PyNamedRecordFindingAnalysisResult> {
        without_gil(py, || self.inner.analyze(input.inner))
            .map(Into::into)
            .map_err(analyzer_error_to_pyerr)
    }
}

/// Registers the Named Record Finding semantic analyzer family in one Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyNamedRecordFindingAnalysisInput>()?;
    m.add_class::<PyNamedRecordFinding>()?;
    m.add_class::<PyNamedRecordFindingAnalysisResult>()?;
    m.add_class::<PyNamedRecordFindingAnalyzer>()?;
    Ok(())
}

#[cfg(test)]
#[path = "named_record_finding_analyzer_tests.rs"]
mod tests;
