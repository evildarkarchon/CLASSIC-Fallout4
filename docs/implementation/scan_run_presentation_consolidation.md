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
pub fn render_local_ignore_recovery(data: Option<&InstalledYamlDataRunData>) -> RecoveryPrompt;
```

The last signature gained its `Option` when it was built. A caller holding `RunResult::installed_yaml_data` holds one and must do *something* when it is absent, and all three native frontends had independently written the same answer for themselves — see [Confirmed Reset To Default Availability Gap](#confirmed-reset-to-default-availability-gap), where the rule is recorded as a three-way agreement. Taking the `Option` makes it one rule rather than three, which is the move this brief makes everywhere else for prose.

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

**Landed.** `scan_run_contract_execute` and the continuation resume entry point gain a `display_lines: Vec<ScanRunDisplayLine>` field on their result DTO. The observer event DTO gains the same field, populated inline in `CxxObserverAdapter::on_event` before the event reaches C++. The seven existing `scan_run_*_label` entry points stay; they remain the correct surface for labelling an enum outside a display line.

Three details differ from the sketch above, each for a reason worth recording:

- **One field, not two.** `scan_run_contract_execute` and `scan_run_continuation_resume` both return the same `ScanRunContractExecutionResult`, so a single `display_lines` on that envelope covers the initial run and the resume alike. It is populated for all three payloads — result, infrastructure error, and resume error — and describes whichever the presence flags select. Putting it on each payload struct instead would have meant four fields saying the same thing, and four baseline rows rather than two.
- **The rendered resume failure drops the code, which stays on the DTO.** `render_resume_error` deliberately omits the stable code, and `resume_error.code` still carries it. That is the boundary the brief asks for, made visible: prose for a person, a token for a consumer.
- **Two parity-gate bugs surfaced during this work and were fixed rather than worked around.** The parser's name scan was a keyword regex over raw text, so a doc comment merely *mentioning* `enum Foo` became a contract row; three phantoms had reached the committed baseline (`definitions` twice, from "cannot share enum definitions", plus `mirroring`). Comments are now stripped before the scan, the three rows are gone, and no real row moved. Separately, `--update-baseline` mirrored the committed contract straight back, so it could never accept an added, removed, or modified item — the flag refreshed only the reports while the contributor guide documented it as the one-step way to accept an intentional bridge change. It now rewrites the contract from current source and exits `0`. Both are covered by new tests in `tools/cxx_api_parity/tests/`.

**Landed.** The recovery prompt crosses as `ScanRunRecoveryPrompt { lines, decisions }` with `ScanRunRecoveryDecisionDescription { decision, label, description, available }`, carried on `ScanRunContractExecutionResult` behind `has_recovery_prompt`. A description's segments flatten exactly as a line's do, so a frontend renders one with the renderer it already has, and the presence flag follows the `has_local_ignore_reset` convention beside it because `cxx` has no optional struct. Two rows were added to the contract and one modified; the segment taxonomy did not move.

### CLI

**Landed.** `classic-cli/src/scan_run_cli.cpp` dropped its own sentence construction for results, the two failure envelopes, per-log outcomes, the Installed YAML Data block, and per-event progress lines, and renders `display_lines` instead. `present_cli_scan_run_execution` is now a line renderer plus the CLI's own section ordering.

What the CLI kept, all of it Display Layout: section ordering, the exit codes, which event kinds earn a durable console line, and which stream a line is routed to. Its output stays plain and pipeable — the per-segment styling is deliberately the empty choice for every kind, emphasis included.

Details worth recording:

- **Event rendering migrated too**, though the ticket's acceptance list named only results, errors, resume errors, and the Installed YAML Data block. Leaving `describe_cli_scan_run_event` composing its own sentences would have left exactly the drift this work removes, in a frontend whose event DTO now carries the rendered lines. `LogQueued` and `LogPhase` are omitted whole rather than reworded, because the progress display already covers them.
- **Two failure envelopes route every line to stderr** rather than by severity. Rust marks a failure's detail lines `Info`, since they are neutral facts about the failure; routing them by severity would split one diagnostic across two streams, so redirecting stdout would separate "failed during discovery" from the path it failed on. Within a run result, lines route by severity: `Warning` and `Failure` to stderr, `Info`/`Notice`/`Success` to stdout. The cut falls at `Warning` rather than `Failure` because a run paused awaiting a Local Ignore decision carries that severity and has always reached the user on stderr; putting only `Failure` there moved it to stdout, which the first review caught.
- **A failure envelope that says nothing still says something.** Both failure renderers always produce a headline, so an empty rendered block is unreachable through the bridge — but it is guarded, because the alternative is exiting 2 in silence, which reads to a user as the process dying rather than as a run that failed. Like the missing-envelope line beside it, that sentence reports a broken bridge promise rather than anything a run said, so it stays the CLI's to write.
- **The recovery prompt now shows the whole rendered run**, including the outcome summary, where it used to show the run message plus the Installed YAML Data block. This matches the call the TUI made and for the same reason — Rust exposes that block only through `render_run_result`, and picking it back out by position would be a structural assumption about a sequence that carries no structure. It is also a known rough edge: an outcome summary reading "0 logs succeeded" before the user has decided anything is noise. It resolves properly in the gated recovery phase, when core supplies a purpose-built `RecoveryPrompt` instead.
- **The completed summary lost three lines.** Scanned, errors, and cancelled counts are stated by Rust now. What remains is `Reports`, `Unsolved`, `Duration`, and `Speed` — the two aggregates over per-log outcomes and the two facts derived from a clock the contract does not carry.
- **Section headers that could no longer be positioned are gone.** `Results (discovery order):` used to caption the per-log block; those lines now arrive inside a flat rendered sequence that carries no structure, so captioning a sub-range would mean guessing an index. The FCX setup projection still leads, and `Scan Complete` still heads the CLI-owned totals.
- **`describe_cli_local_ignore_recovery` takes the execution envelope** rather than the run result, because the rendered lines travel on the envelope. It presents all of them and no longer restates why the run paused — the same call the TUI made in 6ca55427f, for the same reason. Its retained-discovery sentence is still the CLI's, and is the one remaining caller of the local `plural` helper, exactly as in the TUI.
- **`read_cli_local_ignore_recovery_choice` is untouched.** Its input loop, attempt limit, EOF handling, `[P/R/C]` letters, and availability filter all wait for the gated recovery phase. The `abandon` mapping for `CliLocalIgnoreRecoveryChoice::Cancel` landed separately in step 8; the prompt that produces the choice is unchanged.

`classic-cli/tests/test_display_label_audit.cpp` inverted its positive half. The CLI calls none of the seven bridge label accessors any more, because every label it prints arrives inside a `Label` segment; their *absence* is now asserted, and the positive half moved down a level to "the renderer reads every segment kind". The wording assertions in `test_scanner.cpp` became renderer conformance over fabricated lines, and the two end-to-end assertions in `test_scan_run_contract.cpp` that pinned CLI prose were re-anchored on content identities and paths the DTO carries.

### GUI

**Landed.** `classic-gui/src/workers/scanrunpresentation.cpp` is now a `ScanRunDisplayLine` to rich-text renderer plus the GUI's section model. It added no bridge surface: the Qt phase reuses the DTOs #176 landed, so no parity baseline moved and no gate had to be regenerated.

What the GUI kept, all of it Display Layout: `ScanRunTerminalKind` and its one-to-one mapping onto lifecycle signals, the counts, the discovery-ordered `logs`, the FCX Mode setup projection grouped in after the rendered lines, the run-level Installed YAML Data warning's decision to interrupt, and the `[P]`-equivalent affordances of the recovery prompt. What it gained is styling: severity to a dark-theme hex colour, `Count` to an emphasised value beside Rust's noun, `Emphasis` to italics, and `Path` to a `file:` anchor that `showScanRunMessage` makes clickable with `Qt::TextBrowserInteraction`.

Details worth recording:

- **The terminal signals carry rich text; the status row carries one plain line.** `cancelled`, `noLogsFound`, and `error` all end in a `QMessageBox`, so they carry `richText`. `setStatusMessage` writes a `QProgressBar` format string, which is plain and single-line, so `scanRunStatusLine` reduces the block to its leading line — safe because every render entry point opens on the line that states the outcome. The signal *plumbing* is untouched: same signals, same firing points, same thread hops, same invariant errors for a missing continuation and a missing prompt.
- **Event rendering migrated too**, beyond the ticket's acceptance list, for the reason the CLI's did: leaving `eventStatus` composing `Found N crash logs` would have kept exactly the drift this removes, in a frontend whose event DTO now carries the rendered lines. An event that renders more than one line is joined with ` - `, because the progress row is one string.
- **The per-log outcome line moved out of the worker entirely.** `ScanWorker` logged three composed shapes per log — a failure warning in two variants and a moved-to-Unsolved-Logs line. All three are lines in the rendered run, so the worker logs the rendered run once and the loop that remains emits only `logScanned`. `ScanRunLogPresentation::failures` went with them; the typed failures are unchanged on the DTO.
- **Five of seven label accessors lost their last GUI caller.** Only `scan_run_local_ignore_yaml_data_state_label` and `scan_run_installed_yaml_data_provenance_label` survive, both in `installedYamlDataStatusSuffix`, which is the case the accessors remain correct for: a one-row surface with no space for a rendered block, labelling an enum outside a display line. `test_display_label_audit.cpp` inverted for the other five and asserts their absence across every audited source; its positive half moved down a level to "the renderer reads every segment kind and every severity".
- **The per-log disposition line stays unshown as a GUI-owned line.** `presentLog` still maps the three variants onto booleans, still calls no disposition accessor, and still invents no results-view column. The disposition a user reads arrives inside the rendered per-log line.
- **The run-level Installed YAML Data warning keeps its policy and loses its prose.** Its body is now the run's rendered lines under a GUI-owned header, carried on `ScanRunInstalledYamlDataPresentation::runDisplayLines`. It shows the whole run rather than the Installed YAML Data block alone because Rust exposes that block only through `render_run_result` — the same call the CLI and the TUI made for their recovery prompts. Which lines it withholds is still this frontend's, and is preserved exactly: an expected first-run generation, a Local Ignore problem the recovery dialog already asked about, and the reset diagnostic superseded by the backup and replacement lines beside it. A withheld line is recognised by the diagnostic message it carries as its `Emphasis` payload — a value the GUI already holds a typed copy of and compares rather than parses.
- **`formatInstalledYamlDataDiagnostic` is gone**, and with it `installedYamlDataDiagnosticKindLabel`. Its `<kind>: <message> [role, candidate, path]` frame is exactly the line Rust renders for a diagnostic.
- **`formatScanRunRejections` is untouched**, and is the one remaining place the GUI composes a sentence about a run — including its own pluralization of `targeted input(s)`. It survives because the event's rendered lines state the rejection *count* but not the per-rejection path and reason, which this frontend shows at discovery time rather than making the user wait for the terminal block. Migrating it means the presentation crate gaining a per-rejection event line; that is a core change and belongs with the Node/Python phase, not here.
- **The recovery prompt now receives the whole rendered run**, matching the call the TUI and the CLI made and for the same reason. Its own wording, its buttons, and the descriptions beside them are untouched and land with the gated recovery phase.

Still ahead for this frontend, unchanged by this phase: the recovery prompt's own Display Content. `ScanRunInstalledYamlDataPresentation` already gained `localIgnoreResetAvailable` and `promptLocalIgnoreRecoveryChoice` already gained the parameter that withholds the reset button. `scanworker.cpp` routing `ScanRunLocalIgnoreRecoveryChoice::Cancel` to the shared `abandon` operation landed in step 8.

### TUI

**Landed.** `ui-applications/classic-tui/src/scan_run.rs` keeps `sentence_case` and its progress-weight constants — both are Display Layout — and dropped its own composition of the run result, the two error shapes, and the Installed YAML Data block in favour of rendering display lines. It depends on `classic-scan-presentation` directly, with no FFI.

Three details differ from the original sketch, each for a reason worth recording:

- **`append_setup_details` stays.** The FCX Mode setup projection is out of scope until its four types adopt `Vocabulary`, so the crate does not render it. The TUI keeps its `Display`-based projection and groups those lines in *after* the rendered ones. Regrouping whole lines is Display Layout; splicing into the middle of a flat sequence would mean guessing an index.
- **The recovery overlay carries the whole rendered run result.** Core exposes the Installed YAML Data block only through `render_run_result`, and picking that block back out by position would be a structural assumption about a sequence that carries no structure. Every surrounding line describes the run the user is being asked to decide about, so showing them is no loss.
- **`plural` survives with exactly one caller.** The Local Ignore recovery prompt's own prose is still the TUI's, because the prompt renderer lands with the gated recovery phase. Every other count the TUI prints is now a `Count` segment whose noun core already agreed with its value.
- **The recovery overlay no longer restates why the run paused.** Once the overlay carried the whole rendered run result, three things said it at once: the overlay title, core's status line, and core's `Message:` line. The body now opens on the retained-discovery line, and the copy this frontend was making is gone.

Severity reaches two surfaces. Both scan-run overlays style each line through `theme::severity_color`, and the one-row status line at the bottom colours the same way — but only while a Crash Log Scan Run is what wrote it. `scan_status` is written from around sixty places across `app.rs`, `event.rs`, and the three workflow modules, and all but a handful carry no severity at all, so `App` stores the severity *paired with the exact text it applied to*. Any other write silently invalidates it, which keeps a failed run's red off the unrelated message that replaced it without asking sixty call sites to remember to clear a flag.

`app.rs` keeps `PendingLocalIgnoreRecovery` and its overlay, and now takes the continuation out of a result *before* rendering it at both sites. `event.rs` keeps its key map, including Enter left deliberately unbound so no keypress implicitly authorizes a durable reset; gating keys on `RecoveryDecisionDescription::available` rather than on the hand-read `reset_available` flag waits for the gated recovery phase, since that type does not exist yet.

`tests/shared_runtime_audit.rs` moved `CrashLogScanRunStatus` from `DEFERRED_ENUMS` into `AUDITED_ENUMS`, which is the change its deferral note was waiting for. `app.rs`'s two status comparisons became named `bool`-returning predicates so the audit's deliberate `arm_body_end` over-read cannot read a control-flow match as a naming table.

## Node And Python Bindings

### Node

**Landed.** `node-bindings/classic-node/src/scan_run.rs` mirrors `DisplayLine` and `DisplaySegment` as napi objects with the same flattening as the bridge, following the existing `event_to_js` pattern, and applies the crate's documented identifier casing. `index.d.ts` is refreshed and the parity baseline regenerated.

This is the first surface with no frontend of its own. It renders nothing and styles nothing; it carries the lines and hands them to whatever a consumer builds. That is what made the flattening decision easy — reusing the bridge's shape unchanged, empty fields and all, rather than an idiomatic one with optional payloads, because a consumer reading two bindings would otherwise read the same segment two ways.

Details worth recording:

- **Three fields, not one.** The bridge has one execution envelope with presence flags, so a single `display_lines` covers all three payloads. Node resolves two envelopes — `JsScanRunSuccess` and `JsScanRunFailure` — and *rejects* a resume error rather than returning it, so the same coverage costs `displayLines` on each envelope plus one on the rejected error object. The envelope pair is shared by `scanRunExecute` and `scanRunResume`, which is what keeps the initial run and the continuation resume on one field each rather than four.
- **The rejected resume carries lines too**, though the ticket's acceptance list named only the two results and the event. The bridge renders resume errors, and leaving them out would have left a Node consumer composing its own sentence for a reset conflict — the exact drift this work removes — in the one place where the wording matters most. It is purely additive: `code`, `kind`, `stage`, and the identities beside it are untouched.
- **The replay rejection was routed through the shared builder.** `ScanRunResumeTaskOutput::ContinuationConsumed` used to construct its own code and message by hand. Both strings were already byte-identical to `ResumeErrorKind::as_str` and `ResumeError`'s `Display`, so the pair recorded the agreement instead of checking it — and it is what would have left that one rejection without lines. It now goes through `scan_run_resume_error_to_napi` like every other resume failure, gaining `kind` and `displayLines` and changing neither the code nor the message. A test pins both as literals, since deriving them from the same core call the projection makes would prove nothing. `kind` duplicates `code` and was not asked for; it comes free with the shared builder and is recorded in `docs/api/error-contract.md` rather than special-cased away.

- **`displayLines` is required on two objects a consumer could previously build.** `JsScanRunEvent` and `JsScanRunFailure` are plain `#[napi(object)]`, so napi needs the nested display types readable from JavaScript too — which is why those are bidirectional rather than output-only. The consequence is a contract change rather than a pure addition: an object literal that used to satisfy either type no longer does. Harmless, because no entry point on this surface accepts either as an argument; both are only ever resolved out of a run. Narrowing the two parents to `object_from_js = false` instead would have been the larger change.
- **The two hand-written `ts_arg_type` observer unions had to move with the struct.** They narrow `JsScanRunEvent` to the payloads each `kind` actually carries, which the flat all-optional struct cannot express — and they are a second copy of that shape that no compiler checks against the Rust. `bun run build:cli` caught the disagreement, which is the strongest argument for keeping `test:types` and the CLI build in the local loop.
- **A `Count` widens to `i64` and saturates**, because JavaScript has no `u64` — the same treatment a log result's `processingTimeUs` already gets. Unreachable in practice; a wrapped negative count would read as a nonsense quantity rather than as an obvious ceiling.
- **`JsScanRunDisplayLine` and `JsScanRunDisplaySegment` are bidirectional** `#[napi(object)]` rather than output-only, because `JsScanRunEvent` and `JsScanRunFailure` are both constructible from JavaScript today. Narrowing either of those instead would have withdrawn a shape consumers can already build.

