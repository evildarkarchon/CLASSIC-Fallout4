#include <QAbstractButton>
#include <QApplication>
#include <QMessageBox>
#include <QTimer>
#include <QtTest/QtTest>

#include "app/localignorerecoveryprompt.h"

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
                                                            bool* dialogAppeared = nullptr)
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
        nullptr, QStringLiteral("Local Ignore YAML Data is malformed."));
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
    QVERIFY2(offered.filter(QStringLiteral("Reset to Default")).size() == 1, "Reset To Default must be offered");
    QVERIFY2(offered.filter(QStringLiteral("Continue Without Ignore")).size() == 1,
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
        << QStringLiteral("Reset to Default") << static_cast<int>(Choice::ResetToDefault);
    QTest::newRow("proceed-without-ignore")
        << QStringLiteral("Continue Without Ignore") << static_cast<int>(Choice::ProceedWithoutIgnore);
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

QTEST_MAIN(LocalIgnoreRecoveryPromptTests)
#include "test_localignorerecoveryprompt.moc"
