//! Python projection of focused semantic FormID Finding analysis.

use std::path::PathBuf;

use classic_database_core::{
    FormIdValueLookup, FormIdValueLookupEntry, FormIdValueLookupInMemoryReply,
};
use classic_scanlog_core::{
    AnalyzerErrorCode as CoreAnalyzerErrorCode, FormIDFindingAnalysisInput as CoreAnalysisInput,
    FormIDFindingAnalysisResult as CoreAnalysisResult, FormIDFindingAnalyzer as CoreAnalyzer,
    FormIDPlugin as CorePlugin, FormIDValueLookupStatus as CoreLookupStatus,
};
use classic_shared::without_gil_block_on;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::crashgen_settings_analyzer::{
    PyAnalyzerKind, analyzer_error_parts_to_pyerr, analyzer_error_to_pyerr,
};

/// Stable callback-free reply kind for deterministic analyzer lookup fixtures.
#[pyclass(
    name = "FormIDFindingLookupReplyKind",
    eq,
    eq_int,
    frozen,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyFormIDFindingLookupReplyKind {
    /// Successful lookup miss.
    Missing = 0,
    /// Successful lookup hit using the entry's value.
    Found = 1,
    /// Deterministic operational failure using the entry's error message.
    OperationalFailure = 2,
}

/// One fully owned deterministic lookup reply used during analyzer construction.
#[pyclass(name = "FormIDFindingLookupEntry", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyFormIDFindingLookupEntry {
    formid: String,
    plugin: String,
    reply_kind: PyFormIDFindingLookupReplyKind,
    value: Option<String>,
    error_message: Option<String>,
}

#[pymethods]
impl PyFormIDFindingLookupEntry {
    /// Creates one callback-free deterministic lookup reply.
    #[new]
    #[pyo3(signature = (formid, plugin, reply_kind, value=None, error_message=None))]
    pub fn new(
        formid: String,
        plugin: String,
        reply_kind: PyFormIDFindingLookupReplyKind,
        value: Option<String>,
        error_message: Option<String>,
    ) -> Self {
        Self {
            formid,
            plugin,
            reply_kind,
            value,
            error_message,
        }
    }
}

/// One owned plugin identity and load-order prefix.
#[pyclass(name = "FormIDPlugin", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyFormIDPlugin {
    inner: CorePlugin,
}

#[pymethods]
impl PyFormIDPlugin {
    /// Creates one plugin-prefix fact for semantic resolution.
    #[new]
    pub fn new(name: String, prefix: String) -> Self {
        Self {
            inner: CorePlugin { name, prefix },
        }
    }
}

/// Immutable owned input for one aggregate FormID Finding analysis call.
#[pyclass(name = "FormIDFindingAnalysisInput", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyFormIDFindingAnalysisInput {
    inner: CoreAnalysisInput,
}

#[pymethods]
impl PyFormIDFindingAnalysisInput {
    /// Creates owned Crash Log evidence and plugin-prefix facts.
    #[new]
    pub fn new(crash_lines: Vec<String>, plugins: Vec<PyFormIDPlugin>) -> Self {
        Self {
            inner: CoreAnalysisInput {
                crash_lines,
                plugins: plugins.into_iter().map(|plugin| plugin.inner).collect(),
            },
        }
    }
}

/// Stable semantic state of optional FormID Value Lookup for one finding.
#[pyclass(
    name = "FormIDValueLookupStatus",
    eq,
    eq_int,
    frozen,
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyFormIDValueLookupStatus {
    /// Plugin resolution failed, so lookup was inapplicable.
    NotApplicable = 0,
    /// Lookup was explicitly disabled.
    Disabled = 1,
    /// Lookup completed successfully without a value.
    Missing = 2,
    /// Lookup completed successfully with a value.
    Found = 3,
}

impl From<CoreLookupStatus> for PyFormIDValueLookupStatus {
    fn from(value: CoreLookupStatus) -> Self {
        match value {
            CoreLookupStatus::NotApplicable => Self::NotApplicable,
            CoreLookupStatus::Disabled => Self::Disabled,
            CoreLookupStatus::Missing => Self::Missing,
            CoreLookupStatus::Found => Self::Found,
        }
    }
}

/// Immutable Python view of one distinct semantic FormID Finding.
#[pyclass(name = "FormIDFinding", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyFormIDFinding {
    #[pyo3(get)]
    identifier: String,
    #[pyo3(get)]
    occurrences: u32,
    #[pyo3(get)]
    plugin: Option<String>,
    #[pyo3(get)]
    value_lookup_status: PyFormIDValueLookupStatus,
    #[pyo3(get)]
    value: Option<String>,
}

