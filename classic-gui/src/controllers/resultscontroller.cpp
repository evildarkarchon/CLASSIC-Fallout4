#include "controllers/resultscontroller.h"

#include <algorithm>
#include <QApplication>
#include <QClipboard>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QMessageBox>
#include <QProcess>
#include <QSet>
#include <QTabWidget>
#include <QUrl>

#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"
#include "widgets/markdownviewer.h"
#include "widgets/reportlistwidget.h"
#include "widgets/reportmetadatawidget.h"

#include "classic_cxx_bridge/files.h"
#include "rust/cxx.h"

namespace {

QString reportPathKey(const QString& path)
{
    return QDir::cleanPath(QFileInfo(path).absoluteFilePath()).toLower();
}

} // namespace

// ── Construction ───────────────────────────────────────────────────

ResultsController::ResultsController(SignalHub* signalHub, QTabWidget* tabWidget, ReportListWidget* reportList,
                                     MarkdownViewer* markdownViewer, ReportMetadataWidget* metadata, QObject* parent)
    : QObject(parent)
    , m_signalHub(signalHub)
    , m_tabWidget(tabWidget)
    , m_reportList(reportList)
    , m_markdownViewer(markdownViewer)
    , m_metadata(metadata)
{
    // Widget signals → controller slots
    connect(m_reportList, &ReportListWidget::reportSelected, this, &ResultsController::onReportSelected);
    connect(m_reportList, &ReportListWidget::refreshRequested, this, &ResultsController::refreshReports);
    connect(m_reportList, &ReportListWidget::deleteRequested, this, &ResultsController::onDeleteReport);
    connect(m_reportList, &ReportListWidget::openFolderRequested, this, &ResultsController::onOpenFolder);
    connect(m_markdownViewer, &MarkdownViewer::copyAllRequested, this, &ResultsController::onCopyAll);

    // SignalHub scan lifecycle
    if (m_signalHub) {
        connect(m_signalHub, &SignalHub::scanStarted, this, &ResultsController::onScanStarted);
        connect(m_signalHub, &SignalHub::scanCompleted, this, &ResultsController::onScanCompleted);
    }

    // File system watcher
    connect(&m_watcher, &QFileSystemWatcher::directoryChanged, this, &ResultsController::onDirectoryChanged);
}

// ── Public interface ──────────────────────────────────────────────

void ResultsController::setReportDirectories(const QStringList& dirPaths, const QString& primaryDir)
{
    // Remove previous watch paths
    auto dirs = m_watcher.directories();
    if (!dirs.isEmpty()) {
        m_watcher.removePaths(dirs);
    }

    m_reportDirs.clear();
    m_primaryReportDir = QDir::cleanPath(primaryDir.trimmed());

    if (!m_primaryReportDir.isEmpty()) {
        // Crash Logs is the primary report source and should always exist.
        QDir().mkpath(m_primaryReportDir);
    }

    QStringList candidateDirs = dirPaths;
    if (!m_primaryReportDir.isEmpty()) {
        candidateDirs.prepend(m_primaryReportDir);
    }

    QSet<QString> seen;
    for (const auto& rawDir : candidateDirs) {
        const QString cleaned = QDir::cleanPath(rawDir.trimmed());
        if (cleaned.isEmpty()) {
            continue;
        }

        const QString key = cleaned.toLower();
        if (seen.contains(key)) {
            continue;
        }

        seen.insert(key);
        m_reportDirs.append(cleaned);

        if (QDir(cleaned).exists()) {
            m_watcher.addPath(cleaned);
        }
    }

    refreshReports();
}

void ResultsController::setAutoSwitchToResults(bool enabled)
{
    m_autoSwitchToResults = enabled;
}

void ResultsController::refreshReports()
{
    if (m_reportDirs.isEmpty()) {
        m_reportList->clearReports();
        m_markdownViewer->clear();
        m_metadata->clear();
        return;
    }

    QStringList reports = discoverReports();

    if (!m_baselineCaptured) {
        for (const auto& path : reports) {
            m_baselineReports.insert(reportPathKey(path));
        }
        m_baselineCaptured = true;
    }

    QSet<QString> newPaths;
    for (const auto& path : reports) {
        if (!m_baselineReports.contains(reportPathKey(path))) {
            newPaths.insert(path);
        }
    }

    m_reportList->setReports(reports, newPaths);

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
        auto rustContent = classic::files::read_report_file(classic::toRustString(filePath));
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
    m_metadata->setMetadata(date, size);
}

