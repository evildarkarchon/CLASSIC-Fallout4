//! Python projection of semantic Crash Suspect analysis.

use classic_config_core::{SuspectErrorRule, SuspectStackCountRule, SuspectStackRule};
use classic_scanlog_core::{
    CrashSuspectAnalysisInput as CoreAnalysisInput,
    CrashSuspectAnalysisResult as CoreAnalysisResult, CrashSuspectAnalyzer as CoreAnalyzer,
    CrashSuspectFinding as CoreFinding, CrashSuspectFindingKind as CoreFindingKind,
};
use classic_shared::without_gil;
use pyo3::prelude::*;

use crate::crashgen_settings_analyzer::{PyAnalyzerKind, analyzer_error_to_pyerr};

/// Evidence source that produced one Crash Suspect Finding.
#[pyclass(
    name = "CrashSuspectFindingKind",
    eq,
    eq_int,
    frozen,
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyCrashSuspectFindingKind {
    /// A configured main-error rule matched.
    MainErrorRule = 0,
    /// A configured stack rule matched.
    StackRule = 1,
    /// The main error reports DLL involvement.
    DllInvolvement = 2,
}

impl From<CoreFindingKind> for PyCrashSuspectFindingKind {
    fn from(value: CoreFindingKind) -> Self {
        match value {
            CoreFindingKind::MainErrorRule => Self::MainErrorRule,
            CoreFindingKind::StackRule => Self::StackRule,
            CoreFindingKind::DllInvolvement => Self::DllInvolvement,
        }
    }
}

#[pymethods]
impl PyCrashSuspectFindingKind {
    /// Stable cross-language finding-kind token.
    #[getter]
    pub fn value(&self) -> &'static str {
        match self {
            Self::MainErrorRule => "main_error_rule",
            Self::StackRule => "stack_rule",
            Self::DllInvolvement => "dll_involvement",
        }
    }
}

/// Immutable minimum-occurrence condition for a stack rule.
#[pyclass(name = "CrashSuspectStackCountRule", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyCrashSuspectStackCountRule {
    #[pyo3(get)]
    substring: String,
    #[pyo3(get)]
    count: usize,
}

#[pymethods]
impl PyCrashSuspectStackCountRule {
    /// Creates one owned minimum-occurrence matcher.
    #[new]
    pub fn new(substring: String, count: usize) -> Self {
        Self { substring, count }
    }
}

/// Immutable owned main-error rule for analyzer construction.
#[pyclass(name = "CrashSuspectMainErrorRule", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyCrashSuspectMainErrorRule {
    #[pyo3(get)]
    id: String,
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    severity: i32,
    #[pyo3(get)]
    main_error_contains_any: Vec<String>,
}

#[pymethods]
impl PyCrashSuspectMainErrorRule {
    /// Creates one owned main-error rule.
    #[new]
    pub fn new(
        id: String,
        name: String,
        severity: i32,
        main_error_contains_any: Vec<String>,
    ) -> Self {
        Self {
            id,
            name,
            severity,
            main_error_contains_any,
        }
    }
}

impl From<PyCrashSuspectMainErrorRule> for SuspectErrorRule {
    fn from(value: PyCrashSuspectMainErrorRule) -> Self {
        Self {
            id: value.id,
            name: value.name,
            severity: value.severity,
            main_error_contains_any: value.main_error_contains_any,
        }
    }
}

/// Immutable owned stack rule for analyzer construction.
#[pyclass(name = "CrashSuspectStackRule", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyCrashSuspectStackRule {
    #[pyo3(get)]
    id: String,
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    severity: i32,
    #[pyo3(get)]
    main_error_required_any: Vec<String>,
    #[pyo3(get)]
    main_error_optional_any: Vec<String>,
    #[pyo3(get)]
    stack_contains_any: Vec<String>,
    #[pyo3(get)]
    exclude_if_stack_contains_any: Vec<String>,
    #[pyo3(get)]
    stack_contains_at_least: Vec<PyCrashSuspectStackCountRule>,
}

#[pymethods]
impl PyCrashSuspectStackRule {
    /// Creates one owned stack rule.
    #[new]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        id: String,
        name: String,
        severity: i32,
        main_error_required_any: Vec<String>,
        main_error_optional_any: Vec<String>,
        stack_contains_any: Vec<String>,
        exclude_if_stack_contains_any: Vec<String>,
        stack_contains_at_least: Vec<PyCrashSuspectStackCountRule>,
    ) -> Self {
        Self {
            id,
            name,
            severity,
            main_error_required_any,
            main_error_optional_any,
            stack_contains_any,
            exclude_if_stack_contains_any,
            stack_contains_at_least,
        }
    }
}

