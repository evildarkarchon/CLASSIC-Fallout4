## Why

The active `yaml-app-version-field` spec currently documents `v9.2.0-beta.1` as a well-formed `CLASSIC_Info.version` value and requires the YAML loader to accept it, while `load_main_yaml_version` / `validate_release_semver_shape` in `business-logic/classic-config-core/src/shippable.rs` rejects any SemVer prerelease or build-metadata suffix. The loader matches maintainer policy (CLASSIC ships release-only SemVer and already signals prerelease status via the sibling `is_prerelease` boolean plus `version_date`); the spec is the outlier. The contradiction keeps surfacing as a release-blocker in adversarial code reviews, and GUI startup becomes fatal if a prerelease-shaped YAML value ever slips through. Tightening the spec so the contract matches the loader's existing behavior, and aligning `set_version.ps1` + schema docs in the same change, permanently resolves the mismatch.

## What Changes

- **BREAKING (spec-level):** `CLASSIC_Info.version` SHALL be bare SemVer `<MAJOR>.<MINOR>.<PATCH>` with an optional leading `v`. SemVer prerelease suffixes (`-beta.N`, `-rc.N`, `-alpha`, etc.) and build metadata (`+build.N`) are forbidden in the YAML field.
- **Replace** the "Well-formed prerelease version" scenario (loader accepts `v9.2.0-beta.1`) with a "SemVer prerelease suffix is rejected" scenario (loader returns `MainYamlVersionError::VersionInvalid`).
- **Add** a new requirement stating that prerelease release status is signaled via the sibling `is_prerelease: true|false` field (together with a bumped `version_date` in `YY.MM.DD` form), not via a SemVer suffix on `CLASSIC_Info.version`. This matches what the publish workflow already mirrors through `gh release --prerelease=true/false`.
- **Tighten** `set_version.ps1`: narrow the `-Version` `ValidatePattern` to `^\d+\.\d+\.\d+$` and rewrite SYNOPSIS / .PARAMETER / .EXAMPLE / .NOTES / `Show-Help` to instruct maintainers to use `-IsPrerelease $true` + a bumped `-Date`, never a SemVer suffix. Keep the `-IsPrerelease` parameter, the `is_prerelease` YAML write, and the defensive `-replace '[-+].*$', ''` CMake strip (documented as defense-in-depth under the new contract).
- **Update** `docs/api/classic-config-core-yaml-schema.md` `CLASSIC_Info.version` contract paragraph to match the tightened spec wording and cross-link the new requirement.
- **Confirm / extend** `business-logic/classic-config-core/src/shippable_tests.rs` so a `v9.2.0-beta.1` input asserts `MainYamlVersionError::VersionInvalid` with the expected diagnostic.
- **Non-goal:** no change to the CMake `CLASSIC_APP_VERSION` extraction regex in `classic-cli/CMakeLists.txt` (already MAJOR.MINOR.PATCH-only by maintainer policy and correct by construction), no change to `shippable.rs` loader logic (already correct), and no change to `yaml-release-publishing` / `yaml-update-delivery.md` (their "prerelease" usage is the unrelated GitHub release-flag gate).

## Capabilities

### New Capabilities

- *(none — this change only modifies an existing capability)*

### Modified Capabilities

- `yaml-app-version-field`: tighten `CLASSIC_Info.version` shape to forbid SemVer prerelease/build suffixes; replace the "Well-formed prerelease version" acceptance scenario with an explicit rejection scenario; add a new requirement that prerelease status is signaled via `is_prerelease` + `version_date`.

## Impact

- **Spec:** `openspec/specs/yaml-app-version-field/spec.md` — replacement + addition deltas.
- **Tooling:** `set_version.ps1` — narrower parameter validation, refreshed help text, comment on CMake strip.
- **Docs:** `docs/api/classic-config-core-yaml-schema.md` — paragraph rewrite + cross-link.
- **Rust tests:** `business-logic/classic-config-core/src/shippable_tests.rs` — confirm/extend a prerelease-rejection assertion.
- **No runtime-logic change** in `business-logic/classic-config-core/src/shippable.rs` — its loader and `validate_release_semver_shape` already encode the new contract.
- **No change** to `classic-cli/CMakeLists.txt`, `openspec/specs/yaml-release-publishing/spec.md`, `docs/api/yaml-update-delivery.md`, or any binding surface (Node / Python / C++).
- **Maintainer workflow:** contributors can no longer pass `-Version "X.Y.Z-beta.N"` to `set_version.ps1`; documented workflow becomes `-Version "X.Y.Z" -IsPrerelease $true -Date "YY.MM.DD"`.
- **Adversarial-review signal:** Codex / future reviewers stop flagging `validate_release_semver_shape` and the CMake strip as inconsistent with the documented contract.
