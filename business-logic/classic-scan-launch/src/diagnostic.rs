//! Launch diagnostics: non-fatal facts a frontend should show beside the scan it starts.

use classic_user_settings_core::Diagnostic;
use classic_vocabulary::Vocabulary;

/// One non-fatal fact reported by a Crash Log Scan Launch.
///
/// A launch with diagnostics still produced a scannable request; diagnostics never stop a
/// scan. New kinds are added as launch rules gain reportable outcomes. The enum is
/// deliberately exhaustive: a new kind fails to compile in every binding that projects it,
/// which is how CXX, Node and Python stay in parity with it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CrashLogScanLaunchDiagnostic {
    /// A diagnostic User Settings reported when the launch opened them read-only.
    ///
    /// Degraded documents (malformed, newer, needing migration) surface here: the launch
    /// still builds its request, from the values User Settings projected for that document.
    UserSettings(Diagnostic),
}

impl CrashLogScanLaunchDiagnostic {
    /// Returns which launch rule produced this diagnostic.
    #[must_use]
    pub const fn kind(&self) -> CrashLogScanLaunchDiagnosticKind {
        match self {
            Self::UserSettings(_) => CrashLogScanLaunchDiagnosticKind::UserSettings,
        }
    }

    /// Returns the stable machine-readable code for programmatic handling.
    ///
    /// For [`Self::UserSettings`] this is the User Settings diagnostic code unchanged.
    #[must_use]
    pub fn code(&self) -> &str {
        match self {
            Self::UserSettings(diagnostic) => diagnostic.code(),
        }
    }

    /// Returns human-readable context. Prose, freely rewordable; branch on
    /// [`Self::kind`] and [`Self::code`] instead.
    #[must_use]
    pub fn message(&self) -> &str {
        match self {
            Self::UserSettings(diagnostic) => diagnostic.message(),
        }
    }
}

/// Which launch rule produced a [`CrashLogScanLaunchDiagnostic`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CrashLogScanLaunchDiagnosticKind {
    /// Reported by User Settings while the launch opened them.
    UserSettings,
}

impl Vocabulary for CrashLogScanLaunchDiagnosticKind {
    const VARIANTS: &'static [Self] = &[Self::UserSettings];

    /// These tokens are frozen; every binding publishes them unchanged.
    fn as_str(self) -> &'static str {
        match self {
            Self::UserSettings => "user_settings",
        }
    }

    /// Prose, freely rewordable.
    fn label(self) -> &'static str {
        match self {
            Self::UserSettings => "User Settings",
        }
    }
}
