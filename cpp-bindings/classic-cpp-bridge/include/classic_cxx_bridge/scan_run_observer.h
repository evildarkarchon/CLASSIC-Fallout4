#pragma once

#include "rust/cxx.h"

namespace classic::scanner {

struct ScanRunContractEvent;
struct ScanRunObserverDelivery;

/// Optional observer for serialized final-contract lifecycle events.
///
/// Implementations must not throw across the bridge. A delivery failure is
/// reported by returning a failed ScanRunObserverDelivery instead; the
/// ScanRunObserverFailurePolicy passed to execution or settling then decides
/// whether Rust cancels the run, and the execution envelope reports the failure.
class ScanRunObserver {
public:
    virtual ~ScanRunObserver() = default;

    /// Receives one serialized event; implementations must not throw.
    ///
    /// Return a value-initialized `{}` when the event was delivered, or
    /// `{true, "why"}` when it could not be. After the first failed delivery
    /// Rust delivers no further events to this observer.
    virtual ScanRunObserverDelivery on_scan_run_event(const ScanRunContractEvent& event) const noexcept = 0;
};

} // namespace classic::scanner
