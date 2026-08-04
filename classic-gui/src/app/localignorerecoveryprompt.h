#pragma once

#include <QString>

#include "workers/scanrunpresentation.h"

class QWidget;

namespace classic::gui {

/// Presents the three ways a paused Local Ignore recovery can continue and returns the typed answer.
///
/// Rust defines exactly two recovery decisions; `Cancel` is a GUI-only outcome that the caller
/// projects by requesting cancellation before it resumes the retained continuation. The dialog
/// therefore makes no default destructive choice: both the default and the escape button are
/// Cancel, so pressing Return, pressing Escape, or closing the window all leave the malformed file
/// untouched and prevent analysis.
///
/// `parent` may be null, which is what the behavior tests use. This call blocks on a nested event
/// loop, so it must run on the GUI thread while the worker thread holds the continuation.
ScanRunLocalIgnoreRecoveryChoice promptLocalIgnoreRecoveryChoice(QWidget* parent, const QString& message);

} // namespace classic::gui
