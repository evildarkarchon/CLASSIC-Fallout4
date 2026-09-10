pub mod app;
pub mod event;
pub mod results_markdown;
mod scan_run;
// The scan-run module itself stays private, but one of its types crosses into the public surface:
// `App` hands out flattened display lines, and their severity is what `ui.rs` colours by.
pub use scan_run::PresentedLine;
pub mod state;
pub mod tabs;
pub mod theme;
pub mod ui;
pub mod widgets;
