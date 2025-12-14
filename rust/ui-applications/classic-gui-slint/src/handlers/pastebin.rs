// Pastebin integration handlers
use anyhow::{Context, Result};

/// Extract the paste ID from a Pastebin URL
///
/// Supports formats:
/// - `https://pastebin.com/ABC123`
/// - `https://pastebin.com/raw/ABC123`
/// - `pastebin.com/ABC123`
///
/// # Arguments
/// * `url` - Pastebin URL
///
/// # Returns
/// * `Ok(String)` - Paste ID
/// * `Err(anyhow::Error)` - Invalid URL format
fn extract_paste_id(url: &str) -> Result<String> {
    // Remove protocol if present
    let url = url
        .trim_start_matches("https://")
        .trim_start_matches("http://");

    // Check if it's a pastebin.com URL
    if !url.starts_with("pastebin.com/") {
        anyhow::bail!("Not a valid Pastebin URL. Expected format: https://pastebin.com/ABC123");
    }

    // Remove "pastebin.com/" prefix
    let path = url.trim_start_matches("pastebin.com/");

    // Remove "raw/" prefix if present
    let paste_id = path.trim_start_matches("raw/");

    // Validate paste ID (alphanumeric, typically 8 characters)
    if paste_id.is_empty() || !paste_id.chars().all(|c| c.is_alphanumeric()) {
        anyhow::bail!("Invalid paste ID. Expected alphanumeric characters.");
    }

    Ok(paste_id.to_string())
}

/// Download content from a Pastebin URL
///
/// # Arguments
/// * `url` - Pastebin URL (regular or raw format)
///
/// # Returns
/// * `Ok(String)` - Downloaded crash log content
/// * `Err(anyhow::Error)` - Failed to download or invalid URL
pub async fn download_from_pastebin(url: &str) -> Result<String> {
    tracing::info!("Downloading from Pastebin: {}", url);

    // Extract paste ID
    let paste_id = extract_paste_id(url).context("Failed to parse Pastebin URL")?;

    // Build raw URL (always use raw format for clean text)
    let raw_url = format!("https://pastebin.com/raw/{}", paste_id);
    tracing::debug!("Fetching raw URL: {}", raw_url);

    // Download content using reqwest
    let client = reqwest::Client::builder()
        .user_agent("CLASSIC/8.0.0")
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .context("Failed to create HTTP client")?;

    let response = client
        .get(&raw_url)
        .send()
        .await
        .context("Failed to send HTTP request")?;

    // Check status code
    if !response.status().is_success() {
        anyhow::bail!(
            "Failed to download from Pastebin: HTTP {}",
            response.status()
        );
    }

    // Get response text
    let content = response
        .text()
        .await
        .context("Failed to read response body")?;

    // Validate content (should not be empty)
    if content.trim().is_empty() {
        anyhow::bail!("Downloaded content is empty");
    }

    // Check if Pastebin returned an error page
    if content.contains("Error, this is a private paste") {
        anyhow::bail!("This is a private paste and cannot be accessed");
    }

    if content.contains("Error, this paste has been removed") {
        anyhow::bail!("This paste has been removed or does not exist");
    }

    tracing::info!(
        "Successfully downloaded {} bytes from Pastebin",
        content.len()
    );

    Ok(content)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_paste_id_full_url() {
        let result = extract_paste_id("https://pastebin.com/ABC123");
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "ABC123");
    }

    #[test]
    fn test_extract_paste_id_raw_url() {
        let result = extract_paste_id("https://pastebin.com/raw/ABC123");
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "ABC123");
    }

    #[test]
    fn test_extract_paste_id_no_protocol() {
        let result = extract_paste_id("pastebin.com/ABC123");
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "ABC123");
    }

    #[test]
    fn test_extract_paste_id_invalid_domain() {
        let result = extract_paste_id("https://example.com/ABC123");
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_paste_id_empty() {
        let result = extract_paste_id("https://pastebin.com/");
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_paste_id_special_chars() {
        let result = extract_paste_id("https://pastebin.com/ABC-123");
        assert!(result.is_err()); // Should reject non-alphanumeric
    }

    // Note: Actual download tests would require network access
    // and a valid paste ID, so they're omitted here
}
