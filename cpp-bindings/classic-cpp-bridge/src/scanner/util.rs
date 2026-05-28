use classic_scanlog_core::LogParser;
use std::sync::LazyLock;

static CRASH_PATTERN_PARSER: LazyLock<classic_scanlog_core::error::Result<LogParser>> =
    LazyLock::new(|| LogParser::new(None));

pub(crate) fn detect_vr_log(content: &str) -> bool {
    // VR logs contain "Fallout4VR.esm" or "SkyrimVR.esm" in plugin list
    content.contains("Fallout4VR.esm") || content.contains("SkyrimVR.esm")
}

pub(crate) fn detect_crash_pattern(content: &str) -> String {
    // Parse the crash header to extract the main error/crash module
    let lines: Vec<String> = content.lines().map(|l| l.to_string()).collect();
    let parser = match &*CRASH_PATTERN_PARSER {
        Ok(parser) => parser,
        Err(_) => return String::new(),
    };

    match parser.parse_crash_header(&lines) {
        Ok(header) => header.get("main_error").cloned().unwrap_or_default(),
        Err(_) => String::new(),
    }
}

#[cfg(test)]
#[path = "util_tests.rs"]
mod tests;
