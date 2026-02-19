#pragma once

#include <QProgressBar>

/// Progress bar that keeps label text green, but paints overlapping text
/// portions black where the filled chunk intersects the label area.
class AdaptiveProgressBar final : public QProgressBar {
public:
    explicit AdaptiveProgressBar(QWidget* parent = nullptr);

protected:
    void paintEvent(QPaintEvent* event) override;
};

