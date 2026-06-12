## Context

The current app-update check in `business-logic/classic-update-core/src/github.rs` is direct-to-GitHub-API: `GithubClient::get_latest_release` calls `GET /repos/{owner}/{repo}/releases/latest`, parses the `tag_name`, and then `has_update` compares the stripped-`v` tag against the caller-supplied installed version. TUI/GUI/CLI and the three bindings (`cpp-bindings/classic-cpp-bridge/src/update.rs`, `node-bindings/classic-node/src/update.rs`, `python-bindings/classic-update-py/src/github.rs`) all funnel through this pathway.

Meanwhile the repository already ships a proven manifest-based delivery channel for shippable YAML data, documented in `docs/api/yaml-update-delivery.md`. That channel uses a Pages-first fetch at `https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json` with ETag caching, a Releases-API fallback gated by a `yaml-data-v*` tag prefix, and a maintainer publish workflow (`.github/workflows/publish-yaml-data.yml`) that validates, publishes, probes anonymous reachability, and mirrors to Pages. The on-disk types live in `business-logic/classic-update-core/src/yaml_update.rs` and install/rollback helpers live in `business-logic/classic-file-io-core`.

Constraints shaping the design:

- The notification channel must **not** reuse the binary-release "latest" pointer or the `yaml-data-v*` namespace; otherwise one workflow can overwrite the other.
- The notification manifest must remain **payload-free** — no SHA-256 asset checksums, no file install, no rollback. This intentionally diverges from the YAML system to keep the code path minimal.
- The three bindings already have a well-established error contract (`docs/api/error-contract.md`) that differs per language; any new error variants must propagate through that contract without collapsing them into a single shape.
- Parity gates (CXX, Node, Python) are part of the contributor flow. Any new public API must update all three baselines in the same change.
- Windows is the primary dev target; cache paths go through `classic-path-core` platform-cache helpers rather than ad-hoc directory construction.

## Goals / Non-Goals

**Goals:**

- Replace the user-visible update-check path with a manifest-driven, payload-free flow that avoids GitHub's 60 req/hr unauthenticated ceiling and avoids asset-filename string parsing.
- Reuse the **architectural shape** of `yaml_update` (Pages-first with ETag, Releases fallback, typed manifest DTO, classification step) without reusing the **payload complexity** (SHA-256, atomic install, rollback).
- Preserve a compat-only `GithubClient` path for diagnostic tooling that currently uses it, rather than deleting it in the same change and expanding scope.
- Keep the maintainer publish story isomorphic to YAML data: a narrow-tag-triggered workflow, prerelease-flagged probe, then Pages deploy — so the maintainer only learns one mental model.
- Expose a single notification-check entry point on all three bindings (CXX, Node, Python) with the per-language error contract preserved.

**Non-Goals:**

- **Auto-install** of the new CLASSIC binary. The notification is user-visible signalling only; actually downloading/installing a new release remains a manual user action.
- **Removal** of `GithubClient`. Still needed for compatibility and diagnostic use; a separate follow-up change may retire it.
- **Signed manifests.** Sigstore-style signing is documented for future work in `yaml-update-delivery.md` but isn't wired up yet; we mirror that stance rather than introducing it here.
- **Rollback or caching of the manifest beyond a single ETag.** The notification is stateless enough that a simple ETag + JSON body pair is sufficient — no `.prev` swap, no atomic install, no multi-generation history.
- **GUI polish** beyond the minimum to surface classification + display payload. Redesigning the GUI update dialog is out of scope.

## Decisions

### D-01: Payload-free manifest shape in a dedicated module

**Decision:** Add a new `business-logic/classic-update-core/src/notification.rs` module (not inside `yaml_update.rs`), with its own `AppNotificationManifest`, `AppNotificationDisplay`, `NotificationStatus`, and `NotificationError` types. Re-export the public surface from `lib.rs`.

**Why:** `yaml_update.rs` already carries `YamlManifest`, `YamlManifestFile`, `SignatureDescriptor`, `apply_yaml_update_with_decision`, and rollback logic — merging a second schema into it would couple two unrelated delivery flows and make `YamlManifest`-tied helpers accidentally reachable from notification callers. A sibling module keeps the two channels independently evolvable and keeps grep-based auditing clean (`grep -l AppNotification` vs `grep -l YamlManifest`).

**Alternatives considered:**

- *Extend `YamlManifest` with an optional `notification` field.* Rejected: couples the schemas and forces every YAML-update decoder to understand a notification block it will never use.
- *Put the notification logic into the existing `github.rs`.* Rejected: `github.rs` is the compat surface we're migrating *away* from; dumping new logic there would contaminate the deprecation boundary.

### D-02: Reuse Pages-first + ETag path as a trait or helper

**Decision:** Factor the Pages-first + ETag + conditional-GET logic out of `yaml_update.rs` into a small helper (likely in `classic-update-core/src/manifest_fetch.rs`) parameterised over manifest path segment and parsed type. Both `yaml_update` and `notification` call it.

