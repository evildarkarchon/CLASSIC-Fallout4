#![allow(missing_docs)]
//! Criterion benchmarks for `classic-database-core`.

use classic_database_core::DatabasePool;
use classic_shared_core::get_runtime;
use criterion::{BatchSize, BenchmarkId, Criterion, Throughput, criterion_group, criterion_main};
use std::hint::black_box;
use std::path::PathBuf;
use std::time::Duration;

#[path = "../../../benches/common/mod.rs"]
mod common;
#[path = "../../../benches/common/db_fixtures.rs"]
mod db_fixtures;

fn init_pool(db_paths: Vec<PathBuf>, table_name: &str, max_connections: usize) -> DatabasePool {
    let runtime = get_runtime();
    let pool = DatabasePool::new(
        Some(max_connections),
        Duration::from_secs(900),
        table_name.to_string(),
    );
    runtime
        .block_on(pool.initialize(db_paths))
        .expect("database fixture initialization should succeed");
    pool
}

fn single_lookup_benchmarks(c: &mut Criterion) {
    let runtime = get_runtime();
    let fixture = runtime
        .block_on(db_fixtures::DeterministicDbFixture::create(
            db_fixtures::FixtureConfig::default(),
        ))
        .expect("deterministic fixture generation should succeed");

    let mut group = c.benchmark_group("db_single_lookup");
    group.throughput(Throughput::Elements(1));

    let pool = init_pool(vec![fixture.db_paths[0].clone()], &fixture.table_name, 8);
    let (hit_formid, hit_plugin) = fixture.single_hit_pair();
    let (miss_formid, miss_plugin) = fixture.miss_pair();

    group.bench_function(BenchmarkId::from_parameter("cold_hit"), |b| {
        b.iter(|| {
            pool.clear_cache(false);
            let value = runtime
                .block_on(pool.get_entry(&hit_formid, &hit_plugin, None))
                .expect("single lookup should not error");
            black_box(value);
        });
    });

    runtime
        .block_on(pool.get_entry(&hit_formid, &hit_plugin, None))
        .expect("cache warm-up lookup should succeed");

    group.bench_function(BenchmarkId::from_parameter("warm_hit"), |b| {
        b.iter(|| {
            let value = runtime
                .block_on(pool.get_entry(&hit_formid, &hit_plugin, None))
                .expect("single lookup should not error");
            black_box(value);
        });
    });

    group.bench_function(BenchmarkId::from_parameter("cold_miss"), |b| {
        b.iter(|| {
            pool.clear_cache(false);
            let value = runtime
                .block_on(pool.get_entry(&miss_formid, &miss_plugin, None))
                .expect("single lookup should not error");
            black_box(value);
        });
    });

    group.finish();
    runtime
        .block_on(pool.close())
        .expect("database pool close should succeed");
}

fn batch_lookup_benchmarks(c: &mut Criterion) {
    let runtime = get_runtime();
    let fixture = runtime
        .block_on(db_fixtures::DeterministicDbFixture::create(
            db_fixtures::FixtureConfig::default(),
        ))
        .expect("deterministic fixture generation should succeed");

    let mut group = c.benchmark_group("db_batch_lookup");
    let pool = init_pool(vec![fixture.db_paths[0].clone()], &fixture.table_name, 8);

    let classes: [(&str, usize, usize); 11] = [
        ("bucket_boundary_7", 7, 16),
        ("bucket_boundary_8", 8, 16),
        ("bucket_boundary_9", 9, 16),
        ("bucket_boundary_15", 15, 32),
        ("bucket_boundary_16", 16, 32),
        ("bucket_boundary_17", 17, 32),
        ("bucket_boundary_255", 255, 512),
        ("bucket_boundary_256", 256, 512),
        ("bucket_boundary_257", 257, 512),
        ("bucket_boundary_1023", 1_023, 1_024),
        ("bucket_boundary_1024", 1_024, 1_024),
    ];

    for (scenario_id, pair_count, batch_size) in classes {
        let pairs = fixture.mixed_pairs(pair_count, 5);
        group.throughput(Throughput::Elements(pair_count as u64));

        group.bench_with_input(
            BenchmarkId::from_parameter(scenario_id),
            &pairs,
            |b, pairs| {
                b.iter_batched(
                    || pairs.clone(),
                    |pairs| {
                        pool.clear_cache(false);
                        let result = runtime
                            .block_on(pool.get_entries_batch(pairs, None, batch_size))
                            .expect("batch lookup should not error");
                        black_box(result.len());
                    },
                    BatchSize::SmallInput,
                );
            },
        );
    }

    group.finish();
    runtime
        .block_on(pool.close())
        .expect("database pool close should succeed");
}

