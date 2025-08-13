# CLASSIC TUI Developer Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Widget Development](#widget-development)
5. [Screen Development](#screen-development)
6. [Handler Implementation](#handler-implementation)
7. [Testing Strategy](#testing-strategy)
8. [Performance Considerations](#performance-considerations)
9. [Extension Points](#extension-points)
10. [Contributing Guidelines](#contributing-guidelines)

## Architecture Overview

### Design Principles

The CLASSIC TUI follows these architectural principles:

1. **Separation of Concerns**: UI, business logic, and data handling are separated
2. **Async-First**: All I/O operations use async/await patterns
3. **Composition over Inheritance**: Widgets are composed rather than deeply inherited
4. **Event-Driven**: User interactions trigger events handled by specific methods
5. **Testability**: Components are designed for easy unit and integration testing

### Technology Stack

- **Framework**: Textual 0.47+ (Terminal UI framework)
- **Async Runtime**: Python asyncio
- **Testing**: pytest with textual testing extensions
- **Type Checking**: mypy with strict typing
- **Styling**: Textual CSS

### Component Hierarchy

```
CLASSICTuiApp (Main Application)
├── Header (Built-in)
├── MainScreen (Primary Interface)
│   ├── FolderSelector (Widget)
│   ├── ScanButton (Widget)
│   └── OutputViewer (Widget)
├── StatusBar (Custom Widget)
└── Footer (Built-in)

Modal Screens:
├── HelpScreen
├── SettingsScreen
└── Confirmation Dialogs
```

## Project Structure

```
ClassicLib/TUI/
├── __init__.py
├── app.py                 # Main application class
├── screens/              # Screen components
│   ├── __init__.py
│   ├── main_screen.py    # Primary interface
│   ├── help_screen.py    # Help documentation
│   └── settings_screen.py # Settings configuration
├── widgets/              # Reusable widgets
│   ├── __init__.py
│   ├── folder_selector.py
│   ├── scan_buttons.py
│   ├── output_viewer.py
│   ├── status_bar.py
│   ├── progress_bar.py
│   └── confirmation_dialog.py
├── handlers/             # Business logic handlers
│   ├── __init__.py
│   ├── scan_handler.py   # Scan operations
│   └── message_handler.py # Message routing
└── themes/               # Visual themes
    └── __init__.py
```

## Core Components

### Application Class (app.py)

The main application class manages:
- Global keyboard bindings
- Screen navigation
- Application lifecycle
- CSS styling

```python
class CLASSICTuiApp(App):
    """Main TUI application."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f1", "show_help", "Help"),
        # ... more bindings
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        yield MainScreen()
        yield StatusBar()
        yield Footer()
```

### Screen Development

Screens are full-window components that manage a complete interface:

```python
class CustomScreen(Screen):
    """Custom screen implementation."""
    
    def compose(self) -> ComposeResult:
        """Build the screen layout."""
        with Container():
            yield Label("Screen Title")
            yield CustomWidget()
    
    def on_mount(self) -> None:
        """Initialize when screen mounts."""
        self._load_data()
        self._setup_handlers()
```

### Widget Development

Widgets are reusable UI components:

```python
class CustomWidget(Static):
    """Custom widget implementation."""
    
    DEFAULT_CSS = """
    CustomWidget {
        height: auto;
        padding: 1;
    }
    """
    
    # Reactive attributes for state management
    value = reactive("")
    
    def compose(self) -> ComposeResult:
        """Compose widget structure."""
        yield Input(placeholder="Enter value")
    
    def watch_value(self, old_value: str, new_value: str) -> None:
        """React to value changes."""
        self.update_display()
```

## Widget Development

### Creating Custom Widgets

#### 1. Basic Widget Structure

```python
from textual.widget import Widget
from textual.reactive import reactive

class MyWidget(Widget):
    """Custom widget with reactive state."""
    
    # Define reactive properties
    count = reactive(0)
    
    def render(self) -> str:
        """Render widget content."""
        return f"Count: {self.count}"
    
    def on_click(self) -> None:
        """Handle click events."""
        self.count += 1
```

#### 2. Composite Widgets

```python
class CompositeWidget(Static):
    """Widget composed of other widgets."""
    
    def compose(self) -> ComposeResult:
        """Build widget composition."""
        with Horizontal():
            yield Label("Status:")
            yield Button("Action", id="action-btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button events."""
        if event.button.id == "action-btn":
            self.perform_action()
```

#### 3. Async Operations in Widgets

```python
class AsyncWidget(Static):
    """Widget with async operations."""
    
    async def load_data(self) -> None:
        """Load data asynchronously."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                self.update_display(data)
    
    def on_mount(self) -> None:
        """Start async operations on mount."""
        self.call_later(self.load_data)
```

### Widget Communication

#### Event Bubbling

```python
class ChildWidget(Widget):
    """Emits custom events."""
    
    class DataChanged(Message):
        """Custom event message."""
        def __init__(self, data: str) -> None:
            self.data = data
            super().__init__()
    
    def notify_change(self, data: str) -> None:
        """Emit custom event."""
        self.post_message(self.DataChanged(data))

class ParentWidget(Widget):
    """Handles child events."""
    
    def on_child_widget_data_changed(self, event: ChildWidget.DataChanged) -> None:
        """Handle child's custom event."""
        self.process_data(event.data)
```

## Screen Development

### Modal Screens

Modal screens overlay the main interface:

```python
class ModalDialog(ModalScreen[bool]):
    """Modal dialog that returns a result."""
    
    def compose(self) -> ComposeResult:
        """Build modal layout."""
        with Container():
            yield Label("Confirm action?")
            yield Button("Yes", id="confirm")
            yield Button("No", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

# Usage
result = await app.push_screen_wait(ModalDialog())
if result:
    # User confirmed
```

### Screen Navigation

```python
class NavigationApp(App):
    """App with screen navigation."""
    
    def on_mount(self) -> None:
        """Setup initial screen."""
        self.push_screen(MainScreen())
    
    def navigate_to_settings(self) -> None:
        """Navigate to settings screen."""
        self.push_screen(SettingsScreen())
    
    def go_back(self) -> None:
        """Return to previous screen."""
        self.pop_screen()
```

## Handler Implementation

### Scan Handler Pattern

```python
class TuiScanHandler:
    """Handles scan operations for TUI."""
    
    def __init__(self, app: App, output: OutputViewer):
        self.app = app
        self.output = output
        self.scanner = None
    
    async def perform_crash_scan(self) -> None:
        """Execute crash log scan."""
        try:
            # Update UI state
            self.app.query_one(StatusBar).update_status("Scanning...")
            
            # Initialize scanner
            self.scanner = ClassicScanLogs()
            
            # Configure message handler
            handler = TuiMessageHandler(self.output)
            
            # Run scan
            result = await self.scanner.scan_logs_async()
            
            # Process results
            await self.process_results(result)
            
        except Exception as e:
            await self.output.write(f"Error: {e}", style="error")
        finally:
            self.app.query_one(StatusBar).mark_scan_complete()
```

### Message Handler Pattern

```python
class TuiMessageHandler:
    """Routes messages to TUI output."""
    
    def __init__(self, output: OutputViewer):
        self.output = output
    
    async def send_message(self, message: str, level: str = "info") -> None:
        """Send message to output with appropriate styling."""
        style_map = {
            "error": "red",
            "warning": "yellow",
            "success": "green",
            "info": "blue"
        }
        await self.output.write(message, style=style_map.get(level))
    
    async def update_progress(self, current: int, total: int, message: str) -> None:
        """Update progress display."""
        percentage = (current / total) * 100 if total > 0 else 0
        await self.output.write(f"[{percentage:.1f}%] {message}")
```

## Testing Strategy

### Unit Testing Widgets

```python
import pytest
from textual.app import App

class TestCustomWidget:
    """Test custom widget functionality."""
    
    @pytest.mark.asyncio
    async def test_widget_initialization(self):
        """Test widget initializes correctly."""
        async with App().run_test() as pilot:
            widget = CustomWidget()
            pilot.app.mount(widget)
            
            assert widget.value == "initial"
            assert widget.query_one(Input) is not None
    
    @pytest.mark.asyncio
    async def test_widget_interaction(self):
        """Test widget responds to interaction."""
        async with App().run_test() as pilot:
            widget = CustomWidget()
            pilot.app.mount(widget)
            
            # Simulate user input
            await pilot.click(widget.query_one(Button))
            
            # Verify state change
            assert widget.value == "clicked"
```

### Integration Testing

```python
class TestScreenIntegration:
    """Test screen integration."""
    
    @pytest.mark.asyncio
    async def test_screen_navigation(self):
        """Test navigation between screens."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Start at main screen
            assert isinstance(app.screen_stack[-1], MainScreen)
            
            # Navigate to settings
            await pilot.press("ctrl+o")
            assert isinstance(app.screen_stack[-1], SettingsScreen)
            
            # Return to main
            await pilot.press("escape")
            assert isinstance(app.screen_stack[-1], MainScreen)
```

### End-to-End Testing

```python
class TestE2EWorkflow:
    """Test complete workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_scan_workflow(self):
        """Test full scan workflow."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Configure settings
            await pilot.press("ctrl+o")
            await pilot.click("#staging-folder")
            await pilot.type("/test/path")
            await pilot.click("#save-settings")
            
            # Run scan
            await pilot.press("f5")
            await asyncio.sleep(0.5)  # Wait for scan
            
            # Verify output
            output = app.query_one(OutputViewer)
            assert len(output._output_buffer) > 0
```

## Performance Considerations

### Optimizing Rendering

```python
class OptimizedWidget(Widget):
    """Widget with optimized rendering."""
    
    def __init__(self):
        super().__init__()
        self._render_cache = None
        self._dirty = True
    
    def render(self) -> str:
        """Cached rendering."""
        if self._dirty:
            self._render_cache = self._expensive_render()
            self._dirty = False
        return self._render_cache
    
    def invalidate(self) -> None:
        """Mark for re-render."""
        self._dirty = True
        self.refresh()
```

### Async Best Practices

```python
class AsyncBestPractices:
    """Async operation patterns."""
    
    async def batch_operations(self, items: List[str]) -> None:
        """Batch async operations."""
        # Good: Concurrent execution
        tasks = [self.process_item(item) for item in items]
        results = await asyncio.gather(*tasks)
        
        # Bad: Sequential execution
        # for item in items:
        #     await self.process_item(item)
    
    async def with_timeout(self, operation: Coroutine) -> Any:
        """Add timeout to operations."""
        try:
            return await asyncio.wait_for(operation, timeout=30.0)
        except asyncio.TimeoutError:
            self.handle_timeout()
```

### Memory Management

```python
class MemoryEfficientWidget(Widget):
    """Widget with memory management."""
    
    def __init__(self, max_buffer: int = 10000):
        super().__init__()
        self.max_buffer = max_buffer
        self.buffer = deque(maxlen=max_buffer)
    
    def add_content(self, content: str) -> None:
        """Add content with automatic trimming."""
        self.buffer.append(content)
        # Old items automatically removed when maxlen exceeded
```

## Extension Points

### Custom Themes

```python
# themes/custom_theme.py
CUSTOM_THEME = """
App {
    background: $surface;
    color: $text;
}

Button {
    background: $primary;
    color: $text-on-primary;
}

Button:hover {
    background: $primary-lighten-1;
}
"""

# Apply theme in app
class ThemedApp(App):
    CSS = CUSTOM_THEME
```

### Plugin System

```python
class ScanPlugin(ABC):
    """Base class for scan plugins."""
    
    @abstractmethod
    async def analyze(self, log_content: str) -> Dict[str, Any]:
        """Analyze log content."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get plugin name."""
        pass

class PluginManager:
    """Manages scan plugins."""
    
    def __init__(self):
        self.plugins: List[ScanPlugin] = []
    
    def register(self, plugin: ScanPlugin) -> None:
        """Register a plugin."""
        self.plugins.append(plugin)
    
    async def run_plugins(self, content: str) -> Dict[str, Any]:
        """Run all plugins on content."""
        results = {}
        for plugin in self.plugins:
            results[plugin.get_name()] = await plugin.analyze(content)
        return results
```

### Custom Commands

```python
class CommandRegistry:
    """Registry for custom commands."""
    
    def __init__(self):
        self.commands = {}
    
    def register(self, name: str, handler: Callable) -> None:
        """Register a command."""
        self.commands[name] = handler
    
    async def execute(self, name: str, *args, **kwargs) -> Any:
        """Execute a command."""
        if name in self.commands:
            return await self.commands[name](*args, **kwargs)
        raise ValueError(f"Unknown command: {name}")
```

## Contributing Guidelines

### Code Style

1. **Type Hints**: Use type hints for all functions
2. **Docstrings**: Document all classes and public methods
3. **Async/Await**: Use async patterns for I/O operations
4. **Error Handling**: Handle exceptions gracefully
5. **Testing**: Write tests for new features

### Development Workflow

1. **Fork & Clone**: Fork the repository and clone locally
2. **Branch**: Create a feature branch from `main`
3. **Develop**: Implement your feature with tests
4. **Test**: Run the test suite: `pytest tests/`
5. **Lint**: Check code style: `ruff check .`
6. **Document**: Update documentation as needed
7. **PR**: Submit a pull request with description

### Adding New Features

#### 1. New Widget

```python
# widgets/my_widget.py
class MyWidget(Static):
    """New widget implementation."""
    
    def compose(self) -> ComposeResult:
        """Widget composition."""
        pass

# Add to widgets/__init__.py
from .my_widget import MyWidget

# Write tests in tests/test_my_widget.py
```

#### 2. New Screen

```python
# screens/my_screen.py
class MyScreen(Screen):
    """New screen implementation."""
    
    def compose(self) -> ComposeResult:
        """Screen composition."""
        pass

# Add navigation in app.py
def action_show_my_screen(self) -> None:
    """Show my screen."""
    self.push_screen(MyScreen())
```

#### 3. New Handler

```python
# handlers/my_handler.py
class MyHandler:
    """New handler implementation."""
    
    async def process(self, data: Any) -> Any:
        """Process data."""
        pass

# Integrate with existing handlers
```

### Testing Requirements

All new features must include:
1. Unit tests for individual components
2. Integration tests for component interaction
3. Documentation updates
4. Example usage in docstrings

### Performance Guidelines

1. **Lazy Loading**: Load data only when needed
2. **Caching**: Cache expensive computations
3. **Batching**: Batch I/O operations
4. **Limits**: Implement reasonable limits (buffer sizes, etc.)
5. **Profiling**: Profile performance-critical code

## Debugging Tips

### Enable Debug Mode

```python
# Set environment variable
export TEXTUAL_DEBUG=1

# Or in code
import os
os.environ["TEXTUAL_DEBUG"] = "1"
```

### Using the Console

```python
from textual import log

class DebugWidget(Widget):
    """Widget with debug logging."""
    
    def on_mount(self) -> None:
        """Log mount event."""
        log("Widget mounted")
        log(f"State: {self.state}")
```

### Inspector Tool

```bash
# Run with inspector
textual run --dev app.py

# Press Ctrl+D to open inspector
```

## Resources

### Documentation
- [Textual Documentation](https://textual.textualize.io/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [pytest Documentation](https://docs.pytest.org/)

### Examples
- See `tests/` directory for examples
- Check `ClassicLib/TUI/widgets/` for widget patterns
- Review `ClassicLib/TUI/screens/` for screen patterns

### Community
- GitHub Issues for bug reports
- Discussions for feature requests
- Discord for real-time help

## Conclusion

The CLASSIC TUI architecture provides a solid foundation for terminal-based interfaces. Follow the patterns established in existing components, maintain test coverage, and prioritize user experience. The modular design allows for easy extension and modification while maintaining stability.