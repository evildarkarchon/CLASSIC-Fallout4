#include "widgets/reportmetadatawidget.h"

#include <QHBoxLayout>
#include <QFont>
#include <QFrame>
#include <QRegularExpression>

// ── Construction ───────────────────────────────────────────────────

ReportMetadataWidget::ReportMetadataWidget(QWidget* parent)
    : QWidget(parent)
{
    setupUi();
}

// ── UI Setup ───────────────────────────────────────────────────────

void ReportMetadataWidget::setupUi()
{
    auto* layout = new QHBoxLayout(this);
    layout->setContentsMargins(12, 6, 12, 6);
    layout->setSpacing(24);

    // Common label styling: semi-bold key, normal value
    auto makeField = [&](const QString& prefix) -> QLabel* {
        auto* label = new QLabel(prefix + QStringLiteral(" --"));
        label->setTextFormat(Qt::RichText);
        layout->addWidget(label);
        return label;
    };

    m_dateLabel = makeField(QStringLiteral("Date:"));
    m_sizeLabel = makeField(QStringLiteral("Size:"));

    layout->addStretch();
}

// ── Public interface ──────────────────────────────────────────────

void ReportMetadataWidget::setMetadata(const QString& date,
                                       const QString& fileSize)
{
    m_dateLabel->setText(QStringLiteral("<b>Date:</b> ") + date);
    m_sizeLabel->setText(QStringLiteral("<b>Size:</b> ") + fileSize);
}

void ReportMetadataWidget::clear()
{
    m_dateLabel->setText(QStringLiteral("<b>Date:</b> --"));
    m_sizeLabel->setText(QStringLiteral("<b>Size:</b> --"));
}

// ── Static helpers ────────────────────────────────────────────────

QString ReportMetadataWidget::extractDate(const QString& filename)
{
    // Match crash-YYYY-MM-DD-HH-MM-SS or similar timestamp in filename
    static const QRegularExpression re(
        QStringLiteral(R"((\d{4}-\d{2}-\d{2})-(\d{2}-\d{2}-\d{2}))"));

    auto match = re.match(filename);
    if (!match.hasMatch()) {
        return QStringLiteral("Unknown");
    }

    QString date = match.captured(1);
    QString time = match.captured(2).replace(QLatin1Char('-'), QLatin1Char(':'));
    return date + QStringLiteral(" ") + time;
}

QString ReportMetadataWidget::formatFileSize(qint64 bytes)
{
    if (bytes < 1024) {
        return QString::number(bytes) + QStringLiteral(" B");
    }
    if (bytes < 1024 * 1024) {
        return QString::number(static_cast<double>(bytes) / 1024.0, 'f', 1)
               + QStringLiteral(" KB");
    }
    return QString::number(static_cast<double>(bytes) / (1024.0 * 1024.0), 'f', 1)
           + QStringLiteral(" MB");
}

