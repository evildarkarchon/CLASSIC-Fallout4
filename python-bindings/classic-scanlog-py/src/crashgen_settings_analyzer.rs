//! Python projection of semantic Crashgen Settings Analysis.

use std::collections::HashSet;

use classic_config_core::{
    AutoscanReportPlacement as CorePlacement, ConfigLayout, OutcomeKind, RuleSeverity,
};
use classic_scanlog_core::{
    AnalyzerError as CoreAnalyzerError, AnalyzerKind as CoreAnalyzerKind,
    CrashgenExpectationOutcome as CoreOutcome, CrashgenSettingsAnalysisInput as CoreAnalysisInput,
    CrashgenSettingsAnalysisResult as CoreAnalysisResult, CrashgenSettingsAnalyzer as CoreAnalyzer,
    DisabledSettingNotice as CoreNotice,
};
use classic_shared::without_gil;
use pyo3::create_exception;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};

use crate::py_adapters::crashgen_entry_from_py_strict;
use crate::settings_validator::crashgen_snapshot_from_py_sections;

create_exception!(
    classic_scanlog,
    AnalyzerError,
    PyRuntimeError,
    "A focused semantic analyzer could not be constructed or executed."
);

/// Stable focused-analyzer identifiers exposed to Python.
#[pyclass(name = "AnalyzerKind", eq, eq_int, frozen, from_py_object)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyAnalyzerKind {
    /// Crashgen Expectations and Disabled Setting Notices.
    CrashgenSettings = 0,
    /// Known crash messages, stack patterns, and DLL involvement.
    CrashSuspect = 1,
    /// Conflict, crash, solution, and important-mod guidance.
    ModGuidance = 2,
    /// Plugin identity and occurrence evidence.
    PluginEvidence = 3,
    /// Resolved and unresolved FormID evidence.
    FormIdFinding = 4,
    /// Authored named-record evidence.
    NamedRecordFinding = 5,
}

impl From<CoreAnalyzerKind> for PyAnalyzerKind {
    fn from(value: CoreAnalyzerKind) -> Self {
        match value {
            CoreAnalyzerKind::CrashgenSettings => Self::CrashgenSettings,
            CoreAnalyzerKind::CrashSuspect => Self::CrashSuspect,
            CoreAnalyzerKind::ModGuidance => Self::ModGuidance,
            CoreAnalyzerKind::PluginEvidence => Self::PluginEvidence,
            CoreAnalyzerKind::FormIdFinding => Self::FormIdFinding,
            CoreAnalyzerKind::NamedRecordFinding => Self::NamedRecordFinding,
        }
    }
}

#[pymethods]
impl PyAnalyzerKind {
    /// Stable cross-language analyzer token.
    #[getter]
    pub fn code(&self) -> &'static str {
        match self {
            Self::CrashgenSettings => "crashgen_settings",
            Self::CrashSuspect => "crash_suspect",
            Self::ModGuidance => "mod_guidance",
            Self::PluginEvidence => "plugin_evidence",
            Self::FormIdFinding => "formid_finding",
            Self::NamedRecordFinding => "named_record_finding",
        }
    }
}

/// Semantic kind of one Crashgen Expectation outcome.
#[pyclass(
    name = "CrashgenExpectationKind",
    eq,
    eq_int,
    frozen,
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyCrashgenExpectationKind {
    /// Informational notice selected by a preflight rule.
    Notice = 0,
    /// Failed expectation or preflight issue.
    Issue = 1,
    /// Successful expectation with an authored pass message.
    Success = 2,
}

impl From<OutcomeKind> for PyCrashgenExpectationKind {
    fn from(value: OutcomeKind) -> Self {
        match value {
            OutcomeKind::Notice => Self::Notice,
            OutcomeKind::Issue => Self::Issue,
            OutcomeKind::Success => Self::Success,
        }
    }
}

#[pymethods]
impl PyCrashgenExpectationKind {
    /// Stable semantic outcome token.
    #[getter]
    pub fn value(&self) -> &'static str {
        match self {
            Self::Notice => "notice",
            Self::Issue => "issue",
            Self::Success => "success",
        }
    }
}

/// Severity attached to a Crashgen Expectation outcome.
#[pyclass(name = "AnalyzerSeverity", eq, eq_int, frozen, skip_from_py_object)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyAnalyzerSeverity {
    /// Informational severity.
    Info = 0,
    /// Warning severity.
    Warning = 1,
    /// Error severity.
    Error = 2,
}