**Why:** The fetch/ETag/fallback dance is stable and was already tested via the YAML channel. Duplicating it would be brittle — any fix to header parsing or timeout handling would need two edits. A small internal helper (generic over `serde::de::DeserializeOwned`) keeps the two channels consistent.

**Alternatives considered:**

- *Duplicate the helper inline in `notification.rs`.* Rejected for the drift reason above.
- *Introduce a full-blown trait object abstraction.* Rejected as overkill — a plain generic function with two call sites is enough; add a trait only if a third caller appears.

### D-03: Keep Releases-API fallback tag namespace distinct (`app-notification-v*`)

**Decision:** Notification releases use tag prefix `app-notification-v<SEMVER>` (e.g. `app-notification-v9.2.0`). The Releases-API fallback filters on this prefix and ignores both `yaml-data-v*` and bare `v*` (binary release) tags.

**Why:** Three tag namespaces is the contract already established by `yaml-release-publishing`: binary release `v*`, YAML data `yaml-data-v*`, and now notifications `app-notification-v*`. Collapsing the notification into the binary-release tag would force every binary release to republish a notification manifest even when nothing about the latest-available version changed (e.g., hotfix reissues, tag retags). A dedicated namespace lets maintainers cadence the two independently.

**Alternatives considered:**

- *Piggyback the notification manifest on the binary-release tag `v*`.* Rejected: makes it impossible to ship a notification-only change (e.g., deprecate an older client) without cutting a binary release.
- *Use the `yaml-data-v*` namespace.* Rejected: conflates two independent delivery channels.

### D-04: Semantic-version comparison, not string equality

**Decision:** Both "is this installed version up to date?" and "is this installed version below min_supported_version?" use `semver::Version` `PartialOrd`. The caller's installed-version string is trimmed of a leading `v`/`V` before parse, matching the existing `has_update` convention.

**Why:** The current `has_update` already does this for binary releases (`github.rs:466–471`), so keeping the convention avoids surprising consumers. Additionally, the GUI/TUI display path needs an ordering (not just equality) to distinguish "UpToDate" from "UpdateAvailable" from "installed version is *ahead* of the manifest" (which can happen on CI pre-release builds and should classify as `UpToDate`, not `UpdateAvailable`).

**Alternatives considered:**

- *String equality on `tag_name`.* Rejected: this is the current brittle behaviour we're replacing.
- *Date-based comparison on `published_at`.* Rejected: clock skew on the client plus maintainer retags makes this unreliable.

### D-05: Error propagation — new variants on existing `UpdateError`, not a separate enum

**Decision:** Extend `UpdateError` with a notification-tagged variant family (`Notification(NotificationErrorKind)` or sibling variants). Do **not** create a second top-level enum.

**Why:** The bindings already map `UpdateError` to their per-language contract (CXX sentinels, NAPI error codes, PyO3 typed exception hierarchy). Introducing a sibling `NotificationError` enum would double the mapping work and risk the two enums drifting in their `Display` output. A nested `NotificationErrorKind` keeps the public `UpdateError` ergonomic while giving callers enough structure to discriminate.

**Alternatives considered:**

- *Reuse existing `UpdateError::HttpStatus` / `UpdateError::DecodeFailed` for notification paths.* Rejected: the spec requires distinct variants so callers and tests can tell notification failures from binary-release failures.
- *Freestanding `NotificationError` enum.* Rejected as above — doubles binding mapping work.

### D-06: Cache location under `<platform-cache>/CLASSIC/app-notification/`

**Decision:** Store `manifest-latest.json` and `manifest.etag` under the platform cache directory resolved through `classic-path-core`, in a sub-path `app-notification/` that is explicitly disjoint from `yaml-cache/`.

**Why:** Keeps the notification cache separable for diagnostics (user can wipe one without the other), and disjoint naming prevents future typos where a YAML-cache cleanup accidentally nukes the notification ETag.

**Alternatives considered:**

- *Share the `yaml-cache/` directory.* Rejected for the disjoint-cleanup reason.
- *Use a user-config directory.* Rejected — cache semantics (best-effort, rebuildable) are correct here; config semantics (persistent, survives cache wipes) would be wrong.

### D-07: Single bundled PR rather than three per-binding PRs

**Decision:** Ship the Rust core, CXX/Node/Python bindings, parity-baseline refreshes, consumer migrations (TUI/GUI/CLI), docs, and maintainer workflow change in one change-set.

**Why:** The parity gate enforces one-tier-at-a-time addition of public Rust APIs across all three bindings (`docs/api/binding-parity-policy.md`). Splitting into three PRs would require gate-disabling commits between them, which contradicts the policy. The alternative — adding all three bindings simultaneously — is exactly what the one-bundled-PR approach delivers.

**Alternatives considered:**

- *Phase 1: core + CXX; Phase 2: Node; Phase 3: Python.* Rejected: each intermediate state fails the parity gate.

### D-08: Compat-only `GithubClient` retention with a deprecation comment

**Decision:** Add a module-level `//! Compat-only surface; user-facing update checks go through `notification` module.` header to `github.rs` and annotate `GithubClient::get_latest_release` with `#[deprecated(note = "...")]` pointing at `notification::check_app_notification`. Do not delete the code in this change.

