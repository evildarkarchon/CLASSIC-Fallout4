# Phase 17: CI Regression Detection - Research

**Researched:** 2026-02-04
**Domain:** GitHub Actions CI/CD, Criterion benchmarking, performance regression detection
**Confidence:** HIGH

## Summary

This phase implements automated performance regression detection in the CI pipeline. The existing Criterion benchmark infrastructure from Phase 13 provides the foundation - benchmarks run in quick mode (50 samples), baselines stored in `target/criterion/`, and comparison via critcmp. The CI integration adds: running benchmarks on PRs marked ready for review, comparing against cached main-branch baselines, posting PR comments with results, and failing builds on significant regressions (>10%).

The implementation uses GitHub Actions cache for baseline persistence (not committed to repo), the `pull_request` event with `ready_for_review` activity type for triggering, and either `boa-dev/criterion-compare-action` or a custom workflow with critcmp for comparison. A label bypass mechanism (`perf-regression-accepted`) allows merging with documented justification.

**Primary recommendation:** Use a custom GitHub Actions workflow with critcmp for comparison (more control over thresholds and formatting), `actions/cache` for baseline management, and `peter-evans/create-or-update-comment` for PR comments. This approach integrates cleanly with the existing benchmark infrastructure and provides the tiered threshold behavior (5% warning, 10% failure) required.

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|--------------|---------|---------|--------------|
| GitHub Actions | N/A | CI/CD platform | Already in use, native integration |
| actions/cache | v4 | Baseline persistence | Official GitHub action, cross-branch cache access |
| critcmp | 0.1.8 | Baseline comparison | BurntSushi's standard Criterion comparison tool, already in project |
| peter-evans/create-or-update-comment | v5 | PR comment management | Industry standard for find-and-update pattern |
| peter-evans/find-comment | v3 | Find existing comments | Companion to create-or-update-comment |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| actions/github-script | v8 | Custom GitHub API interactions | Complex conditional logic, PR label checks |
| cargo | (workspace) | Run benchmarks | Existing benchmark infrastructure |
| jq | System | JSON parsing | Parse critcmp JSON output in shell |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| critcmp + custom workflow | boa-dev/criterion-compare-action | Pre-built but less control over threshold tiers |
| critcmp + custom workflow | benchmark-action/github-action-benchmark | Full-featured but stores data in GitHub Pages branch |
| actions/cache | Commit baselines to repo | Cache is simpler, avoids repo pollution |
| Custom thresholds | Bencher.dev | SaaS service, additional dependency |

**Installation:**
```bash
# critcmp already installed from Phase 13
cargo install critcmp

# No additional dependencies for GitHub Actions
```

## Architecture Patterns

### Recommended Workflow Structure
```
.github/workflows/
├── ci.yml                      # Existing CI workflow (unchanged)
└── benchmarks.yml              # New: benchmark regression detection
    ├── Job: benchmark-pr       # Runs on PRs marked ready for review
    │   ├── Restore baseline cache from main
    │   ├── Run benchmarks (quick mode)
    │   ├── Compare against baseline
    │   ├── Post/update PR comment
    │   └── Fail if regression > 10%
    └── Job: update-baseline    # Runs on main branch push
        ├── Run benchmarks (quick mode)
        └── Save baseline to cache
```

### Pattern 1: Ready-for-Review Trigger
**What:** Trigger benchmarks only when PR is marked ready for review
**When to use:** Required by user decision - avoid running expensive benchmarks on draft PRs
**Example:**
```yaml
# Source: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows
on:
  pull_request:
    types: [ready_for_review]
    branches: [main]
  push:
    branches: [main]

jobs:
  benchmark:
    # Skip if PR is still draft (handles edge case where synchronize triggers)
    if: github.event_name == 'push' || !github.event.pull_request.draft
```

