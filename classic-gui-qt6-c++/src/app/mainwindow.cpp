#include "mainwindow.h"

#include <QApplication>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QFileDialog>
#include <QFile>
#include <QDir>
#include <QMessageBox>
#include <QCoreApplication>
#include <QTextStream>
#include <QSpacerItem>
#include <QSplitter>
#include <QThread>
#include <filesystem>

#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"
#include "core/threadmanager.h"
#include "controllers/scancontroller.h"
#include "controllers/gamefilescontroller.h"
#include "controllers/backupcontroller.h"
#include "app/settingsdialog.h"
#include "app/aboutdialog.h"
#include "app/papyrusdialog.h"
#include "app/pathdialog.h"
#include "controllers/resultscontroller.h"
#include "widgets/reportlistwidget.h"
#include "widgets/markdownviewer.h"
#include "widgets/reportmetadatawidget.h"
#include "workers/updateworker.h"
#include "workers/papyrusworker.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/yaml.h"
#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/registry.h"
#include "classic_cxx_bridge/scangame.h"

#include <QDesktopServices>
#include <QGroupBox>
#include <QUrl>

namespace fs = std::filesystem;

// ── Construction / Destruction ─────────────────────────────────────

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
{
    setupUi();
    loadStylesheet();
    loadSettings();

    // Create core infrastructure
    m_signalHub = &SignalHub::instance();
    m_threadManager = new ThreadManager(this);
    m_scanController = new ScanController(m_signalHub, m_threadManager, this);
    m_gameFilesController = new GameFilesController(m_signalHub, m_threadManager, this);
    m_backupController = new BackupController(QString(), m_signalHub, this);
    m_resultsController = new ResultsController(
        m_signalHub, m_tabWidget, m_reportList,
        m_markdownViewer, m_reportMetadata, this);

    connectSignals();

    // Initialize results report directory from settings
    initResultsReportDir();

    // Check if first-run path detection is needed
    checkFirstRunPaths();
}

MainWindow::~MainWindow()
{
    saveSettings();
}

// ── Public interface ───────────────────────────────────────────────

void MainWindow::setVersion(const QString& version)
{
    setWindowTitle(QStringLiteral("CLASSIC ") + version);
}

void MainWindow::setStatusMessage(const QString& message)
{
    statusBar()->showMessage(message);
}

// ── UI Setup ───────────────────────────────────────────────────────

