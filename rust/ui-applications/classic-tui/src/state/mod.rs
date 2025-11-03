//! Session state management module
//!
//! This module provides functionality for persisting and restoring application state
//! between sessions, including screen positions, scroll offsets, and user selections.

pub mod persistence;
pub mod session;

pub use session::SessionManager;
