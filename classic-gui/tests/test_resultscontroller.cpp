#include <QDir>
#include <QFile>
#include <QListWidget>
#include <QTabWidget>
#include <QTemporaryDir>
#include <QTextStream>
#include <QtTest/QtTest>

#include "controllers/resultscontroller.h"
#include "core/signalhub.h"
#include "widgets/markdownviewer.h"
#include "widgets/reportlistwidget.h"
#include "widgets/reportmetadatawidget.h"

class ResultsControllerTests : public QObject {
    Q_OBJECT

private slots:
    void setReportDirectories_creates_primary_and_discovers_reports_from_both_dirs();
    void custom_directory_changes_trigger_refresh();
};

namespace {
QString writeTextFile(const QString& filePath, const QString& content)
{
    const QFileInfo info(filePath);
    QDir().mkpath(info.absolutePath());

    QFile file(filePath);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text | QIODevice::Truncate)) {
        return {};
    }

    QTextStream stream(&file);
    stream << content;
    return filePath;
}

QListWidget* findReportList(ReportListWidget& widget)
{
    return widget.findChild<QListWidget*>();
}
} // namespace

void ResultsControllerTests::setReportDirectories_creates_primary_and_discovers_reports_from_both_dirs()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    const QString customDir = tempDir.filePath(QStringLiteral("Custom Folder"));
    QVERIFY(QDir().mkpath(customDir));

    QVERIFY(!QDir(crashDir).exists());

    const QString customReport = writeTextFile(
        customDir + QStringLiteral("/crash-2025-01-01-00-00-00-AUTOSCAN.md"),
        QStringLiteral("SUSPECT: custom\n"));
    const QString customLog = writeTextFile(
        customDir + QStringLiteral("/crash-2025-01-01-00-00-00.log"),
        QStringLiteral("raw log\n"));

    QVERIFY(!customReport.isEmpty());
    QVERIFY(!customLog.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(
        &SignalHub::instance(),
        &tabWidget,
        &reportList,
        &markdownViewer,
        &metadata);

    controller.setReportDirectories({crashDir, customDir}, crashDir);

    QVERIFY(QDir(crashDir).exists());

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    QVERIFY(list->item(0)->text().endsWith(QStringLiteral("-AUTOSCAN.md")));

    const QString crashReport = writeTextFile(
        crashDir + QStringLiteral("/crash-2025-01-01-00-00-01-AUTOSCAN.md"),
        QStringLiteral("NO ISSUES FOUND\n"));
    QVERIFY(!crashReport.isEmpty());

    QTRY_COMPARE(list->count(), 2);
    for (int i = 0; i < list->count(); ++i) {
        QVERIFY(list->item(i)->text().endsWith(QStringLiteral("-AUTOSCAN.md")));
    }
}

void ResultsControllerTests::custom_directory_changes_trigger_refresh()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    const QString customDir = tempDir.filePath(QStringLiteral("Custom Folder"));
    QVERIFY(QDir().mkpath(crashDir));
    QVERIFY(QDir().mkpath(customDir));

    const QString crashReport = writeTextFile(
        crashDir + QStringLiteral("/crash-2025-02-01-00-00-00-AUTOSCAN.md"),
        QStringLiteral("NO ISSUES FOUND\n"));
    QVERIFY(!crashReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(
        &SignalHub::instance(),
        &tabWidget,
        &reportList,
        &markdownViewer,
        &metadata);

    controller.setReportDirectories({crashDir, customDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);

    const QString customReport = writeTextFile(
        customDir + QStringLiteral("/crash-2025-02-01-00-00-01-AUTOSCAN.md"),
        QStringLiteral("SUSPECT: custom\n"));
    QVERIFY(!customReport.isEmpty());

    QTRY_COMPARE(list->count(), 2);
}

QTEST_MAIN(ResultsControllerTests)
#include "test_resultscontroller.moc"
