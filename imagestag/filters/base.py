# ImageStag Filters - Base Classes
"""
Base classes for the filter system.

All filters are dataclasses with JSON serialization support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, fields
from enum import Enum, auto
from typing import Any, ClassVar, TYPE_CHECKING
import json
import re

if TYPE_CHECKING:
    from imagestag import Image


class FilterBackend(Enum):
    """Preferred backend for filter execution."""
    AUTO = auto()    # Choose best available
    PIL = auto()     # Pillow
    CV = auto()      # OpenCV
    RAW = auto()     # Pure numpy


# Global registries
FILTER_REGISTRY: dict[str, type['Filter']] = {}
FILTER_ALIASES: dict[str, type['Filter']] = {}


def register_filter(cls: type['Filter']) -> type['Filter']:
    """Decorator to register a filter class."""
    FILTER_REGISTRY[cls.__name__] = cls
    # Also register lowercase version
    FILTER_REGISTRY[cls.__name__.lower()] = cls
    return cls


def register_alias(alias: str, cls: type['Filter']) -> None:
    """Register an alias for a filter class."""
    FILTER_ALIASES[alias.lower()] = cls


@dataclass
class Filter(ABC):
    """Base class for all filters."""

    # Primary parameter name for string parsing (e.g., 'factor' for Brightness)
    _primary_param: ClassVar[str | None] = None

    @abstractmethod
    def apply(self, image: Image) -> Image:
        """Apply filter to image and return result."""
        pass

    @property
    def type(self) -> str:
        """Filter type name for serialization."""
        return self.__class__.__name__

    @property
    def preferred_backend(self) -> FilterBackend:
        """Preferred backend for this filter."""
        return FilterBackend.AUTO

    def to_dict(self) -> dict[str, Any]:
        """Serialize filter to dictionary."""
        data = {}
        # Only include fields that are actual dataclass fields
        for field in fields(self):
            if not field.name.startswith('_'):
                value = getattr(self, field.name)
                # Handle enums
                if isinstance(value, Enum):
                    value = value.name
                data[field.name] = value
        data['type'] = self.type
        return data

    def to_json(self) -> str:
        """Serialize filter to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Filter':
        """Deserialize filter from dictionary."""
        data = data.copy()  # Don't modify original
        filter_type = data.pop('type', cls.__name__)

        # Find filter class
        filter_cls = FILTER_REGISTRY.get(filter_type) or FILTER_REGISTRY.get(filter_type.lower())
        if filter_cls is None:
            raise ValueError(f"Unknown filter type: {filter_type}")

        return filter_cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'Filter':
        """Deserialize filter from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def parse(cls, text: str) -> 'Filter':
        """Parse single filter from string.

        Examples:
            'blur(1.5)'
            'resize(scale=0.5)'
            'lens(k1=-0.15,k2=0.02)'
            'gray'  # no-arg filter
        """
        text = text.strip()

        # Try with parentheses first
        match = re.match(r'(\w+)\(([^)]*)\)', text)
        if match:
            name = match.group(1).lower()
            args_str = match.group(2)
        else:
            # No parentheses - filter with no arguments
            if re.match(r'^\w+$', text):
                name = text.lower()
                args_str = ''
            else:
                raise ValueError(f"Invalid filter format: {text}")

        # Find filter class (check aliases first, then registry)
        filter_cls = FILTER_ALIASES.get(name) or FILTER_REGISTRY.get(name)
        if filter_cls is None:
            raise ValueError(f"Unknown filter: {name}")

        # Parse arguments
        kwargs = {}
        if args_str:
            for i, arg in enumerate(args_str.split(',')):
                arg = arg.strip()
                if not arg:
                    continue
                if '=' in arg:
                    key, value = arg.split('=', 1)
                    kwargs[key.strip()] = _parse_value(value.strip())
                elif i == 0 and filter_cls._primary_param:
                    # Positional arg goes to primary parameter
                    kwargs[filter_cls._primary_param] = _parse_value(arg)
                else:
                    raise ValueError(f"Positional arg not supported for {name}: {arg}")

        return filter_cls(**kwargs)

    def to_string(self) -> str:
        """Convert filter to compact string format."""
        params = []
        for field in fields(self):
            if field.name.startswith('_'):
                continue
            value = getattr(self, field.name)
            # Skip default values
            if value == field.default:
                continue
            # Handle enums
            if isinstance(value, Enum):
                value = value.name.lower()
            params.append(f"{field.name}={value}")
        return f"{self.type.lower()}({','.join(params)})"


def _parse_value(s: str) -> int | float | bool | str:
    """Parse string value to appropriate type."""
    s = s.strip()
    if s.lower() == 'true':
        return True
    if s.lower() == 'false':
        return False
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s
