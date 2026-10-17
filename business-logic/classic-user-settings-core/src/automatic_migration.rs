//! Silent, startup-time application of a required User Settings migration.
//!
//! Frontends call [`migrate_if_required`] once, before they first open User Settings, so a
//! document in a legacy shape or location transitions to the canonical store without asking the
//! user anything. The transition reuses the explicit plan/apply pipeline unchanged: the original
//! bytes are retained as a verified backup before publication, and a failed publication is rolled
//! back by the core. Ordinary [`UserSettings::open`] calls and commits still never migrate.

use crate::{
    CommitEligibility, MigrationDiagnostic, MigrationPlanningOutcome, Revision, UserSettings,
    UserSettingsMigrationApplyOutcome, UserSettingsMigrationError, UserSettingsMigrationReceipt,
};
use std::path::Path;

/// Result of silently applying a required User Settings migration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AutomaticMigrationOutcome {
    /// The document is missing, current, or only eligible for optional canonicalization, so
    /// nothing was written.
    NotRequired,
    /// The required migration was published and reopened; the receipt names the verified backup.
    Applied(UserSettingsMigrationReceipt),
    /// The document requires migration but no trusted migration edge exists, so it stays
    /// read-only and nothing was written.
    Unavailable(Vec<MigrationDiagnostic>),
    /// Another process changed the document between planning and publication, so nothing was
    /// written. The next startup retries against the new revision.
    Conflict {
        /// Revision the migration was planned against.
        expected_revision: Revision,
        /// Revision found after acquiring cross-process coordination.
        actual_revision: Revision,
    },
    /// Backup, publication, or verification failed; the core rolled back any publication.
    Failed(UserSettingsMigrationError),
}

/// Applies the required User Settings migration at `classic_root`, if there is one.
///
/// Only documents whose commit eligibility is [`CommitEligibility::RequiresMigration`] are
/// touched; optional alias canonicalization of an already-current document is left for an
/// explicit plan. Every outcome other than [`AutomaticMigrationOutcome::Applied`] leaves the
/// filesystem as it was, so callers may report non-applied outcomes as diagnostics and continue
/// with an ordinary open.
pub fn migrate_if_required(classic_root: impl AsRef<Path>) -> AutomaticMigrationOutcome {
    let classic_root = classic_root.as_ref();
    let settings = UserSettings::open(classic_root);
    if settings.commit_eligibility() != CommitEligibility::RequiresMigration {
        return AutomaticMigrationOutcome::NotRequired;
    }
    let plan = match settings.plan_migration() {
        MigrationPlanningOutcome::Planned(plan) if plan.required() => plan,
        // An optional-only plan cannot clear a migration requirement; treat it like no plan.
        MigrationPlanningOutcome::Planned(_) | MigrationPlanningOutcome::NotRequired => {
            return AutomaticMigrationOutcome::NotRequired;
        }
        MigrationPlanningOutcome::Unsupported(diagnostics) => {
            return AutomaticMigrationOutcome::Unavailable(diagnostics);
        }
    };
    match plan.apply(classic_root) {
        Ok(UserSettingsMigrationApplyOutcome::Applied(receipt)) => {
            AutomaticMigrationOutcome::Applied(receipt)
        }
        Ok(UserSettingsMigrationApplyOutcome::Conflict {
            expected_revision,
            actual_revision,
        }) => AutomaticMigrationOutcome::Conflict {
            expected_revision,
            actual_revision,
        },
        Err(error) => AutomaticMigrationOutcome::Failed(error),
    }
}
