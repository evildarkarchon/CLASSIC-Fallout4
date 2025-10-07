//! Comprehensive tests for RecordScanner module
//!
//! This module tests the record scanning components with:
//! - Basic record scanning and extraction
//! - Record validation and filtering
//! - Aho-Corasick multi-pattern matching
//! - Batch processing with parallel operations
//! - PyO3 bindings and report generation
//! - Performance benchmarks (40x speedup target)
//! - Edge cases and error handling

use classic_core::scanlog::{RecordScanner, scan_records_batch, contains_record};
use std::time::Instant;

// ===== Unit Tests (Pure Rust) =====

#[test]
fn test_contains_record_basic() {
    let target_records = vec!["BSResource".to_string(), "Archive".to_string()];
    let ignore_records = vec!["void*".to_string()];

    // Should match - contains target and no ignored terms
    assert!(contains_record(
        "0x7FF6F1E52E60    (BSResource::Archive2**)",
        target_records.clone(),
        ignore_records.clone()
    ));

    // Should not match - contains ignored term
    assert!(!contains_record(
        "0x7FF6EF4B2DC8    (void* -> Fallout4.exe+0712DC8)",
        target_records.clone(),
        ignore_records.clone()
    ));

    // Should not match - doesn't contain target
    assert!(!contains_record(
        "0x1AC             (size_t)",
        target_records.clone(),
        ignore_records.clone()
    ));
}

#[test]
fn test_contains_record_case_insensitive() {
    let target_records = vec!["bsresource".to_string()];
    let ignore_records = vec![];

    // Should match regardless of case
    assert!(contains_record(
        "0x123 (BSResource::Archive)",
        target_records.clone(),
        ignore_records.clone()
    ));
    assert!(contains_record(
        "0x123 (bsresource::archive)",
        target_records.clone(),
        ignore_records.clone()
    ));
    assert!(contains_record(
        "0x123 (BSRESOURCE::ARCHIVE)",
        target_records.clone(),
        ignore_records.clone()
    ));
}

#[test]
fn test_contains_record_multiple_targets() {
    let target_records = vec![
        "BSResource".to_string(),
        "TESObjectREFR".to_string(),
        "Actor".to_string(),
    ];
    let ignore_records = vec![];

    // Should match any target
    assert!(contains_record(
        "0x123 (BSResource*)",
        target_records.clone(),
        ignore_records.clone()
    ));
    assert!(contains_record(
        "0x456 (TESObjectREFR*)",
        target_records.clone(),
        ignore_records.clone()
    ));
    assert!(contains_record(
        "0x789 (Actor*)",
        target_records.clone(),
        ignore_records.clone()
    ));
}

#[test]
fn test_contains_record_multiple_ignores() {
    let target_records = vec!["test".to_string()];
    let ignore_records = vec![
        "void*".to_string(),
        "NULL".to_string(),
        "char*".to_string(),
    ];

    // Should not match if any ignore term is present
    assert!(!contains_record(
        "test (void*)",
        target_records.clone(),
        ignore_records.clone()
    ));
    assert!(!contains_record(
        "test (NULL)",
        target_records.clone(),
        ignore_records.clone()
    ));
    assert!(!contains_record(
        "test (char*) \"string\"",
        target_records.clone(),
        ignore_records.clone()
    ));

    // Should match if no ignore terms present
    assert!(contains_record(
        "test (int)",
        target_records.clone(),
        ignore_records.clone()
    ));
}

#[test]
fn test_contains_record_empty_lists() {
    // Empty targets - should never match
    assert!(!contains_record(
        "0x123 (BSResource*)",
        vec![],
        vec![]
    ));

    // Empty ignores - should match if target present
    let targets = vec!["BSResource".to_string()];
    assert!(contains_record(
        "0x123 (BSResource*)",
        targets,
        vec![]
    ));
}

