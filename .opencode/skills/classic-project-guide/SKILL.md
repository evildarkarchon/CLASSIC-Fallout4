---
name: classic-project-guide
description: CLASSIC-specific command and artifact reference for build, test, parity, publish, Windows/MSVC, PyO3, and CI follow-up workflows. Use when work needs repo-approved validation commands, binding parity artifact ownership, YAML or app-update publish tooling, native wrapper invocations, or platform-specific command choices. Do not use for generic code edits or architecture rules already covered by AGENTS.md.
---

AGENTS.md is the always-on source for CLASSIC architecture placement and hard repository rules. This skill adds bulky command recipes, parity artifact ownership, publish preflights, and CI/platform details only.

## When To Open The Reference

Read `references/repo-guide.md` selectively:

- `Command Picker` for the fastest map from touched surface to local checks.
- `Native C++ Wrappers` for CLI/GUI build, test, install, and package command forms.
- `Rust And PyO3 Commands` for workspace cargo commands and the current PyO3 shell setup.
- `Binding Parity Workflows` for CXX, Node, or Python artifact ownership and refresh commands.
- `Data Publish Workflows` for YAML database or app-update notification validation and publish preflights.
- `CI And Platform Notes` for workflow names or Windows/Linux portability constraints.

Skip this skill when AGENTS.md already answers the question and no command, generated artifact, publish, or CI detail is needed.

## Use The Reference Narrowly

- Load only the sections that match the touched surface.
- For public API or binding-facing changes, pair the relevant commands with affected `docs/api/` pages.
- In the final response, name exact commands run or skipped and call out any remaining parity artifacts, generated files, docs, packaging, submodule setup, or CI follow-up.
