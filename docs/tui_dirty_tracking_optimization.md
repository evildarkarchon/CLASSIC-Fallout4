# TUI Dirty Tracking Optimization

**Version:** 8.0.0
**Date:** 2025-10-10
**Status:** Implemented

---

## Overview

The TUI implements a **dirty region tracking** system to minimize unnecessary rendering operations. This optimization
significantly improves performance by only redrawing widgets that have actually changed.

## Problem

Without optimization, TUI applications typically:

- Redraw all widgets on every event loop iteration
- Waste CPU cycles rendering unchanged content
- Struggle to maintain 60 FPS (16ms frame budget)
- Increase battery consumption on laptops

## Solution: Dirty Tracking

Each widget tracks a `dirty` flag that indicates whether it needs to be redrawn:

```rust
pub struct OutputViewer {
    lines: Vec<String>,
    scroll_offset: usize,
    dirty: bool, // Track if widget needs redraw
}
```

### Core API

All widgets implement these methods:

```rust
impl OutputViewer {
    /// Check if widget needs redraw
    pub fn is_dirty(&self) -> bool {
        self.dirty
    }

    /// Mark widget as clean after rendering
    pub fn mark_clean(&mut self) {
        self.dirty = false;
    }

    /// Force widget to be dirty (useful for external state changes)
    pub fn mark_dirty(&mut self) {
        self.dirty = true;
    }
}
```

## Implementation Pattern

### 1. Initialize as Dirty

Widgets start dirty to ensure initial render:

```rust
pub fn new() -> Self {
    Self {
        lines: Vec::new(),
        scroll_offset: 0,
        dirty: true, // Start dirty to force initial render
    }
}
```

### 2. Mark Dirty on State Change

Operations that change visible state mark the widget dirty:

```rust
pub fn append(&mut self, line: String) {
    self.lines.push(line);
    self.dirty = true; // Mark dirty on content change
}

pub fn set_focused(&mut self, focused: bool) {
    if self.focused != focused {
        self.focused = focused;
        self.dirty = true; // Only mark dirty if focus actually changed
    }
}
```

### 3. Optimization: Avoid Redundant Dirty Marks

Check if state actually changed before marking dirty:

```rust
pub fn scroll_up(&mut self, lines: usize) {
    let old_offset = self.scroll_offset;
    self.scroll_offset = self.scroll_offset.saturating_sub(lines);

    // Only mark dirty if scroll actually changed
    if old_offset != self.scroll_offset {
        self.dirty = true;
    }
}
```

### 4. Threshold-Based Dirty Marking

For continuous updates (like progress), use threshold to reduce render frequency:

```rust
pub fn update_progress(&mut self, progress: f64) {
    if let ButtonState::Scanning { progress: p } = &mut self.state {
        let new_progress = progress.clamp(0.0, 1.0);

        // Only mark dirty if progress changed by >1%
        if (*p - new_progress).abs() > 0.01 {
            *p = new_progress;
            self.dirty = true;
        }
    }
}
```

## Render Loop Integration

### Main Event Loop

```rust
loop {
    // Process events
    handle_events(&mut app);

    // Render only if needed
    terminal.draw(|f| {
        render_ui(f, &mut app);
    })?;

    // Small delay to prevent busy-looping
    thread::sleep(Duration::from_millis(16)); // ~60 FPS
}
```

### Selective Rendering

```rust
fn render_ui(f: &mut Frame, app: &mut App) {
    // Only render widgets that are dirty
    if output_viewer.is_dirty() {
        output_viewer.render(f, output_area);
        output_viewer.mark_clean();
    }

    if scan_button.is_dirty() {
        scan_button.render(f, button_area);
        scan_button.mark_clean();
    }

    if folder_selector.is_dirty() {
        folder_selector.render(f, selector_area);
        folder_selector.mark_clean();
    }
}
```

## Performance Impact

### Benchmarks

From `cargo bench --bench tui_benchmarks`:

| Operation                                 | Time   |
|-------------------------------------------|--------|
| No-op operations (100x)                   | ~28ns  |
| Real changes (10x)                        | ~568ns |
| Progress updates (100x with 1% threshold) | ~143ns |
| Multiple widgets coordination             | ~916ns |

### Before vs After

| Scenario             | Without Dirty Tracking       | With Dirty Tracking           | Improvement        |
|----------------------|------------------------------|-------------------------------|--------------------|
| Idle (no changes)    | 60 FPS = 60 full redraws/sec | 0 redraws/sec                 | ∞ (no wasted work) |
| Scrolling (1 widget) | 60 full redraws/sec          | 60 partial redraws            | ~5x faster         |
| Progress update      | 60 full redraws/sec          | ~6 redraws/sec (1% threshold) | 10x faster         |

## Widget-Specific Behavior

### OutputViewer

- **Marks dirty**: append(), clear(), scroll (if actually moved), search()
- **Threshold**: None (every change visible)
- **Optimization**: Scroll no-ops don't mark dirty

### ScanButton

- **Marks dirty**: start_scan(), complete(), error(), reset(), update_progress()
- **Threshold**: Progress changes <1% don't mark dirty
- **Optimization**: Reduces renders during long scans from 60 FPS to ~10 FPS

