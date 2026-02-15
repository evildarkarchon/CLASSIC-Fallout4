#pragma once

#include <QObject>
#include <QString>
#include <QStringList>
#include <QFileSystemWatcher>

class SignalHub;
class QTabWidget;
class ReportListWidget;
class MarkdownViewer;
class ReportMetadataWidget;

class ResultsController : public QObject {
    Q_OBJECT

public:
    explicit ResultsController(SignalHub* signalHub,
                               QTabWidget* tabWidget,
                               ReportListWidget* reportList,
                               MarkdownViewer* markdownViewer,
                               ReportMetadataWidget* metadata,
                               QObject* parent = nullptr);

    void setReportDirectories(const QStringList& dirPaths,
                              const QString& primaryDir = QString());
    void refreshReports();

private slots:
    void onReportSelected(const QString& filePath);
    void onDeleteReport(const QString& filePath);
    void onOpenFolder();
    void onCopyAll();
    void onScanStarted();
    void onScanCompleted();
    void onDirectoryChanged();

private:
    QStringList discoverReports() const;

    SignalHub* m_signalHub = nullptr;
    QTabWidget* m_tabWidget = nullptr;
    ReportListWidget* m_reportList = nullptr;
    MarkdownViewer* m_markdownViewer = nullptr;
    ReportMetadataWidget* m_metadata = nullptr;
    QFileSystemWatcher m_watcher;

    QStringList m_reportDirs;
    QString m_primaryReportDir;
    static constexpr int kResultsTabIndex = 3;
};
