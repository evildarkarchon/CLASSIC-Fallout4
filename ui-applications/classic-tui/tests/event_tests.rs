use classic_tui::app::{App, Overlay, ReportEntry, TabIndex};
use classic_tui::results_markdown::MarkdownLink;
use classic_tui::tabs::main_tab::MainFocus;
use crossterm::event::{
    Event, KeyCode, KeyEvent, KeyEventKind, KeyEventState, KeyModifiers, MouseButton, MouseEvent,
    MouseEventKind,
};
use ratatui::Terminal;
use ratatui::backend::TestBackend;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

#[test]
fn keyboard_tab_traversal_moves_focus() {
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::MainOptions;
    app.main_focus = MainFocus::StagingInput;

    app.handle_event(Event::Key(KeyEvent::new(KeyCode::Tab, KeyModifiers::NONE)));
    assert_eq!(app.main_focus, MainFocus::StagingBrowse);

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::BackTab,
        KeyModifiers::SHIFT,
    )));
    assert_eq!(app.main_focus, MainFocus::StagingInput);
}

#[test]
fn enter_activates_focused_help_button() {
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::MainOptions;
    app.main_focus = MainFocus::Help;

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Enter,
        KeyModifiers::NONE,
    )));

    assert_eq!(app.active_overlay, Some(Overlay::Help));
}

#[test]
fn mouse_click_hits_help_button() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::MainOptions;

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    let help_area = app.click_areas.main.help;
    let click = MouseEvent {
        kind: MouseEventKind::Down(MouseButton::Left),
        column: help_area.x + 1,
        row: help_area.y + 1,
        modifiers: KeyModifiers::NONE,
    };
    app.handle_event(Event::Mouse(click));

    assert_eq!(app.active_overlay, Some(Overlay::Help));
}

#[test]
fn key_release_events_are_ignored_on_windows_pattern() {
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::MainOptions;
    app.main_focus = MainFocus::StagingInput;

    let release = KeyEvent {
        code: KeyCode::Tab,
        modifiers: KeyModifiers::NONE,
        kind: KeyEventKind::Release,
        state: KeyEventState::NONE,
    };

    app.handle_event(Event::Key(release));
    assert_eq!(app.main_focus, MainFocus::StagingInput);
}

#[test]
fn backup_tab_keyboard_navigation_and_remove_overlay() {
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::FileBackup;
    app.backup_selected_row = 0;

    app.handle_event(Event::Key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE)));
    assert_eq!(app.backup_selected_row, 1);

    app.handle_event(Event::Key(KeyEvent::new(KeyCode::Up, KeyModifiers::NONE)));
    assert_eq!(app.backup_selected_row, 0);

    app.backup_exists[0] = true;
    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Char('d'),
        KeyModifiers::NONE,
    )));

    assert!(matches!(
        app.active_overlay,
        Some(Overlay::ConfirmRemoveBackup(_))
    ));
}

#[test]
fn articles_tab_arrow_keys_wrap_in_2d_grid() {
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Articles;
    app.articles_selected = 0;

    app.handle_event(Event::Key(KeyEvent::new(KeyCode::Left, KeyModifiers::NONE)));
    assert_eq!(app.articles_selected, 2);

    app.handle_event(Event::Key(KeyEvent::new(KeyCode::Up, KeyModifiers::NONE)));
    assert_eq!(app.articles_selected, 8);

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Right,
        KeyModifiers::NONE,
    )));
    assert_eq!(app.articles_selected, 6);

    app.handle_event(Event::Key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE)));
    assert_eq!(app.articles_selected, 0);
}

