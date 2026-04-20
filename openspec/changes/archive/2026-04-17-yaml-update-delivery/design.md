## Context

CLASSIC ships two large YAML datasets — `CLASSIC Main.yaml` (meta + default settings) and `CLASSIC Fallout4.yaml` (crashgen registry, suspect patterns, mod conflict tables, FormID fixes) — bundled at build time under `CLASSIC Data/databases/`. Discoveries about new crash signatures, mod conflicts, or FormID fixes currently require either a full binary release or manual file replacement by end users.

Existing relevant infrastructure:
- `classic-update-core` already uses `reqwest` + semver to poll `GET /repos/{owner}/{repo}/releases/latest`, returns typed `GithubRelease` / `GithubAsset` DTOs, and honors an optional `GITHUB_TOKEN` to raise the 60/hr anonymous rate limit to 5,000/hr.
- `classic-settings-core` owns the YAML stream parse/merge layer (`parse_yaml_content`, `merge_yaml_documents`, `load_yaml_merged_async`).
- `classic-config-core::YamlSource` already enumerates `Game`, `GameLocal`, `Settings`, `Cache` sources — the `Cache` variant is presently reserved / TBD.
- `classic-path-core` resolves documents and game paths but does not yet provide a per-user application cache directory.
- A `.sha256` sidecar already exists for `CLASSIC Fallout4.yaml`, confirming checksum thinking but no runtime verification path.
- No field in any current YAML file identifies a schema/format version; only `CLASSIC_Info.version` exists, which tracks the binary release.

Constraints drawn from [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md):
- No new runtimes — reuse the single shared Tokio runtime from `classic-shared-core`.
- No new hosting infrastructure — GitHub only (Releases API, Actions).
- Business logic lives in Rust; C++/Node/Python surfaces stay thin wrappers gated by parity tests.
- Native targets are Windows-only (MSVC x64); Rust workspace source must remain cross-platform.
- `Update Check: false` must fully disable any network activity in this subsystem too.

## Goals / Non-Goals

**Goals:**
- Establish a durable, forward-compatible `schema_version` contract inside every shippable CLASSIC YAML file.
- Let a running client discover and install a newer YAML dataset from GitHub without binary reinstallation.
- Refuse any update whose schema the client cannot parse, without leaving the on-disk state partially modified.
- Preserve a one-step rollback to the previously installed YAML copy.
- Use only GitHub-native hosting: Releases for distribution, Actions for publishing.
- Keep all business logic in Rust; expose thin binding entry points.
- Surface "data update available" independently of "binary update available" in GUI/CLI.

**Non-Goals:**
- Shipping patches / diffs — full-file replacement is sufficient for ≤ few-hundred-KB YAML files.
- Authenticated / private distribution — releases are public; no per-user licensing or DRM.
- **Bundling any GitHub token, API key, or other credential with the client.** The default flow SHALL never require authentication to GitHub. An already-set `GITHUB_TOKEN` environment variable continues to be honored opportunistically (to the same degree as today in `classic-update-core`), but is never necessary and is never transmitted by code that only this change introduces.
- **Cryptographic signature verification of any kind.** Signing and verifying manifests — Sigstore, minisign, GPG, or any other scheme — is deferred to a dedicated follow-up OpenSpec change (tentatively `yaml-update-sigstore-verify`). This change ships unsigned manifests, which is acceptable because the payload is human-reviewable YAML data, not executable code, and every download is still integrity-checked against the manifest's sha256.
- Auto-applying updates without user consent — the system checks and prompts; install is explicit.
- Generalizing to non-YAML assets (e.g., FormID SQLite DBs) in this change — schema-versioning the YAML files is the scoped deliverable, though the delivery layer should not foreclose future expansion.
- Modifying `update-core-error-propagation` requirements — additive DTOs and helpers only.
- Supporting Linux as a deployment target (source-level portability is maintained, but Windows cache paths are the reference implementation).

## Decisions

### D-01 — Schema version format: `MAJOR.MINOR` integers

Use a simple `MAJOR.MINOR` integer pair serialized in YAML as `schema_version: "2.5"`.

- **MAJOR** increments on breaking changes (renamed/removed keys, changed value shapes).
- **MINOR** increments on additive changes (new optional keys with sensible defaults).
- Each client build declares `ACCEPTED_MAJOR: u32` and `MINIMUM_MINOR: u32` compile-time constants per file family.
- A YAML file is compatible iff `file.major == client.accepted_major && file.minor >= client.minimum_minor`.

**Alternatives considered:**
- *Full semver* (patch tier): overkill for YAML content that has no "bugfix vs feature" runtime distinction.
- *Single monotonic integer*: loses the additive-vs-breaking signal; every change would force either a client rebuild or an integer bump that blocks all older clients.
- *Git SHA or date stamp*: readable but opaque to range-checking logic.

