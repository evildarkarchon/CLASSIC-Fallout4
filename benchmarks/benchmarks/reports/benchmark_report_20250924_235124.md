# CLASSIC Phase 6 Rust Migration Benchmark Report

Generated: 2025-09-24T23:51:24.459255
Duration: 0.00 seconds
Iterations: 1

## Executive Summary

**Overall Status:** NEEDS_IMPROVEMENT
**Message:** Significant optimization required across multiple components.

- **Targets Achieved:** 0/7 (0.0%)
- **Average Speedup:** 0.67x
- **Rust Components Active:** 10/10 (100.0%)

## Component Performance Summary

| Component | Avg Speedup | Target Achievement | Consistency |
|-----------|-------------|-------------------|-------------|
| parser | 1.0x | 0.0% | 1.00 |
| formid_analyzer | 1.3x | 0.0% | 1.00 |
| plugin_analyzer | 0.2x | 0.0% | 1.00 |
| record_scanner | 0.2x | 0.0% | 1.00 |
| report_generation | 0.2x | 0.0% | 1.00 |
| database_pool | 1.0x | 0.0% | 1.00 |
| file_io_core | 0.8x | 0.0% | 1.00 |

## Optimization Priorities

### Immediate Actions Required

#### parser - HIGH Priority
- **Current Speedup:** 1.0x
- **Target Achievement:** 0.0%
- **Recommendations:**
  - Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.
  - Performance below target (0.7% achieved). Consider algorithm optimizations or parallel processing.

#### formid_analyzer - HIGH Priority
- **Current Speedup:** 1.3x
- **Target Achievement:** 0.0%
- **Recommendations:**
  - Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.
  - Performance below target (2.7% achieved). Consider algorithm optimizations or parallel processing.

#### plugin_analyzer - HIGH Priority
- **Current Speedup:** 0.2x
- **Target Achievement:** 0.0%
- **Recommendations:**
  - Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.
  - Performance below target (0.7% achieved). Consider algorithm optimizations or parallel processing.

### Medium-Term Optimizations

## Memory Analysis

- **Components with Memory Issues:** 0
- **Overall Memory Efficiency:** 1.00x

### Memory Optimization Recommendations

## Detailed Component Results


### parser (minimal)

- **Speedup:** 1.04x
- **Target:** 150x (0.7% achieved)
- **Memory Efficiency:** 0.00x
- **Statistical Significance:** Yes

**Performance Details:**
- Rust: 0.0010s (±0.0000s)
- Python: 0.0010s (±0.0000s)
- Cache Hit Rate: 0.0%
- Success Rate: 100.0%

**Recommendations:**
- Performance below target (0.7% achieved). Consider algorithm optimizations or parallel processing.
- Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.

### formid_analyzer (minimal)

- **Speedup:** 1.34x
- **Target:** 50x (2.7% achieved)
- **Memory Efficiency:** 0.00x
- **Statistical Significance:** Yes

**Performance Details:**
- Rust: 0.0000s (±0.0000s)
- Python: 0.0000s (±0.0000s)
- Cache Hit Rate: 0.0%
- Success Rate: 100.0%

**Recommendations:**
- Performance below target (2.7% achieved). Consider algorithm optimizations or parallel processing.
- Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.

### plugin_analyzer (minimal)

- **Speedup:** 0.21x
- **Target:** 30x (0.7% achieved)
- **Memory Efficiency:** 0.00x
- **Statistical Significance:** Yes

**Performance Details:**
- Rust: 0.0002s (±0.0000s)
- Python: 0.0000s (±0.0000s)
- Cache Hit Rate: 0.0%
- Success Rate: 100.0%

**Recommendations:**
- Performance below target (0.7% achieved). Consider algorithm optimizations or parallel processing.
- Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.

### record_scanner (minimal)

- **Speedup:** 0.17x
- **Target:** 40x (0.4% achieved)
- **Memory Efficiency:** 0.00x
- **Statistical Significance:** Yes

**Performance Details:**
- Rust: 0.0001s (±0.0000s)
- Python: 0.0000s (±0.0000s)
- Cache Hit Rate: 0.0%
- Success Rate: 100.0%

**Recommendations:**
- Performance below target (0.4% achieved). Consider algorithm optimizations or parallel processing.
- Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.

### report_generation (minimal)

- **Speedup:** 0.18x
- **Target:** 75x (0.2% achieved)
- **Memory Efficiency:** 0.00x
- **Statistical Significance:** Yes

**Performance Details:**
- Rust: 0.0001s (±0.0000s)
- Python: 0.0000s (±0.0000s)
- Cache Hit Rate: 0.0%
- Success Rate: 100.0%

**Recommendations:**
- Performance below target (0.2% achieved). Consider algorithm optimizations or parallel processing.
- Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.

### database_pool (minimal)

- **Speedup:** 0.98x
- **Target:** 25x (3.9% achieved)
- **Memory Efficiency:** 0.00x
- **Statistical Significance:** Yes

**Performance Details:**
- Rust: 0.0000s (±0.0000s)
- Python: 0.0000s (±0.0000s)
- Cache Hit Rate: 0.0%
- Success Rate: 100.0%

**Recommendations:**
- Performance below target (3.9% achieved). Consider algorithm optimizations or parallel processing.
- Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.

### file_io_core (minimal)

- **Speedup:** 0.79x
- **Target:** 15x (5.3% achieved)
- **Memory Efficiency:** 0.00x
- **Statistical Significance:** Yes

**Performance Details:**
- Rust: 0.0000s (±0.0000s)
- Python: 0.0000s (±0.0000s)
- Cache Hit Rate: 0.0%
- Success Rate: 100.0%

**Recommendations:**
- Performance below target (5.3% achieved). Consider algorithm optimizations or parallel processing.
- Low cache hit rate (0.0%). Consider increasing cache sizes or improving cache strategies.

## System Information

- **Rust Status:** 100.0% components active
- **Missing Components:** None
- **Test Sizes:** minimal
- **Benchmark Types:** micro

---
*Generated by CLASSIC Comprehensive Benchmark Suite*
