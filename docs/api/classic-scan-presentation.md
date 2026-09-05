# classic-scan-presentation

`business-logic/classic-scan-presentation` decides **what a Crash Log Scan Run says**. It turns a
Crash Log Scan Run Result, a single run event, a run-wide infrastructure failure, or a resume failure
into an ordered sequence of display lines. Each frontend decides only **how it looks**.

`CONTEXT.md` defines **Display Content** and **Display Layout**;
[`../adr/0007-rust-owns-crash-log-scan-run-display-content.md`](../adr/0007-rust-owns-crash-log-scan-run-display-content.md)
records the decision and supersedes the ADR-0002 clause that assigned presentation to adapters.

## Status: every frontend renders from it; both bindings carry it

`classic-tui` is the first consumer and depends on this crate directly, with no binding seam in the
way — which is why it went first: it proves the six-segment model before any DTO or parity baseline
exists, at which point changing the taxonomy would cost three baseline regenerations.

`classic-cli` is the second, and the first across a binding seam. It never holds a `RunResult`, so
`classic-cpp-bridge` renders while the Rust value is live and carries the lines across as mirrored
data on the execution envelope and on every observed event. `cxx` cannot express a payload-carrying
Rust enum, so each segment crosses flattened as a kind tag plus a text, a path, and a count field.
That flattening is documented under "Display Content on the envelope" in
[`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md), and the six kinds
are now frozen by a committed parity baseline: adding one costs a baseline regeneration on each of
the three binding surfaces.

`classic-gui` is the third, and reuses the same bridge DTOs the CLI does — the Qt phase added no
bridge surface, so no parity baseline moved. It renders each line into rich text: a severity becomes
a colour, a `Count` emphasises its value beside Rust's noun, and a `Path` becomes an actionable
`file:` anchor, which is the whole reason a path is typed as a path rather than as text. See
[`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md).

The three native frontends between them show what "Rust names no colour" buys. The CLI maps severity
onto a choice of output stream and nothing else, so shared wording reaches a pipeable log without a
single escape sequence; the TUI maps the same severities onto a terminal palette; the GUI maps them
onto hex colours from its dark theme and turns the paths into links. All three print the same words.

`classic-node` is the first surface that carries the lines without rendering anything itself. It has
no frontend to be: it mirrors the same flattening onto napi objects and hands them to whatever a
consumer builds. That is why it reuses the bridge's shape rather than inventing a Node-idiomatic one
with optional payloads — a consumer reading two bindings would otherwise read the same segment two
ways. See [`node-python-contract-map.md`](node-python-contract-map.md).

The demo CLI shipped with that binding, `node-bindings/classic-node/cli/run-scan.ts`, is the fourth
renderer and the worked example of a consumer written against the binding rather than against Rust.
It renders identically to `classic-cli` — segments joined by single spaces, no styling, no
capitalization rule, paths whole, severity spent entirely on the choice of output stream — which is
what a Node frontend gets for free by reading the lines instead of writing its own.

`classic-scanlog-py` is the second carrying binding and the last surface to adopt the model. It
mirrors the same flattening onto pyo3 classes, differing from Node only where the shape of the
surface differs: Python has one execution envelope with `result` and `error` presence, so a single
`display_lines` covers both payloads the way the bridge's does, and its five resume rejections are
exceptions, so each carries the field beside its stable `code`.

`classic-py-cli` is the fifth renderer, and the frontend that fell behind. It is where the
raw-token bug this whole effort begins from survived after the same bug had been fixed in the TUI:
it told a user a run `failed during formid_database_access`. It renders as the native CLI and the
Node demo CLI do, and it gained the display-label audit it had never had — the direct reason that
drift survived here — so it is covered by the same enforcement as the other three from now on.

The Python CLI is also the one frontend that spends severity on nothing. It writes one stream of
plain lines through an output envelope every command shares, so routing by severity would change
that shared contract rather than this run's presentation. Mapping every severity onto plain text is
explicitly correct, and the severity stays on the line for the day that frontend grows a use for it.

See
[`../implementation/scan_run_presentation_consolidation.md`](../implementation/scan_run_presentation_consolidation.md).

## Public surface

```rust
pub enum DisplaySeverity { Info, Notice, Warning, Failure, Success }

pub enum DisplaySegment {
    Text(&'static str),
    Label(&'static str),
    Count { value: u64, noun: &'static str },
    Path(PathBuf),
    Name(String),
    Emphasis(String),
}

pub struct DisplayLine {
    pub severity: DisplaySeverity,
    pub segments: Vec<DisplaySegment>,
}

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

pub fn render_run_result(result: &RunResult) -> Vec<DisplayLine>;
pub fn render_event(event: &Event) -> Vec<DisplayLine>;
pub fn render_infrastructure_error(error: &InfrastructureError) -> Vec<DisplayLine>;
pub fn render_resume_error(error: &ResumeError) -> Vec<DisplayLine>;
pub fn render_local_ignore_recovery(data: Option<&InstalledYamlDataRunData>) -> RecoveryPrompt;
```

