# App Update Notification Delivery

Contributor-facing reference for CLASSIC's binary-release notification channel: how clients learn that a new CLASSIC build is available, how the client-side pipeline resolves and caches the manifest, and how maintainers publish a new notification.

This page describes the cross-crate flow introduced by the `app-update-manifest-notification` OpenSpec change. Companion to [`yaml-update-delivery.md`](yaml-update-delivery.md) — both channels share the same Pages-first + Releases-fallback mental model, but this one is deliberately payload-free (no SHA-256 checksums, no atomic install, no rollback).

For per-crate APIs:

- [`classic-update-core`](classic-update-core.md) — `notification` module (`AppNotificationManifest`, `Classification`, `NotificationStatus`, `check_app_notification`)
- [`classic-path-core`](classic-path-core.md) — `notification_cache_dir`, `ensure_notification_cache_dir`

---

## 1. The notification-manifest contract

A **notification manifest** is a small JSON document published by the maintainer every time a new CLASSIC binary release is announced. Every manifest carries:

| Field | Type | Required | Purpose |
| --- | --- | --- | --- |
| `manifest_version` | string (`MAJOR.MINOR`) | yes | Forward-compat gate; older clients reject a manifest whose MAJOR exceeds what they understand. Regex: `^\d+\.\d+$`. |
| `release_tag` | string | yes | The binary-release tag being advertised (e.g. `"v9.2.0"`). This is the tag a user installs — *not* the `app-notification-v*` tag that triggered the publish workflow. |
| `latest_version` | string (SemVer) | yes | SemVer string used for `installed < latest` comparison. |
| `published_at` | string (RFC 3339) | yes | UTC timestamp of publication. |
| `min_supported_version` | string (SemVer) | no | Minimum client SemVer still supported; when present, installed versions below this classify as `DeprecatedClient`. |
| `display.title` / `display.body` | string | no | Short free-form text for UI surfacing. |
| `display.cta_url` | string | no | Call-to-action URL (download page, changelog, …). MUST be `https://`. Both the publish validator and the runtime validator reject any other scheme so a typo'd or compromised manifest cannot downgrade users onto a cleartext destination at the moment they are being asked to fetch an update. |

The manifest is intentionally **payload-free**: no SHA-256 checksums, no download URLs for assets, no file install. The only "install" is the client remembering the manifest body and its ETag in a small cache directory.

Unknown fields are tolerated so a future manifest can add optional metadata without breaking older clients. Missing required fields surface as `UpdateError::NotificationDecode { field }` — see [`error-contract.md`](error-contract.md) for per-binding error shapes.

---

## 2. Runtime flow (client side)

```
┌───────────────────────────────────────────────────────────────────┐
│ check_app_notification(owner, repo, installed_version):           │
│   1. GET https://<owner>.github.io/<repo>/app-notification/       │
│      manifest-latest.json (Pages, sends If-None-Match when a      │
│      cached ETag exists).                                         │
│   2. On 200/304: parse, validate, classify. On success, clear     │
│      any stale fallback marker so the body is Pages-authoritative │
│      again.                                                       │
│   3. On manifest_version MAJOR > client max: surface              │
│      `ManifestUnsupportedVersion` directly — short-circuit past   │
│      the Releases fallback (same-schema asset would fail there).  │
│   4. On other Pages failure: if a fresh fallback cache exists     │
│      (marker present + body valid + within TTL), classify from    │
│      cache and skip the Releases API — avoids rate-limit thrash   │
│      during prolonged Pages outages. Otherwise hit Releases.      │
│   5. Releases fallback: list releases filtered by the             │
│      `app-notification-v*` prefix, newest tag, download           │
│      `manifest.json`, parse, classify, and seed the Pages cache   │
│      (body + fallback marker, ETag cleared).                      │
│   6. Returns NotificationStatus { classification, latest_version, │
│      published_at, min_supported_version?, display?, parse_error? │
│      }.                                                           │
└───────────────────────────────────────────────────────────────────┘
```

### Classification outcomes

Produced by `classic_update_core::notification::classify(installed, &manifest)`:

