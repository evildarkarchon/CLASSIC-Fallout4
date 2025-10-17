use classic_tui::widgets::Checkbox;
use criterion::{black_box, criterion_group, criterion_main, Criterion};

/// Benchmark widget creation
fn bench_widget_creation(c: &mut Criterion) {
    c.bench_function("checkbox_creation", |b| {
        b.iter(|| {
            let widget = black_box(Checkbox::new("Option", false));
            widget
        })
    });
}

/// Benchmark widget state mutations
fn bench_widget_mutations(c: &mut Criterion) {
    c.bench_function("checkbox_toggle", |b| {
        b.iter(|| {
            let mut checkbox = Checkbox::new("Option", false);
            checkbox.toggle();
            black_box(checkbox)
        })
    });
}


/// Benchmark dirty tracking optimization effectiveness
fn bench_dirty_tracking(c: &mut Criterion) {
    c.bench_function("dirty_tracking_checkbox", |b| {
        b.iter(|| {
            let mut checkbox = Checkbox::new("Option", false);
            checkbox.mark_clean();

            // Toggle and check dirty state
            for _ in 0..10 {
                checkbox.toggle();
                if checkbox.is_dirty() {
                    checkbox.mark_clean(); // Simulate render
                }
            }
            black_box(checkbox)
        })
    });
}

criterion_group!(
    benches,
    bench_widget_creation,
    bench_widget_mutations,
    bench_dirty_tracking
);

criterion_main!(benches);
