#include "widgets/reportlistwidget.h"

#include <algorithm>
#include <QDir>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QRegularExpression>
#include <QVBoxLayout>

namespace {

QString reportPathKey(const QString& path)
{
    return QDir::cleanPath(QFileInfo(path).absoluteFilePath()).toLower();
}

const QString kNewReportMarker = QStringLiteral(" ✨");

} // namespace

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

        m_btnRefresh->setObjectName(QStringLiteral("reportListRefreshButton"));
        m_btnDelete->setObjectName(QStringLiteral("reportListDeleteButton"));
        m_btnOpenFolder->setObjectName(QStringLiteral("reportListOpenFolderButton"));

        btnLayout->addWidget(m_btnRefresh);
        btnLayout->addWidget(m_btnDelete);
        btnLayout->addWidget(m_btnOpenFolder);

        mainLayout->addLayout(btnLayout);
    }

    // Connections
    connect(m_searchBar, &QLineEdit::textChanged, this, &ReportListWidget::onSearchTextChanged);
    connect(m_listWidget, &QListWidget::itemSelectionChanged, this, &ReportListWidget::onItemSelectionChanged);
    connect(m_btnRefresh, &QPushButton::clicked, this, &ReportListWidget::refreshRequested);
    connect(m_btnDelete, &QPushButton::clicked, this, [this]() {
        QString path = currentReportPath();
        if (!path.isEmpty()) {
            emit deleteRequested(path);
        }
    });
    connect(m_btnOpenFolder, &QPushButton::clicked, this, [this]() { emit openFolderRequested(currentReportPath()); });
}

// ── Public interface ──────────────────────────────────────────────

void ReportListWidget::setReports(const QStringList& reportPaths)
{
    setReports(reportPaths, {});
}

void ReportListWidget::setReports(const QStringList& reportPaths, const QSet<QString>& newReportPaths)
{
    m_reportPaths = reportPaths;

    m_newReportPaths.clear();
    for (const auto& path : newReportPaths) {
        m_newReportPaths.insert(reportPathKey(path));
    }

    // Sort newest first by filename (crash-YYYY-MM-DD-HH-MM-SS sorts lexicographically)
    std::sort(m_reportPaths.begin(), m_reportPaths.end(),
              [](const QString& a, const QString& b) { return QFileInfo(a).fileName() > QFileInfo(b).fileName(); });

    rebuildListItems(m_searchBar->text());
}

void ReportListWidget::clearReports()
{
    m_reportPaths.clear();
    m_newReportPaths.clear();
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
    const QString selectedPath = currentReportPath();
    m_listWidget->clear();
    QListWidgetItem* selectedItem = nullptr;

    for (const auto& path : m_reportPaths) {
        QString filename = QFileInfo(path).fileName();

        // Apply filter
        if (!filter.isEmpty() && !filename.contains(filter, Qt::CaseInsensitive)) {
            continue;
        }

        auto* item = new QListWidgetItem(filename);
        item->setData(Qt::UserRole, path);

        // Timestamp tooltip
        QString timestamp = extractTimestamp(filename);
        if (!timestamp.isEmpty()) {
            item->setToolTip(QStringLiteral("Crash: ") + timestamp);
        }

        if (m_newReportPaths.contains(reportPathKey(path))) {
            item->setData(NewReportRole, true);

            QFont font = item->font();
            font.setBold(true);
            item->setFont(font);
            item->setForeground(palette().highlight().color());
            item->setText(filename + kNewReportMarker);

            const QString newSuffix = QStringLiteral(" ✨ (new this session)");
            if (item->toolTip().isEmpty()) {
                item->setToolTip(newSuffix.trimmed());
            } else {
                item->setToolTip(item->toolTip() + newSuffix);
            }
        }

        m_listWidget->addItem(item);

        if (!selectedPath.isEmpty() && item->data(Qt::UserRole).toString() == selectedPath) {
            selectedItem = item;
        }
    }

    if (selectedItem) {
        m_listWidget->setCurrentItem(selectedItem);
    }
}

QString ReportListWidget::extractTimestamp(const QString& filename)
{
    // Match crash-YYYY-MM-DD-HH-MM-SS pattern
    static const QRegularExpression re(QStringLiteral(R"((\d{4}-\d{2}-\d{2})-(\d{2}-\d{2}-\d{2}))"));

    auto match = re.match(filename);
    if (!match.hasMatch()) {
        return {};
    }

    // Convert "2024-01-15" + "08-30-45" → "2024-01-15 08:30:45"
    QString date = match.captured(1);
    QString time = match.captured(2).replace(QLatin1Char('-'), QLatin1Char(':'));
    return date + QStringLiteral(" ") + time;
}