### Pattern 2: Cache-Based Baseline Management
**What:** Store baselines in GitHub Actions cache, update on main branch merge
**When to use:** Required by user decision - baselines not committed to repo
**Example:**
```yaml
# Source: https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows
- name: Restore baseline cache
  uses: actions/cache@v4
  id: baseline-cache
  with:
    path: rust/target/criterion/baseline
    key: criterion-baseline-${{ runner.os }}
    # PRs can restore from main branch cache
    restore-keys: |
      criterion-baseline-${{ runner.os }}

- name: Save baseline cache
  if: github.ref == 'refs/heads/main'
  uses: actions/cache/save@v4
  with:
    path: rust/target/criterion/baseline
    key: criterion-baseline-${{ runner.os }}-${{ github.sha }}
```

### Pattern 3: Tiered Threshold Comparison
**What:** 5% = warning annotation, 10% = build failure
**When to use:** Required by user decision - per-benchmark evaluation
**Example:**
```bash
# Parse critcmp output and apply tiered thresholds
critcmp baseline current --export > comparison.json

# Check for regressions above thresholds
jq -r '
  .[] |
  select(.estimates.mean.percentage_change > 5) |
  if .estimates.mean.percentage_change > 10 then
    "FAIL: \(.name) regressed by \(.estimates.mean.percentage_change | round)%"
  else
    "WARN: \(.name) regressed by \(.estimates.mean.percentage_change | round)%"
  end
' comparison.json
```

### Pattern 4: PR Comment with Collapsible History
**What:** Update existing comment, collapse previous results
**When to use:** Required by user decision - maintain clean PR conversation
**Example:**
```yaml
# Source: https://github.com/peter-evans/create-or-update-comment
- name: Find existing comment
  uses: peter-evans/find-comment@v3
  id: fc
  with:
    issue-number: ${{ github.event.pull_request.number }}
    comment-author: 'github-actions[bot]'
    body-includes: '<!-- benchmark-results -->'

- name: Create or update comment
  uses: peter-evans/create-or-update-comment@v5
  with:
    comment-id: ${{ steps.fc.outputs.comment-id }}
    issue-number: ${{ github.event.pull_request.number }}
    body: |
      <!-- benchmark-results -->
      ## Benchmark Results

      ${{ steps.compare.outputs.summary }}

      <details>
      <summary>Previous results</summary>

      ${{ steps.fc.outputs.body }}
      </details>
    edit-mode: replace
```

### Pattern 5: Label Bypass for Accepted Regressions
**What:** Allow merge with `perf-regression-accepted` label
**When to use:** Required by user decision - escape hatch for intentional trade-offs
**Example:**
```yaml
# Source: https://github.com/orgs/community/discussions/26261
- name: Check for bypass label
  id: check-label
  run: |
    if [[ "${{ contains(github.event.pull_request.labels.*.name, 'perf-regression-accepted') }}" == "true" ]]; then
      echo "bypass=true" >> $GITHUB_OUTPUT
      echo "Regression accepted via label"
    else
      echo "bypass=false" >> $GITHUB_OUTPUT
    fi

- name: Fail on regression
  if: steps.compare.outputs.has_regression == 'true' && steps.check-label.outputs.bypass != 'true'
  run: exit 1
```

### Anti-Patterns to Avoid
- **Benchmarking on draft PRs:** Wastes CI resources, use `ready_for_review` trigger
- **Committing baselines to repo:** Creates merge conflicts, pollutes history
- **Running thorough mode in CI:** Too slow, use quick mode (50 samples) for both PR and baseline
- **Aggregating benchmark results:** Masks individual regressions, evaluate per-benchmark
- **Hardcoded thresholds in code:** Use config file for per-benchmark custom thresholds

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Baseline comparison | Parse Criterion JSON manually | critcmp | Handles edge cases, standard format |
| PR comment management | Direct GitHub API calls | peter-evans/create-or-update-comment | Handles find-and-update pattern |
| Cache between runs | Commit to repo or artifacts | actions/cache | Cross-branch access, 7-day retention |
| Percentage calculation | Manual math from times | critcmp JSON output | Already computed with statistical analysis |
| Ready-for-review detection | Polling PR state | `pull_request: types: [ready_for_review]` | Built into GitHub Actions |

