#pragma once

#include <QWidget>
#include <QLabel>
#include <QString>

class ReportMetadataWidget : public QWidget {
    Q_OBJECT

public:
    explicit ReportMetadataWidget(QWidget* parent = nullptr);

    void setMetadata(const QString& date, const QString& fileSize,
                     int issueCount, const QString& status);
    void clear();

    // Static helpers for metadata extraction
    static QString extractDate(const QString& filename);
    static QString formatFileSize(qint64 bytes);
    static int extractIssueCount(const QString& reportContent);
    static QString determineStatus(const QString& reportContent);

private:
    void setupUi();
    static QString statusDotHtml(const QString& status);

    QLabel* m_dateLabel = nullptr;
    QLabel* m_sizeLabel = nullptr;
    QLabel* m_issuesLabel = nullptr;
    QLabel* m_statusLabel = nullptr;
};
