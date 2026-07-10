#pragma once

#include <QDir>
#include <QFileInfo>
#include <QString>

namespace classic::gui {

/// Return an executable path that belongs to the selected game root.
/// The saved path is preserved only when it exists directly under the root; otherwise the conventional
/// `<gameRoot>/Fallout4.exe` path is returned. An empty root leaves the saved path unchanged.
[[nodiscard]] inline QString normalizeGameExecutablePath(const QString& gameExePath, const QString& gameRoot)
{
    const QString trimmedExePath = gameExePath.trimmed();
    const QString normalizedExePath = trimmedExePath.isEmpty() ? QString{} : QDir::cleanPath(trimmedExePath);
    const QString trimmedGameRoot = gameRoot.trimmed();
    const QString normalizedGameRoot = trimmedGameRoot.isEmpty() ? QString{} : QDir::cleanPath(trimmedGameRoot);

    if (normalizedGameRoot.isEmpty()) {
        return normalizedExePath;
    }

    if (!normalizedExePath.isEmpty()) {
        const QFileInfo exeInfo(normalizedExePath);
        const QString exeParent = QDir::cleanPath(exeInfo.absolutePath());
        if (exeInfo.exists() && exeParent.compare(normalizedGameRoot, Qt::CaseInsensitive) == 0) {
            return normalizedExePath;
        }
    }

    return QDir::cleanPath(normalizedGameRoot + QStringLiteral("/Fallout4.exe"));
}

} // namespace classic::gui
