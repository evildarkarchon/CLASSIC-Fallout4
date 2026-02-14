#pragma once

#include <QDialog>

/// Simple modal "About CLASSIC" dialog displaying version and attribution.
class AboutDialog : public QDialog {
    Q_OBJECT

public:
    explicit AboutDialog(QWidget* parent = nullptr);
};
