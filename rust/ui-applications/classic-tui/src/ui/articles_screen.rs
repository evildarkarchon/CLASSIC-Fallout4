//! Articles and resources screen with categorized help documentation.
//!
//! This module provides a comprehensive help system with markdown-rendered articles organized
//! into categories (Installation, Common Issues, Advanced Topics, Keyboard Shortcuts). The screen
//! features a two-pane layout with category/article navigation on the left and rendered content
//! on the right, including clickable URL detection and highlighting.
//!
//! # Features
//!
//! - **Categorized Navigation**: Four categories with multiple articles each
//! - **Markdown Rendering**: Full markdown support with headers, bold, italic, lists, code blocks
//! - **URL Detection**: Automatically detects and highlights URLs in markdown content
//! - **Keyboard Navigation**: Arrow keys for selection, Enter to open URLs in browser
//! - **Pre-rendered Cache**: All articles rendered once on first access for 60 FPS performance
//! - **Syntax Highlighting**: Color-coded headers (Cyan), URLs (Yellow), code blocks (Green)
//! - **Scrollable Content**: Long articles support vertical scrolling
//!
//! # Categories
//!
//! - **Installation & Setup**: Getting started with CLASSIC, system requirements, configuration
//! - **Common Issues**: Troubleshooting frequent problems, error messages, solutions
//! - **Advanced Topics**: FCX mode, batch processing, performance tuning, database management
//! - **Keyboard Shortcuts**: Complete reference of all keyboard bindings by screen
//!
//! # Architecture
//!
//! The module uses several optimization strategies:
//! - [`RENDERED_ARTICLES_CACHE`]: Global OnceLock cache initialized on first access
//! - Pre-rendering: All markdown parsed once at startup, not every frame (30 FPS rendering loop)
//! - Cache key: `(ArticleCategory, &'static str)` tuple for self-documenting, order-independent lookups
//! - URL tracking: Each article tracks detected URLs with line numbers for keyboard navigation
//!
//! # Layout
//!
//! The screen is divided into two main horizontal sections:
//! - **Left Pane** (30%): Category tabs + Article list with selection highlight
//! - **Right Pane** (70%): Rendered markdown content with scrolling support
//!
//! The left pane contains:
//! - Tab bar (3 lines): Category tabs with active tab underlined
//! - Article list (flexible): Scrollable list of article titles in current category
//! - Instructions (3 lines): Keyboard shortcuts reference
//!
//! # Navigation
//!
//! - **↑/↓**: Navigate between articles in current category
//! - **Left/Right**: Switch between categories
//! - **Enter**: Open currently highlighted URL in browser (if URL navigation is active)
//! - **Tab**: Cycle through detected URLs in current article
//! - **ESC**: Return to main screen
//!
//! # URL Navigation
//!
//! When an article contains URLs (detected via markdown or inline text):
//! 1. URLs are highlighted in Yellow with (n) indicator
//! 2. Press Tab to cycle through URLs
//! 3. Press Enter to open currently selected URL in default browser
//! 4. URL counter shows "[URL X/Y]" in article title bar
//!
//! # Example
//!
//! ```rust,no_run
//! use classic_tui::ui::articles_screen::render_articles_screen;
//! use classic_tui::app::App;
//! use ratatui::backend::CrosstermBackend;
//! use ratatui::Terminal;
//! use std::io;
//!
//! let mut terminal = Terminal::new(CrosstermBackend::new(io::stdout())).unwrap();
//! let app = App::new();
//!
//! terminal.draw(|f| {
//!     render_articles_screen(f, &app, &app.articles_state);
//! }).unwrap();
//! ```
//!
//! # Performance
//!
//! - Pre-rendering eliminates markdown parsing overhead (30 FPS target)
//! - Cache key structure: `(category, title)` for O(1) HashMap lookup with self-documenting keys
//! - Static cache shared across all App instances (useful for testing)
//! - Articles loaded lazily but cached permanently after first access
//!
//! # Cache Design
//!
//! The `RENDERED_ARTICLES_CACHE` uses article titles as cache keys: `(ArticleCategory, &'static str)`.
//! This approach provides several advantages:
//! - **Self-documenting**: Cache keys directly show which article they reference
//! - **Order-independent**: Article ordering doesn't affect cache validity
//! - **O(n) initialization**: Direct title lookup vs. O(n²) position search
//! - **Robust**: Adding/removing articles doesn't invalidate existing cache entries

