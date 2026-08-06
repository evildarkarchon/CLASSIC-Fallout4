# Crash Log Scan Run Presentation Consolidation Brief

## Target

Give Crash Log Scan Run Display Content one Rust owner, so the CLI, GUI, TUI, and Python CLI stop writing the same statements about the same run independently. Adapters keep Display Layout and become thin renderers of core-produced display lines.

This brief deliberately does not repeat work already finished. Vocabulary Token and Display Label adoption already single-sources the naming of seven scan-run and config enums across every frontend and binding surface, enforced by `ui-applications/classic-tui/tests/shared_runtime_audit.rs`, `classic-gui/tests/test_display_label_audit.cpp`, and `classic-cli/tests/test_display_label_audit.cpp`. What remains, and what this brief covers, is sentence composition, the enum families that never adopted `Vocabulary`, and the Local Ignore recovery prompt each frontend built for itself.

## Accepted Decisions

1. Core owns Display Content; adapters own Display Layout. Both terms are defined in `CONTEXT.md`.
2. `docs/adr/0007-rust-owns-crash-log-scan-run-display-content.md` supersedes the clause of ADR-0002 that assigned presentation to adapters. Every other ADR-0002 clause stands.
3. Display Content is a flat sequence of display lines built from semantic segments. It is not a nested tree; grouping and nesting are Display Layout.
4. Core never interpolates. Counts, paths, and names are typed segment payloads, and the plural form of a counted noun is resolved once by core.
5. CLASSIC is single-language. Item 4 is not a commitment to translate; it is a refusal to make translation a rewrite.
6. Display Content is rendered before it crosses a binding seam and travels as mirrored data, because a Crash Log Scan Run Result is not clonable and cannot be held across the seam.
7. The presentation module is a new crate with a strictly one-way dependency on `classic-scanlog-core`, not a module inside it.
8. A named subset of Display Content is byte-identical across frontends and pinned by golden tests. Everything else is free.
9. `Vocabulary` adoption extends to `CrashLogScanRunStatus`, `ScanProgressPhase`, `LocalIgnoreRecoveryDecision`, and `InstalledYamlDataRole`. `ResumeErrorKind` stays token-only by design.
10. Local Ignore recovery presentation lands last, behind an explicit gate.

## Domain Decisions

**Display Content** answers *what is said*: which display lines exist, what each states, and which Display Labels, counts, paths, and names each carries. **Display Layout** answers *how it appears*: ordering, grouping, headers, colour, emphasis, truncation, widget choice, and affordances.

The boundary is testable rather than a matter of taste. If changing a frontend's code changes the *words a user reads about the run*, that frontend is holding Display Content and the code belongs in core. If it changes only where those words sit, how they are styled, or whether they are shown at all, it is Display Layout and stays where it is.

Two existing distinctions are preserved unchanged. A Vocabulary Token is machine-facing identity and is what structured output, logs, exit-code payloads, and programmatic consumers match on. A Display Label is human-facing prose that may be reworded freely. No surface substitutes one for the other, and this brief adds no exception: where a token appears in JSON today, it keeps appearing in JSON.

## Proposed Rust Shape

New crate `business-logic/classic-scan-presentation`, depending on `classic-scanlog-core` and `classic-vocabulary`. The dependency is one-way. `classic-scanlog-core` gains no dependency on this crate, which is what keeps the existing `scan_run` to `scan_run::contract` mutual dependency from growing a third participant.

```rust
/// How a display line should read in severity terms. Adapters map this to their own
/// styling; core never names a colour.
pub enum DisplaySeverity {
    Info,
    Notice,
    Warning,
    Failure,
    Success,
}

/// One typed piece of a display line.
///
/// `Text` and `Label` carry fixed prose that core owns; every other variant carries a
/// value that core refuses to splice into a sentence, so adapters can render a path as a
/// link or a count as an emphasised number without re-deriving the wording around it.
pub enum DisplaySegment {
    /// Fixed core-owned prose. Never contains a placeholder.
    Text(&'static str),
    /// A Display Label obtained from `Vocabulary::label()`.
    Label(&'static str),
    /// A count and the noun it counts. `noun` is already resolved to its singular or
    /// plural form by core, so no adapter re-decides pluralization.
    Count { value: u64, noun: &'static str },
    Path(PathBuf),
    Name(String),
    Emphasis(String),
}

pub struct DisplayLine {
    pub severity: DisplaySeverity,
    pub segments: Vec<DisplaySegment>,
}
```

