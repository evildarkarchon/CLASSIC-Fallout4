//! Shared bridge helpers for CXX FFI.
//!
//! Hosts shared foundation-layer bridge types that belong under the
//! `classic::shared` namespace.

use classic_shared_core::GameId as CoreGameId;

fn from_bridge_game_id(id: ffi::GameId) -> CoreGameId {
    match id {
        ffi::GameId::Fallout4 => CoreGameId::Fallout4,
        ffi::GameId::Fallout4VR => CoreGameId::Fallout4VR,
        ffi::GameId::Skyrim => CoreGameId::Skyrim,
        ffi::GameId::Starfield => CoreGameId::Starfield,
        _ => CoreGameId::Fallout4,
    }
}

fn game_id_as_str(id: ffi::GameId) -> String {
    from_bridge_game_id(id).as_str().to_string()
}

#[cxx::bridge(namespace = "classic::shared")]
mod ffi {
    #[repr(u8)]
    enum GameId {
        Fallout4 = 0,
        Fallout4VR = 1,
        Skyrim = 2,
        Starfield = 3,
    }

    extern "Rust" {
        fn game_id_as_str(id: GameId) -> String;
    }
}

#[cfg(test)]
#[path = "shared_tests.rs"]
mod tests;
