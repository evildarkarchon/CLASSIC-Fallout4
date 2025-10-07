//! Comprehensive tests for the utils module

#[cfg(test)]
mod tests {
    use classic_core::utils::*;

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
            let joined = handler.join_paths("/base".to_string(), vec!["sub".to_string(), "file.txt".to_string()]);
            assert!(joined.contains("sub"));
            assert!(joined.contains("file.txt"));

            // Test split
            let components = handler.split_path("/base/sub/file.txt".to_string());
            assert!(components.len() > 0);

            // Test filename extraction
            let filename = handler.get_filename("/path/to/file.txt".to_string()).unwrap();
            assert_eq!(filename, Some("file.txt".to_string()));

            // Test extension extraction
            let ext = handler.get_extension("/path/to/file.txt".to_string()).unwrap();
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
        use super::performance::{Timer, RustPerformanceMonitor};
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

    mod log_processing_tests {
        use super::*;

        #[test]
        fn test_log_processor_creation() {
            let processor = LogProcessor::new();
            // Cache stats: (local_cache, global_pattern_cache)
            // Local cache should be empty for new processor
            // Global cache may have entries from other tests
            let (local, _global) = processor.cache_stats();
            assert_eq!(local, 0, "New LogProcessor should have empty local cache");
        }

        #[test]
        fn test_pattern_matching() {
            let mut processor = LogProcessor::new();

            let patterns = vec![
                "ERROR".to_string(),
                "WARNING".to_string(),
                "FormID".to_string(),
            ];

            processor.init_pattern_matcher(patterns.clone()).unwrap();

            let text = "This is an ERROR message with a WARNING about FormID 0x12345678".to_string();
            let results = processor.find_all_patterns(text, patterns);

            assert_eq!(results.len(), 3);
            // ERROR should be found
            assert!(results[0].1.len() > 0);
            // WARNING should be found
            assert!(results[1].1.len() > 0);
            // FormID should be found
            assert!(results[2].1.len() > 0);
        }

        #[test]
        fn test_formid_extraction() {
            let processor = LogProcessor::new();

            let text = "Found FormIDs: 0x12345678, 0xABCDEF01, and 87654321".to_string();
            let formids = processor.extract_formids(text);

            assert!(formids.len() >= 2);
            assert!(formids.iter().any(|f| f.contains("12345678")));
        }

        #[test]
        fn test_plugin_extraction() {
            let processor = LogProcessor::new();

            let text = r#"
                Loading plugin: Fallout4.esm
                Found dependency: DLCRobot.esm
                Mod installed: SomeMode.esp
                Patch file: Unofficial.esl
            "#.to_string();

            let plugins = processor.extract_plugins(text);
            assert!(plugins.len() >= 3);
            assert!(plugins.iter().any(|p| p.contains("Fallout4.esm")));
        }

        #[test]
        fn test_line_filtering() {
            let processor = LogProcessor::new();

            let lines = vec![
                "ERROR: Something went wrong".to_string(),
                "INFO: Normal operation".to_string(),
                "WARNING: Check this".to_string(),
                "ERROR: Another error".to_string(),
            ];

            // Filter for lines with ERROR
            let filtered = processor.filter_lines(
                lines.clone(),
                Some(vec!["ERROR".to_string()]),
                None
            );
            assert_eq!(filtered.len(), 2);

            // Filter out lines with ERROR
            let filtered = processor.filter_lines(
                lines.clone(),
                None,
                Some(vec!["ERROR".to_string()])
            );
            assert_eq!(filtered.len(), 2);
        }

        #[test]
        fn test_segment_parsing() {
            let processor = LogProcessor::new();

            let lines = vec![
                "Header information".to_string(),
                "MODULES:".to_string(),
                "Module1.dll".to_string(),
                "Module2.dll".to_string(),
                "STACK:".to_string(),
                "Stack frame 1".to_string(),
                "Stack frame 2".to_string(),
            ];

            let segments = processor.parse_segments(lines);
            assert!(segments.len() >= 2);
            assert!(segments.iter().any(|(name, _)| name.contains("MODULES")));
        }

        #[test]
        fn test_parallel_processing() {
            let processor = LogProcessor::new();

            let lines = vec![
                "  line with spaces  ".to_string(),
                "MIXED case LINE".to_string(),
                "normal line".to_string(),
            ];

            let trimmed = processor.process_lines_parallel(lines.clone(), "trim".to_string());
            assert_eq!(trimmed[0], "line with spaces");

            let upper = processor.process_lines_parallel(lines.clone(), "upper".to_string());
            assert_eq!(upper[1], "MIXED CASE LINE");

            let lower = processor.process_lines_parallel(lines, "lower".to_string());
            assert_eq!(lower[1], "mixed case line");
        }

        #[test]
        fn test_fast_find() {
            let processor = LogProcessor::new();

            let text = "This is a test string with TEST and Test words".to_string();

            // Case sensitive
            let positions = processor.fast_find(text.clone(), "test".to_string(), false);
            assert_eq!(positions.len(), 1);

            // Case insensitive
            let positions = processor.fast_find(text, "test".to_string(), true);
            assert!(positions.len() >= 3);
        }
    }

    mod string_tests {
        use super::*;

        #[test]
        fn test_string_processor() {
            let processor = StringProcessor::new();

            // Test interning
            let s1 = processor.intern("test_string".to_string());
            let s2 = processor.intern("test_string".to_string());
            assert_eq!(s1, s2);
            assert_eq!(processor.pool_stats(), 1);

            // Test batch processing
            let strings = vec![
                "Hello".to_string(),
                "World".to_string(),
                "Test".to_string(),
            ];

            let upper = processor.process_batch(strings.clone(), "upper".to_string());
            assert_eq!(upper[0], "HELLO");

            let lower = processor.process_batch(strings.clone(), "lower".to_string());
            assert_eq!(lower[0], "hello");

            // Test common prefix
            let strings = vec![
                "prefix_file1".to_string(),
                "prefix_file2".to_string(),
                "prefix_file3".to_string(),
            ];
            let prefix = processor.common_prefix(strings);
            assert_eq!(prefix, "prefix_file");

            // Clear pool
            processor.clear_pool();
            assert_eq!(processor.pool_stats(), 0);
        }

        #[test]
        fn test_string_operations() {
            let processor = StringProcessor::new();

            // Test split lines
            let text = "Line 1\nLine 2\nLine 3".to_string();
            let lines = processor.split_lines(text);
            assert_eq!(lines.len(), 3);

            // Test join lines
            let joined = processor.join_lines(lines, " | ".to_string());
            assert!(joined.contains(" | "));
        }
    }
}