#[test]
fn test_scan_records_batch_single_segment() {
    // Note: RSP format is "[RSP+NN ] 0xADDRESS      " which is 30 chars total
    let segments = vec![vec![
        "[RSP+8  ] 0x80ECFDFA90      (void*)".to_string(),
        "[RSP+10 ] 0x1AC             (size_t)".to_string(),
        "[RSP+18 ] 0x22FCA037A78     (char*) \"WCLINS_PRP_Patch - Main.ba2\"".to_string(),
        "[RSP+40 ] 0x7FF6F1E52E60      (BSResource::Archive2**)".to_string(),
        "[RSP+48 ] 0x2302DDAB040       (BSGeometrySegmentData*)".to_string(),
    ]];

    let target_records = vec!["BSResource".to_string(), "BSGeometrySegmentData".to_string()];
    let ignore_records = vec!["void*".to_string(), "char*".to_string()];

    let results = scan_records_batch(segments, target_records, ignore_records);

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].len(), 2);

    // Check extracted records (after RSP offset of 30 chars)
    assert!(results[0][0].contains("BSResource::Archive2**"));
    assert!(results[0][1].contains("BSGeometrySegmentData*"));
}

#[test]
fn test_scan_records_batch_multiple_segments() {
    let segments = vec![
        vec![
            "[RSP+8  ] 0x123             (BSResource*)".to_string(),
            "[RSP+10 ] 0x456             (void*)".to_string(),
        ],
        vec![
            "[RSP+8  ] 0x789             (TESObjectREFR*)".to_string(),
        ],
        vec![
            "No records here".to_string(),
        ],
    ];

    let target_records = vec!["BSResource".to_string(), "TESObjectREFR".to_string()];
    let ignore_records = vec!["void*".to_string()];

    let results = scan_records_batch(segments, target_records, ignore_records);

    assert_eq!(results.len(), 3);
    assert_eq!(results[0].len(), 1); // Only BSResource (void* ignored)
    assert_eq!(results[1].len(), 1); // TESObjectREFR
    assert_eq!(results[2].len(), 0); // No matches
}

#[test]
fn test_scan_records_batch_rsp_extraction() {
    // Test RSP marker detection and offset extraction
    // RSP format: "[RSP+NN ] 0xADDRESS      " = 30 chars
    let segments = vec![vec![
        "[RSP+8  ] 0x123               (BSResource::Archive*)".to_string(),
        "Non-RSP line with BSResource::Archive*".to_string(),
    ]];

    let target_records = vec!["BSResource".to_string()];
    let ignore_records = vec![];

    let results = scan_records_batch(segments, target_records, ignore_records);

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].len(), 2);

    // First should be extracted after offset (30 chars)
    // Second should be the full line (trimmed)
    assert_eq!(results[0][0], "(BSResource::Archive*)");
    assert_eq!(results[0][1], "Non-RSP line with BSResource::Archive*");
}

#[test]
fn test_scan_records_batch_empty() {
    // Empty segments
    let results = scan_records_batch(vec![], vec!["test".to_string()], vec![]);
    assert_eq!(results.len(), 0);

    // Segments with no matches
    let segments = vec![vec!["no match".to_string()]];
    let results = scan_records_batch(segments, vec!["target".to_string()], vec![]);
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].len(), 0);
}

#[test]
fn test_scan_records_batch_short_rsp_line() {
    // Line with RSP marker but shorter than offset
    let segments = vec![vec![
        "[RSP+8  ] short".to_string(),  // Only 15 chars, offset is 30
        "[RSP+10 ] 0x123456789ABCDEF0123456789 (BSResource*)".to_string(), // Long enough
    ]];

    let target_records = vec!["BSResource".to_string(), "short".to_string()];
    let ignore_records = vec![];

    let results = scan_records_batch(segments, target_records, ignore_records);

    assert_eq!(results.len(), 1);
    // Short line should be skipped (len <= offset check)
    // Long line should be extracted
    assert_eq!(results[0].len(), 1);
}

// ===== Performance Tests =====

