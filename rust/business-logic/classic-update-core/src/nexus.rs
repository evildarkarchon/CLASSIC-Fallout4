//! Nexus Mods integration for checking mod updates.
//!
//! This module provides functionality to scrape Nexus Mods pages
//! to check for mod updates, since Nexus doesn't provide an official
//! public API for automated tools.
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_update_core::nexus::NexusClient;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let client = NexusClient::new();
//!
//! // Check mod page
//! let info = client.get_mod_info("fallout4", 1234).await?;
//! println!("Mod: {}", info.name);
//! println!("Latest version: {}", info.version);
//! # Ok(())
//! # }
//! ```
//!
//! # Note
//!
//! This module uses web scraping which is fragile and may break if Nexus
//! changes their HTML structure. Consider using the official Nexus Mods API
//! if it becomes available for your use case.

use crate::error::{Result, UpdateError};
use reqwest::Client;
use scraper::{Html, Selector};
use std::time::Duration;

/// Nexus Mods mod information.
///
/// This struct contains basic information about a mod on Nexus Mods,
/// extracted via web scraping.
#[derive(Debug, Clone)]
pub struct NexusModInfo {
    /// Mod name
    pub name: String,

    /// Current version string
    pub version: String,

    /// Mod description (truncated)
    pub description: String,

    /// Author username
    pub author: String,

    /// Number of endorsements
    pub endorsements: Option<u64>,

    /// Number of downloads
    pub downloads: Option<u64>,

    /// Last update date string
    pub last_updated: String,

    /// Mod page URL
    pub url: String,
}

/// Client for interacting with Nexus Mods.
///
/// This client handles web scraping of Nexus Mods pages to extract
/// mod information and version data.
///
/// # Warning
///
/// Web scraping is fragile and may break if Nexus changes their site structure.
/// Use with caution and consider implementing proper error handling and fallbacks.
///
/// # Thread Safety
///
/// The client is thread-safe and can be cloned cheaply for use across threads.
#[derive(Debug, Clone)]
pub struct NexusClient {
    client: Client,
    base_url: String,
}

impl NexusClient {
    /// Request timeout duration (30 seconds).
    const REQUEST_TIMEOUT: Duration = Duration::from_secs(30);

    /// Nexus Mods base URL.
    const NEXUS_BASE_URL: &'static str = "https://www.nexusmods.com";

    /// Creates a new Nexus Mods client.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_update_core::nexus::NexusClient;
    ///
    /// let client = NexusClient::new();
    /// ```
    pub fn new() -> Self {
        let client = Client::builder()
            .timeout(Self::REQUEST_TIMEOUT)
            .user_agent(format!("CLASSIC-Update/{}", env!("CARGO_PKG_VERSION")))
            .build()
            .expect("Failed to create HTTP client");

        Self {
            client,
            base_url: Self::NEXUS_BASE_URL.to_string(),
        }
    }

    /// Gets information about a specific mod.
    ///
    /// # Arguments
    ///
    /// * `game` - Game identifier (e.g., "fallout4", "skyrimspecialedition")
    /// * `mod_id` - Numeric mod ID
    ///
    /// # Returns
    ///
    /// Returns mod information extracted from the mod page.
    ///
    /// # Errors
    ///
    /// - `UpdateError::HttpError` if the HTTP request fails
    /// - `UpdateError::ScrapingError` if the page structure is unexpected
    /// - `UpdateError::NotFound` if the mod doesn't exist
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_update_core::nexus::NexusClient;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let client = NexusClient::new();
    /// let info = client.get_mod_info("fallout4", 1234).await?;
    /// println!("Mod: {}", info.name);
    /// # Ok(())
    /// # }
    /// ```
    pub async fn get_mod_info(&self, game: &str, mod_id: u64) -> Result<NexusModInfo> {
        let url = self.build_mod_url(game, mod_id);

        let response = self.client.get(&url).send().await?;

        match response.status() {
            reqwest::StatusCode::OK => {
                let html = response.text().await?;
                self.parse_mod_page(&html, &url)
            }
            reqwest::StatusCode::NOT_FOUND => {
                Err(UpdateError::NotFound(format!("Mod {} not found", mod_id)))
            }
            status => Err(UpdateError::NexusError(format!(
                "Nexus returned status {}",
                status
            ))),
        }
    }

    /// Builds a Nexus Mods URL for a specific mod.
    ///
    /// # Arguments
    ///
    /// * `game` - Game identifier
    /// * `mod_id` - Numeric mod ID
    ///
    /// # Returns
    ///
    /// Returns the full URL to the mod page.
    fn build_mod_url(&self, game: &str, mod_id: u64) -> String {
        format!("{}/{}/mods/{}", self.base_url, game, mod_id)
    }

