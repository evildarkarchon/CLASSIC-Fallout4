#include "widgets/reportlistwidget.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFileInfo>
#include <QFile>
#include <QTextStream>
#include <QRegularExpression>
#include <algorithm>

// ── Construction ───────────────────────────────────────────────────

ReportListWidget::ReportListWidget(QWidget* parent)
    : QWidget(parent)
{
    setupUi();
}

// ── UI Setup ───────────────────────────────────────────────────────

void ReportListWidget::setupUi()
{
    auto* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(0, 0, 0, 0);
    mainLayout->setSpacing(8);

    // Search bar
    m_searchBar = new QLineEdit();
    m_searchBar->setPlaceholderText(QStringLiteral("Search reports..."));
    m_searchBar->setClearButtonEnabled(true);
    mainLayout->addWidget(m_searchBar);

    // Report list
    m_listWidget = new QListWidget();
    m_listWidget->setSelectionMode(QAbstractItemView::SingleSelection);
    mainLayout->addWidget(m_listWidget, 1);

    // Button bar
    {
        auto* btnLayout = new QHBoxLayout();
        btnLayout->setSpacing(8);

        m_btnRefresh = new QPushButton(QStringLiteral("Refresh"));
        m_btnDelete = new QPushButton(QStringLiteral("Delete"));
        m_btnOpenFolder = new QPushButton(QStringLiteral("Open Folder"));

        btnLayout->addWidget(m_btnRefresh);
        btnLayout->addWidget(m_btnDelete);
        btnLayout->addWidget(m_btnOpenFolder);

        mainLayout->addLayout(btnLayout);
    }

    // Connections
    connect(m_searchBar, &QLineEdit::textChanged,
            this, &ReportListWidget::onSearchTextChanged);
    connect(m_listWidget, &QListWidget::itemSelectionChanged,
            this, &ReportListWidget::onItemSelectionChanged);
    connect(m_btnRefresh, &QPushButton::clicked,
            this, &ReportListWidget::refreshRequested);
    connect(m_btnDelete, &QPushButton::clicked, this, [this]() {
        QString path = currentReportPath();
        if (!path.isEmpty()) {
            emit deleteRequested(path);
        }
    });
    connect(m_btnOpenFolder, &QPushButton::clicked,
            this, &ReportListWidget::openFolderRequested);
}

// ── Public interface ──────────────────────────────────────────────

void ReportListWidget::setReports(const QStringList& reportPaths)
{
    m_reportPaths = reportPaths;
    m_statusCache.clear();

    // Sort newest first by filename (crash-YYYY-MM-DD-HH-MM-SS sorts lexicographically)
    std::sort(m_reportPaths.begin(), m_reportPaths.end(),
              [](const QString& a, const QString& b) {
                  return QFileInfo(a).fileName() > QFileInfo(b).fileName();
              });

    // Pre-cache status for each report
    for (const auto& path : m_reportPaths) {
        m_statusCache[path] = detectStatus(path);
    }

    rebuildListItems(m_searchBar->text());
}

void ReportListWidget::clearReports()
{
    m_reportPaths.clear();
    m_statusCache.clear();
    m_listWidget->clear();
}

QString ReportListWidget::currentReportPath() const
{
    auto* item = m_listWidget->currentItem();
    if (!item) {
        return {};
    }
    return item->data(Qt::UserRole).toString();
}

// ── Private slots ─────────────────────────────────────────────────

void ReportListWidget::onSearchTextChanged(const QString& text)
{
    rebuildListItems(text);
}

void ReportListWidget::onItemSelectionChanged()
{
    QString path = currentReportPath();
    if (!path.isEmpty()) {
        emit reportSelected(path);
    }
}

// ── Helpers ───────────────────────────────────────────────────────

void ReportListWidget::rebuildListItems(const QString& filter)
{
    m_listWidget->clear();

    for (const auto& path : m_reportPaths) {
        QString filename = QFileInfo(path).fileName();

        // Apply filter
        if (!filter.isEmpty()
            && !filename.contains(filter, Qt::CaseInsensitive)) {
            continue;
        }

        auto* item = new QListWidgetItem(filename);
        item->setData(Qt::UserRole, path);

        // Timestamp tooltip
        QString timestamp = extractTimestamp(filename);
        if (!timestamp.isEmpty()) {
            item->setToolTip(QStringLiteral("Crash: ") + timestamp);
        }

        // Status-based coloring
        ReportStatus status = m_statusCache.value(path, ReportStatus::Unknown);
        item->setForeground(colorForStatus(status));

        m_listWidget->addItem(item);
    }
}

ReportListWidget::ReportStatus
ReportListWidget::detectStatus(const QString& filePath) const
{
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return ReportStatus::Unknown;
    }

    QTextStream stream(&file);
    QString content;
    // Read first ~50 lines for status detection
    for (int i = 0; i < 50 && !stream.atEnd(); ++i) {
        content += stream.readLine() + QStringLiteral("\n");
    }

    if (content.contains(QStringLiteral("NO ISSUES FOUND"), Qt::CaseInsensitive)
        || content.contains(QStringLiteral("NO CRASH"), Qt::CaseInsensitive)) {
        return ReportStatus::Solved;
    }

    if (content.contains(QStringLiteral("INCOMPLETE"), Qt::CaseInsensitive)
        || content.contains(QStringLiteral("TRUNCATED"), Qt::CaseInsensitive)) {
        return ReportStatus::Incomplete;
    }

    // If the file has content with suspects/errors, it's unsolved
    if (content.contains(QStringLiteral("SUSPECT"), Qt::CaseInsensitive)
        || content.contains(QStringLiteral("CRASH"), Qt::CaseInsensitive)) {
        return ReportStatus::Unsolved;
    }

    return ReportStatus::Unknown;
}

QColor ReportListWidget::colorForStatus(ReportStatus status)
{
    switch (status) {
    case ReportStatus::Solved:
        return QColor(0x4C, 0xAF, 0x50); // #4CAF50
    case ReportStatus::Unsolved:
        return QColor(0xF4, 0x43, 0x36); // #f44336
    case ReportStatus::Incomplete:
        return QColor(0xFF, 0xC1, 0x07); // #FFC107
    case ReportStatus::Unknown:
        return QColor(0xE0, 0xE0, 0xE0); // default light gray
    }
    return QColor(0xE0, 0xE0, 0xE0);
}

QString ReportListWidget::extractTimestamp(const QString& filename)
{
    // Match crash-YYYY-MM-DD-HH-MM-SS pattern
    static const QRegularExpression re(
        QStringLiteral(R"((\d{4}-\d{2}-\d{2})-(\d{2}-\d{2}-\d{2}))"));

    auto match = re.match(filename);
    if (!match.hasMatch()) {
        return {};
    }

    // Convert "2024-01-15" + "08-30-45" → "2024-01-15 08:30:45"
    QString date = match.captured(1);
    QString time = match.captured(2).replace(QLatin1Char('-'), QLatin1Char(':'));
    return date + QStringLiteral(" ") + time;
}
