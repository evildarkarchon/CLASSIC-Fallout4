#pragma once

#include <QDialog>
#include <QLabel>
#include <QPushButton>

/// Non-modal dialog displaying live Papyrus log monitoring statistics.
///
/// Shows a grid of stat labels (dumps, stacks, warnings, errors, ratio, etc.).
/// The dialog is updated externally via updateStats() -- typically called
/// from a PapyrusWorker signal.
class PapyrusDialog : public QDialog {
    Q_OBJECT

public:
    explicit PapyrusDialog(QWidget* parent = nullptr);

    /// Update all stat labels with new values from the monitoring worker.
    void updateStats(uint32_t dumps, uint32_t stacks, uint32_t warnings, uint32_t errors, uint32_t linesProcessed,
                     double dumpsStacksRatio);

    /// Set the status text ("Monitoring...", "Stopped", etc.).
    void setMonitoringStatus(const QString& status);

signals:
    /// Emitted when the user clicks "STOP MONITORING" or closes the dialog.
    void stopRequested();

protected:
    void closeEvent(QCloseEvent* event) override;

private:
    void setupUi();

    // Stat labels (right-hand value labels in the grid)
    QLabel* m_lblDumps = nullptr;
    QLabel* m_lblStacks = nullptr;
    QLabel* m_lblWarnings = nullptr;
    QLabel* m_lblErrors = nullptr;
    QLabel* m_lblLinesProcessed = nullptr;
    QLabel* m_lblDumpsStacksRatio = nullptr;

    // Status and controls
    QLabel* m_lblStatus = nullptr;
    QPushButton* m_btnStop = nullptr;
};