fn repeated_bucket_reuse_benchmarks(c: &mut Criterion) {
    let runtime = get_runtime();
    let fixture = runtime
        .block_on(db_fixtures::DeterministicDbFixture::create(
            db_fixtures::FixtureConfig::default(),
        ))
        .expect("deterministic fixture generation should succeed");

    let mut group = c.benchmark_group("db_batch_bucket_reuse");
    let pool = init_pool(vec![fixture.db_paths[0].clone()], &fixture.table_name, 8);

    let classes: [(&str, usize, usize); 3] = [
        ("repeat_bucket_16", 256, 16),
        ("repeat_bucket_32", 512, 32),
        ("repeat_bucket_256", 1_024, 256),
    ];

    for (scenario_id, pair_count, batch_size) in classes {
        let pairs = fixture.mixed_pairs(pair_count, 6);
        group.throughput(Throughput::Elements(pair_count as u64));

        group.bench_with_input(
            BenchmarkId::from_parameter(scenario_id),
            &pairs,
            |b, pairs| {
                b.iter_batched(
                    || pairs.clone(),
                    |pairs| {
                        pool.clear_cache(false);
                        let result = runtime
                            .block_on(pool.get_entries_batch(pairs, None, batch_size))
                            .expect("batch lookup should not error");
                        black_box(result.len());
                    },
                    BatchSize::SmallInput,
                );
            },
        );
    }

    group.finish();
    runtime
        .block_on(pool.close())
        .expect("database pool close should succeed");
}

fn multi_db_fallback_benchmarks(c: &mut Criterion) {
    let runtime = get_runtime();
    let fixture = runtime
        .block_on(db_fixtures::DeterministicDbFixture::create(
            db_fixtures::FixtureConfig::default(),
        ))
        .expect("deterministic fixture generation should succeed");

    let mut group = c.benchmark_group("db_multi_db_fallback");
    group.throughput(Throughput::Elements(1));

    let pool = init_pool(fixture.db_paths.clone(), &fixture.table_name, 8);
    let (secondary_formid, secondary_plugin) = fixture.secondary_only_hit_pair();
    let (miss_formid, miss_plugin) = fixture.miss_pair();
    let secondary_batch = vec![(secondary_formid, secondary_plugin)];

    group.bench_function(BenchmarkId::from_parameter("secondary_only_hit"), |b| {
        b.iter_batched(
            || secondary_batch.clone(),
            |pairs| {
                pool.clear_cache(false);
                let value = runtime
                    .block_on(pool.get_entries_batch(pairs, None, 1))
                    .expect("multi-db lookup should not error");
                black_box(value.len());
            },
            BatchSize::SmallInput,
        );
    });

    group.bench_function(BenchmarkId::from_parameter("miss_all"), |b| {
        b.iter(|| {
            pool.clear_cache(false);
            let value = runtime
                .block_on(pool.get_entry(&miss_formid, &miss_plugin, None))
                .expect("multi-db lookup should not error");
            black_box(value);
        });
    });

    group.finish();
    runtime
        .block_on(pool.close())
        .expect("database pool close should succeed");
}

fn multi_db_budget_benchmarks(c: &mut Criterion) {
    let runtime = get_runtime();
    let fixture = runtime
        .block_on(db_fixtures::DeterministicDbFixture::create(
            db_fixtures::FixtureConfig::default(),
        ))
        .expect("deterministic fixture generation should succeed");

    let mut group = c.benchmark_group("db_multi_db_budget");
    group.throughput(Throughput::Elements(1));

    let (secondary_formid, secondary_plugin) = fixture.secondary_only_hit_pair();
    let (miss_formid, miss_plugin) = fixture.miss_pair();
    let secondary_batch = vec![(secondary_formid, secondary_plugin)];

    for budget in [1_usize, 2, 8] {
        let pool = init_pool(fixture.db_paths.clone(), &fixture.table_name, budget);
        let hit_id = BenchmarkId::new("secondary_only_hit", format!("budget_{budget}"));
        let miss_id = BenchmarkId::new("miss_all", format!("budget_{budget}"));

        group.bench_with_input(hit_id, &secondary_batch, |b, pairs| {
            b.iter_batched(
                || pairs.clone(),
                |pairs| {
                    pool.clear_cache(false);
                    let value = runtime
                        .block_on(pool.get_entries_batch(pairs, None, 1))
                        .expect("multi-db budget lookup should not error");
                    black_box(value.len());
                },
                BatchSize::SmallInput,
            );
        });

        group.bench_function(miss_id, |b| {
            b.iter(|| {
                pool.clear_cache(false);
                let value = runtime
                    .block_on(pool.get_entry(&miss_formid, &miss_plugin, None))
                    .expect("multi-db budget miss should not error");
                black_box(value);
            });
        });

        runtime
            .block_on(pool.close())
            .expect("database pool close should succeed");
    }

    group.finish();
}

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets =
        single_lookup_benchmarks,
        batch_lookup_benchmarks,
        repeated_bucket_reuse_benchmarks,
        multi_db_fallback_benchmarks,
        multi_db_budget_benchmarks
}

criterion_main!(benches);