void ResultsController::onDeleteReport(const QString& filePath)
{
    QFileInfo info(filePath);
    auto result = QMessageBox::question(qobject_cast<QWidget*>(parent()), QStringLiteral("Delete Report"),
                                        QStringLiteral("Delete \"%1\"?\n\nThis cannot be undone.").arg(info.fileName()),
                                        QMessageBox::Yes | QMessageBox::No, QMessageBox::No);

    if (result != QMessageBox::Yes) {
        return;
    }

    QFile file(filePath);
    if (file.remove()) {
        refreshReports();
    } else {
        QMessageBox::warning(qobject_cast<QWidget*>(parent()), QStringLiteral("Delete Failed"),
                             QStringLiteral("Could not delete \"%1\".").arg(info.fileName()));
    }
}

void ResultsController::onOpenFolder(const QString& filePath)
{
    const QString selectedPath = QDir::cleanPath(filePath.trimmed());
    const QFileInfo selectedInfo(selectedPath);
    if (!selectedPath.isEmpty() && selectedInfo.exists() && selectedInfo.isFile()) {
        if (revealFileInFileBrowser(selectedInfo.absoluteFilePath())) {
            return;
        }

        const QString selectedDir = selectedInfo.absolutePath();
        if (!selectedDir.isEmpty() && openFolderInFileBrowser(selectedDir)) {
            return;
        }
    }

    QString openDir = m_primaryReportDir;
    if (openDir.isEmpty() && !m_reportDirs.isEmpty()) {
        openDir = m_reportDirs.first();
    }

    if (!openDir.isEmpty()) {
        openFolderInFileBrowser(openDir);
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
    for (const auto& dir : m_reportDirs) {
        if (QDir(dir).exists()) {
            m_watcher.addPath(dir);
        }
    }

    // Refresh the report list
    refreshReports();

    // Auto-switch to Results tab only when enabled in settings
    if (m_autoSwitchToResults && m_tabWidget && m_tabWidget->count() > kResultsTabIndex) {
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
    // Discover report files in all configured directories.
    // The Rust helper filters to *-AUTOSCAN.md for each directory.
    QStringList paths;
    QSet<QString> seen;

    for (const auto& dir : m_reportDirs) {
        try {
            auto rustPaths = classic::files::discover_report_files(classic::toRustString(dir));
            for (const auto& rpath : rustPaths) {
                const QString path = QDir::cleanPath(classic::toQString(rpath));
                const QString key = path.toLower();
                if (seen.contains(key)) {
                    continue;
                }
                seen.insert(key);
                paths.append(path);
            }
        } catch (const rust::Error&) {
            // Ignore individual directory discovery errors and continue.
        }
    }

    // Global newest-first ordering across all directories.
    std::sort(paths.begin(), paths.end(), [](const QString& a, const QString& b) {
        return QFileInfo(a).lastModified() > QFileInfo(b).lastModified();
    });

    return paths;
}

bool ResultsController::openFolderInFileBrowser(const QString& folderPath)
{
    return QDesktopServices::openUrl(QUrl::fromLocalFile(folderPath));
}

bool ResultsController::startDetachedProcess(const QString& program, const QStringList& arguments,
                                             const QString& nativeArguments)
{
    QProcess process;
    process.setProgram(program);
    process.setArguments(arguments);
#ifdef Q_OS_WIN
    if (!nativeArguments.isEmpty()) {
        process.setNativeArguments(nativeArguments);
    }
#else
    Q_UNUSED(nativeArguments);
#endif
    return process.startDetached();
}

bool ResultsController::revealFileInFileBrowser(const QString& filePath)
{
#ifdef Q_OS_WIN
    const QString nativePath = QDir::toNativeSeparators(QDir::cleanPath(filePath));
    const QString nativeArguments = QStringLiteral("/select,\"%1\"").arg(nativePath);
    return startDetachedProcess(QStringLiteral("explorer.exe"), {}, nativeArguments);
#else
    const QFileInfo info(filePath);
    return QDesktopServices::openUrl(QUrl::fromLocalFile(info.absolutePath()));
#endif
}
