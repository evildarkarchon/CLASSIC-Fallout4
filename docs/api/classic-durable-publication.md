# `classic-durable-publication` Internal API Guide

Contributor-facing architecture notes for [`business-logic/classic-durable-publication/`](../../business-logic/classic-durable-publication).

This `publish = false` business-logic crate owns **Durable Publication**: making complete bytes visible at a canonical path such that a crash cannot leave partial content behind. It exists so that a durability defect has exactly one place to be found and fixed, rather than three.

It sits under `business-logic/` rather than `foundation/` because all of its intended consumers are business-logic crates. Putting it in `classic-shared-core` was rejected: that crate is re-exported to Python and would therefore publish an implementation seam.

## Public workspace API

- `publish(target, bytes, lock)` stages, synchronizes, and atomically replaces whatever is at `target`. It returns a `Publication` carrying the published `ContentIdentity` and a `Durability` outcome.
- `publish_with_verified_backup(target, bytes, backup, lock)` publishes a backup to a path that must not already exist, rereads it from disk, byte-compares it against the caller's retained original, and only then replaces `target`. It returns a `VerifiedBackupPublication` carrying the verified backup identity and the replacement `Publication`.
- `publish_verified_backup(backup)` is the first half of that on its own, returning the `ContentIdentity` of the *reread* bytes. It exists for the caller whose conflict policy must run between the verification and the replacement: `classic-config-core`'s Local Ignore reset rechecks the canonical bytes after the backup exists, so that a user edit landing during backup publication is reported as a conflict — naming the backup that was already retained — rather than being overwritten. That caller then calls `publish` itself.
- `stage(target, bytes)` stops one step short of `publish`, returning a `StagedPublication` whose `publish()` performs only the final move. It exists so a caller's own last-moment check can sit in the narrowest possible window: `classic-config-core`'s Local Ignore reset stages the defaults, rereads and byte-compares the canonical file against what the user approved, and then publishes, so nothing but the move separates the check from the replacement. That path holds no lock against a non-CLASSIC writer such as the user's own editor, which is exactly why the width of that window is the guarantee.
- `install_verified(target, staged, expected_sha256, lock)` adopts a file the caller already wrote to disk, verifies its SHA-256 against `expected_sha256` case-insensitively, deletes it and aborts on mismatch, synchronizes it, rotates an existing `target` to its rollback generation, and moves the staged file into place. It returns an `Install` carrying the verified `ContentIdentity`, whether a rollback generation was created, and a `Durability` outcome. It is the only operation here that starts from bytes this crate did not write, and the only one that can create a rollback generation.
- `rollback_generation_path(target)` returns the `<target>.prev` path `install_verified` uses. It exists so the operations that *consume* a rollback generation agree with the one that creates it by construction rather than by both spelling the suffix.
- `ContentIdentity::from_bytes(bytes)` calculates a SHA-256 digest plus byte length; `from_reader(reader)` does the same by streaming, for content that is already on disk; `sha256_hex()` renders the digest on demand; `matches_sha256_hex(expected)` compares against an expected digest ignoring letter case.
- `Durability::Durable | Durability::Unknown(io::Error)` reports whether the published namespace entry reached the platform's durability barrier.
- `LockPolicy::none() | LockPolicy::sibling(suffix) | LockPolicy::at(path)` selects the cross-process lock, `lock_path(target)` exposes the derived path, and `acquire(target)` takes it directly, returning a `PublicationLock` guard.
- `PublicationStage::{Create, Write, Flush, Sync, Publish}` is the workspace's single publication stage vocabulary. No caller defines a second one. `classic-config-core` publishes it under the name `LocalIgnoreResetPublicationStage`, an alias whose variants were always spelled identically; `classic-user-settings-core` uses this type directly and adds only its own stage-to-error-code projection, because it publishes `commit_replace_failed` for terminal `Publish`. Renaming a variant here therefore moves a binding-visible contract — the CXX bridge's frozen FFI enum, the Node string enum, and the Python stage tokens all derive from these five spellings.
- `PublicationError` is the neutral typed failure; `stage()`, `path()`, and `io_source()` are its accessors.

These are separate named operations over one shared implementation rather than one operation with a policy struct. A five-field policy matrix would make the interface nearly as complex as the mechanism underneath it.

