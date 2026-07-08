# Clear fallback cache before returning `NotPublished`

## Problem

In `business-logic/classic-update-core/src/notification.rs`, the orchestrator
`check_app_notification_with` has a branch (lines ~577-582) that returns
`NotificationStatus::not_published()` when **both** channels confirm absence:

```rust
Err(fallback_err)
    if matches!(&pages_err, UpdateError::NotFound(_))
        && matches!(&fallback_err, UpdateError::NotFound(_)) =>
{
    Ok(NotificationStatus::not_published())
}
```

This arm does **not** clear the on-disk fallback cache. When a prior Releases
fallback seeded `fallback.marker` + `manifest-latest.json`, and this branch
now observes Pages `404` + no matching release, it returns `NotPublished`
while leaving the stale marker/body intact.

### Why that is a bug (resurrection window)

The non-404 failure path above (lines ~546-555) still consults
`try_fallback_cache`:

```rust
if !matches!(&pages_err, UpdateError::NotFound(_)) {
    if let Some(cached) = try_fallback_cache(cache_dir) {
        return Ok(classify(installed_version, &cached));
    }
}
```

So this sequence resurrects a notification that was just confirmed unpublished:

1. Pages `404` + Releases returns a manifest -> `persist_fallback_manifest_body`
   seeds `fallback.marker` + body (ETag cleared). Marker mtime is fresh.
2. Maintainer unpublishes. Next check: Pages `404` + Releases `NotFound` ->
   returns `NotPublished`, **but marker + body remain on disk** (current bug).
3. Within `FALLBACK_CACHE_TTL` (6h), a Pages timeout/`5xx` (non-404) occurs.
   `pages_err` is not `NotFound`, so `try_fallback_cache` runs, finds the still
   in-TTL marker + valid body, and returns the **stale** manifest -> the user
   sees a resurrected notification for a channel that was just confirmed empty.

### Existing coverage gap

`notification_tests.rs::orchestrator::pages_404_with_fresh_fallback_cache_still_checks_releases_absence`
(lines ~1104-1146) sets up exactly this pre-seeded scenario and asserts the
result is `NotPublished`, but it never asserts the cache is purged. The
resurrection vector is therefore untested.

## Goal

When both channels confirm absence, purge the fallback cache before returning
`NotPublished` so a later non-404 Pages failure within `FALLBACK_CACHE_TTL`
cannot resurrect the just-unpublished manifest.

## Scope

- Only `business-logic/classic-update-core`. No public API changes (function
  signatures, `UpdateError` variants, and `NotificationStatus` shape are all
  unchanged), so **no CXX/Node/Python parity gates are triggered** and no
  pyo3/`PYO3_PYTHON` setup is needed for the crate-scoped test run.
- Purely additive private helper + one orchestrator branch line + tests.

### Resolved decisions

- **Doc/spec scope = Standard.** Implement steps 1-4 (code fix, helper, tests,
  and the `docs/api` runtime-flow update). **Do NOT edit the OpenSpec spec**
  (step 5 is dropped from this change).
- **Purge artifacts = marker + body + ETag.** `clear_fallback_cache` removes
  all three for a clean "confirmed absent => empty cache" invariant.

## Changes

### 1. Code: purge the cache in the `not_published` arm

File: `business-logic/classic-update-core/src/notification.rs` (arm at ~577).

Add a `clear_fallback_cache(cache_dir);` call immediately before
`Ok(NotificationStatus::not_published())`, with an explanatory comment:

```rust
Err(fallback_err)
    if matches!(&pages_err, UpdateError::NotFound(_))
        && matches!(&fallback_err, UpdateError::NotFound(_)) =>
{
    // Both channels confirm absence. Purge any fallback-seeded cache
    // (marker + body + stale ETag) so a later non-404 Pages failure
    // within FALLBACK_CACHE_TTL cannot resurrect — via try_fallback_cache —
    // the notification we just confirmed unpublished.
    clear_fallback_cache(cache_dir);
    Ok(NotificationStatus::not_published())
}
```

`cache_dir: Option<&Path>` is already in scope in `check_app_notification_with`.
`fallback_err` is still referenced by the guard, so no unused-binding warning.

### 2. Code: new `clear_fallback_cache` helper

Add after the existing `clear_fallback_marker` (after ~line 758). The needed
names are already imported at the top of the file
(`CACHED_MANIFEST_FILENAME`, `ETAG_FILENAME` from `manifest_fetch`;
`FALLBACK_MARKER_FILENAME` is a module const).

```rust
/// Purge the entire cached notification triplet — fallback marker,
/// manifest body, and any stale Pages ETag — when both channels confirm
/// the notification is unpublished (Pages `404` + no matching
/// `app-notification-v*` release).
///
/// Distinct from [`clear_fallback_marker`], which runs on a Pages
/// *success*: there `try_pages` has just rewritten the body with
/// Pages-authoritative bytes, so only the now-stale marker must go. A
/// confirmed `NotPublished` leaves NO authoritative body anywhere, so the
/// body and ETag are dropped too. Removing the marker alone already closes
/// the [`try_fallback_cache`] reuse window, but clearing the body and ETag
/// as well prevents a later non-404 Pages failure within
/// [`FALLBACK_CACHE_TTL`] from resurrecting the just-unpublished manifest
/// and avoids leaving an orphan ETag paired with a removed body.
///
/// All I/O errors are logged and swallowed: the `NotPublished` result is
/// already correct and a best-effort cache cleanup must not demote it.
fn clear_fallback_cache(cache_dir: Option<&Path>) {
    let Some(dir) = cache_dir else {
        return;
    };
    for (path, label) in [
        (dir.join(FALLBACK_MARKER_FILENAME), "fallback cache marker"),
        (dir.join(CACHED_MANIFEST_FILENAME), "cached manifest body"),
        (dir.join(ETAG_FILENAME), "stale Pages ETag"),
    ] {
        match std::fs::remove_file(&path) {
            Ok(()) => {}
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
            Err(e) => {
                log::warn!(
                    "failed to clear {label} at {} after confirmed not-published: {e}",
                    path.display(),
                );
            }
        }
    }
}
```

