#pragma once

#include <QHash>
#include <QString>
#include <QtGlobal>

#include "classic_cxx_bridge/scanner.h"

class BatchProgressModel {
public:
    explicit BatchProgressModel(int totalLogs = 0);

    /// Applies one serialized final-contract lifecycle event and returns monotonic batch progress.
    float update(const classic::scanner::ScanRunContractEvent& event);
    float percent() const;
    int totalLogs() const;
    int effectiveConcurrency() const;

private:
    struct LogProgressState {
        int rank = -1;
        float contribution = 0.0f;
    };

    static int rankFor(const classic::scanner::ScanRunContractEvent& event);
    static float contributionFor(const classic::scanner::ScanRunContractEvent& event);

    int m_totalLogs = 0;
    int m_effectiveConcurrency = 0;
    float m_percent = 0.0f;
    QHash<quint64, LogProgressState> m_logStates;
};
