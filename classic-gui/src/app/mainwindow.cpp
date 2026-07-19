#include "mainwindow.h"

#include <cstdint>
#include <filesystem>
#include <limits>
#include <QApplication>
#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QDragEnterEvent>
#include <QDragMoveEvent>
#include <QDropEvent>
#include <QEvent>
#include <QFile>
#include <QFileDialog>
#include <QFileInfo>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QLayout>
#include <QMessageBox>
#include <QMimeData>
#include <QSet>
#include <QSizePolicy>
#include <QSpacerItem>
#include <QSplitter>
#include <QTextStream>
#include <QThread>
#include <QTimer>
#include <QVBoxLayout>
#include <string>
#include <vector>

#include "app/aboutdialog.h"
#include "app/papyrusdialog.h"
#include "app/pathdialog.h"
#include "app/settingsdialog.h"
#include "controllers/backupcontroller.h"
#include "controllers/gamefilescontroller.h"
#include "controllers/resultscontroller.h"
#include "controllers/scancontroller.h"
#include "core/gamepathutils.h"
#include "core/gamesetupusersettings.h"
#include "core/guiusersettings.h"
#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"
#include "core/threadmanager.h"
#include "widgets/markdownviewer.h"
#include "widgets/reportlistwidget.h"
#include "widgets/reportmetadatawidget.h"
#include "workers/papyrusworker.h"
#include "workers/updateworker.h"

#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/files.h"
#include "classic_cxx_bridge/game.h"
#include "classic_cxx_bridge/message.h"
#include "classic_cxx_bridge/path.h"
#include "classic_cxx_bridge/registry.h"
#include "classic_cxx_bridge/scangame.h"
#include "classic_cxx_bridge/settings.h"
#include "classic_cxx_bridge/xse.h"
#include "rust/cxx.h"

#include <QDateTime>
#include <QDesktopServices>
#include <QElapsedTimer>
#include <QGroupBox>
#include <QTabBar>
#include <QUrl>

namespace fs = std::filesystem;

namespace {
QString format_elapsed_seconds(const QElapsedTimer& timer)
{
    const qint64 elapsedMs = timer.isValid() ? timer.elapsed() : 0;
    return QString::number(static_cast<double>(elapsedMs) / 1000.0, 'f', 1);
}

/// Returns the stable GUI label for the #146 scan-run Local Ignore state inventory.
QString localIgnoreStateLabel(classic::scanner::ScanRunLocalIgnoreYamlDataState state)
{
    using State = classic::scanner::ScanRunLocalIgnoreYamlDataState;
    switch (state) {
    case State::Existing:
        return QStringLiteral("existing");
    case State::Generated:
        return QStringLiteral("generated");
    case State::RecoveryRequired:
        return QStringLiteral("recovery required");
    case State::ProceedWithoutIgnore:
        return QStringLiteral("proceed without Ignore");
    case State::ResetToDefault:
        return QStringLiteral("reset to default");
    }
    return QStringLiteral("unknown");
}

/// Returns the stable GUI label for every selected YAML Data provenance.
QString installedYamlDataProvenanceLabel(classic::scanner::ScanRunInstalledYamlDataProvenance provenance)
{
    using Provenance = classic::scanner::ScanRunInstalledYamlDataProvenance;
    switch (provenance) {
    case Provenance::Updated:
        return QStringLiteral("updated");
    case Provenance::Previous:
        return QStringLiteral("previous");
    case Provenance::Bundled:
        return QStringLiteral("bundled");
    }
    return QStringLiteral("unknown");
}

/// Returns the stable GUI label for the #146 scan-run Installed YAML Data diagnostic inventory.
QString installedYamlDataDiagnosticKindLabel(classic::scanner::ScanRunInstalledYamlDataDiagnosticKind kind)
{
    using Kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind;
    switch (kind) {
    case Kind::CacheUnavailable:
        return QStringLiteral("cache unavailable");
    case Kind::Missing:
        return QStringLiteral("missing");
    case Kind::Read:
        return QStringLiteral("read");
    case Kind::InvalidUtf8:
        return QStringLiteral("invalid UTF-8");
    case Kind::Parse:
        return QStringLiteral("parse");
    case Kind::InvalidSchema:
        return QStringLiteral("invalid schema");
    case Kind::IncompatibleSchema:
        return QStringLiteral("incompatible schema");
    case Kind::InvalidRoleData:
        return QStringLiteral("invalid role data");
    case Kind::LocalIgnoreGenerated:
        return QStringLiteral("local ignore generated");
    case Kind::LocalIgnoreReset:
        return QStringLiteral("local ignore reset");
    }
    return QStringLiteral("unknown");
}

/// Resolve an existing Fallout 4 script-extender log to use as a setup detection hint.
/// The selected version controls preference, while checking both names keeps auto-detected VR installs working.
QString resolveExistingXseLogPath(const QString& yamlData, const QString& game, const QString& selectedGameVersion,
                                  const QString& configuredDocsRoot)
{
    const auto resolvedFolder = classic::xse::resolve_xse_folder_for_scan(
        classic::toRustString(yamlData), classic::toRustString(game), classic::toRustString(selectedGameVersion),
        classic::toRustString(configuredDocsRoot));
    if (resolvedFolder.empty()) {
        return {};
    }

    const QDir xseFolder(classic::toQString(resolvedFolder));
    const bool preferVrLog = selectedGameVersion.compare(QStringLiteral("VR"), Qt::CaseInsensitive) == 0;
    const QStringList logNames = preferVrLog ? QStringList{QStringLiteral("f4sevr.log"), QStringLiteral("f4se.log")}
                                             : QStringList{QStringLiteral("f4se.log"), QStringLiteral("f4sevr.log")};
    for (const QString& logName : logNames) {
        const QString logPath = QDir::cleanPath(xseFolder.filePath(logName));
        if (QFileInfo(logPath).isFile()) {
            return logPath;
        }
    }

    return {};
}

void logUpdateCheckFailure(const QString& errorMessage)
{
    const QString detail = errorMessage.isEmpty() ? QStringLiteral("unknown error") : errorMessage;
    const std::string message = (QStringLiteral("Update check failed: ") + detail).toStdString();
    classic::message::log_warning(message);
}

QString localYamlFilePath(const QString& dataDir, const QString& game)
{
    return dataDir + QStringLiteral("/CLASSIC %1 Local.yaml").arg(game);
}

bool saveLocalYamlPaths(const QString& dataDir, const QString& game, const QString& gamePath, const QString& docsPath,
                        QString* errorOut)
{
    if (dataDir.isEmpty()) {
        if (errorOut) {
            *errorOut = QStringLiteral("CLASSIC Data directory path is empty.");
        }
        return false;
    }

    if (gamePath.isEmpty() && docsPath.isEmpty()) {
        return true;
    }

    const QString localYamlPath = localYamlFilePath(dataDir, game);

    try {
        classic::config::save_local_yaml_paths(std::string(localYamlPath.toUtf8().constData()),
                                               std::string(gamePath.toUtf8().constData()),
                                               std::string(docsPath.toUtf8().constData()));
        return true;
    } catch (const rust::Error& e) {
        if (errorOut) {
            *errorOut = QStringLiteral("Failed to update local YAML: ") + QString::fromUtf8(e.what());
        }
        return false;
    }
}

/// Formats the structured diagnostics retained by the typed Game Setup snapshot.
QString formatUserSettingsDiagnostics(const classic::gui::GameSetupUserSettingsSnapshot& snapshot)
{
    QStringList lines;
    for (const auto& diagnostic : snapshot.diagnostics) {
        lines.append(QStringLiteral("[%1] %2").arg(diagnostic.code, diagnostic.message));
    }
    return lines.join(QLatin1Char('\n'));
}

/// Presents degraded User Settings state without attempting repair or persistence.
void presentDegradedUserSettings(QWidget* parent, const classic::gui::GameSetupUserSettingsSnapshot& snapshot)
{
    if (snapshot.commitEligibility != QStringLiteral("blocked_untrusted")) {
        return;
    }

    QString detail = formatUserSettingsDiagnostics(snapshot);
    if (!detail.isEmpty()) {
        detail.prepend(QStringLiteral("\n\n"));
    }
    QMessageBox::warning(parent, QStringLiteral("User Settings Need Attention"),
                         QStringLiteral("The %1 User Settings document could not be trusted. "
                                        "CLASSIC will use safety-adjusted values and will not write to it.%2")
                             .arg(snapshot.classification, detail));
}

/// Offers the revision-anchored migration plan and applies or restores it only after explicit user actions.
bool offerUserSettingsMigration(QWidget* parent, const QString& classicRoot)
{
    const std::string root(classicRoot.toUtf8().constData());
    const auto plan = classic::settings::user_settings_plan_migration(root);
    if (!plan.has_plan) {
        QStringList diagnostics;
        for (const auto& diagnostic : plan.diagnostics) {
            diagnostics.append(QStringLiteral("[%1] %2").arg(classic::toQString(diagnostic.code),
                                                             classic::toQString(diagnostic.message)));
        }
        QMessageBox::warning(parent, QStringLiteral("User Settings Migration"),
                             QStringLiteral("CLASSIC could not prepare a safe migration plan.\n\n%1")
                                 .arg(diagnostics.join(QLatin1Char('\n'))));
        return false;
    }

    QStringList changes;
    for (const auto& change : plan.changes) {
        QString row = classic::toQString(change.kind);
        if (change.has_source_path || change.has_target_path) {
            row += QStringLiteral(": %1 -> %2")
                       .arg(change.has_source_path ? classic::toQString(change.source_path) : QStringLiteral("(none)"),
                            change.has_target_path ? classic::toQString(change.target_path) : QStringLiteral("(none)"));
        }
        changes.append(row);
    }

    const QString question =
        QStringLiteral(
            "This User Settings document requires an explicit migration before updates can be saved. "
            "CLASSIC will retain and verify a byte-exact backup before publishing the migrated file.\n\n%1\n\n"
            "Apply this migration now?")
            .arg(changes.join(QLatin1Char('\n')));
    if (QMessageBox::question(parent, QStringLiteral("User Settings Migration"), question, QMessageBox::Yes,
                              QMessageBox::No) != QMessageBox::Yes) {
        return false;
    }

    try {
        auto handle = classic::settings::user_settings_apply_migration(root, plan);
        const auto outcome = classic::settings::user_settings_migration_apply_outcome(*handle);
        if (classic::toQString(outcome.status) == QStringLiteral("conflict")) {
            QMessageBox::warning(
                parent, QStringLiteral("User Settings Changed"),
                QStringLiteral(
                    "User Settings changed before the migration could be committed.\n\nExpected: %1\nFound: %2")
                    .arg(classic::toQString(outcome.expected_revision), classic::toQString(outcome.actual_revision)));
            return false;
        }
        if (!outcome.has_receipt) {
            QMessageBox::warning(parent, QStringLiteral("User Settings Migration"),
                                 QStringLiteral("Migration completed without a verified restore receipt."));
            return false;
        }

        QMessageBox completed(parent);
        completed.setIcon(QMessageBox::Information);
        completed.setWindowTitle(QStringLiteral("User Settings Migrated"));
        completed.setText(QStringLiteral("User Settings were migrated and reopened successfully."));
        completed.setInformativeText(QStringLiteral("Verified backup: %1\nBackup revision: %2\nPublished revision: %3")
                                         .arg(classic::toQString(outcome.receipt.backup_path),
                                              classic::toQString(outcome.receipt.backup_revision),
                                              classic::toQString(outcome.receipt.published_revision)));
        completed.addButton(QStringLiteral("Keep Migrated Settings"), QMessageBox::AcceptRole);
        auto* restoreButton =
            completed.addButton(QStringLiteral("Restore Verified Backup"), QMessageBox::DestructiveRole);
        completed.exec();

        if (completed.clickedButton() == restoreButton) {
            const auto restored = classic::settings::user_settings_restore_migration(root, *handle);
            if (classic::toQString(restored.status) == QStringLiteral("conflict")) {
                QMessageBox::warning(
                    parent, QStringLiteral("User Settings Restore Conflict"),
                    QStringLiteral("The migrated document changed before restore.\n\nExpected: %1\nFound: %2")
                        .arg(classic::toQString(restored.expected_revision),
                             classic::toQString(restored.actual_revision)));
                return false;
            }
            QMessageBox::information(parent, QStringLiteral("User Settings Restored"),
                                     QStringLiteral("The verified pre-migration document was restored successfully."));
        }
        return true;
    } catch (const rust::Error& error) {
        QMessageBox::warning(parent, QStringLiteral("User Settings Migration Failed"), QString::fromUtf8(error.what()));
        return false;
    }
}
} // namespace

