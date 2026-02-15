#pragma once

#include <QWidget>
#include <QLineEdit>
#include <QListWidget>
#include <QPushButton>
#include <QString>
#include <QStringList>

class ReportListWidget : public QWidget {
    Q_OBJECT

public:
    explicit ReportListWidget(QWidget* parent = nullptr);

    void setReports(const QStringList& reportPaths);
    void clearReports();
    QString currentReportPath() const;

signals:
    void reportSelected(const QString& filePath);
    void refreshRequested();
    void deleteRequested(const QString& filePath);
    void openFolderRequested();

private slots:
    void onSearchTextChanged(const QString& text);
    void onItemSelectionChanged();

private:
    void setupUi();
    void rebuildListItems(const QString& filter);
    static QString extractTimestamp(const QString& filename);

    QLineEdit* m_searchBar = nullptr;
    QListWidget* m_listWidget = nullptr;
    QPushButton* m_btnRefresh = nullptr;
    QPushButton* m_btnDelete = nullptr;
    QPushButton* m_btnOpenFolder = nullptr;

    QStringList m_reportPaths;
};