use crate::app::App;
use crate::widgets::markdown_viewer::{MarkdownRenderer, RenderedMarkdown};
use ratatui::{
    Frame,
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
};
use std::collections::HashMap;
use std::sync::OnceLock;

/// Global cache for pre-rendered markdown articles
///
/// This cache is initialized once on first access and contains all articles
/// with their markdown pre-rendered. This avoids re-parsing markdown on every frame (~30 FPS).
/// Uses article titles as cache keys for self-documenting, order-independent lookups.
///
/// # Cache Invalidation Design
///
/// This cache is **intentionally never invalidated** because all articles are embedded
/// static content (`&'static str`) that cannot change at runtime. This design provides
/// optimal performance with no memory overhead for invalidation mechanisms.
///
/// **If articles become dynamic in the future**, replace `OnceLock` with one of:
/// - `LazyLock<RwLock<HashMap<...>>>` for manual invalidation
/// - Event-based cache clearing on content updates
/// - TTL-based expiration for periodically-updated content
static RENDERED_ARTICLES_CACHE: OnceLock<
    HashMap<(ArticleCategory, &'static str), RenderedMarkdown>,
> = OnceLock::new();

/// Global cache for article title lookups (String -> &'static str)
///
/// This cache enables O(1) lookups when restoring session state, where we have
/// a String title from serialization and need the &'static str reference.
static ARTICLE_TITLE_MAP: OnceLock<HashMap<String, &'static str>> = OnceLock::new();

/// Get the article title map, initializing it if necessary
///
/// This map provides O(1) lookups from String titles to &'static str references,
/// used primarily during session restoration to avoid O(n) linear searches.
pub fn get_article_title_map() -> &'static HashMap<String, &'static str> {
    ARTICLE_TITLE_MAP.get_or_init(|| {
        let mut map = HashMap::new();

        // Build map from all articles - O(n) initialization
        for article in get_all_articles() {
            map.insert(article.title.to_string(), article.title);
        }

        map
    })
}

/// Get the rendered articles cache, initializing it if necessary
fn get_rendered_articles_cache()
-> &'static HashMap<(ArticleCategory, &'static str), RenderedMarkdown> {
    RENDERED_ARTICLES_CACHE.get_or_init(|| {
        let mut cache = HashMap::new();

        // Pre-render all articles - O(n) initialization using titles as keys
        for article in get_all_articles() {
            let key = (article.category, article.title);
            // Create a new renderer for each article since render() consumes self
            let renderer = MarkdownRenderer::new();
            let rendered = renderer.render(article.content);
            cache.insert(key, rendered);
        }

        cache
    })
}

/// Article category
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ArticleCategory {
    /// Installation and setup guides
    Installation,
    /// Common issues and troubleshooting
    CommonIssues,
    /// Advanced topics and configuration
    Advanced,
    /// Keyboard shortcuts reference
    Shortcuts,
}

impl ArticleCategory {
    /// Get all categories
    pub fn all() -> Vec<Self> {
        vec![
            Self::Installation,
            Self::CommonIssues,
            Self::Advanced,
            Self::Shortcuts,
        ]
    }

    /// Get category name
    pub fn name(&self) -> &'static str {
        match self {
            Self::Installation => "Installation & Setup",
            Self::CommonIssues => "Common Issues",
            Self::Advanced => "Advanced Topics",
            Self::Shortcuts => "Keyboard Shortcuts",
        }
    }

    /// Get next category
    pub fn next(&self) -> Self {
        match self {
            Self::Installation => Self::CommonIssues,
            Self::CommonIssues => Self::Advanced,
            Self::Advanced => Self::Shortcuts,
            Self::Shortcuts => Self::Installation,
        }
    }

    /// Get previous category
    pub fn prev(&self) -> Self {
        match self {
            Self::Installation => Self::Shortcuts,
            Self::CommonIssues => Self::Installation,
            Self::Advanced => Self::CommonIssues,
            Self::Shortcuts => Self::Advanced,
        }
    }
}

