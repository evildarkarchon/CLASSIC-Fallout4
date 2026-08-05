# `classic-durable-publication` Internal API Guide

Contributor-facing architecture notes for [`business-logic/classic-durable-publication/`](../../business-logic/classic-durable-publication).

This `publish = false` business-logic crate owns **Durable Publication**: making complete bytes visible at a canonical path such that a crash cannot leave partial content behind. It exists so that a durability defect has exactly one place to be found and fixed, rather than three.

It sits under `business-logic/` rather than `foundation/` because all of its intended consumers are business-logic crates. Putting it in `classic-shared-core` was rejected: that crate is re-exported to Python and would therefore publish an implementation seam.

## Public workspace API

- `publish(target, bytes, lock)` stages, synchronizes, and atomically replaces whatever is at `target`. It returns a `Publication` carrying the published `ContentIdentity` and a `Durability` outcome.
- `publish_with_verified_backup(target, bytes, backup, lock)` publishes a backup to a path that must not already exist, rereads it from disk, byte-compares it against the caller's retained original, and only then replaces `target`. It returns a `VerifiedBackupPublication` carrying the verified backup identity and the replacement `Publication`.
- `publish_verified_backup(backup)` is the first half of that on its own, returning the `ContentIdentity` of the *reread* bytes. It exists for the caller whose conflict policy must run between the verification and the replacement: `classic-config-core`'s Local Ignore reset rechecks the canonical bytes after the backup exists, so that a user edit landing during backup publication is reported as a conflict — naming the backup that was already retained — rather than being overwritten. That caller then calls `publish` itself.
- `stage(target, bytes)` stops one step short of `publish`, returning a `StagedPublication` whose `publish()` performs only the final move. It exists so a caller's own last-moment check can sit in the narrowest possible window: `classic-config-core`'s Local Ignore reset stages the defaults, rereads and byte-compares the canonical file against what the user approved, and then publishes, so nothing but the move separates the check from the replacement. That path holds no lock against a non-CLASSIC writer such as the user's own editor, which is exactly why the width of that window is the guarantee.
- `ContentIdentity::from_bytes(bytes)` calculates a SHA-256 digest plus byte length; `sha256_hex()` renders the digest on demand.
- `Durability::Durable | Durability::Unknown(io::Error)` reports whether the published namespace entry reached the platform's durability barrier.
- `LockPolicy::none() | LockPolicy::sibling(suffix) | LockPolicy::at(path)` selects the cross-process lock, and `lock_path(target)` exposes the derived path.
- `PublicationStage::{Create, Write, Flush, Sync, Publish}` is the workspace's single publication stage vocabulary.
- `PublicationError` is the neutral typed failure; `stage()`, `path()`, and `io_source()` are its accessors.

These are separate named operations over one shared implementation rather than one operation with a policy struct. A five-field policy matrix would make the interface nearly as complex as the mechanism underneath it. A third operation, `install_verified`, is planned and arrives with the caller that needs it.

## The sequence

1. **Create** a staging file in the target's *own* directory, so the final move is same-volume and therefore atomic.
2. **Write** the complete bytes into it.
3. **Flush** them out of user space.
4. **Sync** the staging file to the platform's durability barrier.
5. **Publish** it onto the final path.

Nothing is visible at the target until step 5, and step 5 only ever moves a file whose bytes are already complete and synchronized.

## Contracts

- `publish` **always** returns a durability outcome. The crate never decides whether that outcome matters; callers do. `Publication` and `VerifiedBackupPublication` are `#[must_use]` precisely so a durability outcome cannot be dropped by omission: a caller that deliberately discards it must write that down, ideally via `Publication::into_durability()`.
- On Unix, publication is `rename` followed by an explicit parent-directory synchronization. Those are separable events, which is the only reason durability uncertainty can be modelled at all: bytes are visible as soon as the rename returns, but the directory entry is not guaranteed to survive a crash until the synchronization succeeds. A failure there is returned as `Durability::Unknown`, never as an error — reporting it as a failure would falsely imply the previous content survived.
- On Windows, publication is a write-through `MoveFileEx`. **The staged file's temporary attribute must be cleared before that move**, which is what `NamedTempFile::keep()` does. A file still carrying `FILE_ATTRIBUTE_TEMPORARY` may never be written back by the cache manager, which would defeat the write-through move entirely. Do not replace that call with a plain rename of `staged.path()`.
- A clobbering replacement and a unique-path publication are distinct. `publish` replaces; the backup half — whether reached through `publish_with_verified_backup` or `publish_verified_backup` — refuses to overwrite and surfaces an existing path as a `Publish`-stage failure with an `AlreadyExists` source.
- The verified-backup ordering is publish → reread from disk → byte-compare → abort on mismatch. The reread exists because a backup that silently failed to write is indistinguishable from a good one until it is read back. Aborting is what prevents an accepted recovery from destroying the only copy of a user's data.
- Failures are neutral: a stage, a path, and a source error, with no dependency on any caller's error type. Each caller maps them onto its own existing stable error codes, so adopting this crate requires no binding parity refresh.
- This crate is workspace-internal and has no C++, Node, or Python surface. It is deliberately absent from the binding parity matrix and from the Python, Node, and CXX parity baseline generators.

