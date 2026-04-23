//! Shared Pages-first manifest fetch with ETag caching.
//!
//! Both [`crate::yaml_update::fetch_yaml_manifest`] and
//! [`crate::notification::fetch_app_notification_manifest`] use this helper
//! so a single implementation owns the conditional-GET and cache-persistence
//! logic. The Releases-API fallback remains per-channel because tag shapes
//! and asset-lookup rules differ between the YAML-data channel
//! (`yaml-data-v*`) and the notification channel (`app-notification-v*`).
//!
//! # Cache layout
//!
//! On success the helper writes two sibling files to the caller-supplied
//! cache directory:
//!
//! - [`CACHED_MANIFEST_FILENAME`] — the canonicalized manifest body bytes.
//! - [`ETAG_FILENAME`] — the server-issued `ETag` header, trimmed.
//!
//! On a subsequent request the helper sends the stored ETag via
//! `If-None-Match`; on `304 Not Modified` it re-parses and re-validates the
//! cached body. Passing `cache_dir = None` disables caching entirely — no
//! files are written, no `If-None-Match` header is sent, and a `304` would
//! surface as a retryable transport error (unreachable in practice because
//! we never sent the ETag in the first place).

use crate::error::{Result, UpdateError};
use crate::github::GithubClient;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, SystemTime};

/// File name used to persist the last-seen Pages manifest ETag inside the
/// caller-supplied cache directory.
pub const ETAG_FILENAME: &str = "manifest.etag";

/// File name used to persist the last-seen Pages manifest body so a `304
/// Not Modified` response can still return a parsed manifest without an
/// additional body round-trip.
pub const CACHED_MANIFEST_FILENAME: &str = "manifest-latest.json";

/// Default Pages-GET timeout, intentionally shorter than the GitHub API
/// client's 30s so we fall back quickly when Pages is slow or unreachable.
pub(crate) const PAGES_TIMEOUT: Duration = Duration::from_secs(5);

/// Internal classification of a Pages-leg failure.
///
/// Callers ([`crate::yaml_update::fetch_yaml_manifest`],
/// [`crate::notification::fetch_app_notification_manifest`]) branch on
/// this to decide whether to fall back to the Releases API
/// ([`PagesError::Transport`] and [`PagesError::Invalid`]) or surface a
/// structural refusal directly ([`PagesError::UnsupportedVersion`] — the
/// API leg would fail identically).
#[derive(Debug)]
pub(crate) enum PagesError {
    /// Network, timeout, non-304/non-2xx, or cache-read failure.
    /// Retryable via the Releases fallback.
    Transport(UpdateError),
    /// The body parsed as JSON but failed post-parse validation (missing
    /// required field, wrong channel tag, malformed sub-field). Retryable
    /// because the Releases-leg asset could still be healthy.
    Invalid(UpdateError),
    /// `manifest_version` exceeds the client's max-supported number.
    /// Not retryable — the Releases-leg asset would fail identically.
    UnsupportedVersion(UpdateError),
}

impl From<UpdateError> for PagesError {
    fn from(err: UpdateError) -> Self {
        match err {
            UpdateError::ManifestUnsupportedVersion { .. } => PagesError::UnsupportedVersion(err),
            // Structural manifest rejections (YAML validator + notification
            // validator) should fall through to the Releases fallback.
            UpdateError::ManifestInvalid { .. } => PagesError::Invalid(err),
            UpdateError::NotificationDecode { .. } => PagesError::Invalid(err),
            // Raw JSON decode failures are recoverable — the Releases-leg
            // asset might be well-formed even if Pages' was not.
            UpdateError::JsonError(_) => PagesError::Invalid(err),
            other => PagesError::Transport(other),
        }
    }
}

impl std::fmt::Display for PagesError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PagesError::Transport(err)
            | PagesError::Invalid(err)
            | PagesError::UnsupportedVersion(err) => std::fmt::Display::fmt(err, f),
        }
    }
}

