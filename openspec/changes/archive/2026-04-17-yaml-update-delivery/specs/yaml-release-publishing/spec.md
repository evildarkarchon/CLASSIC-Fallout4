## ADDED Requirements

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