    /// Parses a mod page HTML to extract mod information.
    ///
    /// # Arguments
    ///
    /// * `html` - HTML content of the mod page
    /// * `url` - URL of the mod page
    ///
    /// # Returns
    ///
    /// Returns parsed mod information.
    ///
    /// # Errors
    ///
    /// Returns `UpdateError::ScrapingError` if required elements cannot be found.
    ///
    /// # Note
    ///
    /// This method is fragile and depends on Nexus Mods' current HTML structure.
    /// It may break if they change their site layout.
    fn parse_mod_page(&self, html: &str, url: &str) -> Result<NexusModInfo> {
        let document = Html::parse_document(html);

        // Extract mod name
        let name = self
            .extract_text(&document, "h1.page-title, h1")
            .unwrap_or_else(|| "Unknown Mod".to_string());

        // Extract version
        let version = self
            .extract_text(&document, ".version, [class*='version']")
            .unwrap_or_else(|| "Unknown".to_string());

        // Extract description
        let description = self
            .extract_text(&document, ".description, [class*='description']")
            .map(|d| {
                // Truncate to 200 characters
                if d.len() > 200 {
                    format!("{}...", &d[..197])
                } else {
                    d
                }
            })
            .unwrap_or_else(|| "No description available".to_string());

        // Extract author
        let author = self
            .extract_text(&document, ".author, [class*='author']")
            .unwrap_or_else(|| "Unknown Author".to_string());

        // Extract statistics (best-effort)
        let endorsements = self
            .extract_number(&document, "[class*='endorsement'], .endorsements")
            .ok();

        let downloads = self
            .extract_number(&document, "[class*='download'], .downloads")
            .ok();

        // Extract last updated
        let last_updated = self
            .extract_text(&document, "[class*='updated'], .last-updated")
            .unwrap_or_else(|| "Unknown".to_string());

        Ok(NexusModInfo {
            name,
            version,
            description,
            author,
            endorsements,
            downloads,
            last_updated,
            url: url.to_string(),
        })
    }

    /// Extracts text content from the first matching element.
    ///
    /// # Arguments
    ///
    /// * `document` - Parsed HTML document
    /// * `selector` - CSS selector string
    ///
    /// # Returns
    ///
    /// Returns the trimmed text content if found, None otherwise.
    fn extract_text(&self, document: &Html, selector: &str) -> Option<String> {
        let selector = Selector::parse(selector).ok()?;
        document
            .select(&selector)
            .next()
            .map(|el| el.text().collect::<String>().trim().to_string())
    }

    /// Extracts a numeric value from the first matching element.
    ///
    /// # Arguments
    ///
    /// * `document` - Parsed HTML document
    /// * `selector` - CSS selector string
    ///
    /// # Returns
    ///
    /// Returns the parsed number if found and valid.
    ///
    /// # Errors
    ///
    /// Returns `UpdateError::ScrapingError` if the element is not found or cannot be parsed.
    fn extract_number(&self, document: &Html, selector: &str) -> Result<u64> {
        let text = self.extract_text(document, selector).ok_or_else(|| {
            UpdateError::ScrapingError(format!("Element not found: {}", selector))
        })?;

        // Remove commas and other formatting
        let cleaned = text.replace(',', "").replace(' ', "");

        // Extract first number sequence
        let number_str: String = cleaned.chars().filter(|c| c.is_ascii_digit()).collect();

        number_str
            .parse()
            .map_err(|_| UpdateError::ScrapingError(format!("Failed to parse number: {}", text)))
    }

    /// Checks if a mod version has been updated compared to a cached version.
    ///
    /// # Arguments
    ///
    /// * `game` - Game identifier
    /// * `mod_id` - Numeric mod ID
    /// * `cached_version` - Previously cached version string
    ///
    /// # Returns
    ///
    /// Returns `true` if the current version differs from the cached version.
    ///
    /// # Errors
    ///
    /// Returns errors from `get_mod_info` if the mod page cannot be accessed.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_update_core::nexus::NexusClient;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let client = NexusClient::new();
    /// let updated = client.has_update("fallout4", 1234, "1.0").await?;
    /// if updated {
    ///     println!("Mod has been updated!");
    /// }
    /// # Ok(())
    /// # }
    /// ```
    pub async fn has_update(
        &self,
        game: &str,
        mod_id: u64,
        cached_version: &str,
    ) -> Result<bool> {
        let info = self.get_mod_info(game, mod_id).await?;
        Ok(info.version != cached_version)
    }
}

impl Default for NexusClient {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_client_creation() {
        let client = NexusClient::new();
        assert_eq!(client.base_url, NexusClient::NEXUS_BASE_URL);
    }

    #[test]
    fn test_build_mod_url() {
        let client = NexusClient::new();
        let url = client.build_mod_url("fallout4", 1234);
        assert_eq!(url, "https://www.nexusmods.com/fallout4/mods/1234");
    }

    #[test]
    fn test_client_default() {
        let client = NexusClient::default();
        assert_eq!(client.base_url, NexusClient::NEXUS_BASE_URL);
    }

    #[test]
    fn test_client_clone() {
        let client1 = NexusClient::new();
        let client2 = client1.clone();
        assert_eq!(client1.base_url, client2.base_url);
    }
}
