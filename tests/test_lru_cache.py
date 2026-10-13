"""Tests for LRU cache with size-based eviction."""
import pytest
from src.lru_cache import LRUCache, SizeBoundedLRUCache


class TestLRUCache:
    def test_basic_set_get(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") == 1
        assert cache.get("b") == 2

    def test_miss_returns_none(self):
        cache = LRUCache(capacity=3)
        assert cache.get("missing") is None

    def test_eviction_when_full(self):
        cache = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_order(self):
        cache = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # a is now most recently used
        cache.set("c", 3)  # should evict b, not a
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_update_existing_key(self):
        cache = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("a", 10)
        assert cache.get("a") == 10

    def test_update_does_not_evict(self):
        cache = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("a", 10)  # update, not insert
        assert cache.get("b") == 2

    def test_delete(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.delete("a")
        assert cache.get("a") is None

    def test_clear(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert len(cache) == 0

    def test_contains(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        assert "a" in cache
        assert "b" not in cache

    def test_len(self):
        cache = LRUCache(capacity=5)
        assert len(cache) == 0
        cache.set("a", 1)
        assert len(cache) == 1
        cache.set("b", 2)
        assert len(cache) == 2

    def test_keys(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        assert set(cache.keys()) == {"a", "b"}

    def test_values(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        assert set(cache.values()) == {1, 2}

    def test_items(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        assert set(cache.items()) == {("a", 1), ("b", 2)}

    def test_capacity_one(self):
        cache = LRUCache(capacity=1)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_zero_capacity(self):
        cache = LRUCache(capacity=0)
        cache.set("a", 1)
        assert cache.get("a") is None

    def test_none_value(self):
        cache = LRUCache(capacity=3)
        cache.set("a", None)
        assert cache.get("a") is None
        assert "a" in cache

    def test_overwrite_same_key_same_value(self):
        cache = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("a", 1)
        assert cache.get("a") == 1
        assert len(cache) == 1


class TestLRUCacheStats:
    def test_hits_and_misses(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["capacity"] == 3

    def test_hit_rate(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("a")  # hit
        cache.get("b")  # miss
        assert cache.hit_rate() == 2 / 3

    def test_eviction_count(self):
        cache = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # evicts a
        assert cache.stats()["evictions"] == 1


class TestSizeBoundedLRUCache:
    def test_evicts_by_total_size(self):
        cache = SizeBoundedLRUCache(max_size_bytes=100)
        cache.set("a", "x" * 50)
        cache.set("b", "y" * 50)
        cache.set("c", "z" * 50)  # should evict a
        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("c") is not None

    def test_rejects_oversized_value(self):
        cache = SizeBoundedLRUCache(max_size_bytes=10)
        cache.set("a", "x" * 100)
        assert cache.get("a") is None

    def test_size_calculation(self):
        cache = SizeBoundedLRUCache(max_size_bytes=1000)
        cache.set("key", "value")
        assert cache.current_size() > 0
