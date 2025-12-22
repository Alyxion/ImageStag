# ImageStag Filters - Pipeline
"""
FilterPipeline for chaining multiple filters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
import re

from .base import Filter, register_filter

if TYPE_CHECKING:
    from imagestag import Image


@register_filter
@dataclass
class FilterPipeline(Filter):
    """Chain of filters applied in sequence."""
    filters: list[Filter] = field(default_factory=list)

    def apply(self, image: Image) -> Image:
        """Apply all filters in sequence."""
        result = image
        for f in self.filters:
            result = f.apply(result)
        return result

    def append(self, filter: Filter) -> 'FilterPipeline':
        """Add filter to pipeline (chainable)."""
        self.filters.append(filter)
        return self

    def extend(self, filters: list[Filter]) -> 'FilterPipeline':
        """Add multiple filters to pipeline (chainable)."""
        self.filters.extend(filters)
        return self

    def __len__(self) -> int:
        return len(self.filters)

    def __iter__(self):
        return iter(self.filters)

    def __getitem__(self, index: int) -> Filter:
        return self.filters[index]

    def to_dict(self) -> dict[str, Any]:
        """Serialize pipeline to dictionary."""
        return {
            'type': 'FilterPipeline',
            'filters': [f.to_dict() for f in self.filters]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FilterPipeline':
        """Deserialize pipeline from dictionary."""
        filters = [Filter.from_dict(f) for f in data.get('filters', [])]
        return cls(filters=filters)

    @classmethod
    def parse(cls, text: str) -> 'FilterPipeline':
        """Parse filter string into pipeline.

        Examples:
            'resize(0.5)|blur(1.5)|brightness(1.1)'
            'resize(scale=0.5);blur(radius=1.5)'
        """
        if not text:
            return cls()

        filters = []
        # Split by | or ;
        for part in re.split(r'[|;]', text):
            part = part.strip()
            if not part:
                continue
            filters.append(Filter.parse(part))

        return cls(filters=filters)

    def to_string(self) -> str:
        """Convert pipeline to compact string format."""
        return '|'.join(f.to_string() for f in self.filters)
