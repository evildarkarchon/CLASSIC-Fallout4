# Performance conformance fixtures

Authored durations use exact binary-fraction seconds: 125 ms, 375 ms, zero, and 1000 ms. Two scan samples produce count 2, total 500 ms, average 250 ms, minimum 125 ms, maximum 375 ms. A second label tests independent aggregation; clear removes both labels, and reuse starts count at one. Empty clear is idempotent. No timer or wall-clock calls occur. Receipts convert native seconds/milliseconds to integer milliseconds only when exactly integral; no rounding or timing tolerance hides differences. Global metrics are isolated by a dedicated serial runner and cleared on entry and exit. Timer lifecycle and reset aliases remain owned by existing tests.

`sample` and `reject` operations state one duration in both `seconds` and `milliseconds`. Seconds-based adapters (Rust, CXX, Python) read `seconds`; Node reads `milliseconds`. Each spelling is an exact binary value, so no adapter performs a lossy unit conversion ahead of the core's single nanosecond rounding. Every observation lists `rejections`: the stable token that prefixes each rejected sample's native error (Rust `TimingError::code()`, CXX `rust::Error`, Node `InvalidArg`, Python `ValueError`).

- `invalid-rejected-unchanged`: after one 125 ms sample, a negative sample, an out-of-range 10^12 s sample, and a negative sample for a never-recorded label are rejected (`timing_sample_negative`, `timing_sample_out_of_range`, `timing_sample_negative`). The summary still holds only the original sample.
- `counter-limit`: an 18×10^9 s sample fits below `u64::MAX` nanoseconds; adding 10^9 s would wrap the accumulated total, so it is rejected with `timing_counter_overflow` and the summary keeps one sample.
- `nanosecond-precision`: 1/1024 s (976 562.5 ns) and 3/1024 s (2 929 687.5 ns) are exact ties and round to the even neighbour (976 562 and 2 929 688 ns); `-0.0` is recorded as zero. `summaryNs` projects counts and averages in whole nanoseconds.

NaN and infinity cannot be written in JSON. Direct binding tests own those inputs.
