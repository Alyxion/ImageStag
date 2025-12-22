# ImageStag Filters Module
"""
Dataclass-based filter system for image processing.

All filters are JSON-serializable and can be composed into pipelines.
Supports branching via FilterGraph for complex filter operations.
"""

from .base import (
    Filter,
    FilterBackend,
    FILTER_REGISTRY,
    FILTER_ALIASES,
    register_filter,
    register_alias,
)

from .pipeline import FilterPipeline

from .graph import (
    FilterGraph,
    CombinerFilter,
    BlendMode,
    Blend,
    Composite,
    MaskApply,
)

from .color import (
    Brightness,
    Contrast,
    Saturation,
    Sharpness,
    Grayscale,
    Invert,
    Threshold,
)

from .blur import (
    GaussianBlur,
    BoxBlur,
    UnsharpMask,
    Sharpen,
)

from .geometric import (
    Resize,
    Crop,
    CenterCrop,
    Rotate,
    Flip,
)

# Register aliases
register_alias('blur', GaussianBlur)
register_alias('gaussian', GaussianBlur)
register_alias('gray', Grayscale)
register_alias('grey', Grayscale)

__all__ = [
    # Base
    'Filter',
    'FilterBackend',
    'FilterPipeline',
    'FilterGraph',
    'FILTER_REGISTRY',
    'FILTER_ALIASES',
    'register_filter',
    'register_alias',
    # Graph/Combiners
    'CombinerFilter',
    'BlendMode',
    'Blend',
    'Composite',
    'MaskApply',
    # Color
    'Brightness',
    'Contrast',
    'Saturation',
    'Sharpness',
    'Grayscale',
    'Invert',
    'Threshold',
    # Blur
    'GaussianBlur',
    'BoxBlur',
    'UnsharpMask',
    'Sharpen',
    # Geometric
    'Resize',
    'Crop',
    'CenterCrop',
    'Rotate',
    'Flip',
]
