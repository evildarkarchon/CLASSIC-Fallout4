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

float BatchProgressModel::update(const classic::scanner::BatchProgressEvent& event)
{
    if (m_totalLogs <= 0) {
        m_totalLogs = static_cast<int>(std::max(event.total, 1U));
    }

    LogProgressState& state = m_logStates[event.input_index];
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

int BatchProgressModel::rankFor(const classic::scanner::BatchProgressEvent& event)
{
    switch (event.event_kind) {
    case classic::scanner::BatchProgressEventKind::Queued:
        return 0;
    case classic::scanner::BatchProgressEventKind::Started:
        return 1;
    case classic::scanner::BatchProgressEventKind::Phase:
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
    case classic::scanner::BatchProgressEventKind::Completed:
    case classic::scanner::BatchProgressEventKind::Failed:
        return 6;
    }

    return kUnknownRank;
}

float BatchProgressModel::contributionFor(const classic::scanner::BatchProgressEvent& event)
{
    switch (event.event_kind) {
    case classic::scanner::BatchProgressEventKind::Queued:
        return kQueuedContribution;
    case classic::scanner::BatchProgressEventKind::Started:
        return kStartedContribution;
    case classic::scanner::BatchProgressEventKind::Phase:
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
    case classic::scanner::BatchProgressEventKind::Completed:
    case classic::scanner::BatchProgressEventKind::Failed:
        return kTerminalContribution;
    }

    return kQueuedContribution;
}