/// Attempt the Pages leg exactly once, generic over the manifest body type.
///
/// On success: writes the fresh body + ETag to the cache dir (when
/// provided) and returns the parsed manifest. On `304 Not Modified`:
/// re-parses and re-validates the cached body (a poisoned cache MUST NOT
/// short-circuit validation — if the cached body fails validation today
/// the caller should fall through to the Releases fallback rather than
/// silently return the bad manifest).
///
/// The `parse` closure turns raw bytes into `T`; the `validate` closure
/// performs per-channel post-parse checks. Both closures return
/// [`UpdateError`] on failure, which [`PagesError::from`] classifies into
/// the right retry category.
pub(crate) async fn try_pages<T, P, V>(
    client: &GithubClient,
    pages_url: &str,
    cache_dir: Option<&Path>,
    parse: P,
    validate: V,
) -> std::result::Result<T, PagesError>
where
    P: Fn(&[u8]) -> Result<T>,
    V: Fn(&T) -> Result<()>,
{
    // When `cache_dir` is `None`, manifest-cache read/write is disabled:
    // we neither read a stored ETag (no `If-None-Match`) nor persist the
    // 200 body. Deliberately not a `PathBuf::new()` fallback — that
    // previous sentinel caused cache files to land under the process CWD.
    let etag_path = cache_dir.map(|d| d.join(ETAG_FILENAME));
    let cached_manifest_path = cache_dir.map(|d| d.join(CACHED_MANIFEST_FILENAME));

    let mut req = client.http_client().get(pages_url).timeout(PAGES_TIMEOUT);
    let cached_etag = etag_path.as_deref().and_then(read_etag);
    if let Some(etag) = &cached_etag {
        req = req.header("If-None-Match", etag.as_str());
    }

    let response = req
        .send()
        .await
        .map_err(|e| PagesError::Transport(UpdateError::HttpError(e)))?;

    if response.status() == reqwest::StatusCode::NOT_MODIFIED {
        // Pages confirmed our ETag still matches — load the cached body.
        let cached_path = cached_manifest_path.as_deref().ok_or_else(|| {
            // Defensive: we only send `If-None-Match` when an ETag was
            // read from `etag_path`, which requires `cache_dir` to be
            // Some. Surface as Transport so the caller falls back to the
            // Releases API rather than panicking on a poisoned server
            // response.
            PagesError::Transport(UpdateError::Generic(
                "Pages returned 304 but no cache directory was available for the stored body"
                    .into(),
            ))
        })?;
        let bytes = std::fs::read(cached_path).map_err(|e| {
            PagesError::Transport(UpdateError::Generic(format!(
                "Pages returned 304 but cached manifest at {} could not be read: {e}",
                cached_path.display(),
            )))
        })?;
        let manifest = parse(&bytes).map_err(PagesError::from)?;
        // Re-validate: a poisoned 304-cached body must fall through to
        // the API rather than being returned verbatim.
        validate(&manifest).map_err(PagesError::from)?;
        return Ok(manifest);
    }

    if !response.status().is_success() {
        return Err(PagesError::Transport(UpdateError::GithubError(format!(
            "pages GET returned {}",
            response.status()
        ))));
    }

    let etag_header = response
        .headers()
        .get(reqwest::header::ETAG)
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string());

    let bytes = response
        .bytes()
        .await
        .map_err(|e| PagesError::Transport(UpdateError::HttpError(e)))?
        .to_vec();

    let manifest = parse(&bytes).map_err(PagesError::from)?;

    // Validate BEFORE persisting so we never cache an invalid body that a
    // future 304 would then return from the cached-body branch.
    validate(&manifest).map_err(PagesError::from)?;

    // Persist the body + ETag so a future 304 can reuse them. Only
    // reached once parse+validate have both succeeded. Skipped entirely
    // when `cache_dir` is `None` — no relative-cwd fallback.
    //
    // Persistence is transactional across the two files: the new ETag
    // only lands when the new body has been durably committed, and a
    // body-write failure clears any stale ETag on disk. Otherwise a
    // next request could send `If-None-Match: <new>` against a stale
    // (or missing) cached body, take a `304`, and silently return
    // bytes that do not correspond to that ETag. The body write goes
    // through a sibling temp-file + rename so a partial write (disk
    // full, AV/file lock) cannot pair a fresh ETag with half-written
    // body bytes.
    let body_persisted = if let Some(cached_path) = cached_manifest_path.as_deref() {
        if let Some(parent) = cached_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        match write_body_atomically(cached_path, &bytes) {
            Ok(()) => true,
            Err(e) => {
                log::warn!(
                    "failed to persist cached manifest body to {}: {e}",
                    cached_path.display(),
                );
                false
            }
        }
    } else {
        false
    };
    if let Some(etag_p) = etag_path.as_deref() {
        if body_persisted {
            if let Some(etag) = etag_header {
                if let Err(e) = std::fs::write(etag_p, etag.as_bytes()) {
                    log::warn!(
                        "failed to persist manifest ETag to {}: {e}",
                        etag_p.display(),
                    );
                }
            } else {
                // Server returned a body but no ETag — clear any stale
                // cached one so a future If-None-Match doesn't reference
                // bytes we no longer hold.
                let _ = std::fs::remove_file(etag_p);
            }
        } else {
            // Body-write failed: drop any stale ETag so the next
            // request cannot carry an If-None-Match that takes a 304
            // against bytes we never persisted.
            let _ = std::fs::remove_file(etag_p);
        }
    }

    Ok(manifest)
}

