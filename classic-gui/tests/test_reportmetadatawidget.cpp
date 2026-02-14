#include <QLabel>
#include <QtTest/QtTest>

#include "widgets/reportmetadatawidget.h"

class ReportMetadataWidgetTests : public QObject {
    Q_OBJECT

private slots:
    void extractDate_handles_valid_and_invalid_names();
    void formatFileSize_formats_bytes_kb_and_mb();
    void extractIssueCount_counts_known_issue_markers();
    void determineStatus_detects_solved_incomplete_and_unsolved();
    void setMetadata_and_clear_update_labels();
};

void ReportMetadataWidgetTests::extractDate_handles_valid_and_invalid_names()
{
    QCOMPARE(
        ReportMetadataWidget::extractDate(
            QStringLiteral("crash-2024-01-15-08-30-45.log")),
        QStringLiteral("2024-01-15 08:30:45"));

    QCOMPARE(
        ReportMetadataWidget::extractDate(QStringLiteral("no-timestamp.log")),
        QStringLiteral("Unknown"));
}

void ReportMetadataWidgetTests::formatFileSize_formats_bytes_kb_and_mb()
{
    QCOMPARE(ReportMetadataWidget::formatFileSize(512), QStringLiteral("512 B"));
    QCOMPARE(ReportMetadataWidget::formatFileSize(1536), QStringLiteral("1.5 KB"));
    QCOMPARE(ReportMetadataWidget::formatFileSize(2 * 1024 * 1024),
             QStringLiteral("2.0 MB"));
}

void ReportMetadataWidgetTests::extractIssueCount_counts_known_issue_markers()
{
    const QString content = QStringLiteral(
        "line 1\n"
        "SUSPECT: plugin conflict\n"
        "another line\n"
        "[!] risky condition\n"
        "suspect lower case too\n");

    QCOMPARE(ReportMetadataWidget::extractIssueCount(content), 3);
}

void ReportMetadataWidgetTests::determineStatus_detects_solved_incomplete_and_unsolved()
{
    QCOMPARE(ReportMetadataWidget::determineStatus(
                 QStringLiteral("NO ISSUES FOUND in this report")),
             QStringLiteral("Solved"));

    QCOMPARE(
        ReportMetadataWidget::determineStatus(QStringLiteral("report TRUNCATED")),
        QStringLiteral("Incomplete"));

    QCOMPARE(
        ReportMetadataWidget::determineStatus(QStringLiteral("SUSPECT section")),
        QStringLiteral("Unsolved"));
}

void ReportMetadataWidgetTests::setMetadata_and_clear_update_labels()
{
    ReportMetadataWidget widget;
    widget.setMetadata(QStringLiteral("2024-01-15 08:30:45"),
                       QStringLiteral("1.5 KB"),
                       2,
                       QStringLiteral("Solved"));

    QLabel* dateLabel = nullptr;
    QLabel* sizeLabel = nullptr;
    QLabel* issuesLabel = nullptr;
    QLabel* statusLabel = nullptr;
    for (auto* label : widget.findChildren<QLabel*>()) {
        const QString text = label->text();
        if (text.startsWith(QStringLiteral("<b>Date:</b>"))) {
            dateLabel = label;
        } else if (text.startsWith(QStringLiteral("<b>Size:</b>"))) {
            sizeLabel = label;
        } else if (text.startsWith(QStringLiteral("<b>Issues:</b>"))) {
            issuesLabel = label;
        } else if (text.startsWith(QStringLiteral("<b>Status:</b>"))) {
            statusLabel = label;
        }
    }

    QVERIFY(dateLabel);
    QVERIFY(sizeLabel);
    QVERIFY(issuesLabel);
    QVERIFY(statusLabel);

    QCOMPARE(dateLabel->text(),
             QStringLiteral("<b>Date:</b> 2024-01-15 08:30:45"));
    QCOMPARE(sizeLabel->text(), QStringLiteral("<b>Size:</b> 1.5 KB"));
    QCOMPARE(issuesLabel->text(), QStringLiteral("<b>Issues:</b> 2"));
    QVERIFY(statusLabel->text().contains(QStringLiteral("Solved")));
    QVERIFY(statusLabel->text().contains(QStringLiteral("#4CAF50"),
                                         Qt::CaseInsensitive));

    widget.clear();
    QCOMPARE(dateLabel->text(), QStringLiteral("<b>Date:</b> --"));
    QCOMPARE(sizeLabel->text(), QStringLiteral("<b>Size:</b> --"));
    QCOMPARE(issuesLabel->text(), QStringLiteral("<b>Issues:</b> --"));
    QCOMPARE(statusLabel->text(), QStringLiteral("<b>Status:</b> --"));
}

QTEST_MAIN(ReportMetadataWidgetTests)
#include "test_reportmetadatawidget.moc"
