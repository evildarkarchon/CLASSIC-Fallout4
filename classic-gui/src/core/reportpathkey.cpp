#include "core/reportpathkey.h"

#include <QDir>
#include <QFileInfo>

namespace classic::gui {

QString reportPathKey(const QString& path)
{
    return QDir::cleanPath(QFileInfo(path).absoluteFilePath()).toLower();
}

} // namespace classic::gui