## Concurrency

The concurrency contract is stated on the interface so a reader does not have to read the implementation to know what locks.

- `LockPolicy::sibling(suffix)` acquires an exclusive cross-process lock on `<target><suffix>` *before* any staging, holds it for the whole sequence, and releases it when the call returns. This covers `.commit.lock` in `classic-user-settings-core` and `.install.lock` in `classic-file-io-core`.
- `LockPolicy::at(path)` locks exactly the path the caller derived, for a lock that a sibling suffix cannot express — a fixed name several directories above the target, for instance. **It currently has no production caller.** It was added for `classic-config-core`'s Local Ignore reset lock, which is exactly that shape; migrating that caller showed the lock has to span its conflict check, its verified backup, its recheck, and its replacement, which is wider than any single operation here can lock, so the caller kept its own lock and this policy went unused. Retain or delete it when the remaining callers migrate — do not treat its presence as evidence that a caller needs it.
- For `publish_with_verified_backup`, the single lock spans the backup publish, the reread, the comparison, and the replacement, so a backup cannot be verified against one target state and then applied to another.
- The lock is always taken on the **target** path, never on the backup path.
- `LockPolicy::none()` takes no lock. Concurrent writers may race for the final publish; the loser's bytes are discarded and whichever bytes win are complete. This policy also places no new file beside user-editable data.
- `publish_verified_backup` and `stage` take no `LockPolicy` at all. A lock scoped to either alone would release before the move it exists to guard, which is precisely the window a lock closes, so a caller that splits the sequence must hold its own lock across every part. `classic-config-core`'s Local Ignore reset does exactly that: it holds its own `.classic-local-ignore-reset.lock` — a fixed name two directories above the target, unchanged from before the migration — across its conflict check, the verified backup, the recheck, and the replacement, and so takes no lock through this crate at all. No new file appears beside the user's editable data.
- Lock files are never removed. Deleting one races with any process that has opened the path but not yet acquired it.

The lock uses the standard library's `File::lock` rather than `fs4`'s `lock_exclusive`, which two of the three existing call sites use today. Both wrap `flock` on Unix and `LockFileEx` on Windows, so the choice is not about behavior: `File::lock` is stable well below this workspace's `rust-version`, so the one implementation that replaces two needs nothing beyond the standard library. Lock *filenames* stay caller policy, so adopting this crate changes nothing on disk for any caller.

## What this crate does not own

- **Backup location.** Callers supply backup paths through `VerifiedBackup::new`.
- **Conflict and revision policy.** Revision anchoring for User Settings and exact-byte identity checks for Local Ignore YAML Data stay with their owning modules.
- **Rollback generations.** The `.prev` convention is YAML Data Update Channel policy and will live only in `install_verified`, which is how ADR-0006's prohibition for Local Ignore YAML Data is preserved structurally rather than by convention.

## Testing

The crate's public interface is the workspace's single seam for provoking durability failures. Its tests use real filesystem conditions: a missing parent directory, a parent path that is a regular file, a read-only parent (Unix), a read-only replacement destination (Windows), and a backup path that already exists.

Two outcomes have no portable filesystem condition that provokes them on demand, and are driven by `cfg(test)`-only thread-local hooks that are not part of the crate's interface:

- A directory-synchronization failure. `fsync` on a directory handle does not fail to order, yet `Durability::Unknown` is the one outcome every caller must handle.
- A published backup whose bytes on disk differ from what was written. That is precisely a filesystem or device that lied about a completed write, which no cooperating filesystem will reproduce.

Callers testing their own stage-to-error-code mapping should use a fake at their own seam. The injection points here are deliberately not exposed on this crate's interface just because tests once used them.
