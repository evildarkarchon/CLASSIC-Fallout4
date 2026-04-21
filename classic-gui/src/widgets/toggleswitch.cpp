#include "widgets/toggleswitch.h"

#include <QFontMetrics>
#include <QPainter>
#include <QPaintEvent>
#include <QPalette>
#include <QRect>

namespace {
// ToggleSwitch track/thumb colors (dark theme)
static const QColor kTrackOn(0x2F, 0xAE, 0x2F);       // #2FAE2F green
static const QColor kTrackOff(0x55, 0x55, 0x55);      // #555555 gray
static const QColor kTrackDisabled(0x3C, 0x3C, 0x3C); // #3C3C3C
static const QColor kThumbEnabled(0xF2, 0xF2, 0xF2);  // #F2F2F2
static const QColor kThumbDisabled(0x7A, 0x7A, 0x7A); // #7A7A7A
static const QColor kFocusRing(0x52, 0xFF, 0x52);     // #52FF52 Pip-Boy green
} // namespace

ToggleSwitch::ToggleSwitch(const QString& text, QWidget* parent)
    : QCheckBox(text, parent)
{
    setCursor(Qt::PointingHandCursor);
    setSizePolicy(QSizePolicy::MinimumExpanding, QSizePolicy::Fixed);
    setMinimumHeight(24);
}

QSize ToggleSwitch::sizeHint() const
{
    constexpr int kTrackWidth = 40;
    constexpr int kTrackHeight = 22;
    constexpr int kTextGap = 10;
    constexpr int kHorizontalPadding = 6;

    const QFontMetrics metrics(font());
    const int textWidth = metrics.horizontalAdvance(text());
    const int textHeight = metrics.height();
    const int width = kHorizontalPadding + kTrackWidth + kTextGap + textWidth + kHorizontalPadding;
    const int height = qMax(kTrackHeight, textHeight) + 4;
    return {width, height};
}

void ToggleSwitch::paintEvent(QPaintEvent* event)
{
    Q_UNUSED(event);

    constexpr int kTrackWidth = 40;
    constexpr int kTrackHeight = 22;
    constexpr int kThumbDiameter = 16;
    constexpr int kTrackPadding = 3;
    constexpr int kTextGap = 10;

    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing, true);

    QRect trackRect(0, (height() - kTrackHeight) / 2, kTrackWidth, kTrackHeight);
    if (layoutDirection() == Qt::RightToLeft) {
        trackRect.moveLeft(width() - kTrackWidth);
    }

    QColor trackColor = isChecked() ? kTrackOn : kTrackOff;
    if (!isEnabled()) {
        trackColor = kTrackDisabled;
    } else if (underMouse()) {
        trackColor = trackColor.lighter(110);
    }

    painter.setPen(Qt::NoPen);
    painter.setBrush(trackColor);
    painter.drawRoundedRect(trackRect, kTrackHeight / 2.0, kTrackHeight / 2.0);

    const int travel = kTrackWidth - kThumbDiameter - (kTrackPadding * 2);
    int thumbX = trackRect.left() + kTrackPadding + (isChecked() ? travel : 0);
    if (layoutDirection() == Qt::RightToLeft) {
        thumbX = trackRect.left() + kTrackPadding + (isChecked() ? 0 : travel);
    }

    const int thumbY = trackRect.top() + (kTrackHeight - kThumbDiameter) / 2;
    const QRect thumbRect(thumbX, thumbY, kThumbDiameter, kThumbDiameter);

    const QColor thumbColor = isEnabled() ? kThumbEnabled : kThumbDisabled;
    painter.setBrush(thumbColor);
    painter.drawEllipse(thumbRect);

    if (hasFocus()) {
        QPen focusPen(kFocusRing);
        focusPen.setWidth(1);
        painter.setPen(focusPen);
        painter.setBrush(Qt::NoBrush);
        painter.drawRoundedRect(trackRect.adjusted(-1, -1, 1, 1), kTrackHeight / 2.0, kTrackHeight / 2.0);
    }

    QRect textRect;
    if (layoutDirection() == Qt::RightToLeft) {
        textRect = QRect(0, 0, qMax(0, trackRect.left() - kTextGap), height());
    } else {
        textRect = QRect(trackRect.right() + kTextGap, 0, qMax(0, width() - (trackRect.right() + kTextGap)), height());
    }

    QColor textColor = palette().color(QPalette::WindowText);
    if (!isEnabled()) {
        textColor = palette().color(QPalette::Disabled, QPalette::WindowText);
    }
    painter.setPen(textColor);
    painter.drawText(
        textRect, Qt::AlignVCenter | (layoutDirection() == Qt::RightToLeft ? Qt::AlignRight : Qt::AlignLeft), text());
}