| Classification | When | Caller SHOULD |
| --- | --- | --- |
| `UpToDate` | `installed >= latest_version` (covers CI pre-release builds "ahead of latest") | Report current; no user action needed. |
| `UpdateAvailable` | `installed < latest_version` AND not deprecated | Surface display payload if present; optionally open `cta_url`. |
| `DeprecatedClient` | `installed < min_supported_version` | Warn the user; recommend upgrade to `latest_version`. |
| `Unknown` | Installed version fails SemVer parse, or the manifest's `latest_version` is itself not SemVer | Surface `parse_error`; do NOT silently treat as `UpToDate`. |

### Cache layout

Cache files live under the platform cache directory via
`classic_path_core::notification_cache_dir(owner, repo)`. The resolver is
namespaced by GitHub `<owner>/<repo>` so a check against repo A cannot
seed repo B's manifest body, ETag, or fallback marker. Owner and repo
segments are validated against the GitHub-allowed character set
(`A-Za-z0-9._-`); any segment containing path separators, traversal
markers (`.`/`..`), whitespace, or characters outside that set is
rejected with a typed `PathError::InvalidPath`. Pre-namespacing caches at
the unscoped `.../app-notification/` location are deliberately ignored
rather than migrated — they are throwaway per-user state and the next
successful check repopulates the new namespaced location.

```
<platform-cache>/CLASSIC/app-notification/<owner>/<repo>/
├── manifest-latest.json   # most recent 200 OK body OR fallback-seeded body
├── manifest.etag          # server-provided ETag (Pages path only)
└── fallback.marker        # present only when the body was seeded via the
                           # Releases-API fallback; its mtime drives the
                           # fallback-reuse TTL (6h). Cleared on any
                           # successful Pages fetch.
```

The cache is disjoint from the YAML-update cache (`<platform-cache>/CLASSIC/yaml-cache/`) so wiping one never affects the other. Cache corruption self-heals: on decode failure the client discards the cache and refetches.

When `fallback.marker` is present and its mtime is within TTL, a subsequent Pages outage re-uses the cached body instead of hitting the Releases API. Past TTL, the next outage re-fetches via Releases and re-seeds both the body and the marker. A successful Pages fetch removes the marker so the body is treated as Pages-authoritative again.

---

## 3. Error contract (per binding)

All three bindings propagate a single unified `UpdateError` family (design decision D-05) with notification-specific variants `NotificationFetchFailed`, `NotificationDecode`, `NotificationInstalledVersionParse`, `NotificationCacheIo`. The notification path can also surface the shared `ManifestUnsupportedVersion` variant when a fetched notification manifest advertises a newer `manifest_version` major. The shape each binding exposes follows the established per-language idiom:

| Binding | Error shape |
| --- | --- |
| C++ (CXX) | `NotificationStatusDto { classification = "error", error_message = "<Display>", …empty-string sentinels… }` |
| Node (NAPI-RS) | Promise rejects with `Error` whose `message` is prefixed with the variant-keyed code: `"FETCH_FAILED: <detail>"` / `"DECODE: <detail>"` / `"INSTALLED_VERSION_PARSE: <detail>"` / `"CACHE_IO: <detail>"` / `"UPDATE_ERROR: <detail>"`. Consumers discriminate with `err.message.startsWith("FETCH_FAILED:")`. The prefix-on-message shape (rather than a custom `err.code`) is a napi-rs 3.x async-macro constraint — `Status` is a fixed C-style enum, so custom variant codes can't round-trip through `execute_tokio_future_with_finalize_callback` as structured `code` values |
| Python (PyO3) | Raises a `ClassicNotificationError` subclass keyed to the variant, or the `ClassicNotificationError` base for shared notification-channel failures such as `ManifestUnsupportedVersion`; subclass of `ClassicUpdateError` so existing catches still work |

Full precedent + examples: [`error-contract.md`](error-contract.md).

---

## 4. Maintainer publish workflow

The maintainer workflow is [`.github/workflows/publish-app-notification.yml`](../../.github/workflows/publish-app-notification.yml). Trigger surface is narrow by spec:

- Trigger: `push` of a tag matching `app-notification-v*` (e.g. `app-notification-v9.2.0`).
- **No** `pull_request` trigger. **No** `workflow_dispatch` inputs that mutate content.

### Source artifact

The workflow reads its inputs from [`CLASSIC Data/app-notification.yaml`](../../CLASSIC%20Data/app-notification.yaml) (analogous to `client-schema-ranges.yaml` for yaml-data). Maintainers edit this file in the same PR that cuts the binary release and tag it `app-notification-v<SEMVER>` when the release is ready to be announced.

### Workflow stages

1. **Validate** — `tools/publish_app_notification/validate.py` rejects malformed source fields (missing `release_tag`, unparseable `latest_version`, non-RFC3339 `published_at`, typo'd display keys, non-HTTPS `display.cta_url`).
2. **Generate** — `tools/publish_app_notification/generate_manifest.py` projects the validated source into `manifest.json`, substituting the tag's UTC publication timestamp when the source leaves `published_at: null`.
3. **Draft release** — `gh release create --draft --latest=false` uploads `manifest.json` as the sole asset. `--latest=false` is applied at every `gh release edit` point so the repo's `latest` pointer stays on the most recent `v*` binary release (spec scenario "Latest pointer preserved").
4. **Promote to prerelease** — `gh release edit --draft=false --prerelease=true` makes the asset URL anonymously reachable (draft asset URLs 404 anonymously). `fetch_via_releases_fallback` passes `include_prereleases=false` to `get_all_releases`, so no API-fallback client sees the release yet.
5. **Anonymous-reachability probe** — `tools/publish_app_notification/verify_release_asset.py` fetches the asset URL anonymously with a retry budget. Closes the Codex-reviewed race window where a client could discover the release before the CDN has warmed the asset URL.
6. **Pages deploy** — writes `app-notification/manifest-latest.json` and `app-notification/manifest-<tag>.json` to `gh-pages`. The `app-notification/` path is disjoint from `yaml-data/` so the two publishers never collide. Runs while the release is still a prerelease so a Pages failure cannot leave the Releases-API fallback advertising a tag Pages does not serve.
7. **Pages smoke-test** — reuses `tools/publish_yaml_data/smoke_test_pages.py --pages-path app-notification/manifest-latest.json`; polls the Pages URL until its JSON `release_tag` matches the binary-release tag carried in the staged `manifest.json` (NOT the `app-notification-v*` workflow tag — those two deliberately diverge in this channel, so the workflow extracts the expected value from the staged manifest before invoking the helper).
8. **Clear prerelease flag** — `gh release edit --prerelease=false --latest=false` runs LAST, only after Pages has been proven to serve the new tag. Only now does the release become visible to `fetch_via_releases_fallback`. Running this step last keeps the Pages-first and Releases-API fallback channels on the same tag at every instant: a failure of step 6 or 7 leaves the release as a prerelease (invisible to fallback) while Pages-first clients still read the previous `manifest-latest.json`.

### Rollback

The notification channel is stateless beyond the ETag file, so rollback is trivial:

- *Client side:* delete `<platform-cache>/CLASSIC/app-notification/` and rerun the check.
- *Server side:* delete the `app-notification-v<tag>` release and revert the `gh-pages` commit. The next valid notification publish replaces `manifest-latest.json` atomically (the commit is a single file-change).

No database state, no `.prev` swap, no per-file rollback is required (and none is provided by design).

---

## 5. Relation to the binary-release update check

The notification channel **replaces** the old `GithubClient::get_latest_release` + `has_update` pathway on user-facing surfaces (TUI, CLI `--check-app-update`, GUI `CHECK UPDATES` button + Settings dialog). The old `GithubClient` surface is retained as `#[deprecated]` for compat-only diagnostic tooling; it no longer drives any user-visible update check.

---

## See also

- [`classic-update-core.md`](classic-update-core.md) — full `notification` module surface.
- [`yaml-update-delivery.md`](yaml-update-delivery.md) — the adjacent (payload-carrying) YAML data delivery channel.
- [`error-contract.md`](error-contract.md) — per-binding error shape conventions.
