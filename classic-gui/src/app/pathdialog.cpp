#include "pathdialog.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QFileDialog>

ManualPathDialog::ManualPathDialog(bool needsGamePath,
                                   bool needsDocsPath,
                                   QWidget* parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("CLASSIC - Path Setup"));
    setModal(true);
    setMinimumWidth(500);

    auto* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(16, 16, 16, 16);
    mainLayout->setSpacing(12);

    // Explanation header
    auto* headerLabel = new QLabel(
        QStringLiteral("CLASSIC could not automatically detect some required paths.\n"
                       "Please provide the following:"));
    headerLabel->setWordWrap(true);
    mainLayout->addWidget(headerLabel);

    // Game folder path row (only shown if needed)
    if (needsGamePath) {
        auto* label = new QLabel(QStringLiteral("Game Folder Path:"));
        label->setStyleSheet(QStringLiteral("font-weight: bold;"));
        mainLayout->addWidget(label);

        auto* rowLayout = new QHBoxLayout();
        m_editGamePath = new QLineEdit();
        m_editGamePath->setPlaceholderText(
            QStringLiteral("e.g. C:/Program Files (x86)/Steam/steamapps/common/Fallout 4"));
        rowLayout->addWidget(m_editGamePath);

        auto* btnBrowse = new QPushButton(QStringLiteral("Browse"));
        btnBrowse->setFixedWidth(80);
        connect(btnBrowse, &QPushButton::clicked,
                this, &ManualPathDialog::onBrowseGamePath);
        rowLayout->addWidget(btnBrowse);

        mainLayout->addLayout(rowLayout);
    }

    // Documents/INI path row (only shown if needed)
    if (needsDocsPath) {
        auto* label = new QLabel(QStringLiteral("Documents / INI Folder Path:"));
        label->setStyleSheet(QStringLiteral("font-weight: bold;"));
        mainLayout->addWidget(label);

        auto* rowLayout = new QHBoxLayout();
        m_editDocsPath = new QLineEdit();
        m_editDocsPath->setPlaceholderText(
            QStringLiteral("e.g. C:/Users/You/Documents/My Games/Fallout4"));
        rowLayout->addWidget(m_editDocsPath);

        auto* btnBrowse = new QPushButton(QStringLiteral("Browse"));
        btnBrowse->setFixedWidth(80);
        connect(btnBrowse, &QPushButton::clicked,
                this, &ManualPathDialog::onBrowseDocsPath);
        rowLayout->addWidget(btnBrowse);

        mainLayout->addLayout(rowLayout);
    }

    mainLayout->addStretch();

    // Button row: [Cancel] [OK]
    auto* btnRow = new QHBoxLayout();
    btnRow->addStretch();

    auto* btnCancel = new QPushButton(QStringLiteral("Cancel"));
    connect(btnCancel, &QPushButton::clicked, this, &QDialog::reject);
    btnRow->addWidget(btnCancel);

    auto* btnOk = new QPushButton(QStringLiteral("OK"));
    btnOk->setDefault(true);
    connect(btnOk, &QPushButton::clicked, this, &QDialog::accept);
    btnRow->addWidget(btnOk);

    mainLayout->addLayout(btnRow);
}

QString ManualPathDialog::gamePath() const
{
    return m_editGamePath ? m_editGamePath->text() : QString();
}

QString ManualPathDialog::docsPath() const
{
    return m_editDocsPath ? m_editDocsPath->text() : QString();
}

void ManualPathDialog::onBrowseGamePath()
{
    QString dir = QFileDialog::getExistingDirectory(
        this,
        QStringLiteral("Select Game Folder"),
        m_editGamePath->text());
    if (!dir.isEmpty()) {
        m_editGamePath->setText(dir);
    }
}

void ManualPathDialog::onBrowseDocsPath()
{
    QString dir = QFileDialog::getExistingDirectory(
        this,
        QStringLiteral("Select Documents / INI Folder"),
        m_editDocsPath->text());
    if (!dir.isEmpty()) {
        m_editDocsPath->setText(dir);
    }
}
