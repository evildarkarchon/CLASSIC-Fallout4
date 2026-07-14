#pragma once

#include "widgets/adaptiveprogressbar.h"
#include <QElapsedTimer>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMainWindow>
#include <QPushButton>
#include <QStatusBar>
#include <QStringList>
#include <QTabWidget>

class QDragEnterEvent;
class QDragMoveEvent;
class QDropEvent;

class SignalHub;
class ScanController;
class GameFilesController;
class BackupController;
class ResultsController;
class ThreadManager;
struct FeatureContext;
class ReportListWidget;
class MarkdownViewer;
class ReportMetadataWidget;
class PapyrusDialog;

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow() override;

    void setVersion(const QString& version);
    void setStatusMessage(const QString& message);

private:
    void setupUi();
    void setupMainOptionsTab();
    void setupFileBackupTab();
    void setupArticlesTab();
    void setupResultsTab();
    void loadStylesheet();
    void initializeControllers();
    void connectSignals();
    void runStartupWorkflows();

    /// Opens typed Game Setup User Settings, offers explicit bootstrap or migration, and refreshes the UI.
    /// Read-only opens never repair or persist the settings document.
    void loadSettings();

    /// Commits the editable staging and custom-scan paths as one revision-checked User Settings update.
    void saveSettings();
    void initResultsReportDir();

    /// Runs typed Game Setup Intake and commits only paths explicitly accepted by the user.
    /// Declined proposals and cancelled manual entry leave User Settings unchanged.
    void checkFirstRunPaths();
    QString findDataRoot() const;

    /// Persists legacy geometry only when User Settings is trusted, current, and update-eligible.
    void saveTabGeometry(int tabIndex);
    void restoreTabGeometry(int tabIndex);
    bool validateCustomScanFolder(const QString& path);
    QString readCrashLogsDir() const;

    /// Loads and validates the typed saved game and documents roots without interpreting raw settings keys.
    bool loadValidatedGameAndDocsPaths(QString* gamePathOut, QString* docsPathOut) const;
    void checkForUpdates(bool explicitCheck);
    void updateTargetedInputUi();
    void installTargetedDropForwarding();
    bool handleTargetedDragEnter(QDragEnterEvent* event);
    bool handleTargetedDragMove(QDragMoveEvent* event);
    bool handleTargetedDrop(QDropEvent* event);
    void acknowledgeTargetedDrop(int addedCount, int duplicateCount, int nonLocalCount, bool unsupportedPayload,
                                 bool wrongTab);

protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dragMoveEvent(QDragMoveEvent* event) override;
    void dropEvent(QDropEvent* event) override;

private slots:
    void onClearTargetedInputs();
    void onBrowseStaging();
    void onBrowseCustom();
    void onCustomFolderEdited();
    void onScanCrashLogs();

    /// Runs background Game Setup Intake from the typed User Settings projection and an XSE hint.
    void onScanGameFiles();
    void onExit();
    void onCrashScanProgress(float percent, const QString& status, int completed, int total);
    void onScanProgress(float percent, const QString& status);
    void onScanCompleted(int total, int success, int errors);
    void onScanError(const QString& message);
    void onScanWarning(const QString& message);
    void onCrashScanDiscovered(int totalLogs);
    void onCrashLogScanned(int index, bool success, const QString& logPath);
    void onScanReportDirectoriesResolved(const QStringList& reportDirs);
    void onShowSettings();
    void onGameFilesScanFinished(const QString& output, bool hasErrors, uint32_t totalChecks);
    void onGameFilesScanError(const QString& message);
    void onBackupCompleted(const QString& message);
    void onBackupError(const QString& error);
    void onOpenBackupsFolder();
    void onCheckUpdates();
    void onTogglePapyrusMonitor();
    void onTabChanged(int index);

private:
    // Tabs
    QTabWidget* m_tabWidget = nullptr;

    // Main Options tab widgets
    QLineEdit* m_editStagingFolder = nullptr;
    QLineEdit* m_editCustomFolder = nullptr;
    QPushButton* m_btnScanCrashLogs = nullptr;
    QPushButton* m_btnScanGameFiles = nullptr;
    QPushButton* m_btnAbout = nullptr;
    QPushButton* m_btnHelp = nullptr;
    QPushButton* m_btnSettings = nullptr;
    QPushButton* m_btnOpenCrashLogs = nullptr;
    QPushButton* m_btnCheckUpdates = nullptr;
    QPushButton* m_btnPapyrusMonitor = nullptr;
    QPushButton* m_btnExit = nullptr;
    AdaptiveProgressBar* m_progressBar = nullptr;

    // Controllers
    ScanController* m_scanController = nullptr;
    GameFilesController* m_gameFilesController = nullptr;
    BackupController* m_backupController = nullptr;
    ResultsController* m_resultsController = nullptr;
    SignalHub* m_signalHub = nullptr;
    ThreadManager* m_threadManager = nullptr;

    // Results tab widgets
    ReportListWidget* m_reportList = nullptr;
    MarkdownViewer* m_markdownViewer = nullptr;
    ReportMetadataWidget* m_reportMetadata = nullptr;

    // Targeted scan input state (ephemeral, not persisted)
    QStringList m_targetedInputPaths;
    QStringList m_lastScanReportDirs;
    QWidget* m_targetedInputContainer = nullptr;
    QListWidget* m_targetedInputList = nullptr;
    QLabel* m_targetedInputLabel = nullptr;
    QPushButton* m_btnClearTargeted = nullptr;

    // Papyrus monitoring state
    PapyrusDialog* m_papyrusDialog = nullptr;

    // Data root paths
    QString m_dataRoot;
    QString m_dataDir;
    bool m_updateCheckOnStartup = true;
    bool m_autoSwitchToResultsAfterScan = true;
    QString m_gameVersion = QStringLiteral("auto");
    bool m_showFormIdValues = false;
    bool m_fcxMode = false;
    bool m_simplifyLogs = false;
    bool m_moveUnsolvedLogs = false;
    QString m_unsolvedLogsDestination;
    int m_maxConcurrentScans = 0;
    QElapsedTimer m_crashScanTimer;
    int m_crashScanTotalLogs = 0;
    int m_crashScanLogsCompleted = 0;
    bool m_crashScanInProgress = false;

    // Per-tab window geometry
    int m_lastTabIndex = -1;
    bool m_geometryInitialized = false;

    static constexpr int TAB_COUNT = 4;
    static constexpr struct {
        int minWidth;
        int minHeight;
    } kTabMinSizes[TAB_COUNT] = {
        {640, 500}, // Main Options
        {750, 580}, // File Backup
        {550, 350}, // Articles
        {750, 450}, // Results
    };
    static constexpr const char* kTabNames[TAB_COUNT] = {"main_tab", "backups_tab", "articles_tab", "results_tab"};
};
