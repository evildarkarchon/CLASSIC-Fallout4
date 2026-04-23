## Purpose

Define the GitHub Actions publish pipeline that ships CLASSIC YAML data updates: the dedicated release-tag namespace, the pre-publish validation of every shippable YAML file, the release asset layout, the GitHub Pages mirror of the manifest, and the narrow trigger surface that keeps the workflow from being invoked by untrusted contexts.

## Requirements

### Requirement: Dedicated release tag namespace for YAML data

YAML-data-only releases SHALL use git tags that match the pattern `yaml-data-v<YYYY>.<MM>.<DD>` with an optional trailing `.<N>` suffix for same-day re-publishes, and SHALL NOT reuse any tag format used by binary releases.

#### Scenario: Valid YAML data tag

- **WHEN** a maintainer pushes the tag `yaml-data-v2026.04.17`
- **THEN** the publish workflow is triggered

#### Scenario: Same-day re-publish

- **WHEN** a maintainer pushes `yaml-data-v2026.04.17.2` after `yaml-data-v2026.04.17`
- **THEN** both tags produce independent GitHub Releases and the client treats the higher-suffix one as newer

#### Scenario: Binary-release tag does not trigger YAML publish

- **WHEN** a maintainer pushes `v9.2.0`
- **THEN** the YAML-data publish workflow does not run

### Requirement: Publish workflow validates every shippable YAML file

The workflow at `.github/workflows/publish-yaml-data.yml` (or equivalent) SHALL, for every shippable YAML file in `CLASSIC Data/databases/`, verify the file parses successfully and contains a root-level `schema_version` field matching the regex `^\d+\.\d+$` before producing any release.

#### Scenario: Workflow blocks release on missing schema_version

- **WHEN** a YAML file in `CLASSIC Data/databases/` lacks a root-level `schema_version` entry
- **THEN** the validation step fails
- **AND** no `gh release create` call is executed
- **AND** no tag is published

#### Scenario: Workflow blocks release on malformed schema_version

- **WHEN** a shippable YAML file contains `schema_version: "1.0-beta"` or `schema_version: 1.0` (unquoted number)
- **THEN** the validation step fails with a message identifying the offending file and value

### Requirement: Release assets include per-file content, checksums, and a manifest

For every triggered run, the workflow SHALL upload, as release assets, one `<filename>.yaml` per shippable file, one `<filename>.yaml.sha256` sidecar per shippable file, and exactly one `manifest.json` file whose contents match the manifest schema defined by the `yaml-update-delivery` capability.

#### Scenario: Asset set on a successful publish

- **WHEN** the workflow succeeds for `yaml-data-v2026.04.17`
- **THEN** the resulting GitHub Release has assets `CLASSIC Main.yaml`, `CLASSIC Main.yaml.sha256`, `CLASSIC Fallout4.yaml`, `CLASSIC Fallout4.yaml.sha256`, and `manifest.json`
- **AND** `manifest.json`'s `release_tag` field equals `yaml-data-v2026.04.17`
- **AND** every `sha256` value in the manifest matches the corresponding sidecar file

### Requirement: Client-visible release is gated behind anonymous asset reachability

The publish workflow SHALL NOT expose the release to API-fallback client discovery (`fetch_from_releases_api` in `classic-update-core`) until every `files[].download_url` advertised by the manifest has been confirmed reachable by an unauthenticated HTTP client. The gate SHALL be implemented by promoting the release out of draft WITH the GitHub prerelease flag set, running the anonymous reachability probe, and only then clearing the prerelease flag.

#### Scenario: Prerelease flag is set while reachability is unverified

- **WHEN** the workflow promotes the draft release to live
- **THEN** the release is published with `prerelease=true`
- **AND** the prerelease flag is cleared only after the anonymous reachability step reports success

#### Scenario: Reachability failure leaves release client-invisible

- **WHEN** the anonymous reachability probe fails or times out
- **THEN** the workflow exits non-zero
- **AND** the release remains in the `prerelease=true` state
- **AND** `fetch_from_releases_api` does not return the release to clients because its `get_all_releases(include_drafts=false, include_prereleases=false)` filter excludes prereleases

#### Scenario: Pages pointer follows the client-visibility flip, not precedes it

- **WHEN** the workflow reaches the `gh-pages` deploy step
- **THEN** the prerelease flag on the release is already cleared
- **AND** every manifest `download_url` has been confirmed anonymously reachable in a prior step

### Requirement: Published release is not marked as "latest"

The publish workflow SHALL create the release with the "latest" flag set to false (via `gh release create --latest=false`) so that the binary-release "latest" pointer remains untouched.

#### Scenario: Latest pointer preserved

- **WHEN** a YAML data release `yaml-data-v2026.04.17` is published while the latest binary release is `v9.1.0`
- **THEN** the GitHub Releases "latest" pointer still resolves to `v9.1.0`
- **AND** the YAML release is visible in the releases list but not as "latest"

### Requirement: Manifest is mirrored to GitHub Pages as the primary client lookup surface

The publish workflow SHALL, after a successful release publish, deploy the same `manifest.json` content to the repository's GitHub Pages source such that it becomes reachable at `https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json` and at a dated sibling `https://<owner>.github.io/<repo>/yaml-data/manifest-<tag>.json`. Every `files[].download_url` field in the published manifest SHALL be an absolute HTTPS URL under `github.com/<owner>/<repo>/releases/download/` pointing at that release's asset.

#### Scenario: Pages deployment accompanies a successful publish

- **WHEN** the workflow succeeds for tag `yaml-data-v2026.04.17`
- **THEN** within the workflow's `gh-pages` deploy step, `yaml-data/manifest-latest.json` is updated to the new manifest content
- **AND** `yaml-data/manifest-v2026.04.17.json` is added alongside it
- **AND** every `files[].download_url` value in the published manifest starts with `https://github.com/` and resolves to an asset on the same release

