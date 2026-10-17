//! GitHub update checking bridge for CXX FFI.
//!
//! Bridges two related `classic_update_core` surfaces:
//!
//! - **App-update notifications** — [`ffi::check_app_notification`] reports
//!   whether a newer CLASSIC binary release has been announced.
//! - **YAML Data updates** — the first-party YAML Data Update Channel is
//!   exposed through [`ffi::yaml_data_check_update`],
//!   [`ffi::yaml_data_apply_update`], and [`ffi::yaml_data_rollback_update`].
//!   Rust owns the channel coordinates and schema metadata; the generic
//!   explicit-channel updater stays Rust-only.
//!
//! CXX FFI cannot carry tagged unions, so [`ffi::YamlUpdateStatusDto`] is a
//! discriminated struct: its `tag` field names the case (0 = Disabled,
//! 1 = UpdateAvailable, 2 = UpToDate, 3 = Unknown, 4 = Error), and the
//! other fields are populated only when the corresponding case is active.
//! C++ callers should inspect `tag` first and treat the rest as empty when
//! a case doesn't apply.

use classic_shared_core::get_runtime;
use classic_update_core::yaml_update::{
    apply_yaml_data_update_with_decision, check_yaml_data_update, rollback_yaml_data_update,
};
use classic_update_core::{
    ApprovedUpdate, Classification, FileInstallOutcome, GithubClient, NotificationStatus,
    RollbackOutcome, UpdateCheckConfig, UpdateError, YamlManifestFile, YamlUpdateStatus,
    check_app_notification as core_check_app_notification,
};

// ---------------------------------------------------------------------------
// YAML-update bridge (yaml-update-delivery)
// ---------------------------------------------------------------------------

/// Discriminator for [`ffi::YamlUpdateStatusDto::tag`].
const TAG_DISABLED: u32 = 0;
const TAG_UPDATE_AVAILABLE: u32 = 1;
const TAG_UP_TO_DATE: u32 = 2;
const TAG_UNKNOWN: u32 = 3;
const TAG_ERROR: u32 = 4;

fn manifest_file_to_dto(f: &YamlManifestFile) -> ffi::YamlUpdateFileDto {
    ffi::YamlUpdateFileDto {
        name: f.name.clone(),
        schema_version: f.schema_version.clone(),
        sha256: f.sha256.clone(),
        size_bytes: f.size_bytes,
        download_url: f.download_url.clone(),
    }
}

fn empty_status_dto() -> ffi::YamlUpdateStatusDto {
    ffi::YamlUpdateStatusDto {
        tag: TAG_DISABLED,
        release_tag: String::new(),
        published_at: String::new(),
        compatible_files: Vec::new(),
        incompatible_files: Vec::new(),
        incompatible_reasons: Vec::new(),
        unknown_reason: String::new(),
        error_message: String::new(),
    }
}

/// Translate the CXX-friendly empty-string-for-None convention into a core
/// [`UpdateCheckConfig`]. An empty `bundled_yaml_dir` keeps automatic
/// resolution: first-party helpers probe the native frontend installation
/// layouts, while generic helpers retain their `current_exe()`-relative
/// bundled-directory fallback. Anything else becomes an explicit override.
fn build_yaml_config(enabled: bool, bundled_yaml_dir: &str) -> UpdateCheckConfig {
    let mut cfg = if enabled {
        UpdateCheckConfig::enabled()
    } else {
        UpdateCheckConfig::disabled()
    };
    if !bundled_yaml_dir.is_empty() {
        cfg = cfg.with_bundled_yaml_dir(std::path::PathBuf::from(bundled_yaml_dir));
    }
    cfg
}

