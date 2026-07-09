//! Thin NAPI adapter for the read-only User Settings open interface.

use classic_user_settings_core::{
    CommitEligibility, DocumentClassification, PreferenceOrigin, Revision, SourceLocation,
    UserSettings,
};
use napi::bindgen_prelude::Buffer;

/// One structured diagnostic produced while opening User Settings.
#[napi(object)]
pub struct JsUserSettingsDiagnostic {
    /// Stable machine-readable diagnostic code.
    pub code: String,
    /// Human-readable diagnostic context.
    pub message: String,
}

/// Update-related User Settings consumed by update-check policy.
#[napi(object)]
pub struct JsUpdatePreferences {
    /// Whether first-party update checks are enabled after safe fallback policy.
    pub update_check: bool,
    /// Provenance token: `document`, `default`, or `degradedFallback`.
    pub origin: String,
}

/// Read-only User Settings snapshot returned by `openUserSettings`.
#[napi(object)]
pub struct JsUserSettingsSnapshot {
    /// Typed update preferences.
    pub update_preferences: JsUpdatePreferences,
    /// Selected source token: `canonical`, `legacy`, or `missing`.
    pub source_location: String,
    /// Selected source path, absent when the document is missing.
    pub source_path: Option<String>,
    /// Document format/schema classification token.
    pub classification: String,
    /// Parsed schema major, absent for missing or unversioned documents.
    pub schema_major: Option<u32>,
    /// Parsed schema minor, absent for missing or unversioned documents.
    pub schema_minor: Option<u32>,
    /// Content-derived revision token (`sha256:…`, `missing`, or `unavailable`).
    pub revision: String,
    /// Commit policy token: `eligible`, `requiresMigration`, or `blockedUntrusted`.
    pub commit_eligibility: String,
    /// Structured diagnostics in discovery and validation order.
    pub diagnostics: Vec<JsUserSettingsDiagnostic>,
    /// Exact source bytes retained for later semantic preservation.
    pub original_content: Option<Buffer>,
}

/// Opens User Settings relative to an explicit CLASSIC root without changing
/// either supported source document.
#[napi]
pub fn open_user_settings(classic_root: String) -> JsUserSettingsSnapshot {
    let settings = UserSettings::open(classic_root);
    let (schema_major, schema_minor) = settings
        .schema_version()
        .map_or((None, None), |(major, minor)| (Some(major), Some(minor)));

    JsUserSettingsSnapshot {
        update_preferences: JsUpdatePreferences {
            update_check: settings.update_preferences().update_check(),
            origin: preference_origin_token(settings.update_preferences().update_check_origin())
                .to_string(),
        },
        source_location: source_location_token(settings.source().location()).to_string(),
        source_path: settings
            .source()
            .path()
            .map(|path| path.display().to_string()),
        classification: classification_token(settings.classification()).to_string(),
        schema_major,
        schema_minor,
        revision: revision_token(settings.revision()),
        commit_eligibility: commit_eligibility_token(settings.commit_eligibility()).to_string(),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(|diagnostic| JsUserSettingsDiagnostic {
                code: diagnostic.code().to_string(),
                message: diagnostic.message().to_string(),
            })
            .collect(),
        original_content: settings
            .original_bytes()
            .map(|content| Buffer::from(content.to_vec())),
    }
}

/// Returns the JavaScript token for preference provenance.
fn preference_origin_token(origin: PreferenceOrigin) -> &'static str {
    match origin {
        PreferenceOrigin::Document => "document",
        PreferenceOrigin::Default => "default",
        PreferenceOrigin::DegradedFallback => "degradedFallback",
    }
}

/// Returns the JavaScript token for source location.
fn source_location_token(location: SourceLocation) -> &'static str {
    match location {
        SourceLocation::Canonical => "canonical",
        SourceLocation::Legacy => "legacy",
        SourceLocation::Missing => "missing",
    }
}

/// Returns the JavaScript token for document classification.
fn classification_token(classification: DocumentClassification) -> &'static str {
    match classification {
        DocumentClassification::Current => "current",
        DocumentClassification::Unversioned => "unversioned",
        DocumentClassification::Older => "older",
        DocumentClassification::NewerCompatible => "newerCompatible",
        DocumentClassification::FutureMajor => "futureMajor",
        DocumentClassification::LegacyFlat => "legacyFlat",
        DocumentClassification::Malformed => "malformed",
        DocumentClassification::Missing => "missing",
    }
}

/// Returns the JavaScript token for commit eligibility.
fn commit_eligibility_token(eligibility: CommitEligibility) -> &'static str {
    match eligibility {
        CommitEligibility::Eligible => "eligible",
        CommitEligibility::RequiresMigration => "requiresMigration",
        CommitEligibility::BlockedUntrusted => "blockedUntrusted",
    }
}

/// Formats the content revision for JavaScript consumers.
fn revision_token(revision: &Revision) -> String {
    match revision {
        Revision::Missing => "missing".to_string(),
        Revision::Unavailable => "unavailable".to_string(),
        Revision::ContentSha256(digest) => {
            let mut token = String::with_capacity("sha256:".len() + digest.len() * 2);
            token.push_str("sha256:");
            for byte in digest {
                use std::fmt::Write as _;
                write!(&mut token, "{byte:02x}").expect("writing to a String cannot fail");
            }
            token
        }
    }
}