Tests are split the way the surface is. `src/scan_run_tests.rs` pins the flattening — every kind fills exactly its own fields, segments keep their order, every severity has a distinct twin, a count carries the noun Rust agreed with — plus one test per carrier that its lines are the ones the renderer produced. The Bun and Node suites prove the same facts across a real run, and add the one thing a unit test cannot: that every Autoscan Report the run wrote arrives as a whole `Path` segment. No test restates a sentence; wording stays pinned once in `classic-scan-presentation`.

Only `node_api_surface.json` moved in the baseline. No Tier-1 row changed, because the parity contract maps Tier-1 *core* crates to Node exports and `classic-scan-presentation` is not one of them.

#### The Node demo CLI

**Landed.** `node-bindings/classic-node/cli/run-scan.ts` is a frontend on the binding rather than part of it, so it is not named anywhere in the sequencing above. It was migrated in the same change anyway, because leaving it would have left a live copy of `plural(count, "log", "logs")` sitting directly on a surface that had just started carrying Rust's already-resolved nouns — the drift shape this brief exists to remove, one import away from the thing that removes it.

It renders exactly as the native C++ CLI does: segments concatenated in reading order with single spaces, no styling, no capitalization rule, paths whole. Severity reaches no further than a choice of output stream, with the cut at `Warning` for the same reason the native CLI puts it there — a run paused awaiting a Local Ignore decision carries that severity and belongs on stderr.

