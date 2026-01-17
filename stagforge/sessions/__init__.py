"""Session management for Slopstag editor."""

from .manager import SessionManager, session_manager
from .models import EditorSession, LayerInfo, SessionState

__all__ = [
    "SessionManager",
    "session_manager",
    "EditorSession",
    "LayerInfo",
    "SessionState",
]
