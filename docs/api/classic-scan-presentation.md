# classic-scan-presentation

`business-logic/classic-scan-presentation` decides **what a Crash Log Scan Run says**. It turns a
Crash Log Scan Run Result, a single run event, a run-wide infrastructure failure, or a resume failure
into an ordered sequence of display lines. Each frontend decides only **how it looks**.

`CONTEXT.md` defines **Display Content** and **Display Layout**;
[`../adr/0007-rust-owns-crash-log-scan-run-display-content.md`](../adr/0007-rust-owns-crash-log-scan-run-display-content.md)
records the decision and supersedes the ADR-0002 clause that assigned presentation to adapters.

## Status: the TUI and the native CLI render from it

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

The CLI is also the frontend that shows what "Rust names no colour" buys. It maps severity onto a
choice of output stream and nothing else, so shared wording reaches a pipeable log without a single
escape sequence — while the TUI maps the same severities onto a palette.

Still to migrate, in order: the Qt GUI, then the Node and Python surfaces and the Python CLI. See
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

pub fn render_run_result(result: &RunResult) -> Vec<DisplayLine>;
pub fn render_event(event: &Event) -> Vec<DisplayLine>;
pub fn render_infrastructure_error(error: &InfrastructureError) -> Vec<DisplayLine>;
pub fn render_resume_error(error: &ResumeError) -> Vec<DisplayLine>;
```

All four entry points are pure over a borrowed contract value, so wording can be pinned without
running a scan.

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

## Locked versus free

**Locked** — byte-identical everywhere, pinned by the tests in `src/lib_tests.rs`: terminal status
prose, infrastructure error prose, resume error prose, the per-log outcome line, the Installed YAML
Data block, and the per-event progress line.

**Free, and expected to differ** — line ordering and grouping, section headers, colour and emphasis
mapping, truncation and wrapping, widget choice, collapsibility, and whether a section is shown at
all. A CLI's bracketed letters and a TUI's key hints are Display Layout.

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
- **The Local Ignore recovery prompt.** `RecoveryPrompt` and `RecoveryDecisionDescription` land with
  the gated recovery phase, behind the conditions listed in the implementation brief.
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
run and keeps a `plural` helper for one caller only — the Local Ignore recovery prompt, whose
renderer lands with the gated recovery phase.

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

None today. When the render phase reaches the bindings, Display Content is rendered **before** it
crosses a seam and travels as mirrored data, because a `RunResult` cannot be held across one. A
segment flattens to a kind tag plus a text field, a path field, and a count field, with unused fields
empty; for a count, the text field carries the core-resolved noun. See the implementation brief for
the per-surface DTO shapes.

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
