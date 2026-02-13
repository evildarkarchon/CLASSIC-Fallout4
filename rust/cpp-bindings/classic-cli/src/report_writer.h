#pragma once

#include <string>
#include <vector>

/// Write an AUTOSCAN.md report file adjacent to the crash log.
///
/// Derives the output path by replacing .log with -AUTOSCAN.md.
/// Uses the Rust bridge's write_file_string() for encoding-consistent writes,
/// falling back to direct std::ofstream if the bridge call fails.
///
/// Returns true on success, false on failure (logs warning to stderr).
bool write_report(const std::string& log_path,
                  const std::vector<std::string>& report_lines);