#[test]
fn test_batch_scanning_performance() {
    // Create realistic crash log segments
    let mut segments = Vec::new();
    for i in 0..1000 {
        let segment = vec![
            format!("[RSP+{}  ] 0x{:016X}      (void*)", i % 100, i * 123456),
            format!("[RSP+{}  ] 0x{:016X}      (BSResource::Archive2**)", (i % 100) + 8, i * 654321),
            format!("[RSP+{}  ] 0x{:016X}      (size_t)", (i % 100) + 16, i),
            format!("[RSP+{}  ] 0x{:016X}      (TESObjectREFR*)", (i % 100) + 24, i * 111111),
            format!("[RSP+{}  ] 0x{:016X}      (char*) \"test.ba2\"", (i % 100) + 32, i * 222222),
        ];
        segments.push(segment);
    }

    let target_records = vec![
        "BSResource".to_string(),
        "TESObjectREFR".to_string(),
        "Actor".to_string(),
    ];
    let ignore_records = vec!["void*".to_string(), "char*".to_string()];

    let start = Instant::now();
    let results = scan_records_batch(segments, target_records, ignore_records);
    let elapsed = start.elapsed();

    println!("Scanned 1000 segments in {:?}", elapsed);

    assert_eq!(results.len(), 1000);
    // Each segment should find 2 matches (BSResource and TESObjectREFR)
    assert!(results.iter().all(|r| r.len() == 2));

    // Should be fast (< 50ms for 1000 segments)
    assert!(elapsed.as_millis() < 50, "Expected < 50ms, got {:?}", elapsed);
}

#[test]
fn test_aho_corasick_efficiency() {
    // Test that Aho-Corasick provides efficient multi-pattern matching
    let mut segments = Vec::new();
    for i in 0..100 {
        let mut segment = Vec::new();
        for j in 0..100 {
            segment.push(format!("Line {} with pattern{}", j, i % 10));
        }
        segments.push(segment);
    }

    // Many target patterns (Aho-Corasick should be efficient)
    let target_records: Vec<String> = (0..20)
        .map(|i| format!("pattern{}", i))
        .collect();
    let ignore_records = vec![];

    let start = Instant::now();
    let _results = scan_records_batch(segments, target_records, ignore_records);
    let elapsed = start.elapsed();

    println!("Scanned 10000 lines with 20 patterns in {:?}", elapsed);

    // Aho-Corasick should make this very fast
    assert!(elapsed.as_millis() < 100, "Expected < 100ms, got {:?}", elapsed);
}

// ===== Integration Tests with PyO3 =====

