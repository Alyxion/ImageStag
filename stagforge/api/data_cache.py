"""Temporary data cache for push-based transfers.

Instead of returning large data through WebSocket (which has payload limits),
the frontend POSTs data to this cache, and API endpoints wait for it.

Supports any data type: images (webp, avif, png), vectors (svg, json), etc.

Flow:
1. API endpoint creates a request with create_request()
2. API tells JS to push data via run_method
3. JS renders/prepares data and POSTs to /api/upload/{request_id}
4. API endpoint awaits wait_for_data() which returns when data arrives
5. Cache auto-cleans expired entries
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """A cached data entry."""

    data: bytes
    content_type: str
    metadata: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    size: int = 0

    def __post_init__(self):
        self.size = len(self.data)


@dataclass
class PendingRequest:
    """A pending request waiting for data."""

    event: asyncio.Event
    created_at: float = field(default_factory=time.time)
    entry: CacheEntry | None = None
    error: str | None = None


class DataCache:
    """Thread-safe cache for temporary data with automatic cleanup."""

    def __init__(
        self,
        max_total_bytes: int = 500 * 1024 * 1024,  # 500 MB default
        entry_timeout_seconds: float = 300.0,  # 5 minutes
        cleanup_interval_seconds: float = 60.0,  # Clean every minute
    ):
        self._entries: dict[str, CacheEntry] = {}
        self._pending: dict[str, PendingRequest] = {}
        self._lock = threading.Lock()
        self._total_bytes = 0
        self._max_total_bytes = max_total_bytes
        self._entry_timeout = entry_timeout_seconds
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        """Start the background cleanup task."""
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_loop())
            except RuntimeError:
                # No running loop yet, will start later
                pass

    def stop(self) -> None:
        """Stop the background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Don't crash on cleanup errors

    def _cleanup_expired(self) -> None:
        """Remove expired entries and pending requests."""
        now = time.time()
        with self._lock:
            # Clean expired entries
            expired_keys = [
                key
                for key, entry in self._entries.items()
                if now - entry.created_at > self._entry_timeout
            ]
            for key in expired_keys:
                entry = self._entries.pop(key)
                self._total_bytes -= entry.size

            # Clean expired pending requests (signal error)
            expired_pending = [
                key
                for key, req in self._pending.items()
                if now - req.created_at > self._entry_timeout
            ]
            for key in expired_pending:
                req = self._pending.pop(key)
                req.error = "Request timed out"
                req.event.set()

    def _evict_if_needed(self, new_size: int) -> None:
        """Evict oldest entries if adding new_size would exceed max."""
        # Must be called with lock held
        while self._total_bytes + new_size > self._max_total_bytes and self._entries:
            # Find oldest entry
            oldest_key = min(self._entries, key=lambda k: self._entries[k].created_at)
            entry = self._entries.pop(oldest_key)
            self._total_bytes -= entry.size

    def create_request(self, request_id: str) -> None:
        """Create a pending request that will wait for data.

        Args:
            request_id: Unique ID for this request.
        """
        with self._lock:
            if request_id not in self._pending:
                self._pending[request_id] = PendingRequest(
                    event=asyncio.Event(),
                )

    async def wait_for_data(
        self,
        request_id: str,
        timeout: float = 30.0,
    ) -> tuple[CacheEntry | None, str | None]:
        """Wait for data to arrive for a request.

        Args:
            request_id: The request ID to wait for.
            timeout: Maximum time to wait in seconds.

        Returns:
            (CacheEntry, None) on success, or (None, error_message) on failure.
        """
        with self._lock:
            pending = self._pending.get(request_id)
            if not pending:
                return None, "Request not found"

        try:
            await asyncio.wait_for(pending.event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            with self._lock:
                self._pending.pop(request_id, None)
            return None, f"Timeout waiting for data after {timeout}s"

        with self._lock:
            self._pending.pop(request_id, None)

        if pending.error:
            return None, pending.error

        return pending.entry, None

    def store_data(
        self,
        request_id: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        """Store data for a pending request.

        Args:
            request_id: The request ID.
            data: The binary data to store.
            content_type: MIME type of the data.
            metadata: Optional metadata dict.

        Returns:
            (True, None) on success, or (False, error_message) on failure.
        """
        with self._lock:
            pending = self._pending.get(request_id)
            if not pending:
                return False, "Request not found or expired"

            # Check size
            data_size = len(data)
            if data_size > self._max_total_bytes:
                pending.error = f"Data size {data_size} exceeds max {self._max_total_bytes}"
                pending.event.set()
                return False, pending.error

            # Evict old entries if needed
            self._evict_if_needed(data_size)

            # Create entry
            entry = CacheEntry(
                data=data,
                content_type=content_type,
                metadata=metadata or {},
            )

            # Store and signal
            self._entries[request_id] = entry
            self._total_bytes += entry.size
            pending.entry = entry
            pending.event.set()

            return True, None

    def get_entry(self, request_id: str) -> CacheEntry | None:
        """Get a cached entry by ID (doesn't wait)."""
        with self._lock:
            return self._entries.get(request_id)

    def remove_entry(self, request_id: str) -> None:
        """Remove an entry from the cache."""
        with self._lock:
            entry = self._entries.pop(request_id, None)
            if entry:
                self._total_bytes -= entry.size

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "total_bytes": self._total_bytes,
                "max_bytes": self._max_total_bytes,
                "entry_count": len(self._entries),
                "pending_count": len(self._pending),
                "usage_percent": (
                    self._total_bytes / self._max_total_bytes * 100
                    if self._max_total_bytes > 0
                    else 0
                ),
            }


# Global instance
data_cache = DataCache()