/// Article content with markdown
#[derive(Debug, Clone)]
pub struct Article {
    /// Article title displayed in the list
    pub title: &'static str,
    /// Markdown content of the article
    pub content: &'static str,
    /// Category this article belongs to
    pub category: ArticleCategory,
}

impl Article {
    /// Create a new article
    pub const fn new(
        title: &'static str,
        content: &'static str,
        category: ArticleCategory,
    ) -> Self {
        Self {
            title,
            content,
            category,
        }
    }
}

/// Get all articles
pub fn get_all_articles() -> Vec<Article> {
    vec![
        // Installation articles
        Article::new(
            "Getting Started",
            "# Getting Started with CLASSIC\n\n\
            **CLASSIC** (Crash Log Auto Scanner & Setup Integrity Checker) analyzes crash logs from Bethesda games.\n\n\
            ## Quick Start\n\n\
            1. Configure paths in **Settings** (`Ctrl+O`)\n\
            2. Press `F5` to scan crash logs\n\
            3. Press `F9` to view results\n\n\
            ## TUI Interfaces\n\n\
            The TUI provides multiple screens:\n\n\
            - **Main screen**: Scan operations and output\n\
            - **Settings**: Configuration management\n\
            - **Results**: View and search analysis reports\n\
            - **Backup**: Manage XSE/ENB/ReShade backups\n\
            - **Articles**: This help documentation\n\n\
            ## External Resources\n\n\
            - [GitHub Repository](https://github.com/evildarkarchon/CLASSIC-Fallout4)\n\
            - [Nexus Mods Page](https://www.nexusmods.com/fallout4/mods/56255)",
            ArticleCategory::Installation,
        ),
        Article::new(
            "Configuration",
            "Essential settings to configure:\n\n\
            Paths Tab:\n\
            - Game Root: Fallout 4 installation directory\n\
            - Docs Root: Documents/My Games/Fallout4\n\
            - Mods Folder: Mod organizer folder (optional)\n\
            - Custom Scan: Alternative crash logs location\n\n\
            General Tab:\n\
            - FCX Mode: Enhanced FormID analysis\n\
            - Show FormID Values: Display FormID values in output\n\
            - Stat Logging: Enable statistics\n\
            - Move Unsolved Logs: Organize unresolved crashes\n\n\
            Press 'S' to save configuration.",
            ArticleCategory::Installation,
        ),
        // Common issues articles
        Article::new(
            "No Reports Found",
            "## Crash Reports Not Found\n\n\
            If CLASSIC can't find crash reports:\n\n\
            1. Check **Docs Root** path in Settings (`Ctrl+O`)\n\
            2. Verify crash logs exist in `Documents/My Games/Fallout4/F4SE/`\n\
            3. Run a game crash first to generate logs\n\
            4. Try setting a **Custom Scan** path\n\n\
            ### Requirements\n\n\
            **Important**: Crash logs are *only* generated if you have these installed:\n\n\
            - [F4SE (Fallout 4 Script Extender)](https://f4se.silverlock.org/)\n\
            - [Buffout 4](https://www.nexusmods.com/fallout4/mods/47359) or similar crash logger\n\n\
            Without these tools, Fallout 4 will not generate detailed crash logs that CLASSIC can analyze.",
            ArticleCategory::CommonIssues,
        ),
        Article::new(
            "Scan Takes Too Long",
            "If scanning is slow:\n\n\
            1. Check Advanced settings (coming soon)\n\
            2. Reduce batch size for incremental progress\n\
            3. Close other resource-intensive applications\n\
            4. Consider using smaller log file sets\n\n\
            Note: First scan builds database cache and may be slower.",
            ArticleCategory::CommonIssues,
        ),
        // Advanced topics
        Article::new(
            "Papyrus Monitoring",
            "Real-time Papyrus script monitoring:\n\n\
            1. Press F7 to start monitoring\n\
            2. View live statistics (FPS, stack dumps, suspends)\n\
            3. See recent log lines\n\
            4. Press F7 again to stop\n\n\
            Useful for:\n\
            - Detecting script overload\n\
            - Identifying problematic mods\n\
            - Performance debugging",
            ArticleCategory::Advanced,
        ),
        Article::new(
            "Backup Operations",
            "Backup critical game files:\n\n\
            Press F8 to access backup screen.\n\n\
            Supported backups:\n\
            - XSE (F4SE) plugins\n\
            - ReShade files\n\
            - Vulkan layers\n\
            - ENB files\n\n\
            Keys:\n\
            - 1-4: Create backup\n\
            - 5-8: Restore backup\n\
            - 9,0,-,=: Remove backup\n\
            - R: Refresh status",
            ArticleCategory::Advanced,
        ),
        // Keyboard shortcuts
        Article::new(
            "Navigation Keys",
            "Global Shortcuts:\n\
            - F1: Help screen\n\
            - F5: Start crash log scan\n\
            - F6: Start game files scan\n\
            - F7: Toggle Papyrus monitoring\n\
            - F8: Backup operations\n\
            - F9: Results viewer\n\
            - F10: Articles/Resources (this screen)\n\
            - Ctrl+O: Settings\n\
            - Ctrl+L: Clear output\n\
            - Q: Quit application\n\
            - ESC: Return to main screen",
            ArticleCategory::Shortcuts,
        ),
        Article::new(
            "Screen-Specific Keys",
            "Settings Screen:\n\
            - Tab/Shift+Tab: Switch tabs\n\
            - ↑↓: Navigate settings\n\
            - Space/Enter: Toggle or edit\n\
            - R: Reset current tab\n\
            - S: Save settings\n\n\
            Results Screen:\n\
            - ↑↓: Select report\n\
            - PgUp/PgDn: Scroll report\n\
            - /: Start search\n\
            - n/N: Navigate search results\n\
            - R: Refresh reports",
            ArticleCategory::Shortcuts,
        ),
    ]
}

