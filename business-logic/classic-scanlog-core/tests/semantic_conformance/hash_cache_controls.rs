//! Empty-cache control observations for the public CXX-accessible state.

use super::{RunnerResult, invalid};
use classic_file_io_core::hash::FileHasher;
use serde_json::{Value, json};

/// Projects every portable statistic using an explicit canonical decimal ratio.
fn stats() -> Value {
    let value = FileHasher::cache_stats();
    json!({"hits":value.hits,"misses":value.misses,"hitRate":format!("{:.3}",value.hit_rate),"size":value.size,"capacity":value.capacity})
}

/// Exercises idempotent empty-state control calls without claiming populated-cache execution.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    if fixture["operation"] != "empty-controls" {
        return Err(invalid("unsupported cache control fixture").into());
    }
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();
    let initial = stats();
    let initial_size = FileHasher::cache_size();
    FileHasher::reset_cache_stats();
    let reset = stats();
    FileHasher::clear_cache();
    Ok(
        json!({"initial":initial,"initialSize":initial_size,"afterReset":reset,"afterClear":stats(),"finalSize":FileHasher::cache_size()}),
    )
}
