## ADDED Requirements

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
