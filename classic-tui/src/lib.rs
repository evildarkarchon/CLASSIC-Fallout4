// Library exports for testing and potential reuse
pub mod app;
pub mod events;
pub mod handlers;
pub mod ui;
pub mod widgets;

pub use app::App;
pub use classic_config_core::{ClassicConfig, PathConfig};
pub use events::{ScanMessage, UiMessage};
