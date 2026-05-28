## Context

`CLASSIC_Info.version` in `CLASSIC Data/databases/CLASSIC Main.yaml` is the canonical application version string. It is consumed by:

- **Rust loader** `load_main_yaml_version` + `validate_release_semver_shape` in `business-logic/classic-config-core/src/shippable.rs` — enforces an optional leading `v` followed by exactly three all-digit components, and explicitly rejects SemVer prerelease (`-beta.N`) and build-metadata (`+build.N`) suffixes.
- **GUI startup** `classic-gui/src/main.cpp` — treats any `MainYamlVersionError::VersionInvalid` as fatal, so a bad YAML shape blocks launch.
- **CMake build-time guard** `classic-cli/CMakeLists.txt` — extracts `MAJOR.MINOR.PATCH` via regex for `project(VERSION ...)` and bakes it into `CLASSIC_CLI_VERSION` for runtime update classification. `project(VERSION ...)` only accepts `MAJOR.MINOR.PATCH[.TWEAK]`, so the extraction is inherently suffix-stripping.
- **`set_version.ps1`** — maintainer tooling that bumps Cargo crates, `CLASSIC Main.yaml`, and CMake project versions in lockstep. Currently accepts `^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$`, documents `8.2.0-beta.1` as a valid input, and strips the suffix before writing to CMake.
- **`openspec/specs/yaml-app-version-field/spec.md`** — the normative contract. Currently advertises `v9.2.0-beta.1` as well-formed and includes a scenario that requires the loader to accept it.

The YAML file also carries two *sibling* fields that already encode release maturity orthogonally to the version string:

- `version_date: YY.MM.DD` — the publish date; monotonic and ordinal.
- `is_prerelease: true|false` — explicit prerelease boolean.

And the publish workflow at `.github/workflows/publish-yaml-data.yml` mirrors the maturity signal at the GitHub release level via `gh release edit --prerelease=true/false`, which `fetch_from_releases_api` in `classic-update-core` filters against.

So CLASSIC already has a full, first-class prerelease-signal mechanism that does not involve the version string. The SemVer suffix the spec currently permits is *parallel and redundant* to this mechanism, and the loader chooses to reject it — which is the intentional maintainer policy captured in `project_no_semver_prerelease.md` and referenced in the `validate_release_semver_shape` inline doc comment.

The inconsistency between the spec ("accepts `v9.2.0-beta.1`") and the loader ("rejects `v9.2.0-beta.1`") is what triggers adversarial reviews to flag the loader (or the CMake strip, depending on which side they land on) as a release-blocker. The fix is to make the spec match the loader, and to update the one maintainer-facing surface that still advertises the legacy format (`set_version.ps1`) plus its cross-linked schema doc.

## Goals / Non-Goals

**Goals:**

- The normative spec, the Rust loader, the maintainer tooling, and the schema documentation all describe the same `CLASSIC_Info.version` shape: `<MAJOR>.<MINOR>.<PATCH>` with an optional leading `v`, no suffix.
- The spec explicitly names the `is_prerelease` + `version_date` sibling fields as the prerelease-status signal, so contributors and reviewers who read only the spec reach the same conclusion as readers of the code and the memory.
- Future adversarial reviews against this area find a self-consistent contract and stop re-flagging the same issue.
- Contributors who try the old `-Version "X.Y.Z-beta.N"` workflow fail fast at `set_version.ps1` parameter validation, not deep inside the loader at runtime.

**Non-Goals:**

- No change to the Rust loader (`shippable.rs`): its validator already encodes the target contract.
- No change to CMake version extraction in `classic-cli/CMakeLists.txt`: already correct by construction under the new contract.
- No change to `openspec/specs/yaml-release-publishing/spec.md` or `docs/api/yaml-update-delivery.md`: their "prerelease" usage refers to the GitHub *release-flag* gate (part of the anonymous-reachability staged rollout), which is unrelated to SemVer version shape.
- No introduction of a new YAML field or a new version-format dialect. This change narrows the permitted shape; it does not invent new syntax.
- No binding-surface change (C++, Node, Python): the shape is enforced at the loader, and bindings consume the loader's output.

