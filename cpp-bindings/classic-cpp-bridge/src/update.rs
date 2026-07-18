//! GitHub update checking bridge for CXX FFI.
//!
//! Bridges two related `classic_update_core` surfaces:
//!
//! - **Binary releases** — the pre-existing `GithubClient::has_update` /
//!   `get_latest_release` flow, exposed as
//!   [`ffi::github_has_update`] + [`ffi::github_check_for_updates`].
//! - **YAML Data updates** — the first-party YAML Data Update Channel is
//!   exposed through [`ffi::yaml_data_check_update`],
//!   [`ffi::yaml_data_apply_update`], and [`ffi::yaml_data_rollback_update`].
//!   The lower-level generic [`ffi::yaml_check_update`],
//!   [`ffi::yaml_apply_update`], and [`ffi::yaml_rollback_update`] functions
//!   remain available for tests and compatibility callers that need explicit
//!   channel coordinates or schema entries.
//!
//! CXX FFI cannot carry tagged unions, so [`ffi::YamlUpdateStatusDto`] is a
//! discriminated struct: its `tag` field names the case (0 = Disabled,
//! 1 = UpdateAvailable, 2 = UpToDate, 3 = Unknown, 4 = Error), and the
//! other fields are populated only when the corresponding case is active.
//! C++ callers should inspect `tag` first and treat the rest as empty when
//! a case doesn't apply.

use classic_settings_core::{SchemaCompat, SchemaVersion};
use classic_shared_core::get_runtime;
use classic_update_core::yaml_update::{
    apply_yaml_data_update_with_decision, check_yaml_data_update, rollback_yaml_data_update,
};
use classic_update_core::{
    ApprovedUpdate, Classification, ClientSchemaSet, FileInstallOutcome, GithubClient,
    NotificationStatus, RollbackOutcome, UpdateCheckConfig, UpdateError, YamlManifestFile,
    YamlUpdateStatus, apply_yaml_update_with_decision,
    check_app_notification as core_check_app_notification, check_yaml_update, rollback_yaml_update,
};

// ---------------------------------------------------------------------------
// Binary-release bridge (unchanged)
// ---------------------------------------------------------------------------

fn github_has_update(current: &str, latest: &str) -> bool {
    let client = match GithubClient::new("evildarkarchon", "CLASSIC-Fallout4") {
        Ok(client) => client,
        Err(_) => return false,
    };
    client.has_update(current, latest).unwrap_or_default()
}

#[allow(deprecated)] // compat bridge to GithubClient::get_latest_release (design D-08); migrate in notification-bridge task 3.2.
fn github_check_for_updates(
    owner: &str,
    repo: &str,
    current_version: &str,
) -> ffi::UpdateCheckResult {
    let client = match GithubClient::new(owner, repo) {
        Ok(client) => client,
        Err(e) => {
            return ffi::UpdateCheckResult {
                has_update: false,
                latest_version: String::new(),
                release_notes: String::new(),
                error_message: format!("{e}"),
            };
        }
    };
    match get_runtime().block_on(client.get_latest_release()) {
        Ok(release) => {
            let has_update = client
                .has_update(current_version, &release.tag_name)
                .unwrap_or(false);
            ffi::UpdateCheckResult {
                has_update,
                latest_version: release.tag_name,
                release_notes: release.body,
                error_message: String::new(),
            }
        }
        Err(e) => ffi::UpdateCheckResult {
            has_update: false,
            latest_version: String::new(),
            release_notes: String::new(),
            error_message: format!("{e}"),
        },
    }
}

// ---------------------------------------------------------------------------
// YAML-update bridge (yaml-update-delivery)
// ---------------------------------------------------------------------------

/// Discriminator for [`ffi::YamlUpdateStatusDto::tag`].
const TAG_DISABLED: u32 = 0;
const TAG_UPDATE_AVAILABLE: u32 = 1;
const TAG_UP_TO_DATE: u32 = 2;
const TAG_UNKNOWN: u32 = 3;
const TAG_ERROR: u32 = 4;

fn build_client_schema_set(entries: &[ffi::YamlClientSchemaEntryDto]) -> ClientSchemaSet {
    let mut set = ClientSchemaSet::new();
    for entry in entries {
        let accepted = SchemaCompat::new(entry.accepted_major, entry.accepted_minimum_minor);
        let installed = if entry.has_installed {
            Some(SchemaVersion::new(
                entry.installed_major,
                entry.installed_minor,
            ))
        } else {
            None
        };
        set.insert(entry.name.clone(), accepted, installed);
    }
    set
}

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
/// [`UpdateCheckConfig`]. An empty `bundled_yaml_dir` keeps the
/// `current_exe()` fallback (correct for native frontends); anything else
/// becomes an explicit override.
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