impl From<RuleSeverity> for PyAnalyzerSeverity {
    fn from(value: RuleSeverity) -> Self {
        match value {
            RuleSeverity::Info => Self::Info,
            RuleSeverity::Warning => Self::Warning,
            RuleSeverity::Error => Self::Error,
        }
    }
}

#[pymethods]
impl PyAnalyzerSeverity {
    /// Stable severity token.
    #[getter]
    pub fn value(&self) -> &'static str {
        match self {
            Self::Info => "info",
            Self::Warning => "warning",
            Self::Error => "error",
        }
    }
}

/// YAML-owned Autoscan Report Placement for an expectation outcome.
#[pyclass(
    name = "AutoscanReportPlacement",
    eq,
    eq_int,
    frozen,
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyAutoscanReportPlacement {
    /// Settings-related guidance section.
    Settings = 0,
    /// Error Information section.
    ErrorInformation = 1,
}

impl From<CorePlacement> for PyAutoscanReportPlacement {
    fn from(value: CorePlacement) -> Self {
        match value {
            CorePlacement::Settings => Self::Settings,
            CorePlacement::ErrorInformation => Self::ErrorInformation,
        }
    }
}

#[pymethods]
impl PyAutoscanReportPlacement {
    /// Canonical YAML and cross-language placement token.
    #[getter]
    pub fn value(&self) -> &'static str {
        match self {
            Self::Settings => "settings",
            Self::ErrorInformation => "error_information",
        }
    }
}

/// Immutable Python view of one semantic Crashgen Expectation outcome.
#[pyclass(name = "CrashgenExpectationOutcome", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyCrashgenExpectationOutcome {
    /// Stable YAML-authored rule identifier.
    #[pyo3(get)]
    rule_id: String,
    /// Semantic outcome kind.
    #[pyo3(get)]
    kind: PyCrashgenExpectationKind,
    /// Authored severity.
    #[pyo3(get)]
    severity: PyAnalyzerSeverity,
    /// Authored and expanded message without report markup.
    #[pyo3(get)]
    message: String,
    /// Optional authored and expanded fix without report markup.
    #[pyo3(get)]
    fix: Option<String>,
    /// YAML-owned Autoscan Report Placement.
    #[pyo3(get)]
    placement: PyAutoscanReportPlacement,
    /// Target section for setting checks.
    #[pyo3(get)]
    section: Option<String>,
    /// Target key for setting checks.
    #[pyo3(get)]
    setting: Option<String>,
    /// Expected setting value for setting checks.
    #[pyo3(get)]
    expected: Option<String>,
    /// Actual setting value for setting checks.
    #[pyo3(get)]
    actual: Option<String>,
}

impl From<CoreOutcome> for PyCrashgenExpectationOutcome {
    fn from(value: CoreOutcome) -> Self {
        Self {
            rule_id: value.rule_id,
            kind: value.kind.into(),
            severity: value.severity.into(),
            message: value.message,
            fix: value.fix,
            placement: value.placement.into(),
            section: value.section,
            setting: value.setting,
            expected: value.expected,
            actual: value.actual,
        }
    }
}

/// Immutable Python view of one universal Disabled Setting Notice.
#[pyclass(name = "DisabledSettingNotice", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyDisabledSettingNotice {
    /// Disabled setting key retained by the crashgen snapshot.
    #[pyo3(get)]
    setting_name: String,
}

impl From<CoreNotice> for PyDisabledSettingNotice {
    fn from(value: CoreNotice) -> Self {
        Self {
            setting_name: value.setting_name,
        }
    }
}

/// Immutable completed Crashgen Settings Analysis result.
#[pyclass(name = "CrashgenSettingsAnalysisResult", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyCrashgenSettingsAnalysisResult {
    /// Typed expectation outcomes in evaluator order.
    #[pyo3(get)]
    expectation_outcomes: Vec<PyCrashgenExpectationOutcome>,
    /// Universal disabled-setting notices kept separate from expectations.
    #[pyo3(get)]
    disabled_setting_notices: Vec<PyDisabledSettingNotice>,
}

/// Immutable owned input for one aggregate Crashgen Settings Analysis call.
#[pyclass(name = "CrashgenSettingsAnalysisInput", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyCrashgenSettingsAnalysisInput {
    inner: CoreAnalysisInput,
}

