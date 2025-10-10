use classic_tui::widgets::{
    ButtonState, Checkbox, FolderSelector, OutputViewer, ScanButton, ScanType, StatusBar,
};
use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion};
use std::path::PathBuf;
use tempfile::tempdir;

/// Benchmark widget creation
fn bench_widget_creation(c: &mut Criterion) {
    c.bench_function("folder_selector_creation", |b| {
        b.iter(|| {
            let widget = black_box(FolderSelector::new("Test Folder"));
            widget
        })
    });

    c.bench_function("scan_button_creation", |b| {
        b.iter(|| {
            let widget = black_box(ScanButton::new("Scan", ScanType::CrashLogs, "F5"));
            widget
        })
    });

    c.bench_function("output_viewer_creation", |b| {
        b.iter(|| {
            let widget = black_box(OutputViewer::new());
            widget
        })
    });

    c.bench_function("checkbox_creation", |b| {
        b.iter(|| {
            let widget = black_box(Checkbox::new("Option", false));
            widget
        })
    });

    c.bench_function("status_bar_creation", |b| {
        b.iter(|| {
            let widget = black_box(StatusBar::new());
            widget
        })
    });
}

/// Benchmark widget state mutations
fn bench_widget_mutations(c: &mut Criterion) {
    c.bench_function("folder_selector_set_value", |b| {
        let path = PathBuf::from("C:\\Test");
        b.iter(|| {
            let mut selector = FolderSelector::new("Test");
            selector.set_value(path.clone());
            black_box(selector)
        })
    });

    c.bench_function("folder_selector_validation", |b| {
        let temp_dir = tempdir().unwrap();
        let mut selector = FolderSelector::new("Test");
        selector.set_value(temp_dir.path().to_path_buf());

        b.iter(|| {
            let valid = black_box(selector.validate());
            valid
        })
    });

    c.bench_function("scan_button_state_changes", |b| {
        b.iter(|| {
            let mut button = ScanButton::new("Scan", ScanType::CrashLogs, "F5");
            button.start_scan();
            button.update_progress(0.5);
            button.complete();
            button.reset();
            black_box(button)
        })
    });

    c.bench_function("checkbox_toggle", |b| {
        b.iter(|| {
            let mut checkbox = Checkbox::new("Option", false);
            checkbox.toggle();
            black_box(checkbox)
        })
    });
}

/// Benchmark output viewer operations (critical for performance)
fn bench_output_viewer(c: &mut Criterion) {
    let mut group = c.benchmark_group("output_viewer");

    // Test different buffer sizes
    for size in [10, 100, 1000, 10000].iter() {
        group.bench_with_input(BenchmarkId::new("append_lines", size), size, |b, &size| {
            b.iter(|| {
                let mut viewer = OutputViewer::new();
                for i in 0..size {
                    viewer.append(format!("Line {}", i));
                }
                black_box(viewer)
            })
        });
    }

    group.bench_function("scroll_operations", |b| {
        b.iter(|| {
            let mut viewer = OutputViewer::new();
            for i in 0..1000 {
                viewer.append(format!("Line {}", i));
            }
            viewer.scroll_up(10);
            viewer.scroll_down(5, 20); // visible_lines = 20
            viewer.scroll_to_top();
            viewer.scroll_to_bottom();
            black_box(viewer)
        })
    });

    group.bench_function("clear_buffer", |b| {
        b.iter(|| {
            let mut viewer = OutputViewer::new();
            for i in 0..1000 {
                viewer.append(format!("Line {}", i));
            }
            viewer.clear();
            black_box(viewer)
        })
    });

    group.finish();
}

