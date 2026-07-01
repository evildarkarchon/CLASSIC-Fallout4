//! Game Scan Report Builder (G-09/G-10)
//!
//! Provides report generation functionality for mod scanning operations,
//! formatting detected issues into human-readable reports for both unpacked
//! (loose) and archived (BA2) mod scans.
//!
//! This is the Rust equivalent of Python's `ScanReportBuilder` and `ScanValidators`
//! from `ClassicLib/scanning/game/checks/`.
//!
//! ## Architecture
//!
//! - [`ScanValidators`]: Provides cached issue message templates keyed by category
//! - [`ScanReportBuilder`]: Formats issue collections into structured reports

use std::collections::{BTreeMap, BTreeSet};

/// Issue messages map: category name -> list of header/description lines
type IssueMessages = BTreeMap<String, Vec<String>>;

/// Cache key type for (xse_acronym, mode) pairs
type CacheKey = (String, String);

/// Scan validators providing cached issue message templates.
///
/// Generates standardized issue messages for mod scan reports, keyed by
/// issue category (e.g., `tex_dims`, `tex_frmt`, `snd_frmt`). Results
/// are cached per `(xse_acronym, mode)` pair.
///
/// # Example
///
/// ```
/// use classic_scangame_core::game_report::ScanValidators;
///
/// let validators = ScanValidators::new();
/// let messages = validators.get_issue_messages("F4SE", "unpacked");
/// assert!(messages.contains_key("tex_dims"));
/// ```
pub struct ScanValidators {
    /// Cached issue messages keyed by (xse_acronym, mode)
    cache: std::cell::RefCell<BTreeMap<CacheKey, IssueMessages>>,
}

impl ScanValidators {
    /// Create a new ScanValidators instance
    pub fn new() -> Self {
        Self {
            cache: std::cell::RefCell::new(BTreeMap::new()),
        }
    }

    /// Get issue messages for a given XSE acronym and scan mode.
    ///
    /// Returns a map from issue category to a list of header/description lines.
    /// Results are cached for subsequent calls with the same parameters.
    ///
    /// # Arguments
    ///
    /// * `xse_acronym` - Script extender name (e.g., "F4SE", "SKSE")
    /// * `mode` - Scan mode: "unpacked" or "archived"
    ///
    /// # Example
    ///
    /// ```
    /// use classic_scangame_core::game_report::ScanValidators;
    ///
    /// let validators = ScanValidators::new();
    /// let msgs = validators.get_issue_messages("F4SE", "archived");
    /// assert!(msgs.contains_key("ba2_frmt"));
    /// ```
    pub fn get_issue_messages(&self, xse_acronym: &str, mode: &str) -> IssueMessages {
        let key = (xse_acronym.to_string(), mode.to_string());

        // Check cache
        {
            let cache = self.cache.borrow();
            if let Some(cached) = cache.get(&key) {
                return cached.clone();
            }
        }

        // Build base messages (shared between modes)
        let mut messages = BTreeMap::new();

        messages.insert(
            "tex_dims".to_string(),
            vec![
                "\n**[!] DDS DIMENSIONS ARE NOT DIVISIBLE BY 2 [!]**\n".to_string(),
                "[>] Any mods that have texture files with incorrect dimensions\n".to_string(),
                "  are very likely to cause a *Texture (DDS) Crash*. For further details,\n"
                    .to_string(),
                "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n"
                    .to_string(),
            ],
        );

        messages.insert(
            "tex_frmt".to_string(),
            vec![
                "\n**[?] TEXTURE FILES HAVE INCORRECT FORMAT, SHOULD BE DDS [?]**\n".to_string(),
                "[>] Any files with an incorrect file format will not work.\n".to_string(),
                "  Mod authors should convert these files to their proper game format.\n"
                    .to_string(),
                "  If possible, notify the original mod authors about these problems.\n\n"
                    .to_string(),
            ],
        );

        messages.insert(
            "snd_frmt".to_string(),
            vec![
                "\n**[?] SOUND FILES HAVE INCORRECT FORMAT, SHOULD BE XWM OR WAV [?]**\n"
                    .to_string(),
                "[>] Any files with an incorrect file format will not work.\n".to_string(),
                "  Mod authors should convert these files to their proper game format.\n"
                    .to_string(),
                "  If possible, notify the original mod authors about these problems.\n\n"
                    .to_string(),
            ],
        );

        // Add mode-specific messages
        match mode {
            "unpacked" => {
                messages.insert(
                    "xse_file".to_string(),
                    vec![
                        format!(
                            "\n**[!] FOLDERS CONTAIN COPIES OF *{}* SCRIPT FILES [!]**\n",
                            xse_acronym
                        ),
                        "[>] Any mods with copies of original Script Extender files\n".to_string(),
                        "  may cause script related problems or crashes.\n\n".to_string(),
                    ],
                );

                messages.insert(
                    "previs".to_string(),
                    vec![
                        "\n**[!] FOLDERS CONTAIN LOOSE PRECOMBINE / PREVIS FILES [!]**\n"
                            .to_string(),
                        "[>] Any mods that contain custom precombine/previs files\n".to_string(),
                        "  should load after the PRP.esp plugin from Previs Repair Pack (PRP).\n"
                            .to_string(),
                        "  Otherwise, see if there is a PRP patch available for these mods.\n\n"
                            .to_string(),
                    ],
                );

                messages.insert(
                    "animdata".to_string(),
                    vec![
                        "\n**[?] FOLDERS CONTAIN CUSTOM ANIMATION FILE DATA [?]**\n".to_string(),
                        "[>] Any mods that have their own custom Animation File Data\n".to_string(),
                        "  may rarely cause an *Animation Corruption Crash*. For further details,\n".to_string(),
                        "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n".to_string(),
                    ],
                );

                messages.insert(
                    "cleanup".to_string(),
                    vec![
                        "\n**[i] DOCUMENTATION FILES MOVED TO 'CLASSIC Backup\\Cleaned Files' [i]**\n".to_string(),
                    ],
                );
            }
            "archived" => {
                messages.insert(
                    "xse_file".to_string(),
                    vec![
                        format!(
                            "\n**[!] BA2 ARCHIVES CONTAIN COPIES OF *{}* SCRIPT FILES [!]**\n",
                            xse_acronym
                        ),
                        "[>] Any mods with copies of original Script Extender files\n".to_string(),
                        "  may cause script related problems or crashes.\n\n".to_string(),
                    ],
                );

                messages.insert(
                    "ba2_frmt".to_string(),
                    vec![
                        "\n**[?] BA2 ARCHIVES HAVE INCORRECT FORMAT, SHOULD BE BTDX-GNRL OR BTDX-DX10 [?]**\n".to_string(),
                        "[>] Any files with an incorrect file format will not work.\n".to_string(),
                        "  Mod authors should convert these files to their proper game format.\n".to_string(),
                        "  If possible, notify the original mod authors about these problems.\n\n".to_string(),
                    ],
                );
            }
            _ => {}
        }

        // Cache and return
        let result = messages.clone();
        self.cache.borrow_mut().insert(key, messages);
        result
    }
}

