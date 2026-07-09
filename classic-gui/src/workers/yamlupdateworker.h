#pragma once

#include <QMetaType>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QVector>

/// Flat, Qt-native result of a YAML-update check call. Produced on the
/// worker thread and consumed on the UI thread via a queued `checkFinished`
/// signal. We convert away from the CXX DTO here (which carries
/// `rust::String` / `rust::Vec` internally) so the UI-layer code does not
/// need to include the bridge headers.
struct YamlCheckResult {
    /// One of: `"disabled"`, `"updateAvailable"`, `"upToDate"`,
    /// `"unknown"`, `"error"`. Matches the bridge tag semantics.
    QString status;
    QString releaseTag;
    QStringList compatibleFileNames;
    /// SHA-256 digests for `compatibleFileNames`, aligned by index.
    QStringList compatibleFileSha256;
    /// Files the published manifest advertised that this client cannot
    /// install — e.g., a newer MAJOR schema or a file outside the client's
    /// accepted range. Populated on both `updateAvailable` and `upToDate`
    /// so the UI can tell the user "newer data exists but your build is
    /// too old" instead of misreporting `upToDate` when the manifest only
    /// contains future-schema entries. Parallel-indexed with
    /// `incompatibleReasons`.
    QStringList incompatibleFileNames;
    QStringList incompatibleReasons;
    /// Short diagnostic text for `"unknown"` and `"error"` branches.
    QString detail;
};

/// Flat, Qt-native result of an apply call.
struct YamlApplyResult {
    qsizetype installed = 0;
    qsizetype failed = 0;
    QString firstFailureReason;
    /// Populated by the bridge for special-case errors
    /// (`update check disabled`, `decision stale`, transport failures).
    /// Empty for ordinary mixed-outcome batches.
    QString errorMessage;
};

/// Flat, Qt-native result of a rollback batch. The worker aggregates the
/// per-file outcomes into three string lists so the UI can summarize them
/// in a single status line without another round-trip.
struct YamlRollbackResult {
    /// Names of files that were actually rolled back.
    QStringList rolledBack;
    /// Files that had no `.prev` sibling — not an error, just nothing to
    /// do. Surfaced for diagnostic purposes only.
    QStringList noPreviousVersion;
    /// Files that failed outright, each rendered as `"<file>: <reason>"`.
    QStringList errors;
};

Q_DECLARE_METATYPE(YamlCheckResult)
Q_DECLARE_METATYPE(YamlApplyResult)
Q_DECLARE_METATYPE(YamlRollbackResult)

/// Background worker that runs the first-party YAML Data bridge calls off the
/// Qt UI thread.
///
/// Why it exists: the bridge calls block on the shared Tokio runtime and
/// can stall for tens of seconds on slow networks (Pages 5s + API 30s +
/// asset download). Running them on the UI thread freezes the modal
/// Settings dialog precisely on the failure paths where the user most
/// needs feedback. This worker serializes those calls onto a dedicated
/// `QThread`, keeping the dialog responsive and enabling a stable
/// "in progress" label during long waits.
class YamlUpdateWorker : public QObject {
    Q_OBJECT

public:
    explicit YamlUpdateWorker(QObject* parent = nullptr);

public slots:
    /// Run `classic::update::yaml_data_check_update`. Emits `checkFinished`.
    ///
    /// Rust owns the first-party channel recipe and schema metadata, so the UI
    /// slot only needs to pass the on/off setting.
    void doCheck(bool enabled);

    /// Run `classic::update::yaml_data_apply_update` against a reviewed
    /// decision. Emits `applyFinished`.
    void doApply(bool enabled, const QString& approvedReleaseTag,
                 const QStringList& approvedFileNames,
                 const QStringList& approvedFileSha256);

    /// Run `classic::update::yaml_data_rollback_update`, letting Rust expand
    /// the current first-party shippable file list. Emits `rollbackFinished`
    /// with the aggregate result.
    void doRollback();

signals:
    void checkFinished(YamlCheckResult result);
    void applyFinished(YamlApplyResult result);
    void rollbackFinished(YamlRollbackResult result);
};
