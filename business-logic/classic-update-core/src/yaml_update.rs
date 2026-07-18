//! YAML data-update delivery: DTOs, fetch path, and install orchestrator.
//!
//! This module implements the client-side half of the yaml-update-delivery
//! change. It is wholly responsible for:
//!
//! - Deserializing a published `manifest.json` into typed DTOs.
//! - Fetching that manifest with a **Pages-first** lookup that falls back to
//!   the anonymous `GET /releases` endpoint only when Pages is unreachable
//!   (see [`fetch_yaml_manifest`]).
//! - Downloading each advertised YAML file to the per-user yaml-cache
//!   directory and installing it atomically via
//!   [`classic_file_io_core::install_atomic`].
//! - Rolling back one installed generation via
//!   [`classic_file_io_core::rollback`].
//!
//! # No client credentials
//!
//! Nothing in this module synthesizes, embeds, or requires a GitHub token.
//! The existing `classic_update_core::GithubClient` already opportunistically
//! attaches an `Authorization: Bearer` header when `$GITHUB_TOKEN` is set in
//! the environment (see [`crate::github`]); that behavior is preserved
//! unchanged. The unit tests in this module run with `$GITHUB_TOKEN` unset
//! (we deliberately use [`GithubClient::with_base_url`] with `None` so they
//! never accidentally authenticate even if a developer has a `.env` file
//! nearby).
//!
//! Asset downloads always target the URL *verbatim* from the manifest's
//! `download_url` field — the client never constructs asset URLs. However,
//! that verbatim URL must match the canonical release-asset template
//! `https://github.com/<configured-owner>/<configured-repo>/releases/download/<manifest.release_tag>/<url-encoded entry.name>`
//! (see [`is_canonical_asset_url`]). Pinning to the configured owner/repo
//! and the manifest's own `release_tag` prevents a mispublished or
//! compromised manifest from redirecting clients to unrelated GitHub-hosted
//! content that the publisher never actually released. This check lives at
//! both the validation boundary ([`validate_manifest`]) and the download
//! boundary ([`download_release_asset`]) so a direct binding call that
//! bypasses the manifest fetch still cannot escape the template.
//!
//! # Signatures
//!
//! [`SignatureDescriptor`] is parsed here but verification is deliberately a
//! Phase-E concern (see the yaml-update-delivery change, Section 11a). Today
//! a missing or invalid signature is silently tolerated at load; the default
//! policy is `VerifyIfPresent` and the verifier itself lands in a follow-up
//! phase. The DTO surface is stable now so that phase only needs to plug in
//! verification, not rewrite the manifest shape.
//!
//! # Runtime
//!
//! All async calls run on the shared `classic_shared_core::get_runtime()`.
//! This module does not construct its own runtime (enforced by the
//! workspace-wide ONE RUNTIME RULE).

use crate::error::{Result, UpdateError};
use crate::github::GithubClient;
use classic_config_core::{
    InstalledYamlDataInspection, InstalledYamlDataInspectionRequest, client_schemas,
    inspect_installed_yaml_data, inspect_installed_yaml_data_with_env,
};
use classic_file_io_core::{FileIOError, RollbackOutcome as FsRollbackOutcome, install_atomic};
use classic_path_core::{ensure_yaml_cache_dir, ensure_yaml_cache_dir_with_env};
use classic_settings_core::{Compatibility, SchemaCompat, SchemaVersion, schema_compat_check};
use classic_shared_core::GameId;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tokio::io::AsyncWriteExt;

/// Highest `manifest_version` this client can parse. Bumped only when the
/// manifest shape actually changes in a way existing clients cannot tolerate.
pub const MAX_MANIFEST_VERSION: u32 = 1;

/// GitHub Pages path segment for the first-party YAML Data manifest.
const YAML_DATA_PAGES_PATH_SEGMENT: &str = "yaml-data/manifest-latest.json";

/// User-owned Local Ignore data is never eligible for the remote YAML Data channel.
const LOCAL_IGNORE_YAML_FILE_NAME: &str = "CLASSIC Ignore.yaml";

/// Release tag prefix owned by the first-party YAML Data Update Channel.
const YAML_DATA_TAG_PREFIX: &str = "yaml-data-v";

// Pages-cache constants live in [`crate::manifest_fetch`] now that two
// channels (yaml-data and app-notification) both fetch through the shared
// helper. Re-exported here so existing `classic_update_core::yaml_update::ETAG_FILENAME`
// call sites and the crate-root `pub use` statement in `lib.rs` keep working
// without adjustment.
pub use crate::manifest_fetch::{CACHED_MANIFEST_FILENAME, ETAG_FILENAME};

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// One descriptor inside `manifest.signatures`. Each descriptor names a
/// signature artifact and the subject that produced it, so the verifier
/// planned in Phase E can confirm the bundle without another round-trip.
///
/// `format` is the artifact type tag — the only value understood today is
/// `"sigstore-bundle-v1"`, but the DTO shape is forward-compatible so new
/// formats can be added without breaking existing clients.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SignatureDescriptor {
    /// Artifact-type tag (e.g. `"sigstore-bundle-v1"`).
    pub format: String,
    /// `"sha256:<hex>"` of the canonicalized manifest bytes the signature
    /// covers, with the `signatures` array itself stripped.
    pub payload_digest: String,
    /// Absolute HTTPS URL pointing at the signature artifact on the release
    /// (e.g. `manifest.json.sigstore`).
    pub bundle_url: String,
    /// Sigstore Fulcio certificate SAN identifying the signing workflow.
    pub cert_identity: String,
    /// OIDC issuer URL that minted the Fulcio cert.
    pub cert_issuer: String,
}

/// One file entry inside `manifest.files`. Each entry is a self-contained
/// pointer to a single release asset plus the metadata the client needs to
/// decide whether to install it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct YamlManifestFile {
    /// Canonical file name (e.g. `CLASSIC Main.yaml`). Matches the cache-dir
    /// target path exactly.
    pub name: String,
    /// `MAJOR.MINOR` schema version the file itself declares at its YAML
    /// root.
    pub schema_version: String,
    /// Hex-encoded SHA-256 of the file bytes. Compared to the downloaded
    /// content before atomic rename.
    pub sha256: String,
    /// File size in bytes. Advisory; not enforced by the downloader today.
    pub size_bytes: u64,
    /// Lowest `MAJOR.MINOR` client schema the publisher says can still read
    /// this file. Optional — absence means the publisher makes no claim.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub min_client_schema: Option<String>,
    /// Highest `MAJOR.MINOR` client schema the publisher says can still read
    /// this file. Optional — absence means the publisher makes no claim.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_client_schema: Option<String>,
    /// Absolute HTTPS URL used verbatim by the downloader. The client never
    /// constructs asset URLs; it only ever follows what the manifest lists.
    pub download_url: String,
}

/// The published `manifest.json` blob.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct YamlManifest {
    /// Schema version of the *manifest itself* (independent from per-file
    /// schema versions). Checked against [`MAX_MANIFEST_VERSION`].
    pub manifest_version: u32,
    /// Release tag the manifest was published under
    /// (e.g. `"yaml-data-v2026.04.17"`).
    pub release_tag: String,
    /// ISO-8601 UTC timestamp of publication.
    pub published_at: String,
    /// Every shippable file the release attached. Must be non-empty.
    pub files: Vec<YamlManifestFile>,
    /// Optional signature descriptors; empty means the manifest was not
    /// signed (or the publisher omitted the array — same effect).
    #[serde(default)]
    pub signatures: Vec<SignatureDescriptor>,
}

/// One client-side entry per shippable file family:
///
/// - `accepted` is the [`SchemaCompat`] the current client binary is built
///   to parse (pulled from [`classic_config_core::client_schemas`] in
///   production callers; any [`SchemaCompat`] works in tests).
/// - `installed` optionally names the [`SchemaVersion`] currently on disk in
///   the per-user cache; callers pass `None` when there is no cache entry
///   yet, and [`check_yaml_update`] treats that as "update available" for
///   every compatible manifest entry.
/// - `installed_sha256` is the hex-encoded SHA-256 of the currently-installed
///   file bytes. First-party callers populate it from config inspection;
///   generic callers supply it directly when content freshness matters.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientSchemaEntry {
    /// Compatibility range the client advertises for this file family.
    pub accepted: SchemaCompat,
    /// Currently-installed schema version, if any.
    pub installed: Option<SchemaVersion>,
    /// Hex-encoded SHA-256 of the currently-installed file bytes, when the
    /// installed source could be resolved. When `Some`, the update
    /// classifier uses *content identity* (not schema_version) to decide
    /// freshness: a file whose manifest sha matches this value is not
    /// actionable regardless of schema bumps, and a file whose sha differs
    /// IS actionable even when schema_version is unchanged.
    pub installed_sha256: Option<String>,
}

/// Per-filename `(accepted, installed)` pairs the caller tells
/// [`check_yaml_update`] about. Keyed by the canonical file name
/// (e.g. `"CLASSIC Main.yaml"`) so the manifest's `files[].name` can be
/// matched directly.
#[derive(Debug, Clone, Default)]
pub struct ClientSchemaSet {
    entries: HashMap<String, ClientSchemaEntry>,
}

impl ClientSchemaSet {
    /// Create an empty set. Callers populate it with [`Self::insert`] before
    /// passing it to [`check_yaml_update`].
    pub fn new() -> Self {
        Self::default()
    }

