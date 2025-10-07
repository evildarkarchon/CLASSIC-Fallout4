//! Comprehensive tests for the high-performance report generation module
//!
//! This module tests the report generation components with:
//! - String pool interning and memory efficiency
//! - Report fragment creation and composition
//! - Parallel fragment processing
//! - Report generator functionality
//! - Performance benchmarks
//! - PyO3 bindings and error handling

use classic_scanlog::{StringPool, ReportFragment, ReportComposer, ReportGenerator, ParallelReportProcessor};
use std::time::Instant;

// ===== Unit Tests (Pure Rust) =====

// --- StringPool Tests ---

#[test]
fn test_string_pool_creation() {
    let pool = StringPool::new();
    let (size, lookups, hits, insertions) = pool.get_stats();

    assert_eq!(size, 0);
    assert_eq!(lookups, 0);
    assert_eq!(hits, 0);
    assert_eq!(insertions, 0);
}

#[test]
fn test_string_pool_intern_single() {
    let pool = StringPool::new();

    let s1 = pool.intern("test_string");
    assert_eq!(s1, "test_string");

    let (size, lookups, hits, insertions) = pool.get_stats();
    assert_eq!(size, 1);
    assert_eq!(lookups, 1);
    assert_eq!(hits, 0);
    assert_eq!(insertions, 1);
}

#[test]
fn test_string_pool_intern_duplicate() {
    let pool = StringPool::new();

    let s1 = pool.intern("duplicate");
    let s2 = pool.intern("duplicate");

    assert_eq!(s1, s2);

    let (size, lookups, hits, insertions) = pool.get_stats();
    assert_eq!(size, 1); // Only one unique string
    assert_eq!(lookups, 2);
    assert_eq!(hits, 1); // Second lookup was a hit
    assert_eq!(insertions, 1); // Only one insertion
}

#[test]
fn test_string_pool_intern_multiple_unique() {
    let pool = StringPool::new();

    let _s1 = pool.intern("string1");
    let _s2 = pool.intern("string2");
    let _s3 = pool.intern("string3");

    let (size, lookups, hits, insertions) = pool.get_stats();
    assert_eq!(size, 3);
    assert_eq!(lookups, 3);
    assert_eq!(hits, 0);
    assert_eq!(insertions, 3);
}

#[test]
fn test_string_pool_intern_batch() {
    let pool = StringPool::new();

    let strings = vec![
        "batch1".to_string(),
        "batch2".to_string(),
        "batch1".to_string(), // Duplicate
        "batch3".to_string(),
    ];

    let interned = pool.intern_batch(&strings);

    assert_eq!(interned.len(), 4);
    assert_eq!(interned[0], "batch1");
    assert_eq!(interned[1], "batch2");
    assert_eq!(interned[2], "batch1");
    assert_eq!(interned[3], "batch3");

    let (size, _lookups, _hits, _insertions) = pool.get_stats();
    assert_eq!(size, 3); // Only 3 unique strings
}

#[test]
fn test_string_pool_clear() {
    let pool = StringPool::new();

    pool.intern("test1");
    pool.intern("test2");
    pool.intern("test3");

    let (size_before, _, _, _) = pool.get_stats();
    assert_eq!(size_before, 3);

    pool.clear();

    let (size_after, lookups, hits, insertions) = pool.get_stats();
    assert_eq!(size_after, 0);
    assert_eq!(lookups, 0);
    assert_eq!(hits, 0);
    assert_eq!(insertions, 0);
}

#[test]
fn test_string_pool_hit_rate() {
    let pool = StringPool::new();

    // Simulate repeated access pattern
    for _ in 0..100 {
        pool.intern("common_string");
    }

    let (size, lookups, hits, insertions) = pool.get_stats();
    assert_eq!(size, 1);
    assert_eq!(lookups, 100);
    assert_eq!(hits, 99); // First lookup is miss, rest are hits
    assert_eq!(insertions, 1);

    // Calculate hit rate
    let hit_rate = hits as f64 / lookups as f64;
    assert!(hit_rate > 0.95); // Should have >95% hit rate
}

// --- ReportFragment Tests ---

#[test]
fn test_report_fragment_empty() {
    let fragment = ReportFragment::empty();

    assert!(fragment.is_empty());
    assert_eq!(fragment.len(), 0);
    assert_eq!(fragment.to_list().len(), 0);
}

#[test]
fn test_report_fragment_from_lines() {
    let lines = vec![
        "Line 1".to_string(),
        "Line 2".to_string(),
        "Line 3".to_string(),
    ];

    let fragment = ReportFragment::from_lines(lines.clone());

    assert!(!fragment.is_empty());
    assert_eq!(fragment.len(), 3);
    assert_eq!(fragment.to_list(), lines);
}

