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
    m_issuesLabel = makeField(QStringLiteral("Issues:"));
    m_statusLabel = makeField(QStringLiteral("Status:"));

    layout->addStretch();

    // Give the widget a subtle bottom border via a frame-like style
    setStyleSheet(QStringLiteral(
        "ReportMetadataWidget {"
        "  border-bottom: 1px solid #3c3c3c;"
        "  background-color: transparent;"
        "}"));
}

// ── Public interface ──────────────────────────────────────────────

void ReportMetadataWidget::setMetadata(const QString& date,
                                       const QString& fileSize,
                                       int issueCount,
                                       const QString& status)
{
    m_dateLabel->setText(QStringLiteral("<b>Date:</b> ") + date);
    m_sizeLabel->setText(QStringLiteral("<b>Size:</b> ") + fileSize);
    m_issuesLabel->setText(
        QStringLiteral("<b>Issues:</b> ") + QString::number(issueCount));
    m_statusLabel->setText(
        QStringLiteral("<b>Status:</b> ") + statusDotHtml(status)
        + QStringLiteral(" ") + status);
}

void ReportMetadataWidget::clear()
{
    m_dateLabel->setText(QStringLiteral("<b>Date:</b> --"));
    m_sizeLabel->setText(QStringLiteral("<b>Size:</b> --"));
    m_issuesLabel->setText(QStringLiteral("<b>Issues:</b> --"));
    m_statusLabel->setText(QStringLiteral("<b>Status:</b> --"));
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

int ReportMetadataWidget::extractIssueCount(const QString& reportContent)
{
    // Count lines containing "SUSPECT" or "[!]" as issue indicators
    int count = 0;
    const auto lines = reportContent.split(QLatin1Char('\n'));
    for (const auto& line : lines) {
        if (line.contains(QStringLiteral("SUSPECT"), Qt::CaseInsensitive)
            || line.contains(QStringLiteral("[!]"))) {
            ++count;
        }
    }
    return count;
}

QString ReportMetadataWidget::determineStatus(const QString& reportContent)
{
    if (reportContent.contains(QStringLiteral("NO ISSUES FOUND"), Qt::CaseInsensitive)
        || reportContent.contains(QStringLiteral("NO CRASH"), Qt::CaseInsensitive)) {
        return QStringLiteral("Solved");
    }

    if (reportContent.contains(QStringLiteral("INCOMPLETE"), Qt::CaseInsensitive)
        || reportContent.contains(QStringLiteral("TRUNCATED"), Qt::CaseInsensitive)) {
        return QStringLiteral("Incomplete");
    }

    return QStringLiteral("Unsolved");
}

// ── Private helpers ───────────────────────────────────────────────

QString ReportMetadataWidget::statusDotHtml(const QString& status)
{
    // Return a colored Unicode circle as an HTML span
    QString color;
    if (status == QStringLiteral("Solved")) {
        color = QStringLiteral("#4CAF50");
    } else if (status == QStringLiteral("Unsolved")) {
        color = QStringLiteral("#f44336");
    } else if (status == QStringLiteral("Incomplete")) {
        color = QStringLiteral("#FFC107");
    } else {
        color = QStringLiteral("#e0e0e0");
    }

    return QStringLiteral("<span style='color: %1;'>&#9679;</span>").arg(color);
}