#[test]
fn articles_tab_enter_and_mouse_open_selected_link() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Articles;
    app.articles_selected = 4;

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Enter,
        KeyModifiers::NONE,
    )));
    assert!(app.scan_status.contains("Opened CLASSIC NEXUS"));

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");
    let area = app.click_areas.articles.cells[0];
    let click = MouseEvent {
        kind: MouseEventKind::Down(MouseButton::Left),
        column: area.x + 1,
        row: area.y + 1,
        modifiers: KeyModifiers::NONE,
    };
    app.handle_event(Event::Mouse(click));

    assert_eq!(app.articles_selected, 0);
    assert!(app.scan_status.contains("Opened BUFFOUT 4 INSTALLATION"));
}

#[test]
fn results_tab_arrow_navigation_and_sort_toggle() {
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Results;
    app.results.reports = vec![
        ReportEntry::new(
            "b-report.md".to_string(),
            PathBuf::from("b-report.md"),
            String::new(),
            "1.0 KB".to_string(),
        ),
        ReportEntry::new(
            "a-report.md".to_string(),
            PathBuf::from("a-report.md"),
            String::new(),
            "1.0 KB".to_string(),
        ),
    ];
    app.apply_results_filter_sort();

    assert_eq!(app.results.selected_filtered, Some(0));

    app.handle_event(Event::Key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE)));
    assert_eq!(app.results.selected_filtered, Some(1));

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Char('s'),
        KeyModifiers::NONE,
    )));
    assert!(app.results.sort_ascending);
}

#[test]
fn results_empty_scan_button_switches_to_main_tab() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Results;

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    let area = app.click_areas.results.empty_scan_button;
    let click = MouseEvent {
        kind: MouseEventKind::Down(MouseButton::Left),
        column: area.x + 1,
        row: area.y + 1,
        modifiers: KeyModifiers::NONE,
    };
    app.handle_event(Event::Mouse(click));

    assert_eq!(app.active_tab, TabIndex::MainOptions);
}

static COPY_CALLED: AtomicBool = AtomicBool::new(false);
static KEYBOARD_URL_CALLED: AtomicBool = AtomicBool::new(false);
static MOUSE_URL_CALLED: AtomicBool = AtomicBool::new(false);

fn copy_writer_test(_text: &str) -> Result<(), String> {
    COPY_CALLED.store(true, Ordering::SeqCst);
    Ok(())
}

fn keyboard_url_opener_test(_url: &str) -> Result<(), String> {
    KEYBOARD_URL_CALLED.store(true, Ordering::SeqCst);
    Ok(())
}

fn mouse_url_opener_test(_url: &str) -> Result<(), String> {
    MOUSE_URL_CALLED.store(true, Ordering::SeqCst);
    Ok(())
}

#[test]
fn results_ctrl_a_invokes_clipboard_writer() {
    COPY_CALLED.store(false, Ordering::SeqCst);

    let mut app = App::new_for_testing();
    app.set_clipboard_writer(copy_writer_test);
    app.active_tab = TabIndex::Results;
    app.results.selected_report_content = "content".to_string();

    let key = KeyEvent::new(KeyCode::Char('a'), KeyModifiers::CONTROL);
    app.handle_event(Event::Key(key));

    assert!(COPY_CALLED.load(Ordering::SeqCst));
    assert!(app.scan_status.contains("Copied to clipboard"));
}

#[test]
fn results_delete_confirmation_removes_selected_file() {
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let path = std::env::temp_dir().join(format!("classic-tui-delete-test-{unique}.md"));
    std::fs::write(&path, "# temp report").expect("create temp report");

    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Results;
    app.results.reports = vec![ReportEntry::new(
        "temp-report.md".to_string(),
        path.clone(),
        String::new(),
        "1.0 KB".to_string(),
    )];
    app.apply_results_filter_sort();

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Delete,
        KeyModifiers::NONE,
    )));
    assert!(matches!(
        app.active_overlay,
        Some(Overlay::ConfirmDeleteReport(_))
    ));

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Enter,
        KeyModifiers::NONE,
    )));
    assert!(!path.exists());
    assert!(app.scan_status.contains("Deleted"));
}