#[test]
fn test_report_fragment_from_lines_pooled() {
    let pool = StringPool::new();
    let lines = vec![
        "Pooled line 1".to_string(),
        "Pooled line 2".to_string(),
    ];

    let fragment = ReportFragment::from_lines_pooled(lines.clone(), &pool);

    assert!(!fragment.is_empty());
    assert_eq!(fragment.len(), 2);
    assert_eq!(fragment.to_list(), lines);

    // Pool should have been used
    let (size, _, _, _) = pool.get_stats();
    assert_eq!(size, 2);
}

#[test]
fn test_report_fragment_with_header() {
    let fragment = ReportFragment::from_lines(vec![
        "Body line 1".to_string(),
        "Body line 2".to_string(),
    ]);

    let header = vec![
        "Header line 1".to_string(),
        "Header line 2".to_string(),
    ];

    let with_header = fragment.with_header(header.clone());

    assert_eq!(with_header.len(), 4);

    let result = with_header.to_list();
    assert_eq!(result[0], "Header line 1");
    assert_eq!(result[1], "Header line 2");
    assert_eq!(result[2], "Body line 1");
    assert_eq!(result[3], "Body line 2");
}

#[test]
fn test_report_fragment_with_header_empty() {
    let fragment = ReportFragment::empty();
    let header = vec!["Header".to_string()];

    // Adding header to empty fragment should return empty
    let with_header = fragment.with_header(header);
    assert!(with_header.is_empty());
}

#[test]
fn test_report_fragment_combine() {
    let fragment1 = ReportFragment::from_lines(vec![
        "Fragment 1 Line 1".to_string(),
        "Fragment 1 Line 2".to_string(),
    ]);

    let fragment2 = ReportFragment::from_lines(vec![
        "Fragment 2 Line 1".to_string(),
        "Fragment 2 Line 2".to_string(),
    ]);

    let combined = fragment1.combine(&fragment2);

    assert_eq!(combined.len(), 4);

    let result = combined.to_list();
    assert_eq!(result[0], "Fragment 1 Line 1");
    assert_eq!(result[1], "Fragment 1 Line 2");
    assert_eq!(result[2], "Fragment 2 Line 1");
    assert_eq!(result[3], "Fragment 2 Line 2");
}

#[test]
fn test_report_fragment_combine_with_empty() {
    let fragment = ReportFragment::from_lines(vec!["Content".to_string()]);
    let empty = ReportFragment::empty();

    let result1 = fragment.combine(&empty);
    assert_eq!(result1.len(), 1);

    let result2 = empty.combine(&fragment);
    assert_eq!(result2.len(), 1);
}

#[test]
fn test_report_fragment_combine_both_empty() {
    let empty1 = ReportFragment::empty();
    let empty2 = ReportFragment::empty();

    let combined = empty1.combine(&empty2);
    assert!(combined.is_empty());
}

// --- ReportComposer Tests ---

#[test]
fn test_report_composer_creation() {
    let composer = ReportComposer::new();
    // Composer should start empty - test by composing
    let result = composer.compose();
    assert!(result.is_empty());
}

#[test]
fn test_report_composer_add_single() {
    let mut composer = ReportComposer::new();
    let fragment = ReportFragment::from_lines(vec!["Test line".to_string()]);

    composer.add(fragment);

    // Verify by composing
    let result = composer.compose();
    assert_eq!(result.len(), 1);
    assert_eq!(result.to_list()[0], "Test line");
}

#[test]
fn test_report_composer_add_many() {
    let mut composer = ReportComposer::new();

    let fragments = vec![
        ReportFragment::from_lines(vec!["Fragment 1".to_string()]),
        ReportFragment::from_lines(vec!["Fragment 2".to_string()]),
        ReportFragment::from_lines(vec!["Fragment 3".to_string()]),
    ];

    composer.add_many(fragments);

    // Verify by composing
    let result = composer.compose();
    assert_eq!(result.len(), 3);
}

#[test]
fn test_report_composer_compose_empty() {
    let composer = ReportComposer::new();
    let result = composer.compose();

    assert!(result.is_empty());
}

#[test]
fn test_report_composer_compose_single() {
    let mut composer = ReportComposer::new();
    composer.add(ReportFragment::from_lines(vec!["Single fragment".to_string()]));

    let result = composer.compose();
    assert_eq!(result.len(), 1);
    assert_eq!(result.to_list()[0], "Single fragment");
}

#[test]
fn test_report_composer_compose_sequential() {
    let mut composer = ReportComposer::new();

    // Add fewer than parallel_threshold (default 10) to trigger sequential
    for i in 0..5 {
        composer.add(ReportFragment::from_lines(vec![format!("Line {}", i)]));
    }

    let result = composer.compose();
    assert_eq!(result.len(), 5);

    let lines = result.to_list();
    assert_eq!(lines[0], "Line 0");
    assert_eq!(lines[4], "Line 4");
}

#[test]
fn test_report_composer_compose_parallel() {
    let mut composer = ReportComposer::new();

    // Add more than parallel_threshold to trigger parallel composition
    for i in 0..20 {
        composer.add(ReportFragment::from_lines(vec![format!("Line {}", i)]));
    }

    let result = composer.compose();
    assert_eq!(result.len(), 20);

    let lines = result.to_list();
    assert_eq!(lines[0], "Line 0");
    assert_eq!(lines[19], "Line 19");
}

