use classic_tui::app::{App, TabIndex};
use classic_tui::tabs::main_tab::MainFocus;
use ratatui::Terminal;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;

#[test]
fn main_tab_default_render_populates_click_areas() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::MainOptions;

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    assert!(app.click_areas.main.scan_crash.width > 0);
    assert!(app.click_areas.main.scan_game.width > 0);
    assert!(app.click_areas.main.staging_input.width > 0);
    assert!(app.click_areas.main.custom_input.width > 0);
}

#[test]
fn main_tab_scan_in_progress_renders_cancel_label() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::MainOptions;
    app.main_focus = MainFocus::ScanCrash;
    app.scan_in_progress = true;

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    let text = buffer_to_text(terminal.backend().buffer());
    assert!(text.contains("CANCEL"));
    assert!(text.contains("SCANNING..."));
}

#[test]
fn backup_tab_renders_table_and_open_button() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::FileBackup;

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    let text = buffer_to_text(terminal.backend().buffer());
    assert!(text.contains("BACKUP / RESTORE / REMOVE"));
    assert!(text.contains("OPEN CLASSIC BACKUPS"));
}

#[test]
fn articles_tab_renders_grid_and_hint() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Articles;

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    let text = buffer_to_text(terminal.backend().buffer());
    assert!(text.contains("USEFUL RESOURCES & LINKS"));
    assert!(text.contains("BUFFOUT 4"));
    assert!(text.contains("Press Enter or click to open in browser"));
    assert!(app.click_areas.articles.cells[0].width > 0);
    assert!(app.click_areas.articles.cells[8].width > 0);
}

#[test]
fn results_tab_empty_state_renders_scan_button() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Results;

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    let text = buffer_to_text(terminal.backend().buffer());
    assert!(text.contains("No scan results"));
    assert!(text.contains("Run a scan to see results here"));
    assert!(text.contains("Scan Crash Logs"));
    assert!(app.click_areas.results.empty_scan_button.width > 0);
}

fn buffer_to_text(buffer: &Buffer) -> String {
    let mut text = String::new();
    let area = buffer.area;
    for y in area.top()..area.bottom() {
        for x in area.left()..area.right() {
            text.push_str(buffer[(x, y)].symbol());
        }
        text.push('\n');
    }
    text
}
