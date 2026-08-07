#pragma once

#include "workers/scanrunpresentation.h"

class QWidget;

namespace classic::gui {

/// Presents the ways a paused Local Ignore recovery can continue and returns the typed answer.
///
/// Rust defines exactly two recovery decisions; `Cancel` is a GUI-only outcome that the caller
/// projects by requesting cancellation before it resumes the retained continuation. The dialog
/// therefore makes no default destructive choice: both the default and the escape button are
/// Cancel, so pressing Return, pressing Escape, or closing the window all leave the malformed file
/// untouched and prevent analysis.
///
/// `recovery.decisions` is what the dialog builds its buttons from, one per decision, labelled and
/// explained in Rust's words. A decision whose `available` is false gets no button at all, so no
/// single misplaced click can spend the single-use continuation on a decision that is guaranteed to
/// fail and cost the whole scan. The button is omitted rather than disabled: a greyed-out button
/// invites a user to hunt for the setting that would enable it, and there is none. Why it is
/// missing is stated by `recovery.prompt`, which Rust renders — the dialog explains no absence of
/// its own.
///
/// What stays this frontend's: that the prompt is a modal dialog rather than an overlay or a line
/// of stdin, that the descriptions sit under the question rather than beside the buttons, the
/// Cancel affordance and its wording, and the window title.
///
/// `recovery.message` is the paused run rendered as rich text by
/// `renderScanRunDisplayLinesAsRichText`, so it carries the run's severity colouring and its paths
/// as `file:` anchors. The dialog sets `Qt::TextBrowserInteraction` for that reason: without it the
/// anchors render as inert text and the user cannot reach the files the decision is about. Plain
/// text still works — `Qt::AutoText` leaves it alone — which is what the behavior tests pass.
///
/// `parent` may be null, which is what the behavior tests use. This call blocks on a nested event
/// loop, so it must run on the GUI thread while the worker thread holds the continuation. The
/// nesting is what keeps the window responsive: `exec()` runs a *nested* loop on the GUI thread
/// rather than suspending it, so the window keeps painting and handling input while the question is
/// open. `classic-gui/tests/test_recoverypromptnonblocking.cpp` pins that.
ScanRunLocalIgnoreRecoveryChoice promptLocalIgnoreRecoveryChoice(
    QWidget* parent, const ScanRunLocalIgnoreRecoveryPresentation& recovery);

} // namespace classic::gui