    /// Record the accepted-compat range and optional installed version for a
    /// single file. Reinserting under the same name replaces the entry.
    ///
    /// `installed_sha256` is left `None` on this path. Use
    /// [`Self::insert_with_sha256`] when the caller holds an installed digest.
    pub fn insert(
        &mut self,
        name: impl Into<String>,
        accepted: SchemaCompat,
        installed: Option<SchemaVersion>,
    ) {
        self.entries.insert(
            name.into(),
            ClientSchemaEntry {
                accepted,
                installed,
                installed_sha256: None,
            },
        );
    }

    /// Like [`Self::insert`] but also records the installed file's SHA-256
    /// so [`classify_manifest`] can use content identity as the freshness
    /// signal. `installed_sha256` must be 64 lower-case hex chars when
    /// `Some`; malformed values are accepted but will never equal a
    /// manifest-declared sha (which is validated at the fetch boundary),
    /// so in practice they behave the same as `None` for freshness.
    pub fn insert_with_sha256(
        &mut self,
        name: impl Into<String>,
        accepted: SchemaCompat,
        installed: Option<SchemaVersion>,
        installed_sha256: Option<String>,
    ) {
        self.entries.insert(
            name.into(),
            ClientSchemaEntry {
                accepted,
                installed,
                installed_sha256,
            },
        );
    }

    /// Look up the entry for `name`, if any.
    pub fn get(&self, name: &str) -> Option<&ClientSchemaEntry> {
        self.entries.get(name)
    }

    /// Iterate `(name, entry)` pairs. Order is unspecified (HashMap-backed).
    pub fn iter(&self) -> impl Iterator<Item = (&str, &ClientSchemaEntry)> {
        self.entries.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// Total number of entries in the set.
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Whether the set is empty.
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

/// A manifest entry that the client rejected during check/apply, with a
/// human-readable reason. Used inside [`YamlUpdateStatus::UpdateAvailable`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RejectedManifestFile {
    /// The original manifest entry, preserved so GUI / CLI can surface it.
    pub file: YamlManifestFile,
    /// Short diagnostic (e.g. `"incompatible MAJOR: file=2 client_accepted=1"`).
    pub reason: String,
}

/// Outcome of [`check_yaml_update`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum YamlUpdateStatus {
    /// `Update Check: false` — nothing was fetched, no HTTP call was made.
    Disabled,
    /// At least one manifest file is compatible *and* represents a newer
    /// schema than the caller's installed copy. `compatible_files` is the
    /// install-eligible subset the GUI / CLI should offer to the user;
    /// `incompatible_files` documents what was skipped and why.
    UpdateAvailable {
        /// The full parsed manifest, including any files the caller had
        /// never heard of (no entry in [`ClientSchemaSet`]).
        manifest: YamlManifest,
        /// Entries whose schema is both compatible with the client and at a
        /// higher schema than what the client reports installed.
        compatible_files: Vec<YamlManifestFile>,
        /// Entries that were rejected — either because the client refuses
        /// the schema, or because the manifest is advertising something the
        /// client didn't ask about.
        incompatible_files: Vec<RejectedManifestFile>,
    },
    /// No compatible-and-newer file is present in the manifest. No install
    /// action is warranted. Diagnostics about skipped files (unknown to this
    /// client, schema-incompatible, or outside the published min/max
    /// client-schema bounds) are carried in `incompatible_files` so the
    /// caller can surface them without having to also inspect an
    /// `UpdateAvailable` variant with an empty compatible list.
    ///
    /// This variant covers three concrete cases:
    /// - Every known file is already at the installed schema (classic
    ///   "nothing to do" case, `incompatible_files` empty).
    /// - The manifest advertises files this client does not know about
    ///   (future data releases); every known file is current
    ///   (`incompatible_files` contains the unknown entries).
    /// - The manifest advertises files this client recognizes but cannot
    ///   accept (schema-incompatible or out-of-client-range); no compatible
    ///   file is newer (`incompatible_files` contains the rejected entries).
    UpToDate {
        /// The parsed manifest, for UX display.
        manifest: YamlManifest,
        /// Entries that were rejected during classification. Empty on the
        /// pure "nothing to do" case; non-empty when the manifest contained
        /// unknown/incompatible entries but nothing compatible was newer.
        incompatible_files: Vec<RejectedManifestFile>,
    },
    /// The manifest came back but something about it prevented an
    /// install-eligibility decision (e.g. unsupported `manifest_version`).
    /// `reason` is copy-paste-worthy.
    Unknown {
        /// Short human-readable reason, safe to display.
        reason: String,
    },
}

/// Per-file outcome inside [`YamlUpdateReport`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FileInstallOutcome {
    /// File was downloaded, hash-verified, atomically installed, and (if a
    /// prior copy existed) preserved as `<file>.prev`.
    Installed {
        /// Canonical file name.
        name: String,
        /// The schema version advertised by the manifest entry that was
        /// installed (useful for later `check_yaml_update` diffs).
        schema_version: String,
        /// Whether a `.prev` sibling was created.
        created_prev: bool,
    },
    /// File failed to install. The on-disk cache state for this file is
    /// unchanged.
    Failed {
        /// Canonical file name.
        name: String,
        /// Short, user-facing reason (e.g.
        /// `"sha256 mismatch: expected abc..., got def..."`).
        reason: String,
    },
}

/// Aggregate outcome of [`apply_yaml_update`]. Partial success is not an
/// error: the successful subset is installed, and the failed subset is
/// reported here for the GUI / CLI to surface.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct YamlUpdateReport {
    /// Files that were installed atomically.
    pub installed: Vec<FileInstallOutcome>,
    /// Files that were skipped or failed.
    pub failed: Vec<FileInstallOutcome>,
}

/// A user-reviewed update decision, produced from a prior
/// [`check_yaml_update`] call and consumed by
/// [`apply_yaml_update_with_decision`] to install exactly the approved set.
///
/// Review-and-apply is two logical steps separated by an unbounded amount
/// of time (the user reads a confirmation dialog, switches tabs, goes to
/// lunch). Between those steps the published manifest can rotate to a new
/// `release_tag` — and a naive apply that re-fetches the live manifest and
/// installs whatever it finds would silently install a release the user
/// never saw. This type closes that hole by carrying the approved identity
/// forward: apply refuses to run when the live manifest diverges.
///
/// `file_names` and `file_sha256` are parallel arrays describing the exact
/// file identities the user approved at review time. Apply re-checks both
/// dimensions against the freshly-fetched manifest before touching disk.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ApprovedUpdate {
    /// Release tag the user reviewed — used as an identity check against
    /// the freshly-fetched manifest's tag. A mismatch short-circuits with
    /// [`UpdateError::DecisionStale`].
    pub release_tag: String,
    /// Canonical file names (e.g. `"CLASSIC Main.yaml"`) the user
    /// approved.
    pub file_names: Vec<String>,
    /// Manifest-advertised SHA-256 digests for each approved file, aligned
    /// by index with `file_names`.
    pub file_sha256: Vec<String>,
}

impl ApprovedUpdate {
    /// Construct an approved decision directly from the `UpdateAvailable`
    /// variant the user just confirmed. Binding callers that only have
    /// flat DTO fields available should build the struct literally.
    pub fn from_status(status: &YamlUpdateStatus) -> Option<Self> {
        match status {
            YamlUpdateStatus::UpdateAvailable {
                manifest,
                compatible_files,
                ..
            } => Some(Self {
                release_tag: manifest.release_tag.clone(),
                file_names: compatible_files.iter().map(|f| f.name.clone()).collect(),
                file_sha256: compatible_files.iter().map(|f| f.sha256.clone()).collect(),
            }),
            _ => None,
        }
    }
}

fn approved_file_sha_map(approved: &ApprovedUpdate) -> Result<HashMap<&str, &str>> {
    if approved.file_names.len() != approved.file_sha256.len() {
        return Err(UpdateError::Generic(format!(
            "approved decision malformed: {} file names but {} file digests",
            approved.file_names.len(),
            approved.file_sha256.len()
        )));
    }

    let mut approved_sha_by_name = HashMap::with_capacity(approved.file_names.len());
    for (name, sha256) in approved.file_names.iter().zip(&approved.file_sha256) {
        if sha256.len() != 64 || !sha256.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Err(UpdateError::Generic(format!(
                "approved decision malformed: digest for `{name}` is not 64 hex chars"
            )));
        }
        if approved_sha_by_name
            .insert(name.as_str(), sha256.as_str())
            .is_some()
        {
            return Err(UpdateError::Generic(format!(
                "approved decision malformed: duplicate approved file `{name}`"
            )));
        }
    }

    Ok(approved_sha_by_name)
}

/// Outcome of [`rollback_yaml_update`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RollbackOutcome {
    /// `<cache>/<file_name>.prev` existed; the previous copy is now the
    /// canonical cache entry.
    RolledBack {
        /// The file that was rolled back.
        file_name: String,
    },
    /// No `.prev` existed for this file; nothing changed on disk.
    NoPreviousVersion {
        /// The file that was queried.
        file_name: String,
    },
}

// ---------------------------------------------------------------------------
// Manifest fetch
// ---------------------------------------------------------------------------

