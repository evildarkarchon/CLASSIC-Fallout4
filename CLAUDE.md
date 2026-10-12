# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `evildarkarchon/CLASSIC-Fallout4`. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the canonical label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Domain documentation uses a single-context layout: root `GLOSSARY.md` and root `docs/adr/`. See `docs/agents/domain.md`.

Read on demand, not up front:

- `docs/api/README.md` — index of contributor-facing API guides. Read it before changing any public Rust, bridge, GUI-consumer, or binding-facing API (AGENTS.md rule 8).
- `docs/workspace-migration-matrix.md` — legacy `ClassicLib-rs/` to repo-root path and command translation. Read it only when you hit that retired path root in older docs, specs, or tool config.

## Repository Tooling Quickstart

The Python and Node bindings are retired (ADR-0010). Python survives only as repository tooling under `tools/`, which runs from the tools-only uv project at `tools/pyproject.toml` (it holds only `ruamel.yaml` and `pytest`):

```powershell
uv sync --project tools
uv run --project tools python -m pytest tools/binding_compliance/tests -q
```

Run each tools test suite in its own pytest process; several suites share module basenames and do not collect together. The interim repository gates that CI runs directly are listed in `docs/development/repository-gates.md`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