#[test]
fn test_report_composer_compose_optimized() {
    let mut composer = ReportComposer::new();

    for i in 0..15 {
        composer.add(ReportFragment::from_lines(vec![format!("Line {}", i)]));
    }

    let result = composer.compose_optimized();
    assert_eq!(result.len(), 15);
}

#[test]
fn test_report_composer_build_string() {
    let mut composer = ReportComposer::new();

    composer.add(ReportFragment::from_lines(vec![
        "Line 1".to_string(),
        "Line 2".to_string(),
        "Line 3".to_string(),
    ]));

    let result = composer.build_string();

    assert!(result.contains("Line 1"));
    assert!(result.contains("Line 2"));
    assert!(result.contains("Line 3"));

    // Should have newlines
    assert!(result.contains('\n'));
}

#[test]
fn test_report_composer_build_string_with_newlines() {
    let mut composer = ReportComposer::new();

    composer.add(ReportFragment::from_lines(vec![
        "Line with newline\n".to_string(),
        "Line without newline".to_string(),
    ]));

    let result = composer.build_string();

    // Should not add double newlines
    assert!(!result.contains("\n\n\n"));
}

#[test]
fn test_report_composer_build_string_empty() {
    let composer = ReportComposer::new();
    let result = composer.build_string();

    assert!(result.is_empty() || result == "\n");
}

// --- ReportGenerator Tests ---

#[test]
fn test_report_generator_creation() {
    let _generator = ReportGenerator::new();
    // Just ensure it can be created
    assert!(true);
}

#[test]
fn test_report_generator_header() {
    let generator = ReportGenerator::new();

    let header = generator.generate_header("test_crash.log", "CLASSIC v1.0.0");

    assert!(!header.is_empty());

    let lines = header.to_list();

    // Should contain filename
    let has_filename = lines.iter().any(|line| line.contains("test_crash.log"));
    assert!(has_filename);

    // Should contain version
    let has_version = lines.iter().any(|line| line.contains("CLASSIC v1.0.0"));
    assert!(has_version);

    // Should contain viewing instructions
    let has_instructions = lines.iter().any(|line| line.contains("NOTEPAD++"));
    assert!(has_instructions);
}

#[test]
fn test_report_generator_error_section_latest() {
    let generator = ReportGenerator::new();

    let section = generator.generate_error_section(
        "Access Violation",
        "1.28.6",
        "Buffout 4",
        true,
        "You should update!",
    );

    assert!(!section.is_empty());

    let lines = section.to_list();

    // Should contain error
    let has_error = lines.iter().any(|line| line.contains("Access Violation"));
    assert!(has_error);

    // Should contain version
    let has_version = lines.iter().any(|line| line.contains("1.28.6"));
    assert!(has_version);

    // Should show latest version message
    let has_latest = lines.iter().any(|line| line.contains("latest version"));
    assert!(has_latest);

    // Should NOT show outdated warning
    let has_outdated = lines.iter().any(|line| line.contains("You should update!"));
    assert!(!has_outdated);
}

#[test]
fn test_report_generator_error_section_outdated() {
    let generator = ReportGenerator::new();

    let section = generator.generate_error_section(
        "Access Violation",
        "1.28.5",
        "Buffout 4",
        false,
        "You should update to 1.28.6!",
    );

    assert!(!section.is_empty());

    let lines = section.to_list();

    // Should show outdated warning
    let has_outdated = lines.iter().any(|line| line.contains("You should update"));
    assert!(has_outdated);

    // Should NOT show latest version message
    let has_latest = lines.iter().any(|line| line.contains("✅") && line.contains("latest"));
    assert!(!has_latest);
}

#[test]
fn test_report_generator_suspect_section_empty() {
    let generator = ReportGenerator::new();

    let section = generator.generate_suspect_section(vec![]);

    assert!(!section.is_empty());

    let lines = section.to_list();

    // Should contain "no suspects" message
    let has_no_suspects = lines.iter().any(|line|
        line.contains("FOUND NO CRASH ERRORS") || line.contains("NO CRASH")
    );
    assert!(has_no_suspects);
}

#[test]
fn test_report_generator_suspect_section_with_suspects() {
    let generator = ReportGenerator::new();

    let suspects = vec![
        "Suspect 1: Known crash pattern".to_string(),
        "Suspect 2: Another issue".to_string(),
    ];

    let section = generator.generate_suspect_section(suspects.clone());

    assert!(!section.is_empty());

    let lines = section.to_list();

    // Should contain suspects
    let has_suspect1 = lines.iter().any(|line| line.contains("Suspect 1"));
    assert!(has_suspect1);

    let has_suspect2 = lines.iter().any(|line| line.contains("Suspect 2"));
    assert!(has_suspect2);

    // Should have documentation link
    let has_docs_link = lines.iter().any(|line| line.contains("docs.google.com"));
    assert!(has_docs_link);
}

