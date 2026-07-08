//! Version matching algorithm.
//!
//! This module provides the `VersionMatcher` and `MatchResult` types for
//! intelligently matching unknown game versions to the nearest known version.

use crate::GameVersion;
use crate::models::VersionInfo;
use crate::registry::VersionRegistry;

/// Confidence level for version matching results.
///
/// Indicates how confident we are that the matched version is correct.
/// Lower confidence levels may warrant user warnings.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MatchConfidence {
    /// Exact version match found in registry.
    Exact,
    /// Version falls within a defined compatible_range.
    Range,
    /// Matched to nearest known version by semantic distance.
    Nearest,
    /// Using default fallback version for the game.
    Default,
    /// No suitable match found.
    Unknown,
}

impl MatchConfidence {
    /// Check if this is a high-confidence match.
    #[must_use]
    pub const fn is_high_confidence(&self) -> bool {
        matches!(self, Self::Exact | Self::Range)
    }
}

/// Result of version matching.
///
/// Contains the matched version (if any), the confidence level,
/// and a message describing the match result.
#[derive(Debug, Clone)]
pub struct MatchResult {
    /// The matched version info, if found.
    pub version_info: Option<VersionInfo>,
    /// Confidence level of the match.
    pub confidence: MatchConfidence,
    /// The originally detected version.
    pub detected: GameVersion,
    /// Human-readable message about the match.
    pub message: String,
}

impl MatchResult {
    /// Create a new match result.
    #[must_use]
    pub fn new(
        version_info: Option<VersionInfo>,
        confidence: MatchConfidence,
        detected: GameVersion,
        message: impl Into<String>,
    ) -> Self {
        Self {
            version_info,
            confidence,
            detected,
            message: message.into(),
        }
    }

    /// Check if this is an exact match.
    #[must_use]
    pub const fn is_exact(&self) -> bool {
        matches!(self.confidence, MatchConfidence::Exact)
    }

    /// Check if this is a fallback match (Nearest, Default, or Unknown).
    #[must_use]
    pub const fn is_fallback(&self) -> bool {
        matches!(
            self.confidence,
            MatchConfidence::Nearest | MatchConfidence::Default | MatchConfidence::Unknown
        )
    }

    /// Check if the user should be warned about this match.
    ///
    /// Returns `true` for Nearest and Default matches, where the
    /// matched version may not be exactly what the user has.
    #[must_use]
    pub const fn should_warn(&self) -> bool {
        matches!(
            self.confidence,
            MatchConfidence::Nearest | MatchConfidence::Default
        )
    }

    /// Check if this is a valid match (version_info is present and not Unknown).
    #[must_use]
    pub fn is_valid(&self) -> bool {
        self.version_info.is_some() && self.confidence != MatchConfidence::Unknown
    }
}

/// Version matcher for finding the best matching version.
///
/// Implements the matching algorithm with the following priority:
/// 1. Exact match
/// 2. Compatible range match
/// 3. Nearest match (same major version)
/// 4. Default fallback
/// 5. Unknown
pub struct VersionMatcher<'a> {
    registry: &'a VersionRegistry,
}

impl<'a> VersionMatcher<'a> {
    /// Create a new version matcher.
    #[must_use]
    pub const fn new(registry: &'a VersionRegistry) -> Self {
        Self { registry }
    }

    /// Match a detected version to the registry.
    ///
    /// # Arguments
    ///
    /// * `detected` - The detected game version
    /// * `game` - Game identifier (e.g., "Fallout4")
    /// * `is_vr` - Whether VR mode is active
    ///
    /// # Returns
    ///
    /// A `MatchResult` with the best matching version and confidence level.
    pub fn match_version(&self, detected: &GameVersion, game: &str, is_vr: bool) -> MatchResult {
        // Try exact match first
        if let Some(result) = self.find_exact(detected, game, is_vr) {
            return result;
        }

        // Try range match
        if let Some(result) = self.find_range(detected, game, is_vr) {
            return result;
        }

        // Try nearest match
        if let Some(result) = self.find_nearest(detected, game, is_vr) {
            return result;
        }

        // Try default fallback
        if let Some(result) = self.find_default(detected, game, is_vr) {
            return result;
        }

        // No match found
        MatchResult::new(
            None,
            MatchConfidence::Unknown,
            *detected,
            format!(
                "No matching version found for {} (game: {}, VR: {})",
                detected, game, is_vr
            ),
        )
    }

    /// Find an exact version match.
    fn find_exact(&self, detected: &GameVersion, game: &str, is_vr: bool) -> Option<MatchResult> {
        let version = self.registry.get_by_version(detected)?;

        // Verify game and VR mode match
        if version.game != game || version.is_vr != is_vr {
            return None;
        }

        Some(MatchResult::new(
            Some(version.clone()),
            MatchConfidence::Exact,
            *detected,
            format!("Exact match: {} ({})", version.display_name, version.id),
        ))
    }

    /// Find a version within a compatible range.
    fn find_range(&self, detected: &GameVersion, game: &str, is_vr: bool) -> Option<MatchResult> {
        for version in self.registry.get_all_for_game(game, Some(is_vr)) {
            if let Some(range) = &version.compatible_range
                && range.contains(detected)
            {
                return Some(MatchResult::new(
                    Some(version.clone()),
                    MatchConfidence::Range,
                    *detected,
                    format!(
                        "Version {} falls within compatible range for {}",
                        detected, version.display_name
                    ),
                ));
            }
        }
        None
    }

    /// Find the nearest version by semantic distance.
    ///
    /// Only matches versions with the same major version number.
    fn find_nearest(&self, detected: &GameVersion, game: &str, is_vr: bool) -> Option<MatchResult> {
        let candidates: Vec<_> = self
            .registry
            .get_all_for_game(game, Some(is_vr))
            .into_iter()
            .filter(|v| v.version.same_major(detected))
            .collect();

        if candidates.is_empty() {
            return None;
        }

        // Find the nearest by semantic distance
        let mut best = candidates[0];
        let mut best_distance = detected.semantic_distance(&best.version);

        for candidate in &candidates[1..] {
            let distance = detected.semantic_distance(&candidate.version);
            // If same distance, prefer higher priority
            if distance < best_distance
                || (distance == best_distance && candidate.priority > best.priority)
            {
                best = *candidate;
                best_distance = distance;
            }
        }

        Some(MatchResult::new(
            Some(best.clone()),
            MatchConfidence::Nearest,
            *detected,
            format!(
                "Version {} matched to nearest: {} (distance: {})",
                detected, best.display_name, best_distance
            ),
        ))
    }

    /// Find the default version for the game.
    fn find_default(&self, detected: &GameVersion, game: &str, is_vr: bool) -> Option<MatchResult> {
        // Get highest priority version for the game
        let versions = self.registry.get_all_for_game(game, Some(is_vr));

        if versions.is_empty() {
            return None;
        }

        // Already sorted by priority descending
        let default = versions[0];

        Some(MatchResult::new(
            Some(default.clone()),
            MatchConfidence::Default,
            *detected,
            format!(
                "Using default version {} for unrecognized version {}",
                default.display_name, detected
            ),
        ))
    }
}

#[cfg(test)]
#[path = "matching_tests.rs"]
mod tests;