impl Default for ScanValidators {
    fn default() -> Self {
        Self::new()
    }
}

/// Build formatted scan reports from issue collections.
///
/// Takes collections of detected issues (keyed by category) and formats
/// them into human-readable reports with appropriate headers and messages
/// for different issue types.
///
/// # Example
///
/// ```
/// use classic_scangame_core::game_report::{ScanReportBuilder, ScanValidators};
/// use std::collections::{BTreeMap, BTreeSet};
///
/// let validators = ScanValidators::new();
/// let mut builder = ScanReportBuilder::new(&validators);
///
/// let mut issues = BTreeMap::new();
/// let mut tex_issues = BTreeSet::new();
/// tex_issues.insert("  - TGA : textures/bad.tga\n".to_string());
/// issues.insert("tex_frmt".to_string(), tex_issues);
///
/// let report = builder.build_unpacked_report(&issues, "F4SE");
/// assert!(report.contains("UNPACKED"));
/// assert!(report.contains("bad.tga"));
/// ```
pub struct ScanReportBuilder<'a> {
    /// Validators for issue message lookup
    validators: &'a ScanValidators,
}

impl<'a> ScanReportBuilder<'a> {
    /// Create a new report builder with the given validators
    pub fn new(validators: &'a ScanValidators) -> Self {
        Self { validators }
    }

    /// Build report for unpacked (loose) mod file scan.
    ///
    /// Generates a formatted report for unpacked mod file scanning results,
    /// including headers and categorized issues.
    ///
    /// # Arguments
    ///
    /// * `issue_lists` - Map of issue category to set of issue strings
    /// * `xse_acronym` - Script extender name (e.g., "F4SE", "SKSE")
    pub fn build_unpacked_report(
        &self,
        issue_lists: &BTreeMap<String, BTreeSet<String>>,
        xse_acronym: &str,
    ) -> String {
        let mut output = String::new();
        output.push_str("=================== MOD FILES SCAN ====================\n");
        output.push_str("========= RESULTS FROM UNPACKED / LOOSE FILES =========\n");

        let issue_messages = self.validators.get_issue_messages(xse_acronym, "unpacked");

        for (issue_type, items) in issue_lists {
            if !items.is_empty()
                && let Some(messages) = issue_messages.get(issue_type)
            {
                for msg in messages {
                    output.push_str(msg);
                }
                // Sort items for deterministic output
                for item in items {
                    output.push_str(item);
                }
            }
        }

        output
    }

    /// Build report for archived (BA2) mod file scan.
    ///
    /// Generates a formatted report for BA2 archive scanning results,
    /// including headers and categorized issues.
    ///
    /// # Arguments
    ///
    /// * `issue_lists` - Map of issue category to set of issue strings
    /// * `xse_acronym` - Script extender name (e.g., "F4SE", "SKSE")
    pub fn build_archived_report(
        &self,
        issue_lists: &BTreeMap<String, BTreeSet<String>>,
        xse_acronym: &str,
    ) -> String {
        let mut output = String::new();
        output.push_str("\n========== RESULTS FROM ARCHIVED / BA2 FILES ==========\n");

        let issue_messages = self.validators.get_issue_messages(xse_acronym, "archived");

        for (issue_type, items) in issue_lists {
            if !items.is_empty()
                && let Some(messages) = issue_messages.get(issue_type)
            {
                for msg in messages {
                    output.push_str(msg);
                }
                for item in items {
                    output.push_str(item);
                }
            }
        }

        output
    }

    /// Build combined report for both unpacked and archived scans.
    ///
    /// # Arguments
    ///
    /// * `unpacked_issues` - Issues from unpacked file scan
    /// * `archived_issues` - Issues from BA2 archive scan
    /// * `xse_acronym` - Script extender name (e.g., "F4SE", "SKSE")
    pub fn build_combined_report(
        &self,
        unpacked_issues: &BTreeMap<String, BTreeSet<String>>,
        archived_issues: &BTreeMap<String, BTreeSet<String>>,
        xse_acronym: &str,
    ) -> String {
        let mut report = self.build_unpacked_report(unpacked_issues, xse_acronym);
        report.push_str(&self.build_archived_report(archived_issues, xse_acronym));
        report
    }
}

#[cfg(test)]
#[path = "game_report_tests.rs"]
mod tests;