#### Scenario: Pages deployment failure aborts the publish

- **WHEN** the `gh-pages` deploy step fails
- **THEN** the workflow terminates with a non-zero exit status
- **AND** the release remains in the state produced by the prior `gh release create` call, and the workflow surfaces that the Pages mirror is out of sync

#### Scenario: Manifest download_url never points outside github.com

- **WHEN** the manifest-generation step runs
- **THEN** every `download_url` is constructed from the known `github.com/<owner>/<repo>/releases/download/<tag>/<asset>` template and URL-encoded filenames
- **AND** no external CDN or third-party host appears in the manifest

### Requirement: Workflow trigger surface is narrow

The workflow SHALL declare a trigger limited to `push` events on tags matching `yaml-data-v*` and SHALL NOT expose `pull_request` triggers or `workflow_dispatch` inputs that permit arbitrary file content to be published.

#### Scenario: Pull request does not trigger publish

- **WHEN** a pull request opens or updates against any branch
- **THEN** the publish workflow does not run

#### Scenario: Manual dispatch is either absent or restricted

- **WHEN** a maintainer opens the workflow's dispatch form (if declared)
- **THEN** the form accepts no inputs that change file content — it may accept only an already-created tag name

### Requirement: Dedicated release tag namespace for app-notification manifests

App-notification manifest releases SHALL use git tags matching the pattern `app-notification-v<MAJOR>.<MINOR>.<PATCH>` (mirroring the binary-release semantic-version scheme), and SHALL NOT reuse the `yaml-data-v*` namespace or the binary-release tag namespace. The publish workflow trigger SHALL be narrow to this tag prefix.

#### Scenario: Valid app-notification tag

- **WHEN** a maintainer pushes the tag `app-notification-v9.2.0`
- **THEN** the app-notification publish workflow (or the shared publish workflow keyed on that prefix) is triggered

#### Scenario: YAML-data tag does not trigger app-notification publish

- **WHEN** a maintainer pushes `yaml-data-v2026.04.17`
- **THEN** the app-notification publish workflow does not run

#### Scenario: Binary-release tag does not trigger app-notification publish

- **WHEN** a maintainer pushes `v9.2.0`
- **THEN** the app-notification publish workflow does not run (notification publishes SHALL be explicit, not coupled to the binary release tag)

### Requirement: App-notification publish validates manifest schema before release

The publish workflow SHALL, before producing any release, validate that the generated `app-notification.json` parses as JSON, contains a root `manifest_version` matching `^\d+\.\d+$`, contains a root `latest_version` matching semantic-version format, and contains a root `published_at` parseable as RFC 3339. Validation failure SHALL block the release.

#### Scenario: Workflow blocks release on missing required field

- **WHEN** the generated manifest lacks `latest_version` or `published_at`
- **THEN** the validation step fails and no release is produced

#### Scenario: Workflow blocks release on malformed manifest_version

- **WHEN** the generated manifest contains `manifest_version: "1"` (integer-style) or `manifest_version: "1.0-beta"`
- **THEN** validation fails with a message identifying the offending field

### Requirement: App-notification manifest is mirrored to GitHub Pages as the primary lookup surface

The publish workflow SHALL deploy `app-notification.json` (renamed on the mirror to `manifest-latest.json`) to the repository's GitHub Pages source at `https://<owner>.github.io/<repo>/app-notification/manifest-latest.json`, plus a dated sibling `https://<owner>.github.io/<repo>/app-notification/manifest-<tag>.json`. The Pages deploy SHALL accompany a successful release and SHALL be the primary client lookup surface, with GitHub Releases serving only as a fallback.

#### Scenario: Pages deployment accompanies a successful publish

- **WHEN** the workflow succeeds for tag `app-notification-v9.2.0`
- **THEN** within the workflow's `gh-pages` deploy step, `app-notification/manifest-latest.json` is updated to the new manifest content
- **AND** `app-notification/manifest-v9.2.0.json` is added alongside it

#### Scenario: App-notification Pages path is distinct from YAML-data Pages path

- **WHEN** both app-notification and yaml-data Pages mirrors exist
- **THEN** they SHALL live under disjoint path prefixes (`app-notification/` vs `yaml-data/`) so that one publish does not overwrite the other

#### Scenario: Pages deployment failure aborts the publish

- **WHEN** the `gh-pages` deploy step fails
- **THEN** the workflow terminates with a non-zero exit status

### Requirement: App-notification release is not marked as "latest"

The app-notification publish workflow SHALL create its GitHub Release with the "latest" flag set to false (via `gh release create --latest=false`) so that the binary-release "latest" pointer remains untouched.

#### Scenario: Latest pointer preserved

- **WHEN** an app-notification release `app-notification-v9.2.0` is published while the latest binary release is `v9.2.0`
- **THEN** the GitHub Releases "latest" pointer still resolves to `v9.2.0`
- **AND** the app-notification release is visible in the releases list but not as "latest"

### Requirement: App-notification publish trigger surface is narrow

The workflow SHALL declare a trigger limited to `push` events on tags matching `app-notification-v*` and SHALL NOT expose `pull_request` triggers or `workflow_dispatch` inputs that permit arbitrary content to be published.

#### Scenario: Pull request does not trigger publish

- **WHEN** a pull request opens or updates against any branch
- **THEN** the app-notification publish workflow does not run

#### Scenario: Manual dispatch is either absent or restricted

- **WHEN** a maintainer opens the workflow's dispatch form (if declared)
- **THEN** the form SHALL accept no inputs that change manifest content — it may accept only an already-created tag name