// ── Construction / Destruction ─────────────────────────────────────

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
{
    setAcceptDrops(true);
    setupUi();
    loadStylesheet();
    loadSettings();
    initializeControllers();
    connectSignals();
    runStartupWorkflows();
}

MainWindow::~MainWindow()
{
    if (m_geometryInitialized && m_lastTabIndex >= 0) {
        saveTabGeometry(m_lastTabIndex);
    }
}

void MainWindow::initializeControllers()
{
    m_signalHub = &SignalHub::instance();
    m_threadManager = new ThreadManager(this);
    m_scanController = new ScanController(m_signalHub, m_threadManager, this);
    m_gameFilesController = new GameFilesController(m_signalHub, m_threadManager, this);
    m_backupController = new BackupController(QString(), m_signalHub, this);
    m_resultsController =
        new ResultsController(m_signalHub, m_tabWidget, m_reportList, m_markdownViewer, m_reportMetadata, this);
    m_resultsController->setAutoSwitchToResults(m_autoSwitchToResultsAfterScan);
}

void MainWindow::runStartupWorkflows()
{
    initResultsReportDir();
    checkFirstRunPaths();

    // Startup update check (silent unless update/error), matching PySide6 behavior.
    if (m_updateCheckOnStartup) {
        QTimer::singleShot(0, this, [this]() { checkForUpdates(false); });
    }
}

// ── Public interface ───────────────────────────────────────────────

void MainWindow::setVersion(const QString& version)
{
    setWindowTitle(QStringLiteral("CLASSIC ") + version);
}

void MainWindow::setStatusMessage(const QString& message)
{
    QString fmt = message;
    // QProgressBar format strings treat %p/%v/%m as placeholders.
    // Escape only those tokens so normal percent signs render once.
    fmt.replace(QStringLiteral("%p"), QStringLiteral("%%p"));
    fmt.replace(QStringLiteral("%v"), QStringLiteral("%%v"));
    fmt.replace(QStringLiteral("%m"), QStringLiteral("%%m"));
    m_progressBar->setFormat(fmt);
}

// ── UI Setup ───────────────────────────────────────────────────────

void MainWindow::setupUi()
{
    // Main tab minimum/default geometry.
    resize(kTabMinSizes[0].minWidth, kTabMinSizes[0].minHeight);
    setMinimumSize(kTabMinSizes[0].minWidth, kTabMinSizes[0].minHeight);
    setWindowTitle(QStringLiteral("CLASSIC"));

    // Central tab widget
    m_tabWidget = new QTabWidget(this);
    auto* tabBar = m_tabWidget->tabBar();
    tabBar->setElideMode(Qt::ElideRight);
    tabBar->setExpanding(true);
    tabBar->setUsesScrollButtons(false);
    setCentralWidget(m_tabWidget);

    // Progress bar as unified status display (text renders on top of fill)
    m_progressBar = new AdaptiveProgressBar(this);
    m_progressBar->setTextVisible(true);
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    m_progressBar->setFormat(QStringLiteral("Ready"));
    statusBar()->addWidget(m_progressBar, 1);

    // Build each tab
    setupMainOptionsTab();
    setupFileBackupTab();
    setupArticlesTab();
    setupResultsTab();
}

void MainWindow::setupMainOptionsTab()
{
    auto* tabWidget = new QWidget();
    auto* mainLayout = new QVBoxLayout(tabWidget);
    mainLayout->setContentsMargins(16, 16, 16, 16);
    mainLayout->setSpacing(8);

    // ── Folder inputs section ──────────────────────────────────────
    // Row 1: Staging Mods Folder
    {
        auto* rowLayout = new QHBoxLayout();
        auto* label = new QLabel(QStringLiteral("Staging Mods Folder:"));
        label->setFixedWidth(150);
        m_editStagingFolder = new QLineEdit();
        m_editStagingFolder->setPlaceholderText(QStringLiteral("Path to staging mods folder..."));
        auto* btnBrowse = new QPushButton(QStringLiteral("Browse"));
        btnBrowse->setObjectName(QStringLiteral("btnBrowseStaging"));
        btnBrowse->setFixedWidth(80);
        rowLayout->addWidget(label);
        rowLayout->addWidget(m_editStagingFolder);
        rowLayout->addWidget(btnBrowse);
        mainLayout->addLayout(rowLayout);

        connect(btnBrowse, &QPushButton::clicked, this, &MainWindow::onBrowseStaging);
    }

    // Row 2: Custom Scan Folder
    {
        auto* rowLayout = new QHBoxLayout();
        auto* label = new QLabel(QStringLiteral("Custom Scan Folder:"));
        label->setFixedWidth(150);
        m_editCustomFolder = new QLineEdit();
        m_editCustomFolder->setPlaceholderText(QStringLiteral("Path to custom scan folder..."));
        auto* btnBrowse = new QPushButton(QStringLiteral("Browse"));
        btnBrowse->setObjectName(QStringLiteral("btnBrowseCustom"));
        btnBrowse->setFixedWidth(80);
        rowLayout->addWidget(label);
        rowLayout->addWidget(m_editCustomFolder);
        rowLayout->addWidget(btnBrowse);
        mainLayout->addLayout(rowLayout);

        connect(btnBrowse, &QPushButton::clicked, this, &MainWindow::onBrowseCustom);
    }

    // ── Targeted scan drop zone ───────────────────────────────────
    {
        m_targetedInputContainer = new QWidget();
        auto* containerLayout = new QVBoxLayout(m_targetedInputContainer);
        containerLayout->setContentsMargins(0, 4, 0, 0);
        containerLayout->setSpacing(4);

        auto* headerRow = new QHBoxLayout();
        m_targetedInputLabel = new QLabel(QStringLiteral("Targeted Scan: drop files or folders here"));
        m_targetedInputLabel->setStyleSheet(QStringLiteral("color: #888; font-style: italic;"));
        headerRow->addWidget(m_targetedInputLabel);
        headerRow->addStretch();

        m_btnClearTargeted = new QPushButton(QStringLiteral("Clear"));
        m_btnClearTargeted->setObjectName(QStringLiteral("btnClearTargeted"));
        m_btnClearTargeted->setMinimumWidth(qMax(80, m_btnClearTargeted->sizeHint().width()));
        m_btnClearTargeted->setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
        m_btnClearTargeted->setVisible(false);
        headerRow->addWidget(m_btnClearTargeted);
        containerLayout->addLayout(headerRow);

        m_targetedInputList = new QListWidget();
        m_targetedInputList->setFixedHeight(90);
        m_targetedInputList->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        m_targetedInputList->setVisible(false);
        containerLayout->addWidget(m_targetedInputList);

        mainLayout->addWidget(m_targetedInputContainer);

        connect(m_btnClearTargeted, &QPushButton::clicked, this, &MainWindow::onClearTargetedInputs);
        installTargetedDropForwarding();
    }

    // Spacer before primary buttons
    mainLayout->addSpacerItem(new QSpacerItem(20, 20, QSizePolicy::Minimum, QSizePolicy::Expanding));

    // ── Primary action buttons ─────────────────────────────────────
    {
        auto* btnLayout = new QHBoxLayout();
        btnLayout->setSpacing(12);

        m_btnScanCrashLogs = new QPushButton(QStringLiteral("SCAN CRASH LOGS"));
        m_btnScanCrashLogs->setObjectName(QStringLiteral("btnScanCrashLogs"));
        m_btnScanCrashLogs->setFixedHeight(48);

        m_btnScanGameFiles = new QPushButton(QStringLiteral("SCAN GAME FILES"));
        m_btnScanGameFiles->setObjectName(QStringLiteral("btnScanGameFiles"));
        m_btnScanGameFiles->setFixedHeight(48);

        btnLayout->addWidget(m_btnScanCrashLogs);
        btnLayout->addWidget(m_btnScanGameFiles);
        mainLayout->addLayout(btnLayout);
    }

    // Spacer after primary buttons
    mainLayout->addSpacerItem(new QSpacerItem(20, 20, QSizePolicy::Minimum, QSizePolicy::Expanding));

    // ── Bottom row 1: utility buttons ──────────────────────────────
    {
        auto* rowLayout = new QHBoxLayout();
        rowLayout->setSpacing(8);

        m_btnAbout = new QPushButton(QStringLiteral("ABOUT"));
        m_btnHelp = new QPushButton(QStringLiteral("HELP"));
        m_btnSettings = new QPushButton(QStringLiteral("SETTINGS"));
        m_btnOpenCrashLogs = new QPushButton(QStringLiteral("OPEN CRASH LOGS"));
        m_btnCheckUpdates = new QPushButton(QStringLiteral("CHECK UPDATES"));

        rowLayout->addWidget(m_btnAbout);
        rowLayout->addWidget(m_btnHelp);
        rowLayout->addWidget(m_btnSettings);
        rowLayout->addWidget(m_btnOpenCrashLogs);
        rowLayout->addWidget(m_btnCheckUpdates);

        mainLayout->addLayout(rowLayout);
    }

    // ── Bottom row 2: monitoring + exit ────────────────────────────
    {
        auto* rowLayout = new QHBoxLayout();
        rowLayout->setSpacing(8);

        m_btnPapyrusMonitor = new QPushButton(QStringLiteral("START PAPYRUS MONITORING"));
        m_btnPapyrusMonitor->setCheckable(true);
        m_btnPapyrusMonitor->setObjectName(QStringLiteral("btnPapyrusMonitor"));

        m_btnExit = new QPushButton(QStringLiteral("EXIT"));

        rowLayout->addWidget(m_btnPapyrusMonitor);
        rowLayout->addStretch();
        rowLayout->addWidget(m_btnExit);

        mainLayout->addLayout(rowLayout);
    }

    m_tabWidget->addTab(tabWidget, QStringLiteral("MAIN OPTIONS"));
}

