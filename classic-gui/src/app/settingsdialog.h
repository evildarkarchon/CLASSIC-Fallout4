#pragma once

#include <QCheckBox>
#include <QComboBox>
#include <QDialog>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QPushButton>
#include <QSpinBox>
#include <QStringList>
#include <QTabWidget>

// Qt's MOC-generated slot trampolines read queued-signal arguments out of
// QGenericArgument and pass them by value to the matching slot. That
// requires the complete definition of every slot argument type here, not
// just a forward declaration; otherwise moc_settingsdialog.cpp fails with
// "use of undefined type". Pulling the worker header in gives MOC the
// full `YamlCheckResult` / `YamlApplyResult` / `YamlRollbackResult`
// layouts without adding any dependency on the worker's bridge includes,
// which live in yamlupdateworker.cpp.
#include "../workers/yamlupdateworker.h"

class QThread;
class QCloseEvent;
class SignalHub;
class YamlUpdateWorker;

class SettingsDialog : public QDialog {
    Q_OBJECT

public:
    explicit SettingsDialog(const QString& dataDir, SignalHub* signalHub, QWidget* parent = nullptr);
    ~SettingsDialog() override;

protected:
    void closeEvent(QCloseEvent* event) override;
    void reject() override;

private:
    bool canCloseDialog();
    void setupUi();
    void setupGeneralTab(QTabWidget* tabs);
    void setupScanningTab(QTabWidget* tabs);
    void setupPathsTab(QTabWidget* tabs);
    void setupUpdatesTab(QTabWidget* tabs);
    void loadSettings();
    bool saveSettings();
    void resetToDefaults();

    /// Lazily construct the YAML-update worker + its QThread on first use.
    /// Kept lazy so the thread is only paid for when the user opens the
    /// Updates tab and clicks something. Safe to call repeatedly; subsequent
    /// calls are no-ops.
    void ensureYamlUpdateWorker();

private slots:
    void onBrowseGameFolder();
    void onResetGameFolder();
    void onBrowseIniFolder();
    void onResetIniFolder();
    void onBrowseUnsolvedLogsDestination();
    void onResetUnsolvedLogsDestination();
    void onAddFormIdDb();
    void onRemoveFormIdDb();
    void onCheckForUpdates();
    void onCheckForYamlUpdates();
    void onApplyYamlUpdates();
    void onRollbackYamlUpdate();

    /// Marshal worker-thread results back to the UI. These are invoked
    /// via queued connections, so all Qt widget mutations here run on the
    /// UI thread.
    void onYamlCheckFinished(YamlCheckResult result);
    void onYamlApplyFinished(YamlApplyResult result);
    void onYamlRollbackFinished(YamlRollbackResult result);

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
    QLineEdit* m_editUnsolvedLogsDestination = nullptr;
    QCheckBox* m_chkAutoSwitchAfterScan = nullptr;
    QSpinBox* m_spinMaxConcurrentScans = nullptr;

    // Paths tab
    QLineEdit* m_editGameFolder = nullptr;
    QLineEdit* m_editIniFolder = nullptr;
    QListWidget* m_listFormIdDbs = nullptr;

    // Updates tab (binary updates)
    QCheckBox* m_chkUpdateCheck = nullptr;
    QLabel* m_lblUpdateStatus = nullptr;
    QPushButton* m_btnCheckNow = nullptr;

    // Updates tab (YAML data updates — yaml-update-delivery Section 12)
    QPushButton* m_btnCheckYamlUpdates = nullptr;
    QPushButton* m_btnApplyYamlUpdates = nullptr;
    QPushButton* m_btnRollbackYamlUpdates = nullptr;
    QLabel* m_lblYamlUpdateStatus = nullptr;

    // Reviewed-decision token captured from the most recent
    // `onCheckForYamlUpdates` call. Populated when the check returns
    // `UpdateAvailable` and cleared otherwise. Used by
    // `onApplyYamlUpdates` to prove that the install targets match what
    // the user just saw on screen; see the "apply-with-decision" contract
    // in `classic_update_core::apply_yaml_update_with_decision`.
    QString m_approvedReleaseTag;
    QStringList m_approvedFileNames;
    QStringList m_approvedFileSha256;
    bool m_yamlUpdateBusy = false;

    // Dedicated worker thread for the YAML update check/apply/rollback
    // calls. Owned by the dialog; created lazily via
    // `ensureYamlUpdateWorker()`; torn down in the destructor. The worker
    // lives on `m_yamlUpdateThread` and communicates with the dialog via
    // queued signals so every UI mutation still happens on the UI thread.
    QThread* m_yamlUpdateThread = nullptr;
    YamlUpdateWorker* m_yamlUpdateWorker = nullptr;
};
