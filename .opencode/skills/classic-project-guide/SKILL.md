---
name: classic-project-guide
description: Use this skill for CLASSIC-specific repo guidance: deciding whether work belongs in `ClassicLib-rs`, `classic-cli`, `classic-gui`, or `deprecated/`; choosing the right repo build, test, lint, package, or CI-validation commands; checking Windows/MSVC and platform constraints; and handling Node or Python parity updates when Rust APIs touch bindings. Reach for it whenever the user asks how CLASSIC is structured, which repo workflow or release gates apply, what parity artifacts or docs must change, or how to validate changes in this repository. Skip it for generic coding, design, or debugging tasks that do not depend on CLASSIC-specific architecture or workflow.
license: MIT
compatibility: Works best with file search/read tools and terminal access for repo commands.
metadata:
  author: OpenCode
  version: "1.0"
---

Use this skill when a task needs CLASSIC-specific repo knowledge that should not live in the always-on prompt.

## What This Skill Is For

- Route work to the right part of the repo.
- Pick the right build, test, lint, and parity commands.
- Preserve repo-specific architectural rules and platform constraints.
- Recognize when documentation or parity artifacts must change with the code.

## How To Use It

1. Classify the request before editing anything.
   - `classic-cli/` -> C++ CLI frontend work.
   - `classic-gui/` -> Qt desktop frontend work.
   - `ClassicLib-rs/` -> Rust core, bindings, or shared logic.
   - `deprecated/` -> legacy Python archive; avoid new feature work unless explicitly requested.

2. Read only the relevant parts of `references/repo-guide.md`.
   - Use `Architecture Map` when deciding where code belongs.
   - Use `Build, Test, and Validation Commands` before running repo commands.
   - Use `Node API Parity Workflow` or `Python API Parity Workflow` when changing binding-exposed Rust APIs.
   - Use `CI and Platform Notes` when platform or pipeline constraints matter.

3. Apply the repo guardrails while implementing.
   - Prefer active C++ and Rust surfaces over `deprecated/`.
   - Preserve the single shared Tokio runtime; do not introduce another independent runtime.
   - Run C++ tests through CTest or the provided PowerShell wrappers, not by calling test binaries directly.
   - Keep docs in sync when architecture, public behavior, or contributor workflow changes.
   - Never write to `NUL` or `nul` as if it were a file path.

4. Match validation to the touched surface.
   - Native frontend changes usually want the repo PowerShell build/test scripts.
   - Rust changes usually want `cargo fmt`, `cargo clippy`, and relevant `cargo test` commands.
   - Binding-surface changes often require parity artifacts and binding-specific tests in the same change.

5. Call out skipped repo-specific follow-up.
   - If parity artifacts, CI-relevant checks, or docs should be updated but were not run, say so clearly in the final handoff.

## Quick Decision Rules

- If the user is adding or changing product behavior, prefer Rust core plus the C++ frontends.
- If the task touches Node bindings, treat parity gates and generated artifacts as part of the same unit of work.
- If the task touches Python bindings, remember they are legacy-support work, so avoid expanding them unless the request explicitly targets that surface.
- If Linux or cloud execution comes up, remember the native C++ apps are Windows/MSVC-oriented and some Rust crates may need subset builds.

## Output Expectations

- Be explicit about which repo surface you chose and why.
- Mention the exact validation commands that fit the changed area.
- Mention parity/doc follow-up when relevant instead of assuming the reader remembers repo policy.
