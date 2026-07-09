#pragma once

#include "rust/cxx.h"
#include <QString>

namespace classic {

inline QString toQString(const rust::String& s)
{
    return QString::fromUtf8(s.data(), static_cast<int>(s.size()));
}

inline QString toQString(rust::Str s)
{
    return QString::fromUtf8(s.data(), static_cast<int>(s.size()));
}

inline rust::String toRustString(const QString& s)
{
    auto utf8 = s.toUtf8();
    return rust::String(utf8.constData(), utf8.size());
}

} // namespace classic