- **The infrastructure failure was printing a Vocabulary Token as prose.** `${execution.error.stage}: ${execution.error.message}` told a user the run failed during `formid_database_access`. This is the same bug #170's problem statement records against `classic-py-cli`, surviving in a second frontend; it is fixed the same way, and `error.stage` still carries the token for anything matching on it.
- **Three invented fallback sentences are gone**, one per terminal branch: a setup-failure headline, a two-clause explanation of what Local Ignore recovery means, and a no-logs line that named the directories from `process.cwd()` and the configured scan path rather than from the ones discovery actually searched.
- **The completed summary lost `Scanned` and `Errors`**, exactly as the native CLI's did, and keeps `Reports`, `Failed`, `Duration`, and `Speed` — the two aggregates over per-log outcomes the contract does not tally and the two facts derived from a clock it does not carry. `formatPluralizedCount` survives with one caller, the report-failure tally, which is the same shape the TUI and native CLI both ended at.
- **Which event kinds earn a console line is unchanged.** Discovery and effective concurrency still print; the rest still do not. Omitting whole lines is what an adapter may do, and it is now the only thing this frontend does to them.
- **JSON mode is untouched in shape.** Display Content does not enter the payload. Where `message` previously fell back to a CLI-written sentence it now takes the run's leading rendered line, so that field is core's words in every branch rather than in some of them.
- **`const enum` imports cost no runtime require.** The two display enums are inlined by `tsc` and the import erased, which matters because this command resolves the binding at run time through `loadClassicNode` — `dist/cli/` sits at a different depth than the source it was compiled from.