/// Get articles for a specific category
pub fn get_articles_by_category(category: ArticleCategory) -> Vec<Article> {
    get_all_articles()
        .into_iter()
        .filter(|a| a.category == category)
        .collect()
}

/// Articles screen state
#[derive(Debug, Clone)]
pub struct ArticlesState {
    /// Currently selected category
    pub selected_category: ArticleCategory,
    /// Currently selected article title within category
    pub selected_article_title: Option<&'static str>,
    /// Scroll offset for article content
    pub scroll_offset: usize,
    /// Currently selected link index (None if no link selected)
    pub selected_link_index: Option<usize>,
}

impl Default for ArticlesState {
    fn default() -> Self {
        // Select first article in Installation category
        let first_article = get_articles_by_category(ArticleCategory::Installation)
            .first()
            .map(|a| a.title);

        Self {
            selected_category: ArticleCategory::Installation,
            selected_article_title: first_article,
            scroll_offset: 0,
            selected_link_index: None,
        }
    }
}

impl ArticlesState {
    /// Create new articles state
    pub fn new() -> Self {
        Self::default()
    }

    /// Get current article's URLs from pre-rendered cache
    pub fn get_current_urls(&self) -> Vec<String> {
        if let Some(title) = self.selected_article_title {
            let cache = get_rendered_articles_cache();
            let key = (self.selected_category, title);
            if let Some(rendered) = cache.get(&key) {
                return rendered.urls.iter().map(|u| u.url.clone()).collect();
            }
        }
        Vec::new()
    }

    /// Switch to next category
    pub fn next_category(&mut self) {
        self.selected_category = self.selected_category.next();
        self.selected_article_title = get_articles_by_category(self.selected_category)
            .first()
            .map(|a| a.title);
        self.scroll_offset = 0;
        self.selected_link_index = None;
    }

    /// Switch to previous category
    pub fn prev_category(&mut self) {
        self.selected_category = self.selected_category.prev();
        self.selected_article_title = get_articles_by_category(self.selected_category)
            .first()
            .map(|a| a.title);
        self.scroll_offset = 0;
        self.selected_link_index = None;
    }

    /// Select next article
    pub fn next_article(&mut self) {
        let articles = get_articles_by_category(self.selected_category);
        if articles.is_empty() {
            return;
        }

        // Find current article index and select next
        if let Some(current_title) = self.selected_article_title {
            if let Some(current_idx) = articles.iter().position(|a| a.title == current_title) {
                let next_idx = (current_idx + 1) % articles.len();
                self.selected_article_title = articles.get(next_idx).map(|a| a.title);
            }
        } else {
            // No article selected, select first
            self.selected_article_title = articles.first().map(|a| a.title);
        }

        self.scroll_offset = 0;
        self.selected_link_index = None;
    }

