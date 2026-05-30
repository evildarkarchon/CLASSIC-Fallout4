#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QListWidget>
#include <QPushButton>
#include <QTabWidget>
#include <QTemporaryDir>
#include <QTextStream>
#include <QtTest/QtTest>
#include <QWidget>

#include "controllers/resultscontroller.h"
#include "core/reportpathkey.h"
#include "core/signalhub.h"
#include "widgets/markdownviewer.h"
#include "widgets/reportlistwidget.h"
#include "widgets/reportmetadatawidget.h"

class ResultsControllerTests : public QObject {
    Q_OBJECT

private slots:
    void setReportDirectories_creates_primary_and_discovers_reports_from_both_dirs();
    void custom_directory_changes_trigger_refresh();
    void scan_completed_switches_to_results_tab_when_auto_switch_enabled();
    void scan_completed_does_not_switch_tabs_when_auto_switch_disabled();
    void open_folder_reveals_selected_report_when_file_exists();
    void open_folder_reveals_selected_report_after_refresh_rebuild();
#ifdef Q_OS_WIN
    void open_folder_uses_native_explorer_select_arguments_for_paths_with_spaces();
#endif
    void open_folder_falls_back_to_crash_logs_when_no_selection();
    void open_folder_falls_back_to_crash_logs_when_selected_report_missing();
    void open_folder_does_not_launch_browser_when_no_report_dirs_exist();
    void baseline_reports_at_startup_are_not_flagged_new();
    void report_appearing_after_baseline_is_flagged_new();
    void baseline_report_overwritten_is_not_flagged_new();
};

namespace {
const QString kOpenFolderButtonObjectName = QStringLiteral("reportListOpenFolderButton");

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

bool listItemIsNew(QListWidget* list, const QString& reportPath)
{
    const QString key = classic::gui::reportPathKey(reportPath);
    for (int i = 0; i < list->count(); ++i) {
        auto* item = list->item(i);
        const QString itemKey = classic::gui::reportPathKey(item->data(Qt::UserRole).toString());
        if (itemKey == key) {
            return item->data(ReportListWidget::NewReportRole).toBool();
        }
    }
    return false;
}

class TestableResultsController final : public ResultsController {
public:
    using ResultsController::ResultsController;

    QString openedFolderPath;
    QString revealedFilePath;
    int openFolderCalls = 0;
    int revealFileCalls = 0;

protected:
    bool openFolderInFileBrowser(const QString& folderPath) override
    {
        ++openFolderCalls;
        openedFolderPath = QDir::cleanPath(folderPath);
        return true;
    }

    bool revealFileInFileBrowser(const QString& filePath) override
    {
        ++revealFileCalls;
        revealedFilePath = QDir::cleanPath(filePath);
        return true;
    }
};

#ifdef Q_OS_WIN
class ProcessCapturingResultsController final : public ResultsController {
public:
    using ResultsController::ResultsController;

    QString startedProgram;
    QStringList startedArguments;
    QString startedNativeArguments;
    int startDetachedCalls = 0;

protected:
    bool startDetachedProcess(const QString& program, const QStringList& arguments,
                              const QString& nativeArguments) override
    {
        ++startDetachedCalls;
        startedProgram = program;
        startedArguments = arguments;
        startedNativeArguments = nativeArguments;
        return true;
    }
};
#endif
} // namespace

