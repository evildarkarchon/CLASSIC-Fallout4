#include "app/localignorerecoveryprompt.h"

// qmessagebox.h only forward-declares both button types. QAbstractButton must be complete for the
// setEscapeButton/clickedButton overloads to resolve, and QPushButton must be complete so the
// QPushButton* returned by addButton() converts to the QAbstractButton* those calls take.
#include <QAbstractButton>
#include <QHash>
#include <QMessageBox>
#include <QPushButton>
#include <QStringList>

namespace classic::gui {

namespace {

/// Escapes a Display Label for use as button text.
///
/// `QAbstractButton` reads a lone `&` as a mnemonic marker and swallows it, so a label containing
/// one would reach the user with a character missing. Doubling it renders a literal `&` — the
/// escape preserves Rust's words rather than changing them. No current label contains one; this is
/// here so that adding one never silently mangles the button.
QString buttonTextFor(const QString& label)
{
    QString escaped = label;
    escaped.replace(QLatin1Char('&'), QLatin1String("&&"));
    return escaped;
}

} // namespace

ScanRunLocalIgnoreRecoveryChoice promptLocalIgnoreRecoveryChoice(
    QWidget* parent, const ScanRunLocalIgnoreRecoveryPresentation& recovery)
{
    QMessageBox prompt(parent);
    prompt.setIcon(QMessageBox::Warning);
    prompt.setWindowTitle(QStringLiteral("Local Ignore Recovery Required"));
    // Auto-detected rather than forced, so a plain-text message keeps its line breaks; a rendered run
    // opens on a `<span>` and is read as rich text on its own. The interaction flags are the
    // load-bearing half: the style's defaults allow neither selection nor link activation on some
    // platforms, and a paused run's message carries the paths this decision is about as `file:`
    // anchors. Without these the user is asked to choose between repairing and ignoring a file they
    // cannot open.
    prompt.setTextFormat(Qt::AutoText);
    prompt.setText(recovery.message);
    prompt.setTextInteractionFlags(Qt::TextBrowserInteraction);

    // Rust's question first, then one line per offered decision. Both are Rust's words; the bold
    // label, the em dash, and the line breaks between them are this dialog's layout. A description
    // goes here rather than on the button because a button holds a name, not a sentence — and a
    // user deciding between two durable outcomes needs the sentence before they click.
    QStringList informative;
    if (!recovery.prompt.isEmpty()) {
        informative.append(recovery.prompt);
    }
    // Buttons are created in the same pass that describes them, so a decision cannot be explained
    // and then not offered, or offered and not explained.
    QHash<QAbstractButton*, classic::scanner::ScanRunLocalIgnoreRecoveryDecision> decisionButtons;
    for (const auto& option : recovery.decisions) {
        // Not created at all when unavailable. A run that reports it cannot honor the decision would
        // still consume its single-use continuation on the attempt, so one stray click would end the
        // scan with no results, no repair, and nothing to resume.
        if (!option.available) {
            continue;
        }
        // The label is escaped and the description is not, and the asymmetry is deliberate: the
        // label arrives as plain text, while the description was already rendered to rich text by
        // `renderScanRunDisplayLineAsRichText` — escaping it would print its own markup at the user.
        informative.append(
            QStringLiteral("<b>%1</b> &mdash; %2").arg(option.label.toHtmlEscaped(), option.description));
        auto* button = prompt.addButton(buttonTextFor(option.label), QMessageBox::ActionRole);
        decisionButtons.insert(button, option.decision);
    }
    prompt.setInformativeText(informative.join(QStringLiteral("<br><br>")));

    auto* cancelButton = prompt.addButton(QMessageBox::Cancel);
    // Cancel is both the default and the escape route so no keystroke or window close can authorize
    // a durable reset the user did not ask for. It is deliberately absent from `decisions`: Rust
    // spells backing out as the *absence* of a decision, reached through the shared abandon
    // operation, so its affordance and its wording stay this frontend's own.
    prompt.setDefaultButton(cancelButton);
    prompt.setEscapeButton(cancelButton);
    prompt.exec();

    // The null check is load-bearing, not defensive: clickedButton() also returns null when the box
    // was closed without a click, and a null lookup must not resolve to a decision the user never
    // asked for.
    auto* clicked = prompt.clickedButton();
    if (clicked != nullptr) {
        const auto decision = decisionButtons.constFind(clicked);
        if (decision != decisionButtons.constEnd()) {
            switch (decision.value()) {
            case classic::scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore:
                return ScanRunLocalIgnoreRecoveryChoice::ProceedWithoutIgnore;
            case classic::scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault:
                return ScanRunLocalIgnoreRecoveryChoice::ResetToDefault;
            }
        }
    }
    // Every other outcome — Cancel, the escape key, a closed window, or a decision this build does
    // not recognize — leaves the malformed file untouched.
    return ScanRunLocalIgnoreRecoveryChoice::Cancel;
}

} // namespace classic::gui
