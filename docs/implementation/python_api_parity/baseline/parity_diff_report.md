# Rust<->Python Parity Diff Baseline

- Generated: `2026-03-05T12:11:45.389628+00:00`
- Tier-1 contract rows: **10**
- Tier-1 matched: **10**
- Tier-1 missing Rust: **0**
- Tier-1 missing Python: **0**
- Tier-1 signature mismatch: **0**
- Total gaps (Tier-1 + Tier-2): **137**

## Tier-1 Contract Evaluation

| ID | Owner Module | Rust Symbol | Python Export | Status |
|---|---|---|---|---|
| `scanlog-logparser-class` | `scanlog` | `LogParser` | `classic_scanlog.LogParser` | `matched` |
| `scanlog-analysis-config-class` | `scanlog` | `AnalysisConfig` | `classic_scanlog.AnalysisConfig` | `matched` |
| `scanlog-orchestrator-class` | `scanlog` | `OrchestratorCore` | `classic_scanlog.Orchestrator` | `matched` |
| `scanlog-extract-formids-batch` | `scanlog` | `extract_formids_batch` | `classic_scanlog.extract_formids_batch` | `matched` |
| `config-yamldata-class` | `config` | `YamlDataCore` | `classic_config.YamlData` | `matched` |
| `config-create-yamldata` | `config` | `YamlDataCore` | `classic_config.create_yamldata` | `matched` |
| `config-clear-yaml-cache` | `config` | `clear_global_yaml_cache` | `classic_config.clear_yaml_cache` | `matched` |
| `version-registry-class` | `version_registry` | `VersionRegistry` | `classic_version_registry.VersionRegistry` | `matched` |
| `version-registry-get-singleton` | `version_registry` | `get_version_registry` | `classic_version_registry.get_version_registry` | `matched` |
| `version-registry-match-version` | `version_registry` | `VersionRegistry` | `classic_version_registry.match_version_string` | `matched` |

## Gap Counts By Owner/Tier

| Owner Module | Tier 1 Gaps | Tier 2 Gaps |
|---|---:|---:|
| `scanlog` | 0 | 95 |
| `config` | 0 | 10 |
| `version_registry` | 0 | 24 |
| `aux` | 0 | 8 |

Detailed per-gap diagnostics are in `parity_diff_report.json`.
