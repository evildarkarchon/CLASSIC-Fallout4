#pragma once

#include "rust/cxx.h"

namespace classic::scanner {

struct ScanRunContractEvent;

/// Optional observer for serialized final-contract lifecycle events.
///
/// Implementations must not throw across the bridge. Delivery failures remain
/// adapter-owned and may request safe cancellation through ScanRunCancellation.
class ScanRunObserver {
public:
    virtual ~ScanRunObserver() = default;

    /// Receives one serialized event; implementations must not throw and may
    /// request safe cancellation through the control retained by the adapter.
    virtual void on_scan_run_event(const ScanRunContractEvent& event) const noexcept = 0;
};

} // namespace classic::scanner