void MainWindow::setupFileBackupTab()
{
    auto* tabWidget = new QWidget();
    auto* mainLayout = new QVBoxLayout(tabWidget);
    mainLayout->setContentsMargins(16, 16, 16, 16);
    mainLayout->setSpacing(12);

    // ── Header instruction labels ─────────────────────────────────
    {
        auto* headerLabel = new QLabel(QStringLiteral("BACKUP / RESTORE / REMOVE"));
        headerLabel->setProperty("class", QStringLiteral("sectionHeader"));
        headerLabel->setAlignment(Qt::AlignCenter);
        mainLayout->addWidget(headerLabel);

        auto* instructionLabel =
            new QLabel(QStringLiteral("Create backups of game files before modifying them. "
                                      "Restore to revert changes, or remove backups when no longer needed."));
        instructionLabel->setAlignment(Qt::AlignCenter);
        instructionLabel->setWordWrap(true);
        mainLayout->addWidget(instructionLabel);
    }

    // ── Helper lambda: create a backup section group box ──────────
    // Each section has 3 buttons: BACKUP, RESTORE, REMOVE
    auto createBackupSection = [this](const QString& title, const QString& backupType) -> QGroupBox* {
        auto* group = new QGroupBox(title);
        auto* layout = new QHBoxLayout(group);
        layout->setSpacing(8);

        auto* btnBackup = new QPushButton(QStringLiteral("BACKUP"));
        auto* btnRestore = new QPushButton(QStringLiteral("RESTORE"));
        auto* btnRemove = new QPushButton(QStringLiteral("REMOVE"));

        // Fixed button widths for consistent layout
        btnBackup->setFixedHeight(32);
        btnRestore->setFixedHeight(32);
        btnRemove->setFixedHeight(32);

        layout->addWidget(btnBackup);
        layout->addWidget(btnRestore);
        layout->addWidget(btnRemove);

        // Connect buttons to BackupController with the backup type
        connect(btnBackup, &QPushButton::clicked, this,
                [this, backupType]() { m_backupController->backup(backupType); });
        connect(btnRestore, &QPushButton::clicked, this,
                [this, backupType]() { m_backupController->restore(backupType); });
        connect(btnRemove, &QPushButton::clicked, this,
                [this, backupType]() { m_backupController->remove(backupType); });

        return group;
    };

    // ── 4 Backup sections ─────────────────────────────────────────
    mainLayout->addWidget(createBackupSection(QStringLiteral("Script Extender (XSE)"), QStringLiteral("xse")));
    mainLayout->addWidget(createBackupSection(QStringLiteral("ReShade"), QStringLiteral("reshade")));
    mainLayout->addWidget(createBackupSection(QStringLiteral("Vulkan"), QStringLiteral("vulkan")));
    mainLayout->addWidget(createBackupSection(QStringLiteral("ENB"), QStringLiteral("enb")));

    // ── Spacer ────────────────────────────────────────────────────
    mainLayout->addStretch();

    // ── Open Backups Folder button ────────────────────────────────
    {
        auto* btnOpenBackups = new QPushButton(QStringLiteral("OPEN CLASSIC BACKUPS"));
        btnOpenBackups->setFixedHeight(36);
        mainLayout->addWidget(btnOpenBackups);

        connect(btnOpenBackups, &QPushButton::clicked, this, &MainWindow::onOpenBackupsFolder);
    }

    m_tabWidget->addTab(tabWidget, QStringLiteral("FILE BACKUP"));
}

void MainWindow::setupArticlesTab()
{
    auto* tabWidget = new QWidget();
    auto* mainLayout = new QVBoxLayout(tabWidget);
    mainLayout->setContentsMargins(16, 16, 16, 16);
    mainLayout->setSpacing(12);

    // Header
    auto* headerLabel = new QLabel(QStringLiteral("USEFUL RESOURCES & LINKS"));
    headerLabel->setProperty("class", QStringLiteral("sectionHeader"));
    headerLabel->setAlignment(Qt::AlignCenter);
    mainLayout->addWidget(headerLabel);

    // 3x3 grid of URL buttons
    auto* grid = new QGridLayout();
    grid->setSpacing(8);

    // Article data: {text, url} in row-major order
    struct ArticleLink {
        const char* text;
        const char* url;
    };
    static constexpr ArticleLink links[] = {
        {"BUFFOUT 4 INSTALLATION", "https://www.nexusmods.com/fallout4/articles/3115"},
        {"FALLOUT 4 SETUP TIPS", "https://www.nexusmods.com/fallout4/articles/4141"},
        {"IMPORTANT PATCHES LIST", "https://www.nexusmods.com/fallout4/articles/3769"},
        {"BUFFOUT 4 NEXUS", "https://www.nexusmods.com/fallout4/mods/47359"},
        {"CLASSIC NEXUS", "https://www.nexusmods.com/fallout4/mods/56255"},
        {"CLASSIC GITHUB", "https://github.com/evildarkarchon/CLASSIC-Fallout4"},
        {"DDS TEXTURE SCANNER", "https://www.nexusmods.com/fallout4/mods/71588"},
        {"BETHINI PIE", "https://www.nexusmods.com/site/mods/631"},
        {"WRYE BASH", "https://www.nexusmods.com/fallout4/mods/20032"},
    };

    for (int i = 0; i < 9; ++i) {
        auto* btn = new QPushButton(QString::fromUtf8(links[i].text));
        btn->setFixedHeight(36);
        btn->setCursor(Qt::PointingHandCursor);

        // Capture URL by value for the lambda
        QString url = QString::fromUtf8(links[i].url);
        connect(btn, &QPushButton::clicked, this, [url]() { QDesktopServices::openUrl(QUrl(url)); });

        grid->addWidget(btn, i / 3, i % 3);
    }

    mainLayout->addLayout(grid);
    mainLayout->addStretch();

    m_tabWidget->addTab(tabWidget, QStringLiteral("ARTICLES"));
}

void MainWindow::setupResultsTab()
{
    auto* tabWidget = new QWidget();
    auto* layout = new QVBoxLayout(tabWidget);
    layout->setContentsMargins(8, 8, 8, 8);
    layout->setSpacing(0);

    // Horizontal splitter: report list (left) | viewer (right)
    auto* splitter = new QSplitter(Qt::Horizontal);

    // Left panel: report list
    m_reportList = new ReportListWidget();
    splitter->addWidget(m_reportList);

    // Right panel: metadata bar + markdown viewer
    auto* rightPanel = new QWidget();
    auto* rightLayout = new QVBoxLayout(rightPanel);
    rightLayout->setContentsMargins(0, 0, 0, 0);
    rightLayout->setSpacing(4);

    m_reportMetadata = new ReportMetadataWidget();
    rightLayout->addWidget(m_reportMetadata);

    m_markdownViewer = new MarkdownViewer();
    rightLayout->addWidget(m_markdownViewer, 1);

    splitter->addWidget(rightPanel);

    // Initial 30%/70% split ratio
    splitter->setStretchFactor(0, 3);
    splitter->setStretchFactor(1, 7);

    layout->addWidget(splitter);

    m_tabWidget->addTab(tabWidget, QStringLiteral("RESULTS"));
}

// ── Stylesheet ─────────────────────────────────────────────────────

void MainWindow::loadStylesheet()
{
    // Try loading from the application directory first (deployed)
    QString appDir = QCoreApplication::applicationDirPath();
    QString stylePath = appDir + QStringLiteral("/styles/dark_theme.qss");

    QFile styleFile(stylePath);
    if (!styleFile.exists()) {
        // Fallback: source tree path relative to exe (dev builds)
        stylePath = appDir + QStringLiteral("/../src/styles/dark_theme.qss");
        styleFile.setFileName(stylePath);
    }

    if (styleFile.open(QFile::ReadOnly | QFile::Text)) {
        QTextStream stream(&styleFile);
        QString stylesheet = stream.readAll();
        styleFile.close();
        qApp->setStyleSheet(stylesheet);
    }
}

// ── Signal connections ─────────────────────────────────────────────

void MainWindow::connectSignals()
{
    // Scan buttons
    connect(m_btnScanCrashLogs, &QPushButton::clicked, this, &MainWindow::onScanCrashLogs);
    connect(m_btnScanGameFiles, &QPushButton::clicked, this, &MainWindow::onScanGameFiles);

    // Exit button
    connect(m_btnExit, &QPushButton::clicked, this, &MainWindow::onExit);

    // Per-tab window geometry
    connect(m_tabWidget, &QTabWidget::currentChanged, this, &MainWindow::onTabChanged);

    // Custom scan folder validation on manual edit
    connect(m_editCustomFolder, &QLineEdit::editingFinished, this, &MainWindow::onCustomFolderEdited);

    // ScanController → MainWindow
    connect(m_scanController, &ScanController::scanProgress, this, &MainWindow::onCrashScanProgress);
    connect(m_scanController, &ScanController::scanDiscovered, this, &MainWindow::onCrashScanDiscovered);
    connect(m_scanController, &ScanController::scanLogScanned, this, &MainWindow::onCrashLogScanned);
    connect(m_scanController, &ScanController::scanFinished, this, &MainWindow::onScanCompleted);
    connect(m_scanController, &ScanController::scanNoLogsFound, this, &MainWindow::onScanNoLogsFound);
    connect(m_scanController, &ScanController::scanCancelled, this, &MainWindow::onScanCancelled);
    connect(m_scanController, &ScanController::scanError, this, &MainWindow::onScanError);
    connect(m_scanController, &ScanController::scanWarning, this, &MainWindow::onScanWarning);
    connect(m_scanController, &ScanController::scanReportDirectoriesResolved, this,
            &MainWindow::onScanReportDirectoriesResolved);
    connect(m_scanController, &ScanController::scanInstalledYamlDataResolved, this,
            &MainWindow::onScanInstalledYamlDataResolved);

    // Settings button
    connect(m_btnSettings, &QPushButton::clicked, this, &MainWindow::onShowSettings);

    // Re-read settings when they change (e.g. from SettingsDialog)
    connect(m_signalHub, &SignalHub::settingsChanged, this, &MainWindow::loadSettings);

    // GameFilesController → MainWindow
    connect(m_gameFilesController, &GameFilesController::scanProgress, this, &MainWindow::onScanProgress);
    connect(m_gameFilesController, &GameFilesController::scanFinished, this, &MainWindow::onGameFilesScanFinished);
    connect(m_gameFilesController, &GameFilesController::scanError, this, &MainWindow::onGameFilesScanError);

    // BackupController → MainWindow
    connect(m_backupController, &BackupController::operationCompleted, this, &MainWindow::onBackupCompleted);
    connect(m_backupController, &BackupController::operationError, this, &MainWindow::onBackupError);

    // About button -- show the About dialog
    connect(m_btnAbout, &QPushButton::clicked, this, [this]() {
        AboutDialog dlg(this);
        dlg.exec();
    });

    // Help button -- show in-app help from YAML content
    connect(m_btnHelp, &QPushButton::clicked, this, [this]() {
        if (m_dataDir.isEmpty()) {
            QMessageBox::warning(this, QStringLiteral("Error"), QStringLiteral("CLASSIC Data directory not found."));
            return;
        }

        QString mainYamlPath = m_dataDir + QStringLiteral("/databases/CLASSIC Main.yaml");
        try {
            auto ops = classic::settings::yaml_ops_new();
            classic::settings::yaml_ops_load_file(*ops, std::string(mainYamlPath.toUtf8().constData()));
            auto helpText = classic::settings::yaml_ops_get_string(*ops, "CLASSIC_Interface.help_popup_main", "");
            if (!helpText.empty()) {
                QMessageBox::information(this, QStringLiteral("NEED HELP?"), classic::toQString(helpText));
            } else {
                QMessageBox::warning(this, QStringLiteral("Help"), QStringLiteral("Help content not available."));
            }
        } catch (...) {
            QMessageBox::warning(this, QStringLiteral("Help"), QStringLiteral("Failed to load help content."));
        }
    });

    // Open Crash Logs -- open the crash logs directory in file explorer
    connect(m_btnOpenCrashLogs, &QPushButton::clicked, this, [this]() {
        QString crashDir = readCrashLogsDir();
        if (crashDir.isEmpty()) {
            QMessageBox::warning(this, QStringLiteral("Error"),
                                 QStringLiteral("Crash logs directory is not configured. "
                                                "Please set it in Settings."));
            return;
        }

        QDesktopServices::openUrl(QUrl::fromLocalFile(crashDir));
    });

    // Check Updates -- run update check in a background thread
    connect(m_btnCheckUpdates, &QPushButton::clicked, this, &MainWindow::onCheckUpdates);

    // Papyrus Monitor -- toggle monitoring on/off
    connect(m_btnPapyrusMonitor, &QPushButton::clicked, this, &MainWindow::onTogglePapyrusMonitor);
}

