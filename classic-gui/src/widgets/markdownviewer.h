#pragma once

#include <QWidget>
#include <QTextBrowser>
#include <QPushButton>
#include <QLabel>
#include <QShortcut>

class MarkdownViewer : public QWidget {
    Q_OBJECT

public:
    explicit MarkdownViewer(QWidget* parent = nullptr);

    void setMarkdownContent(const QString& markdown);
    void clear();
    void zoomIn();
    void zoomOut();
    void zoomReset();
    QString plainText() const;

signals:
    void copyAllRequested();

private:
    void setupUi();
    void applyZoom();
    void applyContentStylesheet();

    QTextBrowser* m_browser = nullptr;
    QPushButton* m_btnCopyAll = nullptr;
    QPushButton* m_btnZoomIn = nullptr;
    QPushButton* m_btnZoomOut = nullptr;
    QPushButton* m_btnZoomReset = nullptr;
    QLabel* m_zoomLabel = nullptr;

    int m_zoomPercent = 100;
    static constexpr int kZoomMin = 80;
    static constexpr int kZoomMax = 200;
    static constexpr int kZoomStep = 10;
    static constexpr int kBasePointSize = 10; // ~13px at 96 DPI
};