#[test]
fn results_scroll_wheel_updates_scroll_offset_in_viewer() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Results;
    app.results.reports = vec![ReportEntry::new(
        "viewer-test.md".to_string(),
        PathBuf::from("viewer-test.md"),
        String::new(),
        "1.0 KB".to_string(),
    )];
    app.results.filtered_indices = vec![0];
    app.results.selected_filtered = Some(0);
    app.results.rendered_lines = (0..120)
        .map(|i| ratatui::text::Line::from(format!("line-{i}")))
        .collect();
    app.results.total_lines = app.results.rendered_lines.len();

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    let viewer = app.click_areas.results.viewer_area;
    app.handle_event(Event::Mouse(MouseEvent {
        kind: MouseEventKind::ScrollDown,
        column: viewer.x + 1,
        row: viewer.y + 1,
        modifiers: KeyModifiers::NONE,
    }));

    assert!(app.results.scroll_offset > 0);
}

#[test]
fn results_keyboard_link_navigation_and_open() {
    KEYBOARD_URL_CALLED.store(false, Ordering::SeqCst);

    let mut app = App::new_for_testing();
    app.set_url_opener(keyboard_url_opener_test);
    app.active_tab = TabIndex::Results;
    app.results.focus = classic_tui::app::ResultsFocus::Viewer;
    app.results.rendered_lines = vec![
        ratatui::text::Line::from("Link A"),
        ratatui::text::Line::from("Link B"),
    ];
    app.results.total_lines = app.results.rendered_lines.len();
    app.results.rendered_links = vec![
        MarkdownLink {
            index: 0,
            line_index: 0,
            start_col: 0,
            end_col: 4,
            url: "https://example.com/a".to_string(),
            label: "A".to_string(),
        },
        MarkdownLink {
            index: 1,
            line_index: 1,
            start_col: 0,
            end_col: 4,
            url: "https://example.com/b".to_string(),
            label: "B".to_string(),
        },
    ];

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Char('n'),
        KeyModifiers::NONE,
    )));
    assert_eq!(app.results.active_link_index, Some(0));

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Char('n'),
        KeyModifiers::NONE,
    )));
    assert_eq!(app.results.active_link_index, Some(1));

    app.handle_event(Event::Key(KeyEvent::new(
        KeyCode::Enter,
        KeyModifiers::NONE,
    )));
    assert!(KEYBOARD_URL_CALLED.load(Ordering::SeqCst));
    assert!(app.scan_status.contains("Opened link:"));
}

#[test]
fn results_mouse_click_link_opens_url() {
    MOUSE_URL_CALLED.store(false, Ordering::SeqCst);

    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).expect("terminal");
    let mut app = App::new_for_testing();
    app.set_url_opener(mouse_url_opener_test);
    app.active_tab = TabIndex::Results;
    app.results.reports = vec![ReportEntry::new(
        "link-click.md".to_string(),
        PathBuf::from("link-click.md"),
        String::new(),
        "1.0 KB".to_string(),
    )];
    app.results.filtered_indices = vec![0];
    app.results.selected_filtered = Some(0);
    app.results.rendered_lines = vec![ratatui::text::Line::from("open link")];
    app.results.total_lines = 1;
    app.results.rendered_links = vec![MarkdownLink {
        index: 0,
        line_index: 0,
        start_col: 0,
        end_col: 4,
        url: "https://example.com/open".to_string(),
        label: "open".to_string(),
    }];

    terminal
        .draw(|frame| app.render(frame))
        .expect("draw frame");

    let hit = app
        .click_areas
        .results
        .viewer_link_areas
        .first()
        .expect("link area");
    app.handle_event(Event::Mouse(MouseEvent {
        kind: MouseEventKind::Down(MouseButton::Left),
        column: hit.area.x,
        row: hit.area.y,
        modifiers: KeyModifiers::NONE,
    }));

    assert!(MOUSE_URL_CALLED.load(Ordering::SeqCst));
    assert!(app.scan_status.contains("Opened link:"));
}