// ── Settings persistence ───────────────────────────────────────────

void MainWindow::loadSettings()
{
    m_guiSettings = classic::gui::GuiUserSettings::publishedDefaults();
    m_updateCheckOnStartup = m_guiSettings.update.updateCheck;
    m_autoSwitchToResultsAfterScan = m_guiSettings.frontend.autoSwitchAfterScan;

    m_dataRoot = findDataRoot();
    if (m_dataRoot.isEmpty()) {
        m_dataDir = QString();
        return;
    }
    m_dataDir = m_dataRoot + QStringLiteral("/CLASSIC Data");

    auto setup = classic::gui::GameSetupUserSettings::open(m_dataRoot);
    if (setup.classification == QStringLiteral("missing")) {
        const auto choice = QMessageBox::question(
            this, QStringLiteral("Create User Settings"),
            QStringLiteral(
                "No User Settings document exists. Create one from Rust-owned published defaults?\n\n"
                "Choosing No leaves the filesystem unchanged; CLASSIC can continue with in-memory defaults."),
            QMessageBox::Yes, QMessageBox::No);
        if (choice == QMessageBox::Yes) {
            const auto result = classic::gui::GameSetupUserSettings::bootstrap(m_dataRoot);
            if (result.status == QStringLiteral("committed")) {
                setup = classic::gui::GameSetupUserSettings::open(m_dataRoot);
            } else if (result.status == QStringLiteral("conflict")) {
                QMessageBox::warning(
                    this, QStringLiteral("User Settings Changed"),
                    QStringLiteral("Another process created User Settings before bootstrap completed.\n\n"
                                   "Expected: %1\nFound: %2")
                        .arg(result.expectedRevision, result.actualRevision));
                setup = classic::gui::GameSetupUserSettings::open(m_dataRoot);
            } else {
                QStringList diagnostics;
                for (const auto& diagnostic : result.diagnostics) {
                    diagnostics.append(QStringLiteral("[%1] %2").arg(diagnostic.code, diagnostic.message));
                }
                QMessageBox::warning(this, QStringLiteral("User Settings Bootstrap Failed"),
                                     diagnostics.join(QLatin1Char('\n')));
            }
        }
    } else if (setup.commitEligibility == QStringLiteral("requires_migration")) {
        offerUserSettingsMigration(this, m_dataRoot);
        setup = classic::gui::GameSetupUserSettings::open(m_dataRoot);
    }
    presentDegradedUserSettings(this, setup);

    try {
        m_guiSettings = classic::gui::GuiUserSettings::open(m_dataRoot);
        m_updateCheckOnStartup = m_guiSettings.update.updateCheck;
        m_autoSwitchToResultsAfterScan = m_guiSettings.frontend.autoSwitchAfterScan;
        m_editStagingFolder->setText(m_guiSettings.gameSetup.modsRoot.value_or(QString{}));
        m_editCustomFolder->setText(m_guiSettings.scan.customScanInput.value_or(QString{}));
        if (m_guiSettings.gameSetup.gameRoot.has_value() && m_backupController) {
            m_backupController->setGameRoot(*m_guiSettings.gameSetup.gameRoot);
        }
        if (m_resultsController) {
            m_resultsController->setAutoSwitchToResults(m_autoSwitchToResultsAfterScan);
        }
    } catch (const std::exception& e) {
        setStatusMessage(QStringLiteral("Settings load failed: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        setStatusMessage(QStringLiteral("Settings load failed: unknown error"));
    }

    // Geometry is restored from the same typed snapshot so startup renders one cohesive revision.
    int initialTab = m_tabWidget ? m_tabWidget->currentIndex() : 0;
    restoreTabGeometry(initialTab);
    m_lastTabIndex = initialTab;
    m_geometryInitialized = true;

    // Keep results directory watching in sync when settings are reloaded
    // (e.g. after Settings dialog changes).
    if (m_resultsController) {
        initResultsReportDir();
    }
}

void MainWindow::saveRememberedPath(RememberedPath path)
{
    if (m_dataRoot.isEmpty()) {
        return;
    }

    try {
        classic::gui::GameSetupPathChanges changes;
        if (path == RememberedPath::Staging) {
            changes.modsRoot.selected = true;
            changes.modsRoot.value =
                m_editStagingFolder->text().trimmed().isEmpty()
                    ? std::nullopt
                    : std::optional<QString>{QDir::cleanPath(m_editStagingFolder->text().trimmed())};
        } else {
            changes.customScanInput.selected = true;
            changes.customScanInput.value =
                m_editCustomFolder->text().trimmed().isEmpty()
                    ? std::nullopt
                    : std::optional<QString>{QDir::cleanPath(m_editCustomFolder->text().trimmed())};
        }

        const auto result = m_guiSettings.revision == QStringLiteral("missing")
                                ? classic::gui::GameSetupUserSettings::bootstrapWithSelectedPaths(m_dataRoot, changes)
                                : classic::gui::GameSetupUserSettings::commitSelectedPaths(
                                      m_dataRoot, m_guiSettings.revision, changes);
        if (result.status == QStringLiteral("conflict")) {
            QMessageBox::warning(this, QStringLiteral("User Settings Changed"),
                                 QStringLiteral("User Settings changed before the selected paths could be saved. "
                                                "Reload Settings and try again.\n\nExpected: %1\nFound: %2")
                                     .arg(result.expectedRevision, result.actualRevision));
            return;
        } else if (result.status != QStringLiteral("committed")) {
            QStringList diagnostics;
            for (const auto& diagnostic : result.diagnostics) {
                diagnostics.append(QStringLiteral("[%1] %2").arg(diagnostic.code, diagnostic.message));
            }
            setStatusMessage(QStringLiteral("Settings save rejected: ") + diagnostics.join(QLatin1Char(' ')));
            return;
        }
        // Only refresh the launch cache after Rust confirms the complete path update committed.
        m_guiSettings = classic::gui::GuiUserSettings::open(m_dataRoot);
    } catch (const std::exception& e) {
        setStatusMessage(QStringLiteral("Settings save failed: ") + QString::fromUtf8(e.what()));
        return;
    } catch (...) {
        setStatusMessage(QStringLiteral("Settings save failed: unknown error"));
        return;
    }
}

void MainWindow::initResultsReportDir()
{
    if (!m_resultsController) {
        return;
    }

    const QString crashDir = QDir::cleanPath(readCrashLogsDir().trimmed());
    if (crashDir.isEmpty()) {
        m_resultsController->setReportDirectories(QStringList(), QString());
        return;
    }

    // Ensure the primary Crash Logs directory exists before watching.
    QDir().mkpath(crashDir);

    QStringList reportDirs;
    QSet<QString> seenReportDirs;

    const auto appendUniqueReportDir = [&reportDirs, &seenReportDirs](const QString& rawDir) {
        const QString cleanedDir = QDir::cleanPath(rawDir.trimmed());
        if (cleanedDir.isEmpty()) {
            return;
        }

        const QString key = cleanedDir.toLower();
        if (seenReportDirs.contains(key)) {
            return;
        }

        seenReportDirs.insert(key);
        reportDirs.append(cleanedDir);
    };

    appendUniqueReportDir(crashDir);

    if (m_editCustomFolder) {
        const QString customDir = QDir::cleanPath(m_editCustomFolder->text().trimmed());
        if (!customDir.isEmpty() && QDir(customDir).exists() && customDir.compare(crashDir, Qt::CaseInsensitive) != 0) {
            appendUniqueReportDir(customDir);
        }
    }

    for (const auto& reportDir : m_lastScanReportDirs) {
        appendUniqueReportDir(reportDir);
    }

    m_resultsController->setReportDirectories(reportDirs, crashDir);
}

void MainWindow::checkFirstRunPaths()
{
    if (m_dataDir.isEmpty()) {
        return;
    }

    try {
        auto snapshot = classic::gui::GameSetupUserSettings::open(m_dataRoot);
        const QString configuredDocs = snapshot.documentsRoot.value_or(QString{});
        const QString xseLogPath =
            resolveExistingXseLogPath(m_dataDir, snapshot.managedGame, snapshot.gameVersionSelection, configuredDocs);
        auto intake = classic::gui::GameSetupUserSettings::runIntake(m_dataRoot, xseLogPath);
        classic::gui::GameSetupPathChanges changes;
        bool hasAcceptedChanges = false;

        const auto commitChanges = [this, &snapshot](const classic::gui::GameSetupPathChanges& changes) {
            const auto outcome =
                snapshot.classification == QStringLiteral("missing")
                    ? classic::gui::GameSetupUserSettings::bootstrapWithSelectedPaths(m_dataRoot, changes)
                    : classic::gui::GameSetupUserSettings::commitSelectedPaths(m_dataRoot, snapshot.revision, changes);
            if (outcome.status == QStringLiteral("committed")) {
                return true;
            }
            if (outcome.status == QStringLiteral("conflict")) {
                QMessageBox::warning(this, QStringLiteral("User Settings Changed"),
                                     QStringLiteral("User Settings changed while the accepted setup paths were being "
                                                    "committed. No paths were written.\n\nExpected: %1\nFound: %2")
                                         .arg(outcome.expectedRevision, outcome.actualRevision));
            } else {
                QStringList diagnostics;
                for (const auto& diagnostic : outcome.diagnostics) {
                    diagnostics.append(QStringLiteral("[%1] %2").arg(diagnostic.code, diagnostic.message));
                }
                QMessageBox::warning(this, QStringLiteral("Setup Paths Not Saved"),
                                     diagnostics.join(QLatin1Char('\n')));
            }
            return false;
        };

        if (!intake.pathUpdates.empty()) {
            QStringList proposals;
            for (const auto& proposal : intake.pathUpdates) {
                proposals.append(QStringLiteral("%1: %2").arg(proposal.kind, proposal.path));
                if (proposal.kind == QStringLiteral("game_root")) {
                    changes.gameRoot = {true, proposal.path};
                    if (!intake.gameExecutable.isEmpty()) {
                        changes.gameExecutable = {true, intake.gameExecutable};
                    }
                } else if (proposal.kind == QStringLiteral("docs_root")) {
                    changes.documentsRoot = {true, proposal.path};
                }
            }

            const auto choice = QMessageBox::question(
                this, QStringLiteral("Game Setup Paths Detected"),
                QStringLiteral("Game Setup Intake found these path updates. Save all accepted paths as one User "
                               "Settings update?\n\n%1")
                    .arg(proposals.join(QLatin1Char('\n'))),
                QMessageBox::Yes, QMessageBox::No);
            if (choice != QMessageBox::Yes) {
                return;
            }
            hasAcceptedChanges = true;
        }

        QString gamePath = intake.gameRoot;
        QString docsPath = intake.documentsRoot;
        const bool needsGame = gamePath.isEmpty() || !QDir(gamePath).exists();
        const bool needsDocs = docsPath.isEmpty() || !QDir(docsPath).exists();
        if (needsGame || needsDocs) {
            ManualPathDialog dialog(needsGame, needsDocs, this);
            if (dialog.exec() != QDialog::Accepted) {
                return;
            }

            if (needsGame) {
                gamePath = dialog.gamePath();
                changes.gameRoot = {true, gamePath};
                const auto exeName = classic::path::resolve_fallout4_exe_name(
                    std::string(snapshot.gameVersionSelection.toUtf8().constData()));
                changes.gameExecutable = {true, QDir(gamePath).filePath(classic::toQString(exeName))};
            }
            if (needsDocs) {
                docsPath = dialog.docsPath();
                changes.documentsRoot = {true, docsPath};
            }
            hasAcceptedChanges = true;
        }

        if (hasAcceptedChanges) {
            if (!commitChanges(changes)) {
                return;
            }
            // Accepted startup paths must immediately feed later scan launches and remembered-path
            // actions from the exact revision Rust published, not the pre-intake startup snapshot.
            m_guiSettings = classic::gui::GuiUserSettings::open(m_dataRoot);
        }

        QString localYamlError;
        if (!saveLocalYamlPaths(m_dataDir, QStringLiteral("Fallout4"), gamePath, docsPath, &localYamlError)) {
            setStatusMessage(QStringLiteral("Local YAML sync failed: ") + localYamlError);
        }
        if (m_backupController && !gamePath.isEmpty()) {
            m_backupController->setGameRoot(gamePath);
        }
    } catch (const std::exception& e) {
        setStatusMessage(QStringLiteral("Path detection failed: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        setStatusMessage(QStringLiteral("Path detection failed: unknown error"));
    }
}

QString MainWindow::findDataRoot() const
{
    std::error_code ec;

    QString appDir = QCoreApplication::applicationDirPath();
    fs::path appPath(appDir.toStdWString());
    fs::path cwd = fs::current_path(ec);

    std::vector<fs::path> candidates;
    candidates.push_back(appPath);                             // deployed exe dir
    candidates.push_back(cwd);                                 // launch cwd
    candidates.push_back(appPath.parent_path());               // build dir parent
    candidates.push_back(appPath.parent_path().parent_path()); // repo root from build/*
    candidates.push_back(appPath.parent_path() / "install");   // classic-gui/install
    candidates.push_back(cwd / "install");                     // cwd/install

    for (const auto& base : candidates) {
        if (base.empty()) {
            continue;
        }
        if (fs::is_directory(base / "CLASSIC Data", ec)) {
            return QString::fromStdWString(base.wstring());
        }
    }

    // Fallback: return empty (caller should handle)
    return QString();
}

// ── Per-tab window geometry ────────────────────────────────────────

void MainWindow::saveTabGeometry(int tabIndex)
{
    if (tabIndex < 0 || tabIndex >= TAB_COUNT || m_dataRoot.isEmpty()) {
        return;
    }

    if (m_guiSettings.classification != QStringLiteral("current") ||
        m_guiSettings.commitEligibility != QStringLiteral("eligible")) {
        return;
    }

    try {
        const bool maximized = isMaximized();
        const QSize normalSize = maximized ? normalGeometry().size() : size();
        const classic::gui::GuiWindowGeometryChange transition{kGuiWindows[tabIndex],
                                                               {maximized, normalSize.width(), normalSize.height()}};

        const auto result =
            classic::gui::GuiUserSettings::commitFrontendTransition(m_dataRoot, m_guiSettings, transition);
        if (result.status != QStringLiteral("committed")) {
            setStatusMessage(QStringLiteral("Window geometry was not saved (%1).").arg(result.status));
        }
    } catch (const std::exception& error) {
        setStatusMessage(QStringLiteral("Window geometry save failed: ") + QString::fromUtf8(error.what()));
    } catch (...) {
        setStatusMessage(QStringLiteral("Window geometry save failed: unknown error"));
    }
}

void MainWindow::restoreTabGeometry(int tabIndex)
{
    if (tabIndex < 0 || tabIndex >= TAB_COUNT) {
        return;
    }

    int minW = kTabMinSizes[tabIndex].minWidth;
    int minH = kTabMinSizes[tabIndex].minHeight;
    setMinimumSize(minW, minH);

    if (m_dataDir.isEmpty()) {
        resize(minW, minH);
        return;
    }

    const auto geometry = m_guiSettings.frontend.windowGeometry.value(kGuiWindows[tabIndex]);
    const int savedW = geometry.width;
    const int savedH = geometry.height;
    const bool wasMax = geometry.maximized;

    int w = (savedW > 0) ? qMax(savedW, minW) : minW;
    int h = (savedH > 0) ? qMax(savedH, minH) : minH;

    if (wasMax) {
        resize(w, h);
        showMaximized();
    } else {
        if (isMaximized()) {
            showNormal();
        }
        resize(w, h);
    }
}

void MainWindow::onTabChanged(int index)
{
    if (!m_geometryInitialized) {
        return;
    }

    // Save geometry for the outgoing tab
    if (m_lastTabIndex >= 0) {
        saveTabGeometry(m_lastTabIndex);
    }

    // Restore geometry for the incoming tab
    restoreTabGeometry(index);

    // Entering the Results tab should always force a report reload so
    // newly generated files are visible even if no watcher event fired.
    if (index == (TAB_COUNT - 1) && m_resultsController) {
        m_resultsController->refreshReports();
    }

    m_lastTabIndex = index;
}

QString MainWindow::readCrashLogsDir() const
{
    return QDir::cleanPath(QDir(QCoreApplication::applicationDirPath()).filePath(QStringLiteral("Crash Logs")));
}

bool MainWindow::loadValidatedGameAndDocsPaths(QString* gamePathOut, QString* docsPathOut) const
{
    if (gamePathOut) {
        gamePathOut->clear();
    }
    if (docsPathOut) {
        docsPathOut->clear();
    }

    if (m_dataRoot.isEmpty()) {
        return false;
    }

    const QString rawGamePath = m_guiSettings.gameSetup.gameRoot.value_or(QString{}).trimmed();
    const QString rawDocsPath = m_guiSettings.gameSetup.documentsRoot.value_or(QString{}).trimmed();
    const QString gamePath = rawGamePath.isEmpty() ? QString() : QDir::cleanPath(rawGamePath);
    const QString docsPath = rawDocsPath.isEmpty() ? QString() : QDir::cleanPath(rawDocsPath);

    const bool gameValid = !gamePath.isEmpty() && QDir(gamePath).exists();
    const bool docsValid = !docsPath.isEmpty() && QDir(docsPath).exists();

    if (gamePathOut) {
        *gamePathOut = gamePath;
    }
    if (docsPathOut) {
        *docsPathOut = docsPath;
    }
    return gameValid && docsValid;
}

// ── Slot implementations ───────────────────────────────────────────

void MainWindow::onBrowseStaging()
{
    QString dir = QFileDialog::getExistingDirectory(this, QStringLiteral("Select Staging Mods Folder"),
                                                    m_editStagingFolder->text());

    if (!dir.isEmpty()) {
        m_editStagingFolder->setText(dir);
        saveRememberedPath(RememberedPath::Staging);
    }
}

void MainWindow::onBrowseCustom()
{
    QString dir = QFileDialog::getExistingDirectory(this, QStringLiteral("Select Custom Scan Folder"),
                                                    m_editCustomFolder->text());

    if (!dir.isEmpty()) {
        if (validateCustomScanFolder(dir)) {
            m_editCustomFolder->setText(dir);
            saveRememberedPath(RememberedPath::CustomScan);
            initResultsReportDir();
        }
    }
}

bool MainWindow::validateCustomScanFolder(const QString& path)
{
    if (path.isEmpty()) {
        return true; // Empty is valid (clears the setting)
    }

    // Check if path exists and is a directory
    if (!QDir(path).exists()) {
        QMessageBox::warning(this, QStringLiteral("Invalid Path"),
                             QStringLiteral("The path '%1' does not exist or is not a directory.\n\n"
                                            "The custom scan path has been cleared.")
                                 .arg(path));
        m_editCustomFolder->clear();
        return false;
    }

    // Check if path is a restricted Windows system directory
    try {
        if (classic::path::check_restricted_path(std::string(path.toUtf8().constData()))) {
            QMessageBox::warning(this, QStringLiteral("Invalid Custom Scan Path"),
                                 QStringLiteral("The entered directory cannot be used as a custom scan path.\n\n"
                                                "System directories (Program Files, Windows, etc.) are restricted "
                                                "because they can interfere with the operation of the program.\n\n"
                                                "The custom scan path has been cleared."));
            m_editCustomFolder->clear();
            return false;
        }
    } catch (...) {
        // If the bridge call fails, allow the path (non-critical check)
    }

    // Check if path is inside the Crash Logs directory
    QString crashDir = readCrashLogsDir();
    if (!crashDir.isEmpty()) {
        QString normalizedPath = QDir::cleanPath(path).toLower();
        QString normalizedCrashDir = QDir::cleanPath(crashDir).toLower();
        if (normalizedPath == normalizedCrashDir ||
            normalizedPath.startsWith(normalizedCrashDir + QStringLiteral("/"))) {
            QMessageBox::warning(this, QStringLiteral("Invalid Custom Scan Path"),
                                 QStringLiteral("The entered directory cannot be used as a custom scan path.\n\n"
                                                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC "
                                                "and cannot be set as custom scan directories.\n\n"
                                                "The custom scan path has been cleared."));
            m_editCustomFolder->clear();
            return false;
        }
    }

    return true;
}

void MainWindow::onCustomFolderEdited()
{
    QString text = m_editCustomFolder->text().trimmed();

    if (text.isEmpty()) {
        // The typed update persists the empty text as an explicit canonical clear.
        saveRememberedPath(RememberedPath::CustomScan);
        initResultsReportDir();
        return;
    }

    if (validateCustomScanFolder(text)) {
        // Normalize and save
        QString normalized = QDir::cleanPath(text);
        m_editCustomFolder->setText(normalized);
        saveRememberedPath(RememberedPath::CustomScan);
        initResultsReportDir();
    } else {
        // Validation cleared the text box, so persist the canonical clear.
        saveRememberedPath(RememberedPath::CustomScan);
        initResultsReportDir();
    }
}

void MainWindow::onScanCrashLogs()
{
    if (m_dataRoot.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Error"),
                             QStringLiteral("Cannot find CLASSIC Data directory. "
                                            "Ensure the application is in the correct location."));
        return;
    }
    if (m_dataDir.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Error"),
                             QStringLiteral("Cannot find CLASSIC Data directory. "
                                            "Ensure the application is in the correct location."));
        return;
    }

    auto launchSettings = m_guiSettings.scanLaunchSettings(m_guiSettings.gameSetup.managedGame);
    QString setupGameRoot;
    QString setupDocsPath;
    QString setupGameExePath;
    QString setupXseLogPath;
    if (launchSettings.fcxMode) {
        if (!loadValidatedGameAndDocsPaths(&setupGameRoot, &setupDocsPath)) {
            QMessageBox::warning(this, QStringLiteral("FCX Mode Requires Paths"),
                                 QStringLiteral("FCX mode requires valid game and INI folder paths.\n\n"
                                                "Open Settings and configure both paths before scanning crash logs."));
            return;
        }

        setupGameExePath = QDir::cleanPath(launchSettings.setupGameExecutable.trimmed());
        const auto executableName =
            classic::path::resolve_fallout4_exe_name(launchSettings.gameVersion.toStdString());
        setupGameExePath = classic::gui::normalizeGameExecutablePath(
            setupGameExePath, setupGameRoot, classic::toQString(executableName));
        setupXseLogPath =
            resolveExistingXseLogPath(m_dataDir, launchSettings.game, launchSettings.gameVersion, setupDocsPath);
        launchSettings.setupGameRoot = setupGameRoot;
        launchSettings.setupDocumentsRoot = setupDocsPath;
        launchSettings.setupGameExecutable = setupGameExePath;
    }

    m_btnScanCrashLogs->setEnabled(false);
    m_btnScanCrashLogs->setText(QStringLiteral("SCANNING..."));
    m_crashScanTotalLogs = 0;
    m_crashScanLogsCompleted = 0;
    m_crashScanInProgress = true;
    m_lastScanReportDirs.clear();
    m_hasLastInstalledYamlData = false;
    m_lastInstalledYamlData = {};
    m_crashScanTimer.start();
    setStatusMessage(QStringLiteral("Scanning crash logs... 0 logs scanned | elapsed %1s")
                         .arg(format_elapsed_seconds(m_crashScanTimer)));

    m_scanController->startScan(m_dataRoot, launchSettings, setupXseLogPath, m_targetedInputPaths);
}

void MainWindow::onScanGameFiles()
{
    if (m_dataRoot.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Error"),
                             QStringLiteral("Cannot find CLASSIC Data directory. "
                                            "Ensure the application is in the correct location."));
        return;
    }

    QString gameRoot;
    QString docsPath;
    if (!loadValidatedGameAndDocsPaths(&gameRoot, &docsPath)) {
        QMessageBox::warning(
            this, QStringLiteral("Missing Paths"),
            QStringLiteral("Game folder and INI folder paths are required before running Scan Game Files.\n\n"
                           "Open Settings and configure both paths."));
        return;
    }

    const auto setup = classic::gui::GameSetupUserSettings::open(m_dataRoot);
    const QString xseLogPath =
        resolveExistingXseLogPath(m_dataDir, setup.managedGame, setup.gameVersionSelection, docsPath);

    m_btnScanGameFiles->setEnabled(false);
    m_btnScanGameFiles->setText(QStringLiteral("SCANNING..."));
    setStatusMessage(QStringLiteral("Scanning game files..."));

    // Update backup controller with the game root (may have changed)
    m_backupController->setGameRoot(gameRoot);

    m_gameFilesController->startScan(m_dataRoot, xseLogPath);
}

void MainWindow::onExit()
{
    if (m_geometryInitialized && m_lastTabIndex >= 0) {
        saveTabGeometry(m_lastTabIndex);
        // The explicit exit transition already persisted geometry; avoid a duplicate destructor commit.
        m_geometryInitialized = false;
    }
    QApplication::quit();
}

void MainWindow::onCrashScanProgress(float percent, const QString& status, int completed, int total)
{
    if (m_crashScanInProgress) {
        if (total > 0) {
            m_crashScanTotalLogs = total;
            m_crashScanLogsCompleted = qMax(m_crashScanLogsCompleted, qMin(completed, total));
        } else {
            m_crashScanLogsCompleted = qMax(m_crashScanLogsCompleted, completed);
        }
    }

    onScanProgress(percent, status);
}

void MainWindow::onScanProgress(float percent, const QString& status)
{
    if (m_crashScanInProgress) {
        const int completedLogs = (m_crashScanTotalLogs > 0) ? qMin(m_crashScanLogsCompleted, m_crashScanTotalLogs)
                                                             : m_crashScanLogsCompleted;
        const QString scanStats =
            (m_crashScanTotalLogs > 0)
                ? QStringLiteral("%1/%2 logs scanned").arg(completedLogs).arg(m_crashScanTotalLogs)
                : QStringLiteral("%1 logs scanned").arg(completedLogs);

        if (percent < 0.0f) {
            // Indeterminate: range(0,0) triggers bouncing animation
            m_progressBar->setRange(0, 0);
            setStatusMessage(QStringLiteral("%1 | elapsed %2s | %3")
                                 .arg(scanStats)
                                 .arg(format_elapsed_seconds(m_crashScanTimer))
                                 .arg(status));
        } else {
            // Determinate: fill bar to percentage
            m_progressBar->setRange(0, 100);
            m_progressBar->setValue(static_cast<int>(percent));
            setStatusMessage(QStringLiteral("Scanning: %1% | %2 | elapsed %3s | %4")
                                 .arg(static_cast<int>(percent))
                                 .arg(scanStats)
                                 .arg(format_elapsed_seconds(m_crashScanTimer))
                                 .arg(status));
        }
        return;
    }

    if (percent < 0.0f) {
        // Indeterminate: range(0,0) triggers bouncing animation
        m_progressBar->setRange(0, 0);
        setStatusMessage(status);
    } else {
        // Determinate: fill bar to percentage
        m_progressBar->setRange(0, 100);
        m_progressBar->setValue(static_cast<int>(percent));
        setStatusMessage(QStringLiteral("Scanning: %1% - %2").arg(static_cast<int>(percent)).arg(status));
    }
}

void MainWindow::onCrashScanDiscovered(int totalLogs)
{
    m_crashScanTotalLogs = totalLogs;
}

void MainWindow::onCrashLogScanned(int /*index*/, bool /*success*/, const QString& /*logPath*/)
{
    if (m_crashScanTotalLogs > 0) {
        m_crashScanLogsCompleted = qMin(m_crashScanLogsCompleted + 1, m_crashScanTotalLogs);
    } else {
        ++m_crashScanLogsCompleted;
    }
}

void MainWindow::onScanCompleted(int total, int success, int errors)
{
    m_btnScanCrashLogs->setEnabled(true);
    m_btnScanCrashLogs->setText(QStringLiteral("SCAN CRASH LOGS"));
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    m_crashScanInProgress = false;
    m_crashScanTotalLogs = total;
    m_crashScanLogsCompleted = total;
    initResultsReportDir();
    setStatusMessage(QStringLiteral("Scan completed: %1 logs scanned in %2s (%3 succeeded, %4 failed)")
                         .arg(total)
                         .arg(format_elapsed_seconds(m_crashScanTimer))
                         .arg(success)
                         .arg(errors) +
                     installedYamlDataStatusSuffix());

    // Auto-switch to Results tab is handled by ResultsController::onScanCompleted()
}

void MainWindow::onScanCancelled(const QString& message)
{
    m_btnScanCrashLogs->setEnabled(true);
    m_btnScanCrashLogs->setText(QStringLiteral("SCAN CRASH LOGS"));
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    m_crashScanInProgress = false;
    initResultsReportDir();
    setStatusMessage(QStringLiteral("%1 (%2s)").arg(message).arg(format_elapsed_seconds(m_crashScanTimer)) +
                     installedYamlDataStatusSuffix());
}

void MainWindow::onScanNoLogsFound(const QString& message)
{
    m_btnScanCrashLogs->setEnabled(true);
    m_btnScanCrashLogs->setText(QStringLiteral("SCAN CRASH LOGS"));
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    m_crashScanInProgress = false;
    initResultsReportDir();
    setStatusMessage(message + installedYamlDataStatusSuffix());
}

void MainWindow::onScanError(const QString& message)
{
    m_btnScanCrashLogs->setEnabled(true);
    m_btnScanCrashLogs->setText(QStringLiteral("SCAN CRASH LOGS"));
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    m_crashScanInProgress = false;
    initResultsReportDir();
    setStatusMessage(
        QStringLiteral("Scan failed after %1s: %2").arg(format_elapsed_seconds(m_crashScanTimer)).arg(message) +
        installedYamlDataStatusSuffix());

    QMessageBox::critical(this, QStringLiteral("Scan Error"), message);
}

void MainWindow::onScanWarning(const QString& message)
{
    QMessageBox::warning(this, QStringLiteral("Scan Warning"), message);
}

void MainWindow::onScanReportDirectoriesResolved(const QStringList& reportDirs)
{
    m_lastScanReportDirs = reportDirs;
    initResultsReportDir();
}

void MainWindow::onScanInstalledYamlDataResolved(
    const classic::gui::ScanRunInstalledYamlDataPresentation& installedYamlData)
{
    m_lastInstalledYamlData = installedYamlData;
    m_hasLastInstalledYamlData = true;

    qInfo().noquote() << QStringLiteral(
                             "Installed YAML Data: Main %1 schema %2 (%3 bytes, sha256 %4); "
                             "Game %5 schema %6 (%7 bytes, sha256 %8); Local Ignore %9 (%10 bytes, sha256 %11)")
                             .arg(installedYamlDataProvenanceLabel(installedYamlData.main.provenance))
                             .arg(installedYamlData.main.schemaVersion)
                             .arg(installedYamlData.main.byteLength)
                             .arg(installedYamlData.main.sha256)
                             .arg(installedYamlDataProvenanceLabel(installedYamlData.gameFile.provenance))
                             .arg(installedYamlData.gameFile.schemaVersion)
                             .arg(installedYamlData.gameFile.byteLength)
                             .arg(installedYamlData.gameFile.sha256)
                             .arg(localIgnoreStateLabel(installedYamlData.localIgnoreState))
                             .arg(installedYamlData.localIgnoreIdentity.byteLength)
                             .arg(installedYamlData.localIgnoreIdentity.sha256);
    if (installedYamlData.hasLocalIgnoreReset) {
        qInfo().noquote() << QStringLiteral("Local Ignore reset backup: %1 (%2 bytes, sha256 %3)")
                                 .arg(installedYamlData.localIgnoreReset.backupPath)
                                 .arg(installedYamlData.localIgnoreReset.backupIdentity.byteLength)
                                 .arg(installedYamlData.localIgnoreReset.backupIdentity.sha256);
    }
    for (const auto& diagnostic : installedYamlData.diagnostics) {
        QStringList context;
        if (diagnostic.hasRole) {
            context.append(diagnostic.role == classic::scanner::ScanRunInstalledYamlDataRole::Main
                               ? QStringLiteral("Main")
                               : QStringLiteral("Game"));
        }
        if (diagnostic.hasCandidate) {
            context.append(installedYamlDataProvenanceLabel(diagnostic.candidate));
        }
        if (diagnostic.hasPath) {
            context.append(diagnostic.path);
        }
        const QString suffix = context.isEmpty() ? QString{} : QStringLiteral(" [%1]").arg(context.join(", "));
        qInfo().noquote() << QStringLiteral("Installed YAML Data diagnostic (%1): %2%3")
                                 .arg(installedYamlDataDiagnosticKindLabel(diagnostic.kind), diagnostic.message,
                                      suffix);
    }
}

QString MainWindow::installedYamlDataStatusSuffix() const
{
    if (!m_hasLastInstalledYamlData) {
        return {};
    }
    return QStringLiteral(" | YAML Data: Main %1 schema %2, Game %3 schema %4, Local Ignore %5")
        .arg(installedYamlDataProvenanceLabel(m_lastInstalledYamlData.main.provenance),
             m_lastInstalledYamlData.main.schemaVersion,
             installedYamlDataProvenanceLabel(m_lastInstalledYamlData.gameFile.provenance),
             m_lastInstalledYamlData.gameFile.schemaVersion,
             localIgnoreStateLabel(m_lastInstalledYamlData.localIgnoreState));
}

void MainWindow::onShowSettings()
{
    SettingsDialog dlg(m_dataRoot, m_signalHub, this);
    if (dlg.exec() == QDialog::Accepted) {
        loadSettings();
        emit m_signalHub->settingsChanged();
    }
}

// ── Game Files Scan slots ──────────────────────────────────────────

void MainWindow::onGameFilesScanFinished(const QString& output, bool hasErrors, uint32_t totalChecks)
{
    m_btnScanGameFiles->setEnabled(true);
    m_btnScanGameFiles->setText(QStringLiteral("SCAN GAME FILES"));
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);

    QString statusMsg = QStringLiteral("Game files scan completed: %1 checks").arg(totalChecks);
    if (hasErrors) {
        statusMsg += QStringLiteral(" (errors found)");
    }
    setStatusMessage(statusMsg);

    if (output.isEmpty()) {
        return;
    }

    // Write results as a report file in the crash logs directory
    // so the Results tab picks it up via file watching.
    QString crashDir = readCrashLogsDir();
    if (crashDir.isEmpty()) {
        // Fall back to message box if crash logs dir is not configured
        QMessageBox::information(this, QStringLiteral("Game Files Scan Results"), output);
        return;
    }

    // Ensure directory exists
    QDir().mkpath(crashDir);

    // Generate timestamped report filename
    QString timestamp = QDateTime::currentDateTime().toString(QStringLiteral("yyyy-MM-dd_HH-mm-ss"));
    QString filename = QStringLiteral("GameFiles-%1-AUTOSCAN.md").arg(timestamp);
    QString filePath = crashDir + QStringLiteral("/") + filename;

    // Build markdown report
    QString statusLabel = hasErrors ? QStringLiteral("Issues Found") : QStringLiteral("All Clear");
    QString report = QStringLiteral("# Game Files Scan Report\n\n"
                                    "**Date**: %1\n"
                                    "**Checks**: %2\n"
                                    "**Status**: %3\n\n"
                                    "---\n\n"
                                    "%4\n")
                         .arg(QDateTime::currentDateTime().toString(Qt::ISODate))
                         .arg(totalChecks)
                         .arg(statusLabel)
                         .arg(output);

    // Write the report file via CXX bridge
    try {
        classic::files::write_file_string(std::string(filePath.toUtf8().constData()),
                                          std::string(report.toUtf8().constData()));
    } catch (...) {
        // Fall back to message box if file write fails
        QMessageBox::information(this, QStringLiteral("Game Files Scan Results"), output);
    }
}

