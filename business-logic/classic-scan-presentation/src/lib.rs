//! Crash Log Scan Run Display Content.
//!
//! This crate decides *what a Crash Log Scan Run says*. It turns a run result, a single run
//! event, a run-wide infrastructure failure, or a resume failure into an ordered sequence of
//! [`DisplayLine`]s. Each line is a [`DisplaySeverity`] plus an ordered list of typed
//! [`DisplaySegment`]s, so a frontend can style a path as a clickable link or emphasise a
//! number without re-deciding the words around it.
//!
//! Frontends keep Display Layout: what order to show lines in, what to group, what to
//! colour, what to truncate, which widget to use, and which key or button offers a choice.
//! They lose only the ability to invent or reword what the run says. `CONTEXT.md` defines
//! Display Content and Display Layout; `docs/adr/0007-rust-owns-crash-log-scan-run-display-content.md`
//! records the decision.
//!
//! # Core never interpolates
//!
//! Counts, paths, and names stay typed segment payloads and are never spliced into a
//! sentence. A count arrives with its singular or plural noun already resolved, so no
//! adapter re-decides pluralization and no user reads "1 logs". This is also what keeps
//! translation from being a rewrite later, though CLASSIC stays single-language and this
//! crate builds no message catalogue, locale plumbing, or runtime language selection.
//!
//! # Take the continuation out first
//!
//! Every entry point borrows, because a [`RunResult`](classic_scanlog_core::scan_run::contract::RunResult)
//! is not clonable — it retains a one-shot Crash Log Scan Run Continuation. Take the
//! continuation out of the result **before** rendering; see [`render_run_result`].
//!
//! # Rules an adapter must follow
//!
//! 1. Concatenate a line's segments in order, applying per-kind styling. Never reorder
//!    within a line.
//! 2. Reorder, group, or omit whole lines freely.
//! 3. Never call `Vocabulary::label()` for anything already carried in a
//!    [`DisplaySegment::Label`]. Direct label calls stay correct only where the adapter
//!    renders a domain enum outside a display line.
//! 4. Never re-decide a [`DisplaySegment::Count`]'s noun. Print `value`, then `noun`.
//! 5. Keep Vocabulary Tokens in structured, machine-readable output. Display Content is for
//!    humans and never appears in a payload a consumer matches on.
//!
//! # Dependency direction
//!
//! This crate depends on the scanlog core crate and the shared vocabulary crate, one way
//! only. It is deliberately not a module inside the scanlog core crate: that crate already
//! carries a mutual dependency between its scan-run engine and its scan-run contract, and
//! presentation placed inside it would add a third participant to a cycle a separate effort
//! intends to break. Being a separate crate makes the one-way edge something Cargo enforces
//! rather than something a reviewer has to notice.
//!
//! # No consumer yet
//!
//! Nothing renders from this crate today. That is intentional: the wording ships pinned
//! first, so the frontends that follow have something fixed to render.

mod display;
mod render;

pub use display::{DisplayLine, DisplaySegment, DisplaySeverity};
pub use render::{
    render_event, render_infrastructure_error, render_resume_error, render_run_result,
};

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