**Rationale:** matches the existing `semver` dependency's mental model (major/minor) without importing the string-parsing complexity of full semver into every YAML file; easy to validate in a CI workflow with a regex.

### D-02 — Per-file schema, not a single project-wide schema

Each shippable YAML file (`CLASSIC Main.yaml`, `CLASSIC Fallout4.yaml`, future per-game files) carries its own independent `schema_version`. The client likewise declares accepted ranges per file family.

**Rationale:** `CLASSIC Main.yaml` and the per-game datasets evolve at different paces. A single global version would force coupled bumps and stall an additive game-file change behind an unrelated main-file rework.

### D-03 — Dedicated release tag namespace: `yaml-data-vYYYY.MM.DD[.N]`

YAML-only releases use tags beginning with `yaml-data-v`, while binary releases continue to use existing tags (e.g., `v9.1.0`). The client's YAML-update code filters releases to the `yaml-data-` prefix; the binary-update code filters to everything else.

**Alternatives considered:**
- *Reuse binary release tags and attach YAML assets there*: conflates two cadences; slow binary release cuts would block data updates.
- *Use the GitHub Releases "Latest" flag alone*: marking YAML releases as "latest" would confuse the binary update check.

**Rationale:** GitHub supports arbitrary tag-to-release mapping; filtering by prefix is cheap and makes the channel legible to humans browsing the Releases page.

### D-04 — Release asset layout

Each YAML release attaches exactly these assets:
- `manifest.json` — authoritative metadata (see D-05).
- One `<filename>.yaml` per shippable file (verbatim copy).
- One `<filename>.yaml.sha256` per file (matching the `.sha256` sidecar convention already in the repo).

The client **always fetches `manifest.json` first**, validates it against the release's advertised files, then decides what to download.

**Rationale:** keeps the GitHub API hit count low (one metadata fetch gates everything), and the sha256 sidecars remain compatible with the manual verification workflow already in the repo.

### D-05 — `manifest.json` schema

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

- `manifest_version` governs the manifest format itself (independent of per-file YAML schema).
- `min_client_schema` / `max_client_schema` let a publisher explicitly mark, e.g., "this file still works for old 1.0 clients" even if its own `schema_version` is higher.
- `download_url` is absolute and points directly at the release-asset CDN at `github.com/.../releases/download/...`. Asset downloads on that surface do **not** count against the `api.github.com` rate limit, so the client can fetch any file without needing authentication. The client never constructs asset URLs itself — it trusts only URLs listed in the manifest (mitigates a manifest-host compromise that attempts to redirect clients off GitHub).
- `signatures` is reserved as an **array** of signature descriptors so future formats can be added without a schema break. This change always emits and tolerates `signatures: []`; the signing and verification scheme is deferred to the follow-up `yaml-update-sigstore-verify` OpenSpec change and is documented there.

**Alternatives considered:** encoding all this in GitHub release body Markdown (unreliable to parse); using a YAML manifest (forces YAML-parser bootstrap before YAML-parser update — awkward).

### D-06 — Install flow: temp-write → fsync → atomic rename → retain `.prev`

```
1. Resolve target path (user YAML cache dir, see D-07).
2. Download asset to <target>.new.<tmpN> in the same directory.
3. Verify sha256 against manifest; delete temp on mismatch.
4. Rename current <target> → <target>.prev (clobbering any older .prev).
5. Rename <target>.new.<tmpN> → <target>.
6. fsync the parent directory.
```

Failure at any step before (4) leaves the previous state intact. Failure between (4) and (5) is recovered at the next startup: if `<target>` is missing and `<target>.prev` exists, the loader promotes `.prev` back to the canonical name.

**Rationale:** same-directory rename is atomic on NTFS and ext4; `.prev` gives a zero-network rollback and also doubles as the recovery source for an interrupted install. Multiple generations (e.g., `.prev.1`, `.prev.2`) are explicitly out of scope — one rollback step is enough.

### D-07 — Cache directory location

New helper in `classic-path-core`:
- Windows: `%LOCALAPPDATA%\CLASSIC\yaml-cache\` (fallback: `%APPDATA%\CLASSIC\yaml-cache\`).
- Linux / source-portability fallback: `${XDG_CACHE_HOME:-$HOME/.cache}/CLASSIC/yaml-cache/`.

The `YamlSource::Cache` variant (currently reserved) resolves to this directory plus the filename.

**Rationale:** per-user app cache is the standard Windows location for installable-but-regenerable data; avoids polluting the install directory (which may be read-only or in Program Files).

### D-08 — Loader precedence: cache > bundled, gated by schema check

`classic-config-core` load path becomes, for each shippable file:

```
1. If <cache>/<file> exists AND its schema_version is client-compatible:
     load it, record "source=cache, schema=X.Y"
