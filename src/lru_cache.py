"""LRU cache with optional size-based eviction for AST results."""
from __future__ import annotations
from collections import OrderedDict
from typing import Any, Iterator


class LRUCache:
    """Least Recently Used cache with O(1) operations."""

    def __init__(self, capacity: int = 128):
        if capacity < 0:
            raise ValueError("Capacity must be non-negative")
        self._capacity = capacity
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        if key not in self._cache:
            self._misses += 1
            return None
        self._hits += 1
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        if self._capacity == 0:
            return
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
            return
        if len(self._cache) >= self._capacity:
            evicted_key, _ = self._cache.popitem(last=False)
            self._evictions += 1
        self._cache[key] = value

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)

    def keys(self) -> Iterator[str]:
        return iter(self._cache.keys())

    def values(self) -> Iterator[Any]:
        return iter(self._cache.values())

    def items(self) -> Iterator[tuple[str, Any]]:
        return iter(self._cache.items())

    def stats(self) -> dict[str, int]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "size": len(self._cache),
            "capacity": self._capacity,
        }

    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total


class SizeBoundedLRUCache:
    """LRU cache that evicts based on total byte size of values."""

    def __init__(self, max_size_bytes: int = 10 * 1024 * 1024):
        if max_size_bytes <= 0:
            raise ValueError("max_size_bytes must be positive")
        self._max_size = max_size_bytes
        self._current_size = 0
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._sizes: dict[str, int] = {}

    def _value_size(self, value: Any) -> int:
        if isinstance(value, str):
            return len(value.encode("utf-8"))
        elif isinstance(value, (bytes, bytearray)):
            return len(value)
        elif isinstance(value, dict):
            return sum(len(str(k).encode("utf-8")) + len(str(v).encode("utf-8")) for k, v in value.items())
        elif isinstance(value, (list, tuple)):
            return sum(len(str(v).encode("utf-8")) for v in value)
        return len(str(value).encode("utf-8"))

    def get(self, key: str) -> Any | None:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        size = self._value_size(value)
        if size > self._max_size:
            return
        if key in self._cache:
            old_size = self._sizes[key]
            self._current_size -= old_size
            del self._cache[key]
            del self._sizes[key]
        while self._current_size + size > self._max_size and self._cache:
            evicted_key, _ = self._cache.popitem(last=False)
            self._current_size -= self._sizes.pop(evicted_key)
        self._cache[key] = value
        self._sizes[key] = size
        self._current_size += size

    def delete(self, key: str) -> None:
        if key in self._cache:
            self._current_size -= self._sizes.pop(key)
            del self._cache[key]

    def clear(self) -> None:
        self._cache.clear()
        self._sizes.clear()
        self._current_size = 0

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)

    def current_size(self) -> int:
        return self._current_size

    def max_size(self) -> int:
        return self._max_size

    def utilization(self) -> float:
        return self._current_size / self._max_size if self._max_size > 0 else 0.0
