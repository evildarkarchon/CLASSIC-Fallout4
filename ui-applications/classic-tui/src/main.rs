use std::env;
use std::fs;
use std::io::stderr;

use classic_tui::app::App;
use crossterm::cursor::{Hide, Show};
use crossterm::event::{DisableMouseCapture, EnableMouseCapture};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use directories::ProjectDirs;
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;
use tracing_appender::non_blocking::WorkerGuard;

fn main() -> color_eyre::Result<()> {
    color_eyre::install()?;

    if let Some(exit_code) = handle_cli_probe() {
        return exit_code;
    }

    let _log_guard = init_logging();
    let _ = classic_shared_core::get_runtime();

    let mut stderr_handle = stderr();
    execute!(
        stderr_handle,
        EnterAlternateScreen,
        EnableMouseCapture,
        Hide
    )?;
    enable_raw_mode()?;

    let backend = CrosstermBackend::new(stderr());
    let mut terminal = Terminal::new(backend)?;
    let mut app = App::new();

    let result = app.run(&mut terminal);

    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        Show,
        DisableMouseCapture,
        LeaveAlternateScreen
    )?;

    result
}

fn handle_cli_probe() -> Option<color_eyre::Result<()>> {
    for argument in env::args().skip(1) {
        match argument.as_str() {
            "--version" | "-V" => {
                println!("classic-tui {}", env!("CARGO_PKG_VERSION"));
                return Some(Ok(()));
            }
            "--help" | "-h" => {
                println!("classic-tui {}", env!("CARGO_PKG_VERSION"));
                println!("Usage: cargo run -p classic-tui -- [--help] [--version]");
                println!("Launches the CLASSIC terminal UI when no probe flag is provided.");
                return Some(Ok(()));
            }
            _ => {}
        }
    }

    None
}

fn init_logging() -> Option<WorkerGuard> {
    let dirs = ProjectDirs::from("com", "classic", "classic-tui")?;
    let data_dir = dirs.data_local_dir();
    if fs::create_dir_all(data_dir).is_err() {
        return None;
    }

    let log_path = data_dir.join("classic-tui.log");
    let file = fs::File::create(log_path).ok()?;
    let (writer, guard) = tracing_appender::non_blocking(file);

    let subscriber = tracing_subscriber::fmt()
        .with_writer(writer)
        .with_ansi(false)
        .without_time()
        .finish();

    if tracing::subscriber::set_global_default(subscriber).is_err() {
        return None;
    }

    Some(guard)
}