void ResultsControllerTests::setReportDirectories_creates_primary_and_discovers_reports_from_both_dirs()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    const QString customDir = tempDir.filePath(QStringLiteral("Custom Folder"));
    QVERIFY(QDir().mkpath(customDir));

    QVERIFY(!QDir(crashDir).exists());

    const QString customReport = writeTextFile(customDir + QStringLiteral("/crash-2025-01-01-00-00-00-AUTOSCAN.md"),
                                               QStringLiteral("SUSPECT: custom\n"));
    const QString customLog =
        writeTextFile(customDir + QStringLiteral("/crash-2025-01-01-00-00-00.log"), QStringLiteral("raw log\n"));

    QVERIFY(!customReport.isEmpty());
    QVERIFY(!customLog.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir, customDir}, crashDir);

    QVERIFY(QDir(crashDir).exists());

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    QVERIFY(list->item(0)->text().endsWith(QStringLiteral("-AUTOSCAN.md")));

    const QString crashReport = writeTextFile(crashDir + QStringLiteral("/crash-2025-01-01-00-00-01-AUTOSCAN.md"),
                                              QStringLiteral("NO ISSUES FOUND\n"));
    QVERIFY(!crashReport.isEmpty());

    QTRY_COMPARE(list->count(), 2);
    for (int i = 0; i < list->count(); ++i) {
        QVERIFY(list->item(i)->text().contains(QStringLiteral("-AUTOSCAN.md")));
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

    const QString crashReport = writeTextFile(crashDir + QStringLiteral("/crash-2025-02-01-00-00-00-AUTOSCAN.md"),
                                              QStringLiteral("NO ISSUES FOUND\n"));
    QVERIFY(!crashReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir, customDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);

    const QString customReport = writeTextFile(customDir + QStringLiteral("/crash-2025-02-01-00-00-01-AUTOSCAN.md"),
                                               QStringLiteral("SUSPECT: custom\n"));
    QVERIFY(!customReport.isEmpty());

    QTRY_COMPARE(list->count(), 2);
}

void ResultsControllerTests::scan_completed_switches_to_results_tab_when_auto_switch_enabled()
{
    QTabWidget tabWidget;
    QWidget mainTab;
    QWidget backupTab;
    QWidget articlesTab;
    QWidget resultsTab;
    tabWidget.addTab(&mainTab, QStringLiteral("MAIN OPTIONS"));
    tabWidget.addTab(&backupTab, QStringLiteral("FILE BACKUP"));
    tabWidget.addTab(&articlesTab, QStringLiteral("ARTICLES"));
    tabWidget.addTab(&resultsTab, QStringLiteral("RESULTS"));
    tabWidget.setCurrentIndex(0);

    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setAutoSwitchToResults(true);
    emit SignalHub::instance().scanCompleted();

    QTRY_COMPARE(tabWidget.currentIndex(), 3);
}

void ResultsControllerTests::scan_completed_does_not_switch_tabs_when_auto_switch_disabled()
{
    QTabWidget tabWidget;
    QWidget mainTab;
    QWidget backupTab;
    QWidget articlesTab;
    QWidget resultsTab;
    tabWidget.addTab(&mainTab, QStringLiteral("MAIN OPTIONS"));
    tabWidget.addTab(&backupTab, QStringLiteral("FILE BACKUP"));
    tabWidget.addTab(&articlesTab, QStringLiteral("ARTICLES"));
    tabWidget.addTab(&resultsTab, QStringLiteral("RESULTS"));
    tabWidget.setCurrentIndex(1);

    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setAutoSwitchToResults(false);
    emit SignalHub::instance().scanCompleted();

    QTRY_COMPARE(tabWidget.currentIndex(), 1);
}

void ResultsControllerTests::open_folder_reveals_selected_report_when_file_exists()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    const QString customDir = tempDir.filePath(QStringLiteral("Custom Folder"));
    QVERIFY(QDir().mkpath(crashDir));
    QVERIFY(QDir().mkpath(customDir));

    const QString customReport = writeTextFile(customDir + QStringLiteral("/crash-2025-03-01-00-00-00-AUTOSCAN.md"),
                                               QStringLiteral("SUSPECT: custom\n"));
    QVERIFY(!customReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    TestableResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir, customDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    list->setCurrentRow(0);
    QTRY_VERIFY(!reportList.currentReportPath().isEmpty());

    auto* openFolderButton = reportList.findChild<QPushButton*>(kOpenFolderButtonObjectName);
    QVERIFY(openFolderButton);

    openFolderButton->click();

    QTRY_COMPARE(controller.revealFileCalls, 1);
    QCOMPARE(controller.revealedFilePath, QDir::cleanPath(customReport));
    QCOMPARE(controller.openFolderCalls, 0);
}

