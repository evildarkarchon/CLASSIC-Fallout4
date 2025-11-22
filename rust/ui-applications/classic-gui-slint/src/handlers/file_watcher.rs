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
use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use parking_lot::Mutex;
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver, RecvTimeoutError, Sender};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};
use tracing::{error, info, instrument, warn};

/// The file watcher instance. Wrapped in Option to allow for explicit dropping.
/// Wrapped in Arc<Mutex> for thread-safe shared access.
pub type SharedWatcher = Arc<Mutex<Option<RecommendedWatcher>>>;

/// Holds the sender for file watcher events.
/// Wrapped in Arc<Mutex> for thread-safe shared access.
type SharedEventSender = Arc<Mutex<Option<Sender<Vec<PathBuf>>>>>;

/// Global file watcher state.
#[derive(Debug, Clone)]
pub struct FileWatcher {
    /// The actual watcher instance.
    watcher: SharedWatcher,
    /// Sender for debounced events from the watcher thread to the UI thread.
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

    /// Initializes the file watcher and starts the event loop with debouncing.
    ///
    /// # Arguments
    /// * `debounce_duration` - The time to wait for silence before sending events.
    ///
    /// # Returns
    /// The Receiver for debounced events (list of changed paths).
    #[instrument(skip(self))]
    pub fn init(&self, debounce_duration: Duration) -> Result<Receiver<Vec<PathBuf>>> {
        tracing::debug!("Initializing file watcher with debounce: {:?}", debounce_duration);

        // Channel for the final debounced events sent to UI
        let (ui_tx, ui_rx) = channel();
        
        // Clone tx for the thread BEFORE locking and moving into self
        let ui_tx_thread = ui_tx.clone();
        
        *self.event_sender.lock() = Some(ui_tx);

        // Channel for raw events from notify
        let (raw_tx, raw_rx) = channel();

        // Create the watcher instance
        let watcher = RecommendedWatcher::new(
            raw_tx,
            Config::default()
                .with_poll_interval(Duration::from_secs(1)) // Poll fallback
                .with_compare_contents(true),
        )
        .context("Failed to create file system watcher")?;

        // Store watcher
        *self.watcher.lock() = Some(watcher);

        // Clone state for the thread
        let is_paused = self.is_paused.clone();

        // Spawn the debouncing thread
        thread::spawn(move || {
            tracing::info!("File watcher debounce thread started.");
            
            loop {
                // 1. Block until the first event arrives
                let first_event_result = match raw_rx.recv() {
                    Ok(res) => res,
                    Err(_) => {
                        tracing::info!("File watcher raw channel closed. Thread stopping.");
                        break;
                    }
                };

                // If paused, ignore events but keep loop running
                if *is_paused.lock() {
                    continue;
                }

                // 2. Start accumulation phase
                let mut changed_paths = HashSet::new();
                
                // Process the first event
                match first_event_result {
                    Ok(event) => {
                        process_event(&mut changed_paths, event);
                    }
                    Err(e) => error!("File watcher error: {:?}", e),
                }

                // 3. Debounce loop: wait for silence
                let mut deadline = Instant::now() + debounce_duration;

                loop {
                    let now = Instant::now();
                    if now >= deadline {
                        break; // Timeout reached, flush events
                    }
                    
                    let remaining = deadline - now;

                    match raw_rx.recv_timeout(remaining) {
                        Ok(res) => {
                            // New event arrived!
                            if *is_paused.lock() {
                                continue;
                            }

                            match res {
                                Ok(event) => {
                                    if process_event(&mut changed_paths, event) {
                                        // If relevant paths changed, reset the timer (extend wait)
                                        deadline = Instant::now() + debounce_duration;
                                    }
                                }
                                Err(e) => error!("File watcher error during debounce: {:?}", e),
                            }
                        }
                        Err(RecvTimeoutError::Timeout) => {
                            // Timeout reached (silence), break and flush
                            break;
                        }
                        Err(RecvTimeoutError::Disconnected) => {
                            tracing::info!("File watcher raw channel closed during debounce.");
                            return;
                        }
                    }
                }

                // 4. Send accumulated paths to UI
                if !changed_paths.is_empty() {
                    let paths_vec: Vec<PathBuf> = changed_paths.into_iter().collect();
                    info!("Sending {} file updates to UI.", paths_vec.len());
                    
                    if let Err(e) = ui_tx_thread.send(paths_vec) {
                         warn!("Failed to send updates to UI (receiver dropped): {:?}", e);
                         break; // UI is gone, stop thread
                    }
                }
            }
        });

        Ok(ui_rx)
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

/// Helper to extract paths from an event and add to the set.
/// Returns true if paths were added.
fn process_event(paths: &mut HashSet<PathBuf>, event: Event) -> bool {
    let mut added = false;
    // We are interested in Create, Modify, Remove.
    // Access events might be too noisy? For now let's include them or filter?
    // Usually we care about content changes.
    match event.kind {
        EventKind::Access(_) => return false, // Ignore read access
        _ => {
            for path in event.paths {
                if paths.insert(path) {
                    added = true;
                }
            }
        }
    }
    added
}