void MainWindow::onGameFilesScanError(const QString& message)
{
    m_btnScanGameFiles->setEnabled(true);
    m_btnScanGameFiles->setText(QStringLiteral("SCAN GAME FILES"));
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    setStatusMessage(QStringLiteral("Game files scan failed: ") + message);

    QMessageBox::critical(this, QStringLiteral("Game Files Scan Error"), message);
}

// ── Backup operation slots ─────────────────────────────────────────

void MainWindow::onBackupCompleted(const QString& message)
{
    setStatusMessage(message);
}

void MainWindow::onBackupError(const QString& error)
{
    setStatusMessage(QStringLiteral("Backup error: ") + error);
    QMessageBox::warning(this, QStringLiteral("Backup Error"), error);
}

void MainWindow::onOpenBackupsFolder()
{
    // The backup folder is "CLASSIC Backups" under the game root.
    // If the game root is not set, try the data root as fallback.
    QString backupDir;
    if (!m_backupController->gameRoot().isEmpty()) {
        backupDir = m_backupController->gameRoot() + QStringLiteral("/CLASSIC Backups");
    } else if (!m_dataRoot.isEmpty()) {
        backupDir = m_dataRoot + QStringLiteral("/CLASSIC Backups");
    }

    if (backupDir.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Error"), QStringLiteral("Cannot determine backup folder location."));
        return;
    }

    // Create the directory if it doesn't exist yet
    QDir().mkpath(backupDir);
    QDesktopServices::openUrl(QUrl::fromLocalFile(backupDir));
}

