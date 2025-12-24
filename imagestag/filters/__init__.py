# ImageStag Filters Module
"""
Dataclass-based filter system for image processing.

All filters are JSON-serializable and can be composed into pipelines.
Supports branching via FilterGraph for complex filter operations.
"""

from .base import (
    Filter,
    FilterBackend,
    FilterContext,
    FilterOutput,
    AnalyzerFilter,
    FILTER_REGISTRY,
    FILTER_ALIASES,
    register_filter,
    register_alias,
)

from .formats import (
    BitDepth,
    Compression,
    FormatSpec,
    ImageData,
)

from .converters import (
    Encode,
    Decode,
    ConvertFormat,
)

from .analyzers import (
    ImageStats,
    HistogramAnalyzer,
    ColorAnalyzer,
    RegionAnalyzer,
    BoundingBoxDetector,
)

from .pipeline import FilterPipeline

from .graph import (
    FilterGraph,
    GraphSource,
    GraphNode,
    GraphConnection,
    CombinerFilter,
    BlendMode,
    Blend,
    Composite,
    MaskApply,
)

from .source import (
    PipelineSource,
    InputType,
    SourceType,  # Legacy alias for InputType
    ExecutionMode,
    SourceHandler,
)

from .output import (
    PipelineOutput,
    OutputType,
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
    LensDistortion,
    Perspective,
)

from .transforms import (
    CoordinateTransform,
    IdentityTransform,
    LensTransform,
    PerspectiveTransform,
)

from .edge import (
    Canny,
    Sobel,
    Laplacian,
    EdgeEnhance,
)

from .morphology import (
    MorphShape,
    Erode,
    Dilate,
    MorphOpen,
    MorphClose,
    MorphGradient,
    TopHat,
    BlackHat,
)

from .detection import (
    FaceDetector,
    EyeDetector,
    ContourDetector,
)

from .geometry import (
    GeometryFilter,
    HoughCircleDetector,
    HoughLineDetector,
    DrawGeometry,
    ExtractRegions,
    MergeRegions,
)

from .channels import (
    SplitChannels,
    MergeChannels,
    ExtractChannel,
)

from .size_matcher import (
    SizeMatcher,
    SizeMatchMode,
    AspectMode,
    CropPosition,
)

from .generator import (
    ImageGenerator,
    GradientType,
)

# Register aliases
register_alias('blur', GaussianBlur)
register_alias('gaussian', GaussianBlur)
register_alias('gray', Grayscale)
register_alias('grey', Grayscale)
register_alias('lens', LensDistortion)

__all__ = [
    # Base
    'Filter',
    'FilterBackend',
    'FilterContext',
    'FilterOutput',
    'AnalyzerFilter',
    'FilterPipeline',
    'FilterGraph',
    'FILTER_REGISTRY',
    'FILTER_ALIASES',
    'register_filter',
    'register_alias',
    # Formats
    'BitDepth',
    'Compression',
    'FormatSpec',
    'ImageData',
    # Format conversion filters
    'Encode',
    'Decode',
    'ConvertFormat',
    # Analyzers
    'ImageStats',
    'HistogramAnalyzer',
    'ColorAnalyzer',
    'RegionAnalyzer',
    'BoundingBoxDetector',
    # Graph/Combiners
    'GraphSource',
    'GraphNode',
    'GraphConnection',
    'CombinerFilter',
    'BlendMode',
    'Blend',
    'Composite',
    'MaskApply',
    # Pipeline Source/Output
    'PipelineSource',
    'InputType',
    'SourceType',  # Legacy alias
    'ExecutionMode',
    'SourceHandler',
    'PipelineOutput',
    'OutputType',
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
    'LensDistortion',
    'Perspective',
    # Coordinate Transforms
    'CoordinateTransform',
    'IdentityTransform',
    'LensTransform',
    'PerspectiveTransform',
    # Edge Detection
    'Canny',
    'Sobel',
    'Laplacian',
    'EdgeEnhance',
    # Morphology
    'MorphShape',
    'Erode',
    'Dilate',
    'MorphOpen',
    'MorphClose',
    'MorphGradient',
    'TopHat',
    'BlackHat',
    # Detection
    'FaceDetector',
    'EyeDetector',
    'ContourDetector',
    # Geometry detection and drawing
    'GeometryFilter',
    'HoughCircleDetector',
    'HoughLineDetector',
    'DrawGeometry',
    'ExtractRegions',
    'MergeRegions',
    # Channel operations
    'SplitChannels',
    'MergeChannels',
    'ExtractChannel',
    # Size matching
    'SizeMatcher',
    'SizeMatchMode',
    'AspectMode',
    'CropPosition',
    # Image generation
    'ImageGenerator',
    'GradientType',
]