All five entry points are pure over a borrowed contract value, so wording can be pinned without
running a scan.

### The Local Ignore recovery prompt

`render_local_ignore_recovery` is the one entry point that produces something other than a bare line
sequence, because the one interactive surface a run has needs the decisions named as well as
described.

**Availability travels attached to the decision it describes**, not as a separate flag beside the
prompt. That is what closes a confirmed gap by construction: a frontend cannot offer an unavailable
decision without ignoring data placed directly in its hands. Before this, `local_ignore_reset_available`
was a fact each frontend had to remember to consult, and two of them did not — they offered Reset To
Default unconditionally, and choosing it spent the one-shot continuation on a guaranteed failure,
leaving the user with no scan, no repair, and no second attempt. A binding consumer building its own
frontend gets the same protection.

`decisions` is built by walking `LocalIgnoreRecoveryDecision::VARIANTS`, so the list can neither
offer a decision the contract will refuse nor omit one it accepts, and the two exhaustive `match`es
behind it stop the crate compiling if a third variant is ever added.

**Proceed Without Ignore is never unavailable.** It needs nothing from the installation — the ignore
list is simply empty for this operation — so no run can withdraw it. That the two answers differ is
exactly why availability is a per-decision field rather than one flag.

**`lines` states the question, not the facts behind it.** It does not name the malformed file's
identity: `render_run_result` already renders that in the Installed YAML Data block, and every
surface receiving a prompt receives the rendered run on the same envelope — so the identity is never
missing, only stated once. Rendering it in both put the same line on screen twice in all three
interactive frontends, which is the drift this crate exists to remove, merely relocated into core.
So `lines` holds the pause statement, plus a `Notice` explaining any decision being withheld. That
second line is a prompt line rather than part of the withheld decision's `description`, because a
description says what a decision *does* and stays true whether or not this run can honor it.

**Backing out is not a decision.** `LocalIgnoreRecoveryDecision` has exactly two variants by design;
abandonment is spelled as the *absence* of a decision and reaches the contract through
`CrashLogScanRunContinuation::abandon`. The cancel affordance and its wording stay each frontend's.

**The argument is optional** because a caller holding `RunResult::installed_yaml_data` holds an
`Option` and must do something when it is absent. All three native frontends independently decided
the same thing — a run that reported nothing has not reported a denial, so withdrawing an option on
silence would regress the behaviour that shipped before the fact existed — and each wrote that rule
for itself. Taking the `Option` here makes it one rule rather than three.

### The segment taxonomy is closed

Six kinds, fixed for this version. Each addition touches three binding parity baselines, so growth
must be a deliberate decision rather than incidental. `Name` carries a domain entity that is not a
filesystem path; no render path emits one yet, and the variant exists so the kind a non-path name
will need is declared now rather than bolted on later.

### Severity is not colour

`DisplaySeverity` says how gravely a line should read. Core never names a colour, a text attribute,
or a widget. A TUI may map `Failure` to red, a CLI may map every severity to plain text, and both are
correct.

## Core never interpolates

Counts, paths, and names stay typed segment payloads and are never spliced into a sentence. A
`Count` arrives with its singular or plural noun already resolved, so no adapter re-decides
pluralization and no user reads "1 logs".

Agreement is structural rather than remembered: a renderer names a noun *pair* and cannot pick
between its forms — only the value does. That is what removes the duplicated
`plural(count, "log", "logs")` helper each frontend wrote for itself, along with every future chance
for one of them to pass the arguments the wrong way round.

This is also what keeps translation from being a rewrite later. CLASSIC stays single-language; the
crate builds no message catalogue, no locale plumbing, and no runtime language selection.

## Take the continuation out before rendering

A `RunResult` is not clonable — it retains a one-shot Crash Log Scan Run Continuation. Every entry
point therefore borrows, and every adapter must take the continuation out of the result **before**
rendering:

```rust
let continuation = result.continuation.take();
let lines = render_run_result(&result);
```

Rendering first and moving the continuation afterwards borrows the result across the move and will
not compile. All three native frontends already sequence it this way; documenting it makes the
ordering a contract rather than a coincidence.

## Rules an adapter must follow