fn yaml_status_to_dto(result: Result<YamlUpdateStatus, UpdateError>) -> ffi::YamlUpdateStatusDto {
    match result {
        Ok(YamlUpdateStatus::Disabled) => {
            let mut dto = empty_status_dto();
            dto.tag = TAG_DISABLED;
            dto
        }
        Ok(YamlUpdateStatus::UpToDate {
            manifest,
            incompatible_files,
        }) => {
            let mut dto = empty_status_dto();
            dto.tag = TAG_UP_TO_DATE;
            dto.release_tag = manifest.release_tag;
            dto.published_at = manifest.published_at;
            // Surface rejection diagnostics even on the "nothing to do"
            // outcome so the GUI / CLI can display "feed contains N future
            // files your client cannot install; upgrading will unlock them"
            // alongside the release_tag / published_at UX.
            for rej in &incompatible_files {
                dto.incompatible_files.push(manifest_file_to_dto(&rej.file));
                dto.incompatible_reasons.push(rej.reason.clone());
            }
            dto
        }
        Ok(YamlUpdateStatus::UpdateAvailable {
            manifest,
            compatible_files,
            incompatible_files,
        }) => {
            let mut dto = empty_status_dto();
            dto.tag = TAG_UPDATE_AVAILABLE;
            dto.release_tag = manifest.release_tag;
            dto.published_at = manifest.published_at;
            dto.compatible_files = compatible_files.iter().map(manifest_file_to_dto).collect();
            for rej in &incompatible_files {
                dto.incompatible_files.push(manifest_file_to_dto(&rej.file));
                dto.incompatible_reasons.push(rej.reason.clone());
            }
            dto
        }
        Ok(YamlUpdateStatus::Unknown { reason }) => {
            let mut dto = empty_status_dto();
            dto.tag = TAG_UNKNOWN;
            dto.unknown_reason = reason;
            dto
        }
        Err(e) => {
            let mut dto = empty_status_dto();
            dto.tag = TAG_ERROR;
            dto.error_message = format!("{e}");
            dto
        }
    }
}

fn yaml_github_client_error_dto(error: UpdateError) -> ffi::YamlUpdateStatusDto {
    let mut dto = empty_status_dto();
    dto.tag = TAG_ERROR;
    dto.error_message = format!("github client init failed: {error}");
    dto
}

fn yaml_data_check_update(enabled: bool) -> ffi::YamlUpdateStatusDto {
    let client = match GithubClient::new("evildarkarchon", "CLASSIC-Fallout4") {
        Ok(c) => c,
        Err(e) => return yaml_github_client_error_dto(e),
    };

    let config = build_yaml_config(enabled, "");
    let result = get_runtime().block_on(check_yaml_data_update(&client, config));
    yaml_status_to_dto(result)
}

fn approved_update_from_dto(approved: &ffi::ApprovedUpdateDto) -> ApprovedUpdate {
    ApprovedUpdate {
        release_tag: approved.release_tag.clone(),
        file_names: approved.file_names.clone(),
        file_sha256: approved.file_sha256.clone(),
    }
}

fn yaml_report_error_dto(message: String) -> ffi::YamlUpdateReportDto {
    ffi::YamlUpdateReportDto {
        installed: Vec::new(),
        failed: Vec::new(),
        error_message: message,
    }
}

fn yaml_github_client_report_error_dto(error: UpdateError) -> ffi::YamlUpdateReportDto {
    yaml_report_error_dto(format!("github client init failed: {error}"))
}

fn yaml_report_to_dto(
    result: Result<classic_update_core::YamlUpdateReport, UpdateError>,
) -> ffi::YamlUpdateReportDto {
    match result {
        Ok(report) => ffi::YamlUpdateReportDto {
            installed: report
                .installed
                .iter()
                .map(install_outcome_to_dto)
                .collect(),
            failed: report.failed.iter().map(install_outcome_to_dto).collect(),
            error_message: String::new(),
        },
        // Typed errors get stable, GUI-parseable prefixes so the Qt layer
        // can route the "re-check required" message distinctly from a
        // generic transport failure.
        Err(UpdateError::UpdateCheckDisabled) => yaml_report_error_dto(
            "update check disabled: enable \"Check for Updates on Startup\" and try again"
                .to_string(),
        ),
        Err(UpdateError::DecisionStale { approved, manifest }) => yaml_report_error_dto(format!(
            "decision stale: approved release `{approved}` but current manifest is `{manifest}`; re-check required"
        )),
        Err(UpdateError::DecisionDigestStale {
            release_tag,
            file,
            approved_sha256,
            manifest_sha256,
        }) => yaml_report_error_dto(format!(
            "decision stale: approved file `{file}` for release `{release_tag}` changed digest from `{approved_sha256}` to `{manifest_sha256}`; re-check required"
        )),
        Err(e) => yaml_report_error_dto(format!("apply_yaml_update failed: {e}")),
    }
}