void MainWindow::setupUi()
{
    // Window geometry from PRD: 650x580 initial, 550x580 minimum
    resize(650, 580);
    setMinimumSize(550, 580);
    setWindowTitle(QStringLiteral("CLASSIC"));

    // Central tab widget
    m_tabWidget = new QTabWidget(this);
    setCentralWidget(m_tabWidget);

    // Status bar
    statusBar()->showMessage(QStringLiteral("Ready"));

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
        auto* headerLabel = new QLabel(
            QStringLiteral("BACKUP / RESTORE / REMOVE"));
        headerLabel->setAlignment(Qt::AlignCenter);
        headerLabel->setStyleSheet(
            QStringLiteral("font-size: 14px; font-weight: bold;"));
        mainLayout->addWidget(headerLabel);

        auto* instructionLabel = new QLabel(
            QStringLiteral(
                "Create backups of game files before modifying them. "
                "Restore to revert changes, or remove backups when no longer needed."));
        instructionLabel->setAlignment(Qt::AlignCenter);
        instructionLabel->setWordWrap(true);
        mainLayout->addWidget(instructionLabel);
    }

    // ── Helper lambda: create a backup section group box ──────────
    // Each section has 3 buttons: BACKUP, RESTORE, REMOVE
    auto createBackupSection = [this](const QString& title,
                                      const QString& backupType) -> QGroupBox* {
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
    mainLayout->addWidget(
        createBackupSection(QStringLiteral("Script Extender (XSE)"),
                            QStringLiteral("xse")));
    mainLayout->addWidget(
        createBackupSection(QStringLiteral("ReShade"),
                            QStringLiteral("reshade")));
    mainLayout->addWidget(
        createBackupSection(QStringLiteral("Vulkan"),
                            QStringLiteral("vulkan")));
    mainLayout->addWidget(
        createBackupSection(QStringLiteral("ENB"),
                            QStringLiteral("enb")));

    // ── Spacer ────────────────────────────────────────────────────
    mainLayout->addStretch();

    // ── Open Backups Folder button ────────────────────────────────
    {
        auto* btnOpenBackups = new QPushButton(
            QStringLiteral("OPEN CLASSIC BACKUPS"));
        btnOpenBackups->setFixedHeight(36);
        mainLayout->addWidget(btnOpenBackups);

        connect(btnOpenBackups, &QPushButton::clicked,
                this, &MainWindow::onOpenBackupsFolder);
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
    headerLabel->setAlignment(Qt::AlignCenter);
    headerLabel->setStyleSheet(QStringLiteral("font-size: 14px; font-weight: bold;"));
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
        {"BUFFOUT 4 INSTALLATION",  "https://www.nexusmods.com/fallout4/articles/3115"},
        {"FALLOUT 4 SETUP TIPS",    "https://www.nexusmods.com/fallout4/articles/4141"},
        {"IMPORTANT PATCHES LIST",  "https://www.nexusmods.com/fallout4/articles/3769"},
        {"BUFFOUT 4 NEXUS",         "https://www.nexusmods.com/fallout4/mods/47359"},
        {"CLASSIC NEXUS",           "https://www.nexusmods.com/fallout4/mods/56255"},
        {"CLASSIC GITHUB",          "https://github.com/evildarkarchon/CLASSIC-Fallout4"},
        {"DDS TEXTURE SCANNER",     "https://www.nexusmods.com/fallout4/mods/71588"},
        {"BETHINI PIE",             "https://www.nexusmods.com/site/mods/631"},
        {"WRYE BASH",               "https://www.nexusmods.com/fallout4/mods/20032"},
    };

    for (int i = 0; i < 9; ++i) {
        auto* btn = new QPushButton(QString::fromUtf8(links[i].text));
        btn->setFixedHeight(36);
        btn->setCursor(Qt::PointingHandCursor);

        // Capture URL by value for the lambda
        QString url = QString::fromUtf8(links[i].url);
        connect(btn, &QPushButton::clicked, this, [url]() {
            QDesktopServices::openUrl(QUrl(url));
        });

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
    connect(m_btnScanCrashLogs, &QPushButton::clicked,
            this, &MainWindow::onScanCrashLogs);
    connect(m_btnScanGameFiles, &QPushButton::clicked,
            this, &MainWindow::onScanGameFiles);

    // Exit button
    connect(m_btnExit, &QPushButton::clicked,
            this, &MainWindow::onExit);

    // ScanController → MainWindow
    connect(m_scanController, &ScanController::scanProgress,
            this, &MainWindow::onScanProgress);
    connect(m_scanController, &ScanController::scanFinished,
            this, [this](int /*total*/, int /*success*/, int /*errors*/) {
                onScanCompleted();
            });
    connect(m_scanController, &ScanController::scanError,
            this, &MainWindow::onScanError);

    // Settings button
    connect(m_btnSettings, &QPushButton::clicked,
            this, &MainWindow::onShowSettings);

    // Re-read settings when they change (e.g. from SettingsDialog)
    connect(m_signalHub, &SignalHub::settingsChanged,
            this, &MainWindow::loadSettings);

    // GameFilesController → MainWindow
    connect(m_gameFilesController, &GameFilesController::scanProgress,
            this, &MainWindow::onScanProgress);
    connect(m_gameFilesController, &GameFilesController::scanFinished,
            this, &MainWindow::onGameFilesScanFinished);
    connect(m_gameFilesController, &GameFilesController::scanError,
            this, &MainWindow::onGameFilesScanError);

    // BackupController → MainWindow
    connect(m_backupController, &BackupController::operationCompleted,
            this, &MainWindow::onBackupCompleted);
    connect(m_backupController, &BackupController::operationError,
            this, &MainWindow::onBackupError);

    // About button -- show the About dialog
    connect(m_btnAbout, &QPushButton::clicked, this, [this]() {
        AboutDialog dlg(this);
        dlg.exec();
    });

    // Help button -- open the GitHub wiki in the default browser
    connect(m_btnHelp, &QPushButton::clicked, this, [this]() {
        QDesktopServices::openUrl(
            QUrl(QStringLiteral("https://github.com/evildarkarchon/CLASSIC-Fallout4/wiki")));
    });

    // Open Crash Logs -- open the crash logs directory in file explorer
    connect(m_btnOpenCrashLogs, &QPushButton::clicked, this, [this]() {
        if (m_dataDir.isEmpty()) {
            QMessageBox::warning(this, QStringLiteral("Error"),
                QStringLiteral("CLASSIC Data directory not found."));
            return;
        }

        // Read crash logs directory from YAML settings
        QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC_Settings.yaml");
        QString crashDir;
        try {
            auto ops = classic::yaml::yaml_ops_new();
            classic::yaml::yaml_ops_load_file(*ops,
                std::string(settingsPath.toUtf8().constData()));
            auto dir = classic::yaml::yaml_ops_get_string(
                *ops, "CLASSIC_Settings.Crash Logs Folder", "");
            if (!dir.empty()) {
                crashDir = classic::toQString(dir);
            }
        } catch (...) {
            // Ignore -- will show error below
        }

        if (crashDir.isEmpty()) {
            QMessageBox::warning(this, QStringLiteral("Error"),
                QStringLiteral("Crash logs directory is not configured. "
                               "Please set it in Settings."));
            return;
        }

        QDesktopServices::openUrl(QUrl::fromLocalFile(crashDir));
    });

    // Check Updates -- run update check in a background thread
    connect(m_btnCheckUpdates, &QPushButton::clicked,
            this, &MainWindow::onCheckUpdates);

    // Papyrus Monitor -- toggle monitoring on/off
    connect(m_btnPapyrusMonitor, &QPushButton::clicked,
            this, &MainWindow::onTogglePapyrusMonitor);
}

// ── Settings persistence ───────────────────────────────────────────

void MainWindow::loadSettings()
{
    m_dataRoot = findDataRoot();
    if (m_dataRoot.isEmpty()) {
        m_dataDir = QString();
        return;
    }
    m_dataDir = m_dataRoot + QStringLiteral("/CLASSIC Data");

    // Load CLASSIC_Settings.yaml via CXX YAML bridge
    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC_Settings.yaml");
    try {
        auto ops = classic::yaml::yaml_ops_new();
        classic::yaml::yaml_ops_load_file(*ops, std::string(settingsPath.toUtf8().constData()));

        auto staging = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.Staging Mods Folder", "");
        if (!staging.empty()) {
            m_editStagingFolder->setText(classic::toQString(staging));
        }

        auto custom = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.Custom Scan Folder", "");
        if (!custom.empty()) {
            m_editCustomFolder->setText(classic::toQString(custom));
        }

        // Update backup controller with the game root from settings.
        // Guard against the first call during construction (before
        // m_backupController is created).
        auto gameRoot = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.Game Folder Path", "");
        if (!gameRoot.empty() && m_backupController) {
            m_backupController->setGameRoot(classic::toQString(gameRoot));
        }

        // Restore window geometry from settings (if saved previously)
        auto getInt = [&](const char* key) -> int {
            auto val = classic::yaml::yaml_ops_get_setting_value(*ops, key);
            if (val.value_type == "integer") {
                bool ok = false;
                int result = QString::fromStdString(std::string(val.value)).toInt(&ok);
                if (ok) return result;
            }
            return -1;
        };

        int wx = getInt("CLASSIC_Settings.Window X");
        int wy = getInt("CLASSIC_Settings.Window Y");
        int ww = getInt("CLASSIC_Settings.Window Width");
        int wh = getInt("CLASSIC_Settings.Window Height");

        if (ww > 0 && wh > 0) {
            resize(ww, wh);
        }
        if (wx >= 0 && wy >= 0) {
            move(wx, wy);
        }
    } catch (const std::exception& e) {
        setStatusMessage(QStringLiteral("Settings load failed: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        setStatusMessage(QStringLiteral("Settings load failed: unknown error"));
    }
}

void MainWindow::saveSettings()
{
    if (m_dataDir.isEmpty()) {
        return;
    }

    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC_Settings.yaml");
    try {
        auto ops = classic::yaml::yaml_ops_new();
        classic::yaml::yaml_ops_load_file(*ops, std::string(settingsPath.toUtf8().constData()));

        auto stagingValue = m_editStagingFolder->text();
        if (!stagingValue.isEmpty()) {
            classic::yaml::yaml_ops_set_string_setting(
                *ops,
                "CLASSIC_Settings.Staging Mods Folder",
                std::string(stagingValue.toUtf8().constData()));
        }

        auto customValue = m_editCustomFolder->text();
        if (!customValue.isEmpty()) {
            classic::yaml::yaml_ops_set_string_setting(
                *ops,
                "CLASSIC_Settings.Custom Scan Folder",
                std::string(customValue.toUtf8().constData()));
        }

        // Save window geometry
        classic::yaml::yaml_ops_set_integer_setting(
            *ops, "CLASSIC_Settings.Window X",
            static_cast<int64_t>(pos().x()));
        classic::yaml::yaml_ops_set_integer_setting(
            *ops, "CLASSIC_Settings.Window Y",
            static_cast<int64_t>(pos().y()));
        classic::yaml::yaml_ops_set_integer_setting(
            *ops, "CLASSIC_Settings.Window Width",
            static_cast<int64_t>(size().width()));
        classic::yaml::yaml_ops_set_integer_setting(
            *ops, "CLASSIC_Settings.Window Height",
            static_cast<int64_t>(size().height()));

        classic::yaml::yaml_ops_save_file(*ops, std::string(settingsPath.toUtf8().constData()));
    } catch (const std::exception& e) {
        setStatusMessage(QStringLiteral("Settings save failed: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        setStatusMessage(QStringLiteral("Settings save failed: unknown error"));
    }
}

void MainWindow::initResultsReportDir()
{
    if (m_dataDir.isEmpty()) {
        return;
    }

    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC_Settings.yaml");
    try {
        auto ops = classic::yaml::yaml_ops_new();
        classic::yaml::yaml_ops_load_file(*ops, std::string(settingsPath.toUtf8().constData()));

        auto crashLogsDir = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.Crash Logs Folder", "");
        if (!crashLogsDir.empty()) {
            m_resultsController->setReportDirectory(classic::toQString(crashLogsDir));
        }
    } catch (...) {
        // Not critical -- results tab will just be empty until a scan runs
    }
}

void MainWindow::checkFirstRunPaths()
{
    if (m_dataDir.isEmpty()) {
        return;
    }

    // Read current game and docs paths from YAML settings
    QString gamePath;
    QString docsPath;
    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC_Settings.yaml");
    try {
        auto ops = classic::yaml::yaml_ops_new();
        classic::yaml::yaml_ops_load_file(*ops,
            std::string(settingsPath.toUtf8().constData()));

        auto gp = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.Game Folder Path", "");
        if (!gp.empty()) {
            gamePath = classic::toQString(gp);
        }

        auto dp = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.INI Folder Path", "");
        if (!dp.empty()) {
            docsPath = classic::toQString(dp);
        }
    } catch (...) {
        // If settings can't be read, fall through to path detection
    }

    // Ask Rust whether path detection is needed
    try {
        auto needs = classic::scangame::needs_path_detection(
            classic::toRustString(gamePath),
            classic::toRustString(docsPath));

        if (!needs.needs_game_path && !needs.needs_docs_path) {
            return;  // All paths are detected -- nothing to do
        }

        // Show the manual path dialog
        ManualPathDialog dlg(needs.needs_game_path, needs.needs_docs_path, this);
        if (dlg.exec() != QDialog::Accepted) {
            return;  // User cancelled -- they can set paths later via Settings
        }

        // Save the user-provided paths to YAML settings
        try {
            auto ops = classic::yaml::yaml_ops_new();
            classic::yaml::yaml_ops_load_file(*ops,
                std::string(settingsPath.toUtf8().constData()));

            if (needs.needs_game_path && !dlg.gamePath().isEmpty()) {
                classic::yaml::yaml_ops_set_string_setting(
                    *ops, "CLASSIC_Settings.Game Folder Path",
                    std::string(dlg.gamePath().toUtf8().constData()));
            }
            if (needs.needs_docs_path && !dlg.docsPath().isEmpty()) {
                classic::yaml::yaml_ops_set_string_setting(
                    *ops, "CLASSIC_Settings.INI Folder Path",
                    std::string(dlg.docsPath().toUtf8().constData()));
            }

            classic::yaml::yaml_ops_save_file(*ops,
                std::string(settingsPath.toUtf8().constData()));

            // Reload settings so the rest of the app sees the new paths
            loadSettings();

        } catch (const std::exception& e) {
            setStatusMessage(
                QStringLiteral("Failed to save paths: ") + QString::fromUtf8(e.what()));
        }

    } catch (const std::exception& e) {
        // Path detection failure is not fatal
        setStatusMessage(
            QStringLiteral("Path detection failed: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        setStatusMessage(QStringLiteral("Path detection failed: unknown error"));
    }
}

QString MainWindow::findDataRoot() const
{
    std::error_code ec;

    // Check: Application exe directory for "CLASSIC Data/"
    QString appDir = QCoreApplication::applicationDirPath();
    fs::path appPath(appDir.toStdWString());
    if (fs::is_directory(appPath / "CLASSIC Data", ec)) {
        return appDir;
    }

    // Check: Current working directory for "CLASSIC Data/"
    fs::path cwd = fs::current_path(ec);
    if (fs::is_directory(cwd / "CLASSIC Data", ec)) {
        return QString::fromStdWString(cwd.wstring());
    }

    // Check: One level up from exe directory (common for build dirs)
    fs::path parentPath = appPath.parent_path();
    if (fs::is_directory(parentPath / "CLASSIC Data", ec)) {
        return QString::fromStdWString(parentPath.wstring());
    }

    // Fallback: return empty (caller should handle)
    return QString();
}

// ── Slot implementations ───────────────────────────────────────────

void MainWindow::onBrowseStaging()
{
    QString dir = QFileDialog::getExistingDirectory(
        this,
        QStringLiteral("Select Staging Mods Folder"),
        m_editStagingFolder->text());

    if (!dir.isEmpty()) {
        m_editStagingFolder->setText(dir);
        saveSettings();
    }
}

void MainWindow::onBrowseCustom()
{
    QString dir = QFileDialog::getExistingDirectory(
        this,
        QStringLiteral("Select Custom Scan Folder"),
        m_editCustomFolder->text());

    if (!dir.isEmpty()) {
        m_editCustomFolder->setText(dir);
        saveSettings();
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

    m_btnScanCrashLogs->setEnabled(false);
    m_btnScanCrashLogs->setText(QStringLiteral("SCANNING..."));
    setStatusMessage(QStringLiteral("Scanning crash logs..."));

    m_scanController->startScan(
        m_dataRoot,
        m_dataDir,
        QStringLiteral("Fallout4"),
        false,  // vrMode
        m_editCustomFolder->text()
    );
}

void MainWindow::onScanGameFiles()
{
    if (m_dataRoot.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Error"),
            QStringLiteral("Cannot find CLASSIC Data directory. "
                           "Ensure the application is in the correct location."));
        return;
    }

    // Read game paths from YAML settings for the scan
    QString gameExePath;
    QString gameRoot;
    QString gameName = QStringLiteral("Fallout4");

    QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC_Settings.yaml");
    try {
        auto ops = classic::yaml::yaml_ops_new();
        classic::yaml::yaml_ops_load_file(*ops,
            std::string(settingsPath.toUtf8().constData()));

        auto exePath = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.Game EXE Path", "");
        if (!exePath.empty()) {
            gameExePath = classic::toQString(exePath);
        }

        auto root = classic::yaml::yaml_ops_get_string(
            *ops, "CLASSIC_Settings.Game Folder Path", "");
        if (!root.empty()) {
            gameRoot = classic::toQString(root);
        }
    } catch (const std::exception&) {
        // Fall through -- paths may be empty
    }

    if (gameRoot.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Error"),
            QStringLiteral("Game folder path is not configured. "
                           "Please set it in Settings."));
        return;
    }

    // If exe path is not set, construct a default from game root
    if (gameExePath.isEmpty()) {
        gameExePath = gameRoot + QStringLiteral("/Fallout4.exe");
    }

    m_btnScanGameFiles->setEnabled(false);
    m_btnScanGameFiles->setText(QStringLiteral("SCANNING..."));
    setStatusMessage(QStringLiteral("Scanning game files..."));

    // Update backup controller with the game root (may have changed)
    m_backupController->setGameRoot(gameRoot);

    m_gameFilesController->startScan(gameExePath, gameRoot, gameName);
}

void MainWindow::onExit()
{
    saveSettings();
    QApplication::quit();
}

void MainWindow::onScanProgress(float percent, const QString& status)
{
    if (percent < 0.0f) {
        // Indeterminate progress
        setStatusMessage(status);
    } else {
        setStatusMessage(
            QStringLiteral("Scanning: %1% - %2")
                .arg(static_cast<int>(percent))
                .arg(status));
    }
}

void MainWindow::onScanCompleted()
{
    m_btnScanCrashLogs->setEnabled(true);
    m_btnScanCrashLogs->setText(QStringLiteral("SCAN CRASH LOGS"));
    setStatusMessage(QStringLiteral("Scan completed"));

    // Auto-switch to Results tab is handled by ResultsController::onScanCompleted()
}

void MainWindow::onScanError(const QString& message)
{
    m_btnScanCrashLogs->setEnabled(true);
    m_btnScanCrashLogs->setText(QStringLiteral("SCAN CRASH LOGS"));
    setStatusMessage(QStringLiteral("Scan failed: ") + message);

    QMessageBox::critical(this, QStringLiteral("Scan Error"), message);
}

void MainWindow::onShowSettings()
{
    SettingsDialog dlg(m_dataDir, m_signalHub, this);
    if (dlg.exec() == QDialog::Accepted) {
        emit m_signalHub->settingsChanged();
    }
}

// ── Game Files Scan slots ──────────────────────────────────────────

void MainWindow::onGameFilesScanFinished(const QString& output,
                                          bool hasErrors,
                                          uint32_t totalChecks) {
    m_btnScanGameFiles->setEnabled(true);
    m_btnScanGameFiles->setText(QStringLiteral("SCAN GAME FILES"));

    QString statusMsg = QStringLiteral("Game files scan completed: %1 checks")
        .arg(totalChecks);
    if (hasErrors) {
        statusMsg += QStringLiteral(" (errors found)");
    }
    setStatusMessage(statusMsg);

    // Show the results in a message box for now.
    // A future phase may route this to the Results tab instead.
    if (!output.isEmpty()) {
        QMessageBox::information(this,
            QStringLiteral("Game Files Scan Results"),
            output);
    }
}

void MainWindow::onGameFilesScanError(const QString& message) {
    m_btnScanGameFiles->setEnabled(true);
    m_btnScanGameFiles->setText(QStringLiteral("SCAN GAME FILES"));
    setStatusMessage(QStringLiteral("Game files scan failed: ") + message);

    QMessageBox::critical(this,
        QStringLiteral("Game Files Scan Error"), message);
}

// ── Backup operation slots ─────────────────────────────────────────

void MainWindow::onBackupCompleted(const QString& message) {
    setStatusMessage(message);
}

void MainWindow::onBackupError(const QString& error) {
    setStatusMessage(QStringLiteral("Backup error: ") + error);
    QMessageBox::warning(this, QStringLiteral("Backup Error"), error);
}

void MainWindow::onOpenBackupsFolder() {
    // The backup folder is "CLASSIC Backups" under the game root.
    // If the game root is not set, try the data root as fallback.
    QString backupDir;
    if (!m_backupController->gameRoot().isEmpty()) {
        backupDir = m_backupController->gameRoot()
            + QStringLiteral("/CLASSIC Backups");
    } else if (!m_dataRoot.isEmpty()) {
        backupDir = m_dataRoot + QStringLiteral("/CLASSIC Backups");
    }

    if (backupDir.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Error"),
            QStringLiteral("Cannot determine backup folder location."));
        return;
    }

    // Create the directory if it doesn't exist yet
    QDir().mkpath(backupDir);
    QDesktopServices::openUrl(QUrl::fromLocalFile(backupDir));
}

// ── Update check slot ─────────────────────────────────────────────

void MainWindow::onCheckUpdates()
{
    m_btnCheckUpdates->setEnabled(false);
    m_btnCheckUpdates->setText(QStringLiteral("CHECKING..."));
    setStatusMessage(QStringLiteral("Checking for updates..."));

    // Create worker + thread for the background update check
    auto* thread = new QThread();
    auto* worker = new UpdateWorker();

    // Wire completion signal (queued connection across threads)
    connect(worker, &UpdateWorker::updateCheckCompleted, this,
            [this](bool hasUpdate, const QString& latestVersion,
                   const QString& errorMessage) {
                m_btnCheckUpdates->setEnabled(true);
                m_btnCheckUpdates->setText(QStringLiteral("CHECK UPDATES"));

                if (!errorMessage.isEmpty()) {
                    setStatusMessage(QStringLiteral("Update check failed"));
                    QMessageBox::warning(this, QStringLiteral("Update Check"),
                        QStringLiteral("Error checking for updates:\n") + errorMessage);
                } else if (hasUpdate) {
                    setStatusMessage(
                        QStringLiteral("Update available: v") + latestVersion);
                    QMessageBox::information(this, QStringLiteral("Update Available"),
                        QStringLiteral("A new version is available: v%1\n\n"
                                       "Visit the GitHub releases page to download.")
                            .arg(latestVersion));
                } else {
                    setStatusMessage(QStringLiteral("You are up to date"));
                    QMessageBox::information(this, QStringLiteral("Update Check"),
                        QStringLiteral("You are running the latest version."));
                }

                // Clean up the worker thread
                m_threadManager->stopWorker(QStringLiteral("updateCheck"));
            });

    // Start the background check via ThreadManager
    QString currentVersion = QApplication::applicationVersion();
    connect(thread, &QThread::started, worker, [worker, currentVersion]() {
        worker->checkForUpdates(currentVersion);
    });

    m_threadManager->startWorker(QStringLiteral("updateCheck"), thread, worker);
}

// ── Papyrus monitoring slot ───────────────────────────────────────

void MainWindow::onTogglePapyrusMonitor()
{
    bool isChecked = m_btnPapyrusMonitor->isChecked();

    if (isChecked) {
        // Starting monitoring: read Papyrus log path from settings
        if (m_dataDir.isEmpty()) {
            QMessageBox::warning(this, QStringLiteral("Error"),
                QStringLiteral("CLASSIC Data directory not found."));
            m_btnPapyrusMonitor->setChecked(false);
            return;
        }

        QString papyrusLogPath;
        QString settingsPath = m_dataDir + QStringLiteral("/CLASSIC_Settings.yaml");
        try {
            auto ops = classic::yaml::yaml_ops_new();
            classic::yaml::yaml_ops_load_file(*ops,
                std::string(settingsPath.toUtf8().constData()));
            auto logPath = classic::yaml::yaml_ops_get_string(
                *ops, "CLASSIC_Settings.Papyrus Log Path", "");
            if (!logPath.empty()) {
                papyrusLogPath = classic::toQString(logPath);
            }
        } catch (...) {
            // Ignore
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
        m_btnPapyrusMonitor->setStyleSheet(
            QStringLiteral("background-color: #2E7D32;"));  // green
        setStatusMessage(QStringLiteral("Papyrus monitoring active"));

        // Create worker + thread
        auto* thread = new QThread();
        auto* worker = new PapyrusWorker();

        // Create the monitoring dialog
        m_papyrusDialog = new PapyrusDialog(this);

        // Wire stats updates from worker to dialog
        connect(worker, &PapyrusWorker::statsUpdated, m_papyrusDialog,
                &PapyrusDialog::updateStats);

        // Wire error signal
        connect(worker, &PapyrusWorker::monitoringError, this,
                [this](const QString& msg) {
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
        connect(thread, &QThread::started, worker,
                [worker, papyrusLogPath]() {
                    worker->start(papyrusLogPath);
                });

        m_threadManager->startWorker(QStringLiteral("papyrus"), thread, worker);

        // Show the dialog (non-modal)
        m_papyrusDialog->show();

    } else {
        // Stopping monitoring
        m_threadManager->stopWorker(QStringLiteral("papyrus"));

        m_btnPapyrusMonitor->setText(QStringLiteral("START PAPYRUS MONITORING"));
        m_btnPapyrusMonitor->setStyleSheet(QString());  // reset to default
        setStatusMessage(QStringLiteral("Papyrus monitoring stopped"));

        if (m_papyrusDialog) {
            m_papyrusDialog->close();
            m_papyrusDialog->deleteLater();
            m_papyrusDialog = nullptr;
        }
    }
}