/// Fetch a published `manifest.json` from GitHub. Pages-first, with a narrow
/// anonymous API fallback.
///
/// Flow:
///
/// 1. If `pages_url` is set, GET it with the cached ETag (if any). On `200`,
///    validate the manifest and confirm its `release_tag` matches
///    `tag_prefix`, then return. On `304`, return the previously-cached body
///    after the same checks. On any other response (timeout, 4xx, 5xx,
///    invalid body, wrong channel), fall through to step 2.
/// 2. GET `{base_url}/repos/{owner}/{repo}/releases` through the existing
///    [`GithubClient`] (no `Authorization` header unless one was provided at
///    construction — see module docs). Filter the list to tags starting with
///    `tag_prefix`, pick the lexicographically greatest tag, and parse the
///    attached `manifest.json` asset.
///
/// The `cache_dir` argument points at the directory where ETag and cached
/// manifest body are persisted. In production this is
/// [`classic_path_core::yaml_cache_dir`]; tests inject a tempdir. Passing
/// `None` disables caching entirely — no `If-None-Match` header is sent,
/// no 304 cached-body read is attempted, and no files are written.
///
/// # Errors
///
/// - [`UpdateError::ManifestInvalid`] — JSON deserialized but failed post-parse
///   validation (missing `download_url`, non-HTTPS / non-github.com URL,
///   empty `files`, invalid `schema_version`, …).
/// - [`UpdateError::ManifestUnsupportedVersion`] — `manifest_version` is
///   higher than this client's [`MAX_MANIFEST_VERSION`].
/// - [`UpdateError::HttpError`] / [`UpdateError::JsonError`] — underlying
///   transport / parse failures.
/// - [`UpdateError::NotFound`] — both Pages and the API fallback reported no
///   usable manifest.
pub async fn fetch_yaml_manifest(
    client: &GithubClient,
    pages_url: &str,
    tag_prefix: &str,
    cache_dir: Option<&Path>,
) -> Result<YamlManifest> {
    let owner = client.owner().to_string();
    let repo = client.repo().to_string();
    let tag_prefix_owned = tag_prefix.to_string();
    match crate::manifest_fetch::try_pages(
        client,
        pages_url,
        cache_dir,
        parse_manifest,
        |manifest: &YamlManifest| {
            validate_manifest(manifest, &owner, &repo)?;
            validate_release_tag_prefix(&manifest.release_tag, &tag_prefix_owned)
        },
    )
    .await
    {
        Ok(manifest) => {
            return Ok(manifest);
        }
        Err(crate::manifest_fetch::PagesError::UnsupportedVersion(err)) => {
            // The manifest parsed but declares a version this client cannot
            // interpret. Falling back to the Releases API would almost
            // certainly hit the same asset and fail identically, so surface
            // the structural error directly instead of racing the API leg.
            return Err(err);
        }
        Err(crate::manifest_fetch::PagesError::Transport(err))
        | Err(crate::manifest_fetch::PagesError::Invalid(err)) => {
            log::warn!(
                "pages manifest fetch failed for `{pages_url}`: {err}; falling back to anonymous releases API"
            );
        }
    }

    let manifest = fetch_from_releases_api(client, tag_prefix).await?;
    validate_manifest(&manifest, client.owner(), client.repo())?;
    validate_release_tag_prefix(&manifest.release_tag, tag_prefix)?;
    Ok(manifest)
}

fn parse_manifest(bytes: &[u8]) -> Result<YamlManifest> {
    serde_json::from_slice::<YamlManifest>(bytes).map_err(UpdateError::JsonError)
}

fn validate_release_tag_prefix(release_tag: &str, tag_prefix: &str) -> Result<()> {
    if !release_tag.starts_with(tag_prefix) {
        return Err(UpdateError::ManifestInvalid {
            reason: format!(
                "release_tag `{release_tag}` does not match requested prefix `{tag_prefix}`"
            ),
        });
    }
    Ok(())
}

/// Parse a `yaml-data-v<YYYY>.<MM>.<DD>[.<N>]` tag into a comparable tuple
/// so that same-day republishes with multi-digit `N` sort correctly. Returns
/// `None` for anything that doesn't match the expected shape so the caller
/// can decide how to rank unparseable tags.
fn parse_yaml_data_tag(tag: &str, tag_prefix: &str) -> Option<(u32, u32, u32, u32)> {
    let remainder = tag.strip_prefix(tag_prefix)?;
    let mut parts = remainder.split('.');
    let year = parts.next()?.parse::<u32>().ok()?;
    let month = parts.next()?.parse::<u32>().ok()?;
    let day = parts.next()?.parse::<u32>().ok()?;
    let suffix = match parts.next() {
        Some(s) => s.parse::<u32>().ok()?,
        None => 0,
    };
    // Reject anything with extra dotted components so we never silently
    // ignore trailing garbage like `yaml-data-v2026.04.17.2.oops`.
    if parts.next().is_some() {
        return None;
    }
    Some((year, month, day, suffix))
}

/// Anonymous API fallback: list releases, filter by `tag_prefix`, pick the
/// highest-sorted tag, and fetch its `manifest.json` release asset.
///
/// Ordering parses the `YYYY.MM.DD[.N]` suffix of each candidate tag so
/// same-day republishes with multi-digit `N` sort correctly
/// (e.g. `.10 > .9`). A raw lexicographic sort would pick `.9` over `.10`
/// because `"1" < "2"` as strings. Unparseable tags are demoted so they
/// never beat a parseable one, but are still tie-broken lexicographically
/// among themselves for determinism.
async fn fetch_from_releases_api(client: &GithubClient, tag_prefix: &str) -> Result<YamlManifest> {
    // Exclude drafts AND prereleases. Prerelease exclusion is load-bearing:
    // the publish workflow (`.github/workflows/publish-yaml-data.yml`)
    // promotes a freshly-published release to live as a prerelease and
    // only clears that flag after anonymous asset reachability is proven.
    // Filtering prereleases here is what makes that gating effective —
    // without it, an API-fallback client could race the workflow's
    // verification probe and hit a release whose asset URLs are still
    // propagating.
    let releases = client.get_all_releases(false, false).await?;

    let mut candidates: Vec<_> = releases
        .into_iter()
        .filter(|r| r.tag_name.starts_with(tag_prefix))
        .collect();

    if candidates.is_empty() {
        return Err(UpdateError::NotFound(format!(
            "no releases matching prefix `{tag_prefix}` found via API fallback",
        )));
    }

    candidates.sort_by(|a, b| {
        let a_key = parse_yaml_data_tag(&a.tag_name, tag_prefix);
        let b_key = parse_yaml_data_tag(&b.tag_name, tag_prefix);
        match (a_key, b_key) {
            // Descending numeric order.
            (Some(ak), Some(bk)) => bk.cmp(&ak),
            // Parseable beats unparseable.
            (Some(_), None) => std::cmp::Ordering::Less,
            (None, Some(_)) => std::cmp::Ordering::Greater,
            // Deterministic tie-break for two unparseable tags.
            (None, None) => b.tag_name.cmp(&a.tag_name),
        }
    });
    let release = candidates.remove(0);

    let manifest_asset = release
        .assets
        .iter()
        .find(|a| a.name == "manifest.json")
        .ok_or_else(|| {
            UpdateError::NotFound(format!(
                "release `{}` has no `manifest.json` asset",
                release.tag_name
            ))
        })?;

    let mut req = client
        .http_client()
        .get(&manifest_asset.browser_download_url);
    if let Some(token) = client.token() {
        req = req.header("Authorization", format!("Bearer {token}"));
    }

    let response = req.send().await.map_err(UpdateError::HttpError)?;
    if !response.status().is_success() {
        return Err(UpdateError::GithubError(format!(
            "manifest asset GET returned {}",
            response.status()
        )));
    }
    let bytes = response.bytes().await.map_err(UpdateError::HttpError)?;
    parse_manifest(&bytes)
}

/// Reject any manifest or API-level cache file name that isn't a plain
/// basename suitable for direct `<yaml-cache>/<name>` joining.
///
/// A valid cache file name MUST be:
/// - non-empty and not equal to `.` or `..`,
/// - free of path separators (`/` or `\`), `:` stream separators, and
///   embedded NUL bytes,
/// - not end with a space or `.`, because Win32 trims those suffixes during
///   path resolution and aliases them to the unsuffixed on-disk file,
/// - relative, not absolute (rejects `C:\x`, `\\server\share\x`, `/x`),
/// - a single path component (rejects Windows drive-relative forms like
///   `C:x`, which are not absolute but still escape the cache dir),
/// - not a reserved Windows DOS device basename (rejects `NUL`, `CON`,
///   `COM1`, `LPT1`, etc. with or without an extension, case-insensitively)
///   so install/rollback joins cannot be redirected at the kernel level to
///   a device path regardless of which OS the client runs on.
///
/// Windows also treats `name:stream` as an NTFS alternate data stream
/// reference rather than a plain file name, so `:` is rejected even though it
/// is not a path separator.
///
/// This is the single choke point that stops a compromised manifest or a
/// stray binding caller from turning a cache-dir join into a filesystem
/// escape. It is called at manifest validation (so bad data is refused at
/// the boundary) AND again inside `install_one` / `rollback_yaml_update`
/// so direct binding callers of those APIs cannot skip the check.
fn is_valid_cache_file_name(name: &str) -> bool {
    if name.is_empty() || name == "." || name == ".." {
        return false;
    }
    if name
        .bytes()
        .any(|b| b == b'/' || b == b'\\' || b == b':' || b == 0)
    {
        return false;
    }
    if name.ends_with(' ') || name.ends_with('.') {
        return false;
    }
    let path = Path::new(name);
    if path.is_absolute() || path.has_root() {
        return false;
    }
    // Reject multi-component and prefixed paths (e.g. `foo/bar`, `C:foo`).
    // A plain basename produces exactly one `Component::Normal`.
    let mut comps = path.components();
    let first = match comps.next() {
        Some(c) => c,
        None => return false,
    };
    if comps.next().is_some() {
        return false;
    }
    if !matches!(first, std::path::Component::Normal(_)) {
        return false;
    }
    // Reject Windows reserved DOS device basenames. Windows resolves these
    // at the kernel level regardless of the filesystem layout, so a join
    // like `<cache_dir>/NUL` routes at the device rather than into the
    // cache directory. Enforced on every host (not just Windows) because
    // the client may be running on Windows even when validation happens
    // in a non-Windows test or when a validated manifest is shared across
    // platforms.
    if is_reserved_windows_device_basename(name) {
        return false;
    }
    true
}

