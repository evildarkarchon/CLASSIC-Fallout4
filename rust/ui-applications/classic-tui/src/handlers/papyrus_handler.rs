//! Papyrus log monitoring handler for TUI
//!
//! This module provides real-time monitoring of Papyrus logs with "tail -f" behavior.
//! It uses the file watcher to detect changes and sends updates to the UI.

use anyhow::Result;
use classic_scanlog_core::papyrus::{PapyrusAnalyzer, PapyrusStats};
use notify::{Event, RecommendedWatcher, RecursiveMode, Watcher};
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, RwLock};

/// Messages sent from Papyrus monitor to UI
#[derive(Debug, Clone)]
pub enum PapyrusMessage {
    /// Monitoring started successfully
    Started,

    /// Statistics updated with new data
    StatsUpdate(PapyrusStats),

    /// New log lines added (for display)
    NewLines(Vec<String>),

    /// Error occurred during monitoring
    Error(String),

    /// Monitoring stopped
    Stopped,
}

/// Papyrus monitoring handler
pub struct PapyrusHandler {
    /// Path to Papyrus log file
    log_path: PathBuf,

    /// Analyzer instance
    analyzer: Arc<RwLock<PapyrusAnalyzer>>,

    /// Whether monitoring is active
    is_monitoring: Arc<RwLock<bool>>,
}

impl PapyrusHandler {
    /// Create a new Papyrus handler
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the Papyrus.0.log file
    pub fn new(log_path: PathBuf) -> Self {
        let analyzer = PapyrusAnalyzer::new(log_path.clone());

        Self {
            log_path,
            analyzer: Arc::new(RwLock::new(analyzer)),
            is_monitoring: Arc::new(RwLock::new(false)),
        }
    }

    /// Check if the log file exists
    #[allow(dead_code)]
    pub async fn log_exists(&self) -> bool {
        self.analyzer.read().await.log_exists()
    }

    /// Start monitoring Papyrus log file
    ///
    /// This spawns a background task that watches for file changes and sends
    /// updates via the provided channel.
    ///
    /// # Arguments
    ///
    /// * `tx` - Channel to send monitoring updates
    ///
    /// # Returns
    ///
    /// Result indicating success or error
    pub async fn start_monitoring(
        &mut self,
        tx: mpsc::Sender<PapyrusMessage>,
    ) -> Result<()> {
        // Set monitoring flag
        *self.is_monitoring.write().await = true;

        // Start monitoring from end of file (ignore prior history)
        if let Err(e) = self.analyzer.write().await.start_monitoring() {
            let _ = tx.send(PapyrusMessage::Error(format!("Failed to start monitoring: {}", e))).await;
            return Err(e.into());
        }

        let _ = tx.send(PapyrusMessage::Started).await;

        // Clone for background task
        let analyzer = self.analyzer.clone();
        let is_monitoring = self.is_monitoring.clone();
        let log_path = self.log_path.clone();

        // Spawn background monitoring task
        tokio::spawn(async move {
            if let Err(e) = monitor_loop(analyzer, is_monitoring, log_path, tx).await {
                tracing::error!("Papyrus monitoring error: {}", e);
            }
        });

        Ok(())
    }

    /// Stop monitoring
    pub async fn stop_monitoring(&mut self) {
        *self.is_monitoring.write().await = false;
    }

    /// Check if currently monitoring
    #[allow(dead_code)]
    pub async fn is_monitoring(&self) -> bool {
        *self.is_monitoring.read().await
    }

    /// Get current statistics (one-time read)
    #[allow(dead_code)]
    pub async fn get_current_stats(&self) -> Result<PapyrusStats> {
        let mut analyzer = self.analyzer.write().await;
        Ok(analyzer.analyze_full()?.clone())
    }
}