Its wording assertions were re-anchored on paths and exit codes the payload carries, matching the call the native CLI's end-to-end tests made. Renderer conformance moved down a level into three tests over fabricated lines, so no sentence is restated. Two assertions were added for the drift itself: the summary must not print `Scanned:` or `Errors:` again.

### Python

**Landed.** `python-bindings/classic-scanlog-py/src/scan_run.rs` exposes `ScanRunDisplayLine` and `ScanRunDisplaySegment` as frozen pyo3 classes with the same flattening as the bridge, `classic_scanlog.pyi` declares them, and the parity baseline regenerated. `classic-py-cli` renders those lines and gained the display-label audit it had never had.

Details worth recording:

- **One field, not three.** Python's `ScanRunExecution` has `result` and `error` presence flags like the bridge's single envelope, and `scan_run_execute` and `scan_run_resume` return the same type, so one `display_lines` covers the initial run, the continuation resume, and both payloads. Node needs three only because it resolves two envelopes and rejects a resume.
- **The tags are snake_case token strings, not pyo3 enums.** Every other tag this surface publishes on an output — a run `status`, an event `kind`, a log `disposition`, a scan `phase`, a Local Ignore state — is a snake_case token string; the one pyo3 enum on the surface, `ScanRunLocalIgnoreRecoveryDecision`, is an *input*. Making severity and segment kind the surface's only PascalCase output tags would have bought nothing: parity is the flattening beneath the tag, and all three seams already spell the tag in their own language.
- **`path` is a `str`, not a `pathlib.Path`.** Every other kind must leave the field empty, and an empty `Path` is `Path('.')` — a wrong value rather than an absent one. A `str` has a genuine empty form, which is what "unused fields empty" needs to be expressible at all.
- **The resume exceptions carry lines too**, though the ticket's acceptance list named only the run result, the resume result, and the event. The bridge renders resume errors, and leaving them out would have left a Python consumer composing its own sentence for a reset conflict — the exact drift this work removes, in the one place where the wording matters most. Purely additive: `code`, `path`, `stage`, and the identities beside them are untouched.
- **The replay rejection was routed through the shared builder**, exactly as on Node and for the same reason. `scan_run_reset_error_to_py` became `scan_run_resume_error_to_py` and gained the `ContinuationConsumed` arm the entry point used to construct by hand. Both hand-written strings were already byte-identical to `ResumeErrorKind::as_str` and `ResumeError`'s `Display`, so the pair recorded the agreement instead of checking it — and it is what would have left that one rejection with nothing to say. It gains `kind` and `display_lines`, changing neither the code nor the message; a test pins both as literals. `kind` is kept on its own Python-side merits, not because Node publishes one: the four reset exceptions have carried it since they were written, so this was the single member of the resume family for which `except (...) as error: error.kind` raised `AttributeError`. Binding surfaces answer to the core's contract, not to each other's shapes — `node-python-contract-map.md` says so in as many words — so a field is justified here only by what this surface already looks like.
- **The classes are output-only** (`frozen, skip_from_py_object`), unlike Node's, which had to become bidirectional because napi requires a nested type to be readable from JavaScript when its parent is. pyo3 imposes no such constraint, so no consumer-constructible shape was widened.