#[cfg(test)]
mod integration_tests {
    use super::*;
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyList};

    fn create_mock_yamldata(py: Python) -> PyResult<Py<PyAny>> {
        let types_module = py.import("types")?;
        let simple_namespace = types_module.getattr("SimpleNamespace")?;

        let kwargs = PyDict::new(py);

        // Create lists for classic_records_list and game_ignore_records
        let records_list = PyList::new(
            py,
            &[
                "BSResource",
                "TESObjectREFR",
                "Actor",
                "BSGeometrySegmentData",
                "TESForm",
            ]
        )?;

        let ignore_list = PyList::new(
            py,
            &[
                "void*",
                "char*",
                "NULL",
                "size_t",
            ]
        )?;

        kwargs.set_item("classic_records_list", records_list)?;
        kwargs.set_item("game_ignore_records", ignore_list)?;
        kwargs.set_item("crashgen_name", "Buffout 4")?;

        let namespace = simple_namespace.call((), Some(&kwargs))?;
        Ok(namespace.into())
    }

    fn with_record_scanner<F>(test_fn: F)
    where
        F: FnOnce(Python, Bound<PyAny>),
    {
        pyo3::Python::initialize();
        Python::attach(|py| {
            let yamldata = create_mock_yamldata(py).unwrap();
            let scanner = Py::new(
                py,
                RecordScanner::new(yamldata.bind(py)).unwrap()
            ).unwrap();
            let scanner_any = scanner.bind(py).as_any().clone();
            test_fn(py, scanner_any);
        });
    }

    #[test]
    fn test_record_scanner_creation() {
        with_record_scanner(|_py, _scanner| {
            // If we got here, creation succeeded
            assert!(true);
        });
    }

    #[test]
    fn test_extract_records_basic() {
        with_record_scanner(|_py, scanner| {
            // Ensure proper 30-char offset: "[RSP+NN ] 0xADDRESS      "
            let callstack = vec![
                "[RSP+8  ] 0x80ECFDFA90      (void*)".to_string(),
                "[RSP+10 ] 0x1AC             (size_t)".to_string(),
                "[RSP+40 ] 0x7FF6F1E52E60      (BSResource::Archive2**)".to_string(),
                "[RSP+48 ] 0x2302DDAB040       (BSGeometrySegmentData*)".to_string(),
            ];

            let result = scanner.call_method1("extract_records", (callstack,)).unwrap();
            let records = result.extract::<Vec<String>>().unwrap();

            assert_eq!(records.len(), 2);
            assert!(records[0].contains("BSResource"));
            assert!(records[1].contains("BSGeometrySegmentData"));
        });
    }

    #[test]
    fn test_extract_records_empty_callstack() {
        with_record_scanner(|_py, scanner| {
            let callstack: Vec<String> = vec![];

            let result = scanner.call_method1("extract_records", (callstack,)).unwrap();
            let records = result.extract::<Vec<String>>().unwrap();

            assert_eq!(records.len(), 0);
        });
    }

    #[test]
    fn test_extract_records_no_matches() {
        with_record_scanner(|_py, scanner| {
            let callstack = vec![
                "[RSP+8  ] 0x123             (void*)".to_string(),
                "[RSP+10 ] 0x456             (char*)".to_string(),
                "[RSP+18 ] 0x789             (size_t)".to_string(),
            ];

            let result = scanner.call_method1("extract_records", (callstack,)).unwrap();
            let records = result.extract::<Vec<String>>().unwrap();

            // All should be filtered by ignore list
            assert_eq!(records.len(), 0);
        });
    }

    #[test]
    fn test_extract_records_case_insensitive() {
        with_record_scanner(|_py, scanner| {
            let callstack = vec![
                "[RSP+8  ] 0x123             (bsresource*)".to_string(),
                "[RSP+10 ] 0x456             (TESOBJECTREFR*)".to_string(),
                "[RSP+18 ] 0x789             (AcToR*)".to_string(),
            ];

            let result = scanner.call_method1("extract_records", (callstack,)).unwrap();
            let records = result.extract::<Vec<String>>().unwrap();

            assert_eq!(records.len(), 3);
        });
    }

    #[test]
    fn test_extract_records_non_rsp_lines() {
        with_record_scanner(|_py, scanner| {
            let callstack = vec![
                "BSResource::Archive loading".to_string(),
                "  TESObjectREFR reference".to_string(),
                "Actor processing".to_string(),
            ];

            let result = scanner.call_method1("extract_records", (callstack,)).unwrap();
            let records = result.extract::<Vec<String>>().unwrap();

            // Should extract full lines (trimmed) since no RSP marker
            assert_eq!(records.len(), 3);
            assert_eq!(records[0], "BSResource::Archive loading");
            assert_eq!(records[1], "TESObjectREFR reference");
            assert_eq!(records[2], "Actor processing");
        });
    }

    #[test]
    fn test_extract_records_mixed_format() {
        with_record_scanner(|_py, scanner| {
            let callstack = vec![
                "[RSP+8  ] 0x123               (BSResource*)".to_string(),
                "TESObjectREFR without RSP".to_string(),
                "[RSP+10 ] 0x456               (Actor*)".to_string(),
            ];

            let result = scanner.call_method1("extract_records", (callstack,)).unwrap();
            let records = result.extract::<Vec<String>>().unwrap();

            assert_eq!(records.len(), 3);
            // RSP lines should be extracted after offset (30 chars)
            assert_eq!(records[0], "(BSResource*)");
            // Non-RSP line should be full line
            assert_eq!(records[1], "TESObjectREFR without RSP");
            assert_eq!(records[2], "(Actor*)");
        });
    }

    #[test]
    #[ignore = "Requires ClassicLib.ScanLog.ReportFragment Python module"]
    fn test_scan_named_records_with_matches() {
        with_record_scanner(|_py, scanner| {
            let callstack = vec![
                "[RSP+8  ] 0x123             (BSResource*)".to_string(),
                "[RSP+10 ] 0x456             (BSResource*)".to_string(),
                "[RSP+18 ] 0x789             (TESObjectREFR*)".to_string(),
            ];

            let result = scanner.call_method1("scan_named_records", (callstack,));

            // Should return (fragment, matches) tuple
            assert!(result.is_ok());

            if let Ok(tuple) = result {
                let (_fragment, matches) = tuple.extract::<(Py<PyAny>, Vec<String>)>().unwrap();

                assert_eq!(matches.len(), 3);
                assert!(matches[0].contains("BSResource"));
                assert!(matches[1].contains("BSResource"));
                assert!(matches[2].contains("TESObjectREFR"));
            }
        });
    }

    #[test]
    #[ignore = "Requires ClassicLib.ScanLog.ReportFragment Python module"]
    fn test_scan_named_records_no_matches() {
        with_record_scanner(|_py, scanner| {
            let callstack = vec![
                "[RSP+8  ] 0x123             (void*)".to_string(),
                "[RSP+10 ] 0x456             (char*)".to_string(),
            ];

            let result = scanner.call_method1("scan_named_records", (callstack,));

            assert!(result.is_ok());

            if let Ok(tuple) = result {
                let (_fragment, matches) = tuple.extract::<(Py<PyAny>, Vec<String>)>().unwrap();

                // Should return empty matches
                assert_eq!(matches.len(), 0);
            }
        });
    }

    #[test]
    #[ignore = "Requires ClassicLib.ScanLog.ReportFragment Python module"]
    fn test_record_scan_integration() {
        with_record_scanner(|py, scanner| {
            // Create a mock report object
            let report_module = py.import("ClassicLib.ScanLog.Report");

            if report_module.is_err() {
                println!("Skipping test - ClassicLib not available");
                return;
            }

            let report_class = report_module.unwrap().getattr("Report").unwrap();
            let report = report_class.call0().unwrap();

            let callstack = vec![
                "[RSP+8  ] 0x123             (BSResource*)".to_string(),
                "[RSP+10 ] 0x456             (TESObjectREFR*)".to_string(),
            ];

            let result = scanner.call_method1("record_scan", (callstack, report));

            // Should succeed without error
            assert!(result.is_ok());
        });
    }

    #[test]
    fn test_clear_cache() {
        with_record_scanner(|_py, scanner| {
            // Clear cache should not error (even if currently no-op)
            let result = scanner.call_method0("clear_cache");
            assert!(result.is_ok());
        });
    }

    #[test]
    fn test_record_counting_and_sorting() {
        with_record_scanner(|_py, scanner| {
            // Test that duplicate records are counted correctly
            let callstack = vec![
                "[RSP+8  ] 0x123               (BSResource*)".to_string(),
                "[RSP+10 ] 0x456               (BSResource*)".to_string(),
                "[RSP+18 ] 0x789               (BSResource*)".to_string(),
                "[RSP+20 ] 0xABC               (TESObjectREFR*)".to_string(),
                "[RSP+28 ] 0xDEF               (TESObjectREFR*)".to_string(),
                "[RSP+30 ] 0x111               (Actor*)".to_string(),
            ];

            let result = scanner.call_method1("extract_records", (callstack,)).unwrap();
            let records = result.extract::<Vec<String>>().unwrap();

            assert_eq!(records.len(), 6);

            // Count occurrences
            let mut bsresource_count = 0;
            let mut tesobject_count = 0;
            let mut actor_count = 0;

            for record in &records {
                let lower = record.to_lowercase();
                if lower.contains("bsresource") {
                    bsresource_count += 1;
                } else if lower.contains("tesobject") {
                    tesobject_count += 1;
                } else if lower.contains("actor") {
                    actor_count += 1;
                }
            }

            assert_eq!(bsresource_count, 3);
            assert_eq!(tesobject_count, 2);
            assert_eq!(actor_count, 1);
        });
    }

    #[test]
    fn test_realistic_crash_log_segment() {
        with_record_scanner(|_py, scanner| {
            // Real-world crash log segment from test data
            let callstack = vec![
                "[RSP+8  ] 0x80ECFDFA90      (void*)".to_string(),
                "[RSP+10 ] 0x1AC             (size_t)".to_string(),
                "[RSP+18 ] 0x22FCA037A78     (char*) \"WCLINS_PRP_Patch - Main.ba2\"".to_string(),
                "[RSP+20 ] 0x0               (NULL)".to_string(),
                "[RSP+28 ] 0x80ECFDFB30      (void*)".to_string(),
                "[RSP+30 ] 0x22FCA037950     (void*)".to_string(),
                "[RSP+38 ] 0x7FF6EF4B2DC8    (void* -> Fallout4.exe+0712DC8)".to_string(),
                "[RSP+40 ] 0x7FF6F1E52E60      (BSResource::Archive2**)".to_string(),
                "[RSP+48 ] 0x2302DDAB040       (BSGeometrySegmentData*)".to_string(),
            ];

            let result = scanner.call_method1("extract_records", (callstack,)).unwrap();
            let records = result.extract::<Vec<String>>().unwrap();

            // Should find BSResource and BSGeometrySegmentData
            assert_eq!(records.len(), 2);
            assert!(records[0].contains("BSResource::Archive2**"));
            assert!(records[1].contains("BSGeometrySegmentData*"));
        });
    }
}

