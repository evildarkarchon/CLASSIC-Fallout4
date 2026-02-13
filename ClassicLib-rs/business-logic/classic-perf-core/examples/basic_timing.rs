//! Basic timing example for classic-perf-core.
//!
//! This example demonstrates how to use the Timer API for basic performance
//! monitoring and metrics collection.

use classic_perf_core::{clear_metrics, get_summary, start_timer};
use std::thread;
use std::time::Duration;

fn main() {
    // Clear any existing metrics
    clear_metrics();

    println!("=== Basic Timing Example ===\n");

    // Example 1: Simple operation timing
    println!("1. Timing a simple operation...");
    {
        let timer = start_timer("simple_operation");
        thread::sleep(Duration::from_millis(100));
        timer.finish();
    }

    // Example 2: Automatic timing with drop
    println!("2. Automatic timing (no explicit finish)...");
    {
        let _timer = start_timer("auto_operation");
        thread::sleep(Duration::from_millis(50));
        // Timer automatically records when dropped
    }

    // Example 3: Multiple timings of the same operation
    println!("3. Multiple timings of the same operation...");
    for i in 1..=5 {
        let timer = start_timer("batch_operation");
        thread::sleep(Duration::from_millis(20 + i * 5));
        timer.finish();
    }

    // Example 4: Check elapsed time
    println!("4. Checking elapsed time...");
    {
        let timer = start_timer("elapsed_check");
        thread::sleep(Duration::from_millis(30));
        let elapsed = timer.elapsed();
        println!("   Current elapsed: {:.3}s", elapsed);
        thread::sleep(Duration::from_millis(20));
        timer.finish();
    }

    // Get and display summary statistics
    println!("\n=== Summary Statistics ===\n");
    let summary = get_summary();

    for (name, stats) in summary.iter() {
        println!("Operation: {}", name);
        println!("  Count:   {}", stats.count);
        println!("  Total:   {:.3}s", stats.total);
        println!("  Average: {:.3}s", stats.average);
        println!("  Min:     {:.3}s", stats.min);
        println!("  Max:     {:.3}s", stats.max);
        println!();
    }
}