/// Benchmark rendering performance (CRITICAL - target 60 FPS = 16ms per frame)
/// TODO: Fix Terminal lifetime issues - requires creating terminal inside iter closure
#[cfg(feature = "never")] // Disabled due to Terminal lifetime issues
fn bench_rendering(c: &mut Criterion) {
    let mut group = c.benchmark_group("rendering");
    group.measurement_time(Duration::from_secs(5));

    // Target: < 16ms for 60 FPS
    group.bench_function("folder_selector_render", |b| {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let temp_dir = tempdir().unwrap();
        let mut selector = FolderSelector::new("Test Folder");
        selector.set_value(temp_dir.path().to_path_buf());

        b.iter(|| {
            terminal
                .draw(|f| {
                    let area = Rect::new(0, 0, 80, 3);
                    selector.render(f, area);
                })
                .unwrap();
            black_box(&terminal)
        })
    });

    group.bench_function("scan_button_render", |b| {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut button = ScanButton::new("Crash Logs Scan", ScanType::CrashLogs, "F5");
        button.start_scan();
        button.update_progress(0.5);

        b.iter(|| {
            terminal
                .draw(|f| {
                    let area = Rect::new(0, 0, 20, 3);
                    button.render(f, area);
                })
                .unwrap();
            black_box(&terminal)
        })
    });

    group.bench_function("output_viewer_render_large", |b| {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut viewer = OutputViewer::new();

        // Large output buffer
        for i in 0..1000 {
            viewer.append(format!("Output line {} with some content", i));
        }

        b.iter(|| {
            terminal
                .draw(|f| {
                    let area = Rect::new(0, 0, 80, 20);
                    viewer.render(f, area);
                })
                .unwrap();
            black_box(&terminal)
        })
    });

    group.bench_function("full_screen_render", |b| {
        let backend = TestBackend::new(120, 40);
        let mut terminal = Terminal::new(backend).unwrap();

        // Setup multiple widgets
        let temp_dir = tempdir().unwrap();
        let mut selector1 = FolderSelector::new("Staging Folder");
        selector1.set_value(temp_dir.path().to_path_buf());

        let mut selector2 = FolderSelector::new("Custom Folder");
        selector2.set_value(temp_dir.path().to_path_buf());

        let mut button1 = ScanButton::new("Crash Logs", ScanType::CrashLogs, "F5");
        button1.start_scan();

        let button2 = ScanButton::new("Game Files", ScanType::GameFiles, "F6");

        let mut viewer = OutputViewer::new();
        for i in 0..100 {
            viewer.append(format!("Log line {}", i));
        }

        let status = StatusBar::new();

        b.iter(|| {
            terminal
                .draw(|f| {
                    // Simulate full screen layout
                    selector1.render(f, Rect::new(0, 0, 120, 3));
                    selector2.render(f, Rect::new(0, 3, 120, 3));
                    button1.render(f, Rect::new(0, 6, 30, 3));
                    button2.render(f, Rect::new(30, 6, 30, 3));
                    viewer.render(f, Rect::new(0, 9, 120, 28));
                    status.render(f, Rect::new(0, 37, 120, 3));
                })
                .unwrap();
            black_box(&terminal)
        })
    });

    group.finish();
}

/// Benchmark focus management
fn bench_focus_management(c: &mut Criterion) {
    c.bench_function("focus_change_multiple_widgets", |b| {
        b.iter(|| {
            let mut selector1 = FolderSelector::new("Folder 1");
            let mut selector2 = FolderSelector::new("Folder 2");
            let mut selector3 = FolderSelector::new("Folder 3");

            // Simulate tab navigation
            selector1.set_focused(true);
            selector2.set_focused(false);
            selector3.set_focused(false);

            selector1.set_focused(false);
            selector2.set_focused(true);
            selector3.set_focused(false);

            selector1.set_focused(false);
            selector2.set_focused(false);
            selector3.set_focused(true);

            black_box((selector1, selector2, selector3))
        })
    });
}

/// Benchmark memory allocation patterns
fn bench_memory_patterns(c: &mut Criterion) {
    c.bench_function("output_buffer_growth", |b| {
        b.iter(|| {
            let mut viewer = OutputViewer::new();
            for i in 0..1000 {
                viewer.append(format!("Line {}", i));
            }
            black_box(viewer)
        })
    });

    c.bench_function("widget_allocation_batch", |b| {
        b.iter(|| {
            let widgets = vec![
                FolderSelector::new("Folder 1"),
                FolderSelector::new("Folder 2"),
                FolderSelector::new("Folder 3"),
            ];
            black_box(widgets)
        })
    });
}

/// Benchmark state transitions
fn bench_state_transitions(c: &mut Criterion) {
    c.bench_function("scan_button_complete_workflow", |b| {
        b.iter(|| {
            let mut button = ScanButton::new("Test Scan", ScanType::CrashLogs, "F5");

            // Idle -> Scanning
            button.start_scan();

            // Update progress multiple times
            for i in 0..10 {
                button.update_progress(i as f64 / 10.0);
            }

            // Scanning -> Completed
            button.complete();

            // Reset to Idle
            button.reset();

            black_box(button)
        })
    });
}

