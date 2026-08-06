#pragma once

#include <QString>

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
/// `resetAvailable` is the run's own report of whether Reset To Default can succeed. When it is
/// false the reset button is not created at all, so no single misplaced click can spend the
/// single-use continuation on a decision that is guaranteed to fail and cost the whole scan. The
/// button is omitted rather than disabled: a greyed-out button invites a user to hunt for the
/// setting that would enable it, and there is none.
///
/// `parent` may be null, which is what the behavior tests use. This call blocks on a nested event
/// loop, so it must run on the GUI thread while the worker thread holds the continuation.
ScanRunLocalIgnoreRecoveryChoice promptLocalIgnoreRecoveryChoice(QWidget* parent, const QString& message,
                                                                 bool resetAvailable);

} // namespace classic::gui
