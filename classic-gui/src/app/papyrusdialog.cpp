#include "papyrusdialog.h"

#include <QVBoxLayout>
#include <QGridLayout>
#include <QCloseEvent>

PapyrusDialog::PapyrusDialog(QWidget* parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("Papyrus Monitor"));
    setModal(false);  // Allow interaction with main window while monitoring
    setMinimumSize(380, 320);
    setupUi();
}

void PapyrusDialog::setupUi()
{
    auto* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(16, 16, 16, 16);
    mainLayout->setSpacing(12);

    // Header
    auto* headerLabel = new QLabel(QStringLiteral("PAPYRUS LOG MONITOR"));
    headerLabel->setAlignment(Qt::AlignCenter);
    headerLabel->setStyleSheet(QStringLiteral("font-size: 14px; font-weight: bold;"));
    mainLayout->addWidget(headerLabel);

    // Stats grid: 2 columns (label | value)
    auto* grid = new QGridLayout();
    grid->setSpacing(8);

    auto addStatRow = [&](int row, const QString& label, QLabel*& valueLabel) {
        auto* lbl = new QLabel(label);
        lbl->setStyleSheet(QStringLiteral("font-weight: bold;"));
        valueLabel = new QLabel(QStringLiteral("0"));
        valueLabel->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
        grid->addWidget(lbl, row, 0);
        grid->addWidget(valueLabel, row, 1);
    };

    addStatRow(0, QStringLiteral("Dumps:"),              m_lblDumps);
    addStatRow(1, QStringLiteral("Stacks:"),             m_lblStacks);
    addStatRow(2, QStringLiteral("Warnings:"),           m_lblWarnings);
    addStatRow(3, QStringLiteral("Errors:"),             m_lblErrors);
    addStatRow(4, QStringLiteral("Lines Processed:"),    m_lblLinesProcessed);
    addStatRow(5, QStringLiteral("Severity:"),           m_lblSeverity);
    addStatRow(6, QStringLiteral("Dumps/Stacks Ratio:"), m_lblDumpsStacksRatio);
    addStatRow(7, QStringLiteral("Total Issues:"),       m_lblTotalIssues);

    // Severity starts as "OK" with green color
    m_lblSeverity->setText(QStringLiteral("OK"));
    applySeverityColor(QStringLiteral("OK"));

    mainLayout->addLayout(grid);
    mainLayout->addStretch();

    // Status label
    m_lblStatus = new QLabel(QStringLiteral("Monitoring..."));
    m_lblStatus->setAlignment(Qt::AlignCenter);
    mainLayout->addWidget(m_lblStatus);

    // Stop button
    m_btnStop = new QPushButton(QStringLiteral("STOP MONITORING"));
    m_btnStop->setFixedHeight(36);
    mainLayout->addWidget(m_btnStop);

    connect(m_btnStop, &QPushButton::clicked, this, [this]() {
        emit stopRequested();
        accept();
    });
}

void PapyrusDialog::updateStats(uint32_t dumps,
                                 uint32_t stacks,
                                 uint32_t warnings,
                                 uint32_t errors,
                                 uint32_t linesProcessed,
                                 const QString& severity,
                                 double dumpsStacksRatio,
                                 uint32_t totalIssues)
{
    m_lblDumps->setText(QString::number(dumps));
    m_lblStacks->setText(QString::number(stacks));
    m_lblWarnings->setText(QString::number(warnings));
    m_lblErrors->setText(QString::number(errors));
    m_lblLinesProcessed->setText(QString::number(linesProcessed));
    m_lblSeverity->setText(severity);
    m_lblDumpsStacksRatio->setText(QString::number(dumpsStacksRatio, 'f', 2));
    m_lblTotalIssues->setText(QString::number(totalIssues));

    applySeverityColor(severity);
}

void PapyrusDialog::setMonitoringStatus(const QString& status)
{
    m_lblStatus->setText(status);
}

void PapyrusDialog::applySeverityColor(const QString& severity)
{
    // Color-code the severity label: green=OK, yellow=Warning, red=Critical
    QString color;
    if (severity == QStringLiteral("OK")) {
        color = QStringLiteral("color: #4CAF50; font-weight: bold;");  // green
    } else if (severity == QStringLiteral("Warning")) {
        color = QStringLiteral("color: #FF9800; font-weight: bold;");  // orange/yellow
    } else {
        // Critical or unknown -- red
        color = QStringLiteral("color: #F44336; font-weight: bold;");
    }
    m_lblSeverity->setStyleSheet(color);
}

void PapyrusDialog::closeEvent(QCloseEvent* event)
{
    emit stopRequested();
    event->accept();
}