`install_verified` takes a path rather than bytes because its caller — the **YAML Data Update Channel** — streams a downloaded asset to disk before it knows whether the bytes are trustworthy. That shifts one precondition onto the caller which the other operations guarantee for themselves: the staged file must live in `target`'s own directory, or the final move is not same-volume and therefore not atomic. `classic-file-io-core` validates that before calling, because it is the only party that can.

## The sequence

1. **Create** a staging file in the target's *own* directory, so the final move is same-volume and therefore atomic.
2. **Write** the complete bytes into it.
3. **Flush** them out of user space.
4. **Sync** the staging file to the platform's durability barrier.
5. **Publish** it onto the final path.

Nothing is visible at the target until step 5, and step 5 only ever moves a file whose bytes are already complete and synchronized.

## Contracts

- `publish` and `install_verified` **always** return a durability outcome. The crate never decides whether that outcome matters; callers do. `Publication`, `VerifiedBackupPublication`, and `Install` are `#[must_use]` precisely so a durability outcome cannot be dropped by omission: a caller that deliberately discards it must write that down, ideally via `Publication::into_durability()` or `Install::into_durability()`. `classic-file-io-core`'s atomic install and `classic-user-settings-core`'s publisher are such callers — surfacing uncertainty in either would need new stable codes across three bindings — and both name the discard rather than omitting an error check.
- On Unix, publication is `rename` followed by an explicit parent-directory synchronization. Those are separable events, which is the only reason durability uncertainty can be modelled at all: bytes are visible as soon as the rename returns, but the directory entry is not guaranteed to survive a crash until the synchronization succeeds. A failure there is returned as `Durability::Unknown`, never as an error — reporting it as a failure would falsely imply the previous content survived.
- On Windows, publication is a write-through `MoveFileEx`. **The staged file's temporary attribute must be cleared before that move**, which is what `NamedTempFile::keep()` does. A file still carrying `FILE_ATTRIBUTE_TEMPORARY` may never be written back by the cache manager, which would defeat the write-through move entirely. Do not replace that call with a plain rename of `staged.path()`.
- A clobbering replacement and a unique-path publication are distinct. `publish` replaces; the backup half — whether reached through `publish_with_verified_backup` or `publish_verified_backup` — refuses to overwrite and surfaces an existing path as a `Publish`-stage failure with an `AlreadyExists` source. That makes the backup operations usable only by callers whose backup paths really are unique per publication. `classic-user-settings-core` is not one of them: its migration and legacy-import backups are content-addressed, so the same original bytes always resolve to the same backup path, and republishing over it is a supported outcome rather than a conflict. That caller therefore publishes its backups through `publish` and keeps its own reread-and-byte-compare, which is the same ordering with a clobbering publish step.
- The verified-backup ordering is publish → reread from disk → byte-compare → abort on mismatch. The reread exists because a backup that silently failed to write is indistinguishable from a good one until it is read back. Aborting is what prevents an accepted recovery from destroying the only copy of a user's data.
- A digest mismatch in `install_verified` **deletes the staged file** before returning `PublicationError::DigestMismatch`, and touches nothing else — the target and any existing rollback generation are exactly as they were. Deleting is the point: bytes that failed verification must not survive under a name the caller chose for a payload it trusted.
- `install_verified` writes the rollback generation *before* it replaces the target, not after. A failure at the final move therefore leaves the target absent with its previous content in `<target>.prev`, which is precisely the state self-heal promotes. The reverse order would have no recoverable failure point.
- Failures are neutral: a stage, a path, and a source error, with no dependency on any caller's error type. Each caller maps them onto its own existing stable error codes, so adopting this crate requires no binding parity refresh.
- This crate is workspace-internal and has no C++, Node, or Python surface. It is deliberately absent from the binding parity matrix and from the Python, Node, and CXX parity baseline generators.

## Concurrency

The concurrency contract is stated on the interface so a reader does not have to read the implementation to know what locks.

