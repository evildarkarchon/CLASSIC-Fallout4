#include "pathdialog.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QFileDialog>
#include <QDir>
#include <QMessageBox>

#include "classic_cxx_bridge/game.h"
#include "classic_cxx_bridge/path.h"
#include "classic_cxx_bridge/xse.h"

ManualPathDialog::ManualPathDialog(bool needsGamePath,
                                   bool needsDocsPath,
                                   QWidget* parent)
    : QDialog(parent)
    , m_needsGamePath(needsGamePath)
    , m_needsDocsPath(needsDocsPath)
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
        label->setProperty("class", QStringLiteral("fieldLabel"));
        mainLayout->addWidget(label);

        // D-11 / CXXS-09 consumer migration — display the expected XSE loader
        // filename using the new typed classic::xse namespace.
        try {
            auto loader_rust = classic::xse::xse_get_loader_name(classic::xse::XseType::F4SE);
            QString loader_name = QString::fromUtf8(loader_rust.data(),
                                                    static_cast<int>(loader_rust.size()));
            auto* xseHint = new QLabel(
                QStringLiteral("The game folder should contain: %1").arg(loader_name));
            xseHint->setProperty("class", QStringLiteral("hintLabel"));
            mainLayout->addWidget(xseHint);
        } catch (...) {
            // Non-fatal: XSE hint is informational only.
        }

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
        label->setProperty("class", QStringLiteral("fieldLabel"));
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
    connect(btnOk, &QPushButton::clicked, this, &ManualPathDialog::validateAndAccept);
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

void ManualPathDialog::validateAndAccept()
{
    if (m_needsGamePath) {
        const QString gamePath = m_editGamePath ? m_editGamePath->text().trimmed() : QString();
        if (gamePath.isEmpty() || !QDir(gamePath).exists()) {
            QMessageBox::warning(
                this,
                QStringLiteral("Invalid Game Folder"),
                QStringLiteral("Please select a valid existing game folder path."));
            return;
        }

        try {
            if (classic::path::check_restricted_path(std::string(gamePath.toUtf8().constData()))) {
                QMessageBox::warning(
                    this,
                    QStringLiteral("Invalid Game Folder"),
                    QStringLiteral("The selected game folder is in a restricted Windows system location."
                                   "\n\nPlease choose your actual game install folder."));
                return;
            }
        } catch (...) {
            // Non-fatal bridge failure: continue validation using directory existence checks.
        }
    }

    if (m_needsDocsPath) {
        const QString docsPath = m_editDocsPath ? m_editDocsPath->text().trimmed() : QString();
        if (docsPath.isEmpty() || !QDir(docsPath).exists()) {
            QMessageBox::warning(
                this,
                QStringLiteral("Invalid Documents / INI Folder"),
                QStringLiteral("Please select a valid existing Documents / INI folder path."));
            return;
        }
    }

    accept();
}