fn yaml_data_apply_update(
    enabled: bool,
    approved: &ffi::ApprovedUpdateDto,
) -> ffi::YamlUpdateReportDto {
    let client = match GithubClient::new("evildarkarchon", "CLASSIC-Fallout4") {
        Ok(c) => c,
        Err(e) => return yaml_github_client_report_error_dto(e),
    };

    let config = build_yaml_config(enabled, "");
    let approved = approved_update_from_dto(approved);
    let result = get_runtime().block_on(apply_yaml_data_update_with_decision(
        &client, config, &approved,
    ));
    yaml_report_to_dto(result)
}

fn install_outcome_to_dto(outcome: &FileInstallOutcome) -> ffi::YamlUpdateFileOutcomeDto {
    match outcome {
        FileInstallOutcome::Installed {
            name,
            schema_version,
            created_prev,
        } => ffi::YamlUpdateFileOutcomeDto {
            name: name.clone(),
            installed: true,
            schema_version: schema_version.clone(),
            created_prev: *created_prev,
            failure_reason: String::new(),
        },
        FileInstallOutcome::Failed { name, reason } => ffi::YamlUpdateFileOutcomeDto {
            name: name.clone(),
            installed: false,
            schema_version: String::new(),
            created_prev: false,
            failure_reason: reason.clone(),
        },
    }
}

// ---------------------------------------------------------------------------
// App-notification bridge (app-update-manifest-notification change, §3)
// ---------------------------------------------------------------------------
//
// Surface contract: empty-string sentinels + `classification` string for the
// discriminator, matching `docs/api/error-contract.md`. Error case sets
// `classification = "error"` with `error_message` populated; every other
// field carries an empty-string sentinel. On success, the Rust
// `NotificationStatus` is flattened (optional `display` sub-object becomes
// `display_title` / `display_body` / `display_cta_url` with empty strings
// where the source was `None`).

/// Discriminator string values in [`ffi::NotificationStatusDto::classification`].
const CLASSIFICATION_UP_TO_DATE: &str = "up_to_date";
const CLASSIFICATION_UPDATE_AVAILABLE: &str = "update_available";
const CLASSIFICATION_DEPRECATED: &str = "deprecated_client";
const CLASSIFICATION_UNKNOWN: &str = "unknown";
const CLASSIFICATION_NOT_PUBLISHED: &str = "not_published";
const CLASSIFICATION_ERROR: &str = "error";

fn classification_label(c: Classification) -> &'static str {
    match c {
        Classification::UpToDate => CLASSIFICATION_UP_TO_DATE,
        Classification::UpdateAvailable => CLASSIFICATION_UPDATE_AVAILABLE,
        Classification::DeprecatedClient => CLASSIFICATION_DEPRECATED,
        Classification::Unknown => CLASSIFICATION_UNKNOWN,
        Classification::NotPublished => CLASSIFICATION_NOT_PUBLISHED,
    }
}

fn notification_status_to_dto(status: &NotificationStatus) -> ffi::NotificationStatusDto {
    let (display_title, display_body, display_cta_url) = match status.display.as_ref() {
        Some(d) => (
            d.title.clone(),
            d.body.clone(),
            d.cta_url.clone().unwrap_or_default(),
        ),
        None => (String::new(), String::new(), String::new()),
    };
    ffi::NotificationStatusDto {
        classification: classification_label(status.classification).to_string(),
        latest_version: status.latest_version.clone(),
        published_at: status.published_at.clone(),
        min_supported_version: status.min_supported_version.clone().unwrap_or_default(),
        display_title,
        display_body,
        display_cta_url,
        parse_error: status.parse_error.clone().unwrap_or_default(),
        error_message: String::new(),
    }
}

fn notification_error_dto(error: &UpdateError) -> ffi::NotificationStatusDto {
    ffi::NotificationStatusDto {
        classification: CLASSIFICATION_ERROR.to_string(),
        latest_version: String::new(),
        published_at: String::new(),
        min_supported_version: String::new(),
        display_title: String::new(),
        display_body: String::new(),
        display_cta_url: String::new(),
        parse_error: String::new(),
        error_message: error.to_string(),
    }
}

