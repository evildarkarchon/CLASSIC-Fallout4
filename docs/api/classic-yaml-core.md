# `classic-yaml-core` API Guide (retired)

**This crate no longer exists.** It was absorbed into `classic-settings-core` during Phase 1 of the v9.1.0 consolidation milestone. Every symbol it used to own — `YamlOperations`, the path-backed mtime-aware file cache, `merge_keys()`, `clear_global_yaml_cache()`, and `yaml_cache_stats()` — is now re-exported from the `classic-settings-core` crate root. All of them have since moved again, to [`classic_shared_core::yaml`](classic-shared-core.md#generic-yaml-yaml) (`merge_keys()` and `YamlError` in issue #239, `YamlOperations` and its file cache in issue #240); `classic-settings-core` still re-exports them.

Go to [`classic-shared-core.md`](classic-shared-core.md#yamloperations). The absorbed surface is documented there under **`YamlOperations`** and **YAML-file cache**, including the contrast between the path-keyed `YamlOperations` cache and the key-based logical-key cache.

This page is kept only so older inbound links resolve. It is not maintained, and it is intentionally absent from the ordered index in [`README.md`](README.md).

> Historical note: the previous revision of this page documented the crate under the retired `ClassicLib-rs/...` path root. See the [workspace migration matrix](../workspace-migration-matrix.md) for path translation.

Reference: [`AGENTS.md`](../../AGENTS.md).
