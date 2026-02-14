#include "controllers/resultscontroller.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QMessageBox>
#include <QDesktopServices>
#include <QUrl>
#include <QApplication>
#include <QClipboard>
#include <QTabWidget>

#include "core/signalhub.h"
#include "core/rust_qt_bridge.h"
#include "widgets/reportlistwidget.h"
#include "widgets/markdownviewer.h"
#include "widgets/reportmetadatawidget.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/files.h"

// ── Construction ───────────────────────────────────────────────────

ResultsController::ResultsController(SignalHub* signalHub,
                                     QTabWidget* tabWidget,
                                     ReportListWidget* reportList,
                                     MarkdownViewer* markdownViewer,
                                     ReportMetadataWidget* metadata,
                                     QObject* parent)
    : QObject(parent)
    , m_signalHub(signalHub)
    , m_tabWidget(tabWidget)
    , m_reportList(reportList)
    , m_markdownViewer(markdownViewer)
    , m_metadata(metadata)
{
    // Widget signals → controller slots
    connect(m_reportList, &ReportListWidget::reportSelected,
            this, &ResultsController::onReportSelected);
    connect(m_reportList, &ReportListWidget::refreshRequested,
            this, &ResultsController::refreshReports);
    connect(m_reportList, &ReportListWidget::deleteRequested,
            this, &ResultsController::onDeleteReport);
    connect(m_reportList, &ReportListWidget::openFolderRequested,
            this, &ResultsController::onOpenFolder);
    connect(m_markdownViewer, &MarkdownViewer::copyAllRequested,
            this, &ResultsController::onCopyAll);

    // SignalHub scan lifecycle
    if (m_signalHub) {
        connect(m_signalHub, &SignalHub::scanStarted,
                this, &ResultsController::onScanStarted);
        connect(m_signalHub, &SignalHub::scanCompleted,
                this, &ResultsController::onScanCompleted);
    }

    // File system watcher
    connect(&m_watcher, &QFileSystemWatcher::directoryChanged,
            this, &ResultsController::onDirectoryChanged);
}

// ── Public interface ──────────────────────────────────────────────

void ResultsController::setReportDirectory(const QString& dirPath)
{
    // Remove previous watch paths
    auto dirs = m_watcher.directories();
    if (!dirs.isEmpty()) {
        m_watcher.removePaths(dirs);
    }

    m_reportDir = dirPath;

    if (!m_reportDir.isEmpty() && QDir(m_reportDir).exists()) {
        m_watcher.addPath(m_reportDir);
    }

    refreshReports();
}

void ResultsController::refreshReports()
{
    if (m_reportDir.isEmpty()) {
        m_reportList->clearReports();
        m_markdownViewer->clear();
        m_metadata->clear();
        return;
    }

    QStringList reports = discoverReports();
    m_reportList->setReports(reports);

    // Clear the viewer if the list is empty
    if (reports.isEmpty()) {
        m_markdownViewer->clear();
        m_metadata->clear();
    }
}

// ── Private slots ─────────────────────────────────────────────────

void ResultsController::onReportSelected(const QString& filePath)
{
    // Use Rust's encoding-detecting file reader for crash logs that
    // may contain mixed encodings (UTF-8, UTF-16, Latin-1, etc.)
    QString content;
    try {
        auto rustContent = classic::files::read_report_file(
            classic::toRustString(filePath));
        content = classic::toQString(rustContent);
    } catch (const rust::Error&) {
        m_markdownViewer->clear();
        m_metadata->clear();
        return;
    }

    // Update markdown viewer
    m_markdownViewer->setMarkdownContent(content);

    // Extract and set metadata
    QFileInfo info(filePath);
    QString date = ReportMetadataWidget::extractDate(info.fileName());
    QString size = ReportMetadataWidget::formatFileSize(info.size());
    int issues = ReportMetadataWidget::extractIssueCount(content);
    QString status = ReportMetadataWidget::determineStatus(content);
    m_metadata->setMetadata(date, size, issues, status);
}

void ResultsController::onDeleteReport(const QString& filePath)
{
    QFileInfo info(filePath);
    auto result = QMessageBox::question(
        qobject_cast<QWidget*>(parent()),
        QStringLiteral("Delete Report"),
        QStringLiteral("Delete \"%1\"?\n\nThis cannot be undone.")
            .arg(info.fileName()),
        QMessageBox::Yes | QMessageBox::No,
        QMessageBox::No);

    if (result != QMessageBox::Yes) {
        return;
    }

    QFile file(filePath);
    if (file.remove()) {
        refreshReports();
    } else {
        QMessageBox::warning(
            qobject_cast<QWidget*>(parent()),
            QStringLiteral("Delete Failed"),
            QStringLiteral("Could not delete \"%1\".").arg(info.fileName()));
    }
}

void ResultsController::onOpenFolder()
{
    if (!m_reportDir.isEmpty()) {
        QDesktopServices::openUrl(QUrl::fromLocalFile(m_reportDir));
    }
}

void ResultsController::onCopyAll()
{
    // The MarkdownViewer already copies to clipboard in its own handler.
    // This slot exists so the controller is aware the action happened,
    // e.g. for future status bar feedback.
}

void ResultsController::onScanStarted()
{
    // Pause file watching during scans to avoid spurious refreshes
    auto dirs = m_watcher.directories();
    if (!dirs.isEmpty()) {
        m_watcher.removePaths(dirs);
    }
}

void ResultsController::onScanCompleted()
{
    // Resume file watching
    if (!m_reportDir.isEmpty() && QDir(m_reportDir).exists()) {
        m_watcher.addPath(m_reportDir);
    }

    // Refresh the report list
    refreshReports();

    // Auto-switch to Results tab
    if (m_tabWidget) {
        m_tabWidget->setCurrentIndex(kResultsTabIndex);
    }
}

void ResultsController::onDirectoryChanged()
{
    refreshReports();
}

// ── Helpers ───────────────────────────────────────────────────────

QStringList ResultsController::discoverReports() const
{
    // Use Rust bridge for discovery -- returns full paths sorted by
    // modification time (newest first), which is more reliable than
    // filename-based sorting for files without embedded timestamps.
    QStringList paths;
    try {
        auto rustPaths = classic::files::discover_report_files(
            classic::toRustString(m_reportDir));
        paths.reserve(static_cast<int>(rustPaths.size()));
        for (const auto& rpath : rustPaths) {
            paths.append(classic::toQString(rpath));
        }
    } catch (const rust::Error&) {
        // Fall back to empty list on error
    }
    return paths;
}