fn check_app_notification(
    owner: &str,
    repo: &str,
    installed_version: &str,
) -> ffi::NotificationStatusDto {
    match get_runtime().block_on(core_check_app_notification(owner, repo, installed_version)) {
        Ok(status) => notification_status_to_dto(&status),
        Err(err) => notification_error_dto(&err),
    }
}

fn yaml_data_rollback_update() -> ffi::YamlRollbackReportDto {
    let mut dto = ffi::YamlRollbackReportDto {
        rolled_back: Vec::new(),
        no_previous_version: Vec::new(),
        failed_files: Vec::new(),
        failure_reasons: Vec::new(),
    };

    for (requested_name, outcome) in get_runtime().block_on(rollback_yaml_data_update()) {
        match outcome {
            Ok(RollbackOutcome::RolledBack { file_name }) => dto.rolled_back.push(file_name),
            Ok(RollbackOutcome::NoPreviousVersion { file_name }) => {
                dto.no_previous_version.push(file_name);
            }
            Err(error) => {
                dto.failed_files.push(requested_name);
                dto.failure_reasons.push(error.to_string());
            }
        }
    }

    dto
}

#[cxx::bridge(namespace = "classic::update")]
mod ffi {
    /// One file entry inside [`YamlUpdateStatusDto`] or
    /// [`YamlUpdateReportDto`]. Mirrors `YamlManifestFile` but flattens the
    /// optional `min_client_schema`/`max_client_schema` away — the C++ GUI
    /// doesn't read those today.
    struct YamlUpdateFileDto {
        name: String,
        schema_version: String,
        sha256: String,
        size_bytes: u64,
        download_url: String,
    }

    /// Reviewed decision captured from a prior `yaml_data_check_update` call.
    struct ApprovedUpdateDto {
        release_tag: String,
        file_names: Vec<String>,
        file_sha256: Vec<String>,
    }

    /// Discriminated status DTO. Read `tag` first:
    /// - 0 `Disabled`: `Update Check: false`; nothing fetched.
    /// - 1 `UpdateAvailable`: compatible_files + incompatible_files populated.
    /// - 2 `UpToDate`: release_tag + published_at populated; nothing else.
    /// - 3 `Unknown`: unknown_reason populated (e.g. unsupported manifest_version).
    /// - 4 `Error`: error_message populated; manifest state unchanged on disk.
    struct YamlUpdateStatusDto {
        tag: u32,
        release_tag: String,
        published_at: String,
        compatible_files: Vec<YamlUpdateFileDto>,
        incompatible_files: Vec<YamlUpdateFileDto>,
        /// Reason parallel to `incompatible_files`, same index.
        incompatible_reasons: Vec<String>,
        unknown_reason: String,
        error_message: String,
    }

    /// Per-file install outcome inside [`YamlUpdateReportDto`]. When
    /// `installed == true`, `schema_version` and `created_prev` are
    /// populated. When `installed == false`, `failure_reason` is populated.
    struct YamlUpdateFileOutcomeDto {
        name: String,
        installed: bool,
        schema_version: String,
        created_prev: bool,
        failure_reason: String,
    }

    /// Result of [`yaml_data_apply_update`]. `error_message` is non-empty only
    /// when the entire batch failed (e.g. cache dir unresolvable); a
    /// mixed-outcome batch is still a success at the FFI level.
    struct YamlUpdateReportDto {
        installed: Vec<YamlUpdateFileOutcomeDto>,
        failed: Vec<YamlUpdateFileOutcomeDto>,
        error_message: String,
    }

    /// Aggregate result of first-party [`yaml_data_rollback_update`].
    struct YamlRollbackReportDto {
        /// Files whose previous generation was restored.
        rolled_back: Vec<String>,
        /// Files that had no previous generation to restore.
        no_previous_version: Vec<String>,
        /// Files whose rollback failed outright.
        failed_files: Vec<String>,
        /// Reason parallel to `failed_files`, same index.
        failure_reasons: Vec<String>,
    }

