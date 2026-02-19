#include <QApplication>
#include <QClipboard>
#include <QLabel>
#include <QPushButton>
#include <QSignalSpy>
#include <QTextBrowser>
#include <QtTest/QtTest>

#include "widgets/markdownviewer.h"

class MarkdownViewerTests : public QObject {
    Q_OBJECT

private slots:
    void constructor_sets_default_state_and_stylesheet();
    void toolbar_buttons_have_sufficient_width_for_theme_padding();
    void setMarkdownContent_renders_markdown_as_html();
    void clear_removes_content();
    void zoom_controls_update_label_and_font_with_bounds();
    void copy_all_button_copies_text_emits_signal_and_resets_label();
};

namespace {
QPushButton* findButtonByText(MarkdownViewer& viewer, const QString& text)
{
    for (auto* button : viewer.findChildren<QPushButton*>()) {
        if (button->text() == text) {
            return button;
        }
    }
    return nullptr;
}

QLabel* findZoomLabel(MarkdownViewer& viewer)
{
    for (auto* label : viewer.findChildren<QLabel*>()) {
        if (label->text().endsWith(QLatin1Char('%'))) {
            return label;
        }
    }
    return nullptr;
}
} // namespace

void MarkdownViewerTests::constructor_sets_default_state_and_stylesheet()
{
    MarkdownViewer viewer;

    auto* browser = viewer.findChild<QTextBrowser*>();
    auto* copyButton = findButtonByText(viewer, QStringLiteral("Copy All"));
    auto* zoomOutButton = findButtonByText(viewer, QStringLiteral("-"));
    auto* zoomInButton = findButtonByText(viewer, QStringLiteral("+"));
    auto* zoomResetButton = findButtonByText(viewer, QStringLiteral("Reset"));
    auto* zoomLabel = findZoomLabel(viewer);

    QVERIFY(browser);
    QVERIFY(copyButton);
    QVERIFY(zoomOutButton);
    QVERIFY(zoomInButton);
    QVERIFY(zoomResetButton);
    QVERIFY(zoomLabel);

    QCOMPARE(zoomLabel->text(), QStringLiteral("100%"));
    QVERIFY(browser->document()->defaultStyleSheet().contains(
        QStringLiteral("body {")));
}

void MarkdownViewerTests::toolbar_buttons_have_sufficient_width_for_theme_padding()
{
    MarkdownViewer viewer;

    auto* zoomOutButton = findButtonByText(viewer, QStringLiteral("-"));
    auto* zoomInButton = findButtonByText(viewer, QStringLiteral("+"));
    auto* zoomResetButton = findButtonByText(viewer, QStringLiteral("Reset"));
    QVERIFY(zoomOutButton);
    QVERIFY(zoomInButton);
    QVERIFY(zoomResetButton);

    // Global QPushButton theme uses 16px left/right padding.
    // Keep compact controls wide enough so symbols/text stay visible.
    QVERIFY2(zoomOutButton->minimumWidth() >= 44, "Zoom out button too narrow for themed padding");
    QVERIFY2(zoomInButton->minimumWidth() >= 44, "Zoom in button too narrow for themed padding");
    QVERIFY2(zoomResetButton->minimumWidth() >= 80, "Zoom reset button too narrow for themed padding");
}

void MarkdownViewerTests::setMarkdownContent_renders_markdown_as_html()
{
    MarkdownViewer viewer;
    auto* browser = viewer.findChild<QTextBrowser*>();
    QVERIFY(browser);

    viewer.setMarkdownContent(
        QStringLiteral("# Title\n\nThis is **bold** text.\n\n- item"));

    const QString html = browser->toHtml();
    QVERIFY(html.contains(QStringLiteral("Title")));
    QVERIFY(html.contains(QStringLiteral("bold")));
    QVERIFY(!html.contains(QStringLiteral("**bold**")));

    // Rendering markdown as HTML should consume markdown syntax markers.
    QVERIFY(!viewer.plainText().contains(QStringLiteral("# ")));
    QVERIFY(!viewer.plainText().contains(QStringLiteral("**")));
}

void MarkdownViewerTests::clear_removes_content()
{
    MarkdownViewer viewer;
    viewer.setMarkdownContent(QStringLiteral("Some text"));
    QVERIFY(!viewer.plainText().isEmpty());

    viewer.clear();
    QVERIFY(viewer.plainText().isEmpty());
}

void MarkdownViewerTests::zoom_controls_update_label_and_font_with_bounds()
{
    MarkdownViewer viewer;
    auto* browser = viewer.findChild<QTextBrowser*>();
    auto* zoomLabel = findZoomLabel(viewer);
    QVERIFY(browser);
    QVERIFY(zoomLabel);

    QCOMPARE(zoomLabel->text(), QStringLiteral("100%"));
    QVERIFY(browser->font().pointSize() > 0);

    viewer.zoomIn();
    QCOMPARE(zoomLabel->text(), QStringLiteral("110%"));
    QCOMPARE(browser->font().pointSize(), 11);

    viewer.zoomOut();
    QCOMPARE(zoomLabel->text(), QStringLiteral("100%"));
    QCOMPARE(browser->font().pointSize(), 10);

    for (int i = 0; i < 30; ++i) {
        viewer.zoomOut();
    }
    QCOMPARE(zoomLabel->text(), QStringLiteral("80%"));
    QCOMPARE(browser->font().pointSize(), 8);

    for (int i = 0; i < 30; ++i) {
        viewer.zoomIn();
    }
    QCOMPARE(zoomLabel->text(), QStringLiteral("200%"));
    QCOMPARE(browser->font().pointSize(), 20);

    viewer.zoomReset();
    QCOMPARE(zoomLabel->text(), QStringLiteral("100%"));
    QCOMPARE(browser->font().pointSize(), 10);
}

void MarkdownViewerTests::copy_all_button_copies_text_emits_signal_and_resets_label()
{
    MarkdownViewer viewer;
    auto* copyButton = findButtonByText(viewer, QStringLiteral("Copy All"));
    QVERIFY(copyButton);

    viewer.setMarkdownContent(QStringLiteral("Copy me"));

    QSignalSpy spy(&viewer, &MarkdownViewer::copyAllRequested);
    QTest::mouseClick(copyButton, Qt::LeftButton);

    QTRY_COMPARE(spy.count(), 1);
    QCOMPARE(QApplication::clipboard()->text(), viewer.plainText());
    QCOMPARE(copyButton->text(), QStringLiteral("Copied!"));

    QTRY_COMPARE_WITH_TIMEOUT(copyButton->text(), QStringLiteral("Copy All"), 2500);
}

QTEST_MAIN(MarkdownViewerTests)
#include "test_markdownviewer.moc"
