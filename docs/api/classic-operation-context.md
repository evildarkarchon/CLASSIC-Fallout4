# `classic-operation-context` Internal API Guide

Contributor-facing architecture notes for [`foundation/classic-operation-context/`](../../foundation/classic-operation-context).

This `publish = false` foundation crate carries per-operation controls across Rust crate boundaries without creating process-global state or expanding binding-facing business APIs. It does not create, configure, or own a Tokio runtime.

## Public workspace API

- `scope_cancellation(cancellation, future)` polls one future inside an optional task-local `Arc<AtomicBool>` cancellation scope.
- `cancellation_requested()` reads the current scope with acquire ordering and returns `false` outside a scope.

The `Arc<AtomicBool>` is the existing provisional scan-run control representation. The flag is monotonic for a run: callers may change it from `false` to `true`, but must not reset it while a scoped operation is active.

## Contracts

- Scope state is restored on every future poll, so concurrently polled operations remain isolated even when they share an executor task.
- Nested or concurrent scopes do not use process-global mutable state.
- The scope carries control only. It does not abort or drop futures; participating code checks the flag at explicit safe seams.
- Code outside a scope retains its ordinary uncancelled behavior.
- This crate is workspace-internal and has no C++, Node, or Python surface. User-facing cancellation remains owned by the high-level Crash Log Scan Run contract.

The current consumer is `classic-scanlog-core`. Its scan service scopes source discovery, and its `log_collection` module (Crash Log collection and Targeted input resolution, moved from `classic-file-io-core` in #254) checks the scope between completed directory/file operations and enumeration entries. Partial discovery accumulators are discarded by the collection implementation; the scan service checks the same monotonic flag before publishing discovery. `classic-file-io-core` no longer depends on this crate.

## Runtime ownership

`tokio::task_local!` associates state with a polled future but does not create a runtime. Callers continue to use the single shared runtime documented in [`classic-shared-core.md`](classic-shared-core.md) and [`AGENTS.md`](../../AGENTS.md).
