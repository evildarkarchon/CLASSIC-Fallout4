---
name: python-docstrings
description: Generate Google-style docstrings for Python code. Use when writing new modules, classes, or functions to ensure consistent documentation.
---

This skill generates Google-style docstrings for Python code in the CLASSIC project.

## When to Use

- Writing new Python modules, classes, or functions
- Adding documentation to existing undocumented code
- Reviewing code for documentation completeness

## Docstring Templates

### Module Docstring

```python
"""Brief one-line description of the module.

Extended description explaining the module's purpose, key components,
and how it fits into the CLASSIC architecture. Mention Rust acceleration
if applicable.

Example:
    >>> from ClassicLib.Module import SomeClass
    >>> obj = SomeClass()
    >>> obj.do_something()
"""
```

### Class Docstring

```python
class MyClass:
    """Brief one-line description of the class.

    Extended description of the class's purpose and behavior.
    Mention async support and Rust acceleration if applicable.

    Attributes:
        attr_name: Description of the attribute.
        other_attr: Description with type info if not obvious.

    Example:
        >>> obj = MyClass(param="value")
        >>> result = obj.process()
        >>> print(result.status)
        'success'
    """
```

### Function/Method Docstring

```python
def my_function(
    param1: str,
    param2: int,
    *,
    optional: bool = False
) -> ResultType:
    """Brief one-line description of what the function does.

    Extended description if the function is complex. Mention
    async behavior, Rust acceleration, or important side effects.

    Args:
        param1: Description of param1.
        param2: Description of param2.
        optional: Description of optional param. Defaults to False.

    Returns:
        Description of the return value. For complex types:
        - field1: Description of field1
        - field2: Description of field2

    Raises:
        ValueError: When param1 is empty.
        FileNotFoundError: When the specified path doesn't exist.

    Example:
        >>> result = my_function("test", 42)
        >>> result.success
        True

    Note:
        Any important notes about usage, thread-safety, or caveats.
    """
```

### Async Function Docstring

```python
async def async_operation(path: Path) -> Result:
    """Brief description of the async operation.

    Args:
        path: Path to the resource.

    Returns:
        Result object with operation outcome.

    Raises:
        asyncio.TimeoutError: If operation exceeds timeout.

    Note:
        For sync contexts, use AsyncBridge:
        ``bridge.run_async(async_operation(path))``
    """
```

### Property Docstring

```python
@property
def my_property(self) -> str:
    """Brief description of what this property represents.

    Returns:
        Description of the value returned.
    """
    return self._value
```

## Required Sections by Element Type

| Element | Args | Returns | Raises | Example | Attributes |
|---------|------|---------|--------|---------|------------|
| Module | - | - | - | Optional | - |
| Class | - | - | - | Recommended | Required |
| Function | Required | Required | If applicable | Complex APIs | - |
| Property | - | Required | If applicable | - | - |
| `__init__` | Required | - | If applicable | - | - |

## Special Cases

### Deprecated Code
```python
def old_function():
    """Brief description.

    Deprecated:
        Use `new_function()` instead. Will be removed in v2.0.
    """
```

### Generator Functions
```python
def iterate_items():
    """Brief description.

    Yields:
        Item: Each item from the collection.
    """
```

### Context Managers
```python
def managed_resource():
    """Brief description.

    Yields:
        Resource: The managed resource.

    Note:
        Always use with `with` statement to ensure cleanup.
    """
```

## Anti-Patterns

- Single-line "Returns result" - Use detailed descriptions
- Missing Args section - Document all parameters
- No Raises section when exceptions possible - Document all raised exceptions
- Outdated docstrings - Update docs when changing code
- Type info only in hints - Include in docstring too for complex types

## Checklist

Before completing documentation:

- [ ] Module has top-level docstring
- [ ] All public classes documented with Attributes section
- [ ] All public functions have Args and Returns sections
- [ ] Raises section present for functions that can raise
- [ ] Examples provided for complex APIs
- [ ] Async behavior noted where applicable
- [ ] Rust acceleration mentioned if used
