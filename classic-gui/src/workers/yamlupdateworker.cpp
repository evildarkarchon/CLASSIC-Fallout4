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

constexpr const char* kYamlPagesUrl =
    "https://evildarkarchon.github.io/CLASSIC-Fallout4/yaml-data/manifest-latest.json";
constexpr const char* kYamlTagPrefix = "yaml-data-v";

// The set of files the native frontends can install today. This is a
// literal duplicate of `buildYamlSchemaEntries` in settingsdialog.cpp; the
// worker rebuilds it instead of receiving the list from the UI thread so
// the off-thread call has no incidental coupling to Qt-owned state.
rust::Vec<classic::update::YamlClientSchemaEntryDto> buildDefaultEntries()
{
    rust::Vec<classic::update::YamlClientSchemaEntryDto> entries;

    classic::update::YamlClientSchemaEntryDto main{};
    main.name = "CLASSIC Main.yaml";
    main.accepted_major = 1u;
    main.accepted_minimum_minor = 0u;
    main.has_installed = false;
    entries.push_back(std::move(main));

    classic::update::YamlClientSchemaEntryDto fallout4{};
    fallout4.name = "CLASSIC Fallout4.yaml";
    fallout4.accepted_major = 1u;
    fallout4.accepted_minimum_minor = 0u;
    fallout4.has_installed = false;
    entries.push_back(std::move(fallout4));

    return entries;
}

} // namespace

YamlUpdateWorker::YamlUpdateWorker(QObject* parent)
    : QObject(parent)
{
}

void YamlUpdateWorker::doCheck(bool enabled)
{
    YamlCheckResult result;
    try {
        auto entries = buildDefaultEntries();
        // Empty `bundled_yaml_dir` keeps the bridge's `current_exe()`
        // fallback, which is correct for the native GUI exe — it sits
        // next to `CLASSIC Data/`. Non-native hosts (Python/Node bindings)
        // must pass an explicit path; see the bridge header for details.
        auto status = classic::update::yaml_check_update(
            kYamlPagesUrl, kYamlTagPrefix, entries, enabled,
            rust::Str(""));

        switch (status.tag) {
        case kYamlTagDisabled:
            result.status = QStringLiteral("disabled");
            break;
        case kYamlTagUpdateAvailable:
            result.status = QStringLiteral("updateAvailable");
            result.releaseTag = classic::toQString(status.release_tag);
            result.compatibleFileNames.reserve(
                static_cast<int>(status.compatible_files.size()));
            for (const auto& f : status.compatible_files) {
                result.compatibleFileNames.push_back(classic::toQString(f.name));
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
                               const QStringList& approvedFileNames)
{
    YamlApplyResult result;
    try {
        auto entries = buildDefaultEntries();

        rust::Vec<rust::String> approvedNames;
        approvedNames.reserve(static_cast<std::size_t>(approvedFileNames.size()));
        for (const auto& n : approvedFileNames) {
            approvedNames.push_back(rust::String(n.toStdString()));
        }
        const rust::String approvedTag(approvedReleaseTag.toStdString());

        auto report = classic::update::yaml_apply_update(
            kYamlPagesUrl, kYamlTagPrefix, entries, enabled,
            approvedTag, approvedNames, rust::Str(""));

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

void YamlUpdateWorker::doRollback(const QStringList& fileNames)
{
    YamlRollbackResult result;
    for (const auto& fileName : fileNames) {
        try {
            auto outcome = classic::update::yaml_rollback_update(
                rust::String(fileName.toStdString()));
            const QString reportedName = classic::toQString(outcome.file_name);
            const QString errorText = classic::toQString(outcome.error_message);
            if (outcome.rolled_back) {
                result.rolledBack.push_back(
                    reportedName.isEmpty() ? fileName : reportedName);
            } else if (errorText.isEmpty()) {
                // `rolled_back == false` with no error is the documented
                // "NoPreviousVersion" branch in the Rust contract.
                result.noPreviousVersion.push_back(
                    reportedName.isEmpty() ? fileName : reportedName);
            } else {
                result.errors.push_back(fileName + QStringLiteral(": ") + errorText);
            }
        } catch (const rust::Error& e) {
            result.errors.push_back(fileName + QStringLiteral(": ") +
                                    QString::fromUtf8(e.what()));
        } catch (const std::exception& e) {
            result.errors.push_back(fileName + QStringLiteral(": ") +
                                    QString::fromUtf8(e.what()));
        } catch (...) {
            result.errors.push_back(fileName + QStringLiteral(": unknown error"));
        }
    }

    emit rollbackFinished(result);
}