// CXX bridge requires `&Vec<T>` (mapped to `const rust::Vec<T>&` in C++); the
// `ptr_arg` clippy lint's "use `&[_]`" suggestion does not apply here because
// cxx shared-struct transfer is by Vec, not slice.
#[allow(clippy::ptr_arg)]
fn yaml_check_update(
    pages_url: &str,
    tag_prefix: &str,
    entries: &Vec<ffi::YamlClientSchemaEntryDto>,
    enabled: bool,
    bundled_yaml_dir: &str,
) -> ffi::YamlUpdateStatusDto {
    let client = match GithubClient::new("evildarkarchon", "CLASSIC-Fallout4") {
        Ok(c) => c,
        Err(e) => return yaml_github_client_error_dto(e),
    };

    let set = build_client_schema_set(entries);
    let config = build_yaml_config(enabled, bundled_yaml_dir);

    let result = get_runtime().block_on(check_yaml_update(
        &client, pages_url, tag_prefix, &set, config,
    ));

    yaml_status_to_dto(result)
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

fn yaml_apply_update(request: &ffi::YamlApplyRequestDto) -> ffi::YamlUpdateReportDto {
    // Apply is a user-consent-gated operation: we install exactly the files
    // the user reviewed at check-time, for exactly the release tag they
    // saw. The caller passes that decision back via `request.approved`; the
    // core then refuses the install when the live manifest has rotated to a
    // different release or changed the bytes advertised for an approved file.
    //
    // `request.enabled` is honored end-to-end: passing `false` makes the
    // core return `UpdateCheckDisabled` without any HTTP — the "Update
    // Check: false" setting survives between check and apply even if the
    // user toggled it mid-review.
    let client = match GithubClient::new("evildarkarchon", "CLASSIC-Fallout4") {
        Ok(c) => c,
        Err(e) => return yaml_github_client_report_error_dto(e),
    };

    let set = build_client_schema_set(&request.entries);
    let config = build_yaml_config(request.enabled, &request.bundled_yaml_dir);
    let approved = approved_update_from_dto(&request.approved);

    let result = get_runtime().block_on(apply_yaml_update_with_decision(
        &client,
        &request.pages_url,
        &request.tag_prefix,
        &set,
        config,
        &approved,
    ));

    yaml_report_to_dto(result)
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

fn yaml_rollback_update(file_name: &str) -> ffi::YamlRollbackOutcomeDto {
    match rollback_yaml_update(file_name) {
        Ok(RollbackOutcome::RolledBack { file_name: f }) => ffi::YamlRollbackOutcomeDto {
            rolled_back: true,
            file_name: f,
            error_message: String::new(),
        },
        Ok(RollbackOutcome::NoPreviousVersion { file_name: f }) => ffi::YamlRollbackOutcomeDto {
            rolled_back: false,
            file_name: f,
            error_message: String::new(),
        },
        Err(e) => ffi::YamlRollbackOutcomeDto {
            rolled_back: false,
            file_name: file_name.to_string(),
            error_message: format!("{e}"),
        },
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
    /// Result of a binary-release update check (existing).
    struct UpdateCheckResult {
        has_update: bool,
        latest_version: String,
        release_notes: String,
        error_message: String,
    }

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

    /// Client-side compatibility entry passed into [`yaml_check_update`] /
    /// [`yaml_apply_update`]. Callers build one per shippable file family.
    ///
    /// When `has_installed` is `false`, `installed_major` / `installed_minor`
    /// are ignored and the generic updater attempts cache/bundled fallback
    /// discovery before treating a compatible manifest entry as newer.
    struct YamlClientSchemaEntryDto {
        name: String,
        accepted_major: u32,
        accepted_minimum_minor: u32,
        has_installed: bool,
        installed_major: u32,
        installed_minor: u32,
    }

    /// Reviewed decision captured from a prior `yaml_check_update` call.
    struct ApprovedUpdateDto {
        release_tag: String,
        file_names: Vec<String>,
        file_sha256: Vec<String>,
    }

    /// Structured input to `yaml_apply_update`.
    struct YamlApplyRequestDto {
        pages_url: String,
        tag_prefix: String,
        entries: Vec<YamlClientSchemaEntryDto>,
        enabled: bool,
        approved: ApprovedUpdateDto,
        bundled_yaml_dir: String,
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

    /// Result of [`yaml_apply_update`]. `error_message` is non-empty only
    /// when the entire batch failed (e.g. cache dir unresolvable); a
    /// mixed-outcome batch is still a success at the FFI level.
    struct YamlUpdateReportDto {
        installed: Vec<YamlUpdateFileOutcomeDto>,
        failed: Vec<YamlUpdateFileOutcomeDto>,
        error_message: String,
    }

    /// Result of [`yaml_rollback_update`]. `rolled_back == false` with an
    /// empty `error_message` means `NoPreviousVersion` (not an error).
    struct YamlRollbackOutcomeDto {
        rolled_back: bool,
        file_name: String,
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
        fn github_has_update(current: &str, latest: &str) -> bool;
        fn github_check_for_updates(
            owner: &str,
            repo: &str,
            current_version: &str,
        ) -> UpdateCheckResult;

        /// Check the first-party YAML Data Update Channel.
        ///
        /// Native CLI/GUI callers pass only the user's Update Check setting.
        /// Rust owns the Pages URL, `yaml-data-v*` tag namespace, current
        /// shippable file set, accepted schema ranges, and installed-file
        /// enrichment. `enabled == false` returns `tag == 0` without HTTP.
        fn yaml_data_check_update(enabled: bool) -> YamlUpdateStatusDto;

        /// Install exactly the files approved from a prior first-party check.
        ///
        /// `approved` MUST be built from `yaml_data_check_update` result data
        /// the user reviewed: `release_tag` plus each compatible file's
        /// `(name, sha256)`. The Rust core re-fetches the live manifest and
        /// refuses stale release tags or digest drift before touching disk.
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

        /// Check for a published YAML data update.
        ///
        /// This is the lower-level compatibility seam. Native first-party
        /// callers should prefer [`yaml_data_check_update`] so they do not
        /// duplicate channel coordinates or schema metadata.
        ///
        /// `bundled_yaml_dir` is an explicit install-tree directory that
        /// contains the bundled shippable YAML files (e.g.
        /// `CLASSIC Data/databases`). Native C++ frontends normally pass
        /// an empty string to keep the `current_exe()` fallback — that
        /// resolves correctly because the CLI/GUI exe lives next to
        /// `CLASSIC Data/`. Pass an explicit path only when running from
        /// a context where `current_exe()` would yield the wrong parent
        /// (integration tests, unusual installers).
        fn yaml_check_update(
            pages_url: &str,
            tag_prefix: &str,
            entries: &Vec<YamlClientSchemaEntryDto>,
            enabled: bool,
            bundled_yaml_dir: &str,
        ) -> YamlUpdateStatusDto;

        /// Install exactly the files the user approved at check-time.
        ///
        /// This is the lower-level compatibility seam. Native first-party
        /// callers should prefer [`yaml_data_apply_update`] so they do not
        /// duplicate channel coordinates or schema metadata.
        ///
        /// `request.enabled` mirrors the `Update Check: false` settings
        /// toggle; when `false`, no HTTP is issued and `error_message` is
        /// populated with a "update check disabled" diagnostic.
        ///
        /// `request.approved` MUST come from a prior `yaml_check_update`
        /// call whose result the user confirmed — typically from
        /// `YamlUpdateStatusDto::release_tag` and each
        /// `compatible_files[i].{name, sha256}` pair. When the live manifest
        /// has since rotated to a different release tag, or it keeps the
        /// same tag/name but changes the bytes advertised for an approved
        /// file, the call returns an empty report with `error_message`
        /// prefixed `decision stale:`.
        ///
        /// `request.bundled_yaml_dir` has the same meaning as on
        /// [`yaml_check_update`]: empty string keeps the `current_exe()`
        /// fallback; non-empty overrides it.
        fn yaml_apply_update(request: &YamlApplyRequestDto) -> YamlUpdateReportDto;

        /// Roll back one caller-named YAML cache file.
        ///
        /// This lower-level compatibility seam remains available for tests
        /// and unusual hosts. Native first-party callers should use
        /// [`yaml_data_rollback_update`] so Rust owns the target list.
        fn yaml_rollback_update(file_name: &str) -> YamlRollbackOutcomeDto;

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
