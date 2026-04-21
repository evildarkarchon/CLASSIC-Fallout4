#pragma once

#include <cstdint>

#include "rust/cxx.h"

namespace classic::scanner {

struct BatchProgressEvent;

class ScanBatchProgressCallback {
public:
    virtual ~ScanBatchProgressCallback() = default;

    virtual void on_batch_progress(const BatchProgressEvent& event) const = 0;
};

} // namespace classic::scanner