1. Concatenate a line's segments in order, applying per-kind styling. Never reorder within a line.
2. Reorder, group, or omit whole lines freely.
3. Never call `Vocabulary::label()` for anything already carried in a `DisplaySegment::Label`. Direct
   label calls stay correct only where the adapter renders a domain enum outside a display line.
4. Never re-decide a `Count`'s noun. Print `value`, then `noun`.
5. Keep Vocabulary Tokens in structured, machine-readable output. Display Content is for humans and
   never appears in a payload a consumer matches on.
6. Never offer a `RecoveryDecisionDescription` whose `available` is false. The fact travels attached
   to the decision precisely so honouring it takes no separate lookup.

## Locked versus free

**Locked** — byte-identical everywhere, pinned by the tests in `src/lib_tests.rs`: terminal status
prose, infrastructure error prose, resume error prose, the per-log outcome line, the Installed YAML
Data block, the per-event progress line, and the Local Ignore recovery decision descriptions.

**Free, and expected to differ** — line ordering and grouping, section headers, colour and emphasis
mapping, truncation and wrapping, widget choice, collapsibility, and whether a section is shown at
all. A CLI's bracketed letters and a TUI's key hints are Display Layout, and so is the affordance
beside a recovery decision — a button, a key, a menu letter. The description next to it is not.

Two consequences worth naming, because they look like omissions:

- **Paths travel whole.** The per-log outcome line carries the full Crash Log path, not its
  filename. Truncating to a filename is Display Layout, and a frontend that wants to link to the
  Autoscan Report needs the path that reaches it.
- **Capitalization of a line-initial Display Label stays with the adapter.** A progress line led by a
  `Label` reads as a lowercase participle (`parsing`, `cancelled before start`), because the label is
  the vocabulary's and re-casing it in core would be a second copy of the wording. Fixed prose that
  leads a line is written sentence-capitalized. A frontend applies one capitalization rule to all of
  them.

## What this crate does not render

- **The FCX Mode setup projection.** Its check state, check kind, issue severity, and update kind are
  four types in a different subsystem that have not adopted `Vocabulary`, so rendering them here
  would mean inventing prose for machine identifiers — the exact failure this crate exists to
  remove. Adapters keep their existing `Display`-based setup projection until those types adopt
  `Vocabulary` in their own change.
- **The retained-discovery sentence beside a recovery prompt.** How much work an accepted decision
  resumes is a count the prompt's own input does not carry — `render_local_ignore_recovery` reads
  Installed YAML Data, not the run's discovery. It stays each frontend's, and is the one remaining
  caller of the local `plural` helper the TUI, the native CLI, and the Node demo CLI each kept.
  Moving it means the prompt taking a `RunResult`; that is a deliberate change, not a fix to make in
  passing.
- **The resume error's stable code.** `ResumeErrorKind` is token-only by decision: it is an error
  code, not prose, and labelling it invites rendering a code where a sentence belongs. Each resume
  category is instead distinguished by prose, because the distinctions are what a user acts on.

## Dependencies and direction

Depends on `classic-scanlog-core`, `classic-vocabulary`, and `classic-config-core`, one way only.
`classic-scanlog-core` gains **no** dependency on this crate.

It is deliberately not a module inside `classic-scanlog-core`: that crate already carries a mutual
dependency between its `scan_run` engine and its `scan_run::contract`, and presentation placed inside
it would add a third participant to a cycle a separate effort intends to break. Being a separate
crate makes the one-way edge something Cargo enforces rather than something a reviewer has to notice.

The `classic-config-core` edge exists because the scan-run contract exposes Installed YAML Data types
it does not re-export. `classic-tui` carries the same dependency for the same reason.

## What an adapter looks like

`classic-tui` is the worked example. `ui-applications/classic-tui/src/scan_run.rs` concatenates each
line's segments into one string, keeps the whole path in the scrollable overlay and shortens it to a
filename in the one-row status line, groups the FCX Mode setup projection in after the rendered
lines, and hands the severity through to `theme::severity_color`. It composes no sentence about a
run and keeps a `plural` helper for one caller only — the Local Ignore recovery overlay. That
overlay still writes its own choice text; `render_local_ignore_recovery` now exists and reaches
every binding, and the frontends adopt it in their own change.

Its handling of severity on the shared status row is worth copying. That row is written from around
sixty places, most of them nothing to do with a scan run and carrying no severity, so the TUI stores
the severity paired with the exact text it applied to and drops it the moment anything else writes
there. A frontend with a similar shared status area gets the same problem, and pairing solves it
without asking every unrelated write site to clear a flag.

Its `classic-vocabulary` edge moved to `[dev-dependencies]`, which is the clearest single signal
that the migration worked: no non-test code in that crate calls `label()` any more, because every
label it shows now arrives inside a `DisplaySegment::Label`. The tests still call it, to prove the
label rather than the token is what a user reads.