Entry points take references, because `RunResult` is `Debug` but not `Clone` and its retained continuation is one-shot:

```rust
pub fn render_run_result(result: &RunResult) -> Vec<DisplayLine>;
pub fn render_event(event: &Event) -> Vec<DisplayLine>;
pub fn render_infrastructure_error(error: &InfrastructureError) -> Vec<DisplayLine>;
pub fn render_resume_error(error: &ResumeError) -> Vec<DisplayLine>;
pub fn render_local_ignore_recovery(data: &InstalledYamlDataRunData) -> RecoveryPrompt;
```

Every adapter must continue to take the continuation out of the result *before* rendering. All three native frontends already do this; the ordering becomes load-bearing rather than incidental, and the crate documents it.

```rust
/// The core-owned content of a Local Ignore recovery prompt.
///
/// `decisions` lists only the decisions core is willing to accept for this run, each
/// already marked available or not. Adapters choose the affordance — a key hint, a
/// button, a menu letter — but may not offer a decision core marked unavailable.
pub struct RecoveryPrompt {
    pub lines: Vec<DisplayLine>,
    pub decisions: Vec<RecoveryDecisionDescription>,
}

pub struct RecoveryDecisionDescription {
    pub decision: LocalIgnoreRecoveryDecision,
    pub label: &'static str,
    pub description: Vec<DisplaySegment>,
    pub available: bool,
}
```

Two changes land in `classic-scanlog-core` rather than the new crate, because they are behavior and identity, not presentation:

```rust
// business-logic/classic-scanlog-core/src/scan_run.rs
impl Vocabulary for CrashLogScanRunStatus { /* tokens unchanged; labels added */ }

// business-logic/classic-scanlog-core/src/scan_run/contract.rs
impl CrashLogScanRunContinuation {
    /// Abandon a paused Crash Log Scan Run without performing recovery.
    ///
    /// Cancels the run and then claims the continuation with a decision the run will
    /// never act on, yielding the ordinary post-discovery cancelled result and touching
    /// nothing on disk. This replaces the identical cancel-then-resume-with-placeholder
    /// sequence the CLI, GUI, and TUI each wrote for themselves.
    pub async fn abandon(
        self,
        cancellation: &Cancellation,
        observer: Option<&mut dyn Observer>,
    ) -> Result<RunResult, ResumeError>;
}
```

`ScanProgressPhase`, `LocalIgnoreRecoveryDecision`, and `InstalledYamlDataRole` gain `Vocabulary` impls in their owning modules. Existing tokens do not move; only labels are added.

## Locked Display Content Subset

Byte-identical across every frontend, pinned by golden tests:

| Locked item | Replaces |
| --- | --- |
| Terminal status prose | `classic-tui/src/scan_run.rs:301-331`, GUI `ScanRunTerminalKind` switch, CLI terminal switch |
| Infrastructure error prose | `classic-tui/src/scan_run.rs:423`, `scanrunpresentation.cpp:327`, `scan_run_cli.cpp:377`, `classic-py-cli` `commands.py` |
| Resume error prose | Per-frontend resume error rendering |
| Per-log outcome line | `classic-tui/src/scan_run.rs:366-386` and the CLI and GUI equivalents |
| Installed YAML Data block | `classic-tui/src/scan_run.rs:442`, `scan_run_cli.cpp:75`, `classic-gui/src/app/mainwindow.cpp:1579` |
| Per-event progress line | `classic-tui/src/scan_run.rs:220-230` and the CLI and GUI equivalents |
| Local Ignore recovery decision descriptions | `classic-tui/src/scan_run.rs:74-81`, CLI menu text, GUI dialog text |

Explicitly free, and expected to differ: line ordering and grouping, section headers, colour and emphasis mapping, truncation and wrapping, widget choice, collapsibility, whether a section is shown at all, and the **affordance hints** attached to a recovery decision. The CLI's `[P]` / `[R]` / `[C]` letters, the TUI's key hints, and the GUI's buttons are Display Layout. Their accompanying **descriptions** are not.

