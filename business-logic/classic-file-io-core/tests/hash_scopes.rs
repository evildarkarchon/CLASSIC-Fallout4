//! Public-interface probes for scoped file-hash caches (#242).
//!
//! `classic_file_io_core` owns the SHA-256 file-hash cache and its hit/miss
//! statistics. Every cache store is reachable through an opaque
//! [`FileHashScope`] handle so a binding adapter (the merged Python
//! extension) can give each former extension facade (`classic_file_io` and
//! `classic_scangame`) its own cache, while the unscoped [`FileHasher`]
//! functions keep using one process default scope.
//!
//! These tests pin the contract the adapter relies on:
//!
//! - an isolated scope never sees, counts, evicts, resets, or clears another
//!   scope's entries or statistics;
//! - the unscoped [`FileHasher`] functions are exactly the default scope;
//! - every scope keeps the same capacity and bounded eviction rules;
//! - a handle can be moved into async work and keeps naming its own store.

use classic_file_io_core::FileIOError;
use classic_file_io_core::hash::{FileHashScope, FileHasher};
use serial_test::serial;
use std::io::Write;
use std::path::Path;
use tempfile::NamedTempFile;

/// SHA-256 of `b"Hello, World!"`.
const HELLO_SHA256: &str = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f";

/// Create a temporary file holding `content`; the file lives as long as the
/// returned handle.
fn temp_file_with(content: &[u8]) -> NamedTempFile {
    let mut file = NamedTempFile::new().expect("temp file should be created");
    file.write_all(content)
        .expect("temp file should be written");
    file.flush().expect("temp file should flush");
    file
}

/// Reset the process default scope so tests do not inherit its entries or
/// counters from earlier tests in this binary.
fn reset_default_scope() {
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();
}

/// The unscoped `FileHasher` functions and the default handle share one store.
#[test]
#[serial]
fn default_scope_is_the_store_behind_the_unscoped_functions() {
    reset_default_scope();
    let default = FileHashScope::default_scope();
    assert_eq!(default, FileHashScope::default_scope());

    let file = temp_file_with(b"Hello, World!");
    assert_eq!(
        FileHasher::hash_file(file.path()).expect("hash"),
        HELLO_SHA256
    );

    // The unscoped miss is visible through the default handle and vice versa.
    assert_eq!(default.cache_size(), 1);
    assert_eq!(default.cache_stats().misses, 1);
    assert_eq!(default.hash_file(file.path()).expect("hash"), HELLO_SHA256);
    assert_eq!(FileHasher::cache_stats().hits, 1);

    default.reset_cache_stats();
    assert_eq!(FileHasher::cache_stats().hits, 0);
    default.clear_cache();
    assert_eq!(FileHasher::cache_size(), 0);
}

/// Hits, misses, entries, clears, and resets stay inside the scope that made them.
#[test]
#[serial]
fn isolated_scopes_keep_independent_entries_and_statistics() {
    reset_default_scope();
    let file_io = FileHashScope::new_isolated();
    let scangame = FileHashScope::new_isolated();
    assert_ne!(file_io, scangame);
    assert_ne!(file_io, FileHashScope::default_scope());
    assert_eq!(file_io, file_io.clone(), "a clone names the same store");

    let file = temp_file_with(b"Hello, World!");

    // A miss then a hit in one scope.
    assert_eq!(file_io.hash_file(file.path()).expect("hash"), HELLO_SHA256);
    assert_eq!(file_io.hash_file(file.path()).expect("hash"), HELLO_SHA256);
    let file_io_stats = file_io.cache_stats();
    assert_eq!((file_io_stats.hits, file_io_stats.misses), (1, 1));
    assert_eq!(file_io_stats.size, 1);
    assert!((file_io_stats.hit_rate - 0.5).abs() < f64::EPSILON);

    // The other scope and the default scope saw none of that work: the same
    // path is a fresh miss for the other scope rather than a shared hit.
    let untouched = scangame.cache_stats();
    assert_eq!(
        (untouched.hits, untouched.misses, untouched.size),
        (0, 0, 0)
    );
    let default_untouched = FileHasher::cache_stats();
    assert_eq!(
        (
            default_untouched.hits,
            default_untouched.misses,
            default_untouched.size
        ),
        (0, 0, 0)
    );

    assert_eq!(scangame.hash_file(file.path()).expect("hash"), HELLO_SHA256);
    let scangame_stats = scangame.cache_stats();
    assert_eq!((scangame_stats.hits, scangame_stats.misses), (0, 1));
    assert_eq!(
        file_io.cache_stats().misses,
        1,
        "other scope counters unchanged"
    );

    // Resetting one scope's counters leaves the other scope's counters alone.
    scangame.reset_cache_stats();
    assert_eq!(scangame.cache_stats().misses, 0);
    assert_eq!(scangame.cache_size(), 1, "reset preserves entries");
    assert_eq!(file_io.cache_stats().hits, 1);

    // Clearing one scope's entries leaves the other scope's entries alone.
    file_io.clear_cache();
    assert_eq!(file_io.cache_size(), 0);
    assert_eq!(file_io.cache_stats().hits, 1, "clear preserves counters");
    assert_eq!(scangame.cache_size(), 1);

    // Unscoped clears and resets never reach an isolated scope.
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();
    assert_eq!(scangame.cache_size(), 1);
    assert_eq!(file_io.cache_stats().hits, 1);
}

