#pragma once

#include <QDialog>
#include <QTabWidget>
#include <QComboBox>
#include <QCheckBox>
#include <QSpinBox>
#include <QLineEdit>
#include <QListWidget>
#include <QPushButton>
#include <QLabel>

class SignalHub;

class SettingsDialog : public QDialog {
    Q_OBJECT

public:
    explicit SettingsDialog(const QString& dataDir,
                           SignalHub* signalHub,
                           QWidget* parent = nullptr);

private:
    void setupUi();
    void setupGeneralTab(QTabWidget* tabs);
    void setupScanningTab(QTabWidget* tabs);
    void setupPathsTab(QTabWidget* tabs);
    void setupUpdatesTab(QTabWidget* tabs);
    void loadSettings();
    void saveSettings();
    void resetToDefaults();

private slots:
    void onBrowseGameFolder();
    void onResetGameFolder();
    void onBrowseIniFolder();
    void onResetIniFolder();
    void onAddFormIdDb();
    void onRemoveFormIdDb();
    void onCheckForUpdates();

private:
    QString m_dataDir;
    SignalHub* m_signalHub;

    // General tab
    QComboBox* m_comboGameVersion = nullptr;

    // Scanning tab
    QCheckBox* m_chkFcxMode = nullptr;
    QCheckBox* m_chkSimplifyLogs = nullptr;
    QCheckBox* m_chkShowFormIdValues = nullptr;
    QCheckBox* m_chkMoveUnsolvedLogs = nullptr;
    QCheckBox* m_chkAutoSwitchAfterScan = nullptr;
    QSpinBox* m_spinMaxConcurrentScans = nullptr;

    // Paths tab
    QLineEdit* m_editGameFolder = nullptr;
    QLineEdit* m_editIniFolder = nullptr;
    QListWidget* m_listFormIdDbs = nullptr;

    // Updates tab
    QCheckBox* m_chkUpdateCheck = nullptr;
    QLabel* m_lblUpdateStatus = nullptr;
    QPushButton* m_btnCheckNow = nullptr;
};