**Key insight:** The benchmark infrastructure from Phase 13 (Criterion + critcmp) already handles the hard parts of statistical comparison. CI integration is primarily workflow orchestration and cache management, not benchmark analysis.

## Common Pitfalls

### Pitfall 1: Cache Key Collisions
**What goes wrong:** Multiple PRs overwrite each other's caches, baselines get corrupted
**Why it happens:** Using PR-specific keys for baselines that should be shared
**How to avoid:** Use branch-based keys (`criterion-baseline-${{ runner.os }}`) for baselines, not PR-based
**Warning signs:** Inconsistent comparison results across PRs

### Pitfall 2: Cache Scope Restrictions
**What goes wrong:** PRs cannot access main branch baseline cache
**Why it happens:** Caches created in PRs have limited scope
**How to avoid:** Create baseline cache on push to main, PRs restore (not save) with `restore-keys`
**Warning signs:** "Cache miss" messages on every PR run

### Pitfall 3: Missing Baseline on First Run
**What goes wrong:** PRs fail before any baseline exists
**Why it happens:** No main branch benchmark run has occurred yet
**How to avoid:** Skip comparison with warning when baseline cache misses, pass the check
**Warning signs:** All PRs failing with "baseline not found"

### Pitfall 4: GitHub Actions Runner Variance
**What goes wrong:** Benchmarks show 10-20% variance between runs
**Why it happens:** Shared CI infrastructure, variable load on runners
**How to avoid:** Use generous noise threshold (5% for warning, 10% for failure), note in PR comment
**Warning signs:** Flapping results (pass/fail on re-run without code changes)

### Pitfall 5: Comment Update Race Conditions
**What goes wrong:** Multiple concurrent pushes create duplicate comments
**Why it happens:** Find-comment runs before create-comment from another run completes
**How to avoid:** Use hidden HTML comment marker for identification, workflow concurrency limits
**Warning signs:** Multiple benchmark result comments on same PR

### Pitfall 6: Synchronize Event Without Ready-for-Review
**What goes wrong:** Benchmarks run on every push even for draft PRs
**Why it happens:** Using default `pull_request` triggers (opened, synchronize, reopened)
**How to avoid:** Explicitly specify `types: [ready_for_review]` OR add `if: !github.event.pull_request.draft` condition
**Warning signs:** Benchmark jobs running on draft PRs

## Code Examples

