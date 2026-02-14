#include "widgets/markdownviewer.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QApplication>
#include <QClipboard>
#include <QFont>
#include <QKeySequence>
#include <QShortcut>
#include <QTimer>

#include "rust/cxx.h"
#include "classic_cxx_bridge/markdown.h"
#include "core/rust_qt_bridge.h"

// ── Construction ───────────────────────────────────────────────────

MarkdownViewer::MarkdownViewer(QWidget* parent)
    : QWidget(parent)
{
    setupUi();
    applyContentStylesheet();
}

// ── UI Setup ───────────────────────────────────────────────────────

void MarkdownViewer::setupUi()
{
    auto* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(0, 0, 0, 0);
    mainLayout->setSpacing(8);

    // Toolbar
    {
        auto* toolbar = new QHBoxLayout(); 
        toolbar->setSpacing(8);

        m_btnCopyAll = new QPushButton(QStringLiteral("Copy All"));
        toolbar->addWidget(m_btnCopyAll);

        toolbar->addStretch();

        m_btnZoomOut = new QPushButton(QStringLiteral("-"));
        m_btnZoomOut->setFixedWidth(32);
        toolbar->addWidget(m_btnZoomOut);

        m_zoomLabel = new QLabel(QStringLiteral("100%"));
        m_zoomLabel->setFixedWidth(48);
        m_zoomLabel->setAlignment(Qt::AlignCenter);
        toolbar->addWidget(m_zoomLabel);

        m_btnZoomIn = new QPushButton(QStringLiteral("+"));
        m_btnZoomIn->setFixedWidth(32);
        toolbar->addWidget(m_btnZoomIn);

        m_btnZoomReset = new QPushButton(QStringLiteral("Reset"));
        m_btnZoomReset->setFixedWidth(50);
        toolbar->addWidget(m_btnZoomReset);

        mainLayout->addLayout(toolbar);
    }

    // Text browser
    m_browser = new QTextBrowser();
    m_browser->setReadOnly(true);
    m_browser->setOpenExternalLinks(true);
    mainLayout->addWidget(m_browser, 1);

    // Button connections
    connect(m_btnCopyAll, &QPushButton::clicked, this, [this]() {
        QApplication::clipboard()->setText(m_browser->toPlainText());
        m_btnCopyAll->setText(QStringLiteral("Copied!"));
        // Reset label after a short delay
        QTimer::singleShot(1500, this, [this]() {
            m_btnCopyAll->setText(QStringLiteral("Copy All"));
        });
        emit copyAllRequested();
    });
    connect(m_btnZoomIn, &QPushButton::clicked, this, &MarkdownViewer::zoomIn);
    connect(m_btnZoomOut, &QPushButton::clicked, this, &MarkdownViewer::zoomOut);
    connect(m_btnZoomReset, &QPushButton::clicked, this, &MarkdownViewer::zoomReset);

    // Keyboard shortcuts
    auto* scZoomIn = new QShortcut(QKeySequence(QStringLiteral("Ctrl+=")), this);
    connect(scZoomIn, &QShortcut::activated, this, &MarkdownViewer::zoomIn);

    auto* scZoomOut = new QShortcut(QKeySequence(QStringLiteral("Ctrl+-")), this);
    connect(scZoomOut, &QShortcut::activated, this, &MarkdownViewer::zoomOut);

    auto* scZoomReset = new QShortcut(QKeySequence(QStringLiteral("Ctrl+0")), this);
    connect(scZoomReset, &QShortcut::activated, this, &MarkdownViewer::zoomReset);
}

void MarkdownViewer::applyContentStylesheet()
{
    // CSS for QTextBrowser document matching PRD section 2.8 dark theme.
    // This is applied as the document's default stylesheet, separate from
    // the application-wide QSS theme.
    static const QString css = QStringLiteral(
        "body { font-family: 'Segoe UI'; font-size: 13px; color: #e0e0e0; }"
        "h1 { font-size: 22px; font-weight: bold; color: #e0e0e0; }"
        "h2 { font-size: 18px; font-weight: bold; color: #e0e0e0; }"
        "h3 { font-size: 15px; font-weight: bold; color: #e0e0e0; }"
        "code { font-family: 'Consolas'; font-size: 12px;"
        "       background-color: #2a2a2e; border-radius: 3px; padding: 2px 4px; }"
        "pre  { font-family: 'Consolas'; font-size: 12px;"
        "       background-color: #2a2a2e; border-radius: 4px; padding: 8px; }"
        "hr   { border: none; border-top: 1px solid #555555; }"
        "blockquote { border-left: 3px solid #555555; font-style: italic;"
        "             padding-left: 8px; margin-left: 0; }"
        "a    { color: #5599dd; }"
    );

    m_browser->document()->setDefaultStyleSheet(css);
}

// ── Public interface ──────────────────────────────────────────────

void MarkdownViewer::setMarkdownContent(const QString& markdown)
{
    try {
        auto rustMarkdown = classic::toRustString(markdown);
        auto html = classic::markdown::markdown_to_html(rustMarkdown);
        m_browser->setHtml(classic::toQString(html));
    } catch (const rust::Error&) {
        // Fallback: show raw markdown if conversion fails
        m_browser->setPlainText(markdown);
    }
}

void MarkdownViewer::clear()
{
    m_browser->clear();
}

void MarkdownViewer::zoomIn()
{
    if (m_zoomPercent < kZoomMax) {
        m_zoomPercent += kZoomStep;
        applyZoom();
    }
}

void MarkdownViewer::zoomOut()
{
    if (m_zoomPercent > kZoomMin) {
        m_zoomPercent -= kZoomStep;
        applyZoom();
    }
}

void MarkdownViewer::zoomReset()
{
    m_zoomPercent = 100;
    applyZoom();
}

QString MarkdownViewer::plainText() const
{
    return m_browser->toPlainText();
}

// ── Helpers ───────────────────────────────────────────────────────

void MarkdownViewer::applyZoom()
{
    // Scale the base font size by zoom percentage
    auto font = m_browser->font();
    int scaledSize = kBasePointSize * m_zoomPercent / 100;
    if (scaledSize < 1) {
        scaledSize = 1;
    }
    font.setPointSize(scaledSize);
    m_browser->setFont(font);

    m_zoomLabel->setText(QString::number(m_zoomPercent) + QStringLiteral("%"));
}
