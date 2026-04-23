## 1. Spec delta land + validate

- [x] 1.1 Confirm `openspec/changes/yaml-version-forbid-prerelease-suffix/specs/yaml-app-version-field/spec.md` exists with a `## MODIFIED Requirements` block replacing `CLASSIC_Info.version stores bare SemVer without display prefix` (dropping the `-prerelease` bracket from the version shape, removing the `Well-formed prerelease version` scenario, adding `SemVer prerelease suffix is rejected` and `SemVer build metadata is rejected` scenarios, keeping `Well-formed release version` and `Rejection of legacy decorated value`) and a `## ADDED Requirements` block for `Prerelease status is signaled via is_prerelease + version_date, not via SemVer suffix`.
- [x] 1.2 Run `openspec validate yaml-version-forbid-prerelease-suffix --strict` from repo root; confirm it reports zero errors and zero warnings for this change.
- [x] 1.3 Run `openspec diff yaml-version-forbid-prerelease-suffix` (or equivalent) and sanity-check that the emitted delta against the active `yaml-app-version-field` spec matches the intended textual edit (tightened requirement + added requirement, nothing else touched).

## 2. Update `set_version.ps1` parameter validation and help text

- [x] 2.1 In `set_version.ps1`, narrow the `-Version` `[ValidatePattern]` attribute from `^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$` to `^\d+\.\d+\.\d+$` so any `-beta.N` / `+build.N` input is rejected at parameter binding.
- [x] 2.2 Rewrite the comment-based help `.SYNOPSIS` / `.DESCRIPTION` / `.PARAMETER Version` / `.NOTES` blocks so that the documented format is `MAJOR.MINOR.PATCH` only, the `-beta.1` example is replaced with `"9.2.0" -IsPrerelease $true -Date "26.05.01"`, and the CMake-strip note is updated to reflect that the validator now blocks suffixes upstream.
- [x] 2.3 Replace the two `.EXAMPLE` blocks that reference `"8.2.0-beta.1"` with `-IsPrerelease $true` examples using a bare-triple version plus a date bump.
- [x] 2.4 Update `Show-Help` output (SYNTAX / PARAMETERS / EXAMPLES) to mirror the new comment-based help; keep the `-IsPrerelease` and `-Date` parameters prominent in the documented workflow.
- [x] 2.5 Keep `Update-CMakeListsTxt`'s `$CMakeVersion = $NewVersion -replace '[-+].*$', ''` strip intact and add a short comment on the line above it noting that it is defense-in-depth because the `-Version` `ValidatePattern` now rejects suffixed input at the entry point (cross-reference the new requirement in `yaml-app-version-field`).
- [x] 2.6 Run `.\set_version.ps1 -Version "9.2.0-beta.1" -WhatIf` from a scratch shell and confirm the parameter validator errors out *before* any "Processing" lines are printed and before any backup is written.
- [x] 2.7 Run `.\set_version.ps1 -Version "9.2.0" -Date "26.05.01" -IsPrerelease $true -WhatIf` and confirm it would write `CLASSIC_Info.version: v9.2.0`, `version_date: 26.05.01`, `is_prerelease: true` without error.

## 3. Update `docs/api/classic-config-core-yaml-schema.md`

- [x] 3.1 Rewrite the `CLASSIC_Info.version` bare-SemVer contract paragraph so it describes `<MAJOR>.<MINOR>.<PATCH>` with optional leading `v` only, explicitly names prerelease suffixes and build metadata as forbidden, and cross-links the new `is_prerelease + version_date` requirement in `openspec/specs/yaml-app-version-field/spec.md`.
- [x] 3.2 If any nearby example in the same file shows `9.2.0-beta.1` or similar, replace it with a bare-triple example.
- [x] 3.3 If the page already cross-references `openspec/specs/yaml-app-version-field/spec.md`, ensure the link still resolves after the delta archives (the path does not change, so the link survives — but verify).

## 4. Strengthen Rust loader tests

- [x] 4.1 In `business-logic/classic-config-core/src/shippable_tests.rs`, locate the existing `validate_release_semver_shape` / `load_main_yaml_version` tests. Confirm there is a case asserting that `v9.2.0-beta.1` maps to `MainYamlVersionError::VersionInvalid` with a diagnostic containing the phrase "prerelease suffixes and build metadata are not allowed" (or equivalent text from `shippable.rs`).
- [x] 4.2 Add a case (if missing) asserting that `9.1.0+build.5` also maps to `MainYamlVersionError::VersionInvalid` with a similar diagnostic.
- [x] 4.3 Add (or confirm) a case that `v9.1.0` is accepted and a case that `CLASSIC v9.1.0` is rejected with the existing "legacy `CLASSIC ` prefix" diagnostic.
- [x] 4.4 Run `cargo test -p classic-config-core --test '*' shippable` (or `cargo test -p classic-config-core shippable`) and confirm all assertions pass.

## 5. Memory + reviewer-surface follow-up

- [x] 5.1 Update the project memory `project_no_semver_prerelease.md` to include the rationale that `is_prerelease` + `version_date` (plus the `gh release --prerelease` mirror) is the canonical prerelease-status signal, so future Claude sessions do not re-derive it from context.
- [x] 5.2 Verify no other `openspec/specs/*/spec.md` outside `yaml-app-version-field` references `-beta.N` or `-rc.N` as a valid `CLASSIC_Info.version` shape. If any do, open a follow-up change; do not widen this change's scope.
- [x] 5.3 Skim `docs/api/yaml-update-delivery.md` and `openspec/specs/yaml-release-publishing/spec.md` to confirm their "prerelease" mentions remain scoped to the GitHub release-flag gate (unrelated to SemVer shape) after this change lands. No edits expected.

## 6. Pre-archive validation

- [x] 6.1 Run `openspec validate yaml-version-forbid-prerelease-suffix --strict` one more time after all edits (spec, PS1, docs, tests) are in place; confirm zero errors.
- [x] 6.2 Run `cargo build --workspace` and `cargo test -p classic-config-core` from repo root and confirm both pass.
- [x] 6.3 Stage the change set (`proposal.md`, `design.md`, `specs/yaml-app-version-field/spec.md`, `tasks.md`, `set_version.ps1`, `docs/api/classic-config-core-yaml-schema.md`, `business-logic/classic-config-core/src/shippable_tests.rs`, the memory file) for a single commit or a small sequence of commits, ready for `/opsx:verify` and `/opsx:archive`.
