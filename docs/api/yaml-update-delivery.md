# YAML Update Delivery

Contributor-facing reference for CLASSIC's YAML data update channel: how shippable YAML files are versioned, how the client discovers and installs newer copies from GitHub Releases, and how maintainers publish a new release.

This page describes the cross-crate flow introduced by the `yaml-update-delivery` OpenSpec change. For per-crate APIs, see the page for each owner crate:

- [`classic-settings-core`](classic-settings-core.md) — `SchemaVersion`, `SchemaCompat`, `extract_schema_version`, `schema_compat_check`
- [`classic-config-core`](classic-config-core.md) — `client_schemas::*`, `shippable::load_shippable_yaml`
- [`classic-path-core`](classic-path-core.md) — `yaml_cache_dir`, `ensure_yaml_cache_dir`
- [`classic-file-io-core`](classic-file-io-core.md) — `install_atomic`, `rollback`
- [`classic-update-core`](classic-update-core.md) — `yaml_update` module, `check_yaml_update`, `apply_yaml_update`, `apply_yaml_update_with_decision`, `rollback_yaml_update`, `ApprovedUpdate`

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

The drift guard (`tools/schema_version_gate.py`, wired into `ci-python-bindings.yml :: parity-gates`) fails CI whenever a checked-in YAML's `schema_version` MAJOR diverges from the governing constant's `accepted_major`, or when MINOR falls below `minimum_minor`. This catches either side drifting without the other.

---

## 2. Runtime flow (client side)

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. check_yaml_update(client, pages_url, tag_prefix, current,    │
│    config):                                                      │
│      - honors `Update Check: false` (short-circuits to Disabled) │
│      - GET <pages_url>/manifest-latest.json (If-None-Match ETag) │
│      - fallback: GET /repos/<owner>/<repo>/releases,             │
│        filter tag prefix `yaml-data-`, pick highest-sorted tag,  │
│        download that release's manifest.json asset.              │
│      - enrich_installed reads on-disk bytes from                 │
│        config.bundled_yaml_dir (or current_exe() fallback) and   │
│        computes sha256 so classify uses content identity (not    │
│        schema_version) as the freshness signal — see §2a         │
│        "Freshness model" and §2c "Bundled-directory resolution". │
│      - returns UpdateAvailable | UpToDate | Disabled | Unknown.  │
├──────────────────────────────────────────────────────────────────┤
│ 2. apply_yaml_update_with_decision(client, pages_url, tag_prefix,│
│     current, config, approved):                                  │
│      - refuses if config.enabled == false                        │
│        → UpdateError::UpdateCheckDisabled (no HTTP).             │
│      - runs a fresh check_yaml_update to reclassify.             │
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
│ 3. rollback_yaml_update(file_name):                              │
│      - swaps <cache>/<file> ↔ <cache>/<file>.prev                │
│      - returns RolledBack or NoPreviousVersion.                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2a. Freshness model (content identity, not `schema_version`)

`classify_manifest` answers two independent questions per file:

1. **Is the file compatible?** — `schema_compat_check(manifest, client.accepted)` plus the manifest-published `min_client_schema` / `max_client_schema` bounds. Same rules as before.
2. **Is the file fresh?** — if the installed sha256 is known (populated by `enrich_installed` from the on-disk bytes), a file is fresher iff `manifest.sha256 != installed_sha256`. When the installed sha is not known, we fall back to `manifest.schema_version > installed.schema_version` for backward compatibility with callers that bypass `enrich_installed`.

This is what prevents the "data-only release ships but `schema_version` is unchanged" failure mode. A release that adds new crash suspects, mod conflicts, or FormID fixes produces a different sha256, so it is always detected as fresh. Conversely, a release that bumps `schema_version` without actually changing bytes (publisher quirk) short-circuits to UpToDate, because the installed and manifest sha are identical.

The compatibility and freshness checks are distinct — a file must pass both to be install-eligible.

### 2b. Reviewed-decision contract

Review-and-apply is two logical steps separated by an unbounded amount of time (the user reads the confirmation dialog, switches tabs, goes to lunch). Between those steps the published manifest can rotate to a new `release_tag`. A naive apply that re-fetches and installs whatever the live manifest currently advertises would silently install a release the user never saw.

`ApprovedUpdate { release_tag, file_names }` closes that hole. Produced from a prior `check_yaml_update` result:

- `release_tag` — the tag the user reviewed on the confirmation dialog.
- `file_names` — the canonical names of every file the user saw in the `compatible_files` list.

`apply_yaml_update_with_decision` enforces four gates in order:

1. `config.enabled == false` → `UpdateError::UpdateCheckDisabled` (no HTTP). Honors the `Update Check: false` setting end-to-end so a user that toggled the setting off between check and apply cannot still trigger a network install.
2. Fetch + classify the current manifest.
3. If the fresh manifest's `release_tag` differs from `approved.release_tag` → `UpdateError::DecisionStale`. Refuses to install a different release than the one the user confirmed.
4. Install only the intersection of `approved.file_names` ∩ `fresh.compatible_files`. An approved file that is no longer in the current manifest's compatible set is reported as a failure with a `re-check required` reason rather than silently dropped.

Binding-layer contract:

- C++ bridge `yaml_apply_update(pages_url, tag_prefix, entries, enabled, approved_release_tag, approved_file_names, bundled_yaml_dir)` returns `YamlUpdateReportDto`. Typed errors map to stable `error_message` prefixes: `"update check disabled: ..."` and `"decision stale: ..."`. GUI / CLI consumers parse the prefix. The trailing `bundled_yaml_dir` is an empty string for the native CLI / GUI (which relies on the `current_exe()` fallback).
- Node `applyYamlUpdate(pagesUrl, tagPrefix, entries, enabled, approvedReleaseTag, approvedFileNames, bundledYamlDir?)` throws on disabled / stale (propagated as NAPI `Error` with the message body). Node callers should pass the package-local install path because `current_exe()` resolves to `node.exe`.
- Python `apply_yaml_update(pages_url, tag_prefix, entries, enabled, approved_release_tag, approved_file_names, bundled_yaml_dir=None)` raises `RuntimeError` on disabled / stale. Python callers should pass a package-local install path because `current_exe()` resolves to `python.exe`.

### Bundled-directory resolution (non-native hosts)

`check_yaml_update` needs to read the currently-installed bytes of each shippable file so it can compare `sha256` against the manifest and decide whether a given entry is fresh. For native CLASSIC frontends (CLI / GUI) the directory is inferred from `current_exe()`: the CLI / GUI binaries live next to `CLASSIC Data/`, so `current_exe().parent() / "CLASSIC Data/databases"` is the right path.

For bindings hosted in an unrelated executable — the Python binding inside `python.exe`, the Node binding inside `node.exe` / `bun` — `current_exe()` points at the interpreter, not the CLASSIC install. Without an explicit override, the orchestrator cannot find the bundled file, `enrich_installed` cannot populate the installed sha, and every compatible manifest entry is misclassified as `UpdateAvailable` on a clean install. This was flagged as a `high`-severity Codex adversarial-review finding.

`UpdateCheckConfig::bundled_yaml_dir: Option<PathBuf>` is the explicit override. When `Some(path)`, `check_yaml_update` uses that directory; when `None`, it falls back to the `current_exe()`-based resolver. Native frontends keep passing an empty string (CXX) or `None` / `null` (Python / Node) and behave exactly as before. Non-native hosts must compute their package-local directory (e.g. from `__file__` in Python, `__dirname` in Node) and pass it through.

### Load precedence

At load time, `classic_config_core::shippable::load_shippable_yaml(file, compat)` chooses a source using this precedence:

1. `<cache_dir>/<file>` if it exists and its `schema_version` is compatible with `compat`.
2. Otherwise `<install>/CLASSIC Data/databases/<file>` (bundled) if its `schema_version` is compatible.
3. Otherwise a typed `NoCompatibleSource { file_name, candidates }` error.

An incompatible cached file is logged (`warn!`) and ignored, never deleted — the user can downgrade the client to recover.

### Self-heal

If `<cache_dir>/<file>` is missing but `<cache_dir>/<file>.prev` exists, the loader promotes `.prev` → canonical on next startup. This recovers interrupted installs that failed between the two renames in `install_atomic`.

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

1. **Validates** every `*.yaml` under `CLASSIC Data/databases/` (`python tools/publish_yaml_data/validate.py …`). A missing or malformed `schema_version` field fails the job before any release is created.
2. **Stages checksums + manifest** (`python tools/publish_yaml_data/generate_manifest.py …`). Copies each shippable YAML to the staging dir, writes a bare-hex `.sha256` sidecar per file, generates `manifest.json` with `signatures: []`.
3. **Creates a DRAFT GitHub release** via `gh release create "$TAG" --draft --latest=false …` so the binary-release "latest" pointer is untouched and the assets are uploaded while the release is invisible to every client surface.
4. **Promotes the release to live as a PRERELEASE.** `gh release edit --draft=false --prerelease=true` flips the release into a state where anonymous asset downloads work (required for the next step) but the API-fallback client path cannot discover it — `fetch_from_releases_api` in `classic-update-core` calls `get_all_releases(include_drafts=false, include_prereleases=false)` and filters prereleases out.
5. **Verifies anonymous asset reachability** (`python tools/publish_yaml_data/verify_assets_reachable.py …`). Ranged `GET` on every `files[].download_url` without credentials. Failure here keeps the release in its invisible prerelease state so API-fallback clients never observe a release with 404'ing assets.
6. **Clears the prerelease flag** (`gh release edit --prerelease=false …`). Only at this point is the release discoverable via API fallback, and by now every asset URL is proven warm.
7. **Deploys the manifest to GitHub Pages** — checks out (or initializes) the `gh-pages` branch, writes `yaml-data/manifest-latest.json` and `yaml-data/manifest-<tag>.json`, commits, pushes. Any `git push` failure fails the workflow so release + Pages never diverge.
8. **Smoke-tests** `https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json` via `python tools/publish_yaml_data/smoke_test_pages.py …`, retrying for up to 180s to absorb Pages propagation lag.