    /// Select previous article
    pub fn prev_article(&mut self) {
        let articles = get_articles_by_category(self.selected_category);
        if articles.is_empty() {
            return;
        }

        // Find current article index and select previous
        if let Some(current_title) = self.selected_article_title {
            if let Some(current_idx) = articles.iter().position(|a| a.title == current_title) {
                let prev_idx = if current_idx == 0 {
                    articles.len() - 1
                } else {
                    current_idx - 1
                };
                self.selected_article_title = articles.get(prev_idx).map(|a| a.title);
            }
        } else {
            // No article selected, select last
            self.selected_article_title = articles.last().map(|a| a.title);
        }

        self.scroll_offset = 0;
        self.selected_link_index = None;
    }

    /// Select next link in current article
    pub fn next_link(&mut self) {
        let urls = self.get_current_urls();
        if urls.is_empty() {
            return;
        }

        self.selected_link_index = Some(match self.selected_link_index {
            None => 0,
            Some(idx) => (idx + 1) % urls.len(),
        });
    }

    /// Select previous link in current article
    pub fn prev_link(&mut self) {
        let urls = self.get_current_urls();
        if urls.is_empty() {
            return;
        }

        self.selected_link_index = Some(match self.selected_link_index {
            None => urls.len().saturating_sub(1),
            Some(0) => urls.len().saturating_sub(1),
            Some(idx) => idx - 1,
        });
    }

    /// Get currently selected link URL
    pub fn get_selected_link_url(&mut self) -> Option<String> {
        if let Some(link_idx) = self.selected_link_index {
            let urls = self.get_current_urls();
            urls.get(link_idx).cloned()
        } else {
            None
        }
    }

    /// Scroll content up
    pub fn scroll_up(&mut self, lines: usize) {
        self.scroll_offset = self.scroll_offset.saturating_sub(lines);
    }

    /// Scroll content down
    pub fn scroll_down(&mut self, lines: usize, max_lines: usize) {
        if let Some(title) = self.selected_article_title {
            let cache = get_rendered_articles_cache();
            let key = (self.selected_category, title);
            if let Some(rendered) = cache.get(&key) {
                let content_lines = rendered.lines.len();
                let max_scroll = content_lines.saturating_sub(max_lines);
                self.scroll_offset = (self.scroll_offset + lines).min(max_scroll);
            }
        }
    }
}

/// Render the articles screen
pub fn render_articles_screen(f: &mut Frame, app: &App, state: &ArticlesState) {
    let mut working_area = f.area();

    // Render update notification banner if visible (at top)
    if let Some(ref notification) = app.update_notification
        && notification.is_visible()
    {
        notification.render(f, working_area);
        // Adjust working area to account for banner height
        working_area = Rect {
            x: working_area.x,
            y: working_area.y + notification.height(),
            width: working_area.width,
            height: working_area.height.saturating_sub(notification.height()),
        };
    }

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Header
            Constraint::Min(10),   // Content area
            Constraint::Length(3), // Status bar
        ])
        .split(working_area);

    // Header
    render_header(f, chunks[0]);

    // Content area - split into categories, articles list, and viewer
    let content_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(20), // Categories
            Constraint::Percentage(30), // Articles list
            Constraint::Percentage(50), // Article viewer
        ])
        .split(chunks[1]);

    render_categories(f, content_chunks[0], state);
    render_articles_list(f, content_chunks[1], state);
    render_article_viewer(f, content_chunks[2], state);

    // Status bar
    render_status_bar(f, chunks[2], state);

    // Render error dialog overlay if active (should be last so it appears on top)
    if let Some(ref dialog) = app.error_dialog
        && dialog.is_active()
    {
        dialog.render(f, f.area());
    }
}

/// Render header
fn render_header(f: &mut Frame, area: Rect) {
    let title = Paragraph::new(Line::from(vec![
        Span::styled(
            "CLASSIC - ",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            "Articles & Resources",
            Style::default()
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        ),
    ]))
    .alignment(Alignment::Center)
    .block(Block::default().borders(Borders::ALL));

    f.render_widget(title, area);
}