Only `python_api_surface.json` moved in the baseline, mirroring the Node phase exactly. No Tier-1 row changed, because the parity contract maps Tier-1 core crates to Python modules and `classic-scan-presentation` is not one of them.

#### `classic-py-cli`

**Landed.** `python-bindings/classic-py-cli/src/classic_py_cli/display.py` is a new renderer module, and `scan_logs` in `commands.py` presents its lines instead of composing sentences.

It renders as the native C++ CLI and the Node demo CLI do: segments concatenated in reading order with single spaces, no styling, no capitalization rule, paths whole.

- **The raw-token bug is gone at its origin.** `f"Crash Log Scan Run failed during {stage_label}: {message}"` is what told a user a run failed during `formid_database_access` — the sentence #170's problem statement records against this frontend. `error.stage` still carries the token for anything matching on it.
- **Four invented sentences went with it**, one per terminal branch: a setup-failure headline, a two-clause explanation of what Local Ignore recovery means, a cancellation line, and the completed summary's `N succeeded, N failed`. The four branches collapsed into `_UNSUCCESSFUL_TERMINAL_EXIT_CODES`, a status-to-exit-code table: the exit codes are this frontend's and are unchanged, and the prose beside them no longer exists here.
- **`_infrastructure_error_stage_label` is deleted**, and with it this CLI's only call into the six label accessors. Every label it prints now arrives inside a `label` segment. Its absence is what the new audit asserts, the same inversion the native CLI and the Qt GUI made.
- **The Installed YAML Data block appears for the first time.** This frontend never showed one; it arrives inside `render_run_result`'s flat sequence and is printed with everything else.
- **Severity reaches no surface.** `classic-py-cli` writes one stream of plain lines through `output.render_result`, shared by every command and read structurally by the compliance harness, so routing by severity would change that shared contract rather than this run's presentation. Mapping every severity onto plain text is explicitly correct; the severity stays on the line for the day this frontend grows a use for it.
- **JSON mode is untouched in shape.** Display Content does not enter the payload, and the events collected there keep their token-only projection. Where `error.message` previously fell back to a sentence written here it now takes the run's leading rendered line, so that field is Rust's words in every branch rather than in some of them.
- **One sentence stays this CLI's to write.** `_UNRENDERED_RUN` reports a binding that handed back a run and said nothing about it. Every render entry point opens on a line stating the outcome, so it is unreachable through a real binding — but it describes a broken binding promise rather than anything a run said, and the alternative is a silent failure, which reads to a user as the process dying.

`python-bindings/tests/test_classic_py_cli_display_label_audit.py` is the audit this frontend never had. It ports the TUI's coverage test and the C++ audits' inverted accessor-absence assertion, and adds two detectors the earlier three could not express until every frontend had stopped writing sentences: an AST check that no token-bearing value is joined to prose — the exact shape the bug took, and one a literal scan cannot catch because the token appears only at run time — and a deny-list of the domain phrases the presentation crate now owns.

Three details of that audit are worth copying if the other three frontends adopt the deny-list half:

- **It covers all four ways Python builds a string** — f-string, `+`, `%`, and `.format()`. Checking only the f-string would pin the form the bug happened to take rather than the thing that must not happen, and would pass a contributor who reached for `+`.
- **Its coverage test walks recursively.** A top-level glob would let a whole future subpackage escape the audit — the exact failure that test exists to prevent, in the one shape it would not see.
- **Each detector is run against the drift it exists to catch.** An audit whose detector never fires reads as coverage while providing none.

Comments and docstrings are excluded from the literal scans, for the reason the CXX parity gate's name scan was fixed: a comment describing the drift is not the drift.

## Shared Abandonment Rollout

**Landed.** `CrashLogScanRunContinuation::abandon` reaches all three binding surfaces, and both native frontends route their cancel choice through it. The TUI already did, from the phase that added the core operation.

| Surface | Entry point |
| --- | --- |
| CXX | `scan_run_continuation_abandon(continuation, cancellation, observer)` |
| Node | `scanRunAbandon(continuation, cancellation, observer?, cancelOnObserverError?)` |
| Python | `scan_run_abandon(continuation, cancellation, observer=None, cancel_on_observer_error=False)` |

Each takes no decision, cancels the supplied control, and returns whatever its `resume` sibling returns for a cancelled run — rendered `display_lines` included. One row moved in each of the three baselines; the segment taxonomy did not move at all.

Details worth recording:

- **The CXX entry point does not throw, and its sibling does.** `scan_run_continuation_resume` returns `Result<Box<_>>` only because it must reject CXX's non-exhaustive `ScanRunLocalIgnoreRecoveryDecision` sentinel before claiming the one-shot continuation. Abandonment takes no decision, so it has no argument that can be unrepresentable, and declaring a `throws` contract that can never fire would force every C++ caller into unreachable error handling. On this bridge `Result` means "an argument may be unrepresentable", not "the operation may fail" — operational failure travels in the typed envelope, which is where a replayed abandonment's `scan_run_continuation_consumed` arrives.
- **Node and Python model abandonment as the absence of a decision, not a third variant.** Node's task carries `Option<LocalIgnoreRecoveryDecision>` and both entry points go through one `claim_continuation_task` builder; Python's two share one private `claim_continuation`. A parallel task or a second function body would have duplicated the observer adapter, the envelope builders, and the rejection routing — the exact duplication this ticket removes, reintroduced one layer down. `LocalIgnoreRecoveryDecision` still has exactly two variants on all five surfaces.
- **`ScanRunResumeTask` was renamed `ScanRunClaimTask`.** It resumes *or* abandons now, and the one-shot claim is what the two share. The rename costs no baseline row: both entry points override their TypeScript return type, so the task type reaches no declaration.
- **Node's narrowed observer type is duplicated on purpose.** `scan_run_abandon`'s `ts_arg_type` union is byte-identical to `scan_run_resume`'s, because under `strictFunctionTypes` a callback typed for that union is not assignable to a wider parameter — a consumer wiring one observer across both entry points needs the two to agree exactly. `napi`'s attribute takes a string literal, so it cannot be hoisted into a shared constant; `bun run test:types` and `bun run build:cli` are what catch a divergence. `scan_run_execute`'s union is a third, genuinely different one: it alone carries `discovery_completed`.
- **Neither native frontend cancels first any more.** The CLI's `Cancel` arm called `cancellation.request()` and the GUI's called `scan_run_cancellation_cancel`, each followed by a resume with a placeholder. Both are gone: the bridge call cancels the control itself, and it does so *before* attempting the claim, which is the ordering the hand-written copies each had to get right independently. The CLI deliberately does not route through `CliScanRunCancellation::request()` — that wrapper's one-shot guard exists to stop the Ctrl+C monitor and an adapter failure from racing, and Rust's control is monotonic, so a later `request()` is inert rather than a second cancel.
- **Both frontends keep an exhaustive `switch`, now producing a `std::optional<ScanRunLocalIgnoreRecoveryDecision>`.** The first attempt collapsed the three-way choice into `choice == ResetToDefault ? Reset : Proceed` plus an early return for `Cancel`. Semantics were identical today, but it traded away `-Wswitch`: a fourth choice added later would have resolved silently to Proceed Without Ignore — weakening the guard on the two paths that *can* write to disk, in a change whose whole subject is the one that cannot. The `optional` shape also matches the `Option` the Node and Python bindings use, so absence is how abandonment is spelled on all five surfaces. The unreachable trailing `return std::nullopt;` resolves an unrecognized value to abandonment, which is the only outcome that cannot touch a user's files.
- **Node's new registry entry is separate rather than folded into the recovery-decision one.** That entry's `testCaseId` names a specific Bun test about the two decisions; abandonment is deliberately not a third decision, and its coverage belongs to a test that says so. Python's registry entry is per-suite rather than per-case, so `scan_run_abandon` joins the existing scanlog contract row.
- **The prompts themselves are untouched.** `read_cli_local_ignore_recovery_choice`, `promptLocalIgnoreRecoveryChoice`, and the GUI's controller-level `Cancel` fallbacks all still produce the same choice; only what the frontend does with that choice changed. Their own Display Content lands with the gated recovery phase below.

Tests are behavioural, matching the bar the TUI's adoption set. One test per surface asserts what a user would notice: the run reads as cancelled with its retained discovery intact, the supplied control is left cancelled, the run still describes itself in rendered lines, the malformed Local Ignore is byte-identical, no Autoscan Report or backup directory exists, and the shared one-shot claim rejects a later `abandon` *and* a later `resume` with the stable consumed code.

The observer assertion is split off from that set, because the CXX seam cannot make it. `ScanRunObserver` is a C++ virtual class that Rust has no way to implement, so every Rust-side bridge test passes a null observer and none of them can assert what an observer saw. "An abandoned run emits nothing" is therefore pinned from C++ instead, in `classic-cli/tests/test_scan_run_contract.cpp`, which is also the only C++-level exercise of the new entry point — the frontends reach it through their own cancel paths, which pin the outcome but not the seam. Node and Python assert the empty event list in their own suites, where the observer is an ordinary callback.

The existing end-to-end cancel pins in both native frontends — `CLI cancellation at the recovery prompt mutates nothing`, `malformed_local_ignore_recovery_resumes_or_cancels_retained_scan_run`, and `real_scan_worker_abandonment_keeps_the_event_loop_running` — pass unchanged, which is the claim that matters: routing through the shared operation changed no observable behaviour.

## Local Ignore Recovery Phase

This phase does not start until all four conditions hold:

1. The render phase has landed in the TUI, CLI, GUI, and `classic-py-cli`. **Satisfied.**
2. Golden tests pass for every locked item in the subset table. **Satisfied.**
3. All three parity gates are green against regenerated baselines. **Satisfied.**
4. A non-blocking GUI recovery prompt path is demonstrated. **Satisfied** — see `docs/implementation/qt_recovery_prompt_nonblocking_spike.md`.

**Landed.** `render_local_ignore_recovery` produces the prompt, it reaches the C++ bridge, the Node binding, and the Python binding, and all four frontends now render it. No frontend writes a decision sentence any more; `plural` still has one caller each in the TUI, the native CLI, and the Node demo CLI, for the retained-discovery sentence alone.

Details worth recording:

- **The seams changed shape rather than losing a parameter.** `CliLocalIgnoreRecoveryPresentation { details, reset_available }` became `{ details, decisions }`, and `read_cli_local_ignore_recovery_choice` takes the decision list instead of a bool: the menu, the bracketed letters, the retry hint, and the accepted answers are now built in one pass over it, so none can advertise what another withheld. `ScanRunLocalIgnoreRecoveryPrompt` went from `(QString message, bool resetAvailable)` to one copyable `ScanRunLocalIgnoreRecoveryPresentation`, projected on the worker thread — the five constraints the spike fixed all still hold. The TUI's `LocalIgnoreRecoveryPrompt` swapped `reset_available` for `prompt_lines` plus `decisions`, and `App::local_ignore_reset_available` became `local_ignore_decision_available(decision)`.
- **The TUI gates *both* decision keys, not just `r`.** Proceed Without Ignore is unconditionally available, so its guard costs nothing today; what it buys is that a third decision would arrive gated rather than silently ungated. Enter stays unbound.
- **`offersLocalIgnoreResetToDefault` is gone.** Its "silence is not a denial" rule was one of three copies — the CLI and the TUI each had their own. `render_local_ignore_recovery` takes the `Option<&InstalledYamlDataRunData>` precisely so that rule is written once, which is what let all three copies be deleted rather than merely aligned.
- **The Qt buttons now read `Proceed Without Ignore` and `Reset To Default`.** They previously read `Continue Without Ignore` and `Back Up && Reset to Default` — the spelling the Display Label doc comment singles out as not using the word *Proceed* at all. Button text is the Display Label now; only the escaping of a literal `&` is the dialog's.
- **The Python CLI renders the prompt without prompting.** A paused run stays terminal there — `docs/CLASSIC_Python_CLI_PRD.md` puts interactive prompts in CI-oriented commands out of scope — but terminal is not unexplained. The prompt's lines and every *available* decision reach both the plain stream and `data.recoveryPrompt`. It claims no continuation, so no file is touched and there is nothing to abandon. The filter costs that CLI nothing itself; it is there because a consumer reading that payload to drive its own prompt would otherwise repeat the two native frontends' bug.
- **The three sentences joined `core-owned-phrases.txt` with this change**, not before it, exactly as the entry below predicted. All five audits enforce them now.

- **The list carries both decisions, and each carries its own availability.** The acceptance condition "only decisions core is willing to accept appear" is met by construction rather than by filtering: `decisions` is built by walking `LocalIgnoreRecoveryDecision::VARIANTS`, so it can neither offer something the contract will refuse nor omit something it accepts, and the two exhaustive `match`es behind it stop the crate compiling if a third variant is ever added. Filtering unavailable decisions out instead was rejected — a frontend must be able to explain the absence it is about to create, and it can only do that if core tells it what is being withheld.
- **The unavailability sentence moved to core, and nothing else did.** `Reset To Default is unavailable: the selected Main YAML Data retains no usable default Local Ignore to publish.` was already written identically in the TUI overlay, the native CLI menu, and the Qt dialog, each with a comment saying core would own it once this renderer existed. It is a prompt *line* rather than part of the Reset decision's `description`, because a description says what the decision *does* and stays true whether or not this run can honor it.
- **Proceed Without Ignore is hard-coded available.** It needs nothing from the installation, so no run can withdraw it. That the two answers differ is the argument for a per-decision field over one prompt-wide flag, made in code.
- **No entry was added to `core-owned-phrases.txt` by the core phase.** Every phrase on that list must already be gone from every frontend — the file's own third condition — and at that point these three sentences were still written locally in four places. They joined the deny-list with the frontend adoption, not before it, or all five audits would have failed the moment the renderer landed.
- **The retained-discovery sentence stays each frontend's for now.** `render_local_ignore_recovery` reads Installed YAML Data, which does not carry the discovery count. Moving that sentence means the prompt taking a `RunResult`; that is a deliberate widening, not something to do in passing, and it is what would retire `plural`'s last caller on three surfaces.

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

Adapter Mapping Rule 6 has now superseded all of that. `RecoveryDecisionDescription::available` travels with the decision, so a frontend cannot offer an unavailable one without ignoring data placed directly in its hands. The parameters described above were replaced by the bridged prompt rather than removed piecemeal: `read_cli_local_ignore_recovery_choice` takes the decision list, `promptLocalIgnoreRecoveryChoice` takes the whole presentation, `ScanRunInstalledYamlDataPresentation::localIgnoreResetAvailable` is still projected but no longer read by any prompt, and `offersLocalIgnoreResetToDefault` is gone — the ambiguity it resolved is resolved once, in `render_local_ignore_recovery`, for all four frontends.

## Implementation Order

