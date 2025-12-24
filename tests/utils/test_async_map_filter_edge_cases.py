"""Edge case and error handling tests for functional async utilities.

Tests edge cases, error conditions, and boundary scenarios for async_map
and async_filter functions.
"""

import pytest

from ClassicLib.Utils.Async import (
    async_filter,
    async_map,
)


class TestAsyncMapEdgeCases:
    """Edge case tests for async_map."""

    @pytest.mark.asyncio
    async def test_with_empty_items(self):
        """Should handle empty items list."""

        async def func(x):
            return x * 2

        results = await async_map(func, [])
        assert results == []

    @pytest.mark.asyncio
    async def test_with_none_function(self):
        """Should handle None as function."""
        with pytest.raises((TypeError, AttributeError)):
            await async_map(None, [1, 2, 3])  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_with_generator_items(self):
        """Should handle generator as items."""

        async def double(x):
            return x * 2

        gen = (i for i in range(5))
        results = await async_map(double, gen)
        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_function_raises_exception(self):
        """Should propagate exceptions from mapped function."""

        async def failing_func(x):
            if x == 2:
                raise ValueError(f"Cannot process {x}")
            return x

        with pytest.raises(ValueError, match="Cannot process 2"):
            await async_map(failing_func, [1, 2, 3])

    @pytest.mark.asyncio
    async def test_with_mixed_types(self):
        """Should handle items of mixed types."""

        async def stringify(x):
            return str(x)

        items = [1, "two", 3.0, None, True, [4, 5]]
        results = await async_map(stringify, items)
        assert results == ["1", "two", "3.0", "None", "True", "[4, 5]"]


class TestAsyncFilterEdgeCases:
    """Edge case tests for async_filter."""

    @pytest.mark.asyncio
    async def test_with_empty_items(self):
        """Should handle empty items list."""

        async def predicate(x):
            return True

        results = await async_filter(predicate, [])  # type: ignore[arg-type]
        assert results == []

    @pytest.mark.asyncio
    async def test_with_none_predicate(self):
        """Should handle None as predicate."""
        with pytest.raises((TypeError, AttributeError)):
            await async_filter(None, [1, 2, 3])  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_predicate_returns_non_boolean(self):
        """Should handle non-boolean return values from predicate."""

        async def truthy_predicate(x):
            # Return truthy/falsy values instead of bool
            return x if x % 2 == 0 else 0

        results = await async_filter(truthy_predicate, [1, 2, 3, 4, 5])  # type: ignore[arg-type]
        # 2 and 4 return truthy values
        assert results == [2, 4]

    @pytest.mark.asyncio
    async def test_predicate_raises_exception(self):
        """Should propagate exceptions from predicate."""

        async def failing_predicate(x):
            if x == 3:
                raise ValueError(f"Cannot check {x}")
            return x % 2 == 0

        with pytest.raises(ValueError, match="Cannot check 3"):
            await async_filter(failing_predicate, [1, 2, 3, 4])  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_with_set_input(self):
        """Should handle set as input."""

        async def is_even(x):
            return x % 2 == 0

        items_set = {1, 2, 3, 4, 5}
        results = await async_filter(is_even, items_set)  # type: ignore[arg-type]
        assert set(results) == {2, 4}