// ── Update check slot ─────────────────────────────────────────────

void MainWindow::onCheckUpdates()
{
    checkForUpdates(true);
}

void MainWindow::checkForUpdates(bool explicitCheck)
{
    if (m_threadManager->isRunning(QStringLiteral("updateCheck"))) {
        if (explicitCheck) {
            QMessageBox::information(this, QStringLiteral("Update Check"),
                                     QStringLiteral("An update check is already in progress."));
        }
        return;
    }

    if (explicitCheck) {
        m_btnCheckUpdates->setEnabled(false);
        m_btnCheckUpdates->setText(QStringLiteral("CHECKING..."));
        setStatusMessage(QStringLiteral("Checking for updates..."));
    }

    // Create worker + thread for the background update check
    auto* thread = new QThread();
    auto* worker = new UpdateWorker();

    // Wire completion signal (queued connection across threads). The worker
    // emits a QVariantMap shaped like classic::update::NotificationStatusDto
    // — classification + latestVersion + published_at + optional display
    // payload + parseError/errorMessage. Keys are defined as constants on
    // UpdateWorker so we don't sprinkle string literals through the UI.
    connect(worker, &UpdateWorker::updateCheckCompleted, this, [this, explicitCheck](const QVariantMap& result) {
        if (explicitCheck) {
            m_btnCheckUpdates->setEnabled(true);
            m_btnCheckUpdates->setText(QStringLiteral("CHECK UPDATES"));
        }

        const QString classification = result.value(UpdateWorker::kKeyClassification).toString();
        const QString latestVersion = result.value(UpdateWorker::kKeyLatestVersion).toString();
        const QString displayTitle = result.value(UpdateWorker::kKeyDisplayTitle).toString();
        const QString displayBody = result.value(UpdateWorker::kKeyDisplayBody).toString();
        const QString displayCtaUrl = result.value(UpdateWorker::kKeyDisplayCtaUrl).toString();
        const QString minSupported = result.value(UpdateWorker::kKeyMinSupportedVersion).toString();
        const QString parseError = result.value(UpdateWorker::kKeyParseError).toString();
        const QString errorMessage = result.value(UpdateWorker::kKeyErrorMessage).toString();

        if (classification == QLatin1String(UpdateWorker::kClassificationError)) {
            const QString detail = errorMessage.isEmpty() ? QStringLiteral("unknown error") : errorMessage;
            setStatusMessage(QStringLiteral("Update check failed"));
            logUpdateCheckFailure(errorMessage);
            if (explicitCheck) {
                QMessageBox::warning(this, QStringLiteral("Update Check Failed"),
                                     QStringLiteral("Update check failed: ") + detail);
            }
        } else if (classification == QLatin1String(UpdateWorker::kClassificationUpdateAvailable)) {
            setStatusMessage(QStringLiteral("Update available: v") + latestVersion);
            QString body = QStringLiteral("A new version is available: v%1").arg(latestVersion);
            if (!displayTitle.isEmpty()) {
                body += QStringLiteral("\n\n") + displayTitle;
            }
            if (!displayBody.isEmpty()) {
                body += QStringLiteral("\n\n") + displayBody;
            }
            body += QStringLiteral("\n\nOpen the GitHub releases page now?");
            auto response = QMessageBox::question(this, QStringLiteral("Update Available"), body,
                                                  QMessageBox::Yes | QMessageBox::No, QMessageBox::Yes);
            if (response == QMessageBox::Yes) {
                // `displayCtaUrl` originates from the remote
                // app-notification manifest (see
                // `docs/api/app-update-notification-delivery.md`).
                // Even though the manifest is published from our own
                // Pages/Releases infrastructure, restrict the scheme
                // to HTTPS as defense-in-depth: a compromised or
                // misconfigured publish could otherwise hand the
                // system default handler a `file://`, `javascript:`,
                // `data:`, or — the Codex adversarial-review motivator
                // — a cleartext `http://` downgrade at exactly the
                // moment the user is being asked to fetch an update.
                // The publish-side and Rust runtime validators reject
                // non-HTTPS first; this branch is the third line of
                // defense if either is bypassed.
                const QString fallbackUrl =
                    QStringLiteral("https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest");
                QUrl candidate(displayCtaUrl);
                const QString scheme = candidate.scheme().toLower();
                const bool ctaAcceptable =
                    !displayCtaUrl.isEmpty() && candidate.isValid() && scheme == QLatin1String("https");
                QDesktopServices::openUrl(ctaAcceptable ? candidate : QUrl(fallbackUrl));
            }
        } else if (classification == QLatin1String(UpdateWorker::kClassificationDeprecated)) {
            setStatusMessage(QStringLiteral("Client deprecated — upgrade required"));
            QMessageBox::warning(
                this, QStringLiteral("Client Deprecated"),
                QStringLiteral("This CLASSIC build is below the minimum supported version (v%1).\n"
                               "Upgrade to v%2 to keep receiving support.")
                    .arg(minSupported.isEmpty() ? QStringLiteral("unknown") : minSupported, latestVersion));
        } else if (classification == QLatin1String(UpdateWorker::kClassificationUnknown)) {
            if (explicitCheck) {
                setStatusMessage(QStringLiteral("Update check inconclusive"));
                QMessageBox::information(this, QStringLiteral("Update Check"),
                                         parseError.isEmpty()
                                             ? QStringLiteral("Update check returned an unknown status.")
                                             : QStringLiteral("Update check inconclusive: ") + parseError);
            }
        } else if (classification == QLatin1String(UpdateWorker::kClassificationNotPublished)) {
            if (explicitCheck) {
                setStatusMessage(QStringLiteral("No update information available"));
                QMessageBox::information(this, QStringLiteral("Update Check"),
                                         QStringLiteral("No update information is currently available."));
            }
        } else if (explicitCheck) {
            // UpToDate (or any unexpected classification treated as
            // "nothing to show"). Only surface a dialog on user-initiated
            // checks to avoid a popup on startup.
            setStatusMessage(QStringLiteral("You are up to date"));
            QMessageBox::information(this, QStringLiteral("Update Check"),
                                     QStringLiteral("You are running the latest version."));
        }

        // Clean up the worker thread
        m_threadManager->stopWorker(QStringLiteral("updateCheck"));
    });

    // Start the background check via ThreadManager
    QString currentVersion = QApplication::applicationVersion();
    connect(thread, &QThread::started, worker, [worker, currentVersion]() { worker->checkForUpdates(currentVersion); });

    m_threadManager->startWorker(QStringLiteral("updateCheck"), thread, worker);
}