// --- ParallelReportProcessor Tests ---

#[test]
fn test_parallel_report_processor_creation() {
    let _processor = ParallelReportProcessor;
    // Just ensure it can be created
    assert!(true);
}

#[test]
fn test_parallel_combine_fragments() {
    // Note: combine_fragments_parallel is private, tested via Python bindings
    // This test ensures ParallelReportProcessor can be created
    let _processor = ParallelReportProcessor;
    assert!(true);
}

// Note: Parallel combine functionality is tested via Python integration tests
// as the combine_fragments_parallel method is private (only exposed to Python)

// ===== Performance Tests =====

#[test]
fn test_string_pool_performance_common_strings() {
    let pool = StringPool::new();

    // Simulate real-world scenario with common report strings
    let common_strings = vec![
        "### Error Information",
        "**Main Error:**",
        "**Detected Version:**",
        "Form ID:",
        "Plugin:",
    ];

    let start = Instant::now();

    // Repeat interning many times
    for _ in 0..10000 {
        for s in &common_strings {
            pool.intern(s);
        }
    }

    let elapsed = start.elapsed();

    println!("Interned {} strings in {:?}", 50000, elapsed);

    let (size, lookups, hits, insertions) = pool.get_stats();
    assert_eq!(size, 5); // Only 5 unique strings
    assert_eq!(lookups, 50000);
    assert_eq!(hits, 50000 - 5); // All but first lookups are hits
    assert_eq!(insertions, 5);

    // Should be very fast due to caching
    assert!(elapsed.as_millis() < 100);
}

#[test]
fn test_batch_intern_performance() {
    let pool = StringPool::new();

    // Create large batch
    let mut strings = Vec::new();
    for i in 0..10000 {
        strings.push(format!("String {}", i % 100)); // 100 unique strings, repeated
    }

    let start = Instant::now();
    let interned = pool.intern_batch(&strings);
    let elapsed = start.elapsed();

    println!("Batch interned {} strings in {:?}", interned.len(), elapsed);

    assert_eq!(interned.len(), 10000);

    let (size, _, _, _) = pool.get_stats();
    assert_eq!(size, 100); // Only 100 unique

    // Should be fast with parallel processing
    assert!(elapsed.as_millis() < 200);
}

#[test]
fn test_parallel_composition_performance() {
    let mut composer = ReportComposer::new();

    // Create many fragments
    for i in 0..1000 {
        let lines = vec![
            format!("Segment {}", i),
            format!("  Line 1 of segment {}", i),
            format!("  Line 2 of segment {}", i),
        ];
        composer.add(ReportFragment::from_lines(lines));
    }

    let start = Instant::now();
    let result = composer.compose();
    let elapsed = start.elapsed();

    println!("Composed {} fragments in {:?}", 1000, elapsed);

    assert_eq!(result.len(), 3000); // 1000 fragments * 3 lines each

    // Should be fast with parallel processing
    assert!(elapsed.as_millis() < 500);
}

#[test]
fn test_build_string_performance() {
    let mut composer = ReportComposer::new();

    // Create realistic report size
    for i in 0..500 {
        let lines = vec![
            format!("## Section {}", i),
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.".to_string(),
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.".to_string(),
            "".to_string(),
        ];
        composer.add(ReportFragment::from_lines(lines));
    }

    let start = Instant::now();
    let result = composer.build_string();
    let elapsed = start.elapsed();

    println!("Built string of {} bytes in {:?}", result.len(), elapsed);

    assert!(result.len() > 50000); // Should be a substantial report

    // Should be fast with pre-allocated capacity
    assert!(elapsed.as_millis() < 100);
}

// ===== Edge Cases =====

#[test]
fn test_fragment_with_unicode() {
    let fragment = ReportFragment::from_lines(vec![
        "Unicode test: ✅ 🚀 ⚠️".to_string(),
        "Chinese: 中文测试".to_string(),
        "Japanese: 日本語テスト".to_string(),
    ]);

    assert_eq!(fragment.len(), 3);

    let lines = fragment.to_list();
    assert!(lines[0].contains("✅"));
    assert!(lines[1].contains("中文"));
    assert!(lines[2].contains("日本語"));
}

#[test]
fn test_fragment_with_very_long_lines() {
    let long_line = "A".repeat(10000);
    let fragment = ReportFragment::from_lines(vec![long_line.clone()]);

    assert_eq!(fragment.len(), 1);
    assert_eq!(fragment.to_list()[0].len(), 10000);
}

#[test]
fn test_fragment_with_empty_lines() {
    let fragment = ReportFragment::from_lines(vec![
        "Line 1".to_string(),
        "".to_string(),
        "".to_string(),
        "Line 4".to_string(),
    ]);

    assert_eq!(fragment.len(), 4);
    assert_eq!(fragment.to_list()[1], "");
    assert_eq!(fragment.to_list()[2], "");
}

