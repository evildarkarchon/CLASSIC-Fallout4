# YAML Update Delivery

Contributor-facing reference for CLASSIC's YAML data update channel: how shippable YAML files are versioned, how the client discovers and installs newer copies from GitHub Releases, and how maintainers publish a new release.

This page describes the cross-crate flow introduced by the `yaml-update-delivery` OpenSpec change. For per-crate APIs, see the page for each owner crate:

- [`classic-settings-core`](classic-settings-core.md) — `SchemaVersion`, `SchemaCompat`, `extract_schema_version`, `schema_compat_check`
- [`classic-config-core`](classic-config-core.md) — config-owned `inspect_installed_yaml_data`, compatibility metadata, exact-byte identity, semantic validation, and installed candidate policy
- [`classic-path-core`](classic-path-core.md) — `yaml_cache_dir`, `ensure_yaml_cache_dir`
- [`classic-file-io-core`](classic-file-io-core.md) — `install_atomic`, `rollback`
- [`classic-update-core`](classic-update-core.md) — `yaml_update` module, first-party `check_yaml_data_update`, `apply_yaml_data_update_with_decision`, `rollback_yaml_data_update`, plus lower-level generic `check_yaml_update`, `apply_yaml_update_with_decision`, `rollback_yaml_update`, and `ApprovedUpdate`

---

## 1. The shippable-YAML contract

Every YAML file under `CLASSIC Data/databases/` that is intended to ship as a release asset is called a **shippable YAML**. Each one carries a root-level

```yaml
schema_version: "MAJOR.MINOR"
```

header. `MAJOR.MINOR` is a pair of non-negative integers matching the regex `^\d+\.\d+$`. The value is always a quoted string (unquoted `1.0` parses as a float, which the validator rejects).

The current shippable set:

| File | Governing client constant |
| --- | --- |
| `CLASSIC Data/databases/CLASSIC Main.yaml` | `classic_config_core::client_schemas::MAIN_YAML` |
| `CLASSIC Data/databases/CLASSIC Fallout4.yaml` | `classic_config_core::client_schemas::GAME_FALLOUT4_YAML` |

The authoritative list, plus per-file client-schema ranges, lives in [`CLASSIC Data/databases/client-schema-ranges.yaml`](../../CLASSIC%20Data/databases/client-schema-ranges.yaml). Adding a new shippable file requires adding an entry there.

### MAJOR / MINOR bump rules

- **MINOR bump** — the file added an optional key or value that existing clients can ignore. Existing client binaries remain compatible; the publisher may widen `max_client_schema` in `client-schema-ranges.yaml` to advertise that fact.
- **MAJOR bump** — the file removed, renamed, or reshaped a key an older client depended on. Existing client binaries stop accepting the file. Raising the client's `MAIN_YAML.accepted_major` / `GAME_FALLOUT4_YAML.accepted_major` constant is required before the new file is even parseable; contributors should bump both sides in the same change.
  - **Concrete example (2026-04):** `CLASSIC_Info.version` dropped the legacy `CLASSIC v` display prefix and became a bare SemVer string (`v9.1.0` instead of `CLASSIC v9.1.0`). The *shape* of an existing key's value changed, so `CLASSIC Main.yaml` bumped `schema_version` from `"1.0"` → `"2.0"` and `client_schemas::MAIN_YAML.accepted_major` bumped from 1 → 2 in the same commit. Full contract: [`openspec/specs/yaml-app-version-field/spec.md`](../../openspec/specs/yaml-app-version-field/spec.md).

Current additive history:

- `CLASSIC Main.yaml` `"2.0"` → `"2.1"` added optional `CLASSIC_Settings.Unsolved Logs Destination`.
- `"2.1"` → `"2.2"` expanded `CLASSIC_Info.default_settings` into the complete Rust-generated canonical User Settings mirror, including Game Setup and frontend namespaces. Older clients ignore the additive fields; the legacy template fields remain present.

Because both changes are additive, `client_schemas::MAIN_YAML` remains `SchemaCompat::new(2, 0)` while `client-schema-ranges.yaml` advertises the compatible 2.x publish range.

The drift guard (`tools/schema_version_gate.py`, wired into `ci-python-bindings.yml :: parity-gates`) fails CI whenever a checked-in YAML's `schema_version` MAJOR diverges from the governing constant's `accepted_major`, or when MINOR falls below `minimum_minor`. This catches either side drifting without the other.

