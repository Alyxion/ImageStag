"""
Stagforge Layer Models

Pydantic models for layer serialization, matching the JavaScript layer classes.
These models are for data transfer only, not interactive manipulation (which
happens in JS).

Layer Hierarchy:
    BaseLayer (abstract)
    ├── PixelLayer (type: 'raster')
    ├── SVGBaseLayer (abstract)
    │   ├── StaticSVGLayer (type: 'svg')
    │   └── TextLayer (type: 'text')
    └── LayerGroup (type: 'group')

Effects are imported from imagestag.layer_effects.

For SFR file I/O, use stagforge.formats.SFRDocument.
"""

from .base import BaseLayer, LayerType
from .frame import Frame, PixelFrame, SVGFrame, TextFrame
from .pixel_layer import PixelLayer
from .svg_base import SVGBaseLayer
from .svg_layer import StaticSVGLayer, SVGLayer
from .text_layer import TextLayer, TextRun
from .layer_group import LayerGroup
from .page import Page, PageModel

# Document is in formats module, re-export for backwards compatibility
from stagforge.formats import Document, SFRDocument, ViewState, SavedSelection

# Layer type registry for deserialization
_LAYER_REGISTRY: dict[str, type[BaseLayer]] = {
    'raster': PixelLayer,
    'svg': StaticSVGLayer,
    'text': TextLayer,
    'group': LayerGroup,
}


def get_layer_class(layer_type: str) -> type[BaseLayer]:
    """
    Get the appropriate layer class for a layer type.

    Args:
        layer_type: Layer type string ('raster', 'svg', 'text', 'group')

    Returns:
        Layer class
    """
    return _LAYER_REGISTRY.get(layer_type, BaseLayer)


def layer_from_dict(data: dict) -> BaseLayer:
    """
    Create a layer instance from a serialized dictionary.

    Automatically determines the layer type and uses the appropriate class.

    Args:
        data: Serialized layer data

    Returns:
        Layer instance of the appropriate type
    """
    layer_type = data.get('type', 'raster')
    layer_class = get_layer_class(layer_type)
    return layer_class.from_api_dict(data)


__all__ = [
    # Base
    'BaseLayer',
    'LayerType',
    'SVGBaseLayer',
    # Frames
    'Frame',
    'PixelFrame',
    'SVGFrame',
    'TextFrame',
    # Layer types
    'PixelLayer',
    'StaticSVGLayer',
    'SVGLayer',
    'TextLayer',
    'TextRun',
    'LayerGroup',
    # Page
    'Page',
    'PageModel',
    # Document (from stagforge.formats)
    'Document',
    'SFRDocument',
    'ViewState',
    'SavedSelection',
    # Utilities
    'get_layer_class',
    'layer_from_dict',
]