void ResultsControllerTests::open_folder_reveals_selected_report_after_refresh_rebuild()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    const QString customDir = tempDir.filePath(QStringLiteral("Custom Folder"));
    QVERIFY(QDir().mkpath(crashDir));
    QVERIFY(QDir().mkpath(customDir));

    const QString customReport = writeTextFile(customDir + QStringLiteral("/crash-2025-03-01-00-00-00-AUTOSCAN.md"),
                                               QStringLiteral("SUSPECT: custom\n"));
    QVERIFY(!customReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    TestableResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir, customDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    list->setCurrentRow(0);
    QTRY_VERIFY(!reportList.currentReportPath().isEmpty());

    controller.refreshReports();

    auto* openFolderButton = reportList.findChild<QPushButton*>(kOpenFolderButtonObjectName);
    QVERIFY(openFolderButton);

    openFolderButton->click();

    QTRY_COMPARE(controller.revealFileCalls, 1);
    QCOMPARE(controller.revealedFilePath, QDir::cleanPath(customReport));
    QCOMPARE(controller.openFolderCalls, 0);
}

#ifdef Q_OS_WIN
void ResultsControllerTests::open_folder_uses_native_explorer_select_arguments_for_paths_with_spaces()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    const QString customDir = tempDir.filePath(QStringLiteral("Custom Folder"));
    QVERIFY(QDir().mkpath(crashDir));
    QVERIFY(QDir().mkpath(customDir));

    const QString customReport = writeTextFile(customDir + QStringLiteral("/crash-2025-03-01-00-00-00-AUTOSCAN.md"),
                                               QStringLiteral("SUSPECT: custom\n"));
    QVERIFY(!customReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ProcessCapturingResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer,
                                                 &metadata);

    controller.setReportDirectories({crashDir, customDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    list->setCurrentRow(0);
    QTRY_VERIFY(!reportList.currentReportPath().isEmpty());

    auto* openFolderButton = reportList.findChild<QPushButton*>(kOpenFolderButtonObjectName);
    QVERIFY(openFolderButton);

    openFolderButton->click();

    QTRY_COMPARE(controller.startDetachedCalls, 1);
    QVERIFY(
        QFileInfo(controller.startedProgram).fileName().compare(QStringLiteral("explorer.exe"), Qt::CaseInsensitive) ==
        0);
    QCOMPARE(controller.startedArguments, QStringList());
    QCOMPARE(controller.startedNativeArguments,
             QStringLiteral("/select,\"%1\"").arg(QDir::toNativeSeparators(QDir::cleanPath(customReport))));
}
#endif

void ResultsControllerTests::open_folder_falls_back_to_crash_logs_when_no_selection()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    QVERIFY(QDir().mkpath(crashDir));

    const QString crashReport = writeTextFile(crashDir + QStringLiteral("/crash-2025-03-01-00-00-01-AUTOSCAN.md"),
                                              QStringLiteral("NO ISSUES FOUND\n"));
    QVERIFY(!crashReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    TestableResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    list->clearSelection();
    list->setCurrentItem(nullptr);
    QCOMPARE(reportList.currentReportPath(), QString());

    auto* openFolderButton = reportList.findChild<QPushButton*>(kOpenFolderButtonObjectName);
    QVERIFY(openFolderButton);

    openFolderButton->click();

    QTRY_COMPARE(controller.openFolderCalls, 1);
    QCOMPARE(controller.openedFolderPath, QDir::cleanPath(crashDir));
    QCOMPARE(controller.revealFileCalls, 0);
}

void ResultsControllerTests::open_folder_does_not_launch_browser_when_no_report_dirs_exist()
{
    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    TestableResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({}, QString());

    auto* openFolderButton = reportList.findChild<QPushButton*>(kOpenFolderButtonObjectName);
    QVERIFY(openFolderButton);

    openFolderButton->click();

    QCOMPARE(controller.openFolderCalls, 0);
    QCOMPARE(controller.revealFileCalls, 0);
    QCOMPARE(controller.openedFolderPath, QString());
    QCOMPARE(controller.revealedFilePath, QString());
}

void ResultsControllerTests::open_folder_falls_back_to_crash_logs_when_selected_report_missing()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    const QString customDir = tempDir.filePath(QStringLiteral("Custom Folder"));
    QVERIFY(QDir().mkpath(crashDir));
    QVERIFY(QDir().mkpath(customDir));

    const QString customReport = writeTextFile(customDir + QStringLiteral("/crash-2025-03-01-00-00-02-AUTOSCAN.md"),
                                               QStringLiteral("SUSPECT: custom\n"));
    QVERIFY(!customReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    TestableResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir, customDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    list->setCurrentRow(0);
    QTRY_VERIFY(!reportList.currentReportPath().isEmpty());
    QVERIFY(QFile::remove(customReport));

    auto* openFolderButton = reportList.findChild<QPushButton*>(kOpenFolderButtonObjectName);
    QVERIFY(openFolderButton);

    openFolderButton->click();

    QTRY_COMPARE(controller.openFolderCalls, 1);
    QCOMPARE(controller.openedFolderPath, QDir::cleanPath(crashDir));
    QCOMPARE(controller.revealFileCalls, 0);
}

void ResultsControllerTests::baseline_reports_at_startup_are_not_flagged_new()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    QVERIFY(QDir().mkpath(crashDir));

    const QString baselineReport = writeTextFile(crashDir + QStringLiteral("/crash-2025-04-01-00-00-00-AUTOSCAN.md"),
                                                 QStringLiteral("NO ISSUES FOUND\n"));
    QVERIFY(!baselineReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    QVERIFY(!listItemIsNew(list, baselineReport));
    QVERIFY(!list->item(0)->data(Qt::ForegroundRole).isValid());
}

void ResultsControllerTests::report_appearing_after_baseline_is_flagged_new()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    QVERIFY(QDir().mkpath(crashDir));

    const QString baselineReport = writeTextFile(crashDir + QStringLiteral("/crash-2025-04-01-00-00-00-AUTOSCAN.md"),
                                                 QStringLiteral("NO ISSUES FOUND\n"));
    QVERIFY(!baselineReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    QVERIFY(!listItemIsNew(list, baselineReport));

    const QString newReport = writeTextFile(crashDir + QStringLiteral("/crash-2025-04-01-00-00-01-AUTOSCAN.md"),
                                            QStringLiteral("SUSPECT: plugin\n"));
    QVERIFY(!newReport.isEmpty());

    QTRY_COMPARE(list->count(), 2);
    QVERIFY(!listItemIsNew(list, baselineReport));
    QVERIFY(listItemIsNew(list, newReport));
}

void ResultsControllerTests::baseline_report_overwritten_is_not_flagged_new()
{
    QTemporaryDir tempDir;
    QVERIFY(tempDir.isValid());

    const QString crashDir = tempDir.filePath(QStringLiteral("Crash Logs"));
    QVERIFY(QDir().mkpath(crashDir));

    const QString baselineReport = writeTextFile(crashDir + QStringLiteral("/crash-2025-04-01-00-00-00-AUTOSCAN.md"),
                                                 QStringLiteral("NO ISSUES FOUND\n"));
    QVERIFY(!baselineReport.isEmpty());

    QTabWidget tabWidget;
    ReportListWidget reportList;
    MarkdownViewer markdownViewer;
    ReportMetadataWidget metadata;

    ResultsController controller(&SignalHub::instance(), &tabWidget, &reportList, &markdownViewer, &metadata);

    controller.setReportDirectories({crashDir}, crashDir);

    auto* list = findReportList(reportList);
    QVERIFY(list);
    QTRY_COMPARE(list->count(), 1);
    QVERIFY(!listItemIsNew(list, baselineReport));

    QVERIFY(!writeTextFile(baselineReport, QStringLiteral("Report is INCOMPLETE\nre-scanned content\n")).isEmpty());

    controller.refreshReports();

    QTRY_COMPARE(list->count(), 1);
    QVERIFY(!listItemIsNew(list, baselineReport));
    QVERIFY(!list->item(0)->data(Qt::ForegroundRole).isValid());
}

QTEST_MAIN(ResultsControllerTests)
#include "test_resultscontroller.moc"