/// Atomically persist `bytes` at `target` by writing to a sibling temp
/// file and renaming it over the destination. `std::fs::rename` is
/// atomic for files on both POSIX (`rename(2)`) and Windows
/// (`MoveFileExW` with `MOVEFILE_REPLACE_EXISTING`) when source and
/// destination share a filesystem/volume — so a partial write leaves
/// the previous body untouched rather than pairing a fresh ETag with
/// half-written bytes.
///
/// The temp filename is unique per call (PID + process-local counter +
/// a fresh nanosecond sample) rather than a fixed `<target>.tmp`
/// sibling. Two concurrent writers — a GUI app and a CLI run against
/// the same per-user cache directory, two worker threads sharing the
/// runtime, etc. — would otherwise race on the shared temp path:
/// writer A's `std::fs::write` could truncate writer B's temp bytes,
/// then B's `rename` would land A's bytes while B's ETag was about to
/// be persisted separately, silently pairing a fresh ETag with the
/// wrong body. Per-call uniqueness keeps the two writers' payloads on
/// disjoint temp paths; they still race on the `rename`, but `rename`
/// over the destination is atomic at the filesystem level, so the
/// loser's body is replaced wholesale instead of merged.
fn write_body_atomically(target: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let tmp = unique_tmp_sibling(target);
    // Best-effort cleanup of a stranded tmp from a prior crash at the
    // exact same PID+counter+nanos coordinate — astronomically
    // unlikely, but cheap insurance against a pre-existing temp that
    // would otherwise make the write path ambiguous with a prior
    // install.
    let _ = std::fs::remove_file(&tmp);
    std::fs::write(&tmp, bytes)?;
    if let Err(e) = std::fs::rename(&tmp, target) {
        // Rename failed (target is a directory, cross-device, AV lock).
        // Clean up the orphan tmp so a retry starts from a clean slate.
        let _ = std::fs::remove_file(&tmp);
        return Err(e);
    }
    Ok(())
}

/// Process-local counter that guarantees temp-filename uniqueness across
/// writers from the same process even when two calls sample the same
/// nanosecond clock tick.
static TMP_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Build a unique sibling temp path for `target`. Combines the process
/// id, a monotonic process-local counter, and a nanosecond clock sample
/// so two concurrent writers — across processes (two CLASSIC binaries)
/// or within one process (pooled async workers) — never pick the same
/// temp name. The format is `<target>.tmp.<pid>.<counter>.<nanos>`,
/// which keeps the filename recognisable in a `dir` listing while
/// remaining collision-free under contention.
fn unique_tmp_sibling(target: &Path) -> std::path::PathBuf {
    let pid = std::process::id();
    let seq = TMP_COUNTER.fetch_add(1, Ordering::Relaxed);
    let nanos = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let mut tmp_name = target.as_os_str().to_os_string();
    tmp_name.push(format!(".tmp.{pid}.{seq}.{nanos}"));
    std::path::PathBuf::from(tmp_name)
}

/// Read the cached ETag from disk, returning `None` on missing file,
/// empty/whitespace-only content, or read error.
pub(crate) fn read_etag(etag_path: &Path) -> Option<String> {
    std::fs::read_to_string(etag_path).ok().and_then(|s| {
        let trimmed = s.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(trimmed.to_string())
        }
    })
}

#[cfg(test)]
#[path = "manifest_fetch_tests.rs"]
mod tests;