Rationale for clearing the body + ETag (not just the marker): clearing the
marker alone is functionally sufficient to close the `try_fallback_cache`
window (it checks the marker first), but the reviewer asked for marker/body,
and a confirmed `NotPublished` means there is no authoritative manifest
anywhere — leaving a stale body or an orphan ETag (pointing at a now-removed
body) is inconsistent state. Removing all three yields a clean "confirmed
absent => empty cache" invariant (resolved decision: purge all three).

### 3. Tests

File: `business-logic/classic-update-core/src/notification_tests.rs`.

**(a) Unit tests in `mod fallback_cache`** (add before its closing brace,
~line 900). `ETAG_FILENAME`, `CACHED_MANIFEST_FILENAME`, `SystemTime`,
`FALLBACK_MARKER_FILENAME`, `try_fallback_cache_at`, and
`persist_fallback_manifest_body` are all in scope there.

```rust
#[test]
fn clear_fallback_cache_removes_marker_body_and_etag() {
    let tmp = TempDir::new().unwrap();
    persist_fallback_manifest_body(Some(tmp.path()), minimal_manifest_bytes());
    // A stray ETag proves the purge also drops an orphan ETag.
    std::fs::write(tmp.path().join(ETAG_FILENAME), b"\"W/stale\"").unwrap();
    assert!(tmp.path().join(FALLBACK_MARKER_FILENAME).exists());
    assert!(tmp.path().join(CACHED_MANIFEST_FILENAME).exists());

    clear_fallback_cache(Some(tmp.path()));

    assert!(!tmp.path().join(FALLBACK_MARKER_FILENAME).exists(), "marker purged");
    assert!(!tmp.path().join(CACHED_MANIFEST_FILENAME).exists(), "body purged");
    assert!(!tmp.path().join(ETAG_FILENAME).exists(), "stale ETag purged");
    // Reuse window is closed even while still within TTL.
    assert!(
        try_fallback_cache_at(Some(tmp.path()), SystemTime::now()).is_none(),
        "no cache may be reused after a confirmed not-published purge",
    );
}

#[test]
fn clear_fallback_cache_is_noop_when_cache_dir_is_none() {
    clear_fallback_cache(None);
}
```

**(b) Strengthen the orchestrator regression test** — extend
`pages_404_with_fresh_fallback_cache_still_checks_releases_absence`
(~line 1104) with post-call assertions after the existing classification
checks:

```rust
    // The confirmed not-published result MUST purge the fallback cache so a
    // later non-404 Pages failure within TTL cannot resurrect the stale
    // manifest via try_fallback_cache.
    assert!(
        !tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
        "not-published must clear the fallback marker",
    );
    assert!(
        !tmp.path().join(CACHED_MANIFEST_FILENAME).exists(),
        "not-published must clear the fallback body",
    );
    assert!(
        try_fallback_cache_at(Some(tmp.path()), SystemTime::now()).is_none(),
        "purged cache must not be reusable on a later Pages outage",
    );
```

`CACHED_MANIFEST_FILENAME` is already imported in `mod orchestrator`;
`FALLBACK_MARKER_FILENAME` / `try_fallback_cache_at` resolve via `use super::*`.
If `SystemTime` does not resolve, add `use std::time::SystemTime;` to the
`mod orchestrator` imports.

This single addition fails on the current code (marker/body remain) and passes
with the fix — directly proving the resurrection vector is closed.

### 4. Docs sync

File: `docs/api/app-update-notification-delivery.md`, runtime-flow box, step 6
(~lines 59-62). Update to note the purge, preserving the ASCII box right-border
alignment (match the interior width of adjacent rows):

> 6. If Pages reports NotFound and Releases also finds no
>    `app-notification-v*` release, purge the fallback cache (marker + body +
>    ETag) and return NotPublished — so a later Pages outage cannot resurrect
>    the unpublished manifest. A matching release missing `manifest.json` is a
>    broken publish and remains a fetch failure.

### 5. Spec sync — NOT included

Dropped per the resolved Standard scope. The OpenSpec spec
(`openspec/specs/app-update-notification/spec.md`) is left unchanged; the fix
is treated as a bug fix matching the existing `NotPublished` intent.

## Validation

Run from repo root (Rust-only change; no pyo3, no parity gates):

```
cargo test -p classic-update-core
cargo clippy -p classic-update-core --all-targets --all-features -- -D warnings
cargo fmt --all -- --check
```

(If running from Git Bash, `source tools/use_msvc_from_git_bash.sh` first per
AGENTS.md. From pwsh this is not needed.)

## Out of scope / non-goals

- No change to `clear_fallback_marker` (Pages-success path keeps body+ETag as
  Pages-authoritative — correct as-is).
- No change to public API, error variants, bindings, or parity baselines.
- No behavioral change to the `NotPublished` classification value itself; only
  the on-disk cache side effect is added.
- OpenSpec spec is intentionally not edited (Standard scope).