/// Case-insensitive check for the classical Windows reserved device
/// basenames: `CON`, `PRN`, `AUX`, `NUL`, `COM1`..`COM9`, `LPT1`..`LPT9`.
///
/// Windows treats the stem (the part before the first `.`) as the device
/// name, so `NUL`, `nul.yaml`, and `Con.txt` all refer to the same device.
/// Trailing whitespace/dots on Windows filenames are also stripped before
/// resolution; we reject those too by trimming before comparing.
fn is_reserved_windows_device_basename(name: &str) -> bool {
    // Strip anything from the first `.` onward — Windows device name
    // resolution looks only at the stem.
    let stem = match name.find('.') {
        Some(idx) => &name[..idx],
        None => name,
    };
    // Windows also strips trailing spaces and dots from filenames before
    // resolving. We already handled dots; trim trailing spaces.
    let stem = stem.trim_end_matches(' ');
    if stem.is_empty() {
        return false;
    }
    let upper = stem.to_ascii_uppercase();
    matches!(upper.as_str(), "CON" | "PRN" | "AUX" | "NUL")
        || matches!(
            upper.as_str(),
            "COM1" | "COM2" | "COM3" | "COM4" | "COM5" | "COM6" | "COM7" | "COM8" | "COM9"
        )
        || matches!(
            upper.as_str(),
            "LPT1" | "LPT2" | "LPT3" | "LPT4" | "LPT5" | "LPT6" | "LPT7" | "LPT8" | "LPT9"
        )
}

fn validate_cache_file_name(name: &str) -> Result<()> {
    if !is_valid_cache_file_name(name) {
        return Err(UpdateError::ManifestInvalid {
            reason: format!("file name {name:?} is not a valid plain cache-dir basename"),
        });
    }
    Ok(())
}

/// Return whether a cache basename aliases user-owned Local Ignore YAML Data.
///
/// Comparison is case-insensitive because the supported Windows filesystem contract is too.
fn is_local_ignore_yaml_file_name(name: &str) -> bool {
    name.eq_ignore_ascii_case(LOCAL_IGNORE_YAML_FILE_NAME)
}

/// Normalize a validated cache basename to the same identity Windows path
/// resolution uses for collision checks.
///
/// Windows file lookup is case-insensitive and strips trailing dots/spaces.
/// Validation already rejects names with those suffixes, but the duplicate
/// guard still trims them here so the normalization stays aligned with the
/// platform rule if the validator changes later.
fn windows_normalized_cache_file_key(name: &str) -> String {
    name.trim_end_matches([' ', '.']).to_ascii_lowercase()
}

/// Defense-in-depth containment check: after joining a validated basename
/// onto `cache_dir`, confirm the resolved path still begins with
/// `cache_dir` component-wise. Uses lexical comparison because the target
/// may not yet exist (tmp-download case), so `canonicalize` would fail.
fn ensure_path_in_cache(cache_dir: &Path, target: &Path) -> Result<()> {
    if !target.starts_with(cache_dir) {
        return Err(UpdateError::ManifestInvalid {
            reason: format!(
                "resolved path {} escapes yaml-cache directory {}",
                target.display(),
                cache_dir.display(),
            ),
        });
    }
    Ok(())
}

/// Validate a parsed manifest against the client's invariants. Called by
/// both legs of the fetch path and exposed for integration tests.
///
/// `owner` and `repo` are the configured GitHub repository this client is
/// willing to install from. Every `files[].download_url` must resolve to
/// the canonical release-asset template for this owner/repo and the
/// manifest's own `release_tag`; see [`is_canonical_asset_url`] for the
/// exact shape. A URL outside that template is rejected as
/// [`UpdateError::ManifestInvalid`].
pub fn validate_manifest(manifest: &YamlManifest, owner: &str, repo: &str) -> Result<()> {
    if manifest.manifest_version == 0 {
        return Err(UpdateError::ManifestInvalid {
            reason: "manifest_version must be >= 1".into(),
        });
    }
    if manifest.manifest_version > MAX_MANIFEST_VERSION {
        return Err(UpdateError::ManifestUnsupportedVersion {
            found: manifest.manifest_version,
            max_supported: MAX_MANIFEST_VERSION,
        });
    }
    if manifest.release_tag.is_empty() {
        return Err(UpdateError::ManifestInvalid {
            reason: "release_tag must be non-empty".into(),
        });
    }
    if manifest.files.is_empty() {
        return Err(UpdateError::ManifestInvalid {
            reason: "files must be non-empty".into(),
        });
    }
    // Reject duplicate `files[].name` entries by Windows path identity. A
    // second install of the same target path would rotate `.prev` away from
    // the pre-update copy, making rollback depend on manifest order instead
    // of the on-disk state before the apply call. Refuse at the validation
    // boundary so `apply_yaml_update` never iterates a list that can corrupt
    // its own rollback invariant.
    let mut seen_names: std::collections::HashSet<String> = std::collections::HashSet::new();
    for entry in &manifest.files {
        validate_cache_file_name(&entry.name)?;
        let normalized_name = windows_normalized_cache_file_key(&entry.name);
        if !seen_names.insert(normalized_name) {
            return Err(UpdateError::ManifestInvalid {
                reason: format!(
                    "files[] contains duplicate entry for `{}`; each file name must appear at most once",
                    entry.name
                ),
            });
        }
        if entry.sha256.len() != 64 || !entry.sha256.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Err(UpdateError::ManifestInvalid {
                reason: format!("files[].sha256 for `{}` is not 64 hex chars", entry.name),
            });
        }
        if entry.download_url.is_empty() {
            return Err(UpdateError::ManifestInvalid {
                reason: format!("files[].download_url for `{}` is missing", entry.name),
            });
        }
        if !is_canonical_asset_url(
            &entry.download_url,
            owner,
            repo,
            &manifest.release_tag,
            &entry.name,
        ) {
            return Err(UpdateError::ManifestInvalid {
                reason: format!(
                    "files[].download_url for `{}` does not match the canonical \
                     release-asset template https://github.com/{owner}/{repo}/releases/download/{}/<asset>",
                    entry.name, manifest.release_tag,
                ),
            });
        }
        // schema_version parse is enforced separately by the caller, but we
        // do a cheap shape check here so an obviously malformed value is
        // rejected before we try to download anything.
        if entry.schema_version.parse::<SchemaVersion>().is_err() {
            return Err(UpdateError::ManifestInvalid {
                reason: format!(
                    "files[].schema_version for `{}` ({:?}) is not MAJOR.MINOR",
                    entry.name, entry.schema_version
                ),
            });
        }
    }
    Ok(())
}

/// Accept only URLs that match the canonical release-asset template
/// `https://github.com/<owner>/<repo>/releases/download/<release_tag>/<url-encoded asset_name>`.
///
/// `asset_name` is compared against the last path segment AFTER
/// percent-decoding the segment, so `CLASSIC%20Main.yaml` in the URL
/// correctly matches `CLASSIC Main.yaml` in the manifest entry.
///
/// # Rationale (reversed from prior review)
///
/// An earlier "intentional scope" comment at this site argued for a
/// host-only allowlist with three reasons: the manifest's per-file
/// `sha256`, the Pages-first fetch origin, and concern about
/// over-constraining legitimate release-asset URLs. A second adversarial
/// review pushed back that the sha256 only binds bytes to what the
/// manifest itself declared — a mispublished or compromised manifest that
/// lists the hash of arbitrary GitHub-hosted content still validates.
/// Pinning the full path template closes that hole without affecting
/// legitimate flows: the server-side 302 redirect to object storage
/// happens on the HTTP layer AFTER this check passes, so well-formed
/// manifest URLs still resolve the same way. Phase E signature
/// verification remains deferred, so the cheap template check is the
/// right place to harden the trust boundary today.
fn is_canonical_asset_url(
    url: &str,
    owner: &str,
    repo: &str,
    release_tag: &str,
    asset_name: &str,
) -> bool {
    let parsed = match url::Url::parse(url) {
        Ok(u) => u,
        Err(_) => return false,
    };
    if parsed.scheme() != "https" {
        return false;
    }
    if parsed.host_str() != Some("github.com") {
        return false;
    }
    // github.com release-asset URLs carry no query/fragment — reject them
    // to avoid a `?foo=bar` hiding a redirect parameter a future GitHub
    // change might honor.
    if parsed.query().is_some() || parsed.fragment().is_some() {
        return false;
    }
    let segments: Vec<&str> = match parsed.path_segments() {
        Some(s) => s.collect(),
        None => return false,
    };
    // Expect exactly: <owner>/<repo>/releases/download/<release_tag>/<asset>.
    if segments.len() != 6 {
        return false;
    }
    if segments[0] != owner
        || segments[1] != repo
        || segments[2] != "releases"
        || segments[3] != "download"
        || segments[4] != release_tag
    {
        return false;
    }
    // URL-decode the final segment and compare to the manifest-declared
    // asset name. A mismatch here means the URL points at a different
    // asset than the manifest claims.
    match percent_decode_ascii_or_utf8(segments[5]) {
        Some(decoded) => decoded == asset_name,
        None => false,
    }
}

