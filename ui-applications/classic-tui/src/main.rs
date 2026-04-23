use std::env;
use std::fs;
use std::io::stderr;

use classic_tui::app::App;
use crossterm::cursor::{Hide, Show};
use crossterm::event::{DisableMouseCapture, EnableMouseCapture};
use crossterm::execute;
use crossterm::terminal::{
    EnterAlternateScreen, LeaveAlternateScreen, disable_raw_mode, enable_raw_mode,
};
use directories::ProjectDirs;
use ratatui::Terminal;
use ratatui::backend::CrosstermBackend;
use tracing_appender::non_blocking::WorkerGuard;

struct TerminalStateGuard;

impl TerminalStateGuard {
    fn enter() -> color_eyre::Result<Self> {
        let mut stderr_handle = stderr();
        execute!(
            stderr_handle,
            EnterAlternateScreen,
            EnableMouseCapture,
            Hide
        )?;
        if let Err(error) = enable_raw_mode() {
            let _ = execute!(
                stderr_handle,
                Show,
                DisableMouseCapture,
                LeaveAlternateScreen
            );
            return Err(error.into());
        }

        Ok(Self)
    }
}

impl Drop for TerminalStateGuard {
    fn drop(&mut self) {
        let _ = disable_raw_mode();

        let mut stderr_handle = stderr();
        let _ = execute!(
            stderr_handle,
            Show,
            DisableMouseCapture,
            LeaveAlternateScreen
        );
    }
}

fn main() -> color_eyre::Result<()> {
    color_eyre::install()?;

    if let Some(exit_code) = handle_cli_probe() {
        return exit_code;
    }

    let _log_guard = init_logging();
    let _ = classic_shared_core::get_runtime();

    let _terminal_state = TerminalStateGuard::enter()?;

    let backend = CrosstermBackend::new(stderr());
    let mut terminal = Terminal::new(backend)?;
    let mut app = App::new();

    app.run(&mut terminal)
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