1. **`classic-py-cli` raw token fix.** Independent, shipped separately, ahead of everything else.
2. **`Vocabulary` adoption** for `CrashLogScanRunStatus`, `ScanProgressPhase`, `LocalIgnoreRecoveryDecision`, and `InstalledYamlDataRole`. Tokens unchanged.
3. **`classic-scan-presentation` crate** with `render_run_result`, `render_event`, and the two error renderers, plus unit tests. **Landed.**
4. **TUI migration.** Direct Rust dependency, no FFI, fastest feedback; proves the segment model before any DTO exists. **Landed.**
5. **Bridge DTOs and CLI migration.** The CLI is the simplest C++ consumer and shakes the DTO out before GUI threading is involved. **Landed.**
6. **GUI migration.** **Landed.**
7. **Node and Python surfaces**, then `classic-py-cli` migration. Last, because the segment taxonomy is only stable now and the baselines regenerate once. **Landed.** The taxonomy held: six kinds, unchanged, across all three baselines.
8. **`CrashLogScanRunContinuation::abandon`** and the three call-site replacements. **Landed.** See [Shared Abandonment Rollout](#shared-abandonment-rollout).
9. **Recovery prompt**, gated as above. **Landed** — core, transport, and all four frontends. See [Local Ignore Recovery Phase](#local-ignore-recovery-phase).

## Tests To Add Or Update

Rust unit tests live in sibling `_tests.rs` files declared with `#[cfg(test)] #[path = "<name>_tests.rs"] mod tests;`, never inline.

Display Content wording is pinned **once**, at the `classic-scan-presentation` render functions — the only new seam this brief introduces. Per-frontend golden suites are deliberately not used: they would assert the same wording four times, so one rewording would produce four diffs and four chances to disagree, which is the drift this brief exists to remove. What a frontend must prove instead is narrower and belongs at the audit seam that already exists: that it did not reword what core handed it.

- `business-logic/classic-scan-presentation/src/lib_tests.rs` — one test per locked item, asserting exact segment sequences; a test that no `DisplaySegment::Text` payload contains a placeholder character; a test that every `Count` noun matches its value's grammatical number.
- `business-logic/classic-scanlog-core/src/scan_run/contract_tests.rs` — `abandon` yields the ordinary cancelled result, consumes the continuation exactly once, and leaves the filesystem untouched; replay yields `ResumeError::ContinuationConsumed`.
- Vocabulary conformance via `assert_vocabulary_conformance` for each newly adopted enum, plus a test that each new label differs from its token where the forms differ, matching `every_infrastructure_stage_renders_its_display_label`.
- `ui-applications/classic-tui/tests/shared_runtime_audit.rs` — extend `AUDITED_ENUMS` with the four new adopters, and add a sentence-template detector over a deny-list of domain phrases owned by the presentation crate. Scope it to that deny-list; a general "no format strings" rule would drown in false positives.

  Step 2 could only add two of the four. Step 4 added the third: `CrashLogScanRunStatus` moved out of `DEFERRED_ENUMS` once `format_result` stopped composing its count-bearing sentences and the `Run status: <token>` detail line disappeared with the rest of the local composition. Moving it also required restructuring the two status comparisons left in `app.rs` into named `bool`-returning predicates, because `arm_body_end`'s deliberate over-read otherwise reads a control-flow match arm as a table.

  `LocalIgnoreRecoveryDecision` is the one still deferred, for the same over-read and with no frontend change of its own outstanding. It can move as soon as that bound is tightened or its match is restructured the same way.

  The sentence-template detector **landed** once every frontend had stopped writing those phrases, which is what made a deny-list of core-owned prose enforceable at all.
- `classic-gui/tests/test_display_label_audit.cpp` and `classic-cli/tests/test_display_label_audit.cpp` — same deny-list detector. **Landed.**
- A new display-label audit for `classic-py-cli`, which had none. Its absence is why the raw-token bug survived. **Landed** at `python-bindings/tests/test_classic_py_cli_display_label_audit.py`. It also carried the first working sentence-template detector, plus an AST detector for a token interpolated into prose — the shape the bug actually took, which no literal scan can see.

  All five detectors read one shared deny-list, `business-logic/classic-scan-presentation/core-owned-phrases.txt`, rather than inline copies: a per-frontend list would put the many-copies drift back into the test layer, one level up from where this work removed it. Each audit additionally guards that the shared file is readable and non-empty, and feeds its detector the drift it exists to catch alongside a compliant rendering loop — without that pair, a mislocated file or a broken detector reads as coverage while providing none. The full contract, including when a phrase belongs on the list, is written up once in `docs/api/classic-vocabulary.md`.
- A fifth audit, `node-bindings/classic-node/__test__/display_label_audit.spec.ts`. **Landed.** The Node CLI had already migrated to display lines and composed no sentences of its own; what it lacked was anything keeping it that way — the same unenforced state the Python CLI was in when the raw-token bug survived there. It carries the deny-list detector and the coverage meta-test only; `cli.spec.ts` already held the renderer-conformance half. The roster went from four audits to five without a detector changing, which is the property the shared file was chosen for.
- The Qt GUI status bar. **Landed**, and it was the last surface composing its own sentence about a run: `Scan completed: %1 logs scanned in %2s (%3 succeeded, %4 failed)`, which also re-derived the plural of "logs". The cause was upstream — `ScanWorker::finished(int, int, int)` was the one terminal signal carrying no words, so the window had nothing to state the outcome with. It now carries `terminal.richText` like the other three, and `MainWindow::onScanCompleted` collapses onto the shape `onScanCancelled` already used. That unblocked `succeeded,`, which had lived as a named supplement in the Python CLI's audit and moved into the shared file once no frontend wrote it.

  Enforcing it also exposed that the four source-scanning detectors were reading too much. They stripped comments and searched the remaining *code*, so `succeeded,` matched the GUI's own `emit finished(terminal.succeeded, terminal.failed, ...)` — a line that says nothing to a user. They now extract string literals instead, newline-separated so two adjacent literals cannot fuse into a phrase neither contains. That removes the whole class of false positive and matches the Python audit, which reads literals off the AST for the same reason.
- One thin segment-renderer test per frontend — not golden wording. It asserts that segments concatenate in order, that a `Count` prints core's resolved noun rather than a re-derived one, and that a `RecoveryDecisionDescription` marked unavailable is withheld.
- One test per frontend asserting that Reset To Default is **not** offered when `available` is false. Already done for the TUI, the native CLI, and the Qt GUI, when the frontend half shipped early — the CLI test that pinned the opposite was split into an available case and an unavailable case, and the Qt dialog gained a withheld-button case. When the render phase lands these re-point from the hand-threaded availability flag onto `RecoveryDecisionDescription::available` rather than being written from scratch. `classic-py-cli` needs no such case and never will in its current shape: it treats `local_ignore_recovery_required` as terminal and never resumes, so it offers no recovery decision to withhold. If it ever grows one, it inherits the same rule.

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