#[test]
fn test_composer_with_mixed_empty_fragments() {
    let mut composer = ReportComposer::new();

    composer.add(ReportFragment::from_lines(vec!["Content 1".to_string()]));
    composer.add(ReportFragment::empty());
    composer.add(ReportFragment::from_lines(vec!["Content 2".to_string()]));
    composer.add(ReportFragment::empty());

    let result = composer.compose();

    // Empty fragments should still contribute to the composition
    let lines = result.to_list();
    assert!(lines.contains(&"Content 1".to_string()));
    assert!(lines.contains(&"Content 2".to_string()));
}

#[test]
fn test_string_pool_with_empty_strings() {
    let pool = StringPool::new();

    let s1 = pool.intern("");
    let s2 = pool.intern("");

    assert_eq!(s1, "");
    assert_eq!(s2, "");

    let (size, lookups, hits, insertions) = pool.get_stats();
    assert_eq!(size, 1); // Empty string should be pooled
    assert_eq!(lookups, 2);
    assert_eq!(hits, 1);
    assert_eq!(insertions, 1);
}

#[test]
fn test_report_generator_with_special_characters() {
    let generator = ReportGenerator::new();

    let header = generator.generate_header(
        "crash<test>.log",
        "CLASSIC v1.0.0 & \"special\""
    );

    let lines = header.to_list();
    let combined = lines.join("");

    assert!(combined.contains("crash<test>.log"));
    assert!(combined.contains("CLASSIC v1.0.0 & \"special\""));
}

// ===== Integration Tests with PyO3 =====

#[cfg(test)]
mod integration_tests {
    use super::*;
    use pyo3::prelude::*;
    use pyo3::types::PyList;