### Complete Benchmark Workflow
```yaml
# Source: Compiled from GitHub Actions documentation and community patterns
# .github/workflows/benchmarks.yml
name: Benchmark Regression Detection

on:
  pull_request:
    types: [ready_for_review]
    branches: [main]
  push:
    branches: [main]

env:
  BENCH_MODE: quick
  CARGO_TERM_COLOR: always

# Prevent concurrent benchmark runs for same PR
concurrency:
  group: benchmarks-${{ github.event.pull_request.number || github.sha }}
  cancel-in-progress: true

jobs:
  benchmark:
    name: Run Benchmarks
    runs-on: windows-latest
    timeout-minutes: 60

    # Skip draft PRs (belt and suspenders with ready_for_review)
    if: github.event_name == 'push' || !github.event.pull_request.draft

    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Cache cargo registry
        uses: actions/cache@v4
        with:
          path: ~/.cargo/registry
          key: ${{ runner.os }}-cargo-registry-${{ hashFiles('**/Cargo.lock') }}
          restore-keys: ${{ runner.os }}-cargo-registry-

      - name: Cache cargo build
        uses: actions/cache@v4
        with:
          path: rust/target
          key: ${{ runner.os }}-cargo-bench-${{ hashFiles('**/Cargo.lock') }}
          restore-keys: ${{ runner.os }}-cargo-bench-

      - name: Restore baseline cache
        id: baseline-cache
        uses: actions/cache/restore@v4
        with:
          path: rust/target/criterion/baseline
          key: criterion-baseline-${{ runner.os }}-dummy
          restore-keys: criterion-baseline-${{ runner.os }}

      - name: Install critcmp
        run: cargo install critcmp --locked

      - name: Run benchmarks
        working-directory: rust
        run: cargo bench -- --save-baseline current

      - name: Compare against baseline (PR only)
        if: github.event_name == 'pull_request'
        id: compare
        working-directory: rust
        shell: bash
        run: |
          if [ -d "target/criterion/baseline" ]; then
            # Run comparison
            critcmp baseline current > comparison.txt 2>&1 || true
            critcmp baseline current --export > comparison.json 2>&1 || true

            # Parse results for thresholds
            # ... (threshold parsing logic)

            echo "baseline_exists=true" >> $GITHUB_OUTPUT
          else
            echo "No baseline found - skipping comparison"
            echo "baseline_exists=false" >> $GITHUB_OUTPUT
          fi

      - name: Check for bypass label
        if: github.event_name == 'pull_request'
        id: check-label
        run: |
          if [[ "${{ contains(github.event.pull_request.labels.*.name, 'perf-regression-accepted') }}" == "true" ]]; then
            echo "bypass=true" >> $GITHUB_OUTPUT
          else
            echo "bypass=false" >> $GITHUB_OUTPUT
          fi
        shell: bash

      - name: Find existing comment
        if: github.event_name == 'pull_request'
        uses: peter-evans/find-comment@v3
        id: fc
        with:
          issue-number: ${{ github.event.pull_request.number }}
          comment-author: 'github-actions[bot]'
          body-includes: '<!-- benchmark-results -->'

      - name: Post benchmark results
        if: github.event_name == 'pull_request'
        uses: peter-evans/create-or-update-comment@v5
        with:
          comment-id: ${{ steps.fc.outputs.comment-id }}
          issue-number: ${{ github.event.pull_request.number }}
          body: |
            <!-- benchmark-results -->
            ## Benchmark Results

            **Status:** ${{ steps.compare.outputs.status || 'Comparison pending' }}

            ${{ steps.compare.outputs.summary }}
          edit-mode: replace

      - name: Update baseline (main only)
        if: github.ref == 'refs/heads/main'
        working-directory: rust
        run: |
          # Copy current results to baseline
          if [ -d "target/criterion/current" ]; then
            rm -rf target/criterion/baseline
            cp -r target/criterion/current target/criterion/baseline
          fi
        shell: bash

      - name: Save baseline cache (main only)
        if: github.ref == 'refs/heads/main'
        uses: actions/cache/save@v4
        with:
          path: rust/target/criterion/baseline
          key: criterion-baseline-${{ runner.os }}-${{ github.sha }}

      - name: Fail on regression
        if: |
          github.event_name == 'pull_request' &&
          steps.compare.outputs.has_failure == 'true' &&
          steps.check-label.outputs.bypass != 'true'
        run: |
          echo "Performance regression detected (>10%)"
          echo "Add label 'perf-regression-accepted' to merge with documented justification"
          exit 1
```

### Benchmark Threshold Configuration
```yaml
# rust/benchmark-config.yaml (optional per-benchmark thresholds)
# Default thresholds
defaults:
  warning_threshold: 5
  failure_threshold: 10

# Per-benchmark overrides for noisy benchmarks
overrides:
  yaml_parsing/parse/5000_lines:
    warning_threshold: 8
    failure_threshold: 15
    reason: "Large YAML parsing has high variance"

  file_io/read/encoding_detection:
    warning_threshold: 10
    failure_threshold: 20
    reason: "Encoding detection involves filesystem operations"
```