Its conformance test is deliberately thin: that presented lines carry core's lines in core's order
with neither words nor severities changed, that a count prints core's noun, and that the two path
treatments are the split they claim to be. It does not restate a single sentence pinned here.

## Binding surface

All three: the C++ bridge, the Node binding, and the Python binding. Display Content is rendered
**before** it crosses a seam and travels as mirrored data, because a `RunResult` cannot be held
across one. A segment flattens to a kind tag plus a text field, a path field, and a count field, with
unused fields empty; for a count, the text field carries the core-resolved noun. All three seams
consume that one flattening, which is what lets a wording fix reach every consumer without three
separate readings of the same segment.

Where the seams differ is only in where the field can sit and how each language spells the two tags.

- **The bridge** has one execution envelope with presence flags, so a single `display_lines` on it
  covers the run result, the infrastructure error, and the resume error.
- **Node** resolves two envelopes instead — a success and a failure — and rejects a resume error
  rather than returning it, so the same coverage costs three `displayLines` fields: one on each
  envelope and one on the rejected error object beside its stable `code`.
- **Python** has one envelope like the bridge, so one `display_lines` covers `result` and `error`
  alike, plus one on each of the five resume exceptions.

Events carry it identically on all three.

The recovery prompt rides the same seams and is rendered under the same rule — while the Rust value
is live — but only for a run whose status is Local Ignore Recovery Required, which is exactly when
the execution retains a continuation to answer with. Every other run carries no prompt rather than an
empty one, so a consumer cannot mistake "nothing to ask" for "ask with no options":

- **The bridge** carries `has_recovery_prompt` beside a `ScanRunRecoveryPrompt`, because `cxx` has no
  optional struct — the same presence-flag convention `has_local_ignore_reset` already uses.
- **Node** carries `recoveryPrompt?: JsScanRunRecoveryPrompt` on the success envelope, and **Python**
  a `recovery_prompt: ScanRunRecoveryPrompt | None` getter on `ScanRunExecution`. Both languages have
  a native absent form, and `undefined`/`None` is what a consumer on each surface already reads as
  "not present".

A decision's `description` is an ordinary segment list on all three, flattened exactly as the lines
beside it are, so a consumer renders one with the renderer it already has. The `decision` itself
crosses as each surface's existing recovery-decision enum rather than as a token, on all three, so a
consumer answers with precisely the value it was offered instead of mapping a string back.

Two per-seam details worth knowing:

- **Node widens a `Count` to `i64` and saturates**, because JavaScript has no `u64`. Nothing counts
  anywhere near that far, and the alternative — a silently wrapped negative quantity — would read as
  nonsense rather than as an obvious ceiling. Python keeps the `u64`.
- **The severity and the segment kind are spelled per language.** The bridge uses C++ enums, Node
  uses PascalCase `string_enum` values, and Python uses snake_case token strings, because a
  snake_case token is what every other tag on that surface already is — a run status, an event kind,
  a log disposition. Parity is the flattening beneath the tag, not the tag's spelling.

## Testing

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo test -p classic-scan-presentation
```

Rust unit tests live in `src/lib_tests.rs`, declared from `src/lib.rs` with
`#[cfg(test)] #[path = "lib_tests.rs"] mod tests;`.

Wording is pinned once, here. Per-frontend golden suites are deliberately not used: they would assert
the same wording four times, so one rewording would produce four diffs and four chances to disagree —
reintroducing, in the test layer, exactly the drift this crate exists to remove. What a frontend must
prove is narrower and belongs at the display-label audit seam it already has: that it did not reword
what core handed it.

Beyond one exact-sequence test per locked item, three tests guard the crate's invariants:

- No fixed-prose segment payload carries a placeholder character, so core cannot quietly go back to
  interpolating.
- Every `Count`'s noun agrees with its value's grammatical number.
- Every registered noun reaches the test corpus in **both** grammatical numbers, so a fixture that
  stops covering the singular fails loudly instead of leaving the agreement test checking nothing.

The Installed YAML Data line renderers are `pub(crate)` rather than private, and its header is a
function rather than an inline literal, for one reason: `InspectedYamlDataFile` and
`InstalledYamlDataRunDiagnostic` are accessor-only with no public constructor, so no test can
assemble an `InstalledYamlDataRunData` to feed through `render_run_result`. Pinning that block means
calling its line renderers with the same facts `render_run_result` reads out of those types.

What that leaves untested is the block's assembly order — the six-line sequence inside
`append_installed_yaml_data`. Every line it emits is pinned individually; only their order is not,
and closing that would mean widening `classic-config-core`'s public API purely for a test.
