#![allow(missing_docs)]
//! Criterion benchmarks for `classic-database-core`.

use classic_database_core::DatabasePool;
use classic_shared_core::get_runtime;
use criterion::{
    BatchSize, BenchmarkId, Criterion, Throughput, criterion_group, criterion_main,
};
use std::path::PathBuf;
use std::hint::black_box;
use std::time::Duration;

#[path = "../../../benches/common/mod.rs"]
mod common;
#[path = "../../../benches/common/db_fixtures.rs"]
mod db_fixtures;

fn init_pool(db_paths: Vec<PathBuf>, table_name: &str) -> DatabasePool {
    let runtime = get_runtime();
    let pool = DatabasePool::new(Some(8), Duration::from_secs(900), table_name.to_string());
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

    let pool = init_pool(vec![fixture.db_paths[0].clone()], &fixture.table_name);
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
    let pool = init_pool(vec![fixture.db_paths[0].clone()], &fixture.table_name);

    let classes: [(&str, usize, usize); 3] = [
        ("small_32", 32, 32),
        ("medium_256", 256, 128),
        ("large_1024", 1_024, 256),
    ];

    for (scenario_id, pair_count, batch_size) in classes {
        let pairs = fixture.mixed_pairs(pair_count, 5);
        group.throughput(Throughput::Elements(pair_count as u64));

        group.bench_with_input(BenchmarkId::from_parameter(scenario_id), &pairs, |b, pairs| {
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
        });
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

    let pool = init_pool(fixture.db_paths.clone(), &fixture.table_name);
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

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets =
        single_lookup_benchmarks,
        batch_lookup_benchmarks,
        multi_db_fallback_benchmarks
}

criterion_main!(benches);