// ===== Edge Case Tests =====

#[test]
fn test_scan_records_batch_special_characters() {
    let segments = vec![vec![
        "[RSP+8  ] 0x123             (BSResource::Archive<T>*)".to_string(),
        "[RSP+10 ] 0x456             (TESForm[100])".to_string(),
    ]];

    let target_records = vec!["BSResource".to_string(), "TESForm".to_string()];
    let ignore_records = vec![];

    let results = scan_records_batch(segments, target_records, ignore_records);

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].len(), 2);
}

#[test]
fn test_scan_records_batch_unicode() {
    let segments = vec![vec![
        "[RSP+8  ] 0x123             (Record with émojis 🎮)".to_string(),
    ]];

    let target_records = vec!["Record".to_string()];
    let ignore_records = vec![];

    let results = scan_records_batch(segments, target_records, ignore_records);

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].len(), 1);
}

#[test]
fn test_scan_records_batch_very_long_lines() {
    let long_record = format!("BSResource{}", "A".repeat(10000));
    let segments = vec![vec![
        format!("[RSP+8  ] 0x123             ({})", long_record),
    ]];

    let target_records = vec!["BSResource".to_string()];
    let ignore_records = vec![];

    let results = scan_records_batch(segments, target_records, ignore_records);

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].len(), 1);
    assert!(results[0][0].len() > 10000);
}

