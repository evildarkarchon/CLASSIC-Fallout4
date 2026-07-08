# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

Configured layout: single-context.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root.
- **`docs/adr/`** for ADRs that touch the area about to be changed.

If any of these files do not exist, proceed silently. Do not flag their absence and do not suggest creating them upfront. The `/domain-modeling` skill, reached via `/grill-with-docs` and `/improve-codebase-architecture`, creates them lazily when terms or decisions actually get resolved.

## File structure

Single-context repo:

```text
/
|-- CONTEXT.md
|-- docs/
|   `-- adr/
`-- src/
```

## Use the glossary's vocabulary

When your output names a domain concept, such as in an issue title, refactor proposal, hypothesis, or test name, use the term as defined in `CONTEXT.md`. Do not drift to synonyms the glossary explicitly avoids.

If the concept you need is not in the glossary yet, that is a signal. Either you are inventing language the project does not use, or there is a real gap to note for `/domain-modeling`.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> Contradicts ADR-0007 (`example-decision`) because this proposal would change the chosen architecture.