- `LockPolicy::sibling(suffix)` acquires an exclusive cross-process lock on `<target><suffix>` *before* any staging, holds it for the whole sequence, and releases it when the call returns. This covers `.commit.lock` in `classic-user-settings-core` and `.install.lock` in `classic-file-io-core`. `classic-user-settings-core` builds that sibling policy but takes it through `acquire` rather than through a publish operation, because a migration or import sequence publishes a backup and a document under one lock; its publications then pass `LockPolicy::none()`.
- `LockPolicy::at(path)` locks exactly the path the caller derived, for a lock that a sibling suffix cannot express — a fixed name several directories above the target, for instance. **It currently has no production caller.** It was added for `classic-config-core`'s Local Ignore reset lock, which is exactly that shape; migrating that caller showed the lock has to span its conflict check, its verified backup, its recheck, and its replacement, which is wider than any single operation here can lock, so the caller kept its own lock and this policy went unused. Retain or delete it when the remaining callers migrate — do not treat its presence as evidence that a caller needs it.
- For `publish_with_verified_backup`, the single lock spans the backup publish, the reread, the comparison, and the replacement, so a backup cannot be verified against one target state and then applied to another.
- The lock is always taken on the **target** path, never on the backup path.
- `LockPolicy::none()` takes no lock. Concurrent writers may race for the final publish; the loser's bytes are discarded and whichever bytes win are complete. This policy also places no new file beside user-editable data.
- `publish_verified_backup` and `stage` take no `LockPolicy` at all. A lock scoped to either alone would release before the move it exists to guard, which is precisely the window a lock closes, so a caller that splits the sequence must hold its own lock across every part. `classic-config-core`'s Local Ignore reset does exactly that: it holds its own `.classic-local-ignore-reset.lock` — a fixed name two directories above the target, unchanged from before the migration — across its conflict check, the verified backup, the recheck, and the replacement, and so takes no lock through this crate at all. No new file appears beside the user's editable data.
- `LockPolicy::acquire` is public so that a caller's *neighbouring* operations — ones that publish nothing but move the same files an install moves — can serialize against it on the same lock file. `classic-file-io-core`'s `rollback` and `self_heal` are such callers: they swap or promote `<target>.prev` and must not interleave with an install's rotation. `classic-user-settings-core` uses it for the related reason that its lock has to span more than one publication plus the reopen-and-verify steps between them. Using this rather than a second hand-rolled lock is what keeps the workspace at one cross-process lock implementation; it is also what let `classic-file-io-core` drop its `fs4` dependency entirely.
- Lock files are never removed. Deleting one races with any process that has opened the path but not yet acquired it.

The lock uses the standard library's `File::lock` rather than `fs4`'s `lock_exclusive`, which the original call sites used. Both wrap `flock` on Unix and `LockFileEx` on Windows, so the choice is not about behavior: `File::lock` is stable well below this workspace's `rust-version`, so the one implementation that replaces two needs nothing beyond the standard library. Lock *filenames* stay caller policy, so adopting this crate changes nothing on disk for any caller.

## What this crate does not own

- **Backup location.** Callers supply backup paths through `VerifiedBackup::new`.
- **Conflict and revision policy.** Revision anchoring for User Settings and exact-byte identity checks for Local Ignore YAML Data stay with their owning modules.
- **Rollback generations.** The `.prev` convention is YAML Data Update Channel policy and lives only in `install_verified`, which is how ADR-0006's prohibition for Local Ignore YAML Data is preserved structurally rather than by convention. The suffix appears exactly once in this crate, and `publish` and `publish_with_verified_backup` cannot reach it — the Local Ignore path could not create a rollback generation even if a future contributor wanted it to. A test asserts that.

## Testing

The crate's public interface is the workspace's single seam for provoking durability failures. Its tests use real filesystem conditions: a missing parent directory, a parent path that is a regular file, a read-only parent (Unix), a read-only replacement destination (Windows), a backup path that already exists, an unreadable staged file, and a staged file whose digest does not match.

Two outcomes have no portable filesystem condition that provokes them on demand, and are driven by `cfg(test)`-only thread-local hooks that are not part of the crate's interface:

- A directory-synchronization failure. `fsync` on a directory handle does not fail to order, yet `Durability::Unknown` is the one outcome every caller must handle.
- A published backup whose bytes on disk differ from what was written. That is precisely a filesystem or device that lied about a completed write, which no cooperating filesystem will reproduce.

Callers testing their own stage-to-error-code mapping should use a fake at their own seam. The injection points here are deliberately not exposed on this crate's interface just because tests once used them.
