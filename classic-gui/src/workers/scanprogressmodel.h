#pragma once

#include <QHash>
#include <QString>
#include <QtGlobal>

#include "classic_cxx_bridge/scanner.h"

class BatchProgressModel {
public:
    explicit BatchProgressModel(int totalLogs = 0);

    float update(const classic::scanner::BatchProgressEvent& event);
    float percent() const;

private:
    struct LogProgressState {
        int rank = -1;
        float contribution = 0.0f;
    };

    static int rankFor(const classic::scanner::BatchProgressEvent& event);
    static float contributionFor(const classic::scanner::BatchProgressEvent& event);

    int m_totalLogs = 0;
    float m_percent = 0.0f;
    QHash<quint32, LogProgressState> m_logStates;
};