The embedded default mirror has an independent content-freshness gate because the outer schema guard cannot inspect a literal scalar's settings semantics. `cargo run -p classic-user-settings-core --bin generate-user-settings-default-mirror -- --check` parses every canonical registered path and compares its exact generated text. The generator is the only supported way to edit that block; the Rust User Settings runtime never loads defaults from YAML Data.

---

## 2. Runtime flow (client side)

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. check_yaml_data_update(client, config):                       │
│      - honors `Update Check: false` (short-circuits to Disabled) │
│      - derives the first-party Pages URL from client owner/repo   │
│      - owns the `yaml-data-v*` tag namespace and schema entries   │
│      - GET canonical Pages manifest URL (If-None-Match ETag)     │
│      - fallback: GET /repos/<owner>/<repo>/releases,             │
│        filter tag prefix `yaml-data-v`, pick highest-sorted tag, │
│        download that release's manifest.json asset.              │
│      - config core inspects Installed Main/game independently,   │
│        applying exact-byte compatibility + semantic validation,  │
│        updated/previous/bundled selection, and diagnostics.      │
│      - projects selected schema + sha256 into the classifier so  │
│        content identity (not schema_version) drives freshness.   │
│      - returns UpdateAvailable | UpToDate | Disabled | Unknown.  │
├──────────────────────────────────────────────────────────────────┤
│ 2. apply_yaml_data_update_with_decision(client, config, approved):│
│      - refuses if config.enabled == false                        │
│        → UpdateError::UpdateCheckDisabled (no HTTP).             │
│      - runs a fresh first-party check to reclassify.             │
│      - compares manifest.release_tag vs approved.release_tag.    │
│        Mismatch → UpdateError::DecisionStale (no install).       │
│      - installs only files whose name appears in                 │
│        approved.file_names AND that the fresh classifier still   │
│        marks compatible. See §2b "Reviewed-decision contract".   │
│      - 2a) legacy path apply_yaml_update(client, status) is      │
│           retained for internal reuse but MUST NOT be exposed    │
│           to review-then-apply UI flows — it has no staleness    │
│           check.                                                 │
├──────────────────────────────────────────────────────────────────┤
│ 3. rollback_yaml_data_update():                                  │
│      - expands the Rust-owned first-party shippable target list   │
│      - swaps <cache>/<file> ↔ <cache>/<file>.prev per target     │
│      - groups RolledBack, NoPreviousVersion, and failures.       │
└──────────────────────────────────────────────────────────────────┘
```

The lower-level generic interface remains available for tests, unusual hosts,
and Node/Python compatibility consumers. Generic callers pass `pages_url`,
`tag_prefix`, and a caller-built `ClientSchemaSet` to
`check_yaml_update` / `apply_yaml_update_with_decision`, or a single
`file_name` to `rollback_yaml_update`. Generic checks preserve supplied
installed metadata; entries with neither a version nor digest are enriched
from compatible cache bytes first and bundled bytes second.
Native first-party callers should use the `yaml_data_*` helpers so installed
selection and channel policy stay in Rust.

### 2a. Freshness model (content identity, not `schema_version`)

`classify_manifest` answers two independent questions per file:

1. **Is the file compatible?** — `schema_compat_check(manifest, client.accepted)` plus the manifest-published `min_client_schema` / `max_client_schema` bounds. Same rules as before.
2. **Is the file fresh?** — if the installed sha256 is known, a file is fresher iff `manifest.sha256 != installed_sha256`. First-party checks always receive that digest from config inspection of the same exact bytes used for schema and semantic validation. Generic callers may omit a digest; in that compatibility case classification falls back to `manifest.schema_version > installed.schema_version`.

This is what prevents the "data-only release ships but `schema_version` is unchanged" failure mode. A release that adds new crash suspects, mod conflicts, or FormID fixes produces a different sha256, so it is always detected as fresh. Conversely, a release that bumps `schema_version` without actually changing bytes (publisher quirk) short-circuits to UpToDate, because the installed and manifest sha are identical.

The compatibility and freshness checks are distinct — a file must pass both to be install-eligible.

### 2b. Reviewed-decision contract

Review-and-apply is two logical steps separated by an unbounded amount of time (the user reads the confirmation dialog, switches tabs, goes to lunch). Between those steps the published manifest can rotate to a new `release_tag`. A naive apply that re-fetches and installs whatever the live manifest currently advertises would silently install a release the user never saw.

`ApprovedUpdate { release_tag, file_names, file_sha256 }` closes that hole. Produced from a prior `check_yaml_update` result:

- `release_tag` — the tag the user reviewed on the confirmation dialog.
- `file_names` — the canonical names of every file the user saw in the `compatible_files` list.
- `file_sha256` — the manifest-advertised digest for each approved file, aligned by index with `file_names`.

`apply_yaml_update_with_decision` enforces four gates in order:

1. `config.enabled == false` → `UpdateError::UpdateCheckDisabled` (no HTTP). Honors the `Update Check: false` setting end-to-end so a user that toggled the setting off between check and apply cannot still trigger a network install.
2. Fetch + classify the current manifest.
3. If the fresh manifest's `release_tag` differs from `approved.release_tag` → `UpdateError::DecisionStale`. Refuses to install a different release than the one the user confirmed.
4. If a fresh manifest entry keeps the same file name but advertises a different `sha256` than `approved.file_sha256[i]` → `UpdateError::DecisionDigestStale`. Same tag plus same file name is not sufficient consent when the bytes changed.
5. Install only the intersection of `approved.file_names` ∩ `fresh.compatible_files`. An approved file that is no longer in the current manifest's compatible set is reported as a failure with a `re-check required` reason rather than silently dropped.

Binding-layer contract:

- Native C++ bridge callers use `yaml_data_check_update(enabled)`, `yaml_data_apply_update(enabled, approved)`, and `yaml_data_rollback_update()`. The bridge returns the same status/apply DTO shapes as the generic functions; rollback returns an aggregate `YamlRollbackReportDto`. Typed apply errors map to stable `error_message` prefixes: `"update check disabled: ..."` and `"decision stale: ..."`. GUI / CLI consumers parse the prefix.
- The native CLI exposes those first-party operations as `--check-yaml-updates`, `--apply-yaml-updates`, and `--rollback-yaml-updates`. Check/apply open the typed `UpdatePreferencesDto`, surface User Settings validation or migration diagnostics, and pass its safety-adjusted policy bit to the update bridge; they do not interpret a raw User Settings key path. Rollback is local-only and does not perform a network check.
- The native GUI opens Update Check and the canonical `GitHub` / `Both` Update Source token as part of one revision-cohesive `GuiSettingsSnapshotDto`. The Settings dialog writes either preference only through the all-or-nothing User Settings Update preview/commit seam; cancel, validation rejection, and revision conflicts cannot partially change update policy. The YAML Data network gate continues to use the accepted `Update Check` value.
- Lower-level C++ bridge compatibility callers may still use `yaml_check_update(pages_url, tag_prefix, entries, enabled, bundled_yaml_dir)`, `yaml_apply_update(request)`, and `yaml_rollback_update(file_name)`. When an entry has `has_installed == false`, the retained bundled-directory argument supplies the fallback source after the per-user cache; an empty path keeps the native `current_exe()`-relative fallback.
- Node `applyYamlUpdate(request)` takes `JsYamlApplyRequest { pagesUrl, tagPrefix, entries, enabled, approved, bundledYamlDir? }`, where `approved` is `JsApprovedUpdate { releaseTag, fileNames, fileSha256 }`. It throws on disabled / stale. Node/Bun callers pass their package-local bundled directory so entries without installed metadata can be enriched outside the interpreter's executable tree.
- Python `apply_yaml_update(request)` takes `YamlApplyRequest(pages_url, tag_prefix, entries, enabled, approved, bundled_yaml_dir=None)`, where `approved` is `ApprovedUpdate(release_tag, file_names, file_sha256)`. It raises `RuntimeError` on disabled / stale. Python callers likewise pass the package-local bundled directory when `python.exe` cannot provide the native fallback location.

All generic compatibility seams still reserve `CLASSIC Ignore.yaml` case-insensitively. Registering it in a caller-supplied schema set cannot make it classifiable or installable, and direct rollback refuses it before cache resolution.

### Installation-root resolution

First-party checks identify one CLASSIC installation root. The binding-compatible `UpdateCheckConfig::bundled_yaml_dir` layout hint accepts either that root or its canonical `CLASSIC Data/databases` directory; native frontends may omit it because the first-party helper falls back to `current_exe().parent()`. Config inspection resolves bundled candidates only beneath `<installation_root>/CLASSIC Data/databases` and resolves the per-user update cache through `classic-path-core`.

First-party helpers translate a canonical `.../CLASSIC Data/databases` hint back to its installation root. Generic `check_yaml_update` preserves the legacy interpretation: an explicit hint names the bundled directory itself, while an omitted hint probes `CLASSIC Data/databases` beside `current_exe()`. The generic lookup runs only for entries whose installed version and digest are both absent.

### Inspection precedence

`classic_config_core::inspect_installed_yaml_data` independently selects Main and the typed game's registered data file:

1. canonical `<cache_dir>/<file>` when compatible and semantically usable;
2. `<cache_dir>/<file>.prev` only when canonical is absent, selected read-only;
3. `<installation_root>/CLASSIC Data/databases/<file>` as bundled fallback;
4. otherwise typed `NoUsableSource` with structured candidate diagnostics.

A present invalid canonical candidate never promotes or selects `.prev`. Rejected candidates are logged/returned but never deleted or rewritten. Inspection does not read Local Ignore YAML Data.

### Interrupted-install recovery inspection

If `<cache_dir>/<file>` is missing but `<cache_dir>/<file>.prev` exists, inspection may select the compatible, semantically valid previous bytes as recovery provenance. This check is side-effect-limited: it does not rename or promote the sibling. Explicit rollback remains updater-owned.

### Crash durability of the install

`install_atomic` opens the temp file and calls `sync_all()` before renaming it into `<cache_dir>/<file>`. Without this step, callers that wrote the temp file via async I/O (tokio's `write_all` + `flush`) would only drain user-space buffers; a power loss between the rename and the OS writeback could leave `<file>` existing with truncated bytes while `self_heal` refused to recover (it only restores from `.prev` when the canonical target is missing, not when it is present but corrupt). The parent-directory fsync (Unix) commits rename metadata, not data — both fsyncs are needed for crash durability.

### Cache directory

`classic_path_core::yaml_cache_dir()` resolves to:

- Windows: `%LOCALAPPDATA%\CLASSIC\yaml-cache\` (fallback `%APPDATA%\CLASSIC\yaml-cache\`)
- Other targets (source portability only): `${XDG_CACHE_HOME:-$HOME/.cache}/CLASSIC/yaml-cache/`

`ensure_yaml_cache_dir()` creates the directory if missing. `yaml_cache_dir()` without creation is used by read paths.

### Runtime and credentials

- All async work runs on the shared Tokio runtime from `classic_shared_core::get_runtime()`. No new runtimes are created anywhere in the subsystem.
- **No GitHub token is bundled with the client.** The Pages lookup is anonymous; release-asset downloads are anonymous; the API-fallback `GET /releases` is anonymous. An already-set `GITHUB_TOKEN` environment variable is honored opportunistically by `classic-update-core` for rate-limit headroom, but is never required and is never transmitted for the Pages or release-asset legs.
- `Update Check: false` in `CLASSIC_Settings.yaml` short-circuits `check_yaml_update` with `Disabled` before any HTTP call.

---

## 3. Manifest format

Each `yaml-data-v*` release publishes a `manifest.json` asset with this shape (fields abridged; canonical schema defined in the `yaml-release-publishing` spec):

```json
{
  "manifest_version": 1,
  "release_tag": "yaml-data-v2026.04.17",
  "published_at": "2026-04-17T12:00:00Z",
  "files": [
    {
      "name": "CLASSIC Main.yaml",
      "schema_version": "1.3",
      "sha256": "…",
      "size_bytes": 12345,
      "min_client_schema": "1.0",
      "max_client_schema": "1.99",
      "download_url": "https://github.com/<owner>/<repo>/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml"
    }
  ],
  "signatures": []
}
```

Rules enforced at manifest-generation time and at client-fetch time:

- `manifest_version` is `1`. Clients reject higher values as `ManifestUnsupportedVersion`.
- Every `download_url` is under `https://github.com/<owner>/<repo>/releases/download/<tag>/` with a URL-encoded asset name (e.g., spaces become `%20`). The client refuses any other host.
- `signatures` is an empty array in the Section 11 slice. Section 11a of the `yaml-update-delivery` change adds a Sigstore-bundle descriptor here after cosign signs the manifest; the Rust `SignatureDescriptor` DTO already accepts and parses that descriptor.