/// Immutable completed FormID Finding analysis result.
#[pyclass(name = "FormIDFindingAnalysisResult", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyFormIDFindingAnalysisResult {
    #[pyo3(get)]
    findings: Vec<PyFormIDFinding>,
}

impl From<CoreAnalysisResult> for PyFormIDFindingAnalysisResult {
    fn from(value: CoreAnalysisResult) -> Self {
        Self {
            findings: value
                .findings
                .into_iter()
                .map(|finding| PyFormIDFinding {
                    identifier: finding.identifier,
                    occurrences: finding.occurrences,
                    plugin: finding.plugin,
                    value_lookup_status: finding.value_lookup_status.into(),
                    value: finding.value,
                })
                .collect(),
        }
    }
}

/// Immutable Python handle for repeated aggregate FormID Finding analysis.
#[pyclass(name = "FormIDFindingAnalyzer", frozen, skip_from_py_object)]
#[derive(Clone, Debug)]
pub struct PyFormIDFindingAnalyzer {
    inner: CoreAnalyzer,
}

impl Default for PyFormIDFindingAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyFormIDFindingAnalyzer {
    /// Creates an analyzer with FormID Value Lookup explicitly disabled.
    #[new]
    pub fn new() -> Self {
        Self {
            inner: CoreAnalyzer::new(FormIdValueLookup::disabled()),
        }
    }

    /// Creates an analyzer from fully owned deterministic lookup replies.
    #[staticmethod]
    pub fn in_memory(entries: Vec<PyFormIDFindingLookupEntry>) -> PyResult<Self> {
        let entries = entries
            .into_iter()
            .map(lookup_entry_to_core)
            .collect::<PyResult<Vec<_>>>()?;
        Ok(Self {
            inner: CoreAnalyzer::new(FormIdValueLookup::in_memory(entries)),
        })
    }

    /// Creates an analyzer over one owned SQLite lookup adapter using the shared runtime.
    #[staticmethod]
    pub fn sqlite(py: Python<'_>, database_path: String, game_table: String) -> PyResult<Self> {
        without_gil_block_on(py, || async move {
            FormIdValueLookup::sqlite(PathBuf::from(database_path), game_table)
                .await
                .map(|lookup| Self {
                    inner: CoreAnalyzer::new(lookup),
                })
                .map_err(|error| {
                    analyzer_error_parts_to_pyerr(
                        PyAnalyzerKind::FormIdFinding,
                        CoreAnalyzerErrorCode::OperationalFailure.as_str(),
                        error.message(),
                    )
                })
        })
    }

    /// Returns the stable focused-analyzer identity for this handle.
    #[getter]
    pub fn kind(&self) -> PyAnalyzerKind {
        PyAnalyzerKind::FormIdFinding
    }

    /// Runs aggregate semantic analysis while releasing the GIL around shared-runtime work.
    pub fn analyze(
        &self,
        py: Python<'_>,
        input: PyFormIDFindingAnalysisInput,
    ) -> PyResult<PyFormIDFindingAnalysisResult> {
        without_gil_block_on(py, || self.inner.analyze(input.inner))
            .map(Into::into)
            .map_err(analyzer_error_to_pyerr)
    }
}

/// Converts one Python-owned deterministic reply into the core lookup facade input.
fn lookup_entry_to_core(entry: PyFormIDFindingLookupEntry) -> PyResult<FormIdValueLookupEntry> {
    let reply = match entry.reply_kind {
        PyFormIDFindingLookupReplyKind::Missing => FormIdValueLookupInMemoryReply::Value(None),
        PyFormIDFindingLookupReplyKind::Found => {
            FormIdValueLookupInMemoryReply::Value(Some(entry.value.ok_or_else(|| {
                PyValueError::new_err("found FormID lookup reply requires value")
            })?))
        }
        PyFormIDFindingLookupReplyKind::OperationalFailure => {
            FormIdValueLookupInMemoryReply::OperationalFailure(entry.error_message.ok_or_else(
                || PyValueError::new_err("operational FormID lookup reply requires error_message"),
            )?)
        }
    };
    Ok(FormIdValueLookupEntry::new(
        entry.formid,
        entry.plugin,
        reply,
    ))
}

/// Registers the FormID Finding semantic analyzer family in one Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyFormIDFindingLookupReplyKind>()?;
    m.add_class::<PyFormIDFindingLookupEntry>()?;
    m.add_class::<PyFormIDPlugin>()?;
    m.add_class::<PyFormIDFindingAnalysisInput>()?;
    m.add_class::<PyFormIDValueLookupStatus>()?;
    m.add_class::<PyFormIDFinding>()?;
    m.add_class::<PyFormIDFindingAnalysisResult>()?;
    m.add_class::<PyFormIDFindingAnalyzer>()?;
    Ok(())
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "formid_finding_analyzer_tests.rs"] mod tests;
