#include <QAbstractButton>
#include <QApplication>
#include <QMessageBox>
#include <QTimer>
#include <QtTest/QtTest>

#include "app/localignorerecoveryprompt.h"
#include "recoverypromptfixture.h"

#include <functional>

namespace {

/// Returns the modal recovery dialog once its nested event loop has shown it, or nullptr.
QMessageBox* findRecoveryDialog()
{
    for (QWidget* widget : QApplication::topLevelWidgets()) {
        auto* box = qobject_cast<QMessageBox*>(widget);
        if (box != nullptr && box->windowTitle() == QStringLiteral("Local Ignore Recovery Required")) {
            return box;
        }
    }
    return nullptr;
}

/// Returns the dialog button whose visible text contains `label`, ignoring Qt's mnemonic escapes.
QAbstractButton* buttonContaining(QMessageBox* box, const QString& label)
{
    for (QAbstractButton* button : box->buttons()) {
        if (button->text().remove(QLatin1Char('&')).contains(label)) {
            return button;
        }
    }
    return nullptr;
}

/// Drives the modal prompt by running `act` against the dialog once it exists.
///
/// `promptLocalIgnoreRecoveryChoice` blocks on `QMessageBox::exec()`, so the interaction has to be
/// queued before the call and polled until the nested loop is running.
/// Number of 5 ms polls to wait for the modal before giving up, so a broken prompt fails instead of
/// hanging the suite until CTest's timeout.
constexpr int PROMPT_POLL_ATTEMPTS = 400;

classic::gui::ScanRunLocalIgnoreRecoveryChoice drivePrompt(const std::function<void(QMessageBox*)>& act,
                                                            bool* dialogAppeared = nullptr,
                                                            bool resetAvailable = true)
{
    // The timer lives on this stack frame, which outlives the nested exec() loop below, so the
    // captured reference to `act` can never dangle.
    QTimer poll;
    poll.setInterval(5);
    int attempts = 0;
    if (dialogAppeared != nullptr) {
        *dialogAppeared = false;
    }
    QObject::connect(&poll, &QTimer::timeout, &poll, [&poll, &act, &attempts, dialogAppeared]() {
        QMessageBox* box = findRecoveryDialog();
        if (box == nullptr) {
            if (++attempts >= PROMPT_POLL_ATTEMPTS) {
                poll.stop();
            }
            return;
        }
        poll.stop();
        if (dialogAppeared != nullptr) {
            *dialogAppeared = true;
        }
        act(box);
    });
    poll.start();

    return classic::gui::promptLocalIgnoreRecoveryChoice(
        nullptr, classic::gui::test::recoveryPresentation(resetAvailable));
}

} // namespace

class LocalIgnoreRecoveryPromptTests : public QObject {
    Q_OBJECT

private slots:
    /// Verifies the user is offered exactly the three Rust-backed continuations plus cancellation.
    void prompt_offers_both_decisions_and_a_non_mutating_cancel();
    /// Verifies each offered button resolves to its typed decision.
    void each_button_returns_its_typed_choice_data();
    void each_button_returns_its_typed_choice();
    /// Verifies no keystroke or window close can authorize a destructive reset.
    void dismissing_the_prompt_never_selects_a_destructive_default();
    /// Verifies every offered decision is named and explained in the words it was handed.
    void each_offered_decision_is_named_and_explained_from_the_presentation();
    /// Verifies a reset the run cannot honor is never presented as a clickable option.
    void unavailable_reset_is_not_offered();
    /// Verifies withholding the reset leaves the decisions that can succeed intact.
    void unavailable_reset_leaves_the_remaining_decisions_working();
};

void LocalIgnoreRecoveryPromptTests::prompt_offers_both_decisions_and_a_non_mutating_cancel()
{
    QStringList offered;
    bool dialogAppeared = false;
    const auto choice = drivePrompt([&offered](QMessageBox* box) {
        for (QAbstractButton* button : box->buttons()) {
            offered.append(button->text().remove(QLatin1Char('&')));
        }
        QVERIFY(box->text().contains(QStringLiteral("malformed")));
        box->close();
    }, &dialogAppeared);

    QVERIFY2(dialogAppeared, "the recovery prompt never presented a dialog");
    QCOMPARE(offered.size(), 3);
    QVERIFY2(offered.filter(QStringLiteral("Reset To Default")).size() == 1, "Reset To Default must be offered");
    QVERIFY2(offered.filter(QStringLiteral("Proceed Without Ignore")).size() == 1,
             "Proceed Without Ignore must be offered");
    QVERIFY2(offered.filter(QStringLiteral("Cancel")).size() == 1, "Cancel must be offered");
    QCOMPARE(choice, classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel);
}

void LocalIgnoreRecoveryPromptTests::each_button_returns_its_typed_choice_data()
{
    using Choice = classic::gui::ScanRunLocalIgnoreRecoveryChoice;
    QTest::addColumn<QString>("buttonLabel");
    QTest::addColumn<int>("expectedChoiceValue");

    QTest::newRow("reset-to-default")
        << QStringLiteral("Reset To Default") << static_cast<int>(Choice::ResetToDefault);
    QTest::newRow("proceed-without-ignore")
        << QStringLiteral("Proceed Without Ignore") << static_cast<int>(Choice::ProceedWithoutIgnore);
    QTest::newRow("cancel") << QStringLiteral("Cancel") << static_cast<int>(Choice::Cancel);
}