#[test]
fn test_contains_record_partial_matches() {
    let target_records = vec!["BS".to_string()];
    let ignore_records = vec![];

    // Should match partial substring
    assert!(contains_record(
        "BSResource",
        target_records.clone(),
        ignore_records.clone()
    ));
    assert!(contains_record(
        "ABSTRACT",
        target_records.clone(),
        ignore_records.clone()
    ));
}

#[test]
fn test_contains_record_exact_boundary() {
    let target_records = vec!["test".to_string()];
    let ignore_records = vec!["test".to_string()];

    // Target and ignore both match - ignore should win
    assert!(!contains_record(
        "test",
        target_records,
        ignore_records
    ));
}

// ===== Benchmark Tests (Ignored by default) =====

#[cfg(test)]
mod benchmarks {
    use super::*;

    #[test]
    #[ignore]
    fn bench_record_scanning_large_scale() {
        // Simulate scanning 100 crash log segments
        let mut segments = Vec::new();
        for i in 0..100 {
            let mut segment = Vec::new();
            for j in 0..1000 {
                let record_type = match j % 10 {
                    0 => "BSResource::Archive2**",
                    1 => "TESObjectREFR*",
                    2 => "Actor*",
                    3 => "TESForm*",
                    4 => "BSGeometrySegmentData*",
                    _ => "void*",
                };
                segment.push(format!(
                    "[RSP+{}  ] 0x{:016X}      ({})",
                    (j % 100) * 8,
                    i * 1000 + j,
                    record_type
                ));
            }
            segments.push(segment);
        }

        let target_records = vec![
            "BSResource".to_string(),
            "TESObjectREFR".to_string(),
            "Actor".to_string(),
            "TESForm".to_string(),
            "BSGeometrySegmentData".to_string(),
        ];
        let ignore_records = vec!["void*".to_string()];

        let start = Instant::now();
        let results = scan_records_batch(segments, target_records, ignore_records);
        let elapsed = start.elapsed();

        let total_matches: usize = results.iter().map(|r| r.len()).sum();
        println!("Scanned 100 segments (100,000 lines) in {:?}", elapsed);
        println!("Found {} total matches", total_matches);
        println!("Average: {:?} per segment", elapsed / 100);

        // Target: 40x speedup over Python (assume Python takes ~400ms)
        // Rust should complete in ~10ms or less
        assert!(elapsed.as_millis() < 100, "Expected < 100ms, got {:?}", elapsed);
    }