**Why:** CLI diagnostic tooling and some test harnesses currently depend on `GithubClient`. Deleting it in the same change as the new API would cascade into unrelated test refactors and balloon scope. The `#[deprecated]` annotation gives contributors a warning at use-site, and a follow-up change can remove it once we've verified no other caller remains.

**Alternatives considered:**

- *Delete `GithubClient` now.* Rejected for scope-creep reasons.
- *Leave `GithubClient` untouched without a deprecation marker.* Rejected: silent retention invites accidental re-use by future contributors who grep for "update check" and land on the wrong API.

## Risks / Trade-offs

- **[Pages propagation latency]** GitHub Pages can take up to several minutes to reflect a new deploy. → Mitigation: maintainer workflow already includes a smoke-test poll against the Pages URL (pattern from `.github/workflows/publish-yaml-data.yml`, adapted for `app-notification/manifest-latest.json`). Clients that fetch during the propagation window fall through to the Releases-API fallback.
- **[Releases-fallback rate limit]** The fallback still hits `GET /repos/{owner}/{repo}/releases?per_page=100` unauthenticated. → Mitigation: Pages-first path is now the fast path, so fallback is rare. Cache the Releases-listing response briefly (e.g., 30 min in-memory) to absorb Pages outages without thrashing the fallback.
- **[Schema drift between client and manifest]** A newer manifest might add fields a client doesn't understand. → Mitigation: serde decoder tolerates unknown fields (per spec); `manifest_version` is MAJOR.MINOR so a future major bump can be rejected cleanly with a typed error.
- **[Cache corruption]** Partially-written cache files could yield malformed JSON on next load. → Mitigation: On decode failure from cache, discard cache and fetch fresh. Don't atomic-write the cache (explicit non-goal) — re-fetching is cheaper than a full rollback machinery.
- **[Installed version parse failures are silent in the current API]** The new `Unknown` classification could regress reporting quality if consumers treat it as `UpToDate`. → Mitigation: spec requires the classification to be distinct and the returned status to carry the parse error so consumers must explicitly handle it (not `match _ => "up to date"`).
- **[Binding mapping drift]** CXX/Node/Python error shapes per `error-contract.md` differ; adding notification variants invites inconsistency. → Mitigation: extend `docs/api/error-contract.md` in the same change with a notification-error row, and have the parity gate refresh catch missed entries.
- **[Maintainer footgun — wrong tag namespace]** A maintainer who tags `app-notification-v9.2.0` thinking they're shipping a binary release could confuse release dashboards. → Mitigation: the publish workflow flags the release `--latest=false` (per spec) so the binary-release "latest" pointer stays untouched regardless.

## Migration Plan

1. **Land Rust core + new `notification` module** (spec requirements: manifest schema, fetch + ETag, classification, fallback). Unit tests live at `business-logic/classic-update-core/src/notification_tests.rs` per rule 10 of `AGENTS.md`.
2. **Land CXX bridge entry point + DTO**, refresh CXX parity baseline under `cpp-bindings/classic-cpp-bridge/parity-artifacts/baseline/`.
3. **Land Node binding + `index.d.ts` refresh**, refresh Node parity baseline.
4. **Land Python binding + `.pyi` refresh**, refresh Python parity baseline.
5. **Migrate consumers**: TUI `app.rs`, GUI update controller, CLI update-check subcommand. Leave `GithubClient` in place but mark it `#[deprecated]`.
6. **Publish maintainer workflow** (`.github/workflows/publish-app-notification.yml`) mirroring the `yaml-data` one with distinct Pages path and tag prefix.
7. **Dry-run the maintainer workflow** against a throwaway `app-notification-v0.0.0-dryrun` tag to confirm Pages deploy + prerelease-gate behaviour before cutting a real notification.
8. **Update docs**: new `docs/api/app-update-notification-delivery.md`; refresh `docs/api/classic-update-core.md`, `docs/api/README.md` index, `docs/api/error-contract.md`.

**Rollback strategy:** If the notification pathway misbehaves in production, consumers can temporarily revert their call site to `GithubClient::get_latest_release` (still present as compat). The manifest and Pages mirror can remain in place with no client impact. No database or persistent-state rollback is needed because the notification channel is stateless beyond an ETag file that can be deleted.

## Open Questions

- Should the maintainer workflow for app-notification be a **new separate file** (`.github/workflows/publish-app-notification.yml`) or a **trigger-prefix extension** of the existing `publish-yaml-data.yml`? Leaning toward new file for blast-radius isolation, but a shared composite action is possible. Defer to tasks phase.
- Does the GUI want a **push-style** notification (manifest check on start-up + periodic) or **pull-style** (only when user opens "Check for updates" dialog)? Scope note: current TUI does start-up check, so mirroring that is the safe default; GUI periodic polling can be a follow-up.
- Should `min_supported_version` drive a **hard-block** on launch for deprecated clients or just display a warning? Recommend warning-only in this change — a hard-block is a behavioural shift that deserves its own proposal.