    fn with_string_pool<F>(test_fn: F)
    where
        F: FnOnce(Python, Bound<PyAny>),
    {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let pool = Py::new(py, StringPool::new()).unwrap();
            let pool_any = pool.bind(py).as_any().clone();
            test_fn(py, pool_any);
        });
    }

    fn with_report_composer<F>(test_fn: F)
    where
        F: FnOnce(Python, Bound<PyAny>),
    {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let composer = Py::new(py, ReportComposer::new()).unwrap();
            let composer_any = composer.bind(py).as_any().clone();
            test_fn(py, composer_any);
        });
    }

    fn with_report_generator<F>(test_fn: F)
    where
        F: FnOnce(Python, Bound<PyAny>),
    {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let generator = Py::new(py, ReportGenerator::new()).unwrap();
            let generator_any = generator.bind(py).as_any().clone();
            test_fn(py, generator_any);
        });
    }

    fn with_parallel_processor<F>(test_fn: F)
    where
        F: FnOnce(Python, Bound<PyAny>),
    {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let processor = Py::new(py, ParallelReportProcessor).unwrap();
            let processor_any = processor.bind(py).as_any().clone();
            test_fn(py, processor_any);
        });
    }

    // --- StringPool Python Tests ---

    #[test]
    fn test_python_string_pool_intern() {
        with_string_pool(|_py, pool| {
            let s1 = pool.call_method1("intern", ("test_string",)).unwrap();
            let s1_str = s1.extract::<String>().unwrap();
            assert_eq!(s1_str, "test_string");

            let s2 = pool.call_method1("intern", ("test_string",)).unwrap();
            let s2_str = s2.extract::<String>().unwrap();
            assert_eq!(s2_str, "test_string");

            // Check stats
            let stats = pool.call_method0("stats").unwrap();
            let (size, lookups, hits, insertions) = stats.extract::<(usize, usize, usize, usize)>().unwrap();
            assert_eq!(size, 1);
            assert_eq!(lookups, 2);
            assert_eq!(hits, 1);
            assert_eq!(insertions, 1);
        });
    }

    #[test]
    fn test_python_string_pool_intern_batch() {
        with_string_pool(|py, pool| {
            let strings = PyList::new(
                py,
                &["str1", "str2", "str1", "str3"]
            ).unwrap();

            let result = pool.call_method1("intern_batch", (strings,)).unwrap();
            let result_list = result.downcast::<PyList>().unwrap();

            assert_eq!(result_list.len(), 4);

            let stats = pool.call_method0("stats").unwrap();
            let (size, _, _, _) = stats.extract::<(usize, usize, usize, usize)>().unwrap();
            assert_eq!(size, 3); // Only 3 unique
        });
    }

    #[test]
    fn test_python_string_pool_clear() {
        with_string_pool(|_py, pool| {
            pool.call_method1("intern", ("test",)).unwrap();
            pool.call_method1("intern", ("test2",)).unwrap();

            let stats_before = pool.call_method0("stats").unwrap();
            let (size_before, _, _, _) = stats_before.extract::<(usize, usize, usize, usize)>().unwrap();
            assert_eq!(size_before, 2);

            pool.call_method0("clear").unwrap();

            let stats_after = pool.call_method0("stats").unwrap();
            let (size_after, lookups, hits, insertions) = stats_after.extract::<(usize, usize, usize, usize)>().unwrap();
            assert_eq!(size_after, 0);
            assert_eq!(lookups, 0);
            assert_eq!(hits, 0);
            assert_eq!(insertions, 0);
        });
    }

    // --- ReportFragment Python Tests ---

    #[test]
    fn test_python_report_fragment_creation() {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let fragment = Py::new(
                py,
                ReportFragment::from_lines(vec!["Line 1".to_string(), "Line 2".to_string()])
            ).unwrap();

            let len = fragment.bind(py).call_method0("__len__").unwrap();
            assert_eq!(len.extract::<usize>().unwrap(), 2);
        });
    }

    #[test]
    fn test_python_report_fragment_empty() {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let empty_class = Py::new(py, ReportFragment::empty()).unwrap();
            let empty = empty_class.bind(py);

            let is_empty = empty.call_method0("__len__").unwrap();
            assert_eq!(is_empty.extract::<usize>().unwrap(), 0);

            let has_content = empty.getattr("has_content").unwrap();
            assert_eq!(has_content.extract::<bool>().unwrap(), false);
        });
    }

    #[test]
    fn test_python_report_fragment_combine() {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let fragment1 = Py::new(
                py,
                ReportFragment::from_lines(vec!["Line 1".to_string()])
            ).unwrap();

            let fragment2 = Py::new(
                py,
                ReportFragment::from_lines(vec!["Line 2".to_string()])
            ).unwrap();

            let combined = fragment1.bind(py).call_method1("__add__", (fragment2.bind(py),)).unwrap();

            let len = combined.call_method0("__len__").unwrap();
            assert_eq!(len.extract::<usize>().unwrap(), 2);
        });
    }

    #[test]
    fn test_python_report_fragment_to_list() {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let fragment = Py::new(
                py,
                ReportFragment::from_lines(vec!["Test line".to_string()])
            ).unwrap();

            let list = fragment.bind(py).call_method0("to_list").unwrap();
            let list_py = list.downcast::<PyList>().unwrap();

            assert_eq!(list_py.len(), 1);
            assert_eq!(list_py.get_item(0).unwrap().extract::<String>().unwrap(), "Test line");
        });
    }

    // --- ReportComposer Python Tests ---

    #[test]
    fn test_python_report_composer_creation() {
        with_report_composer(|_py, _composer| {
            // If we got here, creation succeeded
            assert!(true);
        });
    }

    #[test]
    fn test_python_report_composer_add() {
        with_report_composer(|py, composer| {
            let fragment = Py::new(
                py,
                ReportFragment::from_lines(vec!["Test".to_string()])
            ).unwrap();

            composer.call_method1("add", (fragment.bind(py),)).unwrap();

            let len = composer.call_method0("__len__").unwrap();
            assert_eq!(len.extract::<usize>().unwrap(), 1);
        });
    }

    #[test]
    fn test_python_report_composer_compose() {
        with_report_composer(|py, composer| {
            for i in 0..5 {
                let fragment = Py::new(
                    py,
                    ReportFragment::from_lines(vec![format!("Line {}", i)])
                ).unwrap();
                composer.call_method1("add", (fragment.bind(py),)).unwrap();
            }

            let result = composer.call_method0("compose").unwrap();
            let result_fragment = result.extract::<ReportFragment>().unwrap();

            assert_eq!(result_fragment.len(), 5);
        });
    }

    #[test]
    fn test_python_report_composer_build_string() {
        with_report_composer(|py, composer| {
            let fragment = Py::new(
                py,
                ReportFragment::from_lines(vec![
                    "Line 1".to_string(),
                    "Line 2".to_string(),
                ])
            ).unwrap();

            composer.call_method1("add", (fragment.bind(py),)).unwrap();

            let result = composer.call_method0("build_string").unwrap();
            let result_str = result.extract::<String>().unwrap();

            assert!(result_str.contains("Line 1"));
            assert!(result_str.contains("Line 2"));
        });
    }

    #[test]
    fn test_python_report_composer_pool_stats() {
        with_report_composer(|_py, composer| {
            let stats = composer.getattr("pool_stats").unwrap();
            let (_size, _lookups, _hits, _insertions) = stats.extract::<(usize, usize, usize, usize)>().unwrap();

            // Stats should be accessible (usize is always >= 0, just verify it extracts)
            assert!(true);
        });
    }

    // --- ReportGenerator Python Tests ---

    #[test]
    fn test_python_report_generator_header() {
        with_report_generator(|_py, generator| {
            let header = generator.call_method1(
                "generate_header",
                ("test.log", "CLASSIC v1.0")
            ).unwrap();

            let header_fragment = header.extract::<ReportFragment>().unwrap();
            assert!(!header_fragment.is_empty());

            let lines = header_fragment.to_list();
            let combined = lines.join("");
            assert!(combined.contains("test.log"));
            assert!(combined.contains("CLASSIC v1.0"));
        });
    }

    #[test]
    fn test_python_report_generator_error_section() {
        with_report_generator(|_py, generator| {
            let section = generator.call_method1(
                "generate_error_section",
                (
                    "Access Violation",
                    "1.28.6",
                    "Buffout 4",
                    true,
                    "Update warning"
                )
            ).unwrap();

            let section_fragment = section.extract::<ReportFragment>().unwrap();
            assert!(!section_fragment.is_empty());

            let lines = section_fragment.to_list();
            let combined = lines.join("");
            assert!(combined.contains("Access Violation"));
            assert!(combined.contains("1.28.6"));
        });
    }

    #[test]
    fn test_python_report_generator_suspect_section_empty() {
        with_report_generator(|py, generator| {
            let empty_list = PyList::empty(py);

            let section = generator.call_method1(
                "generate_suspect_section",
                (empty_list,)
            ).unwrap();

            let section_fragment = section.extract::<ReportFragment>().unwrap();
            assert!(!section_fragment.is_empty());

            let lines = section_fragment.to_list();
            let combined = lines.join("");
            assert!(combined.contains("FOUND NO CRASH"));
        });
    }

    #[test]
    fn test_python_report_generator_suspect_section_with_suspects() {
        with_report_generator(|py, generator| {
            let suspects = PyList::new(
                py,
                &["Suspect 1", "Suspect 2"]
            ).unwrap();

            let section = generator.call_method1(
                "generate_suspect_section",
                (suspects,)
            ).unwrap();

            let section_fragment = section.extract::<ReportFragment>().unwrap();
            let lines = section_fragment.to_list();
            let combined = lines.join("");

            assert!(combined.contains("Suspect 1"));
            assert!(combined.contains("Suspect 2"));
            assert!(combined.contains("docs.google.com"));
        });
    }

    // --- ParallelReportProcessor Python Tests ---

    #[test]
    fn test_python_parallel_processor_combine_fragments() {
        with_parallel_processor(|py, processor| {
            let fragments = PyList::new(py, &[
                Py::new(py, ReportFragment::from_lines(vec!["Frag 1".to_string()])).unwrap(),
                Py::new(py, ReportFragment::from_lines(vec!["Frag 2".to_string()])).unwrap(),
                Py::new(py, ReportFragment::from_lines(vec!["Frag 3".to_string()])).unwrap(),
            ]).unwrap();

            let result = processor.call_method1(
                "combine_fragments_parallel",
                (fragments,)
            ).unwrap();

            let result_fragment = result.extract::<ReportFragment>().unwrap();
            assert_eq!(result_fragment.len(), 3);
        });
    }

    #[test]
    fn test_python_parallel_processor_transform_uppercase() {
        with_parallel_processor(|py, processor| {
            let fragments = PyList::new(py, &[
                Py::new(py, ReportFragment::from_lines(vec!["lowercase text".to_string()])).unwrap(),
            ]).unwrap();

            let result = processor.call_method1(
                "transform_fragments",
                (fragments, "uppercase")
            ).unwrap();

            let result_list = result.downcast::<PyList>().unwrap();
            let first_fragment = result_list.get_item(0).unwrap().extract::<ReportFragment>().unwrap();

            let lines = first_fragment.to_list();
            assert_eq!(lines[0], "LOWERCASE TEXT");
        });
    }

    #[test]
    fn test_python_parallel_processor_transform_trim() {
        with_parallel_processor(|py, processor| {
            let fragments = PyList::new(py, &[
                Py::new(py, ReportFragment::from_lines(vec!["  text with spaces  ".to_string()])).unwrap(),
            ]).unwrap();

            let result = processor.call_method1(
                "transform_fragments",
                (fragments, "trim")
            ).unwrap();

            let result_list = result.downcast::<PyList>().unwrap();
            let first_fragment = result_list.get_item(0).unwrap().extract::<ReportFragment>().unwrap();

            let lines = first_fragment.to_list();
            assert_eq!(lines[0], "text with spaces");
        });
    }

    #[test]
    fn test_python_parallel_processor_process_reports() {
        with_parallel_processor(|py, processor| {
            let reports = PyList::new(py, &[
                PyList::new(py, &["Report 1 Line 1", "Report 1 Line 2"]).unwrap(),
                PyList::new(py, &["Report 2 Line 1", "Report 2 Line 2"]).unwrap(),
            ]).unwrap();

            let result = processor.call_method1("process_reports", (reports,)).unwrap();
            let result_list = result.downcast::<PyList>().unwrap();

            assert_eq!(result_list.len(), 2);

            let report1 = result_list.get_item(0).unwrap().extract::<String>().unwrap();
            let report2 = result_list.get_item(1).unwrap().extract::<String>().unwrap();

            assert!(report1.contains("Report 1 Line 1"));
            assert!(report2.contains("Report 2 Line 1"));
        });
    }

    // --- Full Integration Test ---

    #[test]
    fn test_full_report_generation_workflow() {
        pyo3::Python::initialize();
        Python::attach(|py| {
            // Create generator
            let generator = Py::new(py, ReportGenerator::new()).unwrap();

            // Generate header
            let header = generator.bind(py).call_method1(
                "generate_header",
                ("crash_2024_01_15.log", "CLASSIC v2.0.0")
            ).unwrap();

            // Generate error section
            let error_section = generator.bind(py).call_method1(
                "generate_error_section",
                (
                    "EXCEPTION_ACCESS_VIOLATION",
                    "1.28.6",
                    "Buffout 4",
                    true,
                    ""
                )
            ).unwrap();

            // Generate suspect section
            let suspects = PyList::new(py, &[
                "Detected: Null Pointer Dereference",
                "Detected: Memory Corruption",
            ]).unwrap();
            let suspect_section = generator.bind(py).call_method1(
                "generate_suspect_section",
                (suspects,)
            ).unwrap();

            // Compose into final report
            let composer = Py::new(py, ReportComposer::new()).unwrap();

            composer.bind(py).call_method1("add", (header,)).unwrap();
            composer.bind(py).call_method1("add", (error_section,)).unwrap();
            composer.bind(py).call_method1("add", (suspect_section,)).unwrap();

            // Build final string
            let final_report = composer.bind(py).call_method0("build_string").unwrap();
            let report_str = final_report.extract::<String>().unwrap();

            // Verify complete report
            assert!(report_str.contains("crash_2024_01_15.log"));
            assert!(report_str.contains("CLASSIC v2.0.0"));
            assert!(report_str.contains("EXCEPTION_ACCESS_VIOLATION"));
            assert!(report_str.contains("Null Pointer Dereference"));
            assert!(report_str.len() > 500); // Should be a substantial report
        });
    }
}

