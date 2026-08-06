#include "app/localignorerecoveryprompt.h"

// qmessagebox.h only forward-declares both button types. QAbstractButton must be complete for the
// setEscapeButton/clickedButton overloads to resolve, and QPushButton must be complete so the
// QPushButton* returned by addButton() converts to the QAbstractButton* those calls take.
#include <QAbstractButton>
#include <QMessageBox>
#include <QPushButton>

namespace classic::gui {

ScanRunLocalIgnoreRecoveryChoice promptLocalIgnoreRecoveryChoice(QWidget* parent, const QString& message,
                                                                 bool resetAvailable)
{
    QMessageBox prompt(parent);
    prompt.setIcon(QMessageBox::Warning);
    prompt.setWindowTitle(QStringLiteral("Local Ignore Recovery Required"));
    prompt.setText(message);
    prompt.setInformativeText(
        resetAvailable
            ? QStringLiteral(
                  "Back Up & Reset preserves the malformed CLASSIC Ignore.yaml in CLASSIC Backup before replacing it "
                  "with the retained default. Continue Without Ignore leaves the file unchanged and disables local "
                  "ignores for this scan only.")
            // Explaining the absence keeps a missing button from reading as a missing feature. The
            // first sentence is worded identically to the TUI's overlay and the native CLI's menu
            // rather than freshly phrased here: core will own it once the presentation crate lands,
            // and three copies that already agree are one wording to move, not three to reconcile.
            : QStringLiteral(
                  "Reset To Default is unavailable: the selected Main YAML Data retains no usable default "
                  "Local Ignore to publish. Continue Without Ignore leaves the file unchanged and disables "
                  "local ignores for this scan only."));
    // Not created at all when unavailable. A run that reports it cannot honor the decision would
    // still consume its single-use continuation on the attempt, so one stray click would end the
    // scan with no results, no repair, and nothing to resume.
    QAbstractButton* resetButton = nullptr;
    if (resetAvailable) {
        resetButton = prompt.addButton(QStringLiteral("Back Up && Reset to Default"), QMessageBox::AcceptRole);
    }
    auto* proceedButton = prompt.addButton(QStringLiteral("Continue Without Ignore"), QMessageBox::ActionRole);
    auto* cancelButton = prompt.addButton(QMessageBox::Cancel);
    // Cancel is both the default and the escape route so no keystroke or window close can authorize
    // a durable reset the user did not ask for.
    prompt.setDefaultButton(cancelButton);
    prompt.setEscapeButton(cancelButton);
    prompt.exec();

    // The null check is load-bearing, not defensive: clickedButton() also returns null when the box
    // was closed without a click, so comparing against a withheld (null) resetButton would report a
    // durable reset the user never asked for.
    if (resetButton != nullptr && prompt.clickedButton() == resetButton) {
        return ScanRunLocalIgnoreRecoveryChoice::ResetToDefault;
    }
    if (prompt.clickedButton() == proceedButton) {
        return ScanRunLocalIgnoreRecoveryChoice::ProceedWithoutIgnore;
    }
    return ScanRunLocalIgnoreRecoveryChoice::Cancel;
}

} // namespace classic::gui