/// Minimal RFC 3986 percent-decoder. Returns `None` on malformed escapes
/// or invalid UTF-8. Scoped local to avoid pulling the `percent-encoding`
/// crate into the dep tree for a single call site.
fn percent_decode_ascii_or_utf8(s: &str) -> Option<String> {
    let bytes = s.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' {
            if i + 2 >= bytes.len() {
                return None;
            }
            let hi = (bytes[i + 1] as char).to_digit(16)?;
            let lo = (bytes[i + 2] as char).to_digit(16)?;
            out.push(((hi << 4) | lo) as u8);
            i += 3;
        } else {
            out.push(bytes[i]);
            i += 1;
        }
    }
    String::from_utf8(out).ok()
}

// ---------------------------------------------------------------------------
// Asset download
// ---------------------------------------------------------------------------

/// Stream the content at `url` into `dest_tmp` verbatim.
///
/// `url` must match the canonical release-asset template for the
/// configured `client.owner()` / `client.repo()` and the given
/// `release_tag` / `asset_name` — see [`is_canonical_asset_url`] for the
/// exact shape. The check runs here as well as in [`validate_manifest`]
/// so a direct binding caller that hand-builds a [`YamlManifestFile`] and
/// hits [`apply_yaml_update`] still cannot download something off-template.
///
/// The body is written with `tokio::io::AsyncWriteExt::write_all` as it
/// arrives — no buffering beyond the chunk size. `dest_tmp` MUST be inside
/// the directory of the eventual install target so the subsequent
/// [`install_atomic`] rename stays same-directory-atomic.
pub async fn download_release_asset(
    client: &GithubClient,
    url: &str,
    dest_tmp: &Path,
    release_tag: &str,
    asset_name: &str,
) -> Result<()> {
    if !is_canonical_asset_url(url, client.owner(), client.repo(), release_tag, asset_name) {
        return Err(UpdateError::ManifestInvalid {
            reason: format!(
                "asset URL `{url}` does not match canonical release-asset template \
                 https://github.com/{}/{}/releases/download/{release_tag}/<asset>",
                client.owner(),
                client.repo(),
            ),
        });
    }

    let mut req = client.http_client().get(url);
    if let Some(token) = client.token() {
        req = req.header("Authorization", format!("Bearer {token}"));
    }
    let response = req.send().await.map_err(UpdateError::HttpError)?;

    if !response.status().is_success() {
        return Err(UpdateError::GithubError(format!(
            "asset GET `{url}` returned {}",
            response.status()
        )));
    }

    let bytes = response.bytes().await.map_err(UpdateError::HttpError)?;

    if let Some(parent) = dest_tmp.parent() {
        tokio::fs::create_dir_all(parent)
            .await
            .map_err(|e| UpdateError::Generic(format!("mkdir {}: {e}", parent.display())))?;
    }

    // Shippable YAML files are small (< few-hundred KB), so a single
    // write_all is fine and keeps the dep surface smaller than pulling in
    // reqwest's `stream` feature just for this path.
    let mut file = tokio::fs::File::create(dest_tmp)
        .await
        .map_err(|e| UpdateError::Generic(format!("create {}: {e}", dest_tmp.display())))?;
    file.write_all(&bytes)
        .await
        .map_err(|e| UpdateError::Generic(format!("write {}: {e}", dest_tmp.display())))?;
    file.flush()
        .await
        .map_err(|e| UpdateError::Generic(format!("flush {}: {e}", dest_tmp.display())))?;

    Ok(())
}

// ---------------------------------------------------------------------------
// Orchestrator
// ---------------------------------------------------------------------------

/// User-visible configuration for the update subsystem.
///
/// Carries the `Update Check` toggle from `CLASSIC Settings.yaml` and the
/// optional installation layout used by first-party YAML Data checks. Generic
/// manifest checks classify only the installed metadata supplied in their
/// [`ClientSchemaSet`] and do not inspect either layout field.
///
/// No longer `Copy`: `PathBuf` does not implement `Copy`, and the single
/// current `check_yaml_update` call inside
/// [`apply_yaml_update_with_decision`] moves the value once. Callers that
/// need to reuse a config across multiple calls should `clone()`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateCheckConfig {
    /// When `false`, [`check_yaml_update`] short-circuits with
    /// [`YamlUpdateStatus::Disabled`] without any HTTP call.
    pub enabled: bool,
    /// First-party layout hint naming either the CLASSIC installation root or
    /// its `CLASSIC Data/databases` directory.
    ///
    /// The established binding-facing field is retained so every supported
    /// adapter can supply non-native host layout without another Rust-only
    /// configuration surface. Generic checks ignore this field.
    pub bundled_yaml_dir: Option<PathBuf>,
}

impl UpdateCheckConfig {
    /// Shortcut for an enabled config with no explicit installation layout.
    pub const fn enabled() -> Self {
        Self {
            enabled: true,
            bundled_yaml_dir: None,
        }
    }

    /// Shortcut for a disabled config with no installation layout.
    pub const fn disabled() -> Self {
        Self {
            enabled: false,
            bundled_yaml_dir: None,
        }
    }

    /// Builder-style setter for the explicit first-party layout hint. Pattern:
    ///
    /// ```rust,ignore
    /// UpdateCheckConfig::enabled()
    ///     .with_bundled_yaml_dir(package_root.join("CLASSIC Data/databases"))
    /// ```
    pub fn with_bundled_yaml_dir(mut self, dir: PathBuf) -> Self {
        self.bundled_yaml_dir = Some(dir);
        self
    }
}

/// Build the canonical GitHub Pages URL for the first-party YAML Data manifest.
///
/// The owner and repository are read from `client`, which keeps forks and tests
/// on the same channel shape without hard-coding the official repository in
/// core update logic.
fn build_yaml_data_pages_url(client: &GithubClient) -> String {
    format!(
        "https://{owner}.github.io/{repo}/{segment}",
        owner = client.owner(),
        repo = client.repo(),
        segment = YAML_DATA_PAGES_PATH_SEGMENT,
    )
}

/// Returns the current first-party YAML Data rollback target names.
///
/// This list is derived from `classic-config-core` shippable schema metadata,
/// the same Rust-side source used to build update-check schema entries.
fn yaml_data_rollback_targets() -> Vec<String> {
    client_schemas::shippable_schema_entries()
        .into_iter()
        .map(|entry| entry.file.file_name)
        .collect()
}

/// Builds the schema set for the first-party YAML Data Update Channel.
///
/// Installed versions and exact-byte digests come exclusively from the
/// config-owned inspection result; the generic updater does not inspect disk.
fn yaml_data_client_schema_set(inspection: &InstalledYamlDataInspection) -> ClientSchemaSet {
    let mut set = ClientSchemaSet::new();
    set.insert_with_sha256(
        "CLASSIC Main.yaml",
        client_schemas::MAIN_YAML,
        Some(inspection.main().schema_version()),
        Some(inspection.main().identity().sha256_hex()),
    );
    set.insert_with_sha256(
        "CLASSIC Fallout4.yaml",
        client_schemas::GAME_FALLOUT4_YAML,
        Some(inspection.game_file().schema_version()),
        Some(inspection.game_file().identity().sha256_hex()),
    );
    set
}

/// Check the first-party YAML Data Update Channel.
///
/// This is the product-level helper native callers should use. It owns the
/// Pages URL shape and `yaml-data-v*` tag namespace, obtains installed schema
/// and content identity through config-owned inspection, then delegates the
/// network/classification work to the generic lower-level update interface.
pub async fn check_yaml_data_update(
    client: &GithubClient,
    config: UpdateCheckConfig,
) -> Result<YamlUpdateStatus> {
    let pages_url = build_yaml_data_pages_url(client);
    check_yaml_data_update_with(client, &pages_url, config).await
}

/// Testable first-party YAML Data check with an explicit Pages URL.
///
/// Production callers should prefer [`check_yaml_data_update`]. This variant
/// exists for integration tests and fork tooling that need to exercise the
/// first-party schema/tag policy against a mock or alternate Pages endpoint
/// while still keeping the tag prefix and shippable schema set in Rust.
pub async fn check_yaml_data_update_with(
    client: &GithubClient,
    pages_url: &str,
    config: UpdateCheckConfig,
) -> Result<YamlUpdateStatus> {
    check_yaml_data_update_with_env(client, pages_url, config, process_env_lookup).await
}

/// Testable first-party check with one injected cache environment.
///
/// The same environment resolves both manifest caching and config-owned
/// Installed YAML Data inspection, keeping tests and non-native hosts from
/// observing different cache locations within one check.
pub async fn check_yaml_data_update_with_env<F>(
    client: &GithubClient,
    pages_url: &str,
    config: UpdateCheckConfig,
    env: F,
) -> Result<YamlUpdateStatus>
where
    F: Fn(&str) -> Option<String>,
{
    if !config.enabled {
        return Ok(YamlUpdateStatus::Disabled);
    }
    let installation_root = resolve_installation_root(&config).ok_or_else(|| {
        UpdateError::Generic(
            "could not resolve the CLASSIC installation root for YAML Data inspection".to_string(),
        )
    })?;
    let inspection = inspect_installed_yaml_data_with_env(
        InstalledYamlDataInspectionRequest {
            installation_root,
            game: GameId::Fallout4,
        },
        &env,
    )
    .map_err(|source| {
        UpdateError::Generic(format!("Installed YAML Data inspection failed: {source}"))
    })?;
    let current = yaml_data_client_schema_set(&inspection);
    let cache_dir = prepare_yaml_cache_dir(ensure_yaml_cache_dir_with_env(&env));
    check_yaml_update_with_cache_dir(
        client,
        pages_url,
        YAML_DATA_TAG_PREFIX,
        &current,
        cache_dir.as_deref(),
    )
    .await
}