2. Else:
     load the bundled <install>/CLASSIC Data/databases/<file>,
     record "source=bundled, schema=X.Y"
3. If neither exists or neither is compatible, raise a typed error.
```

An incompatible cached file is **not** silently deleted; it is logged and ignored. This gives the user the option to rebase to a compatible build without losing the cached data.

### D-09 — GitHub Actions workflow: `.github/workflows/publish-yaml-data.yml`

Trigger: push of a tag matching `yaml-data-v*`.

Steps:
1. Checkout.
2. Python validator step (reuse existing tooling style under `tools/`): parse each shippable YAML, assert `schema_version` is present and matches regex `^\d+\.\d+$`.
3. Compute sha256 for each file; write `<file>.sha256` sidecars.
4. Generate `manifest.json` from the validated data + tag name + push timestamp.
5. `gh release create <tag>` with all files attached; mark as "latest: false" so the binary-release "latest" pointer is untouched.

**Rationale:** keeps all publishing logic in-tree and auditable; any contributor can open a PR that changes YAML content, and a maintainer publishes by pushing a `yaml-data-vX` tag.

### D-10 — Rust surface placement

- Extend `classic-update-core` with:
  - `YamlManifest`, `YamlManifestFile` DTOs (serde).
  - `GithubClient::fetch_yaml_manifest(tag_filter: &str) -> Result<YamlManifest>`.
  - `YamlUpdateDecision::{NoUpdate, Compatible { files }, IncompatibleSchema { … }}`.
- New crate or new module in existing crate — recommend a **new module** inside `classic-update-core` (not a new crate) to avoid crate-count churn and to keep the HTTP client colocated with its only consumer.
- Install/verification lives in a new helper module in `classic-file-io-core` (which already owns file/hash primitives): `install_atomic(target, src_tmp, expected_sha256)`.
- Schema-version parsing/validation lives in `classic-settings-core` alongside existing YAML utilities: `extract_schema_version(doc) -> Result<SchemaVersion>`.

**Alternatives considered:** a brand-new `classic-yaml-update-core` crate — rejected because the v9.1.0 milestone is consolidating crates, not adding them.

### D-11 — Binding exposure

Via the CXX bridge, GUI/CLI call only:
- `classic::update::check_yaml_update() -> YamlUpdateStatus`
- `classic::update::apply_yaml_update(decision) -> YamlUpdateReport`
- `classic::update::rollback_yaml_update(file_name) -> bool`

Node (NAPI) and Python (PyO3) surfaces mirror these entry points automatically under the one-tier parity policy; no independent logic.

### D-12 — Opt-out and telemetry

- Honor the existing `CLASSIC_Settings.Update Check: false` flag: when false, the YAML update subsystem short-circuits with `NoUpdate` without any HTTP call.
- No separate telemetry. Log actions at `info!` / `warn!` with the existing `log` crate.

### D-13 — Manifest is hosted on GitHub Pages; API is only a fallback

The authoritative runtime manifest lookup URL is `https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json`, served from GitHub Pages. The publish workflow (D-09) writes the same `manifest.json` content as the release asset and additionally deploys a copy to the `gh-pages` branch under `yaml-data/manifest-latest.json` (and a dated sibling `yaml-data/manifest-<tag>.json` for auditability).

The client lookup sequence is:

```
1. GET  https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json
        with If-None-Match (ETag) / If-Modified-Since when a cached copy exists.
2. If (1) fails after a short timeout (e.g., 5s) OR returns an invalid
   manifest, fall back to:
   GET https://api.github.com/repos/<owner>/<repo>/releases
     -> filter tag prefix "yaml-data-v"
     -> pick highest-sorted tag
     -> download that release's manifest.json asset.
3. If both fail, surface a typed "manifest unreachable" error; do not
   mutate any cached YAML state.
