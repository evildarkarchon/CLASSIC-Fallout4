#include "mainwindow.h"

#include <QApplication>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFileDialog>
#include <QFile>
#include <QDir>
#include <QMessageBox>
#include <QCoreApplication>
#include <QTextStream>
#include <QSpacerItem>
#include <filesystem>

#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"
#include "core/threadmanager.h"
#include "controllers/scancontroller.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/yaml.h"
#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/registry.h"

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

    connectSignals();
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
    auto* layout = new QVBoxLayout(tabWidget);
    layout->setContentsMargins(16, 16, 16, 16);
    auto* label = new QLabel(QStringLiteral("Coming soon..."));
    label->setAlignment(Qt::AlignCenter);
    layout->addWidget(label);

    m_tabWidget->addTab(tabWidget, QStringLiteral("FILE BACKUP"));
}

void MainWindow::setupArticlesTab()
{
    auto* tabWidget = new QWidget();
    auto* layout = new QVBoxLayout(tabWidget);
    layout->setContentsMargins(16, 16, 16, 16);
    auto* label = new QLabel(QStringLiteral("Coming soon..."));
    label->setAlignment(Qt::AlignCenter);
    layout->addWidget(label);

    m_tabWidget->addTab(tabWidget, QStringLiteral("ARTICLES"));
}

void MainWindow::setupResultsTab()
{
    auto* tabWidget = new QWidget();
    auto* layout = new QVBoxLayout(tabWidget);
    layout->setContentsMargins(16, 16, 16, 16);
    auto* label = new QLabel(QStringLiteral("Coming soon..."));
    label->setAlignment(Qt::AlignCenter);
    layout->addWidget(label);

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

    // Placeholder connections for buttons wired in later phases:
    // m_btnAbout, m_btnHelp, m_btnSettings, m_btnOpenCrashLogs,
    // m_btnCheckUpdates, m_btnPapyrusMonitor
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

        classic::yaml::yaml_ops_save_file(*ops, std::string(settingsPath.toUtf8().constData()));
    } catch (const std::exception& e) {
        setStatusMessage(QStringLiteral("Settings save failed: ") + QString::fromUtf8(e.what()));
    } catch (...) {
        setStatusMessage(QStringLiteral("Settings save failed: unknown error"));
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

    m_btnScanGameFiles->setEnabled(false);
    m_btnScanGameFiles->setText(QStringLiteral("SCANNING..."));
    setStatusMessage(QStringLiteral("Scanning game files..."));

    // GameFilesController will be created and wired in Phase 6.
    setStatusMessage(QStringLiteral("Game files scan not yet implemented"));
    m_btnScanGameFiles->setEnabled(true);
    m_btnScanGameFiles->setText(QStringLiteral("SCAN GAME FILES"));
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

    // Auto-switch to Results tab (index 3)
    m_tabWidget->setCurrentIndex(3);
}

void MainWindow::onScanError(const QString& message)
{
    m_btnScanCrashLogs->setEnabled(true);
    m_btnScanCrashLogs->setText(QStringLiteral("SCAN CRASH LOGS"));
    setStatusMessage(QStringLiteral("Scan failed: ") + message);

    QMessageBox::critical(this, QStringLiteral("Scan Error"), message);
}