/// Apply an approved first-party YAML Data update decision.
///
/// The approved decision must come from a prior first-party check result the
/// user reviewed. This helper owns the channel URL, tag prefix, and schema set,
/// and keeps the existing stale-decision and digest-drift protections from
/// [`apply_yaml_update_with_decision`].
pub async fn apply_yaml_data_update_with_decision(
    client: &GithubClient,
    config: UpdateCheckConfig,
    approved: &ApprovedUpdate,
) -> Result<YamlUpdateReport> {
    let pages_url = build_yaml_data_pages_url(client);
    apply_yaml_data_update_with_decision_with(client, &pages_url, config, approved).await
}

/// Testable first-party YAML Data apply helper with an explicit Pages URL.
///
/// Like [`check_yaml_data_update_with`], this keeps first-party policy in Rust
/// while allowing tests to point the Pages leg at a mock server.
pub async fn apply_yaml_data_update_with_decision_with(
    client: &GithubClient,
    pages_url: &str,
    config: UpdateCheckConfig,
    approved: &ApprovedUpdate,
) -> Result<YamlUpdateReport> {
    if !config.enabled {
        return Err(UpdateError::UpdateCheckDisabled);
    }
    let installation_root = resolve_installation_root(&config).ok_or_else(|| {
        UpdateError::Generic(
            "could not resolve the CLASSIC installation root for YAML Data inspection".to_string(),
        )
    })?;
    let inspection = inspect_installed_yaml_data(InstalledYamlDataInspectionRequest {
        installation_root,
        game: GameId::Fallout4,
    })
    .map_err(|source| {
        UpdateError::Generic(format!("Installed YAML Data inspection failed: {source}"))
    })?;
    let current = yaml_data_client_schema_set(&inspection);
    apply_yaml_update_with_decision(
        client,
        pages_url,
        YAML_DATA_TAG_PREFIX,
        &current,
        config,
        approved,
    )
    .await
}

/// Roll back every current first-party shippable YAML Data file.
///
/// Native callers use this instead of naming individual files. Rust expands
/// the current first-party shippable target list and runs the lower-level
/// rollback for each file. The returned vector preserves target order and
/// carries the requested file name beside each outcome so frontends can still
/// identify failed targets without duplicating the first-party file list.
pub async fn rollback_yaml_data_update() -> Vec<(String, Result<RollbackOutcome>)> {
    yaml_data_rollback_targets()
        .into_iter()
        .map(|file_name| {
            let outcome = rollback_yaml_update(&file_name);
            (file_name, outcome)
        })
        .collect()
}

/// Drive the manifest fetch + classify step. See [`YamlUpdateStatus`] for
/// the outcomes.
///
/// `current` tells the orchestrator which files the client cares about and
/// what it already has installed. Entries in the manifest that have no
/// corresponding entry in `current` are reported under
/// `incompatible_files` with reason `"unknown file"` so the caller can
/// surface the diagnostic (spec scenario "no compatible files in manifest").
pub async fn check_yaml_update(
    client: &GithubClient,
    pages_url: &str,
    tag_prefix: &str,
    current: &ClientSchemaSet,
    config: UpdateCheckConfig,
) -> Result<YamlUpdateStatus> {
    if !config.enabled {
        return Ok(YamlUpdateStatus::Disabled);
    }
    let cache_dir = prepare_yaml_cache_dir(ensure_yaml_cache_dir());
    check_yaml_update_with_cache_dir(client, pages_url, tag_prefix, current, cache_dir.as_deref())
        .await
}

/// Fetch and classify a generic manifest using an already-resolved best-effort cache directory.
///
/// Installed schema and digest facts come only from `current`; this helper never inspects data files.
async fn check_yaml_update_with_cache_dir(
    client: &GithubClient,
    pages_url: &str,
    tag_prefix: &str,
    current: &ClientSchemaSet,
    cache_dir: Option<&Path>,
) -> Result<YamlUpdateStatus> {
    let manifest = match fetch_yaml_manifest(client, pages_url, tag_prefix, cache_dir).await {
        Ok(m) => m,
        Err(UpdateError::ManifestUnsupportedVersion {
            found,
            max_supported,
        }) => {
            return Ok(YamlUpdateStatus::Unknown {
                reason: format!(
                    "manifest_version {found} not supported (max supported: {max_supported})",
                ),
            });
        }
        Err(e) => return Err(e),
    };
    classify_manifest(manifest, current)
}

/// Convert cache preparation into the updater's best-effort manifest-cache policy.
fn prepare_yaml_cache_dir(
    result: std::result::Result<PathBuf, classic_path_core::PathError>,
) -> Option<PathBuf> {
    match result {
        Ok(directory) => Some(directory),
        Err(source) => {
            log::warn!(
                "could not prepare YAML cache directory: {source}; manifest fetch will proceed without ETag caching"
            );
            None
        }
    }
}

/// Resolve one CLASSIC installation root for config-owned first-party inspection.
fn resolve_installation_root(config: &UpdateCheckConfig) -> Option<PathBuf> {
    config
        .bundled_yaml_dir
        .as_deref()
        .map(installation_root_from_layout_hint)
        .or_else(|| {
            std::env::current_exe()
                .ok()
                .and_then(|executable| executable.parent().map(Path::to_path_buf))
        })
}

/// Translate a binding-compatible layout hint into one installation root.
fn installation_root_from_layout_hint(directory: &Path) -> PathBuf {
    let is_databases = directory.file_name().and_then(|name| name.to_str()) == Some("databases");
    let classic_data = directory
        .parent()
        .filter(|parent| parent.file_name().and_then(|name| name.to_str()) == Some("CLASSIC Data"));
    if is_databases && let Some(root) = classic_data.and_then(Path::parent) {
        return root.to_path_buf();
    }
    directory.to_path_buf()
}

/// Read one process environment value while treating empty strings as unset.
fn process_env_lookup(name: &str) -> Option<String> {
    match std::env::var(name) {
        Ok(value) if !value.is_empty() => Some(value),
        _ => None,
    }
}

/// Enforce the manifest's published `min_client_schema` /
/// `max_client_schema` bounds against the client's accepted schema range.
///
/// The client's accepted set is **not** a single point. A `SchemaCompat`
/// of `(accepted_major, minimum_minor)` means the client reads every
/// `(accepted_major, m)` with `m >= minimum_minor` — one major, an
/// open-ended minor range. The file declares the closed interval of
/// client schemas it supports; per `CLASSIC Data/databases/
/// client-schema-ranges.yaml`, a client accepts a file iff the client's
/// accepted range **overlaps** `[min_client_schema, max_client_schema]`.
///
/// Collapsing the client to `(accepted_major, minimum_minor)` and doing
/// a point-in-interval test is strictly stricter than overlap: a client
/// that reads `1.0..` would be rejected against a file range `[1.5,
/// 1.999]` even though `1.5..1.999` is entirely inside the client's
/// accepted set. The three rejection rules below are the actual
/// non-overlap conditions for a client range `{M.m : M == accepted_major
/// && m >= minimum_minor}` vs. a file range `[min, max]`:
///
/// 1. `accepted_major < min.major` — client's sole major is below the
///    file's lowest supported major.
/// 2. `accepted_major > max.major` — client's sole major is above the
///    file's highest supported major.
/// 3. `accepted_major == max.major && minimum_minor > max.minor` —
///    client's floor within the shared top major is above the file's
///    ceiling. (The symmetric "`accepted_major == min.major &&
///    minimum_minor > something`" check is *not* a non-overlap case,
///    because the client's minor range extends upward to infinity —
///    any file minor at or above `max(minimum_minor, min.minor)`
///    overlaps.)
///
/// A manifest that publishes both bounds must also publish a non-inverted
/// interval (`min_client_schema <= max_client_schema`). Contradictory bounds
/// are rejected as malformed manifest data even if a specific client schema
/// point would otherwise appear to sit inside one side of the interval.
///
/// Returns `Ok(())` when bounds are absent or overlap exists;
/// `Err(reason)` with a short diagnostic otherwise.
fn check_client_schema_bounds(
    entry: &YamlManifestFile,
    client_entry: &ClientSchemaEntry,
) -> std::result::Result<(), String> {
    let accepted_major = client_entry.accepted.accepted_major;
    let minimum_minor = client_entry.accepted.minimum_minor;

    let min = match &entry.min_client_schema {
        Some(s) => Some(
            s.parse::<SchemaVersion>()
                .map_err(|e| format!("min_client_schema {s:?} is malformed: {e}"))?,
        ),
        None => None,
    };
    let max = match &entry.max_client_schema {
        Some(s) => Some(
            s.parse::<SchemaVersion>()
                .map_err(|e| format!("max_client_schema {s:?} is malformed: {e}"))?,
        ),
        None => None,
    };

    if let (Some(min), Some(max)) = (&min, &max)
        && min > max
    {
        return Err(format!(
            "file client schema bounds inverted: min_client_schema {min} exceeds max_client_schema {max}"
        ));
    }

    if let Some(ref min) = min
        && accepted_major < min.major
    {
        return Err(format!(
            "client major {accepted_major} below file min_client_schema {min}"
        ));
    }
    if let Some(ref max) = max {
        if accepted_major > max.major {
            return Err(format!(
                "client major {accepted_major} above file max_client_schema {max}"
            ));
        }
        if accepted_major == max.major && minimum_minor > max.minor {
            return Err(format!(
                "client floor {accepted_major}.{minimum_minor} above file max_client_schema {max}"
            ));
        }
    }
    Ok(())
}

