//! File system watcher module for detecting changes in report directories.
//!
//! This module provides functionality to set up and manage a file system watcher
//! using the `notify` crate. It includes debouncing logic to prevent excessive
//! notifications and methods to add/remove directories from being watched.
//!
//! The watcher is managed in a separate thread to avoid blocking the UI thread,
//! and updates are sent back via a channel for processing on the UI thread.
//!
//! Special care is taken to manage the `RecommendedWatcher` to prevent heap
//! corruption issues on Windows when used in global static contexts.

use anyhow::{Context, Result};
use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher};
use parking_lot::Mutex;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::Arc;
use std::time::Duration;
use tracing::instrument;

/// The file watcher instance. Wrapped in Option to allow for explicit dropping.
/// Wrapped in Arc<Mutex> for thread-safe shared access.
pub type SharedWatcher = Arc<Mutex<Option<RecommendedWatcher>>>;

/// Holds the sender for file watcher events.
/// Wrapped in Arc<Mutex> for thread-safe shared access.
type SharedEventSender = Arc<Mutex<Option<Sender<notify::Result<Event>>>>>;

/// Global file watcher state.
#[derive(Debug, Clone)] // Add Debug and Clone derive
pub struct FileWatcher {
    /// The actual watcher instance.
    watcher: SharedWatcher,
    /// Sender for events from the watcher thread to the UI thread.
    event_sender: SharedEventSender,
    /// Paths currently being watched.
    watched_paths: Arc<Mutex<HashMap<PathBuf, RecursiveMode>>>,
    /// Flag to indicate if the watcher is paused.
    is_paused: Arc<Mutex<bool>>,
}

impl FileWatcher {
    /// Creates a new, uninitialized FileWatcher instance.
    /// Call `init()` to set up the watcher and start processing events.
    pub fn new() -> Self {
        Self {
            watcher: Arc::new(Mutex::new(None)),
            event_sender: Arc::new(Mutex::new(None)),
            watched_paths: Arc::new(Mutex::new(HashMap::new())),
            is_paused: Arc::new(Mutex::new(false)),
        }
    }

    /// Initializes the file watcher and starts the event loop.
    /// Returns the Receiver for events.
    #[instrument(skip(self))]
    pub fn init(&self) -> Result<Receiver<notify::Result<Event>>> {
        tracing::debug!("Initializing file watcher...");

        let (tx, rx) = channel();

        // Store sender
        *self.event_sender.lock() = Some(tx.clone()); // Clone tx for watcher itself

        // Create the watcher instance
        let watcher = RecommendedWatcher::new(
            tx, // Pass tx to the watcher
            Config::default()
                .with_poll_interval(Duration::from_secs(1)) // Poll every 1 second
                .with_compare_contents(true), // Detect changes even if timestamp is same
        )
        .context("Failed to create file system watcher")?;

        // Store watcher (wrapped in Option for explicit dropping)
        *self.watcher.lock() = Some(watcher);

        Ok(rx) // Return the receiver to the caller
    }

    /// Adds a path to be watched.
    #[instrument(skip(self))]
    pub fn add_path(&self, path: &Path, recursive_mode: RecursiveMode) -> Result<()> {
        let mut watched_paths_guard = self.watched_paths.lock();
        if watched_paths_guard.contains_key(path) {
            tracing::debug!("Path {:?} is already being watched.", path);
            return Ok(());
        }

        let mut watcher_guard = self.watcher.lock();
        if let Some(watcher) = watcher_guard.as_mut() {
            watcher
                .watch(path, recursive_mode)
                .with_context(|| format!("Failed to watch path: {:?}", path))?;
            watched_paths_guard.insert(path.to_path_buf(), recursive_mode);
            tracing::info!("Started watching path: {:?}", path);
            Ok(())
        } else {
            anyhow::bail!("File watcher not initialized.");
        }
    }

    /// Removes a path from being watched.
    #[instrument(skip(self))]
    #[allow(dead_code)]
    pub fn remove_path(&self, path: &Path) -> Result<()> {
        let mut watched_paths_guard = self.watched_paths.lock();
        if !watched_paths_guard.contains_key(path) {
            tracing::debug!("Path {:?} is not being watched.", path);
            return Ok(());
        }

        let mut watcher_guard = self.watcher.lock();
        if let Some(watcher) = watcher_guard.as_mut() {
            watcher
                .unwatch(path)
                .with_context(|| format!("Failed to unwatch path: {:?}", path))?;
            watched_paths_guard.remove(path);
            tracing::info!("Stopped watching path: {:?}", path);
            Ok(())
        } else {
            anyhow::bail!("File watcher not initialized.");
        }
    }

    /// Pauses the file watcher, stopping event processing until resumed.
    #[instrument(skip(self))]
    pub fn pause(&self) {
        *self.is_paused.lock() = true;
        tracing::info!("File watcher paused.");
    }

    /// Resumes the file watcher, allowing event processing to continue.
    #[instrument(skip(self))]
    pub fn resume(&self) {
        *self.is_paused.lock() = false;
        tracing::info!("File watcher resumed.");
    }

    /// Stops the file watcher and clears all watched paths.
    /// This should be called before application exit to ensure proper cleanup,
    /// especially on Windows to prevent heap corruption issues with `notify`.
    #[instrument(skip(self))]
    pub fn stop(&self) {
        let mut watcher_guard = self.watcher.lock();
        if watcher_guard.is_some() {
            // Explicitly drop the watcher to clean up resources
            *watcher_guard = None;
            tracing::info!("File watcher stopped and dropped.");
        }

        let mut watched_paths_guard = self.watched_paths.lock();
        watched_paths_guard.clear();
        tracing::info!("All watched paths cleared.");
    }

    /// Checks if the file watcher is currently paused.
    pub fn is_paused(&self) -> bool {
        *self.is_paused.lock()
    }
}
