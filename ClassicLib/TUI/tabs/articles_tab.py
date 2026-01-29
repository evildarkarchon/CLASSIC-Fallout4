"""Articles Tab for CLASSIC TUI.

This tab provides a grid of buttons linking to useful resources and guides.
"""

import webbrowser
from typing import override

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Button, Label, Static

from ClassicLib.TUI.constants import ARTICLE_LINKS


class ArticlesTab(Vertical):
    """Articles tab with grid of resource link buttons.

    Provides quick access to useful resources:
        - Buffout 4 installation guide
        - Fallout 4 setup tips
        - Important patches list
        - Tool download pages (Buffout, CLASSIC, DDS Scanner, etc.)
    """

    DEFAULT_CSS = """
    ArticlesTab {
        padding: 1 2;
    }

    .articles-header {
        text-style: bold;
        color: #4a9eff;
        text-align: center;
        margin-bottom: 2;
    }

    #articles-grid {
        grid-size: 3;
        grid-gutter: 1;
        height: auto;
        margin-bottom: 2;
    }

    #articles-grid Button {
        width: 100%;
        min-height: 3;
    }

    .articles-footer {
        text-align: center;
        color: #808080;
    }
    """

    @override
    def compose(self) -> ComposeResult:
        """Create the articles tab layout.

        Yields:
            Header, 3-column grid of link buttons, and footer instruction.

        """
        yield Label("USEFUL RESOURCES & LINKS", classes="articles-header")

        with Grid(id="articles-grid"):
            for i, link in enumerate(ARTICLE_LINKS):
                yield Button(
                    link["text"],
                    id=f"link-{i}",
                    classes="resource-link",
                )

        yield Static(
            "Press Enter to open selected link in browser",
            classes="articles-footer",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press to open URL in browser.

        Args:
            event: The button pressed event.

        """
        button_id = event.button.id
        if button_id and button_id.startswith("link-"):
            try:
                index = int(button_id.split("-")[1])
                if 0 <= index < len(ARTICLE_LINKS):
                    url = ARTICLE_LINKS[index]["url"]
                    webbrowser.open(url)
                    self.notify(f"Opening: {ARTICLE_LINKS[index]['text']}")
            except (ValueError, IndexError):
                pass
