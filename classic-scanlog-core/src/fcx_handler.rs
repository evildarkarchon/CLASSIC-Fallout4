//! FCX Mode Handler - FCX mode state management and message generation
//!
//! This module handles FCX (File Check eXtended) mode operations:
//! - Managing FCX mode enabled/disabled state
//! - Generating appropriate FCX mode messages
//! - Collecting file check results (delegated to Python for complex imports)

use crate::report::ReportFragment;

/// FCX Mode Handler for managing file check operations
#[derive(Clone, Debug)]
pub struct FcxModeHandler {
    /// Whether FCX mode is enabled
        pub fcx_mode: bool,

    /// Main files check result (from Python)
        pub main_files_check: Option<String>,

    /// Game files check result (from Python)
        pub game_files_check: Option<String>,
}

impl FcxModeHandler {
    pub fn new(fcx_mode: bool) -> Self {
        Self {
            fcx_mode,
            main_files_check: None,
            game_files_check: None,
        }
    }

    /// Set main files check result (called from Python after running checks)
    ///
    /// Args:
    ///     result: Main files check result string
    pub fn set_main_files_result(&mut self, result: String) {
        self.main_files_check = Some(result);
    }

    /// Set game files check result (called from Python after running checks)
    ///
    /// Args:
    ///     result: Game files check result string
    pub fn set_game_files_result(&mut self, result: String) {
        self.game_files_check = Some(result);
    }

    /// Generate FCX mode messages based on current state
    ///
    /// Returns:
    ///     ReportFragment containing FCX mode messages
    pub fn get_fcx_messages(&self) -> ReportFragment {
        let mut lines = Vec::new();

        if self.fcx_mode {
            lines.push("* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n\n".to_string());
            lines.push("[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n".to_string());

            // Add main files check if available
            if let Some(ref main_check) = self.main_files_check {
                if !main_check.is_empty() {
                    lines.push(main_check.clone());
                }
            }

            // Add game files check if available
            if let Some(ref game_check) = self.game_files_check {
                if !game_check.is_empty() {
                    lines.push(game_check.clone());
                }
            }
        } else {
            lines.push("* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n\n".to_string());
            lines.push("[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n".to_string());
        }

        ReportFragment::from_lines(lines)
    }

    /// Get FCX mode enabled message only (for quick checks)
    ///
    /// Returns:
    ///     String with FCX mode status message
    pub fn get_fcx_status_message(&self) -> String {
        if self.fcx_mode {
            "FCX Mode: ENABLED".to_string()
        } else {
            "FCX Mode: DISABLED".to_string()
        }
    }

    /// Check if FCX mode has any results to display
    ///
    /// Returns:
    ///     True if there are check results available
    pub fn has_results(&self) -> bool {
        if !self.fcx_mode {
            return false;
        }

        self.main_files_check.as_ref().map_or(false, |s| !s.is_empty())
            || self.game_files_check.as_ref().map_or(false, |s| !s.is_empty())
    }

    /// Reset all FCX check results (for new scan session)
    pub fn reset(&mut self) {
        self.main_files_check = None;
        self.game_files_check = None;
    }

    /// Create a disabled FCX handler (convenience constructor)
    pub fn disabled() -> Self {
        Self {
            fcx_mode: false,
            main_files_check: None,
            game_files_check: None,
        }
    }

    /// Create an enabled FCX handler (convenience constructor)
    pub fn enabled() -> Self {
        Self {
            fcx_mode: true,
            main_files_check: None,
            game_files_check: None,
        }
    }


}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fcx_disabled_messages() {
        let handler = FcxModeHandler::new(false);
        let fragment = handler.get_fcx_messages();

        assert!(fragment.len() > 0);
        let lines = fragment.to_list();
        assert!(lines.iter().any(|line| line.contains("DISABLED")));
    }

    #[test]
    fn test_fcx_enabled_messages() {
        let handler = FcxModeHandler::new(true);
        let fragment = handler.get_fcx_messages();

        assert!(fragment.len() > 0);
        let lines = fragment.to_list();
        assert!(lines.iter().any(|line| line.contains("ENABLED")));
    }

    #[test]
    fn test_fcx_with_results() {
        let mut handler = FcxModeHandler::new(true);
        handler.set_main_files_result("Main files OK\n".to_string());
        handler.set_game_files_result("Game files OK\n".to_string());

        let fragment = handler.get_fcx_messages();
        let lines = fragment.to_list();

        assert!(lines.iter().any(|line| line.contains("Main files")));
        assert!(lines.iter().any(|line| line.contains("Game files")));
    }

    #[test]
    fn test_fcx_has_results() {
        let mut handler = FcxModeHandler::new(true);
        assert!(!handler.has_results());

        handler.set_main_files_result("Main files OK\n".to_string());
        assert!(handler.has_results());
    }

    #[test]
    fn test_fcx_reset() {
        let mut handler = FcxModeHandler::new(true);
        handler.set_main_files_result("Main files OK\n".to_string());
        handler.set_game_files_result("Game files OK\n".to_string());

        assert!(handler.has_results());

        handler.reset();

        assert!(!handler.has_results());
    }

    #[test]
    fn test_fcx_convenience_constructors() {
        let enabled = FcxModeHandler::enabled();
        assert!(enabled.fcx_mode);

        let disabled = FcxModeHandler::disabled();
        assert!(!disabled.fcx_mode);
    }
}