// ===== Benchmark Tests (Ignored by default) =====

#[cfg(test)]
mod benchmarks {
    use super::*;

    #[test]
    #[ignore]
    fn bench_string_pool_large_scale() {
        let pool = StringPool::new();

        // Simulate 1 million interning operations
        let start = Instant::now();
        for i in 0..1_000_000 {
            pool.intern(&format!("String {}", i % 1000)); // 1000 unique strings
        }
        let elapsed = start.elapsed();

        println!("String pool 1M operations: {:?}", elapsed);
        println!("Average: {:?} per operation", elapsed / 1_000_000);

        let (_size, lookups, hits, _) = pool.get_stats();
        println!("Hit rate: {:.2}%", (hits as f64 / lookups as f64) * 100.0);
    }

    #[test]
    #[ignore]
    fn bench_fragment_composition_large_report() {
        let mut composer = ReportComposer::new();

        // Create a very large report (10,000 fragments)
        for i in 0..10_000 {
            let lines = vec![
                format!("## Section {}", i),
                "Lorem ipsum dolor sit amet".to_string(),
                "Consectetur adipiscing elit".to_string(),
                "Sed do eiusmod tempor".to_string(),
            ];
            composer.add(ReportFragment::from_lines(lines));
        }

        let start = Instant::now();
        let result = composer.compose();
        let elapsed = start.elapsed();

        println!("Composed {} fragments ({} lines) in {:?}",
                 10_000, result.len(), elapsed);
        println!("Average: {:?} per fragment", elapsed / 10_000);
    }

