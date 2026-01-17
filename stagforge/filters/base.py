"""Base filter class."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class BaseFilter(ABC):
    """Base class for all image filters."""

    name: str = "Base Filter"
    description: str = "Base filter description"
    category: str = "uncategorized"

    @classmethod
    def get_params_schema(cls) -> list[dict[str, Any]]:
        """Return parameter schema for this filter.

        Returns list of parameter definitions:
        [
            {
                "id": "strength",
                "name": "Strength",
                "type": "range",  # range, select, checkbox
                "min": 0,
                "max": 100,
                "default": 50
            },
            ...
        ]
        """
        return []

    @abstractmethod
    def apply(self, image: np.ndarray, **params) -> np.ndarray:
        """Apply the filter to an image.

        Args:
            image: RGBA numpy array, shape (height, width, 4), dtype uint8
            **params: Filter parameters

        Returns:
            Filtered RGBA numpy array, same shape and dtype
        """
        pass
