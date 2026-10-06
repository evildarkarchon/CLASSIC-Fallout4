use super::*;
use classic_file_io_core::FileHasher;
use std::fs;
use tempfile::TempDir;

/// Build an explicit Fallout 4 intake over a temporary game root that holds a
/// fake executable, so a run always hashes at least that file.
fn intake_over_fake_game_root(temp: &TempDir) -> PyGameSetupIntake {
    let game_root = temp.path().join("Fallout4");
    let docs_root = temp.path().join("Docs");
    fs::create_dir_all(&game_root).expect("game root");
    fs::create_dir_all(&docs_root).expect("docs root");
    fs::write(game_root.join("Fallout4.exe"), b"not a real pe").expect("fake exe");
    PyGameSetupIntake {
        inner: GameSetupIntake::new(GameId::Fallout4, "Original")
            .with_game_root(game_root)
            .with_docs_root(docs_root),
    }
}

/// Game Setup Intake runs started through this facade hash only through
/// `SCANGAME_HASH_SCOPE`, never through the process default scope.
#[test]
fn run_game_setup_intake_hashes_only_in_the_scangame_facade_scope() {
    let temp = TempDir::new().expect("temp dir");
    let intake = intake_over_fake_game_root(&temp);
    // Nothing else in this test binary hashes through the default scope, so
    // it must stay at zero; the facade scope is a process static, so compare
    // its counters as deltas.
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();
    let before = SCANGAME_HASH_SCOPE.cache_stats();

    Python::attach(|py| {
        let first = run_game_setup_intake(py, &intake);
        let second = run_game_setup_intake(py, &intake);
        assert_eq!(first.status, second.status);
    });

    let after = SCANGAME_HASH_SCOPE.cache_stats();
    let misses = after.misses - before.misses;
    let hits = after.hits - before.hits;
    assert!(misses >= 1, "the first run hashes the executable");
    assert_eq!(hits, misses, "the repeat run is served from the same scope");

    let default = FileHasher::cache_stats();
    assert_eq!(
        (default.hits, default.misses, default.size),
        (0, 0, 0),
        "the facade never hashes through the process default scope"
    );
    assert_ne!(*SCANGAME_HASH_SCOPE, FileHashScope::default_scope());
}

/// Every registry-backed scangame entry point reads the facade's own Version
/// Registry scope, which must not be the process default (#233, #244).
#[test]
fn facade_version_registry_scope_is_not_the_process_default() {
    use classic_version_registry_core::{VersionRegistryScope, get_version_registry};

    let scope = &*crate::classic_scangame::SCANGAME_VERSION_REGISTRY_SCOPE;
    assert_ne!(*scope, VersionRegistryScope::default_scope());
    assert!(!std::ptr::eq(scope.registry(), get_version_registry()));
}