## Decisions

### Decision 1: Forbid SemVer prerelease/build suffixes in `CLASSIC_Info.version`

- **Choice:** `CLASSIC_Info.version` accepts only `<MAJOR>.<MINOR>.<PATCH>` with an optional leading `v`/`V`. `-beta.N`, `-rc.N`, `-alpha`, `+build.N` are all rejected at the loader and forbidden by the spec.
- **Rationale:** Three pragmatic constraints collapse onto the same choice:
  1. CMake's `project(VERSION ...)` only accepts `MAJOR.MINOR.PATCH[.TWEAK]`. Any prerelease suffix would have to be stripped for the build guard, meaning the runtime-comparable identifier would always be the stripped form. The suffix would carry no semantic weight at the CLI update-check boundary.
  2. CLASSIC already has an explicit `is_prerelease` boolean plus a monotonic `version_date`. A SemVer suffix duplicates that signal with weaker ordering (SemVer prerelease precedence rules are non-obvious and vary by consumer) and no truth-source tie to the publish workflow's `gh release --prerelease=true/false` gate.
  3. The Rust loader already rejects the suffix form with a descriptive diagnostic, and has done so since the schema-2.0 cutover.
- **Alternatives considered:**
  - **Keep `-beta.N` permitted; make the loader accept it.** Rejected. This would require the loader to also normalize the form for `check_app_notification` classification, which compares with `semver::Version::parse` semantics — prerelease precedence against stable releases is a subtle rule that downstream code does not currently encode, and mis-classification there would silently surface as `Classification::Unknown` (the exact hazard the validator's inline doc comment calls out).
  - **Keep `-beta.N` permitted but document a canonical *publish* format that strips it before release.** Rejected. This would require every surface that reads `CLASSIC_Info.version` (GUI startup, CMake configure, bindings) to learn the same normalization rule, and the contract would depend on out-of-YAML conventions. A single narrower contract is simpler and already free of any in-tree consumer that relies on the suffix.
  - **Introduce a new parallel field such as `semver_prerelease_tag`.** Rejected as scope creep. The information is already present in `is_prerelease` + `version_date` and in the GitHub release metadata. A third channel would create new synchronization bugs.

### Decision 2: `is_prerelease` + `version_date` is the canonical prerelease-status signal

- **Choice:** The spec names `is_prerelease` (paired with `version_date`) as the prerelease mechanism, and says this explicitly in a new requirement so future readers do not have to infer it from the surrounding ecosystem.
- **Rationale:** Both fields already exist and are already written in lockstep by `set_version.ps1 -IsPrerelease $true`. The publish workflow's `gh release --prerelease` flag mirrors the same boolean. Making the spec name this relationship turns an implicit convention into a documented one — which is the piece that was missing when adversarial reviewers saw a standalone loader rejection and assumed it was a bug.
- **Alternatives considered:**
  - **Describe the prerelease mechanism only in `set_version.ps1` help text and in the memory.** Rejected because that is the current state, and it has not prevented the confusion.
  - **Defer the new requirement and only tighten the existing one.** Rejected. The confusion is specifically about "how *does* CLASSIC mark a prerelease then?" Answering that inside the spec is the load-bearing clarity.

### Decision 3: Fail the bad maintainer input at `set_version.ps1` parameter validation, not downstream

- **Choice:** Narrow `-Version`'s `ValidatePattern` to `^\d+\.\d+\.\d+$` so a `9.2.0-beta.1` input is rejected before any file is touched.
- **Rationale:** The old pattern admitted prerelease inputs; the script then wrote the suffixed value to `CLASSIC Main.yaml`, which the Rust loader would later reject at GUI startup. Moving the rejection to parameter validation surfaces the policy at the point of intent (the maintainer command line) rather than at the next build.
- **Alternatives considered:**
  - **Leave the pattern permissive but add a runtime check after regex match.** Rejected — `ValidatePattern` already gives us the right diagnostic surface for free.
  - **Accept the suffix but strip it before writing to YAML.** Rejected — hides the policy violation instead of reporting it, and would inject maintainer-facing surprise ("I typed `-beta.1` but the YAML doesn't show it").

### Decision 4: Retain the CMake `-replace '[-+].*$', ''` strip in `set_version.ps1` with a clarifying comment

- **Choice:** Keep the defense-in-depth strip, add a short comment noting that the upstream validator now prevents suffixes from reaching this path.
- **Rationale:** Deleting the strip would couple the CMake-writer's correctness to the parameter validator. If a future change loosens the validator (or someone else's script calls `Update-CMakeListsTxt` directly), the strip remains the safety net that prevents writing an invalid `project(VERSION ...)`. Cheap to keep, documents the invariant.

