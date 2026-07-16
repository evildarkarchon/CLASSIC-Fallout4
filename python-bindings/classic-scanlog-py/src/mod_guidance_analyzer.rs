//! Python projection of semantic Mod Guidance analysis.

use std::collections::HashSet;

use classic_config_core::{
    CoreModEntry, CoreModExclude, ModConflictEntry, ModSolutionCriteria, ModSolutionEntry,
};
use classic_scanlog_core::mod_guidance_analyzer::{
    ImportantModGuidance as CoreImportantModGuidance, ModConflictGuidance as CoreConflictGuidance,
    ModGuidanceAnalysisInput as CoreAnalysisInput, ModGuidanceAnalysisResult as CoreAnalysisResult,
    ModGuidanceAnalyzer as CoreAnalyzer, ModGuidanceMatchState as CoreMatchState,
    ModSolutionGuidance as CoreSolutionGuidance,
};
use classic_shared::{pydict_to_indexmap_str, without_gil};
use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::crashgen_settings_analyzer::{PyAnalyzerKind, analyzer_error_to_pyerr};

/// Grouped match strategy for one frequent-crash or solution rule.
#[pyclass(name = "ModGuidanceCriteriaKind", eq, eq_int, frozen, from_py_object)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyModGuidanceCriteriaKind {
    /// Match when any configured criterion is present.
    Any = 0,
    /// Match only when every configured criterion is present.
    All = 1,
}

#[pymethods]
impl PyModGuidanceCriteriaKind {
    /// Returns the stable cross-language criteria-kind token.
    #[getter]
    pub fn value(&self) -> &'static str {
        match self {
            Self::Any => "any",
            Self::All => "all",
        }
    }
}

/// Semantic match state shared by every Mod Guidance result family.
#[pyclass(
    name = "ModGuidanceMatchState",
    eq,
    eq_int,
    frozen,
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PyModGuidanceMatchState {
    /// Configured guidance matched installed evidence.
    Matched = 0,
    /// An applicable important mod was not found.
    Missing = 1,
    /// An installed GPU-specific mod does not match the detected GPU.
    GpuMismatch = 2,
}

impl From<CoreMatchState> for PyModGuidanceMatchState {
    fn from(value: CoreMatchState) -> Self {
        match value {
            CoreMatchState::Matched => Self::Matched,
            CoreMatchState::Missing => Self::Missing,
            CoreMatchState::GpuMismatch => Self::GpuMismatch,
        }
    }
}

#[pymethods]
impl PyModGuidanceMatchState {
    /// Returns the stable cross-language match-state token.
    #[getter]
    pub fn value(&self) -> &'static str {
        match self {
            Self::Matched => "matched",
            Self::Missing => "missing",
            Self::GpuMismatch => "gpu_mismatch",
        }
    }
}

/// Immutable owned conflict rule for analyzer construction.
#[pyclass(name = "ModGuidanceConflictRule", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyModGuidanceConflictRule {
    #[pyo3(get)]
    mod_a: String,
    #[pyo3(get)]
    mod_b: String,
    #[pyo3(get)]
    name_a: String,
    #[pyo3(get)]
    name_b: String,
    #[pyo3(get)]
    description: String,
    #[pyo3(get)]
    fix: String,
    #[pyo3(get)]
    link: Option<String>,
}

#[pymethods]
impl PyModGuidanceConflictRule {
    /// Creates one owned YAML-authored conflict rule.
    #[new]
    #[pyo3(signature = (mod_a, mod_b, name_a, name_b, description, fix, link = None))]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        mod_a: String,
        mod_b: String,
        name_a: String,
        name_b: String,
        description: String,
        fix: String,
        link: Option<String>,
    ) -> Self {
        Self {
            mod_a,
            mod_b,
            name_a,
            name_b,
            description,
            fix,
            link,
        }
    }
}

impl From<PyModGuidanceConflictRule> for ModConflictEntry {
    fn from(value: PyModGuidanceConflictRule) -> Self {
        Self {
            mod_a: value.mod_a,
            mod_b: value.mod_b,
            name_a: value.name_a,
            name_b: value.name_b,
            description: value.description,
            fix: value.fix,
            link: value.link,
        }
    }
}

/// Immutable owned frequent-crash or solution rule for analyzer construction.
#[pyclass(name = "ModGuidanceSolutionRule", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyModGuidanceSolutionRule {
    #[pyo3(get)]
    id: String,
    #[pyo3(get)]
    criteria_kind: PyModGuidanceCriteriaKind,
    #[pyo3(get)]
    criteria: Vec<String>,
    #[pyo3(get)]
    exceptions: Vec<String>,
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    description: String,
}

#[pymethods]
impl PyModGuidanceSolutionRule {
    /// Creates one owned rule with typed any/all grouped criteria.
    #[new]
    pub fn new(
        id: String,
        criteria_kind: PyModGuidanceCriteriaKind,
        criteria: Vec<String>,
        exceptions: Vec<String>,
        name: String,
        description: String,
    ) -> Self {
        Self {
            id,
            criteria_kind,
            criteria,
            exceptions,
            name,
            description,
        }
    }
}

