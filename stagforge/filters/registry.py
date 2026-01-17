"""Filter registry."""

from typing import Type

from .base import BaseFilter

# Global filter registry
filter_registry: dict[str, Type[BaseFilter]] = {}


def register_filter(filter_id: str):
    """Decorator to register a filter class."""

    def decorator(cls: Type[BaseFilter]):
        filter_registry[filter_id] = cls
        return cls

    return decorator


def load_builtin_filters():
    """Import all built-in filter modules to trigger registration."""
    from . import blur, color, edge, sharpen, morphology, threshold, artistic, noise  # noqa: F401
