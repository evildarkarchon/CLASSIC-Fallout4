#include <QFile>
#include <QLineEdit>
#include <QListWidget>
#include <QPushButton>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QTextStream>
#include <QtTest/QtTest>

#include "widgets/reportlistwidget.h"

class ReportListWidgetTests : public QObject {
    Q_OBJECT

private slots:
    void setReports_sorts_reports_and_sets_tooltip_without_status_coloring();
    void search_filter_rebuilds_visible_items();
    void selection_and_toolbar_buttons_emit_expected_signals();
};

namespace {
const QString kRefreshButtonObjectName = QStringLiteral("reportListRefreshButton");
const QString kDeleteButtonObjectName = QStringLiteral("reportListDeleteButton");
const QString kOpenFolderButtonObjectName = QStringLiteral("reportListOpenFolderButton");

QString writeReportFile(QTemporaryDir& tempDir,
                        const QString& fileName,
                        const QString& content)
{
    const QString path = tempDir.filePath(fileName);
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return {};
    }

    QTextStream stream(&file);
    stream << content;
    return path;
}
} // namespace

void ReportListWidgetTests::setReports_sorts_reports_and_sets_tooltip_without_status_coloring()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString solved = writeReportFile(
        tempDir, QStringLiteral("crash-2024-01-15-08-30-45.log"),
        QStringLiteral("NO ISSUES FOUND\n"));
    const QString incomplete = writeReportFile(
        tempDir, QStringLiteral("crash-2024-01-16-09-00-00.log"),
        QStringLiteral("Report is INCOMPLETE\n"));
    const QString unsolved = writeReportFile(
        tempDir, QStringLiteral("crash-2024-01-17-10-00-00.log"),
        QStringLiteral("SUSPECT: plugin\n"));
    const QString unknown = writeReportFile(
        tempDir, QStringLiteral("crash-2024-01-18-11-00-00.log"),
        QStringLiteral("normal text only\n"));

    QVERIFY(!solved.isEmpty());
    QVERIFY(!incomplete.isEmpty());
    QVERIFY(!unsolved.isEmpty());
    QVERIFY(!unknown.isEmpty());

    ReportListWidget widget;
    auto* list = widget.findChild<QListWidget*>();
    QVERIFY(list);

    widget.setReports({solved, unknown, unsolved, incomplete});

    QCOMPARE(list->count(), 4);
    QCOMPARE(list->item(0)->text(),
             QStringLiteral("crash-2024-01-18-11-00-00.log"));
    QCOMPARE(list->item(1)->text(),
             QStringLiteral("crash-2024-01-17-10-00-00.log"));
    QCOMPARE(list->item(2)->text(),
             QStringLiteral("crash-2024-01-16-09-00-00.log"));
    QCOMPARE(list->item(3)->text(),
             QStringLiteral("crash-2024-01-15-08-30-45.log"));

    for (int i = 0; i < list->count(); ++i) {
        auto* item = list->item(i);
        QVERIFY(!item->data(Qt::ForegroundRole).isValid());
    }

    QCOMPARE(list->item(0)->toolTip(),
             QStringLiteral("Crash: 2024-01-18 11:00:00"));
}

void ReportListWidgetTests::search_filter_rebuilds_visible_items()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString a = writeReportFile(
        tempDir, QStringLiteral("crash-2024-01-15-08-30-45.log"),
        QStringLiteral("NO ISSUES FOUND\n"));
    const QString b = writeReportFile(
        tempDir, QStringLiteral("crash-2025-06-01-12-00-00.log"),
        QStringLiteral("SUSPECT\n"));

    QVERIFY(!a.isEmpty());
    QVERIFY(!b.isEmpty());

    ReportListWidget widget;
    auto* list = widget.findChild<QListWidget*>();
    auto* search = widget.findChild<QLineEdit*>();
    QVERIFY(list);
    QVERIFY(search);

    widget.setReports({a, b});
    QCOMPARE(list->count(), 2);

    search->setText(QStringLiteral("2025-06"));
    QTRY_COMPARE(list->count(), 1);
    QVERIFY(list->item(0)->text().contains(QStringLiteral("2025-06")));

    search->clear();
    QTRY_COMPARE(list->count(), 2);
}

void ReportListWidgetTests::selection_and_toolbar_buttons_emit_expected_signals()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString a = writeReportFile(
        tempDir, QStringLiteral("crash-2024-01-15-08-30-45.log"),
        QStringLiteral("NO ISSUES FOUND\n"));
    const QString b = writeReportFile(
        tempDir, QStringLiteral("crash-2025-06-01-12-00-00.log"),
        QStringLiteral("SUSPECT\n"));

    QVERIFY(!a.isEmpty());
    QVERIFY(!b.isEmpty());

    ReportListWidget widget;
    auto* list = widget.findChild<QListWidget*>();
    QVERIFY(list);

    auto* refreshButton = widget.findChild<QPushButton*>(kRefreshButtonObjectName);
    auto* deleteButton = widget.findChild<QPushButton*>(kDeleteButtonObjectName);
    auto* openFolderButton = widget.findChild<QPushButton*>(kOpenFolderButtonObjectName);
    QVERIFY(refreshButton);
    QVERIFY(deleteButton);
    QVERIFY(openFolderButton);

    widget.setReports({a, b});
    QCOMPARE(list->count(), 2);

    QSignalSpy selectedSpy(&widget, &ReportListWidget::reportSelected);
    QSignalSpy refreshSpy(&widget, &ReportListWidget::refreshRequested);
    QSignalSpy deleteSpy(&widget, &ReportListWidget::deleteRequested);
    QSignalSpy openFolderSpy(&widget, &ReportListWidget::openFolderRequested);

    list->setCurrentRow(0);
    QTRY_COMPARE(selectedSpy.count(), 1);
    QVERIFY(!widget.currentReportPath().isEmpty());
    QCOMPARE(selectedSpy.takeFirst().at(0).toString(), widget.currentReportPath());

    refreshButton->click();
    QTRY_COMPARE(refreshSpy.count(), 1);

    deleteButton->click();
    QTRY_COMPARE(deleteSpy.count(), 1);
    QCOMPARE(deleteSpy.takeFirst().at(0).toString(), widget.currentReportPath());

    openFolderButton->click();
    QTRY_COMPARE(openFolderSpy.count(), 1);
    QCOMPARE(openFolderSpy.takeFirst().at(0).toString(), widget.currentReportPath());
}

QTEST_MAIN(ReportListWidgetTests)
#include "test_reportlistwidget.moc"