## Adapter Mapping Rules

1. An adapter renders a `DisplayLine` by concatenating its segments in order, applying its own styling per segment kind. It never reorders segments within a line.
2. An adapter may reorder, group, or omit whole lines.
3. An adapter never calls `Vocabulary::label()` for anything already carried in a `DisplaySegment::Label`. Direct label calls remain correct only where the adapter renders a domain enum outside a display line.
4. An adapter never formats a `Count` by re-deciding the noun form; it prints `value` then `noun`.
5. Structured, machine-readable output keeps Vocabulary Tokens. Display Content is for humans and never appears in a JSON payload consumers match on.
6. An adapter never offers a `RecoveryDecisionDescription` whose `available` is false.

## C++ Bridge And Native Frontends

### C++ bridge

Because C++ never holds a Rust `RunResult`, the bridge renders while the Rust value is live and carries the lines across as mirrored data. `cxx` cannot express a Rust enum with payloads, so `DisplaySegment` flattens:

```rust
// cpp-bindings/classic-cpp-bridge/src/scanner.rs — shared types
pub enum ScanRunDisplaySeverity { Info, Notice, Warning, Failure, Success }
pub enum ScanRunDisplaySegmentKind { Text, Label, Count, Path, Name, Emphasis }

pub struct ScanRunDisplaySegment {
    pub kind: ScanRunDisplaySegmentKind,
    /// Payload for `Text`, `Label`, `Name`, and `Emphasis`; for `Count` this is the
    /// core-resolved noun. Empty for `Path`.
    pub text: String,
    /// Payload for `Path`. Empty otherwise.
    pub path: String,
    /// Payload for `Count`. Zero otherwise.
    pub count: u64,
}

pub struct ScanRunDisplayLine {
    pub severity: ScanRunDisplaySeverity,
    pub segments: Vec<ScanRunDisplaySegment>,
}
```

`scan_run_contract_execute` and the continuation resume entry point gain a `display_lines: Vec<ScanRunDisplayLine>` field on their result DTO. The observer event DTO gains the same field, populated inline in `ObserverBridge::on_event` before the event reaches C++. The seven existing `scan_run_*_label` entry points stay; they remain the correct surface for labelling an enum outside a display line.

The recovery prompt crosses as `ScanRunRecoveryPrompt { lines, decisions }` with `ScanRunRecoveryDecisionDescription { decision, label, description, available }`.

### CLI

`classic-cli/src/scan_run_cli.cpp` drops its own sentence construction and renders `display_lines`. `present_cli_scan_run_execution` becomes a line renderer plus the CLI's own section ordering. `describe_cli_local_ignore_recovery` is replaced by the bridged prompt; `read_cli_local_ignore_recovery_choice` keeps its input loop, attempt limit, EOF handling, and `[P/R/C]` letters, and gains a filter so an unavailable decision is neither printed nor accepted. `CliLocalIgnoreRecoveryChoice::Cancel` maps to the new `abandon` entry point instead of the local cancel-then-resume sequence.

### GUI

`classic-gui/src/workers/scanrunpresentation.cpp` becomes a `ScanRunDisplayLine` to rich-text renderer plus the GUI's section model. The deliberate omission of `scan_run_log_disposition_label` is preserved as a Display Layout choice: the GUI keeps not showing that line. `scanworker.cpp` keeps its signal plumbing and its existing invariant errors for a missing continuation or missing prompt, and routes `ScanRunLocalIgnoreRecoveryChoice::Cancel` to `abandon`. `ScanRunInstalledYamlDataPresentation` gains the `localIgnoreResetAvailable` field it currently omits, and `promptLocalIgnoreRecoveryChoice` gains the parameter needed to withhold the reset button.

### TUI

`ui-applications/classic-tui/src/scan_run.rs` keeps `sentence_case` and its progress-weight constants — both are Display Layout — and drops `format_result`, `format_error`, `format_resume_error`, `append_installed_yaml_data_details`, and `append_setup_details` in favour of rendering display lines. It depends on `classic-scan-presentation` directly, with no FFI. `app.rs` keeps `PendingLocalIgnoreRecovery` and its overlay; `event.rs` keeps its key map, including Enter left deliberately unbound so no keypress implicitly authorizes a durable reset, and now gates keys on `RecoveryDecisionDescription::available` rather than on a hand-read flag.

