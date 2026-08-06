# graphify
- **graphify** - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

The graphify skill is *not* vendored into this repository; it comes from the contributor's own
Claude install (user-level `skills/graphify/`) or an equivalent plugin. Do not point this entry at a
repo-relative `SKILL.md` path — there is none, and naming one makes the command resolve to a missing
file. Contributors without the skill installed should fall back to the `graphify` CLI directly
(`graphify query`/`path`/`explain`/`update`), as described in `AGENTS.md`.