### One-time Pages setup (per repository)

GitHub Pages must be enabled for the repo with source = `gh-pages` branch, `/ (root)` folder. This is a manual setting in **Settings → Pages** that cannot be applied by the workflow itself. Once enabled it persists; document this in the repo's maintainer notes so a fresh fork doesn't silently break the smoke-test step on first publish.

### Secrets and permissions

The workflow uses only Actions-provided credentials:

- `GITHUB_TOKEN` (built in, minted per run, scoped to the repo) — used by `gh release create` and by the `gh-pages` push.
- `permissions: contents: write` — required to create releases and push to `gh-pages`.

No repository-level secret (`COSIGN_KEY`, `MINISIGN_KEY`, or similar) is referenced or required. **No GitHub token is ever bundled into shipped client binaries.**

---

## 5. Rollback and recovery

- **User-initiated rollback** — `rollback_yaml_update(file_name)` swaps `<cache>/<file>` ↔ `<cache>/<file>.prev` and returns `RolledBack` or `NoPreviousVersion`. There is exactly one `.prev` generation; successive rollbacks return `NoPreviousVersion` after the first.
- **Interrupted install** — if power is lost between the two renames in `install_atomic`, startup self-heal promotes `.prev` → canonical so the client never observes a missing shippable file.
- **Checksum failure** — on sha256 mismatch during `install_atomic`, the temp file is deleted; the target and any existing `.prev` are untouched.
- **Rollback to bundled** — removing `<cache>/<file>` AND `<cache>/<file>.prev` forces the loader to fall back to the bundled copy on next load. Contributors generally should not recommend this to users since manual cache mutation is outside the atomic-install contract.

---

## 6. Where the code lives

| Concern | Path |
| --- | --- |
| `SchemaVersion` / `SchemaCompat` / `extract_schema_version` | [`business-logic/classic-settings-core/src/schema_version.rs`](../../business-logic/classic-settings-core/src/schema_version.rs) |
| `client_schemas::MAIN_YAML`, `client_schemas::GAME_FALLOUT4_YAML` | [`business-logic/classic-config-core/src/client_schemas.rs`](../../business-logic/classic-config-core/src/client_schemas.rs) |
| `shippable::load_shippable_yaml` | [`business-logic/classic-config-core/src/shippable.rs`](../../business-logic/classic-config-core/src/shippable.rs) |
| `yaml_cache_dir`, `ensure_yaml_cache_dir` | [`business-logic/classic-path-core/src/lib.rs`](../../business-logic/classic-path-core/src/lib.rs) |
| `install_atomic`, `rollback` | [`business-logic/classic-file-io-core/src/lib.rs`](../../business-logic/classic-file-io-core/src/lib.rs) |
| `YamlManifest`, `fetch_yaml_manifest`, `check_yaml_update`, `apply_yaml_update`, `rollback_yaml_update` | [`business-logic/classic-update-core/src/yaml_update.rs`](../../business-logic/classic-update-core/src/yaml_update.rs) |
| CXX bridge (`yaml_check_update`, `yaml_apply_update`, `yaml_rollback_update`) | [`cpp-bindings/classic-cpp-bridge/src/update.rs`](../../cpp-bindings/classic-cpp-bridge/src/update.rs) |
| Node bindings (`checkYamlUpdate`, `applyYamlUpdate`, `rollbackYamlUpdate`) | [`node-bindings/classic-node/src/update.rs`](../../node-bindings/classic-node/src/update.rs) |
| Python bindings (`check_yaml_update`, `apply_yaml_update`, `rollback_yaml_update`) | [`python-bindings/classic-update-py/src/yaml_update.rs`](../../python-bindings/classic-update-py/src/yaml_update.rs) |
| Publish workflow | [`.github/workflows/publish-yaml-data.yml`](../../.github/workflows/publish-yaml-data.yml) |
| Publish tooling | [`tools/publish_yaml_data/`](../../tools/publish_yaml_data) |
| Drift guard | [`tools/schema_version_gate.py`](../../tools/schema_version_gate.py) |
| Shippable metadata | [`CLASSIC Data/databases/client-schema-ranges.yaml`](../../CLASSIC%20Data/databases/client-schema-ranges.yaml) |