## Node And Python Bindings

### Node

`node-bindings/classic-node/src/scan_run.rs` mirrors `DisplayLine` and `DisplaySegment` as napi objects with the same flattening as the bridge, following the existing `event_to_js` pattern, and applies the crate's documented identifier casing. `index.d.ts` is refreshed and the parity baseline regenerated.

### Python

`python-bindings/classic-scanlog-py/src/scan_run.rs` exposes `DisplayLine` and `DisplaySegment` as pyo3 classes alongside the existing result and event DTOs, with `.pyi` stubs and a regenerated parity baseline. `classic-py-cli` then renders display lines instead of building its own sentences.

## Local Ignore Recovery Phase

This phase does not start until all four conditions hold:

1. The render phase has landed in the TUI, CLI, GUI, and `classic-py-cli`.
2. Golden tests pass for every locked item in the subset table.
3. All three parity gates are green against regenerated baselines.
4. A non-blocking GUI recovery prompt path is demonstrated. **Satisfied** — see `docs/implementation/qt_recovery_prompt_nonblocking_spike.md`.

Condition 4 was the real risk and is why the phase is separated. The CLI blocks on `std::getline` and the TUI owns its render loop, but `ScanWorker` runs its prompt as an injected callable that must not block the Qt event loop. If the shared prompt could not be driven without blocking, that would have been a design finding that stopped this phase rather than surfacing mid-implementation.

It can. The GUI thread never stops servicing its event queue while the prompt is open: `Qt::BlockingQueuedConnection` parks the *worker* thread, and `QMessageBox::exec()` runs a *nested* loop on the GUI thread rather than suspending it. The spike pins this at `classic-gui/tests/test_recoverypromptnonblocking.cpp`. It also fixes five constraints the shared prompt must satisfy — the call stays synchronous and value-returning, its payload stays copyable and carries no continuation or `rust::Box`, rendering happens on the worker thread before the hop, the answer stays a plain enum, and the same-thread short-circuit in `makeLocalIgnoreRecoveryPrompt` must survive because `BlockingQueuedConnection` self-deadlocks without it. The prompt shape proposed above satisfies all five; the finding document has the reasoning.

### Confirmed Reset To Default Availability Gap

**Status: the user-facing half shipped ahead of this phase.** `local_ignore_reset_available` tells a frontend whether Reset To Default can succeed at all. It was originally honoured only by the TUI, while both C++ frontends offered the decision unconditionally:

- `classic-cli/src/scan_run_cli.cpp` printed `[R] Reset to default` with no branch, and `read_cli_local_ignore_recovery_choice` could not gate it even in principle — its parameters were a stream pair and a cancellation token, with no result argument. The identifier appeared **zero times** anywhere under `classic-cli/`.
- `classic-gui/src/app/localignorerecoveryprompt.cpp` added the reset button unconditionally, and `ScanRunInstalledYamlDataPresentation` mirrored every neighbouring DTO field and omitted exactly this one. Zero occurrences under `classic-gui/` either.

The CXX, Node, and Python DTOs all carry the field correctly — `cpp-bindings/classic-cpp-bridge/src/scanner.rs:833` even documents the hazard in place. The frontends simply never read it.

Core fails safely: `resume` does not check the flag, so it claims the one-shot continuation first and then returns a typed `ResumeError::LocalIgnoreResetBackupFailure`. Nothing on disk is touched. But the continuation is spent, so the user gets no scan, no repair, and no second attempt without re-running from scratch — precisely the outcome the bridge's own doc comment warns about.

Because that is a recoverability bug a user hits today, the frontend half was shipped early rather than waiting for the render phase to land. Both C++ frontends now read the fact:

