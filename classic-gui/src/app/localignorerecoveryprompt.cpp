#include "app/localignorerecoveryprompt.h"

// qmessagebox.h only forward-declares both button types. QAbstractButton must be complete for the
// setEscapeButton/clickedButton overloads to resolve, and QPushButton must be complete so the
// QPushButton* returned by addButton() converts to the QAbstractButton* those calls take.
#include <QAbstractButton>
#include <QMessageBox>
#include <QPushButton>

namespace classic::gui {

ScanRunLocalIgnoreRecoveryChoice promptLocalIgnoreRecoveryChoice(QWidget* parent, const QString& message)
{
    QMessageBox prompt(parent);
    prompt.setIcon(QMessageBox::Warning);
    prompt.setWindowTitle(QStringLiteral("Local Ignore Recovery Required"));
    prompt.setText(message);
    prompt.setInformativeText(QStringLiteral(
        "Back Up & Reset preserves the malformed CLASSIC Ignore.yaml in CLASSIC Backup before replacing it "
        "with the retained default. Continue Without Ignore leaves the file unchanged and disables local ignores "
        "for this scan only."));
    auto* resetButton = prompt.addButton(QStringLiteral("Back Up && Reset to Default"), QMessageBox::AcceptRole);
    auto* proceedButton = prompt.addButton(QStringLiteral("Continue Without Ignore"), QMessageBox::ActionRole);
    auto* cancelButton = prompt.addButton(QMessageBox::Cancel);
    // Cancel is both the default and the escape route so no keystroke or window close can authorize
    // a durable reset the user did not ask for.
    prompt.setDefaultButton(cancelButton);
    prompt.setEscapeButton(cancelButton);
    prompt.exec();

    if (prompt.clickedButton() == resetButton) {
        return ScanRunLocalIgnoreRecoveryChoice::ResetToDefault;
    }
    if (prompt.clickedButton() == proceedButton) {
        return ScanRunLocalIgnoreRecoveryChoice::ProceedWithoutIgnore;
    }
    return ScanRunLocalIgnoreRecoveryChoice::Cancel;
}

} // namespace classic::gui