/// Split `manifest.files` into compatible-and-newer vs everything else.
/// Public for integration tests that want to reuse classification without
/// the HTTP step.
///
/// # Freshness vs. compatibility
///
/// The terminal rule is: a file is install-eligible when it is both
/// **compatible** with the client AND **fresher** than what is installed.
/// Those two conditions answer different questions and use different
/// signals:
///
/// - Compatibility: does this client's binary know how to parse these
///   bytes? Answered by [`schema_compat_check`] against the client's
///   `accepted` [`SchemaCompat`] and the manifest-published
///   `min_client_schema` / `max_client_schema` bounds.
/// - Freshness: are the manifest bytes the same as what is already
///   installed? Answered by comparing the manifest's per-file `sha256` to
///   [`ClientSchemaEntry::installed_sha256`].
///
/// Using content identity for freshness is what prevents the
/// "data-only release ships but schema_version is unchanged" failure
/// mode: a release that adds crash suspects, mod conflicts, or FormID
/// fixes without changing the structural schema still produces a
/// different sha256, so it classifies as `UpdateAvailable` exactly when
/// there is actually something new to install.
///
/// Historical fallback: when `installed_sha256` is `None` (the caller
/// never resolved an installed copy), we still fall back to the older
/// `schema_version > installed` comparison. That path is only reachable
/// for generic callers that supply an installed schema without a digest.
/// First-party checks always use config inspection's exact-byte digest.
///
/// # Status selection
///
/// If any file is both compatible and fresher, return
/// [`YamlUpdateStatus::UpdateAvailable`]; otherwise return
/// [`YamlUpdateStatus::UpToDate`]. Both variants carry `incompatible_files`
/// so diagnostics about unknown/incompatible entries survive regardless of
/// outcome.
///
/// A common past bug was to classify "manifest adds a future file this
/// client does not know about, every known file is current" as
/// `UpdateAvailable { compatible_files: [] }`, forcing the GUI / CLI to
/// loop on a non-actionable "update available" status forever. The current
/// rule — actionability is `!compatible_files.is_empty()`, nothing else —
/// closes that hole: a feed that only grows with forward-compatible new
/// entries still reports `UpToDate` on older clients.
pub fn classify_manifest(
    manifest: YamlManifest,
    current: &ClientSchemaSet,
) -> Result<YamlUpdateStatus> {
    let mut compatible_files: Vec<YamlManifestFile> = Vec::new();
    let mut incompatible_files: Vec<RejectedManifestFile> = Vec::new();

    for entry in &manifest.files {
        if is_local_ignore_yaml_file_name(&entry.name) {
            incompatible_files.push(RejectedManifestFile {
                file: entry.clone(),
                reason: "Local Ignore YAML Data is user-owned and not update-eligible".into(),
            });
            continue;
        }
        let manifest_version = match entry.schema_version.parse::<SchemaVersion>() {
            Ok(v) => v,
            Err(_) => {
                incompatible_files.push(RejectedManifestFile {
                    file: entry.clone(),
                    reason: format!(
                        "manifest schema_version {:?} is malformed",
                        entry.schema_version
                    ),
                });
                continue;
            }
        };

        let Some(client_entry) = current.get(&entry.name) else {
            // Manifest is advertising a file the client doesn't know about.
            // This is not a bug in the manifest — future data releases can
            // add files — but the current client cannot install it because
            // it has no compatibility range to check against. Recorded as
            // a diagnostic; does NOT by itself prevent an `UpToDate` status
            // when the client's known files are all current.
            incompatible_files.push(RejectedManifestFile {
                file: entry.clone(),
                reason: "unknown file: client declared no schema range".into(),
            });
            continue;
        };

        match schema_compat_check(&manifest_version, &client_entry.accepted) {
            Compatibility::Compatible => {
                // Enforce the manifest's per-file min/max client-schema
                // bounds. A file whose own `schema_version` would pass
                // `schema_compat_check` can still be refused here when
                // the publisher has narrowed support to a client range
                // that excludes us. This covers the Codex adversarial
                // review finding "published min/max_client_schema
                // bounds are parsed but never enforced".
                if let Err(reason) = check_client_schema_bounds(entry, client_entry) {
                    incompatible_files.push(RejectedManifestFile {
                        file: entry.clone(),
                        reason,
                    });
                    continue;
                }
                // Freshness: prefer content identity (sha256) when we have
                // it, so data-only releases at the same `schema_version`
                // are detected. Fall back to schema_version comparison for
                // generic callers that set `installed` without a hash.
                // Manifest shas are
                // already validated to 64 lowercase hex chars at the fetch
                // boundary; compare case-insensitively so a caller-provided
                // upper-case hex still matches.
                let is_newer = match (&client_entry.installed_sha256, &client_entry.installed) {
                    (Some(installed_sha), _) => !installed_sha.eq_ignore_ascii_case(&entry.sha256),
                    (None, Some(installed_version)) => manifest_version > *installed_version,
                    (None, None) => true,
                };
                if is_newer {
                    compatible_files.push(entry.clone());
                }
            }
            Compatibility::IncompatibleMajor {
                file_major,
                client_accepted_major,
            } => {
                incompatible_files.push(RejectedManifestFile {
                    file: entry.clone(),
                    reason: format!(
                        "incompatible MAJOR: file={file_major} client_accepted={client_accepted_major}"
                    ),
                });
            }
            Compatibility::IncompatibleMinor {
                file_minor,
                client_minimum_minor,
            } => {
                incompatible_files.push(RejectedManifestFile {
                    file: entry.clone(),
                    reason: format!(
                        "incompatible MINOR: file={file_minor} client_minimum={client_minimum_minor}"
                    ),
                });
            }
        }
    }

    if compatible_files.is_empty() {
        return Ok(YamlUpdateStatus::UpToDate {
            manifest,
            incompatible_files,
        });
    }

    Ok(YamlUpdateStatus::UpdateAvailable {
        manifest,
        compatible_files,
        incompatible_files,
    })
}

/// Download + atomically install each compatible file listed in `status`.
///
/// `status` must be a [`YamlUpdateStatus::UpdateAvailable`]; any other
/// variant returns an empty [`YamlUpdateReport`] without HTTP or disk I/O.
/// Per-file errors are collected in the report's `failed` vec rather than
/// surfaced as an [`UpdateError`]: a partial batch where one file fails is
/// a successful orchestrator outcome from the caller's perspective.
pub async fn apply_yaml_update(
    client: &GithubClient,
    status: YamlUpdateStatus,
) -> Result<YamlUpdateReport> {
    let (files, release_tag) = match status {
        YamlUpdateStatus::UpdateAvailable {
            manifest,
            compatible_files,
            ..
        } => (compatible_files, manifest.release_tag),
        _ => return Ok(YamlUpdateReport::default()),
    };

    let cache_dir = ensure_yaml_cache_dir()
        .map_err(|e| UpdateError::Generic(format!("cache dir unavailable: {e}")))?;

    let mut report = YamlUpdateReport::default();

    for entry in files {
        match install_one(client, &entry, &cache_dir, &release_tag).await {
            Ok(outcome) => report.installed.push(outcome),
            Err(failure) => report.failed.push(failure),
        }
    }

    Ok(report)
}