impl PyModGuidanceSolutionRule {
    /// Converts one typed Python rule into core-owned configuration.
    fn into_core(self) -> ModSolutionEntry {
        let criteria = match self.criteria_kind {
            PyModGuidanceCriteriaKind::Any => ModSolutionCriteria::Any(self.criteria),
            PyModGuidanceCriteriaKind::All => ModSolutionCriteria::All(self.criteria),
        };
        ModSolutionEntry {
            id: self.id,
            criteria,
            exceptions: self.exceptions,
            name: self.name,
            description: self.description,
        }
    }
}

/// Immutable owned important-mod rule for analyzer construction.
#[pyclass(name = "ModGuidanceImportantModRule", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyModGuidanceImportantModRule {
    #[pyo3(get)]
    detect: String,
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    description: String,
    #[pyo3(get)]
    gpu: Option<String>,
    #[pyo3(get)]
    gpu_mismatch_warning: Option<String>,
    #[pyo3(get)]
    exclude_when_plugin_any: Option<Vec<String>>,
}

#[pymethods]
impl PyModGuidanceImportantModRule {
    /// Creates one owned important-mod rule and optional plugin exclusion.
    #[new]
    #[pyo3(signature = (
        detect,
        name,
        description,
        gpu = None,
        gpu_mismatch_warning = None,
        exclude_when_plugin_any = None
    ))]
    pub fn new(
        detect: String,
        name: String,
        description: String,
        gpu: Option<String>,
        gpu_mismatch_warning: Option<String>,
        exclude_when_plugin_any: Option<Vec<String>>,
    ) -> Self {
        Self {
            detect,
            name,
            description,
            gpu,
            gpu_mismatch_warning,
            exclude_when_plugin_any,
        }
    }
}

impl From<PyModGuidanceImportantModRule> for CoreModEntry {
    fn from(value: PyModGuidanceImportantModRule) -> Self {
        Self {
            detect: value.detect,
            name: value.name,
            description: value.description,
            gpu: value.gpu,
            gpu_mismatch_warning: value.gpu_mismatch_warning,
            exclude_when: value.exclude_when_plugin_any.map(CoreModExclude::PluginAny),
        }
    }
}

/// Immutable owned facts for one aggregate Mod Guidance analysis call.
#[pyclass(name = "ModGuidanceAnalysisInput", frozen, from_py_object)]
#[derive(Clone)]
pub struct PyModGuidanceAnalysisInput {
    inner: CoreAnalysisInput,
}

#[pymethods]
impl PyModGuidanceAnalysisInput {
    /// Converts ordered plugin, GPU, and XSE-module facts into owned Rust data.
    #[new]
    #[pyo3(signature = (plugins, user_gpu = None, xse_modules = HashSet::new()))]
    pub fn new(
        plugins: &Bound<'_, PyDict>,
        user_gpu: Option<String>,
        xse_modules: HashSet<String>,
    ) -> PyResult<Self> {
        let ordered_plugins = pydict_to_indexmap_str(plugins)?;
        Ok(Self {
            inner: CoreAnalysisInput {
                plugins: ordered_plugins,
                user_gpu,
                xse_modules,
            },
        })
    }
}

/// Immutable Python view of one matched mod conflict.
#[pyclass(name = "ModConflictGuidance", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyModConflictGuidance {
    #[pyo3(get)]
    state: PyModGuidanceMatchState,
    #[pyo3(get)]
    mod_a: String,
    #[pyo3(get)]
    mod_b: String,
    #[pyo3(get)]
    name_a: String,
    #[pyo3(get)]
    name_b: String,
    #[pyo3(get)]
    description: String,
    #[pyo3(get)]
    fix: String,
    #[pyo3(get)]
    link: Option<String>,
}

impl From<CoreConflictGuidance> for PyModConflictGuidance {
    fn from(value: CoreConflictGuidance) -> Self {
        Self {
            state: value.state.into(),
            mod_a: value.mod_a,
            mod_b: value.mod_b,
            name_a: value.name_a,
            name_b: value.name_b,
            description: value.description,
            fix: value.fix,
            link: value.link,
        }
    }
}

/// Immutable Python view of one frequent-crash or solution match.
#[pyclass(name = "ModSolutionGuidance", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyModSolutionGuidance {
    #[pyo3(get)]
    state: PyModGuidanceMatchState,
    #[pyo3(get)]
    id: String,
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    description: String,
    #[pyo3(get)]
    matched_plugin_ids: Vec<String>,
}

impl From<CoreSolutionGuidance> for PyModSolutionGuidance {
    fn from(value: CoreSolutionGuidance) -> Self {
        Self {
            state: value.state.into(),
            id: value.id,
            name: value.name,
            description: value.description,
            matched_plugin_ids: value.matched_plugin_ids,
        }
    }
}

