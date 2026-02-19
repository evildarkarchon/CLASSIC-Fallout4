#pragma once

#include <cstdint>

#include "rust/cxx.h"

namespace classic::scanner {

class ScanBatchProgressCallback {
public:
    virtual ~ScanBatchProgressCallback() = default;

    virtual void on_batch_progress(
        std::uint32_t completed,
        std::uint32_t total,
        std::uint32_t input_index,
        rust::Str log_path,
        bool success
    ) const = 0;
};

} // namespace classic::scanner
