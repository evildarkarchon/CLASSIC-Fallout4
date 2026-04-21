#include "errordialog.h"

#include <QApplication>
#include <QClipboard>
#include <QFont>
#include <QHBoxLayout>
#include <QStyle>
#include <QVBoxLayout>

// ── Construction ───────────────────────────────────────────────────

ErrorDialog::ErrorDialog(const QString& message, const QString& details, QWidget* parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("Error"));
    setModal(true);
    setupUi(message, details);
}

// ── UI Setup ───────────────────────────────────────────────────────

void ErrorDialog::setupUi(const QString& message, const QString& details)
{
    setMinimumSize(400, 200);

    auto* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(16, 16, 16, 16);
    mainLayout->setSpacing(12);

    // ── Top row: icon + message ────────────────────────────────────
    {
        auto* topRow = new QHBoxLayout();
        topRow->setSpacing(12);

        // Error icon from system theme
        m_iconLabel = new QLabel();
        QIcon errorIcon = style()->standardIcon(QStyle::SP_MessageBoxCritical);
        m_iconLabel->setPixmap(errorIcon.pixmap(48, 48));
        m_iconLabel->setFixedSize(48, 48);
        m_iconLabel->setAlignment(Qt::AlignTop);
        topRow->addWidget(m_iconLabel);

        // Message text
        m_messageLabel = new QLabel(message);
        m_messageLabel->setWordWrap(true);
        m_messageLabel->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
        m_messageLabel->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
        topRow->addWidget(m_messageLabel);

        mainLayout->addLayout(topRow);
    }

    // ── Details text edit (hidden if no details) ───────────────────
    {
        m_detailsEdit = new QTextEdit();
        m_detailsEdit->setReadOnly(true);
        m_detailsEdit->setPlainText(details);

        QFont monoFont(QStringLiteral("Consolas"), 10);
        monoFont.setStyleHint(QFont::Monospace);
        m_detailsEdit->setFont(monoFont);

        if (details.isEmpty()) {
            m_detailsEdit->hide();
        }

        mainLayout->addWidget(m_detailsEdit);
    }

    // ── Button row ─────────────────────────────────────────────────
    {
        auto* btnRow = new QHBoxLayout();

        m_copyButton = new QPushButton(QStringLiteral("Copy Details"));
        if (details.isEmpty()) {
            m_copyButton->hide();
        }
        btnRow->addWidget(m_copyButton);

        btnRow->addStretch();

        m_okButton = new QPushButton(QStringLiteral("OK"));
        m_okButton->setDefault(true);
        m_okButton->setFixedWidth(80);
        btnRow->addWidget(m_okButton);

        mainLayout->addLayout(btnRow);
    }

    // Connections
    connect(m_okButton, &QPushButton::clicked, this, &QDialog::accept);
    connect(m_copyButton, &QPushButton::clicked, this, &ErrorDialog::copyDetails);

    // Adjust size based on whether details are present
    if (!details.isEmpty()) {
        resize(500, 300);
    }
}

// ── Slots ──────────────────────────────────────────────────────────

void ErrorDialog::copyDetails()
{
    QApplication::clipboard()->setText(m_detailsEdit->toPlainText());
    m_copyButton->setText(QStringLiteral("Copied!"));
}
