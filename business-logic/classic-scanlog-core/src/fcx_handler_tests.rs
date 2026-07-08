use super::*;
use std::{
    sync::Arc,
    sync::{
        LazyLock, Mutex as StdMutex,
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    thread,
    time::Duration,
};

static TEST_LOCK: LazyLock<StdMutex<()>> = LazyLock::new(|| StdMutex::new(()));

fn sample_issue() -> ConfigIssue {
    ConfigIssue::new(
        "test.ini".to_string(),
        Some("General".to_string()),
        "bExample".to_string(),
        "0".to_string(),
        "1".to_string(),
        "Example issue".to_string(),
        "warning".to_string(),
    )
}

fn seed_dirty_global_state() {
    let mut handler = GLOBAL_FCX_HANDLER.lock();
    handler.fcx_mode = true;
    handler.set_main_files_result("Main files OK\n".to_string());
    handler.set_game_files_result("Game files OK\n".to_string());
    handler.set_detected_issues(vec![sample_issue()]);
    handler.checks_run = true;
}

fn seed_clean_global_state() {
    let mut handler = GLOBAL_FCX_HANDLER.lock();
    handler.fcx_mode = false;
    handler.reset();
}

#[test]
fn test_fcx_disabled_messages() {
    let handler = FcxModeHandler::new(false);
    let fragment = handler.get_fcx_messages();

    assert!(fragment.is_empty());
    assert!(fragment.to_list().is_empty());
}

#[test]
fn test_fcx_enabled_messages() {
    let handler = FcxModeHandler::new(true);
    let fragment = handler.get_fcx_messages();

    assert!(!fragment.is_empty());
    let lines = fragment.to_list();
    assert!(lines.iter().any(|line| line.contains("ENABLED")));
}

#[test]
fn test_fcx_with_results() {
    let mut handler = FcxModeHandler::new(true);
    handler.set_main_files_result("Main files OK\n".to_string());
    handler.set_game_files_result("Game files OK\n".to_string());

    let fragment = handler.get_fcx_messages();
    let lines = fragment.to_list();

    assert!(lines.iter().any(|line| line.contains("Main files")));
    assert!(lines.iter().any(|line| line.contains("Game files")));
}

#[test]
fn test_fcx_has_results() {
    let mut handler = FcxModeHandler::new(true);
    assert!(!handler.has_results());

    handler.set_main_files_result("Main files OK\n".to_string());
    assert!(handler.has_results());
}

#[test]
fn test_fcx_reset() {
    let mut handler = FcxModeHandler::new(true);
    handler.set_main_files_result("Main files OK\n".to_string());
    handler.set_game_files_result("Game files OK\n".to_string());

    assert!(handler.has_results());

    handler.reset();

    assert!(!handler.has_results());
}

#[test]
fn test_fcx_convenience_constructors() {
    let enabled = FcxModeHandler::enabled();
    assert!(enabled.fcx_mode);

    let disabled = FcxModeHandler::disabled();
    assert!(!disabled.fcx_mode);
}

#[test]
fn fcx_reset_dirty_global_state_returns_success_and_clears_cached_state() {
    let _test_guard = TEST_LOCK.lock().expect("test lock poisoned");
    seed_dirty_global_state();

    assert_eq!(FcxModeHandler::reset_global_state(), Ok(()));

    let handler = GLOBAL_FCX_HANDLER.lock();
    assert!(handler.main_files_check.is_none());
    assert!(handler.game_files_check.is_none());
    assert!(handler.detected_issues.is_empty());
    assert!(!handler.checks_run);
}

#[test]
fn fcx_reset_clean_global_state_returns_unnecessary() {
    let _test_guard = TEST_LOCK.lock().expect("test lock poisoned");
    seed_clean_global_state();

    assert_eq!(
        FcxModeHandler::reset_global_state(),
        Err(FcxResetError::Unnecessary)
    );
}

#[test]
fn fcx_reset_waits_for_contention_and_clears_state_after_lock_release() {
    let _test_guard = TEST_LOCK.lock().expect("test lock poisoned");
    seed_dirty_global_state();

    let (lock_ready_tx, lock_ready_rx) = mpsc::channel();
    let (release_tx, release_rx) = mpsc::channel();
    let reset_finished = Arc::new(AtomicBool::new(false));
    let reset_finished_ref = Arc::clone(&reset_finished);

    let lock_holder = thread::spawn(move || {
        let _handler = GLOBAL_FCX_HANDLER.lock();
        lock_ready_tx.send(()).expect("lock ready signal failed");
        release_rx.recv().expect("release signal failed");
    });

    lock_ready_rx
        .recv()
        .expect("lock holder never acquired mutex");

    let reset_thread = thread::spawn(move || {
        let result = FcxModeHandler::reset_global_state();
        reset_finished_ref.store(true, Ordering::SeqCst);
        result
    });

    thread::sleep(Duration::from_millis(50));
    assert!(
        !reset_finished.load(Ordering::SeqCst),
        "reset should block while another thread holds the mutex"
    );

    release_tx.send(()).expect("failed to release lock holder");
    lock_holder.join().expect("lock holder thread panicked");

    assert_eq!(reset_thread.join().expect("reset thread panicked"), Ok(()));

    let handler = GLOBAL_FCX_HANDLER.lock();
    assert!(handler.main_files_check.is_none());
    assert!(handler.game_files_check.is_none());
    assert!(handler.detected_issues.is_empty());
    assert!(!handler.checks_run);
}