impl From<PyCrashSuspectStackRule> for SuspectStackRule {
    fn from(value: PyCrashSuspectStackRule) -> Self {
        Self {
            id: value.id,
            name: value.name,
            severity: value.severity,
            main_error_required_any: value.main_error_required_any,
            main_error_optional_any: value.main_error_optional_any,
            stack_contains_any: value.stack_contains_any,
            exclude_if_stack_contains_any: value.exclude_if_stack_contains_any,
            stack_contains_at_least: value
                .stack_contains_at_least
                .into_iter()
                .map(|count_rule| SuspectStackCountRule {
                    substring: count_rule.substring,
                    count: count_rule.count,
                })
                .collect(),
        }
    }
}

/// Immutable owned input for one aggregate Crash Suspect analysis call.
#[pyclass(name = "CrashSuspectAnalysisInput", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyCrashSuspectAnalysisInput {
    inner: CoreAnalysisInput,
}

#[pymethods]
impl PyCrashSuspectAnalysisInput {
    /// Creates owned Crash Log evidence for one analysis call.
    #[new]
    pub fn new(main_error: String, call_stack: String) -> Self {
        Self {
            inner: CoreAnalysisInput {
                main_error,
                call_stack,
            },
        }
    }
}

/// Immutable Python view of one semantic Crash Suspect Finding.
#[pyclass(name = "CrashSuspectFinding", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyCrashSuspectFinding {
    #[pyo3(get)]
    kind: PyCrashSuspectFindingKind,
    #[pyo3(get)]
    rule_id: Option<String>,
    #[pyo3(get)]
    name: Option<String>,
    #[pyo3(get)]
    severity: Option<i32>,
}

impl From<CoreFinding> for PyCrashSuspectFinding {
    fn from(value: CoreFinding) -> Self {
        let kind = value.kind().into();
        match value {
            CoreFinding::MainErrorRule {
                rule_id,
                name,
                severity,
            } => Self {
                kind,
                rule_id: Some(rule_id),
                name: Some(name),
                severity: Some(severity),
            },
            CoreFinding::StackRule {
                rule_id,
                name,
                severity,
            } => Self {
                kind,
                rule_id: Some(rule_id),
                name: Some(name),
                severity: Some(severity),
            },
            CoreFinding::DllInvolvement => Self {
                kind,
                rule_id: None,
                name: None,
                severity: None,
            },
        }
    }
}

/// Immutable completed Crash Suspect analysis result.
#[pyclass(name = "CrashSuspectAnalysisResult", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyCrashSuspectAnalysisResult {
    #[pyo3(get)]
    findings: Vec<PyCrashSuspectFinding>,
}

impl From<CoreAnalysisResult> for PyCrashSuspectAnalysisResult {
    fn from(value: CoreAnalysisResult) -> Self {
        Self {
            findings: value.findings.into_iter().map(Into::into).collect(),
        }
    }
}

/// Immutable Python handle for repeated concurrent Crash Suspect analysis.
#[pyclass(name = "CrashSuspectAnalyzer", frozen)]
#[derive(Debug)]
pub struct PyCrashSuspectAnalyzer {
    inner: CoreAnalyzer,
}

#[pymethods]
impl PyCrashSuspectAnalyzer {
    /// Validates and compiles owned Crash Suspect rules immediately.
    #[new]
    pub fn new(
        main_error_rules: Vec<PyCrashSuspectMainErrorRule>,
        stack_rules: Vec<PyCrashSuspectStackRule>,
    ) -> PyResult<Self> {
        let inner = CoreAnalyzer::new(
            main_error_rules.into_iter().map(Into::into).collect(),
            stack_rules.into_iter().map(Into::into).collect(),
        )
        .map_err(analyzer_error_to_pyerr)?;
        Ok(Self { inner })
    }

    /// Returns the stable kind of this analyzer handle.
    #[getter]
    pub fn kind(&self) -> PyAnalyzerKind {
        PyAnalyzerKind::CrashSuspect
    }

    /// Runs aggregate semantic analysis while releasing the GIL.
    pub fn analyze(
        &self,
        py: Python<'_>,
        input: PyCrashSuspectAnalysisInput,
    ) -> PyResult<PyCrashSuspectAnalysisResult> {
        without_gil(py, || self.inner.analyze(input.inner))
            .map(Into::into)
            .map_err(analyzer_error_to_pyerr)
    }
}

/// Registers the Crash Suspect semantic analyzer family in one Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCrashSuspectFindingKind>()?;
    m.add_class::<PyCrashSuspectStackCountRule>()?;
    m.add_class::<PyCrashSuspectMainErrorRule>()?;
    m.add_class::<PyCrashSuspectStackRule>()?;
    m.add_class::<PyCrashSuspectAnalysisInput>()?;
    m.add_class::<PyCrashSuspectFinding>()?;
    m.add_class::<PyCrashSuspectAnalysisResult>()?;
    m.add_class::<PyCrashSuspectAnalyzer>()?;
    Ok(())
}

#[cfg(test)]
#[path = "crash_suspect_analyzer_tests.rs"]
mod tests;
