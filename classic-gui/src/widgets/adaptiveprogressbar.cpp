#include "widgets/adaptiveprogressbar.h"

#include <QPainter>
#include <QPalette>
#include <QStyle>
#include <QStyleOptionProgressBar>

namespace {
QRect progressChunkRect(const QStyleOptionProgressBar& opt,
                        const QProgressBar* progressBar)
{
    const QRect contentsRect =
        progressBar->style()->subElementRect(
            QStyle::SE_ProgressBarContents, &opt, progressBar);
    if (contentsRect.isEmpty()) {
        return QRect();
    }

    // Busy/indeterminate mode: chunk position is style-driven and not exposed.
    // Use the full contents rect to keep text contrast reliable while active.
    if (opt.minimum >= opt.maximum) {
        return contentsRect;
    }

    const int boundedValue = qBound(opt.minimum, opt.progress, opt.maximum);
    const qreal ratio = qreal(boundedValue - opt.minimum) /
                        qreal(opt.maximum - opt.minimum);
    if (ratio <= 0.0) {
        return QRect();
    }
    if (ratio >= 1.0) {
        return contentsRect;
    }

    QRect chunkRect = contentsRect;
    if (progressBar->orientation() == Qt::Horizontal) {
        const int fillWidth = qMax(1, qRound(contentsRect.width() * ratio));
        const bool reverseFill =
            opt.invertedAppearance ^ (opt.direction == Qt::RightToLeft);
        if (reverseFill) {
            chunkRect.setLeft(contentsRect.right() - fillWidth + 1);
        } else {
            chunkRect.setRight(contentsRect.left() + fillWidth - 1);
        }
    } else {
        const int fillHeight = qMax(1, qRound(contentsRect.height() * ratio));
        if (opt.invertedAppearance) {
            chunkRect.setBottom(contentsRect.top() + fillHeight - 1);
        } else {
            chunkRect.setTop(contentsRect.bottom() - fillHeight + 1);
        }
    }

    return chunkRect;
}
}  // namespace

AdaptiveProgressBar::AdaptiveProgressBar(QWidget* parent)
    : QProgressBar(parent) {}

void AdaptiveProgressBar::paintEvent(QPaintEvent* event)
{
    Q_UNUSED(event);

    QStyleOptionProgressBar opt;
    initStyleOption(&opt);

    const QString labelText = opt.text;
    const bool shouldDrawText = opt.textVisible && !labelText.isEmpty();

    QStyleOptionProgressBar barOpt(opt);
    barOpt.textVisible = false;

    QPainter painter(this);
    style()->drawControl(QStyle::CE_ProgressBar, &barOpt, &painter, this);

    if (!shouldDrawText) {
        return;
    }

    const QRect textRect =
        style()->subElementRect(QStyle::SE_ProgressBarLabel, &opt, this);
    if (textRect.isEmpty()) {
        return;
    }

    painter.setPen(opt.palette.color(QPalette::Text));
    painter.drawText(textRect, opt.textAlignment, labelText);

    const QRect chunkRect = progressChunkRect(opt, this);
    if (chunkRect.isEmpty()) {
        return;
    }

    painter.save();
    painter.setClipRect(textRect.intersected(chunkRect));
    painter.setPen(Qt::black);
    painter.drawText(textRect, opt.textAlignment, labelText);
    painter.restore();
}
