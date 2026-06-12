## Why

CLASSIC's pattern/rule data (`CLASSIC Main.yaml`, `CLASSIC Fallout4.yaml`) evolves faster than the binary — new crash suspects, mod conflict entries, and FormID fixes are discovered between releases — yet today users only receive those updates by downloading a whole new build. There is no way to ship a fresh YAML dataset to an installed client, and no field in the YAML identifies its schema shape, so a naive "just download the latest file" approach would let a future schema break older clients silently. We need an update channel that (a) works without hosting infrastructure beyond GitHub, (b) requires **no bundled API key or personal access token** — end users should get updates without ever creating a GitHub account or tripping API rate limits, and (c) refuses to install a YAML file whose schema the installed binary cannot parse.

## What Changes

- Introduce an explicit `schema_version` field at the root of every shippable CLASSIC YAML file, paired with a compile-time compatibility range each client build accepts.
- Add a new Rust subsystem that, given the existing `GithubClient`, can (1) list the most recent release assets, (2) pick the newest YAML bundle whose `schema_version` falls inside the client's accepted range, (3) verify its integrity, and (4) atomically install it into a per-user cache while preserving the previously installed copy for rollback.
- Add a GitHub Actions workflow that, on a `yaml-data-v*` tag push, validates every shippable YAML file (schema-version present, parseable, sha256 recorded), publishes them — plus a `manifest.json` — as assets on a dedicated GitHub Release, **and mirrors `manifest-latest.json` to GitHub Pages** so the client's lookup path hits the Pages CDN (no API rate limit consumed) while asset downloads come from the release's `github.com/.../releases/download/...` URLs (also outside the API rate limit).
- Extend the YAML loader path resolution so that, when a cached "updated" copy exists and passes compatibility checks, it is preferred over the bundled copy; otherwise the bundled copy is used (never silently replaced).
- Add manifest metadata (schema_version ranges, sha256, release tag, published_at) to `classic-update-core` DTOs so both the Qt GUI and CLI can surface "YAML data update available" independently of binary updates.
- **BREAKING** (internal): every `-core` crate that reads these YAML files must tolerate the new `schema_version` header; older checked-in YAML files without the field must be migrated in the same change.

## Capabilities

### New Capabilities
- `yaml-schema-versioning`: Defines the `schema_version` header field, the client-side accepted-range declaration, and the compatibility check that gates loads and downloads.
- `yaml-update-delivery`: Defines the Rust client-side flow for discovering, downloading, verifying, caching, installing, and rolling back updated YAML data bundles from GitHub Releases.
- `yaml-release-publishing`: Defines the GitHub Actions workflow, release-tag convention, and release-asset layout (manifest + YAML files + checksums) used to publish YAML data updates.

### Modified Capabilities
<!-- None. We extend classic-update-core with new DTOs, but its current spec
     (update-core-error-propagation) only governs GithubClient error handling,
     which this change does not alter. New behavior is additive. -->

## Impact

- **Affected crates**: `classic-update-core` (new DTOs + download helper), `classic-config-core` / `classic-settings-core` (schema_version parsing + load-path preference), `classic-path-core` (per-user YAML cache directory resolver), new thin wrapper callable from bindings.
- **Affected binding surfaces**: CXX bridge (new `update::check_yaml_update` / `apply_yaml_update` entry points), Node (NAPI) and Python (PyO3) bindings follow automatically via the one-tier parity policy.
- **Affected UI**: `classic-gui` (new "Check for data updates" action and progress feedback), `classic-cli` (new `--check-yaml-updates` flag), optional surfacing in TUI.
- **Affected YAML content**: `CLASSIC Data/databases/CLASSIC Main.yaml` and `CLASSIC Data/databases/CLASSIC Fallout4.yaml` gain a `schema_version` header; any additional shippable files (e.g., `CLASSIC Ignore.yaml` if promoted) follow the same convention.
- **New CI asset**: `.github/workflows/publish-yaml-data.yml` (or equivalent) plus a release tag namespace (e.g., `yaml-data-vYYYY.MM.DD`) and a `gh-pages`-backed manifest mirror.
- **No runtime credentials**: the shipped client never requires a GitHub token; `GITHUB_TOKEN` remains honored if already present in a user's environment (unchanged from today) but is never necessary for the default update flow.
- **New runtime dependency direction**: HTTP download of release assets (the existing `reqwest` dependency in `classic-update-core` already covers this — no new crates are introduced).
- **User-visible behavior**: first run after a binary upgrade still loads bundled YAML; subsequent data updates land on-demand. Users without network access or with `Update Check: false` are unaffected.
- **Rollout risk**: if a schema_version range is set too narrow, users on older builds stop receiving any updates; if too wide, a breaking YAML change could ship to incompatible clients. Design must pin both sides.