- The CLI's prompt seam carries `CliLocalIgnoreRecoveryPresentation { details, reset_available }`, and `read_cli_local_ignore_recovery_choice` takes the availability as an argument. When it is false the `[R]` line is not printed, the bracketed letters narrow to `[P/C]`, and `r`/`reset` are rejected like any other unrecognized word.
- `ScanRunInstalledYamlDataPresentation` gained `localIgnoreResetAvailable`, `ScanRunLocalIgnoreRecoveryPrompt` and `promptLocalIgnoreRecoveryChoice` gained a `resetAvailable` parameter, and the reset button is not created when it is false.
- All three frontends resolve absent Installed YAML Data as *available*: a run that reported nothing has not reported a denial, and withdrawing an option on silence would regress the behaviour that shipped before the fact existed.

Adapter Mapping Rule 6 still supersedes this when the render phase lands: `RecoveryDecisionDescription::available` travels with the decision, so a frontend cannot offer an unavailable one without ignoring data placed directly in its hands. At that point the parameters described above are replaced by the bridged prompt rather than removed piecemeal.

## Implementation Order

1. **`classic-py-cli` raw token fix.** Independent, shipped separately, ahead of everything else.
2. **`Vocabulary` adoption** for `CrashLogScanRunStatus`, `ScanProgressPhase`, `LocalIgnoreRecoveryDecision`, and `InstalledYamlDataRole`. Tokens unchanged.
3. **`classic-scan-presentation` crate** with `render_run_result`, `render_event`, and the two error renderers, plus unit tests. No consumer yet.
4. **TUI migration.** Direct Rust dependency, no FFI, fastest feedback; proves the segment model before any DTO exists.
5. **Bridge DTOs and CLI migration.** The CLI is the simplest C++ consumer and shakes the DTO out before GUI threading is involved.
6. **GUI migration.**
7. **Node and Python surfaces**, then `classic-py-cli` migration. Last, because the segment taxonomy is only stable now and the baselines regenerate once.
8. **`CrashLogScanRunContinuation::abandon`** and the three call-site replacements.
9. **Recovery prompt**, gated as above.

## Tests To Add Or Update

Rust unit tests live in sibling `_tests.rs` files declared with `#[cfg(test)] #[path = "<name>_tests.rs"] mod tests;`, never inline.

Display Content wording is pinned **once**, at the `classic-scan-presentation` render functions — the only new seam this brief introduces. Per-frontend golden suites are deliberately not used: they would assert the same wording four times, so one rewording would produce four diffs and four chances to disagree, which is the drift this brief exists to remove. What a frontend must prove instead is narrower and belongs at the audit seam that already exists: that it did not reword what core handed it.

- `business-logic/classic-scan-presentation/src/lib_tests.rs` — one test per locked item, asserting exact segment sequences; a test that no `DisplaySegment::Text` payload contains a placeholder character; a test that every `Count` noun matches its value's grammatical number.
- `business-logic/classic-scanlog-core/src/scan_run/contract_tests.rs` — `abandon` yields the ordinary cancelled result, consumes the continuation exactly once, and leaves the filesystem untouched; replay yields `ResumeError::ContinuationConsumed`.
- Vocabulary conformance via `assert_vocabulary_conformance` for each newly adopted enum, plus a test that each new label differs from its token where the forms differ, matching `every_infrastructure_stage_renders_its_display_label`.
- `ui-applications/classic-tui/tests/shared_runtime_audit.rs` — extend `AUDITED_ENUMS` with the four new adopters, and add a sentence-template detector over a deny-list of domain phrases owned by the presentation crate. Scope it to that deny-list; a general "no format strings" rule would drown in false positives.

  Step 2 could only add two of the four. `ScanProgressPhase` and `InstalledYamlDataRole` are audited; `CrashLogScanRunStatus` and `LocalIgnoreRecoveryDecision` sit in a `DEFERRED_ENUMS` constant beside them with their reasons, held there by a meta-test that asserts every adopter is either audited or explicitly deferred. **The TUI migration in step 4 is what clears that list**, and nothing fails until someone does it — the deferral does not expire on its own. Moving `CrashLogScanRunStatus` across needs `format_result`'s count-bearing sentences rendered from display segments *and* the `Run status: <token>` detail line switched to its Display Label. `LocalIgnoreRecoveryDecision` needs no frontend change at all; it is deferred only because `arm_body_end`'s over-read reports a false positive on control-flow matches, so it can move as soon as that bound is tightened or the affected match is restructured.