```

Why each leg is rate-limit-safe:

- **Pages (primary)**: served by a GitHub-operated CDN; has its own generous limits, does **not** consume any `api.github.com` quota, and requires no authentication for public Pages sites.
- **Release-asset downloads** (both the fallback manifest download and every `download_url` in the manifest) go to `github.com/.../releases/download/...` which is **not counted against the API rate limit** at all.
- **API fallback** (leg 2) uses anonymous `GET /releases`; the 60/hr-per-IP anonymous limit is ample for a feature that checks at most once per app launch (or once per day in a background timer), and is only reached when Pages is unreachable — an already-degraded path.

Net effect: an unauthenticated client on a home IP, checking once per app launch, typically consumes **zero** units of the `api.github.com` rate limit.

**Alternatives considered:**
- *Only the Releases API*: workable but ties default UX to the 60/hr anonymous limit — enough for a single user but brittle under corporate NAT where many users share an IP.
- *jsDelivr CDN (`cdn.jsdelivr.net/gh/...`)*: fast and cache-friendly, but adds a third-party dependency and caching TTL that is hard to invalidate quickly after a publish.
- *`raw.githubusercontent.com`*: has a rate limit and is documented as not intended for production traffic.

**Rationale:** GitHub Pages is the only GitHub-native option whose rate-limit envelope is high enough to guarantee a zero-prompt user experience without any credentials. The publish workflow is already the right place to deploy it, so operational cost is a single extra job step.

## Risks / Trade-offs

- **Schema version drift between YAML and client constants** → Mitigation: CI job (`tools/`) that parses the checked-in YAML's `schema_version` against the client's declared `ACCEPTED_MAJOR` constants and fails the build on mismatch.
- **User on an old binary stops receiving updates after a major bump** → Mitigation: explicitly intended behavior; surface a user-visible message explaining "your build is too old for the latest data, update the application" instead of silent no-op.
- **GitHub API rate limit (60/hr unauthenticated)** → Mitigation: the primary manifest lookup is on GitHub Pages (D-13), which is outside the API quota; asset downloads use the release-download CDN, also outside the API quota. The anonymous `/releases` endpoint is only hit when Pages is unreachable. Cache the last-known manifest ETag locally and send `If-None-Match` on every Pages fetch to return `304 Not Modified` (zero-payload) on repeat checks.
- **GitHub Pages propagation lag after a publish** → Mitigation: Pages typically takes ≤ 2 minutes to deploy after workflow completion. This is acceptable for update delivery (users don't need second-latency on new YAML data). Document the lag in `docs/api/yaml-update-delivery.md`.
- **Pages blocked by corporate firewall / DNS policy** → Mitigation: the anonymous Releases-API fallback (D-13 leg 2) keeps the feature functional even when `*.github.io` is unreachable, at the cost of the 60/hr anonymous rate limit.
- **Partial download due to network interruption mid-install** → Mitigation: atomic rename flow (D-06) means any interruption before rename is harmless; after rename, `.prev` retains recoverable state.
- **User modifies cached YAML manually** → Mitigation: every install overwrites the cached copy. Users with local tweaks should edit the bundled file or a future `CLASSIC <Game> Local.yaml` override, not the cache.
- **Manifest poisoning (MITM on GitHub)** → Mitigation: HTTPS everywhere + sha256 verification of every downloaded asset against manifest values. Cryptographic signing is *not* installed by this change; see the deferred `yaml-update-sigstore-verify` follow-up for the signing story.
- **Workflow YAML-as-code risk** → Mitigation: the Actions workflow runs only on tag-push by maintainers; no `pull_request` trigger; no `workflow_dispatch` inputs that affect file contents.
- **Corrupted cache state surviving restarts** → Mitigation: loader validates schema_version on every startup (D-08) and falls back to bundled + `.prev` if the primary cached file is unparseable.

## Migration Plan

1. Land `schema_version: "1.0"` in every currently-checked-in shippable YAML file and bump to `"1.1"`, `"1.2"`, … as subsequent PRs introduce additive fields.
2. Ship one interim client build that *reads* `schema_version` but does not yet hit the network — proves the loader change works in isolation.
3. In a follow-up release, enable the network path (`check_yaml_update`, `apply_yaml_update`) behind the existing `Update Check` setting.
4. First `yaml-data-v*` GitHub release publishes the same content that is already bundled, exercising the publish workflow end-to-end without changing behavior for users.
5. Subsequent releases ship real data deltas.

Rollback at any stage: revert the binary PR. Cache directory retains last-known-good `.prev`, and loader falls back to bundled content automatically.

## Resolved Questions

- **Should `CLASSIC Ignore.yaml` be promoted to shippable?** — **Resolved: No.** `CLASSIC Ignore.yaml` is autogenerated at runtime per user install, not authored centrally. It is explicitly out of scope; the shippable set remains `CLASSIC Main.yaml` + `CLASSIC Fallout4.yaml`.
- **Beta / pre-release channel (`yaml-data-beta-v*`)?** — **Resolved: No, for now.** A second channel is not worthwhile until the existing program-level `is_prerelease` flag is reworked. Today, `is_prerelease` in `CLASSIC Main.yaml` disables the auto-update check entirely; adopting it for a YAML beta channel would require a similar but inverted semantics (enable a second feed), which is a broader program-wide concern and out of scope for this change. Tag namespace is held open for a future change: `yaml-data-beta-v*` is reserved but never emitted or consumed by the client shipped here.
- **Signature verification?** — **Resolved: Deferred to a dedicated follow-up OpenSpec change (tentatively `yaml-update-sigstore-verify`).** This change ships unsigned manifests. The payload is human-reviewable YAML data (not executable code), every download is sha256-verified against the manifest, and the manifest `signatures` field is reserved as an empty array so a future signing change can populate it without a schema break.
