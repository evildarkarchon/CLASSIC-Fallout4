"""TUI-specific constants and configuration values."""

# Minimum terminal size for proper display
MIN_WIDTH = 80
MIN_HEIGHT = 24

# Recommended terminal size for optimal experience
RECOMMENDED_WIDTH = 120
RECOMMENDED_HEIGHT = 40

# Panel proportions for Results tab (in characters)
REPORT_LIST_WIDTH = 30
REPORT_VIEWER_MIN_WIDTH = 50

# Grid configuration for Articles tab
ARTICLES_GRID_COLUMNS = 3

# Progress bar width (characters)
PROGRESS_BAR_WIDTH = 50

# Papyrus monitoring poll interval (seconds)
PAPYRUS_POLL_INTERVAL = 1.0

# Article links for Resources tab
ARTICLE_LINKS: list[dict[str, str]] = [
    {"text": "BUFFOUT 4 INSTALLATION", "url": "https://www.nexusmods.com/fallout4/articles/3115"},
    {"text": "FALLOUT 4 SETUP TIPS", "url": "https://www.nexusmods.com/fallout4/articles/4141"},
    {"text": "IMPORTANT PATCHES LIST", "url": "https://www.nexusmods.com/fallout4/articles/3769"},
    {"text": "BUFFOUT 4 NEXUS", "url": "https://www.nexusmods.com/fallout4/mods/47359"},
    {"text": "CLASSIC NEXUS", "url": "https://www.nexusmods.com/fallout4/mods/56255"},
    {"text": "CLASSIC GITHUB", "url": "https://github.com/evildarkarchon/CLASSIC-Fallout4"},
    {"text": "DDS TEXTURE SCANNER", "url": "https://www.nexusmods.com/fallout4/mods/71588"},
    {"text": "BETHINI PIE", "url": "https://www.nexusmods.com/site/mods/631"},
    {"text": "WRYE BASH", "url": "https://www.nexusmods.com/fallout4/mods/20032"},
]