/// Batch hashing through a scope counts and caches only in that scope.
#[test]
#[serial]
fn isolated_scope_batch_hashing_counts_only_in_that_scope() -> Result<(), FileIOError> {
    reset_default_scope();
    let scope = FileHashScope::new_isolated();
    let first = temp_file_with(b"batch-one");
    let second = temp_file_with(b"batch-two");
    let missing = Path::new("definitely-missing-hash-scope-file.bin");
    let paths = [first.path(), second.path(), missing];

    let results = scope.hash_files_parallel(&paths)?;
    assert_eq!(results.len(), 3);
    assert!(results[0].1.is_some());
    assert!(results[1].1.is_some());
    assert!(results[2].1.is_none(), "missing files fail soft");

    let map = scope.hash_files_to_map(&paths)?;
    assert_eq!(map.len(), 2);

    let stats = scope.cache_stats();
    // First batch: three misses (the missing file counts as a miss but is not
    // cached). Second batch: two hits plus another miss for the missing file.
    assert_eq!((stats.hits, stats.misses, stats.size), (2, 4, 2));

    let default_stats = FileHasher::cache_stats();
    assert_eq!(
        (default_stats.hits, default_stats.misses, default_stats.size),
        (0, 0, 0)
    );
    Ok(())
}

/// Every scope keeps the 1024-entry bound, and overfilling one evicts nothing elsewhere.
#[test]
#[serial]
fn isolated_scope_keeps_the_bounded_capacity_and_evicts_only_itself() {
    reset_default_scope();
    let scope = FileHashScope::new_isolated();
    let sibling = FileHashScope::new_isolated();
    let kept = temp_file_with(b"kept-in-sibling");
    sibling.hash_file(kept.path()).expect("hash");

    let capacity = scope.cache_stats().capacity;
    assert_eq!(capacity, FileHasher::cache_stats().capacity);
    assert_eq!(capacity, 1024);

    let files: Vec<_> = (0..=capacity)
        .map(|index| temp_file_with(format!("scoped-bounded-{index}").as_bytes()))
        .collect();
    for file in &files {
        scope.hash_file(file.path()).expect("hash");
    }

    let stats = scope.cache_stats();
    assert!(stats.size <= stats.capacity);
    assert_eq!(stats.misses, u64::try_from(files.len()).expect("fits"));

    // Filling one scope past capacity evicts nothing from another scope.
    assert_eq!(sibling.cache_size(), 1);
    assert_eq!(sibling.cache_stats().misses, 1);
    assert_eq!(FileHasher::cache_size(), 0);
}

/// A handle moved onto the shared runtime keeps hashing into its own store.
#[test]
#[serial]
fn scope_handle_moved_into_async_work_keeps_naming_its_store() {
    reset_default_scope();
    let scope = FileHashScope::new_isolated();
    let file = temp_file_with(b"Hello, World!");
    let path = file.path().to_path_buf();

    // Use the one shared runtime, as the binding adapters do, rather than a
    // private test runtime.
    let moved = scope.clone();
    let hash = classic_shared_core::get_runtime()
        .block_on(async move {
            tokio::task::spawn_blocking(move || moved.hash_file(&path))
                .await
                .expect("task should join")
        })
        .expect("hash");

    assert_eq!(hash, HELLO_SHA256);
    assert_eq!(scope.cache_stats().misses, 1);
    assert_eq!(scope.cache_size(), 1);
    assert_eq!(FileHasher::cache_stats().misses, 0);
}
