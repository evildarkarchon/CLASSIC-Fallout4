# Report Generation Backend Improvement Strategy

## Current Problem

The report generation currently uses an **anti-pattern** where a single mutable `list[str]` is passed to 30+ methods across 10+ modules:

```python
# Current anti-pattern
autoscan_report = []  # Shared mutable state
detect_mods_single(data, plugins, autoscan_report)  # Mutates list
scan_suspects(callstack, autoscan_report)  # Mutates list
formid_analyzer.match(formids, plugins, autoscan_report)  # Mutates list
# ... 30+ more mutations
```

### Specific Issues

1. **Retroactive Header Insertion Pattern** - The code repeatedly does:
   ```python
   initial_len = len(autoscan_report)
   detect_mods_single(data, plugins, autoscan_report)
   if len(autoscan_report) > initial_len:
       # Retroactively insert header at saved position
       for i, line in enumerate(header_lines):
           autoscan_report.insert(initial_len + i, line)
   ```

2. **Testing Difficulty** - Can't test components in isolation without setting up mutable state
3. **Thread Safety** - Shared mutable list is not thread-safe for async operations
4. **Hidden Data Flow** - Can't trace what modifies the report without reading all code
5. **Tight Coupling** - Every component knows about and depends on the report structure

## Proposed Solution: Functional Composition

Replace mutable list passing with **immutable fragments** that get composed:

```python
# New functional pattern
header_fragment = generate_header(crashlog_file.name, version)
error_fragment = generate_error_section(main_error, crashgen_info)
mods_fragment = detect_mods_fragment(yaml_dict, plugins)

# Compose fragments
final_report = ReportComposer.compose(
    header_fragment,
    error_fragment,
    mods_fragment.with_header("### Mods Section") if mods_fragment.has_content else empty()
)
```

## Key Components

### 1. ReportFragment (Immutable)
```python
@dataclass(frozen=True)
class ReportFragment:
    content: tuple[str, ...]  # Immutable tuple
    has_content: bool  # Explicitly track if content exists

    def with_header(self, header: list[str]) -> ReportFragment:
        """Add header only if fragment has content"""
```

### 2. Conditional Sections (Replace Retroactive Headers)
```python
# Old pattern (complex mutation)
initial_len = len(report)
detect_mods(data, plugins, report)
if len(report) > initial_len:
    insert_header_at(initial_len, header)

# New pattern (functional)
fragment = ReportComposer.conditional_section(
    generator_func=lambda: detect_mods_fragment(data, plugins),
    header_func=lambda: ["### Section Header\n"]
)
```

### 3. Backwards Compatibility
```python
class FragmentCollector:
    """Looks like a list but uses fragments internally"""

    def append(self, line: str): ...
    def extend(self, lines: list): ...
    def to_list(self) -> list[str]: ...
```

## Migration Strategy

### Phase 1: Infrastructure ✅
- Create ReportFragment and ReportComposer
- Add FragmentCollector for compatibility
- No changes to existing code yet

### Phase 2: Leaf Functions
Convert scanners/analyzers to return fragments:
```python
# Add new fragment version
def detect_mods_fragment(data, plugins) -> ReportFragment:
    lines = []
    # ... logic ...
    return ReportFragment.from_lines(lines)

# Keep old version using new internals
def detect_mods_single(data, plugins, report):
    fragment = detect_mods_fragment(data, plugins)
    report.extend(fragment.to_list())
```

### Phase 3: Orchestrator
Update orchestrator to compose fragments instead of passing mutable list:
```python
async def process_crash_log(self, file: Path):
    fragments = []

    # Parallel fragment generation (thread-safe!)
    fragments = await asyncio.gather(
        self.generate_header_async(file),
        self.scan_suspects_async(data),
        self.analyze_formids_async(formids),
    )

    # Compose final report
    report = ReportComposer.compose(*fragments)
    return report.to_list()
```

### Phase 4: Cleanup
- Remove old mutable methods
- Update all tests to use fragments
- Remove compatibility layers

## Benefits

1. **Testability** - Test each component in isolation:
   ```python
   def test_mods_detection():
       fragment = detect_mods_fragment(test_data, test_plugins)
       assert fragment.has_content
       assert "expected warning" in fragment.content[0]
   ```

2. **Thread Safety** - Immutable fragments are inherently thread-safe

3. **Clear Data Flow** - Each function returns its contribution:
   ```python
   header = generate_header(...)  # Returns: ReportFragment
   error = generate_error(...)    # Returns: ReportFragment
   final = compose(header, error)  # Returns: ReportFragment
   ```

4. **Parallel Processing** - Can generate fragments concurrently:
   ```python
   fragments = await asyncio.gather(
       analyze_suspects_async(),
       scan_formids_async(),
       check_settings_async()
   )
   ```

5. **Maintainability** - Each component has clear inputs/outputs

## Output Compatibility

**The markdown output remains 100% identical**. Only the internal generation mechanism changes.

## Implementation Priority

1. Start with the most complex sections (mod detection with conditional headers)
2. Convert simple generators (header, footer)
3. Update async components (FormID analyzer)
4. Refactor orchestrator last

## Example Comparison

### Before (Mutable)
```python
def process(self, file, data):
    report = []

    # Every function mutates report
    generate_header(file, report)

    initial_len = len(report)
    detect_mods(data, plugins, report)
    if len(report) > initial_len:
        # Complex retroactive insertion
        for i, line in enumerate(header):
            report.insert(initial_len + i, line)

    scan_suspects(data, report)

    return report
```

### After (Functional)
```python
def process(self, file, data):
    # Each function returns a fragment
    header = generate_header_fragment(file)

    mods = conditional_section(
        lambda: detect_mods_fragment(data, plugins),
        lambda: ["### Mods Header\n"]
    )

    suspects = scan_suspects_fragment(data)

    # Compose final report
    return compose(header, mods, suspects).to_list()
```

## Summary

This approach eliminates the "passing a mutable list everywhere" anti-pattern while:
- Maintaining **exact output compatibility**
- Improving **testability and maintainability**
- Enabling **parallel fragment generation**
- Providing **clear data flow**
- Supporting **gradual migration**

The key insight is replacing **mutation with composition** - instead of everyone modifying a shared list, each component returns its contribution, and the orchestrator composes them.
