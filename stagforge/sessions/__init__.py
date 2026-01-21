"""Session management for Stagforge editor."""

from .manager import SessionManager, session_manager
from .models import DocumentInfo, EditorSession, LayerInfo, SessionState

__all__ = [
    "SessionManager",
    "session_manager",
    "DocumentInfo",
    "EditorSession",
    "LayerInfo",
    "SessionState",
]