/// Benchmark terminal backend operations
/// TODO: Fix Terminal lifetime issues
#[cfg(feature = "never")] // Disabled due to Terminal lifetime issues
fn bench_terminal_operations(c: &mut Criterion) {
    c.bench_function("terminal_creation", |b| {
        b.iter(|| {
            let backend = TestBackend::new(80, 24);
            let terminal = Terminal::new(backend).unwrap();
            black_box(terminal)
        })
    });

    c.bench_function("terminal_clear", |b| {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();

        b.iter(|| {
            terminal.clear().unwrap();
            black_box(&terminal)
        })
    });
}

/// Benchmark dirty tracking optimization effectiveness
fn bench_dirty_tracking(c: &mut Criterion) {
    c.bench_function("dirty_tracking_no_op_operations", |b| {
        b.iter(|| {
            let mut viewer = OutputViewer::new();
            viewer.mark_clean();

            // 100 no-op operations that should not mark dirty
            for _ in 0..100 {
                viewer.scroll_up(0); // No actual scroll
                black_box(viewer.is_dirty()); // Check but don't render
            }
            black_box(viewer)
        })
    });

    c.bench_function("dirty_tracking_real_changes", |b| {
        b.iter(|| {
            let mut viewer = OutputViewer::new();
            viewer.mark_clean();

            // 10 real changes that should mark dirty
            for i in 0..10 {
                viewer.append(format!("Line {}", i));
                if viewer.is_dirty() {
                    viewer.mark_clean(); // Simulate render
                }
            }
            black_box(viewer)
        })
    });

    c.bench_function("dirty_tracking_mixed_operations", |b| {
        b.iter(|| {
            let mut viewer = OutputViewer::new();
            viewer.append("Initial".to_string());
            viewer.mark_clean();

            // Mix of operations: some dirty, some not
            for i in 0..20 {
                if i % 3 == 0 {
                    viewer.append(format!("Line {}", i)); // Marks dirty
                } else {
                    viewer.scroll_up(0); // No-op, doesn't mark dirty
                }

                if viewer.is_dirty() {
                    viewer.mark_clean(); // Simulate render
                }
            }
            black_box(viewer)
        })
    });

    c.bench_function("dirty_tracking_progress_updates", |b| {
        b.iter(|| {
            let mut button = ScanButton::new("Test", ScanType::CrashLogs, "F5");
            button.start_scan();
            button.mark_clean();

            // Simulate 100 progress updates (only large changes mark dirty)
            for i in 0..100 {
                button.update_progress(i as f64 / 100.0);
                if button.is_dirty() {
                    button.mark_clean(); // Simulate render
                }
            }
            black_box(button)
        })
    });

    c.bench_function("dirty_tracking_multiple_widgets", |b| {
        b.iter(|| {
            let mut viewer = OutputViewer::new();
            let mut button1 = ScanButton::new("Crash", ScanType::CrashLogs, "F5");
            let mut button2 = ScanButton::new("Game", ScanType::GameFiles, "F6");
            let mut selector = FolderSelector::new("Mods");

            // Clean all
            viewer.mark_clean();
            button1.mark_clean();
            button2.mark_clean();
            selector.mark_clean();

            // Interleaved operations on different widgets
            for i in 0..20 {
                match i % 4 {
                    0 => viewer.append(format!("Line {}", i)),
                    1 => button1.update_progress(i as f64 / 20.0),
                    2 => button2.update_progress(i as f64 / 20.0),
                    _ => selector.set_value(PathBuf::from(format!("C:\\Path{}", i))),
                }

                // Only render widgets that are dirty
                if viewer.is_dirty() {
                    viewer.mark_clean();
                }
                if button1.is_dirty() {
                    button1.mark_clean();
                }
                if button2.is_dirty() {
                    button2.mark_clean();
                }
                if selector.is_dirty() {
                    selector.mark_clean();
                }
            }

            black_box((viewer, button1, button2, selector))
        })
    });
}

criterion_group!(
    benches,
    bench_widget_creation,
    bench_widget_mutations,
    bench_output_viewer,
    // bench_rendering, // TODO: Fix Terminal lifetime issues - requires creating terminal inside iter
    bench_focus_management,
    bench_memory_patterns,
    bench_state_transitions,
    bench_dirty_tracking,
    // bench_terminal_operations // TODO: Fix Terminal lifetime issues
);

criterion_main!(benches);