// ── Papyrus monitoring slot ───────────────────────────────────────

void MainWindow::onTogglePapyrusMonitor()
{
    bool isChecked = m_btnPapyrusMonitor->isChecked();

    if (isChecked) {
        // Starting monitoring: read Papyrus log path from settings
        if (m_dataDir.isEmpty()) {
            QMessageBox::warning(this, QStringLiteral("Error"), QStringLiteral("CLASSIC Data directory not found."));
            m_btnPapyrusMonitor->setChecked(false);
            return;
        }

        QString papyrusLogPath;
        try {
            const auto setup = classic::gui::GameSetupUserSettings::open(m_dataRoot);
            papyrusLogPath = setup.papyrusLog.value_or(QString{});
        } catch (...) {
            // The warning below explains the unavailable typed path to the user.
        }

        if (papyrusLogPath.isEmpty()) {
            QMessageBox::warning(this, QStringLiteral("Error"),
                                 QStringLiteral("Papyrus log path is not configured.\n"
                                                "The path is usually:\n"
                                                "<Documents>/My Games/Fallout4/Logs/Script/Papyrus.0.log\n\n"
                                                "Please set it in Settings."));
            m_btnPapyrusMonitor->setChecked(false);
            return;
        }

        // Update button appearance
        m_btnPapyrusMonitor->setText(QStringLiteral("STOP PAPYRUS MONITORING"));
        setStatusMessage(QStringLiteral("Papyrus monitoring active"));

        // Create worker + thread
        auto* thread = new QThread();
        auto* worker = new PapyrusWorker();

        // Create the monitoring dialog
        m_papyrusDialog = new PapyrusDialog(this);

        // Wire stats updates from worker to dialog
        connect(worker, &PapyrusWorker::statsUpdated, m_papyrusDialog, &PapyrusDialog::updateStats);

        // Wire error signal
        connect(worker, &PapyrusWorker::monitoringError, this, [this](const QString& msg) {
            setStatusMessage(QStringLiteral("Papyrus error: ") + msg);
            // Auto-stop on error
            m_btnPapyrusMonitor->setChecked(false);
            onTogglePapyrusMonitor();
        });

        // Wire dialog close/stop to cleanup
        connect(m_papyrusDialog, &PapyrusDialog::stopRequested, this, [this]() {
            m_btnPapyrusMonitor->setChecked(false);
            onTogglePapyrusMonitor();
        });

        // Start worker on thread
        connect(thread, &QThread::started, worker, [worker, papyrusLogPath]() { worker->start(papyrusLogPath); });

        m_threadManager->startWorker(QStringLiteral("papyrus"), thread, worker);

        // Show the dialog (non-modal)
        m_papyrusDialog->show();

    } else {
        // Stopping monitoring
        m_threadManager->stopWorker(QStringLiteral("papyrus"));

        m_btnPapyrusMonitor->setText(QStringLiteral("START PAPYRUS MONITORING"));
        setStatusMessage(QStringLiteral("Papyrus monitoring stopped"));

        if (m_papyrusDialog) {
            m_papyrusDialog->close();
            m_papyrusDialog->deleteLater();
            m_papyrusDialog = nullptr;
        }
    }
}

