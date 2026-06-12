use super::*;

#[test]
fn test_runtime_config_default() {
    let config = RuntimeConfig::default();
    assert!(config.worker_threads.is_none());
    assert!(config.enable_io);
    assert!(config.enable_time);
    assert!(config.stack_size.is_none());
    assert_eq!(config.thread_name, "tokio-worker");
}

#[test]
fn test_runtime_config_io_optimized() {
    let config = RuntimeConfig::io_optimized();
    assert_eq!(config.worker_threads, Some(4));
    assert!(config.enable_io);
    assert!(config.enable_time);
    assert_eq!(config.thread_name, "classic-io");
}

#[test]
fn test_runtime_config_cpu_optimized() {
    let config = RuntimeConfig::cpu_optimized();
    assert!(config.worker_threads.is_none());
    assert_eq!(config.thread_name, "classic-cpu");
}

#[test]
fn test_runtime_config_minimal() {
    let config = RuntimeConfig::minimal();
    assert_eq!(config.worker_threads, Some(2));
    assert_eq!(config.stack_size, Some(1024 * 1024));
    assert_eq!(config.thread_name, "classic-min");
}

#[test]
fn test_runtime_config_debug() {
    let config = RuntimeConfig::default();
    let debug = format!("{:?}", config);
    assert!(debug.contains("RuntimeConfig"));
    assert!(debug.contains("tokio-worker"));
}

#[test]
fn test_runtime_config_clone() {
    let config = RuntimeConfig::io_optimized();
    let cloned = config.clone();
    assert_eq!(cloned.worker_threads, config.worker_threads);
    assert_eq!(cloned.thread_name, config.thread_name);
}

#[test]
fn test_runtime_config_apply_to_builder() {
    // Test that apply_to_builder doesn't panic with various configs
    let configs = vec![
        RuntimeConfig::default(),
        RuntimeConfig::io_optimized(),
        RuntimeConfig::cpu_optimized(),
        RuntimeConfig::minimal(),
        RuntimeConfig {
            worker_threads: Some(1),
            enable_io: false,
            enable_time: false,
            stack_size: Some(512 * 1024),
            thread_name: "test-worker".to_string(),
        },
    ];

    for config in configs {
        let builder = tokio::runtime::Builder::new_multi_thread();
        let _ = config.apply_to_builder(builder);
        // Just verify it doesn't panic
    }
}

#[test]
fn test_get_runtime_returns_same_instance() {
    let rt1 = get_runtime();
    let rt2 = get_runtime();
    // Both should be the same pointer (from LazyLock)
    assert!(std::ptr::eq(rt1, rt2));
}

#[test]
fn test_runtime_can_block_on() {
    let result = get_runtime().block_on(async { 42 });
    assert_eq!(result, 42);
}
