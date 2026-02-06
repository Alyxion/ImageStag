"""
Upload Queue - Temporary storage for SFR files with automatic cleanup.

Provides a time-limited queue for uploading SFR content that can be
loaded by JavaScript clients. Prevents memory hoarding with automatic
expiration and size limits.
"""

import asyncio
import io
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueuedDocument:
    """A document waiting to be loaded."""

    id: str
    data: bytes  # SFR file bytes
    created_at: float
    expires_at: float
    name: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def size_bytes(self) -> int:
        return len(self.data)


class UploadQueue:
    """
    Temporary queue for uploaded SFR documents.

    Documents are stored in memory with automatic expiration.
    Cleanup runs periodically to remove expired entries.

    Limits:
    - Default TTL: 5 minutes (300 seconds)
    - Max queue size: 100 MB total
    - Max per document: 50 MB
    - Max documents: 50
    """

    DEFAULT_TTL = 300  # 5 minutes
    MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_DOC_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_DOCUMENTS = 50
    CLEANUP_INTERVAL = 60  # Run cleanup every 60 seconds

    def __init__(
        self,
        ttl: int = DEFAULT_TTL,
        max_total_size: int = MAX_TOTAL_SIZE,
        max_doc_size: int = MAX_DOC_SIZE,
        max_documents: int = MAX_DOCUMENTS,
    ):
        self.ttl = ttl
        self.max_total_size = max_total_size
        self.max_doc_size = max_doc_size
        self.max_documents = max_documents

        self._queue: dict[str, QueuedDocument] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @property
    def total_size(self) -> int:
        """Total size of all queued documents in bytes."""
        return sum(doc.size_bytes for doc in self._queue.values())

    @property
    def document_count(self) -> int:
        """Number of documents in queue."""
        return len(self._queue)

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired documents."""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log but don't crash the cleanup loop
                print(f"[UploadQueue] Cleanup error: {e}")

    async def cleanup_expired(self) -> int:
        """Remove expired documents. Returns count of removed documents."""
        async with self._lock:
            expired_ids = [
                doc_id for doc_id, doc in self._queue.items() if doc.is_expired
            ]
            for doc_id in expired_ids:
                del self._queue[doc_id]
            return len(expired_ids)

    async def add(
        self,
        data: bytes,
        name: Optional[str] = None,
        ttl: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Add a document to the queue.

        Args:
            data: SFR file bytes
            name: Optional document name
            ttl: Time-to-live in seconds (default: queue TTL)
            metadata: Optional metadata dict

        Returns:
            Queue ID for retrieving the document

        Raises:
            ValueError: If document exceeds size limits or queue is full
        """
        if len(data) > self.max_doc_size:
            raise ValueError(
                f"Document too large: {len(data)} bytes (max {self.max_doc_size})"
            )

        async with self._lock:
            # Clean up expired first
            expired = [
                doc_id for doc_id, doc in self._queue.items() if doc.is_expired
            ]
            for doc_id in expired:
                del self._queue[doc_id]

            # Check queue limits
            if len(self._queue) >= self.max_documents:
                # Remove oldest document to make room
                oldest_id = min(
                    self._queue.keys(), key=lambda k: self._queue[k].created_at
                )
                del self._queue[oldest_id]

            # Check total size limit
            while self.total_size + len(data) > self.max_total_size and self._queue:
                # Remove oldest to make room
                oldest_id = min(
                    self._queue.keys(), key=lambda k: self._queue[k].created_at
                )
                del self._queue[oldest_id]

            # Create new entry
            doc_id = str(uuid.uuid4())
            now = time.time()
            doc_ttl = ttl if ttl is not None else self.ttl

            self._queue[doc_id] = QueuedDocument(
                id=doc_id,
                data=data,
                created_at=now,
                expires_at=now + doc_ttl,
                name=name,
                metadata=metadata or {},
            )

            return doc_id

    async def get(self, doc_id: str, consume: bool = True) -> Optional[QueuedDocument]:
        """
        Get a document from the queue.

        Args:
            doc_id: Queue ID
            consume: If True, remove document after retrieval (default: True)

        Returns:
            QueuedDocument or None if not found/expired
        """
        async with self._lock:
            doc = self._queue.get(doc_id)
            if doc is None or doc.is_expired:
                # Clean up if expired
                if doc_id in self._queue:
                    del self._queue[doc_id]
                return None

            if consume:
                del self._queue[doc_id]

            return doc

    async def peek(self, doc_id: str) -> Optional[QueuedDocument]:
        """Get document without consuming it."""
        return await self.get(doc_id, consume=False)

    async def remove(self, doc_id: str) -> bool:
        """Remove a document from the queue. Returns True if removed."""
        async with self._lock:
            if doc_id in self._queue:
                del self._queue[doc_id]
                return True
            return False

    async def clear(self) -> int:
        """Clear all documents from the queue. Returns count of removed documents."""
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            "document_count": self.document_count,
            "total_size_bytes": self.total_size,
            "max_documents": self.max_documents,
            "max_total_size_bytes": self.max_total_size,
            "max_doc_size_bytes": self.max_doc_size,
            "ttl_seconds": self.ttl,
            "documents": [
                {
                    "id": doc.id,
                    "name": doc.name,
                    "size_bytes": doc.size_bytes,
                    "created_at": doc.created_at,
                    "expires_at": doc.expires_at,
                    "ttl_remaining": max(0, doc.expires_at - time.time()),
                    "is_expired": doc.is_expired,
                }
                for doc in self._queue.values()
            ],
        }


# Global upload queue instance
upload_queue = UploadQueue()