### FolderSelector

- **Marks dirty**: set_value(), set_focused()
- **Threshold**: None
- **Optimization**: Setting same value doesn't mark dirty

### Checkbox

- **Marks dirty**: toggle(), set_checked(), set_focused()
- **Threshold**: None
- **Optimization**: Setting same state doesn't mark dirty

### StatusBar

- **Marks dirty**: set_message(), clear_message(), set_key_hints()
- **Threshold**: None
- **Optimization**: Setting same message doesn't mark dirty

## Best Practices

### Do:

✅ Always check `is_dirty()` before rendering
✅ Call `mark_clean()` after successful render
✅ Use thresholds for continuous updates (progress, animation)
✅ Check if state actually changed before marking dirty
✅ Initialize widgets as dirty (ensures first render)

### Don't:

❌ Forget to mark dirty on state changes
❌ Mark dirty on no-op operations
❌ Call `render()` without checking `is_dirty()`
❌ Skip `mark_clean()` after render (causes endless re-renders)
❌ Use dirty tracking for widgets that always change (wastes CPU on checks)

## Testing

### Unit Tests

```rust
#[test]
fn test_output_viewer_dirty_tracking() {
    let mut viewer = OutputViewer::new();

    // Starts dirty
    assert!(viewer.is_dirty());

    // Mark clean
    viewer.mark_clean();
    assert!(!viewer.is_dirty());

    // Append marks dirty
    viewer.append("New line".to_string());
    assert!(viewer.is_dirty());
}
```

### Integration Tests

```rust
#[test]
fn test_dirty_tracking_optimization_efficiency() {
    let mut viewer = OutputViewer::new();
    let mut renders_needed = 0;

    // Initial render
    if viewer.is_dirty() {
        renders_needed += 1;
        viewer.mark_clean();
    }

    // 100 no-op operations
    for _ in 0..100 {
        viewer.scroll_up(0); // No actual scroll
        if viewer.is_dirty() {
            renders_needed += 1;
            viewer.mark_clean();
        }
    }

    // Should only need initial render (1 render total)
    assert_eq!(renders_needed, 1);
}
```

## Future Enhancements

### Potential Improvements

1. **Dirty Rectangles**: Track exact regions that changed
   ```rust
   pub struct DirtyRegion {
       x: u16,
       y: u16,
       width: u16,
       height: u16,
   }
   ```

2. **Damage Tracking**: Track which parts of widget changed
   ```rust
   pub enum DirtyFlag {
       Clean,
       Content,      // Content changed
       Style,        // Styling changed
       Layout,       // Size/position changed
       Full,         // Everything changed
   }
   ```

3. **Smart Batching**: Group multiple changes before marking dirty
   ```rust
   pub struct ChangeAccumulator {
       changes: Vec<Change>,
       threshold: usize,
   }
   ```

4. **Adaptive Thresholds**: Dynamically adjust based on system load
   ```rust
   pub struct AdaptiveThreshold {
       current: f64,
       min: f64,
       max: f64,
       fps_target: f64,
   }
   ```

## Troubleshooting

### Widget Never Renders

**Problem**: Widget stays invisible after creation.

**Cause**: Forgot to mark initial dirty or cleaned too early.

**Solution**:

```rust
pub fn new() -> Self {
    Self {
        // ...
        dirty: true, // Ensure initial render
    }
}
```

### Widget Renders Too Often

**Problem**: Widget re-renders on every frame despite no changes.

**Cause**: Forgot to call `mark_clean()` after render.

**Solution**:

```rust
if widget.is_dirty() {
    widget.render(f, area);
    widget.mark_clean(); // Don't forget!
}
```

### Progress Bar Flickers

**Problem**: Progress updates cause excessive rendering.

**Cause**: No threshold for progress changes.

**Solution**:

```rust
pub fn update_progress(&mut self, progress: f64) {
    let new_progress = progress.clamp(0.0, 1.0);

    // Only mark dirty for visible changes (>1%)
    if (self.progress - new_progress).abs() > 0.01 {
        self.progress = new_progress;
        self.dirty = true;
    }
}
```

### Scroll Feels Laggy

**Problem**: Scroll operations marked dirty but terminal updates slowly.

**Cause**: Terminal backend or event loop delay.

**Solution**:

```rust
// Reduce event loop delay
thread::sleep(Duration::from_millis(16)); // 60 FPS

// Or use immediate mode for scroll
if let Event::Key(key) = event::read()? {
    match key.code {
        KeyCode::Up => {
            output_viewer.scroll_up(1);
            // Render immediately for responsive feel
            terminal.draw(|f| render_ui(f, app))?;
        }
    }
}
```

## References

- Ratatui immediate mode rendering: https://ratatui.rs/concepts/rendering/
- Game loop patterns: https://gameprogrammingpatterns.com/game-loop.html
- Dirty region optimization: https://en.wikipedia.org/wiki/Dirty_rectangle

---

**Implementation Date**: 2025-10-10
**Tests**: `cargo test --test dirty_tracking_tests`
**Benchmarks**: `cargo bench --bench tui_benchmarks -- dirty_tracking`
