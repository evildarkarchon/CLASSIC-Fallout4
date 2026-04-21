#include "typography.h"

#include <array>

#include <QApplication>
#include <QFont>
#include <QFontDatabase>
#include <QLatin1String>
#include <QString>

#include "classic_cxx_bridge/message.h"

namespace classic::gui {

namespace {

constexpr std::array<QLatin1String, 4> kBundledInterFaces = {
    QLatin1String(":/fonts/Inter/Inter-Regular.ttf"),
    QLatin1String(":/fonts/Inter/Inter-Italic.ttf"),
    QLatin1String(":/fonts/Inter/Inter-Bold.ttf"),
    QLatin1String(":/fonts/Inter/Inter-BoldItalic.ttf"),
};

} // namespace

void registerBundledFonts(const std::string& correlationId)
{
    for (const QLatin1String& resourcePath : kBundledInterFaces) {
        const int fontId = QFontDatabase::addApplicationFont(resourcePath);
        if (fontId == -1) {
            classic::message::log_startup_binding_contract_failed(
                "classic-gui.startup", std::string(resourcePath.data(), static_cast<std::size_t>(resourcePath.size())),
                "font_registration",
                "Rebuild classic-gui so the bundled Inter font resource is "
                "refreshed; the GUI will fall back to Segoe UI Variable or "
                "Segoe UI for this session.",
                "QFontDatabase::addApplicationFont returned -1", correlationId);
        }
    }
}

void installDefaultFont()
{
    QFont defaultFont(QStringLiteral("Inter"), 10);
    defaultFont.setStyleStrategy(QFont::PreferAntialias);
    defaultFont.setHintingPreference(QFont::PreferVerticalHinting);
    QApplication::setFont(defaultFont);
}

} // namespace classic::gui
