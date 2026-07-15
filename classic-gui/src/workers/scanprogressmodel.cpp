#include "scanprogressmodel.h"

#include <algorithm>

namespace {
constexpr float kQueuedContribution = 0.0f;
constexpr float kStartedContribution = 0.08f;
constexpr float kSetupContribution = 0.15f;
constexpr float kParseContribution = 0.40f;
constexpr float kAnalyzeContribution = 0.82f;
constexpr float kFinalizeContribution = 0.95f;
constexpr float kTerminalContribution = 1.0f;
constexpr int kUnknownRank = -2;
} // namespace

BatchProgressModel::BatchProgressModel(int totalLogs)
    : m_totalLogs(totalLogs)
{
}

float BatchProgressModel::update(const classic::scanner::ScanRunContractEvent& event)
{
    using EventKind = classic::scanner::ScanRunContractEventKind;
    if (event.kind == EventKind::DiscoveryCompleted) {
        m_totalLogs = static_cast<int>(event.discovery.accepted_logs.size());
        return m_percent;
    }
    if (event.kind == EventKind::EffectiveConcurrencySelected) {
        m_effectiveConcurrency = static_cast<int>(event.effective_concurrency);
        return m_percent;
    }
    if (m_totalLogs <= 0) {
        return m_percent;
    }

    LogProgressState& state = m_logStates[static_cast<quint64>(event.discovery_index)];
    const int nextRank = rankFor(event);
    if (nextRank == kUnknownRank) {
        return m_percent;
    }

    if (nextRank >= state.rank) {
        state.rank = nextRank;
        state.contribution = contributionFor(event);
    }

    float aggregate = 0.0f;
    for (auto it = m_logStates.cbegin(); it != m_logStates.cend(); ++it) {
        aggregate += it.value().contribution;
    }

    const float computedPercent = (aggregate * 100.0f) / static_cast<float>(std::max(m_totalLogs, 1));
    m_percent = std::max(m_percent, computedPercent);
    return m_percent;
}

float BatchProgressModel::percent() const
{
    return m_percent;
}

int BatchProgressModel::totalLogs() const
{
    return m_totalLogs;
}

int BatchProgressModel::effectiveConcurrency() const
{
    return m_effectiveConcurrency;
}

int BatchProgressModel::rankFor(const classic::scanner::ScanRunContractEvent& event)
{
    using EventKind = classic::scanner::ScanRunContractEventKind;
    switch (event.kind) {
    case EventKind::LogQueued:
        return 0;
    case EventKind::LogStarted:
        return 1;
    case EventKind::LogPhase:
        switch (event.phase) {
        case classic::scanner::BatchProgressPhase::Setup:
            return 2;
        case classic::scanner::BatchProgressPhase::Parse:
            return 3;
        case classic::scanner::BatchProgressPhase::Analyze:
            return 4;
        case classic::scanner::BatchProgressPhase::Finalize:
            return 5;
        }
        break;
    case EventKind::LogFinished:
        return 6;
    case EventKind::DiscoveryCompleted:
    case EventKind::EffectiveConcurrencySelected:
        return kUnknownRank;
    }

    return kUnknownRank;
}

float BatchProgressModel::contributionFor(const classic::scanner::ScanRunContractEvent& event)
{
    using EventKind = classic::scanner::ScanRunContractEventKind;
    switch (event.kind) {
    case EventKind::LogQueued:
        return kQueuedContribution;
    case EventKind::LogStarted:
        return kStartedContribution;
    case EventKind::LogPhase:
        switch (event.phase) {
        case classic::scanner::BatchProgressPhase::Setup:
            return kSetupContribution;
        case classic::scanner::BatchProgressPhase::Parse:
            return kParseContribution;
        case classic::scanner::BatchProgressPhase::Analyze:
            return kAnalyzeContribution;
        case classic::scanner::BatchProgressPhase::Finalize:
            return kFinalizeContribution;
        }
        break;
    case EventKind::LogFinished:
        return kTerminalContribution;
    case EventKind::DiscoveryCompleted:
    case EventKind::EffectiveConcurrencySelected:
        return kQueuedContribution;
    }

    return kQueuedContribution;
}
