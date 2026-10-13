# CXX Bridge Policy

Reference: [`AGENTS.md`](../../AGENTS.md) rules 3 and 4, [ADR-0010](../adr/0010-retire-python-and-node-bindings.md), [`binding-parity-overview.md`](binding-parity-overview.md).

The C++ bridge (`cpp-bindings/classic-cpp-bridge`, CXX) is the one binding
surface. The Python and Node bindings retired with ADR-0010, and with them the
one-tier parity policy that required every public `-core` symbol on every
binding. This page states what the bridge exposes now, what it never exposes,
and the gate that enforces it.

---

## Definitions

- **Production caller:** code under `classic-cli/src` or `classic-gui/src`
  that calls a bridge export. Callers in C++ unit tests, CLI integration tests,
  benches, and conformance runners are not production callers.
- **Consumer-driven bridge:** a bridge that exposes exactly what production
  callers use. It grows and shrinks with the CLI and GUI, not with the Rust
  core.
- **Orphan export:** a bridge function with no production caller, or a shared
  struct, enum, or opaque type that no surviving function's signature or fields
  reach. `cargo xtask cxx-bridge-gate` fails on any orphan export.

---

## The consumer-driven rule

The bridge exposes exactly what `classic-cli` and `classic-gui` production code
calls.

- **Add an export in the same change as its first production call site.**
  Nothing is exported ahead of need, not even for a frontend change that is
  "coming next".
- **Remove an export in the same change as its last production call.** A change
  that deletes the last caller also deletes the export.
- **One frontend's call is enough.** An export that only the CLI or only the GUI
  calls survives the same as a shared one. The two frontends do not need a
  common surface.
- **There is no "coherent API" exception.** Lopsided pairs are fine: the bridge
  keeps `log_warning` without the other log levels, and `registry_set_bool`
  without `registry_get_bool`. A sibling comes back the day a frontend calls it.
- **Conformance never keeps an export alive.** A conformance runner is not a
  production caller. When a conformance family needs an export that production
  does not, CXX leaves that family in `tests/conformance/participants.json`
  rather than keeping the export.
- **Types follow functions.** A struct, enum, or opaque type is exported only
  while a surviving export's signature or fields reach it.
- **A core change updates the bridge only where a frontend consumes the
  affected capability.** Business logic never moves into the bridge to
  compensate. Public Rust API in a `-core` crate that has no bridge caller stays
  Rust API; it does not need a bridge entry.

A removed export takes all of its bridge code with it: the `#[cxx::bridge]`
declaration, the Rust shim, DTO conversion code that only it uses, and its
cases in the module's sibling `*_tests.rs`. Conversion helpers shared with
surviving exports stay. A C++ test whose only subject is the removed export is
deleted; a test that reached production behaviour through it is rewritten onto
the production path.

---

## The never-exposed rule

Some things are never exposed, even when a frontend asks. Under
[ADR-0005](../adr/0005-semantic-autoscan-report-contributions.md) the bridge
exposes no private contribution collector, no Autoscan Report Assembly, no
report primitives, and no fragment-producing compatibility aliases. Frontends
render Display Content and never assemble reports, so a request for one of
these is a design error, not a reason to export. This boundary does not depend
on demand. The Scan Run contract manifest's `forbiddenExports`
(`tests/fixtures/crash_log_scan_run/manifest.json`) asserts that removed and
forbidden names stay absent from the Rust core and bridge source.

## Display Labels

A Display Label crosses the seam only when a frontend renders it. Adopting the
`Vocabulary` trait (see [`classic-vocabulary`](classic-vocabulary.md)) on a
core enum adds no bridge entry; a label projection is added in the same change
as the frontend code that displays it, like any other export.

---

## Gate

```powershell
cargo xtask cxx-bridge-gate
```

| | |
| --- | --- |
| Invariant | No orphan exports: every bridge function has a production caller, and every exported type is reached by a surviving function. |
| CI home | `ci-cpp.yml`, job `cxx-bridge-gate` (`windows-latest`), blocking, in parallel with `cli-tests` and `gui-tests`. The build wrappers do not call it. |
| Output | `OK: <summary>` on stdout and exit 0 on a pass. Otherwise one `path:line: rule: message` line per finding on stderr, naming the export (for example `orphan-export: function classic::message::log_debug has no caller in classic-cli/src or classic-gui/src`), then a summary, and exit 1. |

How it works:

- It parses every `#[cxx::bridge]` module in `cpp-bindings/classic-cpp-bridge/src`
  with `syn` and takes each module's namespace from the attribute's
  `namespace = "..."` argument. `extern "C++"` items (for example the scan-run
  observer callbacks the frontends implement) are not checked, but the types
  their signatures name count as reached.
- It scans the `.cpp`, `.h`, and `.hpp` files under `classic-cli/src` and
  `classic-gui/src`, with comments and string literals blanked. It accepts
  exactly two reference forms: `classic::<module>::name`, and `<alias>::name`
  after `namespace <alias> = classic::<module>;`. Any other reference to a
  bridge namespace, such as `using namespace classic::<module>;` or
  `using classic::<module>::name;`, fails as an unsupported reference form.
- It checks one direction only. A missing export is caught by the CLI and GUI
  production builds, which must pass on MSVC and clang-cl.
- There is no baseline and no waiver list. If production code reaches an export
  in a way the matcher cannot see, the matcher is widened in a reviewed change.

The gate is source-only and needs no MSVC toolchain. It is listed with the other
repository checks in [repository gates](../development/repository-gates.md).

---

## Adding or removing an export

1. **Implement the behaviour in the Rust core crate.** Business logic stays in
   Rust (AGENTS.md rule 2).
2. **Add the bridge entry** in `cpp-bindings/classic-cpp-bridge/src/`: a CXX
   shared struct for a DTO, an opaque type for stateful handles, and
   `block_on()` for async work on the shared runtime.
3. **Call it from `classic-cli/src` or `classic-gui/src` in the same change**,
   using `classic::<module>::name` or a namespace alias.
4. **Run the checks:** `cargo xtask cxx-bridge-gate`, then
   `classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test` for
   the changed consumers.

To remove an export, delete the last production call and the bridge code listed
under the consumer-driven rule together, then run the same checks. If a
conformance family enrols `cxx` with a capability that depended on the export,
update `tests/conformance/participants.json` in the same change.

For an older `ClassicLib-rs/...` instruction, use the
[`workspace migration matrix`](../workspace-migration-matrix.md).

---

## Reference

- [`AGENTS.md`](../../AGENTS.md) -- rules 3 and 4
- [`binding-parity-overview.md`](binding-parity-overview.md) -- per-crate bridge surface reference
- [`../development/repository-gates.md`](../development/repository-gates.md) -- the gate's CI home and the conformance verdict