#[pymethods]
impl PyCrashgenSettingsAnalysisInput {
    /// Converts Python-owned settings, plugin, version, and layout facts once.
    #[new]
    #[pyo3(signature = (settings, installed_plugins, crashgen_version = None, config_layout = None))]
    pub fn new(
        settings: &Bound<'_, PyDict>,
        installed_plugins: HashSet<String>,
        crashgen_version: Option<(u32, u32, u32)>,
        config_layout: Option<String>,
    ) -> PyResult<Self> {
        let settings = crashgen_snapshot_from_py_sections(settings)?;
        let config_layout = config_layout
            .as_deref()
            .and_then(ConfigLayout::parse)
            .unwrap_or(ConfigLayout::Unknown);
        Ok(Self {
            inner: CoreAnalysisInput {
                settings,
                installed_plugins,
                crashgen_version,
                config_layout,
            },
        })
    }
}

impl From<CoreAnalysisResult> for PyCrashgenSettingsAnalysisResult {
    fn from(value: CoreAnalysisResult) -> Self {
        Self {
            expectation_outcomes: value
                .expectation_outcomes
                .into_iter()
                .map(Into::into)
                .collect(),
            disabled_setting_notices: value
                .disabled_setting_notices
                .into_iter()
                .map(Into::into)
                .collect(),
        }
    }
}

/// Immutable Python handle for repeated, concurrent Crashgen Settings Analysis.
#[pyclass(name = "CrashgenSettingsAnalyzer", frozen)]
#[derive(Debug)]
pub struct PyCrashgenSettingsAnalyzer {
    inner: CoreAnalyzer,
}

#[pymethods]
impl PyCrashgenSettingsAnalyzer {
    /// Validates analyzer configuration and compiles matcher state immediately.
    #[new]
    pub fn new(crashgen_name: String, crashgen_entry: &Bound<'_, PyAny>) -> PyResult<Self> {
        let (entry, diagnostics) = crashgen_entry_from_py_strict(crashgen_entry)?;
        let inner = CoreAnalyzer::from_parsed_configuration(crashgen_name, entry, diagnostics)
            .map_err(analyzer_error_to_pyerr)?;
        Ok(Self { inner })
    }

    /// Returns the stable kind of this analyzer handle.
    #[getter]
    pub fn kind(&self) -> PyAnalyzerKind {
        PyAnalyzerKind::CrashgenSettings
    }

    /// Runs aggregate semantic analysis over one immutable owned-input value.
    pub fn analyze(
        &self,
        py: Python<'_>,
        input: PyCrashgenSettingsAnalysisInput,
    ) -> PyResult<PyCrashgenSettingsAnalysisResult> {
        without_gil(py, || self.inner.analyze(input.inner))
            .map(Into::into)
            .map_err(analyzer_error_to_pyerr)
    }
}

/// Registers the semantic analyzer contract and its typed error in one module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("AnalyzerError", m.py().get_type::<AnalyzerError>())?;
    m.add_class::<PyAnalyzerKind>()?;
    m.add_class::<PyCrashgenExpectationKind>()?;
    m.add_class::<PyAnalyzerSeverity>()?;
    m.add_class::<PyAutoscanReportPlacement>()?;
    m.add_class::<PyCrashgenExpectationOutcome>()?;
    m.add_class::<PyDisabledSettingNotice>()?;
    m.add_class::<PyCrashgenSettingsAnalysisInput>()?;
    m.add_class::<PyCrashgenSettingsAnalysisResult>()?;
    m.add_class::<PyCrashgenSettingsAnalyzer>()?;
    Ok(())
}

pub(crate) fn analyzer_error_to_pyerr(error: CoreAnalyzerError) -> PyErr {
    let py_error = AnalyzerError::new_err(error.message().to_string());
    Python::attach(|py| {
        let value = py_error.value(py);
        // Exception attributes preserve the shared typed contract for Python callers.
        let _ = value.setattr("analyzer_kind", PyAnalyzerKind::from(error.analyzer()));
        let _ = value.setattr("code", error.code().as_str());
        let _ = value.setattr("message", error.message());
    });
    py_error
}

#[cfg(test)]
#[path = "crashgen_settings_analyzer_tests.rs"]
mod tests;