// ── Drag-and-drop for targeted scan inputs ─────────────────────────

void MainWindow::installTargetedDropForwarding()
{
    const auto enableDropTarget = [this](QWidget* widget) {
        if (widget) {
            widget->setAcceptDrops(true);
            widget->installEventFilter(this);
        }
    };

    enableDropTarget(m_targetedInputContainer);
    enableDropTarget(m_targetedInputLabel);
    enableDropTarget(m_targetedInputList);
    // QListWidget routes drops over its item area through the internal viewport.
    enableDropTarget(m_targetedInputList ? m_targetedInputList->viewport() : nullptr);
    enableDropTarget(m_btnClearTargeted);
}

bool MainWindow::eventFilter(QObject* watched, QEvent* event)
{
    const bool isTargetedDropSurface =
        watched == m_targetedInputContainer || watched == m_targetedInputLabel || watched == m_targetedInputList ||
        (m_targetedInputList && watched == m_targetedInputList->viewport()) || watched == m_btnClearTargeted;

    if (isTargetedDropSurface) {
        switch (event->type()) {
        case QEvent::DragEnter:
            if (handleTargetedDragEnter(static_cast<QDragEnterEvent*>(event))) {
                return true;
            }
            break;
        case QEvent::DragMove:
            if (handleTargetedDragMove(static_cast<QDragMoveEvent*>(event))) {
                return true;
            }
            break;
        case QEvent::Drop:
            if (handleTargetedDrop(static_cast<QDropEvent*>(event))) {
                return true;
            }
            break;
        default:
            break;
        }
    }

    return QMainWindow::eventFilter(watched, event);
}

bool MainWindow::handleTargetedDragEnter(QDragEnterEvent* event)
{
    if (!event->mimeData()->hasUrls()) {
        return false;
    }

    if (m_tabWidget && m_tabWidget->currentIndex() == 0) {
        event->acceptProposedAction();
    } else {
        event->ignore();
    }
    return true;
}

bool MainWindow::handleTargetedDragMove(QDragMoveEvent* event)
{
    if (!event->mimeData()->hasUrls()) {
        return false;
    }

    if (m_tabWidget && m_tabWidget->currentIndex() == 0) {
        event->acceptProposedAction();
    } else {
        event->ignore();
    }
    return true;
}

bool MainWindow::handleTargetedDrop(QDropEvent* event)
{
    const bool wrongTab = !m_tabWidget || m_tabWidget->currentIndex() != 0;
    const bool unsupportedPayload = !event->mimeData()->hasUrls();

    if (unsupportedPayload) {
        acknowledgeTargetedDrop(0, 0, 0, true, wrongTab);
        event->ignore();
        return true;
    }

    if (wrongTab) {
        acknowledgeTargetedDrop(0, 0, 0, false, true);
        event->ignore();
        return true;
    }

    int addedCount = 0;
    int duplicateCount = 0;
    int nonLocalCount = 0;

    for (const QUrl& url : event->mimeData()->urls()) {
        if (!url.isLocalFile()) {
            ++nonLocalCount;
            continue;
        }

        const QString path = QDir::toNativeSeparators(url.toLocalFile());
        if (m_targetedInputPaths.contains(path)) {
            ++duplicateCount;
            continue;
        }

        m_targetedInputPaths.append(path);
        ++addedCount;
    }

    if (addedCount > 0) {
        updateTargetedInputUi();
    }

    acknowledgeTargetedDrop(addedCount, duplicateCount, nonLocalCount, false, false);
    event->acceptProposedAction();
    return true;
}

void MainWindow::acknowledgeTargetedDrop(int addedCount, int duplicateCount, int nonLocalCount, bool unsupportedPayload,
                                         bool wrongTab)
{
    if (wrongTab) {
        setStatusMessage(QStringLiteral("Switch to the Main Options tab to add targeted scan inputs."));
        return;
    }

    if (unsupportedPayload) {
        setStatusMessage(QStringLiteral("Drop ignored: only local file paths are supported for targeted scans."));
        return;
    }

    QStringList parts;
    if (addedCount > 0) {
        parts.append(QStringLiteral("Added %1 targeted input%2.").arg(addedCount).arg(addedCount == 1 ? "" : "s"));
    }
    if (duplicateCount > 0) {
        parts.append(QStringLiteral("Skipped %1 duplicate path%2 already in the list.")
                         .arg(duplicateCount)
                         .arg(duplicateCount == 1 ? "" : "s"));
    }
    if (nonLocalCount > 0) {
        parts.append(QStringLiteral("Skipped %1 non-local URL%2; only local files are supported.")
                         .arg(nonLocalCount)
                         .arg(nonLocalCount == 1 ? "" : "s"));
    }

    if (parts.isEmpty()) {
        setStatusMessage(QStringLiteral("Drop ignored: no local file paths were found."));
        return;
    }

    setStatusMessage(parts.join(QStringLiteral(" ")));
}

void MainWindow::dragEnterEvent(QDragEnterEvent* event)
{
    handleTargetedDragEnter(event);
}

void MainWindow::dragMoveEvent(QDragMoveEvent* event)
{
    handleTargetedDragMove(event);
}

void MainWindow::dropEvent(QDropEvent* event)
{
    handleTargetedDrop(event);
}

void MainWindow::onClearTargetedInputs()
{
    m_targetedInputPaths.clear();
    updateTargetedInputUi();
}

void MainWindow::updateTargetedInputUi()
{
    const bool hasInputs = !m_targetedInputPaths.isEmpty();
    m_targetedInputList->setVisible(hasInputs);
    m_btnClearTargeted->setVisible(hasInputs);

    if (hasInputs) {
        m_targetedInputLabel->setText(QStringLiteral("Targeted Scan: %1 path%2 selected")
                                          .arg(m_targetedInputPaths.size())
                                          .arg(m_targetedInputPaths.size() == 1 ? "" : "s"));
        m_targetedInputLabel->setStyleSheet(QStringLiteral("font-weight: bold;"));

        m_targetedInputList->clear();
        for (const auto& p : m_targetedInputPaths) {
            m_targetedInputList->addItem(p);
        }
    } else {
        m_targetedInputLabel->setText(QStringLiteral("Targeted Scan: drop files or folders here"));
        m_targetedInputLabel->setStyleSheet(QStringLiteral("color: #888; font-style: italic;"));
    }

    m_targetedInputList->updateGeometry();
    m_btnClearTargeted->updateGeometry();
    m_targetedInputContainer->updateGeometry();
    if (auto* central = centralWidget()) {
        central->updateGeometry();
        if (central->layout()) {
            central->layout()->activate();
        }
    }

    if (hasInputs && !isMaximized() && !isFullScreen()) {
        const QSize requestedSize = sizeHint().expandedTo(minimumSize());
        const QSize currentSize = size();
        if (requestedSize.width() > currentSize.width() || requestedSize.height() > currentSize.height()) {
            resize(qMax(currentSize.width(), requestedSize.width()),
                   qMax(currentSize.height(), requestedSize.height()));
        }
    }
}