/// Main monitoring loop that watches for file changes
async fn monitor_loop(
    analyzer: Arc<RwLock<PapyrusAnalyzer>>,
    is_monitoring: Arc<RwLock<bool>>,
    log_path: PathBuf,
    tx: mpsc::Sender<PapyrusMessage>,
) -> Result<()> {
    // Get parent directory for watching
    let watch_dir = log_path.parent().ok_or_else(|| {
        anyhow::anyhow!("Log path has no parent directory")
    })?;

    // Create file watcher
    let (watch_tx, mut watch_rx) = mpsc::channel(100);

    let mut watcher: RecommendedWatcher = notify::recommended_watcher(
        move |res: Result<Event, notify::Error>| {
            if let Ok(event) = res {
                // Use try_send to avoid blocking if channel is full
                if watch_tx.try_send(event).is_err() {
                    tracing::warn!("Papyrus watch channel full, dropping file system event");
                }
            }
        }
    )?;

    // Watch the directory containing the log file
    watcher.watch(watch_dir, RecursiveMode::NonRecursive)?;

    // Also poll periodically in case file watching fails
    let mut poll_interval = tokio::time::interval(Duration::from_secs(2));

    loop {
        // Check if still monitoring
        if !*is_monitoring.read().await {
            let _ = tx.send(PapyrusMessage::Stopped).await;
            break;
        }

        // Monitor channel capacity to prevent overload
        if tx.capacity() < 10 {
            tracing::warn!("Papyrus message channel nearly full (capacity < 10), slowing down");
            tokio::time::sleep(Duration::from_millis(100)).await;
        }

        tokio::select! {
            // File system event received
            Some(event) = watch_rx.recv() => {
                // Check if this event is for our log file
                if event.paths.iter().any(|p| p == &log_path) {
                    if let Err(e) = check_for_updates(&analyzer, &tx).await {
                        tracing::error!("Error checking for updates: {}", e);
                    }
                }
            }

            // Periodic poll (fallback)
            _ = poll_interval.tick() => {
                if let Err(e) = check_for_updates(&analyzer, &tx).await {
                    tracing::error!("Error during poll: {}", e);
                }
            }
        }
    }

    Ok(())
}

/// Check for new updates in the log file
async fn check_for_updates(
    analyzer: &Arc<RwLock<PapyrusAnalyzer>>,
    tx: &mpsc::Sender<PapyrusMessage>,
) -> Result<()> {
    // Clone Arc to move into spawn_blocking
    let analyzer_clone = Arc::clone(analyzer);

    // Use spawn_blocking to prevent file I/O from blocking the async runtime
    // This moves the blocking file I/O and write lock acquisition to a thread pool
    let result = tokio::task::spawn_blocking(move || {
        // Use blocking lock instead of async lock since we're in spawn_blocking
        let mut analyzer_guard = analyzer_clone.blocking_write();
        analyzer_guard.check_for_updates()
    })
    .await
    .map_err(|e| anyhow::anyhow!("Spawn blocking failed: {}", e))?;

    match result {
        Ok(Some((new_lines, stats))) => {
            // Send new lines if any
            if !new_lines.is_empty() {
                let _ = tx.send(PapyrusMessage::NewLines(new_lines)).await;
            }

            // Send updated stats
            let _ = tx.send(PapyrusMessage::StatsUpdate(stats)).await;
        }
        Ok(None) => {
            // No changes
        }
        Err(e) => {
            let _ = tx
                .send(PapyrusMessage::Error(format!("Read error: {}", e)))
                .await;
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use std::time::Duration;
    use tempfile::NamedTempFile;
    use tokio::time::sleep;

    #[tokio::test]
    async fn test_handler_creation() {
        let temp_file = NamedTempFile::new().unwrap();
        let handler = PapyrusHandler::new(temp_file.path().to_path_buf());

        assert!(handler.log_exists().await);
        assert!(!handler.is_monitoring().await);
    }

    #[tokio::test]
    async fn test_monitoring_start_stop() {
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "Initial line").unwrap();
        temp_file.flush().unwrap();

        let mut handler = PapyrusHandler::new(temp_file.path().to_path_buf());
        let (tx, mut rx) = mpsc::channel(100);

        // Start monitoring
        handler.start_monitoring(tx).await.unwrap();
        assert!(handler.is_monitoring().await);

        // Should receive Started message
        let msg = rx.recv().await.unwrap();
        assert!(matches!(msg, PapyrusMessage::Started));

        // Stop monitoring
        handler.stop_monitoring().await;

        // Give it a moment to process
        sleep(Duration::from_millis(100)).await;
    }

    #[tokio::test]
    async fn test_get_current_stats() {
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "Dumping Stacks").unwrap();
        writeln!(temp_file, "[2024/01/01] error: Test error").unwrap();
        temp_file.flush().unwrap();

        let handler = PapyrusHandler::new(temp_file.path().to_path_buf());
        let stats = handler.get_current_stats().await.unwrap();

        assert_eq!(stats.dumps, 1);
        assert_eq!(stats.errors, 1);
    }
}
