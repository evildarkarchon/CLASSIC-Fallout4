#pragma once

#include <QLabel>
#include <QString>
#include <QWidget>

class ReportMetadataWidget : public QWidget {
    Q_OBJECT

public:
    explicit ReportMetadataWidget(QWidget* parent = nullptr);

    void setMetadata(const QString& date, const QString& fileSize);
    void clear();

    // Static helpers for metadata extraction
    static QString extractDate(const QString& filename);
    static QString formatFileSize(qint64 bytes);

private:
    void setupUi();

    QLabel* m_dateLabel = nullptr;
    QLabel* m_sizeLabel = nullptr;
};
