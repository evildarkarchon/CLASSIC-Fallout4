// Help system handlers
use anyhow::{Context, Result};
use std::path::PathBuf;
use yaml_rust2::{Yaml, YamlLoader};

/// Help topic data structure
#[derive(Debug, Clone)]
pub struct HelpTopic {
    pub title: String,
    pub content: String,
    pub related: Vec<RelatedTopic>,
}

/// Related topic reference
#[derive(Debug, Clone)]
pub struct RelatedTopic {
    pub category: String,
    pub topic: String,
    pub display: String,
}

/// Load help content from YAML file
///
/// # Returns
/// * `Ok(Yaml)` - Parsed YAML help content
/// * `Err(anyhow::Error)` - Failed to load or parse YAML
pub async fn load_help_yaml() -> Result<Yaml> {
    let help_path = PathBuf::from("CLASSIC Data/Help/GUI_Help.yaml");

    if !help_path.exists() {
        anyhow::bail!("Help file not found: {}", help_path.display());
    }

    // Read file contents
    let contents = tokio::fs::read_to_string(&help_path)
        .await
        .context("Failed to read help file")?;

    // Parse YAML
    let docs = YamlLoader::load_from_str(&contents)
        .context("Failed to parse help YAML")?;

    if docs.is_empty() {
        anyhow::bail!("Help file is empty");
    }

    Ok(docs[0].clone())
}

/// Get a specific help topic by category and topic ID
///
/// # Arguments
/// * `category` - Category name (e.g., "main", "backups", "results", "settings")
/// * `topic` - Topic ID (e.g., "scan_crash_logs", "backup_xse")
///
/// # Returns
/// * `Ok(HelpTopic)` - Help topic data
/// * `Err(anyhow::Error)` - Topic not found or error loading help
pub async fn get_help_topic(category: &str, topic: &str) -> Result<HelpTopic> {
    let yaml = load_help_yaml().await?;

    // Navigate: yaml["help"][category][topic]
    let help_root = &yaml["help"];
    if help_root.is_badvalue() {
        anyhow::bail!("Invalid help file structure: missing 'help' root");
    }

    let category_node = &help_root[category];
    if category_node.is_badvalue() {
        anyhow::bail!("Help category not found: {}", category);
    }

    let topic_node = &category_node[topic];
    if topic_node.is_badvalue() {
        anyhow::bail!("Help topic not found: {}/{}", category, topic);
    }

    // Extract topic data
    let title = topic_node["title"]
        .as_str()
        .unwrap_or("Help")
        .to_string();

    let content = topic_node["content"]
        .as_str()
        .unwrap_or("No content available.")
        .to_string();

    // Extract related topics
    let mut related = Vec::new();
    if let Some(related_array) = topic_node["related"].as_vec() {
        for related_item in related_array {
            if let (Some(cat), Some(top)) = (
                related_item["category"].as_str(),
                related_item["topic"].as_str(),
            ) {
                // Look up the display name from the referenced topic
                let display_name = if let Ok(referenced_topic) = get_topic_title(cat, top).await {
                    referenced_topic
                } else {
                    format!("{}/{}", cat, top) // Fallback if topic not found
                };

                related.push(RelatedTopic {
                    category: cat.to_string(),
                    topic: top.to_string(),
                    display: display_name,
                });
            }
        }
    }

    Ok(HelpTopic {
        title,
        content,
        related,
    })
}

/// Get the title of a help topic without loading full content
///
/// # Arguments
/// * `category` - Category name
/// * `topic` - Topic ID
///
/// # Returns
/// * `Ok(String)` - Topic title
/// * `Err(anyhow::Error)` - Topic not found
async fn get_topic_title(category: &str, topic: &str) -> Result<String> {
    let yaml = load_help_yaml().await?;

    let topic_node = &yaml["help"][category][topic];
    if topic_node.is_badvalue() {
        anyhow::bail!("Topic not found: {}/{}", category, topic);
    }

    Ok(topic_node["title"]
        .as_str()
        .unwrap_or("Unknown Topic")
        .to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_load_help_yaml() {
        // Skip if help file doesn't exist
        let help_path = PathBuf::from("CLASSIC Data/Help/GUI_Help.yaml");
        if !help_path.exists() {
            return;
        }

        let result = load_help_yaml().await;
        assert!(result.is_ok(), "Failed to load help YAML");
    }

    #[tokio::test]
    async fn test_get_help_topic() {
        // Skip if help file doesn't exist
        let help_path = PathBuf::from("CLASSIC Data/Help/GUI_Help.yaml");
        if !help_path.exists() {
            return;
        }

        let result = get_help_topic("main", "scan_crash_logs").await;
        assert!(result.is_ok(), "Failed to get help topic");

        if let Ok(topic) = result {
            assert_eq!(topic.title, "Scan Crash Logs");
            assert!(!topic.content.is_empty());
        }
    }

    #[tokio::test]
    async fn test_get_nonexistent_topic() {
        // Skip if help file doesn't exist
        let help_path = PathBuf::from("CLASSIC Data/Help/GUI_Help.yaml");
        if !help_path.exists() {
            return;
        }

        let result = get_help_topic("nonexistent", "topic").await;
        assert!(result.is_err(), "Should fail for nonexistent topic");
    }
}
