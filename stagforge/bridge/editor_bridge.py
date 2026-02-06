"""WebSocket-based communication bridge for Python-JavaScript interop.

This module provides a thread-safe, synchronous API for Python code to
communicate with JavaScript running in the browser via WebSocket.
"""

import asyncio
import json
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .exceptions import (
    BridgeProtocolError,
    BridgeSessionError,
    BridgeTimeoutError,
)
from .session import BridgeSession


class PendingCall:
    """Tracks a pending command awaiting response."""

    def __init__(self, command_id: str, timeout: float, method: str = ""):
        self.command_id = command_id
        self.method = method
        self.timeout = timeout
        self.event = threading.Event()
        self.result: Any = None
        self.error: dict | None = None
        self.created_at = datetime.now()
        self.completed_at: datetime | None = None

    @property
    def duration_ms(self) -> float | None:
        """Get the duration of the call in milliseconds."""
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds() * 1000
        return None


class EditorBridge:
    """Thread-safe WebSocket bridge with synchronous API.

    Provides bidirectional communication between Python and JavaScript:
    - Python calls JS methods via `call()` (blocking) or `fire()` (async)
    - JS sends events to Python via `emit()` (handled by session callbacks)

    Example usage:
        bridge = EditorBridge()
        bridge.start()

        # In FastAPI route:
        @app.websocket("/ws/editor/{session_id}")
        async def ws_endpoint(websocket: WebSocket, session_id: str):
            await bridge.websocket_endpoint(websocket, session_id)

        # From any Python thread:
        result = bridge.call(session_id, "executeCommand", {"command": "undo"})
    """

    def __init__(
        self,
        session_timeout: float = 30.0,
        heartbeat_interval: float = 1.0,
        response_timeout: float = 30.0,
    ):
        """Initialize the bridge.

        Args:
            session_timeout: Remove sessions after this many seconds of inactivity.
            heartbeat_interval: Expected heartbeat rate from JS (for documentation).
            response_timeout: Default timeout for call() operations.
        """
        self._session_timeout = timedelta(seconds=session_timeout)
        self._heartbeat_interval = heartbeat_interval
        self._response_timeout = response_timeout

        # Sessions by ID
        self._sessions: dict[str, BridgeSession] = {}
        self._sessions_lock = threading.Lock()

        # Pending calls awaiting responses
        self._pending_calls: dict[str, PendingCall] = {}
        self._pending_lock = threading.Lock()

        # Event loop for async operations (runs in dedicated thread)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

        # Event handlers
        self._on_session_created: list[callable] = []
        self._on_session_removed: list[callable] = []

        # Command statistics
        self._command_stats: dict[str, dict] = {}  # method -> {count, total_ms, min_ms, max_ms}
        self._stats_lock = threading.Lock()

    # ==================== Session Management ====================

    def get_session(self, session_id: str) -> BridgeSession | None:
        """Get a session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            BridgeSession if found, None otherwise.
        """
        with self._sessions_lock:
            return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: str) -> BridgeSession:
        """Get existing session or create a new one.

        Args:
            session_id: The session identifier.

        Returns:
            The existing or newly created session.
        """
        with self._sessions_lock:
            if session_id in self._sessions:
                return self._sessions[session_id]

            session = BridgeSession(id=session_id)
            self._sessions[session_id] = session
            print(f"[EditorBridge] Created session: {session_id}")

            # Notify handlers
            for handler in self._on_session_created:
                try:
                    handler(session)
                except Exception as e:
                    print(f"[EditorBridge] Session created handler error: {e}")

            return session

    def remove_session(self, session_id: str) -> bool:
        """Remove a session.

        Args:
            session_id: The session identifier.

        Returns:
            True if session was removed, False if not found.
        """
        with self._sessions_lock:
            session = self._sessions.pop(session_id, None)
            if session:
                print(f"[EditorBridge] Removed session: {session_id}")
                # Notify handlers
                for handler in self._on_session_removed:
                    try:
                        handler(session)
                    except Exception as e:
                        print(f"[EditorBridge] Session removed handler error: {e}")
                return True
            return False

    def get_all_sessions(self) -> list[BridgeSession]:
        """Get all active sessions.

        Returns:
            List of all sessions, sorted by last heartbeat (most recent first).
        """
        with self._sessions_lock:
            sessions = list(self._sessions.values())
            sessions.sort(key=lambda s: s.last_heartbeat, reverse=True)
            return sessions

    # ==================== Commands ====================

    def call(
        self,
        session_id: str,
        method: str,
        params: dict | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Call a JavaScript method and wait for response.

        This is a thread-safe, blocking call. It can be called from any thread.

        Args:
            session_id: The target session ID.
            method: The JS method name to call.
            params: Optional parameters to pass.
            timeout: Timeout in seconds (uses default if None).

        Returns:
            The result from JavaScript.

        Raises:
            BridgeSessionError: If session not found or not connected.
            BridgeTimeoutError: If response not received within timeout.
            BridgeProtocolError: If JS returns an error.
        """
        session = self.get_session(session_id)
        if not session:
            raise BridgeSessionError(f"Session not found: {session_id}")
        if not session.is_connected:
            raise BridgeSessionError(f"Session not connected: {session_id}")

        timeout = timeout if timeout is not None else self._response_timeout
        command_id = str(uuid.uuid4())

        # Create pending call tracker
        pending = PendingCall(command_id, timeout, method)
        with self._pending_lock:
            self._pending_calls[command_id] = pending

        try:
            # Build command message
            message = {
                "type": "command",
                "id": command_id,
                "method": method,
                "params": params or {},
            }

            # Send via event loop
            self._send_message(session_id, message)

            # Wait for response
            if not pending.event.wait(timeout):
                raise BridgeTimeoutError(
                    f"Timeout waiting for response to {method} (session={session_id})"
                )

            # Record completion time
            pending.completed_at = datetime.now()

            # Update stats
            self._record_command_stats(method, pending.duration_ms)

            # Check for error
            if pending.error:
                raise BridgeProtocolError(
                    f"JS error: {pending.error.get('message', 'Unknown error')}"
                )

            return pending.result

        finally:
            # Clean up pending call
            with self._pending_lock:
                self._pending_calls.pop(command_id, None)

    async def call_async(
        self,
        session_id: str,
        method: str,
        params: dict | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Call a JavaScript method and wait for response (async version).

        This is an async-friendly version that doesn't block the event loop.
        Use this when calling from async code (e.g., FastAPI endpoints).

        Args:
            session_id: The target session ID.
            method: The JS method name to call.
            params: Optional parameters to pass.
            timeout: Timeout in seconds (uses default if None).

        Returns:
            The result from JavaScript.

        Raises:
            BridgeSessionError: If session not found or not connected.
            BridgeTimeoutError: If response not received within timeout.
            BridgeProtocolError: If JS returns an error.
        """
        session = self.get_session(session_id)
        if not session:
            raise BridgeSessionError(f"Session not found: {session_id}")
        if not session.is_connected:
            raise BridgeSessionError(f"Session not connected: {session_id}")
        if not session.websocket:
            raise BridgeSessionError(f"Session has no websocket: {session_id}")

        timeout = timeout if timeout is not None else self._response_timeout
        command_id = str(uuid.uuid4())

        # Create pending call tracker with asyncio.Event instead of threading.Event
        pending = PendingCall(command_id, timeout, method)
        async_event = asyncio.Event()

        with self._pending_lock:
            self._pending_calls[command_id] = pending

        try:
            # Build command message
            message = {
                "type": "command",
                "id": command_id,
                "method": method,
                "params": params or {},
            }

            # Send message directly using the current event loop
            # (the websocket is attached to this loop)
            await self._send_message_async(session, message)

            # Wait for response using asyncio-friendly polling
            # (the threading.Event will be set by the websocket handler)
            start_time = datetime.now()
            while True:
                # Check if threading.Event is set
                if pending.event.is_set():
                    break

                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    raise BridgeTimeoutError(
                        f"Timeout waiting for response to {method} (session={session_id})"
                    )

                # Yield to event loop (allow other tasks to run)
                await asyncio.sleep(0.01)

            # Record completion time
            pending.completed_at = datetime.now()

            # Update stats
            self._record_command_stats(method, pending.duration_ms)

            # Check for error
            if pending.error:
                raise BridgeProtocolError(
                    f"JS error: {pending.error.get('message', 'Unknown error')}"
                )

            return pending.result

        finally:
            # Clean up pending call
            with self._pending_lock:
                self._pending_calls.pop(command_id, None)

    def _record_command_stats(self, method: str, duration_ms: float | None) -> None:
        """Record command execution statistics."""
        if duration_ms is None:
            return

        with self._stats_lock:
            if method not in self._command_stats:
                self._command_stats[method] = {
                    "count": 0,
                    "total_ms": 0.0,
                    "min_ms": float("inf"),
                    "max_ms": 0.0,
                }

            stats = self._command_stats[method]
            stats["count"] += 1
            stats["total_ms"] += duration_ms
            stats["min_ms"] = min(stats["min_ms"], duration_ms)
            stats["max_ms"] = max(stats["max_ms"], duration_ms)

    def get_command_stats(self) -> dict[str, dict]:
        """Get command execution statistics.

        Returns:
            Dict of method -> {count, total_ms, avg_ms, min_ms, max_ms}
        """
        with self._stats_lock:
            result = {}
            for method, stats in self._command_stats.items():
                count = stats["count"]
                result[method] = {
                    "count": count,
                    "total_ms": round(stats["total_ms"], 2),
                    "avg_ms": round(stats["total_ms"] / count, 2) if count > 0 else 0,
                    "min_ms": round(stats["min_ms"], 2) if stats["min_ms"] != float("inf") else 0,
                    "max_ms": round(stats["max_ms"], 2),
                }
            return result

    def reset_command_stats(self) -> None:
        """Reset command execution statistics."""
        with self._stats_lock:
            self._command_stats.clear()

    def fire(
        self,
        session_id: str,
        method: str,
        params: dict | None = None,
    ) -> None:
        """Send a command without waiting for response (fire-and-forget).

        Args:
            session_id: The target session ID.
            method: The JS method name to call.
            params: Optional parameters to pass.

        Raises:
            BridgeSessionError: If session not found or not connected.
        """
        session = self.get_session(session_id)
        if not session:
            raise BridgeSessionError(f"Session not found: {session_id}")
        if not session.is_connected:
            raise BridgeSessionError(f"Session not connected: {session_id}")

        message = {
            "type": "command",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
        }

        self._send_message(session_id, message)

    def broadcast(
        self,
        method: str,
        params: dict | None = None,
    ) -> None:
        """Send a command to all connected sessions.

        Args:
            method: The JS method name to call.
            params: Optional parameters to pass.
        """
        sessions = self.get_all_sessions()
        for session in sessions:
            if session.is_connected:
                try:
                    self.fire(session.id, method, params)
                except BridgeSessionError:
                    pass  # Session disconnected between check and send

    # ==================== WebSocket Handler ====================

    async def websocket_endpoint(
        self,
        websocket: WebSocket,
        session_id: str,
    ) -> None:
        """Handle WebSocket connection for a session.

        This should be called from a FastAPI WebSocket route.

        Args:
            websocket: The FastAPI WebSocket connection.
            session_id: The session identifier.
        """
        await websocket.accept()

        # Get or create session
        session = self.get_or_create_session(session_id)
        old_websocket = session.websocket
        session.websocket = websocket
        session.update_heartbeat()

        print(f"[EditorBridge] WebSocket connected: {session_id}")

        # Send time sync message so client can calculate offset
        await self._send_message_async(
            session,
            {
                "type": "sync",
                "serverTime": int(datetime.now().timestamp() * 1000),  # ms since epoch
            },
        )

        try:
            while True:
                # Receive message
                try:
                    data = await websocket.receive_text()
                except WebSocketDisconnect:
                    break

                # Parse and handle
                try:
                    message = json.loads(data)
                    await self._handle_message(session, message)
                except json.JSONDecodeError as e:
                    print(f"[EditorBridge] Invalid JSON from {session_id}: {e}")
                except Exception as e:
                    print(f"[EditorBridge] Error handling message from {session_id}: {e}")

        finally:
            # Clean up connection
            if session.websocket is websocket:
                session.websocket = None

            print(f"[EditorBridge] WebSocket disconnected: {session_id}")

            # Notify disconnect callback
            if session.on_disconnect:
                try:
                    session.on_disconnect()
                except Exception as e:
                    print(f"[EditorBridge] Disconnect handler error: {e}")

    async def _handle_message(
        self,
        session: BridgeSession,
        message: dict,
    ) -> None:
        """Handle an incoming WebSocket message.

        Args:
            session: The session that sent the message.
            message: The parsed JSON message.
        """
        msg_type = message.get("type")

        if msg_type == "heartbeat":
            # Update heartbeat and send ack
            session.update_heartbeat()
            await self._send_message_async(
                session,
                {"type": "heartbeat_ack"},
            )

        elif msg_type == "response":
            # Route to pending call
            correlation_id = message.get("correlationId")
            if correlation_id:
                with self._pending_lock:
                    pending = self._pending_calls.get(correlation_id)
                    if pending:
                        pending.result = message.get("result")
                        pending.error = message.get("error")
                        pending.event.set()

        elif msg_type == "event":
            # Route to session event handler
            event_name = message.get("event")
            event_data = message.get("data", {})
            if session.on_event:
                try:
                    session.on_event(event_name, event_data)
                except Exception as e:
                    print(f"[EditorBridge] Event handler error: {e}")

        elif msg_type == "error":
            # Error from JS (might be for a pending call)
            correlation_id = message.get("correlationId")
            if correlation_id:
                with self._pending_lock:
                    pending = self._pending_calls.get(correlation_id)
                    if pending:
                        pending.error = message.get("error", {"message": "Unknown error"})
                        pending.event.set()
            else:
                print(f"[EditorBridge] JS error: {message.get('error')}")

    # ==================== Internal Messaging ====================

    def _send_message(self, session_id: str, message: dict) -> None:
        """Send a message to a session (thread-safe).

        Args:
            session_id: The target session ID.
            message: The message to send.
        """
        session = self.get_session(session_id)
        if not session or not session.websocket:
            return

        # Run in event loop
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._send_message_async(session, message),
                self._loop,
            )
        else:
            # Fallback: try to get current loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(
                        self._send_message_async(session, message),
                        loop=loop,
                    )
                else:
                    loop.run_until_complete(
                        self._send_message_async(session, message)
                    )
            except RuntimeError:
                # No event loop - can't send
                print(f"[EditorBridge] No event loop to send message")

    async def _send_message_async(
        self,
        session: BridgeSession,
        message: dict,
    ) -> None:
        """Send a message to a session asynchronously.

        Args:
            session: The target session.
            message: The message to send.
        """
        if not session.websocket:
            return

        try:
            await session.websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"[EditorBridge] Failed to send message to {session.id}: {e}")

    # ==================== Lifecycle ====================

    def start(self) -> None:
        """Start the bridge (cleanup task, event loop thread)."""
        if self._running:
            return

        self._running = True

        # Start dedicated event loop thread for background tasks
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._cleanup_task = self._loop.create_task(self._cleanup_loop())
            self._loop.run_forever()

        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()

        print("[EditorBridge] Started")

    def stop(self) -> None:
        """Stop the bridge and close all connections."""
        if not self._running:
            return

        self._running = False

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Stop event loop
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        # Wait for thread
        if self._loop_thread:
            self._loop_thread.join(timeout=2.0)

        # Close all sessions
        with self._sessions_lock:
            for session in self._sessions.values():
                if session.websocket:
                    # Can't close from here - let them timeout
                    session.websocket = None
            self._sessions.clear()

        print("[EditorBridge] Stopped")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up inactive sessions."""
        while self._running:
            try:
                await asyncio.sleep(5.0)  # Check every 5 seconds
                self._cleanup_inactive()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[EditorBridge] Cleanup error: {e}")

    def _cleanup_inactive(self) -> int:
        """Remove sessions that have been inactive too long.

        Returns:
            Number of sessions removed.
        """
        now = datetime.now()
        removed = 0

        with self._sessions_lock:
            inactive = []
            for sid, session in self._sessions.items():
                if now - session.last_heartbeat > self._session_timeout:
                    inactive.append(sid)

            for sid in inactive:
                session = self._sessions.pop(sid, None)
                if session:
                    removed += 1
                    print(f"[EditorBridge] Removed inactive session: {sid}")
                    # Notify handlers
                    for handler in self._on_session_removed:
                        try:
                            handler(session)
                        except Exception:
                            pass

        return removed

    # ==================== Event Handlers ====================

    def on_session_created(self, handler: callable) -> None:
        """Register a handler for session creation events.

        Args:
            handler: Callable that receives (session: BridgeSession).
        """
        self._on_session_created.append(handler)

    def on_session_removed(self, handler: callable) -> None:
        """Register a handler for session removal events.

        Args:
            handler: Callable that receives (session: BridgeSession).
        """
        self._on_session_removed.append(handler)


# Global singleton instance
editor_bridge = EditorBridge()
