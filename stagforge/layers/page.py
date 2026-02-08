"""
Page - Pydantic model for a document page.

Each page contains its own LayerStack (list of layers + active layer index).
All pages in a document share the same dimensions.
"""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Page(BaseModel):
    """
    A single page within a document.

    Serialization format matches JS Document.serialize() page entries:
    {
        "id": "uuid",
        "name": "Page 1",
        "duration": 0.0,
        "framerate": 24,
        "layers": [...],
        "activeLayerIndex": 0
    }
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=False,
        extra='ignore',
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default='Page 1')
    duration: float = Field(default=0.0)
    framerate: int = Field(default=24)
    layers: list[dict[str, Any]] = Field(default_factory=list)
    active_layer_index: int = Field(default=0, alias='activeLayerIndex')


# Backward compatibility alias
PageModel = Page