void LocalIgnoreRecoveryPromptTests::each_button_returns_its_typed_choice()
{
    QFETCH(QString, buttonLabel);
    QFETCH(int, expectedChoiceValue);

    bool clicked = false;
    const auto choice = drivePrompt([&buttonLabel, &clicked](QMessageBox* box) {
        QAbstractButton* button = buttonContaining(box, buttonLabel);
        if (button == nullptr) {
            box->close();
            return;
        }
        clicked = true;
        button->click();
    });

    QVERIFY2(clicked, "the expected button was not present in the prompt");
    QCOMPARE(static_cast<int>(choice), expectedChoiceValue);
}

void LocalIgnoreRecoveryPromptTests::dismissing_the_prompt_never_selects_a_destructive_default()
{
    // Closing the window without answering must not be read as consent to a durable reset.
    QCOMPARE(drivePrompt([](QMessageBox* box) { box->close(); }),
             classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel);

    // Escape is bound to the same non-mutating outcome.
    QCOMPARE(drivePrompt([](QMessageBox* box) { QTest::keyClick(box, Qt::Key_Escape); }),
             classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel);

    // Return activates the default button, which is deliberately Cancel rather than a reset.
    QCOMPARE(drivePrompt([](QMessageBox* box) { QTest::keyClick(box, Qt::Key_Return); }),
             classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel);
}

void LocalIgnoreRecoveryPromptTests::each_offered_decision_is_named_and_explained_from_the_presentation()
{
    // A button holds a name, not a sentence, and a user deciding between two durable outcomes needs
    // the sentence before they click. The dialog writes none of it: the label is the button's text
    // and the description sits beside it, both exactly as handed over.
    QString informative;
    bool dialogAppeared = false;
    drivePrompt(
        [&informative](QMessageBox* box) {
            informative = box->informativeText();
            box->close();
        },
        &dialogAppeared);

    QVERIFY2(dialogAppeared, "the recovery prompt never presented a dialog");
    // Rust's question opens the block, then one line per offered decision.
    QVERIFY(informative.contains(QStringLiteral("why the run paused")));
    QVERIFY(informative.contains(QStringLiteral("Proceed Without Ignore")));
    QVERIFY(informative.contains(QStringLiteral("what proceeding does")));
    QVERIFY(informative.contains(QStringLiteral("Reset To Default")));
    QVERIFY(informative.contains(QStringLiteral("what resetting does")));
}

void LocalIgnoreRecoveryPromptTests::unavailable_reset_is_not_offered()
{
    // A run that reports Reset To Default cannot succeed still spends its single-use continuation on
    // the attempt, so one misplaced click would end the scan with no results and nothing to resume.
    // The button is absent rather than disabled: there is no setting a user could go and change.
    QStringList offered;
    bool dialogAppeared = false;
    const auto choice = drivePrompt(
        [&offered](QMessageBox* box) {
            for (QAbstractButton* button : box->buttons()) {
                offered.append(button->text().remove(QLatin1Char('&')));
            }
            // The explanation is Rust's, carried in the prompt lines, so a dialog that omits a
            // button never has to write one of its own.
            QVERIFY2(box->informativeText().contains(QStringLiteral("unavailable")),
                     "the absent reset must be explained rather than silently missing");
            // A withheld decision is not described either. Listing what it would have done next to
            // no way of choosing it reads as a broken dialog rather than a withdrawn option.
            QVERIFY2(!box->informativeText().contains(QStringLiteral("what resetting does")),
                     "a decision that cannot be chosen must not be described as if it could");
            box->close();
        },
        &dialogAppeared, false);

    QVERIFY2(dialogAppeared, "the recovery prompt never presented a dialog");
    QVERIFY2(offered.filter(QStringLiteral("Reset To Default")).isEmpty(),
             "Reset To Default must not be offered when the run reported it cannot succeed");
    QCOMPARE(offered.size(), 2);
    QVERIFY2(offered.filter(QStringLiteral("Proceed Without Ignore")).size() == 1,
             "Proceed Without Ignore must still be offered");
    QVERIFY2(offered.filter(QStringLiteral("Cancel")).size() == 1, "Cancel must still be offered");
    // Closing a dialog with no reset button must not read as a reset. QMessageBox::clickedButton()
    // returns null here, which is the same value a withheld reset button would have.
    QCOMPARE(choice, classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel);
}

void LocalIgnoreRecoveryPromptTests::unavailable_reset_leaves_the_remaining_decisions_working()
{
    bool clicked = false;
    const auto proceed = drivePrompt(
        [&clicked](QMessageBox* box) {
            QAbstractButton* button = buttonContaining(box, QStringLiteral("Proceed Without Ignore"));
            if (button == nullptr) {
                box->close();
                return;
            }
            clicked = true;
            button->click();
        },
        nullptr, false);
    QVERIFY2(clicked, "Proceed Without Ignore was not present in the prompt");
    QCOMPARE(proceed, classic::gui::ScanRunLocalIgnoreRecoveryChoice::ProceedWithoutIgnore);

    // Abandoning the prompt behaves exactly as it does when the reset is available.
    QCOMPARE(drivePrompt([](QMessageBox* box) { QTest::keyClick(box, Qt::Key_Escape); }, nullptr, false),
             classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel);
    QCOMPARE(drivePrompt([](QMessageBox* box) { QTest::keyClick(box, Qt::Key_Return); }, nullptr, false),
             classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel);
}

QTEST_MAIN(LocalIgnoreRecoveryPromptTests)
#include "test_localignorerecoveryprompt.moc"
