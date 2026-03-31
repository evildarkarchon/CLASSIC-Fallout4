#include "aboutdialog.h"

#include <QVBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QApplication>
#include <QIcon>

AboutDialog::AboutDialog(QWidget* parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("About CLASSIC"));
    setModal(true);
    setFixedSize(400, 260);

    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(24, 24, 24, 24);
    layout->setSpacing(12);

    // Application icon (reuse window icon if available)
    QIcon appIcon = QApplication::windowIcon();
    if (!appIcon.isNull()) {
        auto* iconLabel = new QLabel();
        iconLabel->setPixmap(appIcon.pixmap(64, 64));
        iconLabel->setAlignment(Qt::AlignCenter);
        layout->addWidget(iconLabel);
    }

    // Title
    auto* titleLabel = new QLabel(QStringLiteral("CLASSIC"));
    titleLabel->setObjectName(QStringLiteral("aboutTitle"));
    titleLabel->setAlignment(Qt::AlignCenter);
    layout->addWidget(titleLabel);

    // Description and version
    QString version = QApplication::applicationVersion();
    auto* descLabel = new QLabel(
        QStringLiteral("Crash Log Auto Scanner & Setup Integrity Checker<br>"
                       "Version: %1<br><br>"
                       "Developed by evildarkarchon<br>"
                       "Based on the original CLASSIC by Poet<br>"
                       "Special credits to wxMichael, kittivelae, and AtomicFallout757<br><br>"
                       "<a href=\"https://github.com/evildarkarchon/CLASSIC-Fallout4\">"
                       "https://github.com/evildarkarchon/CLASSIC-Fallout4</a>")
            .arg(version));
    descLabel->setAlignment(Qt::AlignCenter);
    descLabel->setWordWrap(true);
    descLabel->setTextFormat(Qt::RichText);
    descLabel->setOpenExternalLinks(true);
    layout->addWidget(descLabel);

    layout->addStretch();

    // Close button
    auto* btnClose = new QPushButton(QStringLiteral("Close"));
    btnClose->setFixedWidth(100);
    connect(btnClose, &QPushButton::clicked, this, &QDialog::accept);

    auto* btnLayout = new QVBoxLayout();
    btnLayout->setAlignment(Qt::AlignCenter);
    btnLayout->addWidget(btnClose);
    layout->addLayout(btnLayout);
}