The authoritative runtime manifest URL is `https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json` (GitHub Pages). The anonymous `GET /repos/<owner>/<repo>/releases` path is only used when Pages is unreachable.

---

## 4. Publish flow (maintainer side)

A YAML-data release is triggered by pushing a tag matching `yaml-data-v<YYYY>.<MM>.<DD>` (or `yaml-data-v<YYYY>.<MM>.<DD>.<N>` for same-day re-publishes). The workflow at [`.github/workflows/publish-yaml-data.yml`](../../.github/workflows/publish-yaml-data.yml) runs and:

1. **Validates** every `*.yaml` under `CLASSIC Data/databases/` (`python tools/publish_yaml_data/validate.py …`). A missing or malformed `schema_version` field, or any `client-schema-ranges.yaml` entry whose `files[].name` is not a client-installable cache basename (for example `NUL.yaml`, `CON.txt`, ADS/path-like names, or trailing-dot/space forms), fails the job before any release is created.
2. **Stages checksums + manifest** (`python tools/publish_yaml_data/generate_manifest.py …`). Copies each shippable YAML to the staging dir, writes a bare-hex `.sha256` sidecar per file, generates `manifest.json` with `signatures: []`.
3. **Creates a DRAFT GitHub release** via `gh release create "$TAG" --draft --latest=false …` so the binary-release "latest" pointer is untouched and the assets are uploaded while the release is invisible to every client surface.
4. **Promotes the release to live as a PRERELEASE.** `gh release edit --draft=false --prerelease=true` flips the release into a state where anonymous asset downloads work (required for the next step) but the API-fallback client path cannot discover it — `fetch_from_releases_api` in `classic-update-core` calls `get_all_releases(include_drafts=false, include_prereleases=false)` and filters prereleases out.
5. **Verifies anonymous asset bytes** (`python tools/publish_yaml_data/verify_assets_reachable.py …`). Full unauthenticated `GET` on the release `manifest.json` asset and every `files[].download_url`, streaming SHA-256 compared to the staged manifest bytes or manifest entry `sha256`. A same-tag republish reuses the same release-asset URLs; reachability-only probes can pass while GitHub's CDN still serves stale bytes, so digest mismatches retry until the CDN catches up. Failure here keeps the release in its invisible prerelease state so API-fallback clients never observe a release whose manifest or file assets do not match the staged publish.
6. **Clears the prerelease flag** (`gh release edit --prerelease=false …`). Only at this point is the release discoverable via API fallback, and by now the manifest asset and every file asset URL are proven warm.
7. **Deploys the manifest to GitHub Pages** — checks out (or initializes) the `gh-pages` branch, writes `yaml-data/manifest-latest.json` and `yaml-data/manifest-<tag>.json`, commits, pushes. The YAML-data and app-notification publishers share the `publish-gh-pages-${{ github.repository }}` concurrency group so only one maintainer job mutates the branch at a time. If the push or smoke test fails, the workflow exits non-zero for maintainer follow-up, but the matching release is already visible to fallback clients before any Pages pointer can advance.
8. **Smoke-tests** `https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json` via `python tools/publish_yaml_data/smoke_test_pages.py --expected-body-path …`, comparing the live Pages response bytes against the staged manifest (SHA-256). Same-tag republishes can keep the same `release_tag`, so tag-only smoke tests can pass before gh-pages propagates; strict-body mode retries for up to 180s to absorb Pages propagation lag.

