#include "yamlupdateworker.h"

#include "core/rust_qt_bridge.h"

#include "classic_cxx_bridge/update.h"
#include "rust/cxx.h"

#include <cstdint>
#include <exception>
#include <string>

namespace {

// Kept in lockstep with the bridge discriminator constants in
// `cpp-bindings/classic-cpp-bridge/src/update.rs`. Duplicated rather than
// cross-included so the worker does not pull in the full settings-dialog
// translation unit.
constexpr std::uint32_t kYamlTagDisabled = 0u;
constexpr std::uint32_t kYamlTagUpdateAvailable = 1u;
constexpr std::uint32_t kYamlTagUpToDate = 2u;
constexpr std::uint32_t kYamlTagUnknown = 3u;
constexpr std::uint32_t kYamlTagError = 4u;

} // namespace

YamlUpdateWorker::YamlUpdateWorker(QObject* parent)
    : QObject(parent)
{
}

void YamlUpdateWorker::doCheck(bool enabled)
{
    YamlCheckResult result;
    try {
        auto status = classic::update::yaml_data_check_update(enabled);

        switch (status.tag) {
        case kYamlTagDisabled:
            result.status = QStringLiteral("disabled");
            break;
        case kYamlTagUpdateAvailable:
            result.status = QStringLiteral("updateAvailable");
            result.releaseTag = classic::toQString(status.release_tag);
            result.compatibleFileNames.reserve(
                static_cast<int>(status.compatible_files.size()));
            result.compatibleFileSha256.reserve(
                static_cast<int>(status.compatible_files.size()));
            for (const auto& f : status.compatible_files) {
                result.compatibleFileNames.push_back(classic::toQString(f.name));
                result.compatibleFileSha256.push_back(classic::toQString(f.sha256));
            }
            result.incompatibleFileNames.reserve(
                static_cast<int>(status.incompatible_files.size()));
            result.incompatibleReasons.reserve(
                static_cast<int>(status.incompatible_reasons.size()));
            for (std::size_t i = 0; i < status.incompatible_files.size(); ++i) {
                result.incompatibleFileNames.push_back(
                    classic::toQString(status.incompatible_files[i].name));
                result.incompatibleReasons.push_back(
                    i < status.incompatible_reasons.size()
                        ? classic::toQString(status.incompatible_reasons[i])
                        : QString());
            }
            break;
        case kYamlTagUpToDate:
            result.status = QStringLiteral("upToDate");
            result.releaseTag = classic::toQString(status.release_tag);
            // Also carry incompatible-file diagnostics on upToDate. The core
            // status model reports these even when no compatible file is
            // newer, so the UI can distinguish "genuinely in sync" from
            // "newer feed exists but this client cannot consume it".
            result.incompatibleFileNames.reserve(
                static_cast<int>(status.incompatible_files.size()));
            result.incompatibleReasons.reserve(
                static_cast<int>(status.incompatible_reasons.size()));
            for (std::size_t i = 0; i < status.incompatible_files.size(); ++i) {
                result.incompatibleFileNames.push_back(
                    classic::toQString(status.incompatible_files[i].name));
                result.incompatibleReasons.push_back(
                    i < status.incompatible_reasons.size()
                        ? classic::toQString(status.incompatible_reasons[i])
                        : QString());
            }
            break;
        case kYamlTagUnknown:
            result.status = QStringLiteral("unknown");
            result.detail = classic::toQString(status.unknown_reason);
            break;
        case kYamlTagError:
            result.status = QStringLiteral("error");
            result.detail = classic::toQString(status.error_message);
            break;
        default:
            result.status = QStringLiteral("error");
            result.detail = QStringLiteral("unrecognised status tag=%1").arg(status.tag);
            break;
        }
    } catch (const rust::Error& e) {
        result.status = QStringLiteral("error");
        result.detail = QString::fromUtf8(e.what());
    } catch (const std::exception& e) {
        result.status = QStringLiteral("error");
        result.detail = QString::fromUtf8(e.what());
    } catch (...) {
        result.status = QStringLiteral("error");
        result.detail = QStringLiteral("unknown error");
    }

    emit checkFinished(result);
}

void YamlUpdateWorker::doApply(bool enabled, const QString& approvedReleaseTag,
                               const QStringList& approvedFileNames,
                               const QStringList& approvedFileSha256)
{
    YamlApplyResult result;
    try {
        rust::Vec<rust::String> approvedNames;
        rust::Vec<rust::String> approvedSha256;
        approvedNames.reserve(static_cast<std::size_t>(approvedFileNames.size()));
        approvedSha256.reserve(static_cast<std::size_t>(approvedFileSha256.size()));
        for (const auto& n : approvedFileNames) {
            approvedNames.push_back(rust::String(n.toStdString()));
        }
        for (const auto& sha256 : approvedFileSha256) {
            approvedSha256.push_back(rust::String(sha256.toStdString()));
        }
        const rust::String approvedTag(approvedReleaseTag.toStdString());

        classic::update::ApprovedUpdateDto approved{};
        approved.release_tag = approvedTag;
        approved.file_names = std::move(approvedNames);
        approved.file_sha256 = std::move(approvedSha256);

        auto report = classic::update::yaml_data_apply_update(enabled, approved);

        result.installed = static_cast<qsizetype>(report.installed.size());
        result.failed = static_cast<qsizetype>(report.failed.size());
        if (!report.failed.empty()) {
            result.firstFailureReason =
                classic::toQString(report.failed[0].failure_reason);
        }
        result.errorMessage = classic::toQString(report.error_message);
    } catch (const rust::Error& e) {
        result.errorMessage = QString::fromUtf8(e.what());
    } catch (const std::exception& e) {
        result.errorMessage = QString::fromUtf8(e.what());
    } catch (...) {
        result.errorMessage = QStringLiteral("unknown error");
    }

    emit applyFinished(result);
}

void YamlUpdateWorker::doRollback()
{
    YamlRollbackResult result;
    try {
        auto report = classic::update::yaml_data_rollback_update();
        for (const auto& fileName : report.rolled_back) {
            result.rolledBack.push_back(classic::toQString(fileName));
        }
        for (const auto& fileName : report.no_previous_version) {
            result.noPreviousVersion.push_back(classic::toQString(fileName));
        }
        for (std::size_t i = 0; i < report.failed_files.size(); ++i) {
            const QString fileName = classic::toQString(report.failed_files[i]);
            const QString reason = i < report.failure_reasons.size()
                                       ? classic::toQString(report.failure_reasons[i])
                                       : QStringLiteral("unknown error");
            result.errors.push_back(fileName + QStringLiteral(": ") + reason);
        }
    } catch (const rust::Error& e) {
        result.errors.push_back(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        result.errors.push_back(QString::fromUtf8(e.what()));
    } catch (...) {
        result.errors.push_back(QStringLiteral("unknown error"));
    }

    emit rollbackFinished(result);
}
