//! Comprehensive tests for the utils module

#[cfg(test)]
mod tests {
    use classic_shared::*;

    mod path_tests {
        use super::*;

        #[test]
        fn test_path_normalization() {
            let handler = PathHandler::new(300);

            // Test basic normalization
            let result = handler.normalize_path("./test/../file.txt".to_string());
            assert!(result.is_ok());

            // Test absolute path
            let result = handler.normalize_path("/absolute/path".to_string());
            assert!(result.is_ok());
        }

        #[test]
        fn test_path_cache() {
            let handler = PathHandler::new(1); // 1 second TTL

            let path = "./test/path".to_string();

            // First call should cache
            let _ = handler.normalize_path(path.clone());
            let (path_cache_size, _) = handler.cache_stats();
            assert_eq!(path_cache_size, 1);

            // Second call should use cache
            let _ = handler.normalize_path(path.clone());
            let (path_cache_size, _) = handler.cache_stats();
            assert_eq!(path_cache_size, 1);

            // Clear cache
            handler.clear_cache();
            let (path_cache_size, _) = handler.cache_stats();
            assert_eq!(path_cache_size, 0);
        }

        #[test]
        fn test_path_validation_batch() {
            let handler = PathHandler::new(300);

            let paths = vec![
                ".".to_string(),
                "/nonexistent/path".to_string(),
                "Cargo.toml".to_string(),
            ];

            let results = handler.validate_paths_batch(paths);
            assert_eq!(results.len(), 3);

            // Current directory should be valid
            assert!(results[0].1);
            // Nonexistent path should be invalid
            assert!(!results[1].1);
        }

        #[test]
        fn test_path_operations() {
            let handler = PathHandler::new(300);

            // Test join
            let joined = handler.join_paths(
                "/base".to_string(),
                vec!["sub".to_string(), "file.txt".to_string()],
            );
            assert!(joined.contains("sub"));
            assert!(joined.contains("file.txt"));

            // Test split
            let components = handler.split_path("/base/sub/file.txt".to_string());
            assert!(components.len() > 0);

            // Test filename extraction
            let filename = handler
                .get_filename("/path/to/file.txt".to_string())
                .unwrap();
            assert_eq!(filename, Some("file.txt".to_string()));

            // Test extension extraction
            let ext = handler
                .get_extension("/path/to/file.txt".to_string())
                .unwrap();
            assert_eq!(ext, Some("txt".to_string()));

            // Test parent extraction
            let parent = handler.get_parent("/path/to/file.txt".to_string()).unwrap();
            assert!(parent.is_some());
        }

        #[test]
        fn test_common_prefix() {
            let handler = PathHandler::new(300);

            let paths = vec![
                "/home/user/documents/file1.txt".to_string(),
                "/home/user/documents/file2.txt".to_string(),
                "/home/user/downloads/file3.txt".to_string(),
            ];

            let prefix = handler.common_prefix(paths);
            assert!(prefix.is_some());
            assert!(prefix.unwrap().contains("home"));
        }
    }

    mod error_tests {
        use super::*;

        #[test]
        fn test_error_creation() {
            let err = ClassicError::io("Test I/O error", None::<std::io::Error>);
            assert!(err.to_string().contains("I/O error"));

            let err = ClassicError::path("Invalid path", Some("/test/path"));
            assert!(err.to_string().contains("Invalid path"));

            let err = ClassicError::validation("Invalid value", Some("test_field"));
            assert!(err.to_string().contains("Invalid value"));
        }

        #[test]
        fn test_error_with_context() {
            let err = ClassicError::validation("Invalid value", Some("test_field"))
                .with_context("During configuration loading");

            let err_str = err.to_string();
            assert!(err_str.contains("Invalid value") || err_str.contains("During configuration"));
        }

        #[test]
        fn test_error_conversion() {
            use std::io;
            let io_error = io::Error::new(io::ErrorKind::NotFound, "File not found");
            let classic_error = ClassicError::from(io_error);
            assert!(matches!(classic_error, ClassicError::NotFound { .. }));
        }
    }

    mod performance_tests {
        use super::performance::{RustPerformanceMonitor, Timer};
        use std::thread;
        use std::time::Duration;

        #[test]
        fn test_timer() {
            let timer = Timer::start("test_operation");
            thread::sleep(Duration::from_millis(10));
            timer.stop();

            let monitor = RustPerformanceMonitor::new();
            monitor.clear_metrics(); // Clear any previous metrics

            // Record a new metric
            monitor.record_metric("test_metric".to_string(), 100, Some(1024));
        }

        #[test]
        fn test_performance_monitoring() {
            let monitor = RustPerformanceMonitor::new();
            monitor.clear_metrics();

            // Record some metrics
            monitor.record_metric("operation1".to_string(), 50, Some(1024));
            monitor.record_metric("operation1".to_string(), 60, Some(2048));
            monitor.record_metric("operation2".to_string(), 100, None);
        }
    }
}