### Decision 5: No code change to `shippable.rs` or `classic-cli/CMakeLists.txt`

- **Choice:** Both files already match the tightened contract; the only code-shaped delta is an expanded test assertion in `shippable_tests.rs` plus the PowerShell changes. The loader's `validate_release_semver_shape` inline doc comment already cites `project_no_semver_prerelease.md` — the spec tightening retroactively makes that citation fully accurate.
- **Rationale:** Scope hygiene. The contradiction being fixed is spec-side and tooling-side, not loader-side. Editing the loader would risk introducing behavior drift in an area the spec is *already* aligning toward.

## Risks / Trade-offs

- **[Risk] External consumers of `CLASSIC Main.yaml` (third-party parsers, mirrored yaml-data fetchers) might assume SemVer prerelease is permitted** → Mitigation: the spec delta documents the bare-triple shape explicitly; the only public consumer today is CLASSIC itself plus the Pages-mirrored manifest channel, which exposes the same file the loader already rejects the suffix form in. Any third party that has been permissively parsing the field continues to work because no in-tree producer has ever shipped a suffixed value (only the now-obsolete examples in `set_version.ps1` help text suggested the form was usable).

- **[Risk] Maintainers used to typing `set_version.ps1 -Version "9.2.0-beta.1"`** → Mitigation: the refreshed `.EXAMPLE` / `Show-Help` block calls out the new workflow (`-Version "9.2.0" -IsPrerelease $true -Date "YY.MM.DD"`). The `ValidatePattern` rejection provides an immediate error at the command line; no file is modified.

- **[Risk] Future desire to signal prerelease ordering via SemVer precedence (e.g., `9.2.0-beta.1 < 9.2.0-beta.2 < 9.2.0`)** → Mitigation: `version_date` is monotonic and already ordinal for this purpose; `is_prerelease` distinguishes the `< 9.2.0` stable tier from the earlier betas. If that mechanism ever proves insufficient, a future change can add a bounded `prerelease_iteration: N` integer field without reopening this decision.

- **[Trade-off] The spec and the loader both reject `+build.N` even though build metadata is semantically "ignored" in SemVer comparisons** → Accepted. Build metadata has no caller in this project and rejecting it keeps the diagnostic surface simple.

## Migration Plan

1. **Land the spec delta first** (`openspec validate yaml-app-version-field --strict`).
2. **Update `set_version.ps1`** — tighten regex and refresh help/examples. Verify with a dry-run (`-WhatIf`) that `-Version "9.2.0"` still works.
3. **Update `docs/api/classic-config-core-yaml-schema.md`** — rewrite the `CLASSIC_Info.version` paragraph to match the new spec wording.
4. **Confirm / extend `shippable_tests.rs`** — ensure `v9.2.0-beta.1`, `9.1.0-rc.2`, and `9.1.0+build.5` all map to `MainYamlVersionError::VersionInvalid`.
5. **Run `cargo test -p classic-config-core`** to confirm no regression.
6. **Update the project memory** `project_no_semver_prerelease.md` to include the `is_prerelease` + `version_date` rationale (out-of-change but recommended follow-up so future sessions have the full story).

**Rollback:** each touched file is independently revertable. Reverting only the `set_version.ps1` change leaves the spec tightening in place — contributors would see `ValidatePattern` succeed on a suffixed input but the Rust loader would still reject the YAML at runtime. Reverting only the spec change leaves `set_version.ps1` tightened but the archived-day contract unchanged. Both partial-revert states are benign because the loader remains the source of truth.
