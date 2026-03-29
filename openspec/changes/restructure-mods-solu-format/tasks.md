## 1. Config Schema And Data Model

- [ ] 1.1 Replace `game_mods_solu` key/value storage in `classic-config-core` with structured ordered `Mods_SOLU` entry types that carry `id`, grouped `criteria`, optional `exceptions`, `name`, and `description`.
- [ ] 1.2 Implement YAML parsing for `criteria.any` and `criteria.all`, preserve entry order, and add `classic-config-core` coverage for structured entries, grouped matching inputs, and exception data.
- [ ] 1.3 Convert `CLASSIC Data/databases/CLASSIC Fallout4.yaml` and all affected Rust/Node/Python config fixtures from the legacy `Mods_SOLU` map format to the structured sequence format with stable ids.

## 2. Scanlog Detection And Report Output

- [ ] 2.1 Add a dedicated structured `Mods_SOLU` matcher in `classic-scanlog-core` that evaluates `any`/`all` criteria, suppresses matches through `exceptions`, and keeps deterministic ordering based on matched plugin ids.
- [ ] 2.2 Update orchestration/report generation to render the structured `name` and `description` fields directly instead of deriving the title from the first line of a free-form warning string.
- [ ] 2.3 Add scanlog-core tests covering successful `any` matches, failed `all` matches, exception suppression, and structured report text output for detected solution entries.

## 3. Bindings, Docs, And Validation

- [ ] 3.1 Update Python, Node, and C++ binding/config exposures so `Mods_SOLU` is returned as structured ordered entries, and refresh any generated contract artifacts or parity fixtures that depend on the old map shape.
- [ ] 3.2 Update contributor API docs for the new contract, including `docs/api/README.md`, `docs/api/classic-config-core-yaml-schema.md`, `docs/api/classic-scanlog-core.md`, and `docs/api/classic-cpp-bridge-data-entrypoints.md`.
- [ ] 3.3 Run the relevant Rust tests plus Node/Python parity or binding checks for the changed surfaces and resolve any contract mismatches introduced by the structured `Mods_SOLU` format.