    /// Result of [`check_app_notification`]. C++ callers inspect
    /// `classification` first:
    ///
    /// - `"up_to_date"` — installed `>=` manifest `latest_version`.
    /// - `"update_available"` — installed `<` manifest `latest_version`; the
    ///   display fields (`display_title`, `display_body`, `display_cta_url`)
    ///   may be populated and SHOULD be surfaced to the user.
    /// - `"deprecated_client"` — installed `<` manifest `min_supported_version`.
    ///   `min_supported_version` carries the publisher's declared floor.
    /// - `"unknown"` — the installed-version string could not be parsed as
    ///   semver; `parse_error` carries the diagnostic. The caller MUST NOT
    ///   treat this as `up_to_date`.
    /// - `"not_published"` — no notification manifest exists on either channel.
    ///   Manifest fields, `parse_error`, and `error_message` are empty-string
    ///   sentinels; callers MUST NOT treat this as the `"error"` classification.
    /// - `"error"` — both Pages and Releases fallbacks failed (or the
    ///   manifest body was structurally invalid). `error_message` carries
    ///   the `Display` rendering of the underlying `UpdateError`, and every
    ///   other string field is an empty-string sentinel per
    ///   `docs/api/error-contract.md`.
    ///
    /// Optional Rust fields are flattened with empty-string sentinels:
    /// `min_supported_version == ""` means the manifest omitted the field;
    /// `display_title == ""` means there was no display payload (in which
    /// case `display_body` and `display_cta_url` will also be empty).
    struct NotificationStatusDto {
        classification: String,
        latest_version: String,
        published_at: String,
        min_supported_version: String,
        display_title: String,
        display_body: String,
        display_cta_url: String,
        parse_error: String,
        error_message: String,
    }

    extern "Rust" {
        /// Check the first-party YAML Data Update Channel.
        ///
        /// Native CLI/GUI callers pass only the user's Update Check setting.
        /// Rust owns installation-root discovery across the supported native
        /// layouts, the Pages URL, `yaml-data-v*` tag namespace, current
        /// shippable file set, accepted schema ranges, and installed-file
        /// enrichment. `enabled == false` returns `tag == 0` without HTTP.
        fn yaml_data_check_update(enabled: bool) -> YamlUpdateStatusDto;

        /// Install exactly the files approved from a prior first-party check.
        ///
        /// `approved` MUST be built from `yaml_data_check_update` result data
        /// the user reviewed: `release_tag` plus each compatible file's
        /// `(name, sha256)`. The Rust core re-fetches the live manifest and
        /// refuses stale release tags or digest drift before touching disk.
        /// Installation-root discovery follows the same native layout search
        /// as [`yaml_data_check_update`].
        fn yaml_data_apply_update(
            enabled: bool,
            approved: &ApprovedUpdateDto,
        ) -> YamlUpdateReportDto;

        /// Roll back every current first-party shippable YAML Data file.
        ///
        /// The Rust core owns the rollback target list. Per-file failures are
        /// returned in `failed_files` / `failure_reasons`; a file with no
        /// `.prev` generation is reported under `no_previous_version`.
        fn yaml_data_rollback_update() -> YamlRollbackReportDto;

        /// Check for a published CLASSIC binary-release notification.
        ///
        /// Fetches the payload-free notification manifest Pages-first
        /// (`https://<owner>.github.io/<repo>/app-notification/manifest-latest.json`)
        /// with an ETag cache and falls back to listing releases filtered
        /// by the `app-notification-v*` tag prefix. Returns a
        /// [`NotificationStatusDto`] whose `classification` field names
        /// the outcome; on failure, `classification = "error"` and
        /// `error_message` is populated (empty-string sentinels on every
        /// other string field per `docs/api/error-contract.md`).
        ///
        /// `owner` and `repo` identify the GitHub org / repo slug
        /// (e.g. `"evildarkarchon"` / `"CLASSIC-Fallout4"`).
        /// `installed_version` is the caller's current client semver; a
        /// leading `v` or `V` is tolerated.
        fn check_app_notification(
            owner: &str,
            repo: &str,
            installed_version: &str,
        ) -> NotificationStatusDto;
    }
}

#[cfg(test)]
#[path = "update_tests.rs"]
mod tests;
