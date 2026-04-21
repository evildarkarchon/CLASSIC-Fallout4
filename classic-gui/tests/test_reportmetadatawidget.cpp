#include <QLabel>
#include <QtTest/QtTest>

#include "widgets/reportmetadatawidget.h"

class ReportMetadataWidgetTests : public QObject {
    Q_OBJECT

private slots:
    void extractDate_handles_valid_and_invalid_names();
    void formatFileSize_formats_bytes_kb_and_mb();
    void setMetadata_and_clear_update_labels();
};

void ReportMetadataWidgetTests::extractDate_handles_valid_and_invalid_names()
{
    QCOMPARE(ReportMetadataWidget::extractDate(QStringLiteral("crash-2024-01-15-08-30-45.log")),
             QStringLiteral("2024-01-15 08:30:45"));

    QCOMPARE(ReportMetadataWidget::extractDate(QStringLiteral("no-timestamp.log")), QStringLiteral("Unknown"));
}

void ReportMetadataWidgetTests::formatFileSize_formats_bytes_kb_and_mb()
{
    QCOMPARE(ReportMetadataWidget::formatFileSize(512), QStringLiteral("512 B"));
    QCOMPARE(ReportMetadataWidget::formatFileSize(1536), QStringLiteral("1.5 KB"));
    QCOMPARE(ReportMetadataWidget::formatFileSize(2 * 1024 * 1024), QStringLiteral("2.0 MB"));
}

void ReportMetadataWidgetTests::setMetadata_and_clear_update_labels()
{
    ReportMetadataWidget widget;
    widget.setMetadata(QStringLiteral("2024-01-15 08:30:45"), QStringLiteral("1.5 KB"));

    QLabel* dateLabel = nullptr;
    QLabel* sizeLabel = nullptr;
    for (auto* label : widget.findChildren<QLabel*>()) {
        const QString text = label->text();
        if (text.startsWith(QStringLiteral("<b>Date:</b>"))) {
            dateLabel = label;
        } else if (text.startsWith(QStringLiteral("<b>Size:</b>"))) {
            sizeLabel = label;
        }
    }

    QVERIFY(dateLabel);
    QVERIFY(sizeLabel);

    QCOMPARE(dateLabel->text(), QStringLiteral("<b>Date:</b> 2024-01-15 08:30:45"));
    QCOMPARE(sizeLabel->text(), QStringLiteral("<b>Size:</b> 1.5 KB"));

    bool hasIssues = false;
    bool hasStatus = false;
    for (auto* label : widget.findChildren<QLabel*>()) {
        if (label->text().startsWith(QStringLiteral("<b>Issues:</b>"))) {
            hasIssues = true;
        }
        if (label->text().startsWith(QStringLiteral("<b>Status:</b>"))) {
            hasStatus = true;
        }
    }
    QVERIFY(!hasIssues);
    QVERIFY(!hasStatus);

    widget.clear();
    QCOMPARE(dateLabel->text(), QStringLiteral("<b>Date:</b> --"));
    QCOMPARE(sizeLabel->text(), QStringLiteral("<b>Size:</b> --"));
}

QTEST_MAIN(ReportMetadataWidgetTests)
#include "test_reportmetadatawidget.moc"