### PR Comment Formatting
```markdown
<!-- benchmark-results -->
## Benchmark Results

**Commit:** abc1234
**Baseline:** main @ def5678
**Mode:** quick (50 samples)

### Summary

| Status | Count |
|--------|-------|
| Regressions (>10%) | 0 |
| Warnings (5-10%) | 2 |
| Improved (<-5%) | 1 |
| Unchanged | 15 |

### Regressions

None

### Warnings

| Benchmark | Change | Current | Baseline |
|-----------|--------|---------|----------|
| yaml_parsing/parse/1000_lines | +7.2% | 1.23ms | 1.15ms |
| scanlog/extract_formids | +5.8% | 450us | 425us |

### Improvements

| Benchmark | Change | Current | Baseline |
|-----------|--------|---------|----------|
| file_io/read/small | -12.3% | 89us | 101us |

---
*Benchmarks run on GitHub Actions. Results may vary due to shared infrastructure.*
*To accept regressions, add label `perf-regression-accepted` with justification.*
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Commit baselines to repo | GitHub Actions cache | 2023+ | Cleaner git history, automatic cleanup |
| Manual baseline comparison | Automated CI detection | 2020+ | Catches regressions before merge |
| Single failure threshold | Tiered thresholds (warn/fail) | 2024+ | Reduces alert fatigue |
| Run all benchmarks | Filter by changed files | 2025+ | Faster CI, focused feedback |

**Deprecated/outdated:**
- `benchmark-action/github-action-benchmark` with GitHub Pages: Overkill for this use case, adds branch complexity
- Manual critcmp in local dev only: No automated protection against regressions
- `pull_request` without types filter: Runs on every push including drafts

## Open Questions

Things that couldn't be fully resolved:

1. **GitHub Actions Runner Variance**
   - What we know: Shared runners have variable performance (10-20% noise)
   - What's unclear: Whether quick mode (50 samples) provides sufficient statistical stability
   - Recommendation: Start with current thresholds (5%/10%), adjust based on false positive rate

2. **Cache Eviction Recovery**
   - What we know: GitHub Actions cache has 7-day retention and 10GB limit
   - What's unclear: Exact behavior when cache is evicted mid-week
   - Recommendation: Next main branch push re-establishes baseline, PRs warn until then (per user decision)

3. **Concurrent PR Baseline Conflicts**
   - What we know: Multiple PRs may run benchmarks simultaneously
   - What's unclear: Whether cache restore is atomic across concurrent jobs
   - Recommendation: Use `concurrency` group to prevent parallel benchmark runs for same PR

## Sources

### Primary (HIGH confidence)
- [GitHub Actions Events Documentation](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows) - pull_request types, ready_for_review
- [GitHub Actions Cache Documentation](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows) - Cache key matching, cross-branch access
- [critcmp GitHub](https://github.com/BurntSushi/critcmp) - Baseline comparison, JSON export
- [peter-evans/create-or-update-comment](https://github.com/peter-evans/create-or-update-comment) - PR comment management

### Secondary (MEDIUM confidence)
- [boa-dev/criterion-compare-action](https://github.com/boa-dev/criterion-compare-action) - Reference implementation
- [benchmark-action/github-action-benchmark](https://github.com/benchmark-action/github-action-benchmark) - Alternative approach
- [Bencher.dev GitHub Actions Guide](https://bencher.dev/docs/how-to/github-actions/) - Statistical benchmarking patterns

### Tertiary (LOW confidence)
- Community discussions on label-based job skipping
- Blog posts on GitHub Actions benchmark patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - GitHub Actions and critcmp are well-documented, stable
- Architecture: HIGH - Follows established patterns, integrates with existing infrastructure
- Pitfalls: HIGH - Common issues documented in GitHub community and official docs
- Threshold tuning: MEDIUM - May need adjustment based on observed variance

**Research date:** 2026-02-04
**Valid until:** 60 days (GitHub Actions API is stable)
