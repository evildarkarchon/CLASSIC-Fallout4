#pragma once

#include <QDialog>
#include <QLabel>
#include <QTextEdit>
#include <QPushButton>

class ErrorDialog : public QDialog {
    Q_OBJECT

public:
    explicit ErrorDialog(const QString& message,
                        const QString& details = QString(),
                        QWidget* parent = nullptr);

private slots:
    void copyDetails();

private:
    void setupUi(const QString& message, const QString& details);

    QLabel* m_iconLabel = nullptr;
    QLabel* m_messageLabel = nullptr;
    QTextEdit* m_detailsEdit = nullptr;
    QPushButton* m_copyButton = nullptr;
    QPushButton* m_okButton = nullptr;
};