    #[test]
    #[ignore]
    fn bench_parallel_vs_sequential_composition() {
        // Note: Can't directly control parallel_threshold as it's private
        // This benchmark shows the general composition performance
        let mut composer = ReportComposer::new();

        // Add fragments - automatic parallel processing for 10+
        for i in 0..100 {
            let lines = vec![format!("Line {}", i); 10];
            composer.add(ReportFragment::from_lines(lines));
        }

        // Benchmark composition
        let start = Instant::now();
        let _result = composer.compose();
        let elapsed = start.elapsed();

        println!("Composed 100 fragments (1000 lines) in: {:?}", elapsed);
        println!("Average per fragment: {:?}", elapsed / 100);
    }

    #[test]
    #[ignore]
    fn bench_report_generation_full_workflow() {
        let generator = ReportGenerator::new();

        let start = Instant::now();

        for i in 0..1000 {
            let _header = generator.generate_header(
                &format!("crash_{}.log", i),
                "CLASSIC v2.0.0"
            );

            let _error = generator.generate_error_section(
                "ACCESS_VIOLATION",
                "1.28.6",
                "Buffout 4",
                true,
                ""
            );

            let suspects = vec![
                "Suspect 1".to_string(),
                "Suspect 2".to_string(),
                "Suspect 3".to_string(),
            ];
            let _suspects_section = generator.generate_suspect_section(suspects);
        }

        let elapsed = start.elapsed();

        println!("Generated 1000 reports in {:?}", elapsed);
        println!("Average: {:?} per report", elapsed / 1000);
    }
}