/// Immutable Python view of one applicable important-mod state.
#[pyclass(name = "ImportantModGuidance", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyImportantModGuidance {
    #[pyo3(get)]
    state: PyModGuidanceMatchState,
    #[pyo3(get)]
    detect: String,
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    description: String,
    #[pyo3(get)]
    gpu: Option<String>,
    #[pyo3(get)]
    gpu_mismatch_warning: Option<String>,
}

impl From<CoreImportantModGuidance> for PyImportantModGuidance {
    fn from(value: CoreImportantModGuidance) -> Self {
        Self {
            state: value.state.into(),
            detect: value.detect,
            name: value.name,
            description: value.description,
            gpu: value.gpu,
            gpu_mismatch_warning: value.gpu_mismatch_warning,
        }
    }
}

/// Immutable completed aggregate Mod Guidance analysis result.
#[pyclass(name = "ModGuidanceAnalysisResult", frozen, skip_from_py_object)]
#[derive(Clone)]
pub struct PyModGuidanceAnalysisResult {
    #[pyo3(get)]
    conflicts: Vec<PyModConflictGuidance>,
    #[pyo3(get)]
    frequent_crashes: Vec<PyModSolutionGuidance>,
    #[pyo3(get)]
    solutions: Vec<PyModSolutionGuidance>,
    #[pyo3(get)]
    important_mods: Vec<PyImportantModGuidance>,
}

impl From<CoreAnalysisResult> for PyModGuidanceAnalysisResult {
    fn from(value: CoreAnalysisResult) -> Self {
        Self {
            conflicts: value.conflicts.into_iter().map(Into::into).collect(),
            frequent_crashes: value.frequent_crashes.into_iter().map(Into::into).collect(),
            solutions: value.solutions.into_iter().map(Into::into).collect(),
            important_mods: value.important_mods.into_iter().map(Into::into).collect(),
        }
    }
}

/// Immutable Python handle for repeated concurrent Mod Guidance analysis.
#[pyclass(name = "ModGuidanceAnalyzer", frozen)]
#[derive(Debug)]
pub struct PyModGuidanceAnalyzer {
    inner: CoreAnalyzer,
}

#[pymethods]
impl PyModGuidanceAnalyzer {
    /// Validates and compiles all four owned Mod Guidance rule families.
    ///
    /// The four parameters retain configuration order for conflicts,
    /// frequent-crash guidance, solutions, and important mods respectively.
    /// Invalid authored fields or matcher configuration raise the shared
    /// `AnalyzerError` before an analyzer handle is returned.
    #[new]
    pub fn new(
        conflicts: Vec<PyModGuidanceConflictRule>,
        frequent_crashes: Vec<PyModGuidanceSolutionRule>,
        solutions: Vec<PyModGuidanceSolutionRule>,
        important_mods: Vec<PyModGuidanceImportantModRule>,
    ) -> PyResult<Self> {
        let frequent_crashes = frequent_crashes
            .into_iter()
            .map(PyModGuidanceSolutionRule::into_core)
            .collect();
        let solutions = solutions
            .into_iter()
            .map(PyModGuidanceSolutionRule::into_core)
            .collect();
        let inner = CoreAnalyzer::new(
            conflicts.into_iter().map(Into::into).collect(),
            frequent_crashes,
            solutions,
            important_mods.into_iter().map(Into::into).collect(),
        )
        .map_err(analyzer_error_to_pyerr)?;
        Ok(Self { inner })
    }

    /// Returns the stable kind of this analyzer handle.
    #[getter]
    pub fn kind(&self) -> PyAnalyzerKind {
        PyAnalyzerKind::ModGuidance
    }

    /// Runs one aggregate semantic analysis while releasing the GIL.
    ///
    /// The returned result always contains all four guidance collections;
    /// completed no-match analysis returns four explicit empty lists. Core
    /// analysis failures raise the shared `AnalyzerError`, and the immutable
    /// handle remains safe for reuse across Python threads.
    pub fn analyze(
        &self,
        py: Python<'_>,
        input: PyModGuidanceAnalysisInput,
    ) -> PyResult<PyModGuidanceAnalysisResult> {
        without_gil(py, || self.inner.analyze(input.inner))
            .map(Into::into)
            .map_err(analyzer_error_to_pyerr)
    }
}

/// Registers the Mod Guidance semantic analyzer family in one Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyModGuidanceCriteriaKind>()?;
    m.add_class::<PyModGuidanceMatchState>()?;
    m.add_class::<PyModGuidanceConflictRule>()?;
    m.add_class::<PyModGuidanceSolutionRule>()?;
    m.add_class::<PyModGuidanceImportantModRule>()?;
    m.add_class::<PyModGuidanceAnalysisInput>()?;
    m.add_class::<PyModConflictGuidance>()?;
    m.add_class::<PyModSolutionGuidance>()?;
    m.add_class::<PyImportantModGuidance>()?;
    m.add_class::<PyModGuidanceAnalysisResult>()?;
    m.add_class::<PyModGuidanceAnalyzer>()?;
    Ok(())
}

#[cfg(test)]
#[path = "mod_guidance_analyzer_tests.rs"]
mod tests;
