#pragma once

#include <QMainWindow>
#include <QTabWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QStatusBar>

class SignalHub;
class ScanController;
class ThreadManager;
struct FeatureContext;

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
    void connectSignals();
    void loadSettings();
    void saveSettings();
    QString findDataRoot() const;

private slots:
    void onBrowseStaging();
    void onBrowseCustom();
    void onScanCrashLogs();
    void onScanGameFiles();
    void onExit();
    void onScanProgress(float percent, const QString& status);
    void onScanCompleted();
    void onScanError(const QString& message);

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

    // Controllers
    ScanController* m_scanController = nullptr;
    SignalHub* m_signalHub = nullptr;
    ThreadManager* m_threadManager = nullptr;

    // Data root paths
    QString m_dataRoot;
    QString m_dataDir;
};
