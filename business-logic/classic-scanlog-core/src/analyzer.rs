//! Shared contracts for focused semantic analyzers.

use thiserror::Error;

/// Identifies the focused analyzer that produced a result or error.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AnalyzerKind {
    /// Crashgen Expectations and Disabled Setting Notices.
    CrashgenSettings,
    /// Known crash messages, stack patterns, and DLL involvement.
    CrashSuspect,
    /// Conflict, frequent-crash, solution, and important-mod guidance.
    ModGuidance,
    /// Plugin identity and occurrence evidence.
    PluginEvidence,
    /// Resolved and unresolved FormID evidence.
    FormIdFinding,
    /// Authored named-record evidence.
    NamedRecordFinding,
}

impl AnalyzerKind {
    /// Returns the stable cross-language identifier for this analyzer.
    pub const fn as_str(self) -> &'static str {
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

/// Stable error categories shared by focused analyzers and their bindings.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AnalyzerErrorCode {
    /// Analyzer configuration is incomplete, inconsistent, or otherwise invalid.
    InvalidConfiguration,
    /// The supplied configuration version is not supported by this build.
    UnsupportedConfigurationVersion,
    /// An analyzer dependency returned malformed semantic data.
    MalformedResult,
    /// An analyzer dependency could not complete its operation.
    OperationalFailure,
}

impl AnalyzerErrorCode {
    /// Returns the stable cross-language code for this error category.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::InvalidConfiguration => "invalid_configuration",
            Self::UnsupportedConfigurationVersion => "unsupported_configuration_version",
            Self::MalformedResult => "malformed_result",
            Self::OperationalFailure => "operational_failure",
        }
    }
}

/// Failure produced while constructing or running a focused analyzer.
#[derive(Clone, Debug, Error, PartialEq, Eq)]
#[error("{message}")]
pub struct AnalyzerError {
    analyzer: AnalyzerKind,
    code: AnalyzerErrorCode,
    message: String,
}

impl AnalyzerError {
    /// Creates a shared analyzer error from a stable kind, code, and readable message.
    pub(crate) fn new(
        analyzer: AnalyzerKind,
        code: AnalyzerErrorCode,
        message: impl Into<String>,
    ) -> Self {
        Self {
            analyzer,
            code,
            message: message.into(),
        }
    }

    /// Returns the focused analyzer that produced this error.
    pub const fn analyzer(&self) -> AnalyzerKind {
        self.analyzer
    }

    /// Returns the stable machine-readable error code.
    pub const fn code(&self) -> AnalyzerErrorCode {
        self.code
    }

    /// Returns the human-readable diagnostic message.
    pub fn message(&self) -> &str {
        &self.message
    }

    /// Formats the stable analyzer identity, code, and diagnostic for internal error envelopes.
    pub(crate) fn formatted_message(&self) -> String {
        format!(
            "{} [{}]: {}",
            self.analyzer.as_str(),
            self.code.as_str(),
            self.message
        )
    }
}

/// Result type used by all focused semantic analyzers.
pub type AnalyzerResult<T> = std::result::Result<T, AnalyzerError>;

#[cfg(test)]
#[path = "analyzer_tests.rs"]
mod tests;
