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
    headerLabel->setProperty("class", QStringLiteral("sectionHeader"));
    headerLabel->setAlignment(Qt::AlignCenter);
    mainLayout->addWidget(headerLabel);

    // Stats grid: 2 columns (label | value)
    auto* grid = new QGridLayout();
    grid->setSpacing(8);

    auto addStatRow = [&](int row, const QString& label, QLabel*& valueLabel) {
        auto* lbl = new QLabel(label);
        lbl->setProperty("class", QStringLiteral("fieldLabel"));
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
    addStatRow(5, QStringLiteral("Dumps/Stacks Ratio:"), m_lblDumpsStacksRatio);

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
                                 double dumpsStacksRatio)
{
    m_lblDumps->setText(QString::number(dumps));
    m_lblStacks->setText(QString::number(stacks));
    m_lblWarnings->setText(QString::number(warnings));
    m_lblErrors->setText(QString::number(errors));
    m_lblLinesProcessed->setText(QString::number(linesProcessed));
    m_lblDumpsStacksRatio->setText(QString::number(dumpsStacksRatio, 'f', 2));
}

void PapyrusDialog::setMonitoringStatus(const QString& status)
{
    m_lblStatus->setText(status);
}

void PapyrusDialog::closeEvent(QCloseEvent* event)
{
    emit stopRequested();
    event->accept();
}