### One-time Pages setup (per repository)

GitHub Pages must be enabled for the repo with source = `gh-pages` branch, `/ (root)` folder. This is a manual setting in **Settings → Pages** that cannot be applied by the workflow itself. Once enabled it persists; document this in the repo's maintainer notes so a fresh fork doesn't silently break the smoke-test step on first publish.

### Secrets and permissions

The workflow uses only Actions-provided credentials:

- `GITHUB_TOKEN` (built in, minted per run, scoped to the repo) — used by `gh release create` and by the `gh-pages` push.
- `permissions: contents: write` — required to create releases and push to `gh-pages`.

No repository-level secret (`COSIGN_KEY`, `MINISIGN_KEY`, or similar) is referenced or required. **No GitHub token is ever bundled into shipped client binaries.**

---

## 5. Rollback and recovery

- **User-initiated first-party rollback** — `rollback_yaml_data_update()` expands the current first-party shippable YAML Data target list in Rust, swaps `<cache>/<file>` ↔ `<cache>/<file>.prev` per target, and groups `rolled_back`, `no_previous_version`, and `failed` outcomes. There is exactly one `.prev` generation per file; successive rollbacks return `NoPreviousVersion` after the first.
- **Lower-level rollback** — `rollback_yaml_update(file_name)` remains available for compatibility callers that intentionally name one cache file.
- **Interrupted install** — if power is lost between the two renames in `install_atomic`, config inspection can select the valid `.prev` bytes when canonical is absent. Update checks leave the sibling untouched; rollback/promotion remains an explicit updater action.
- **Checksum failure** — on sha256 mismatch during `install_atomic`, the temp file is deleted; the target and any existing `.prev` are untouched.
- **Rollback to bundled** — removing `<cache>/<file>` AND `<cache>/<file>.prev` forces the loader to fall back to the bundled copy on next load. Contributors generally should not recommend this to users since manual cache mutation is outside the atomic-install contract.
- **Publish smoke failure** — if the Pages smoke test fails after the release becomes fallback-discoverable, maintainers should inspect Pages propagation and the `gh-pages` commit. Because the prerelease flag was cleared before the Pages push, a later-propagating `manifest-latest.json` cannot point at a release hidden from API-fallback clients.

