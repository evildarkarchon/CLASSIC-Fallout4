# Graph Report - D:\repos\CLASSIC-Fallout4\foundation  (2026-07-28)

## Corpus Check
- Corpus is ~17,035 words - fits in a single context window. You may not need a graph.

## Summary
- 498 nodes · 817 edges · 24 communities
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 36 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 8
- Community 10
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 19
- Community 20

## God Nodes (most connected - your core abstractions)
1. `PathHandler` - 30 edges
2. `get_global_metrics()` - 23 edges
3. `ClassicError` - 20 edges
4. `PyPathHandler` - 19 edges
5. `StringProcessor` - 16 edges
6. `PyStringProcessor` - 16 edges
7. `PerformanceMetrics` - 14 edges
8. `PyGameId` - 13 edges
9. `GameId` - 10 edges
10. `PathLike` - 10 edges

## Surprising Connections (you probably didn't know these)
- `get_runtime_stats()` --calls--> `get_runtime()`  [INFERRED]
  classic-shared-py/src/lib.rs → classic-shared-core/src/lib.rs
- `is_runtime_healthy()` --calls--> `get_runtime()`  [INFERRED]
  classic-shared-py/src/lib.rs → classic-shared-core/src/lib.rs
- `without_gil_block_on()` --calls--> `get_runtime()`  [INFERRED]
  classic-shared-py/src/lib.rs → classic-shared-core/src/lib.rs
- `PathCacheEntry` --references--> `PathBuf`  [EXTRACTED]
  classic-shared-core/src/path_core.rs → classic-shared-py/src/path.rs
- `PathHandler` --references--> `PathBuf`  [EXTRACTED]
  classic-shared-core/src/path_core.rs → classic-shared-py/src/path.rs

## Import Cycles
- 1-file cycle: `classic-shared-py/src/path.rs -> classic-shared-py/src/path.rs`

## Communities (24 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (31): AsRef, Borrowed, classic_shared(), configure_python_stdio(), configure_python_text_stream(), get_runtime_stats(), parent_dir_from_python_path(), resolve_python_entry_dir() (+23 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (23): AtomicU64, get_timer_start(), OperationStats, PerformanceMetrics, RollingStats, AtomicUsize, DashMap, Default (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (14): PathCacheEntry, PathHandler, Arc, AtomicUsize, ClassicResult, DashMap, Default, Duration (+6 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (14): GameId, Display, Err, Formatter, FromStr, Result, Self, PyGameId (+6 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (16): ParseStringOperationError, Arc, Default, Display, Err, Error, Formatter, FromStr (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (16): Box, ClassicError, IntoClassicError, Result<T, E>, ClassicResult, E, Error, From (+8 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (10): PyPathHandler, Bound, Option, PyList, PyResult, Python, Self, String (+2 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (11): Builder, get_runtime(), Default, Option, Self, String, RuntimeConfig, test_get_runtime_returns_same_instance() (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.17
Nodes (22): bench_concurrent_recording(), bench_get_operations(), bench_get_stats(), bench_memory_efficiency(), bench_record_bytes(), bench_record_timing(), bench_throughput_calculation(), bench_timer() (+14 more)

### Community 12 - "Community 12"
Cohesion: 0.21
Nodes (10): PyStringProcessor, Bound, Default, PyList, PyResult, Python, Self, String (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.10
Nodes (4): test_get_global_metrics(), test_time_async(), test_time_operation(), test_time_with_bytes()

### Community 14 - "Community 14"
Cohesion: 0.20
Nodes (11): PyRustPerformanceMonitor, Bound, Default, Option, PyAny, PyDict, PyResult, Python (+3 more)

### Community 15 - "Community 15"
Cohesion: 0.23
Nodes (17): pyany_to_indexmap_str(), pyany_to_indexmap_vecstr(), pydict_to_indexmap_str(), pydict_to_indexmap_str_optional(), pydict_to_indexmap_vecstr(), Bound, Option, PyAny (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.21
Nodes (10): Result<T, E>, ResultExt, E, PyResult, T, ToPyErr, ClassicError, to_py_err() (+2 more)

### Community 17 - "Community 17"
Cohesion: 0.20
Nodes (7): AtomicBool, Arc, F, Option, scope_cancellation(), cancellation_scope_reads_its_control(), Output

### Community 19 - "Community 19"
Cohesion: 0.52
Nodes (6): bench_cache_eviction(), bench_cache_metrics(), bench_normalize_path(), bench_path_operations(), bench_validate_paths_batch(), Criterion

### Community 20 - "Community 20"
Cohesion: 0.52
Nodes (6): bench_batch_operations(), bench_common_prefix(), bench_normalize(), bench_split_lines(), bench_string_interning(), Criterion

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_runtime()` connect `Community 8` to `Community 0`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `PathBuf` connect `Community 0` to `Community 2`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `PathHandler` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `get_global_metrics()` (e.g. with `bench_concurrent_recording()` and `bench_get_operations()`) actually correct?**
  _`get_global_metrics()` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0796221322537112 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.10661268556005399 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.11260504201680673 - nodes in this community are weakly interconnected._