/// Render categories list
fn render_categories(f: &mut Frame, area: Rect, state: &ArticlesState) {
    let categories: Vec<ListItem> = ArticleCategory::all()
        .iter()
        .map(|cat| {
            let style = if *cat == state.selected_category {
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };

            let prefix = if *cat == state.selected_category {
                "> "
            } else {
                "  "
            };

            ListItem::new(format!("{}{}", prefix, cat.name())).style(style)
        })
        .collect();

    let list = List::new(categories).block(
        Block::default()
            .borders(Borders::ALL)
            .title(" Categories ")
            .border_style(Style::default().fg(Color::Cyan)),
    );

    f.render_widget(list, area);
}

/// Render articles list
fn render_articles_list(f: &mut Frame, area: Rect, state: &ArticlesState) {
    let articles = get_articles_by_category(state.selected_category);

    let items: Vec<ListItem> = articles
        .iter()
        .map(|article| {
            let is_selected = state.selected_article_title == Some(article.title);

            let style = if is_selected {
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };

            let prefix = if is_selected { "> " } else { "  " };

            ListItem::new(format!("{}{}", prefix, article.title)).style(style)
        })
        .collect();

    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .title(format!(" {} ", state.selected_category.name()))
            .border_style(Style::default().fg(Color::Cyan)),
    );

    f.render_widget(list, area);
}

/// Render article viewer with markdown
fn render_article_viewer(f: &mut Frame, area: Rect, state: &ArticlesState) {
    let content = if let Some(title) = state.selected_article_title {
        // Get pre-rendered markdown from cache
        let cache = get_rendered_articles_cache();
        let key = (state.selected_category, title);
        let rendered = cache.get(&key).expect("Article not found in cache");

        // Take lines from scroll offset
        let lines: Vec<Line> = rendered
            .lines
            .iter()
            .skip(state.scroll_offset)
            .cloned()
            .collect();

        // Show link count if any links present
        let title_text = if rendered.urls.is_empty() {
            format!(" {} ", title)
        } else {
            let selected_indicator = state
                .selected_link_index
                .map(|idx| format!(" (Link {}/{}) ", idx + 1, rendered.urls.len()))
                .unwrap_or_default();
            format!(" {} {} ", title, selected_indicator)
        };

        Paragraph::new(lines).wrap(Wrap { trim: false }).block(
            Block::default()
                .borders(Borders::ALL)
                .title(title_text)
                .border_style(Style::default().fg(Color::Cyan)),
        )
    } else {
        Paragraph::new("No article selected")
            .alignment(Alignment::Center)
            .block(Block::default().borders(Borders::ALL))
    };

    f.render_widget(content, area);
}

/// Render status bar
fn render_status_bar(f: &mut Frame, area: Rect, state: &ArticlesState) {
    let has_links = !state.get_current_urls().is_empty();

    let mut hint_spans = vec![
        Span::styled("ESC", Style::default().fg(Color::Yellow)),
        Span::raw(" Back | "),
        Span::styled("←→", Style::default().fg(Color::Yellow)),
        Span::raw(" Category | "),
        Span::styled("↑↓", Style::default().fg(Color::Yellow)),
        Span::raw(" Article | "),
        Span::styled("PgUp/PgDn", Style::default().fg(Color::Yellow)),
        Span::raw(" Scroll"),
    ];

    if has_links {
        hint_spans.extend_from_slice(&[
            Span::raw(" | "),
            Span::styled("Tab", Style::default().fg(Color::Yellow)),
            Span::raw(" Next Link | "),
            Span::styled("Enter", Style::default().fg(Color::Yellow)),
            Span::raw(" Open Link"),
        ]);
    }

    hint_spans.extend_from_slice(&[
        Span::raw(" | "),
        Span::styled("Q", Style::default().fg(Color::Yellow)),
        Span::raw(" Quit"),
    ]);

    let hints = Line::from(hint_spans);

    let status = Paragraph::new(hints)
        .alignment(Alignment::Center)
        .block(Block::default().borders(Borders::ALL));

    f.render_widget(status, area);
}
