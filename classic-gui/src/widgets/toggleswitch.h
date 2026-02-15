#pragma once

#include <QCheckBox>
#include <QSize>

class ToggleSwitch : public QCheckBox {
public:
    explicit ToggleSwitch(const QString& text, QWidget* parent = nullptr);

    QSize sizeHint() const override;

protected:
    void paintEvent(QPaintEvent* event) override;
};