---

## 6. Where the code lives

| Concern | Path |
| --- | --- |
| `SchemaVersion` / `SchemaCompat` / `extract_schema_version` | [`business-logic/classic-settings-core/src/schema_version.rs`](../../business-logic/classic-settings-core/src/schema_version.rs) |
| `client_schemas::MAIN_YAML`, `client_schemas::GAME_FALLOUT4_YAML` | [`business-logic/classic-config-core/src/client_schemas.rs`](../../business-logic/classic-config-core/src/client_schemas.rs) |
| Installed YAML Data inspection, exact-byte identity, candidate diagnostics | [`business-logic/classic-config-core/src/installed_yaml_data.rs`](../../business-logic/classic-config-core/src/installed_yaml_data.rs) |
| `yaml_cache_dir`, `ensure_yaml_cache_dir` | [`business-logic/classic-path-core/src/lib.rs`](../../business-logic/classic-path-core/src/lib.rs) |
| `install_atomic`, `rollback` | [`business-logic/classic-file-io-core/src/lib.rs`](../../business-logic/classic-file-io-core/src/lib.rs) |
| First-party YAML Data Update Channel (`check_yaml_data_update`, `apply_yaml_data_update_with_decision`, `rollback_yaml_data_update`) plus generic `YamlManifest`, `fetch_yaml_manifest`, `check_yaml_update`, `apply_yaml_update`, `rollback_yaml_update` | [`business-logic/classic-update-core/src/yaml_update.rs`](../../business-logic/classic-update-core/src/yaml_update.rs) |
| CXX bridge first-party helpers (`yaml_data_check_update`, `yaml_data_apply_update`, `yaml_data_rollback_update`) and generic compatibility helpers (`yaml_check_update`, `yaml_apply_update`, `yaml_rollback_update`) | [`cpp-bindings/classic-cpp-bridge/src/update.rs`](../../cpp-bindings/classic-cpp-bridge/src/update.rs) |
| Typed CXX/Qt User Settings policy snapshot and atomic GUI edit seam | [`cpp-bindings/classic-cpp-bridge/src/settings.rs`](../../cpp-bindings/classic-cpp-bridge/src/settings.rs), [`classic-gui/src/core/guiusersettings.cpp`](../../classic-gui/src/core/guiusersettings.cpp) |
| Node bindings (`checkYamlUpdate`, `applyYamlUpdate`, `rollbackYamlUpdate`) | [`node-bindings/classic-node/src/update.rs`](../../node-bindings/classic-node/src/update.rs) |
| Python bindings (`check_yaml_update`, `apply_yaml_update`, `rollback_yaml_update`) | [`python-bindings/classic-update-py/src/yaml_update.rs`](../../python-bindings/classic-update-py/src/yaml_update.rs) |
| Publish workflow | [`.github/workflows/publish-yaml-data.yml`](../../.github/workflows/publish-yaml-data.yml) |
| Publish tooling | [`tools/publish_yaml_data/`](../../tools/publish_yaml_data) |
| Drift guard | [`tools/schema_version_gate.py`](../../tools/schema_version_gate.py) |
| Shippable metadata | [`CLASSIC Data/databases/client-schema-ranges.yaml`](../../CLASSIC%20Data/databases/client-schema-ranges.yaml) |
