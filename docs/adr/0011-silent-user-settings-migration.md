# Migrate User Settings silently at startup

A User Settings document that requires migration (the flat `ClassicConfig` shape, an unversioned nested document, or the previous `CLASSIC Data/` location) is migrated without asking. Every frontend calls `classic_user_settings_core::migrate_if_required` once, before it first opens User Settings: the GUI, the TUI, and each CLI command that resolves an Installation Root. The transition presents nothing. There is no confirmation, no completion dialog, no restore offer, and no status-bar or status-line text, because the status bar is reserved for scan progress. A migration that cannot run is only logged (GUI `qWarning`, TUI `tracing`, CLI stderr). The document then stays read-only and is retried on the next start.

This supersedes the "adapters own consent" part of ADR-0004 for migration only. The prompt asked users a question they had no basis to answer: the plan was the only valid transition, and declining it just left their settings read-only. The prompt confused CLASSIC's audience more than it protected them. Everything else that made migration safe stays in the core and is unchanged. Planning is still pure. Apply still conflict-checks the planned revision, durably publishes and rereads a byte-exact content-addressed backup under `CLASSIC Backup/User Settings/Migrations/`, and rolls back a publication that fails verification. `UserSettings::open` and ordinary commits still never migrate, and the silent path never applies optional alias canonicalization to an already-current document or creates a missing one.

## Considered options

- **Keep a pre-apply confirmation in each frontend.** Rejected for the reason above. The GUI dialog was the only frontend prompt, the TUI needed a hidden `M` key in the Settings overlay, and the CLI never migrated at all, so the same installation behaved differently depending on which frontend started first.
- **Apply silently but keep a post-apply "Keep / Restore" dialog.** Rejected: it is still a migration prompt, and it reintroduces the question the change removes. Restore remains a core operation authorized by the migration receipt.
- **Migrate inside `UserSettings::open`.** Rejected: opens are read-only by contract (ADR-0004, ADR-0009), and scan launch, intake, and tests rely on that. A separate startup call keeps the write visible and in one place.

## Consequences

The CXX plan/apply/restore adapters and their DTOs lost their only caller and were removed under the consumer-driven bridge rule (ADR-0010), replaced by `user_settings_migrate_if_required`. The TUI's `M` key and its consumer obligation `tui.settings-migration-interaction` were replaced by `tui.settings-silent-migration`, and `tui.settings-startup` now asserts that no migration prompt appears. The core `user-settings.migrate` conformance scenarios are unchanged.
