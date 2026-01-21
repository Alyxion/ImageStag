"""Tests for the data cache module."""

import asyncio
import time

import pytest

from stagforge.api.data_cache import DataCache, CacheEntry


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_entry_calculates_size(self):
        """CacheEntry automatically calculates size from data."""
        data = b"test data 12345"
        entry = CacheEntry(data=data, content_type="text/plain", metadata={})
        assert entry.size == len(data)

    def test_entry_stores_metadata(self):
        """CacheEntry stores metadata correctly."""
        metadata = {"width": 100, "height": 200, "format": "webp"}
        entry = CacheEntry(data=b"x", content_type="image/webp", metadata=metadata)
        assert entry.metadata == metadata
        assert entry.content_type == "image/webp"


class TestDataCache:
    """Tests for the DataCache class."""

    def test_create_and_store(self):
        """Can create a request and store data."""
        cache = DataCache()
        request_id = "test-123"

        cache.create_request(request_id)
        success, error = cache.store_data(
            request_id,
            data=b"test image data",
            content_type="image/webp",
            metadata={"width": 100, "height": 100},
        )

        assert success is True
        assert error is None

        # Entry should be retrievable
        entry = cache.get_entry(request_id)
        assert entry is not None
        assert entry.data == b"test image data"
        assert entry.content_type == "image/webp"
        assert entry.metadata["width"] == 100

    def test_store_without_request_fails(self):
        """Storing data without creating request first fails."""
        cache = DataCache()
        success, error = cache.store_data(
            "nonexistent",
            data=b"data",
            content_type="text/plain",
        )
        assert success is False
        assert "not found" in error.lower()

    def test_remove_entry(self):
        """Can remove an entry from cache."""
        cache = DataCache()
        request_id = "test-remove"

        cache.create_request(request_id)
        cache.store_data(request_id, b"data", "text/plain")

        assert cache.get_entry(request_id) is not None

        cache.remove_entry(request_id)
        assert cache.get_entry(request_id) is None

    def test_stats(self):
        """Cache reports statistics correctly."""
        cache = DataCache(max_total_bytes=1000)

        # Initially empty
        stats = cache.stats
        assert stats["total_bytes"] == 0
        assert stats["entry_count"] == 0
        assert stats["pending_count"] == 0

        # Add some data
        cache.create_request("req1")
        cache.store_data("req1", b"x" * 100, "text/plain")

        stats = cache.stats
        assert stats["total_bytes"] == 100
        assert stats["entry_count"] == 1
        assert stats["usage_percent"] == 10.0

    def test_eviction_on_max_storage(self):
        """Old entries are evicted when max storage is reached."""
        cache = DataCache(max_total_bytes=100)

        # Fill with first entry (50 bytes)
        cache.create_request("req1")
        cache.store_data("req1", b"x" * 50, "text/plain")

        # Add second entry (60 bytes) - should evict first
        cache.create_request("req2")
        cache.store_data("req2", b"y" * 60, "text/plain")

        # First entry should be evicted
        assert cache.get_entry("req1") is None
        assert cache.get_entry("req2") is not None
        assert cache.stats["total_bytes"] == 60

    def test_data_too_large_fails(self):
        """Storing data larger than max fails."""
        cache = DataCache(max_total_bytes=100)

        cache.create_request("req1")
        success, error = cache.store_data("req1", b"x" * 200, "text/plain")

        assert success is False
        assert "exceeds" in error.lower()


class TestDataCacheAsync:
    """Async tests for DataCache."""

    @pytest.mark.asyncio
    async def test_wait_for_data_success(self):
        """wait_for_data returns when data is stored."""
        cache = DataCache()
        request_id = "async-test"

        cache.create_request(request_id)

        # Store data in a separate task
        async def store_later():
            await asyncio.sleep(0.1)
            cache.store_data(request_id, b"async data", "text/plain", {"key": "value"})

        store_task = asyncio.create_task(store_later())

        # Wait should succeed
        entry, error = await cache.wait_for_data(request_id, timeout=5.0)

        await store_task

        assert error is None
        assert entry is not None
        assert entry.data == b"async data"
        assert entry.metadata["key"] == "value"

    @pytest.mark.asyncio
    async def test_wait_for_data_timeout(self):
        """wait_for_data returns error on timeout."""
        cache = DataCache()
        request_id = "timeout-test"

        cache.create_request(request_id)

        # Don't store anything - should timeout
        entry, error = await cache.wait_for_data(request_id, timeout=0.1)

        assert entry is None
        assert "timeout" in error.lower()

    @pytest.mark.asyncio
    async def test_wait_for_nonexistent_request(self):
        """wait_for_data fails for nonexistent request."""
        cache = DataCache()

        entry, error = await cache.wait_for_data("nonexistent", timeout=0.1)

        assert entry is None
        assert "not found" in error.lower()


class TestDataCacheCleanup:
    """Tests for cache cleanup functionality."""

    def test_cleanup_expired_entries(self):
        """Expired entries are cleaned up."""
        cache = DataCache(entry_timeout_seconds=0.1)

        cache.create_request("req1")
        cache.store_data("req1", b"data", "text/plain")

        assert cache.get_entry("req1") is not None

        # Wait for expiration
        time.sleep(0.2)

        # Trigger cleanup
        cache._cleanup_expired()

        assert cache.get_entry("req1") is None

    def test_cleanup_expired_pending(self):
        """Expired pending requests are cleaned up."""
        cache = DataCache(entry_timeout_seconds=0.1)

        cache.create_request("pending1")

        # Wait for expiration
        time.sleep(0.2)

        # Trigger cleanup
        cache._cleanup_expired()

        # Pending should be gone
        assert cache.stats["pending_count"] == 0
