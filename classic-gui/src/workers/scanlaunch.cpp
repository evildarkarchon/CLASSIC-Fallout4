#include "scanlaunch.h"

#include "core/rust_qt_bridge.h"
#include "scanrunpresentation.h"

#include <cstddef>

namespace classic::gui {

rust::Box<classic::scanner::ScanRunLaunch> launchScanRun(const QString& installationRoot,
                                                         const QStringList& targetedInputs)
{
    // Value-initialised: every `has_*` flag is false and every supplied-as-on option is off, so
    // Rust applies the saved User Settings unchanged.
    const classic::scanner::ScanRunLaunchOverridesDto overrides{};
    const auto root = classic::toRustString(installationRoot);
    if (targetedInputs.isEmpty()) {
        return classic::scanner::scan_run_launch_standard(root, overrides);
    }

    rust::Vec<rust::String> inputs;
    inputs.reserve(static_cast<std::size_t>(targetedInputs.size()));
    for (const auto& input : targetedInputs) {
        inputs.push_back(classic::toRustString(input));
    }
    return classic::scanner::scan_run_launch_targeted(root, inputs, overrides);
}

QString formatScanRunLaunchWarning(const classic::scanner::ScanRunLaunchRequestDto& view)
{
    return renderScanRunDisplayLinesAsRichText(presentScanRunDisplayLines(view.display_lines));
}

} // namespace classic::gui
