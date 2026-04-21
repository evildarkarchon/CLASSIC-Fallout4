//! GitHub update checking bridge for CXX FFI.
//!
//! Bridges two related `classic_update_core` surfaces:
//!
//! - **Binary releases** — the pre-existing `GithubClient::has_update` /
//!   `get_latest_release` flow, exposed as
//!   [`ffi::github_has_update`] + [`ffi::github_check_for_updates`].
//! - **YAML data updates** — the yaml-update-delivery flow added in the
//!   `yaml-update-delivery` change. C++ callers use
//!   [`ffi::yaml_check_update`], [`ffi::yaml_apply_update`], and
//!   [`ffi::yaml_rollback_update`] to drive the Pages-first manifest fetch,
//!   atomic cache install, and one-step rollback.
//!
//! CXX FFI cannot carry tagged unions, so [`ffi::YamlUpdateStatusDto`] is a
//! discriminated struct: its `tag` field names the case (0 = Disabled,
//! 1 = UpdateAvailable, 2 = UpToDate, 3 = Unknown, 4 = Error), and the
//! other fields are populated only when the corresponding case is active.
//! C++ callers should inspect `tag` first and treat the rest as empty when
//! a case doesn't apply.

use classic_settings_core::{SchemaCompat, SchemaVersion};
use classic_shared_core::get_runtime;
use classic_update_core::{
    ApprovedUpdate, ClientSchemaSet, FileInstallOutcome, GithubClient, RollbackOutcome,
    UpdateCheckConfig, UpdateError, YamlManifestFile, YamlUpdateStatus,
    apply_yaml_update_with_decision, check_yaml_update, rollback_yaml_update,
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
        Err(e) => {
            let mut dto = empty_status_dto();
            dto.tag = TAG_ERROR;
            dto.error_message = format!("github client init failed: {e}");
            return dto;
        }
    };

    let set = build_client_schema_set(entries);
    let config = build_yaml_config(enabled, bundled_yaml_dir);

    let result = get_runtime().block_on(check_yaml_update(
        &client, pages_url, tag_prefix, &set, config,
    ));

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

#[allow(clippy::ptr_arg)] // CXX Vec transfer — see yaml_check_update.
fn yaml_apply_update(
    pages_url: &str,
    tag_prefix: &str,
    entries: &Vec<ffi::YamlClientSchemaEntryDto>,
    enabled: bool,
    approved_release_tag: &str,
    approved_file_names: &Vec<String>,
    approved_file_sha256: &Vec<String>,
    bundled_yaml_dir: &str,
) -> ffi::YamlUpdateReportDto {
    // Apply is a user-consent-gated operation: we install exactly the files
    // the user reviewed at check-time, for exactly the release tag they
    // saw. The caller passes that decision back via `approved_release_tag`
    // + per-file `(name, sha256)` identity; the core then refuses the
    // install when the live manifest has rotated to a different release or
    // changed the bytes advertised for an approved file.
    //
    // `enabled` is honored end-to-end: passing `false` makes the core
    // return `UpdateCheckDisabled` without any HTTP — the "Update Check:
    // false" setting survives between check and apply even if the user
    // toggled it mid-review.
    let client = match GithubClient::new("evildarkarchon", "CLASSIC-Fallout4") {
        Ok(c) => c,
        Err(e) => {
            return ffi::YamlUpdateReportDto {
                installed: Vec::new(),
                failed: Vec::new(),
                error_message: format!("github client init failed: {e}"),
            };
        }
    };

    let set = build_client_schema_set(entries);
    let config = build_yaml_config(enabled, bundled_yaml_dir);
    let approved = ApprovedUpdate {
        release_tag: approved_release_tag.to_string(),
        file_names: approved_file_names.clone(),
        file_sha256: approved_file_sha256.clone(),
    };

    let result = get_runtime().block_on(apply_yaml_update_with_decision(
        &client, pages_url, tag_prefix, &set, config, &approved,
    ));

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
        Err(UpdateError::UpdateCheckDisabled) => ffi::YamlUpdateReportDto {
            installed: Vec::new(),
            failed: Vec::new(),
            error_message:
                "update check disabled: enable \"Check for Updates on Startup\" and try again"
                    .to_string(),
        },
        Err(UpdateError::DecisionStale { approved, manifest }) => ffi::YamlUpdateReportDto {
            installed: Vec::new(),
            failed: Vec::new(),
            error_message: format!(
                "decision stale: approved release `{approved}` but current manifest is `{manifest}`; re-check required"
            ),
        },
        Err(UpdateError::DecisionDigestStale {
            release_tag,
            file,
            approved_sha256,
            manifest_sha256,
        }) => ffi::YamlUpdateReportDto {
            installed: Vec::new(),
            failed: Vec::new(),
            error_message: format!(
                "decision stale: approved file `{file}` for release `{release_tag}` changed digest from `{approved_sha256}` to `{manifest_sha256}`; re-check required"
            ),
        },
        Err(e) => ffi::YamlUpdateReportDto {
            installed: Vec::new(),
            failed: Vec::new(),
            error_message: format!("apply_yaml_update failed: {e}"),
        },
    }
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
    /// are ignored and the orchestrator treats every compatible manifest
    /// entry as "newer".
    struct YamlClientSchemaEntryDto {
        name: String,
        accepted_major: u32,
        accepted_minimum_minor: u32,
        has_installed: bool,
        installed_major: u32,
        installed_minor: u32,
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

    extern "Rust" {
        fn github_has_update(current: &str, latest: &str) -> bool;
        fn github_check_for_updates(
            owner: &str,
            repo: &str,
            current_version: &str,
        ) -> UpdateCheckResult;

        /// Check for a published YAML data update.
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
        /// `enabled` mirrors the `Update Check: false` settings toggle; when
        /// `false`, no HTTP is issued and `error_message` is populated with
        /// a "update check disabled" diagnostic.
        ///
        /// `approved_release_tag` + the parallel `approved_file_names` /
        /// `approved_file_sha256` arrays form the reviewed decision. They
        /// MUST come from a prior `yaml_check_update` call whose result the
        /// user confirmed — typically from `YamlUpdateStatusDto::release_tag`
        /// and each `compatible_files[i].{name, sha256}` pair. When the live
        /// manifest has since rotated to a different release tag, or it keeps
        /// the same tag/name but changes the bytes advertised for an approved
        /// file, the call returns an empty report with `error_message`
        /// prefixed `decision stale:`.
        ///
        /// `bundled_yaml_dir` has the same meaning as on
        /// [`yaml_check_update`]: empty string keeps the `current_exe()`
        /// fallback; non-empty overrides it.
        fn yaml_apply_update(
            pages_url: &str,
            tag_prefix: &str,
            entries: &Vec<YamlClientSchemaEntryDto>,
            enabled: bool,
            approved_release_tag: &str,
            approved_file_names: &Vec<String>,
            approved_file_sha256: &Vec<String>,
            bundled_yaml_dir: &str,
        ) -> YamlUpdateReportDto;

        fn yaml_rollback_update(file_name: &str) -> YamlRollbackOutcomeDto;
    }
}

#[cfg(test)]
#[path = "update_tests.rs"]
mod tests;
