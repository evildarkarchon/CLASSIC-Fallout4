//! Basic usage example for classic-registry-core.
//!
//! This example demonstrates the core functionality of the global registry:
//! - Registering values
//! - Retrieving values
//! - Using predefined keys
//! - Type-safe access
//! - Convenience functions

use classic_registry_core::{Keys, get, get_game, is_registered, register, set_game};
use std::path::PathBuf;

fn main() {
    println!("=== Classic Registry Core - Basic Usage ===\n");

    // Example 1: Register and retrieve a string
    println!("1. Register and retrieve a string:");
    register(Keys::GAME, "Fallout4".to_string());
    if let Some(game) = get::<_, String>(Keys::GAME) {
        println!("   Game: {}", game);
    }
    println!();

    // Example 2: Check if a key is registered
    println!("2. Check registration:");
    println!(
        "   Is {} registered? {}",
        Keys::GAME,
        is_registered(Keys::GAME)
    );
    println!(
        "   Is {} registered? {}",
        Keys::DOCS_PATH,
        is_registered(Keys::DOCS_PATH)
    );
    println!();

    // Example 3: Register different types
    println!("3. Register different types:");
    register(Keys::IS_GUI_MODE, true);
    register(Keys::LOCAL_DIR, PathBuf::from("/path/to/game"));
    register("custom_count", 42);

    if let Some(gui_mode) = get::<_, bool>(Keys::IS_GUI_MODE) {
        println!("   GUI Mode: {}", gui_mode);
    }
    if let Some(local_dir) = get::<_, PathBuf>(Keys::LOCAL_DIR) {
        println!("   Local Dir: {}", local_dir.display());
    }
    if let Some(count) = get::<_, i32>("custom_count") {
        println!("   Custom Count: {}", count);
    }
    println!();

    // Example 4: Convenience functions
    println!("4. Convenience functions:");
    set_game("Skyrim");
    println!("   Game (via convenience function): {}", get_game());
    println!();

    // Example 5: Type safety
    println!("5. Type safety:");
    register("number", 123);
    let as_int: Option<i32> = get("number");
    let as_string: Option<String> = get("number");
    println!("   Value as i32: {:?}", as_int);
    println!("   Value as String: {:?} (type mismatch!)", as_string);
    println!();

    println!("=== Example Complete ===");
}