/// Fetch the current manifest and install only the subset the user approved
/// at review time. This is the single entry point binding callers should
/// use for apply: it folds the fetch, classify, consent gate, and install
/// loop into one step with explicit staleness detection.
///
/// # Gates (in order)
///
/// 1. `config.enabled == false` → [`UpdateError::UpdateCheckDisabled`].
///    No HTTP. Honors the `Update Check: false` setting end-to-end so a
///    user that toggled the setting off between check and apply cannot
///    still trigger a network install.
/// 2. Fresh manifest fetch + classify (same rules as [`check_yaml_update`]).
/// 3. If the fresh manifest's `release_tag` differs from
///    `approved.release_tag` → [`UpdateError::DecisionStale`]. The
///    publisher rotated to a new release while the user was reviewing;
///    refuse to install the new release silently and surface the drift
///    so the GUI / CLI can prompt a re-check.
/// 4. If a freshly-fetched manifest entry keeps the same file name but now
///    advertises a different `sha256` than the user approved,
///    [`UpdateError::DecisionDigestStale`] short-circuits the whole apply.
///    Same tag plus same name is not sufficient consent when the bytes
///    changed.
/// 5. Install only manifest files whose `name` is in `approved.file_names`
///    AND that the fresh classifier still marks as compatible. An approved
///    file that no longer appears in the manifest (or that has become
///    incompatible) is recorded in the report's `failed` list with a
///    reason, not silently dropped.
///
/// # Why not just `apply_yaml_update(status)` directly
///
/// `apply_yaml_update` takes a `YamlUpdateStatus` produced moments ago
/// and has no way to know whether the user actually saw the exact files
/// it is about to install. Embedding the approved identity in a separate
/// type makes the consent contract explicit and lets the FFI carry
/// exactly the data the GUI already displays to the user.
pub async fn apply_yaml_update_with_decision(
    client: &GithubClient,
    pages_url: &str,
    tag_prefix: &str,
    current: &ClientSchemaSet,
    config: UpdateCheckConfig,
    approved: &ApprovedUpdate,
) -> Result<YamlUpdateReport> {
    if !config.enabled {
        return Err(UpdateError::UpdateCheckDisabled);
    }

    // Validate the approved decision early, before any network I/O, so
    // binding-layer bugs fail fast without unnecessary HTTP traffic.
    let approved_sha_by_name = approved_file_sha_map(approved)?;

    let status = check_yaml_update(client, pages_url, tag_prefix, current, config).await?;

    let (manifest, compatible_files, incompatible_files) = match status {
        YamlUpdateStatus::UpdateAvailable {
            manifest,
            compatible_files,
            incompatible_files,
        } => (manifest, compatible_files, incompatible_files),
        YamlUpdateStatus::UpToDate {
            manifest,
            incompatible_files,
        } => (manifest, Vec::new(), incompatible_files),
        YamlUpdateStatus::Disabled => {
            // Guarded above via `config.enabled`, but check_yaml_update
            // may return Disabled for other reasons in the future. Keep
            // the branch surface-level safe.
            return Err(UpdateError::UpdateCheckDisabled);
        }
        YamlUpdateStatus::Unknown { reason } => {
            return Err(UpdateError::Generic(format!(
                "manifest classification unknown: {reason}"
            )));
        }
    };

    if manifest.release_tag != approved.release_tag {
        return Err(UpdateError::DecisionStale {
            approved: approved.release_tag.clone(),
            manifest: manifest.release_tag,
        });
    }

    for entry in &manifest.files {
        if let Some(approved_sha256) = approved_sha_by_name.get(entry.name.as_str())
            && !approved_sha256.eq_ignore_ascii_case(&entry.sha256)
        {
            return Err(UpdateError::DecisionDigestStale {
                release_tag: manifest.release_tag.clone(),
                file: entry.name.clone(),
                approved_sha256: (*approved_sha256).to_string(),
                manifest_sha256: entry.sha256.clone(),
            });
        }
    }

    // Build a quick lookup set so we don't pay O(N*M) membership checks
    // when the approved list has more than a handful of names.
    let approved_names: std::collections::HashSet<&str> =
        approved_sha_by_name.keys().copied().collect();
    let manifest_names: std::collections::HashSet<&str> = manifest
        .files
        .iter()
        .map(|entry| entry.name.as_str())
        .collect();
    let rejected_reasons: HashMap<&str, &str> = incompatible_files
        .iter()
        .map(|rejected| (rejected.file.name.as_str(), rejected.reason.as_str()))
        .collect();

    // Partition the freshly-classified compatible files into "approved"
    // (install) and "not approved" (ignore — the user didn't confirm them,
    // so we won't touch them even if the manifest newly marks them as
    // compatible). This is the "install only what the user reviewed"
    // contract.
    let mut report = YamlUpdateReport::default();
    let mut approved_found: std::collections::HashSet<&str> = std::collections::HashSet::new();
    let mut cache_dir: Option<PathBuf> = None;
    for entry in &compatible_files {
        if approved_names.contains(entry.name.as_str()) {
            approved_found.insert(entry.name.as_str());
            if cache_dir.is_none() {
                cache_dir =
                    Some(ensure_yaml_cache_dir().map_err(|e| {
                        UpdateError::Generic(format!("cache dir unavailable: {e}"))
                    })?);
            }
            let Some(cache_dir) = cache_dir.as_deref() else {
                return Err(UpdateError::Generic(
                    "cache dir unavailable after initialization".to_string(),
                ));
            };
            match install_one(client, entry, cache_dir, &manifest.release_tag).await {
                Ok(outcome) => report.installed.push(outcome),
                Err(failure) => report.failed.push(failure),
            }
        }
    }

    // Any approved name that did not survive the fresh classification is
    // reported only when the file disappeared from the manifest entirely or
    // was freshly rejected as incompatible. If the file is still present and
    // compatible but no longer newer than what is installed, that is a
    // truthful no-op rather than a failure.
    for approved_name in &approved.file_names {
        if !approved_found.contains(approved_name.as_str()) {
            if let Some(reason) = rejected_reasons.get(approved_name.as_str()) {
                report.failed.push(FileInstallOutcome::Failed {
                    name: approved_name.clone(),
                    reason: format!(
                        "approved file `{approved_name}` is no longer installable: {reason}; re-check required"
                    ),
                });
            } else if !manifest_names.contains(approved_name.as_str()) {
                report.failed.push(FileInstallOutcome::Failed {
                    name: approved_name.clone(),
                    reason: format!(
                        "approved file `{approved_name}` is no longer present in the current manifest; re-check required"
                    ),
                });
            }
        }
    }

    Ok(report)
}

async fn install_one(
    client: &GithubClient,
    entry: &YamlManifestFile,
    cache_dir: &Path,
    release_tag: &str,
) -> std::result::Result<FileInstallOutcome, FileInstallOutcome> {
    if is_local_ignore_yaml_file_name(&entry.name) {
        return Err(FileInstallOutcome::Failed {
            name: entry.name.clone(),
            reason: "install refused: Local Ignore YAML Data is user-owned".to_string(),
        });
    }
    // Defense-in-depth: even though validate_manifest already ran, a
    // binding caller could build a YamlManifestFile by hand and feed it
    // straight to apply_yaml_update. Re-validate the name and re-check
    // the resolved path stays inside `cache_dir` before any FS touch.
    if let Err(e) = validate_cache_file_name(&entry.name) {
        return Err(FileInstallOutcome::Failed {
            name: entry.name.clone(),
            reason: format!("install refused: {e}"),
        });
    }
    let target = cache_dir.join(&entry.name);
    if let Err(e) = ensure_path_in_cache(cache_dir, &target) {
        return Err(FileInstallOutcome::Failed {
            name: entry.name.clone(),
            reason: format!("install refused: {e}"),
        });
    }
    // Unique same-directory tmp path. The atomic rename requires the source
    // to live in the target's directory, so the tmp must stay a cache-dir
    // sibling. A shared `<name>.new` path would let two overlapping apply
    // calls (two app instances, GUI and CLI, or a retry racing a slow first
    // run) clobber each other's download before checksum/rename. Encoding
    // pid + nanos + a process-local counter makes a collision impossible
    // within a process and vanishingly unlikely across processes.
    let tmp = cache_dir.join(unique_tmp_name(&entry.name));

    if let Err(e) =
        download_release_asset(client, &entry.download_url, &tmp, release_tag, &entry.name).await
    {
        let _ = std::fs::remove_file(&tmp);
        return Err(FileInstallOutcome::Failed {
            name: entry.name.clone(),
            reason: format!("download failed: {e}"),
        });
    }

    match install_atomic(&target, &tmp, &entry.sha256) {
        Ok(outcome) => Ok(FileInstallOutcome::Installed {
            name: entry.name.clone(),
            schema_version: entry.schema_version.clone(),
            created_prev: outcome.created_prev,
        }),
        Err(FileIOError::ChecksumMismatch {
            expected, actual, ..
        }) => {
            // Ensure our own tmp is cleaned up on integrity failure as well.
            let _ = std::fs::remove_file(&tmp);
            Err(FileInstallOutcome::Failed {
                name: entry.name.clone(),
                reason: format!("sha256 mismatch: expected {expected}, got {actual}"),
            })
        }
        Err(e) => {
            let _ = std::fs::remove_file(&tmp);
            Err(FileInstallOutcome::Failed {
                name: entry.name.clone(),
                reason: format!("install failed: {e}"),
            })
        }
    }
}

/// Produce a per-invocation unique temp-file name for `entry_name`. Format:
/// `<entry_name>.new.<pid>.<nanos>.<seq>`. Every component is deterministic
/// but the combination is unique: `pid` separates processes, `nanos`
/// separates time, `seq` separates simultaneous calls within the same
/// process (AtomicU64 strictly monotonic).
fn unique_tmp_name(entry_name: &str) -> String {
    use std::sync::atomic::{AtomicU64, Ordering};
    static TMP_SEQ: AtomicU64 = AtomicU64::new(0);

    let pid = std::process::id();
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let seq = TMP_SEQ.fetch_add(1, Ordering::Relaxed);
    format!("{entry_name}.new.{pid}.{nanos}.{seq}")
}

/// Roll back the cache copy of `file_name` to its `.prev` sibling.
///
/// Returns [`RollbackOutcome::NoPreviousVersion`] when no `.prev` exists —
/// not an error, because the steady-state after a successful install with
/// no prior copy legitimately has no `.prev`.
pub fn rollback_yaml_update(file_name: &str) -> Result<RollbackOutcome> {
    // Binding callers reach rollback_yaml_update directly, so we can't
    // rely on manifest validation to have already refused a traversal
    // name. Validate here and confirm path containment before touching
    // the filesystem. See the Codex adversarial review finding for the
    // direct-call escape scenario this blocks.
    validate_cache_file_name(file_name)?;
    if is_local_ignore_yaml_file_name(file_name) {
        return Err(UpdateError::Generic(
            "rollback refused: Local Ignore YAML Data is user-owned".to_string(),
        ));
    }
    // Rollback uses the same per-target lockfile helper as install, so the
    // cache directory must exist even when the file itself never has.
    let cache_dir = ensure_yaml_cache_dir()
        .map_err(|e| UpdateError::Generic(format!("cache dir unavailable: {e}")))?;
    let target = cache_dir.join(file_name);
    ensure_path_in_cache(&cache_dir, &target)?;

    match classic_file_io_core::rollback(&target).map_err(|e| {
        UpdateError::Generic(format!("rollback failed for {}: {e}", target.display()))
    })? {
        FsRollbackOutcome::RolledBack { .. } => Ok(RollbackOutcome::RolledBack {
            file_name: file_name.to_string(),
        }),
        FsRollbackOutcome::NoPreviousVersion { .. } => Ok(RollbackOutcome::NoPreviousVersion {
            file_name: file_name.to_string(),
        }),
    }
}

#[cfg(test)]
#[path = "yaml_update_tests.rs"]
mod unit_tests;