- `classic-gui/tests/test_display_label_audit.cpp` and `classic-cli/tests/test_display_label_audit.cpp` — same deny-list detector.
- A new display-label audit for `classic-py-cli`, which has none today. Its absence is why the raw-token bug survived.
- One thin segment-renderer test per frontend — not golden wording. It asserts that segments concatenate in order, that a `Count` prints core's resolved noun rather than a re-derived one, and that a `RecoveryDecisionDescription` marked unavailable is withheld.
- One test per frontend asserting that Reset To Default is **not** offered when `available` is false. Already done for the TUI, the native CLI, and the Qt GUI, when the frontend half shipped early — the CLI test that pinned the opposite was split into an available case and an unavailable case, and the Qt dialog gained a withheld-button case. When the render phase lands these re-point from the hand-threaded availability flag onto `RecoveryDecisionDescription::available` rather than being written from scratch. `classic-py-cli` still needs its case.

## Docs To Update

- `docs/api/classic-scan-presentation.md` — new page for the crate's public surface.
- `docs/api/README.md` — index the new page and place it in the layering rationale.
- `docs/api/classic-cpp-bridge-data-entrypoints.md` — the new result DTO field, the display types, and the recovery prompt.
- `docs/api/classic-cpp-bridge-scan-progress-callback.md` — the event DTO's new field.
- `docs/api/classic-vocabulary.md` — the four new adopters in the adoption inventory, and a note that `ResumeErrorKind` is token-only by decision.
- `docs/api/classic-scanlog-core.md` — `CrashLogScanRunContinuation::abandon`.
- `CONTEXT.md` and `docs/adr/0007-rust-owns-crash-log-scan-run-display-content.md` are already updated.

## Validation Commands

Run from repo root unless stated otherwise.

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo fmt --all -- --check
cargo test -p classic-scan-presentation
cargo test -p classic-scanlog-core
cargo test -p classic-tui
```

C++ bridge and native frontends. Do not invoke C++ test binaries or raw `ctest` directly:

```powershell
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

Node, from `node-bindings/classic-node`:

```powershell
bun install
bun run dts:refresh
bun run parity:gate
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

Python, from repo root:

```powershell
uv sync --project python-bindings --inexact --group drift-guards
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

Workspace check:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

## Non-Goals

- **Translation.** No message catalogue, no locale plumbing, no runtime language selection. The model only avoids foreclosing it.
- **A nested display tree.** Grouping, sections, and collapsibility are Display Layout. If a frontend needs structure core does not express, it composes it from lines.
- **An open segment taxonomy.** The six segment kinds are fixed for v1. Each addition touches three parity baselines, so growth is a deliberate decision, never incidental.
- **A `Cancel` variant on `LocalIgnoreRecoveryDecision`.** This is the honest domain fix — three frontends independently invented the concept, which is exactly the signal that the model is short a variant — but it reshapes a type crossing five binding surfaces and would reopen ADR-0002's cancellation semantics. `abandon` encapsulates the workaround instead. Revisit separately.
- **The FCX setup vocabulary.** `check.state`, `check.kind`, `issue.severity`, and `update.kind` are four types in a different subsystem and would dominate this change. `append_setup_details` keeps its `Display`-based projection until they adopt `Vocabulary` in their own change.
- **`ResumeErrorKind` labels.** It is a stable error code, not prose. Labelling it invites rendering a code where a sentence belongs.
- **A distinct `ResumeErrorKind::LocalIgnoreResetDefaultsUnavailable`.** When Reset To Default is attempted without available defaults, core reports `LocalIgnoreResetBackupFailure` with `stage: None` even though no backup was attempted, so the user reads "backup failure" for what is really "Main YAML has no default ignore file". That mislabel is a core error-taxonomy bug, not a presentation one, and adding a variant changes a type on five binding surfaces. Once frontends stop offering unavailable resets it becomes unreachable in practice; fix it separately.
- **Breaking the `scan_run` to `scan_run::contract` cycle.** Review entry 5 owns that. This brief only avoids making it worse, by placing presentation in a separate crate.
- **Collapsing the four parallel run-status enums** in the bridge, GUI, and Python. Review entry 8 owns that cleanup; this brief supplies the `Vocabulary` impl it needs.