    #[test]
    #[ignore]
    fn bench_aho_corasick_many_patterns() {
        // Test Aho-Corasick efficiency with many patterns
        let mut segments = Vec::new();
        for i in 0..1000 {
            let mut segment = Vec::new();
            for j in 0..100 {
                segment.push(format!("Pattern{} value {}", j % 50, i));
            }
            segments.push(segment);
        }

        // 50 different patterns
        let target_records: Vec<String> = (0..50)
            .map(|i| format!("Pattern{}", i))
            .collect();
        let ignore_records = vec![];

        let start = Instant::now();
        let _results = scan_records_batch(segments, target_records, ignore_records);
        let elapsed = start.elapsed();

        println!("Scanned 100,000 lines with 50 patterns in {:?}", elapsed);

        // Aho-Corasick should be O(n + m) not O(n * m)
        assert!(elapsed.as_millis() < 200, "Expected < 200ms, got {:?}", elapsed);
    }

    #[test]
    #[ignore]
    fn bench_parallel_vs_sequential_simulation() {
        // Create workload that benefits from parallelism
        let mut segments = Vec::new();
        for i in 0..10000 {
            segments.push(vec![
                format!("Line 1 segment {}", i),
                format!("Line 2 BSResource {}", i),
                format!("Line 3 TESObjectREFR {}", i),
            ]);
        }

        let target_records = vec!["BSResource".to_string(), "TESObjectREFR".to_string()];
        let ignore_records = vec![];

        let start = Instant::now();
        let _results = scan_records_batch(segments, target_records, ignore_records);
        let parallel_time = start.elapsed();

        println!("Parallel processing of 10,000 segments: {:?}", parallel_time);

        // With Rayon parallelism, should be very fast
        assert!(parallel_time.as_millis() < 100, "Expected < 100ms, got {:?}", parallel_time);
    }

    #[test]
    #[ignore]
    fn bench_contains_record_hot_path() {
        // Benchmark the hot path for record checking
        let target_records = vec![
            "BSResource".to_string(),
            "TESObjectREFR".to_string(),
            "Actor".to_string(),
        ];
        let ignore_records = vec!["void*".to_string(), "char*".to_string()];

        let test_lines = vec![
            "0x123 (BSResource*)",
            "0x456 (void*)",
            "0x789 (TESObjectREFR*)",
            "0xABC (char*)",
            "0xDEF (Actor*)",
        ];

        let iterations = 100_000u128;  // Reduced for reasonable test time
        let start = Instant::now();

        for _ in 0..iterations {
            for line in &test_lines {
                let _ = contains_record(line, target_records.clone(), ignore_records.clone());
            }
        }

        let elapsed = start.elapsed();
        let total_calls = iterations * test_lines.len() as u128;
        let per_call = elapsed.as_nanos() / total_calls;

        println!("Checked {} calls in {:?}", total_calls, elapsed);
        println!("Average: {}ns per call", per_call);

        // Should be very fast (< 10μs per call with cloning overhead)
        assert!(per_call < 10000, "Expected < 10μs per call, got {}ns", per_call);
    }
}
