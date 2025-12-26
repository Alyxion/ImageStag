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
    # Documentation classes
    FilterInfo,
    ParameterInfo,
    PortInfo,
    get_all_filters_info,
    get_filter_info,
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
    ToDataUrl,
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
    AutoContrast,
    Posterize,
    Solarize,
    Equalize,
    FalseColor,
)

from .blur import (
    GaussianBlur,
    BoxBlur,
    UnsharpMask,
    Sharpen,
    MedianBlur,
    BilateralFilter,
    MedianFilter,
    MinFilter,
    MaxFilter,
    ModeFilter,
    Smooth,
    Detail,
    Contour,
    Emboss,
    FindEdges,
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
    Scharr,
)

from .histogram import (
    EqualizeHist,
    CLAHE,
    AdaptiveThreshold,
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

# Scikit-image based filters (optional dependency)
from .skeleton import (
    Skeletonize,
    MedialAxis,
    RemoveSmallObjects,
    RemoveSmallHoles,
)

from .ridge import (
    Frangi,
    Sato,
    Meijering,
    Hessian,
)

from .restoration import (
    DenoiseNLMeans,
    DenoiseTV,
    DenoiseWavelet,
    Inpaint,
)

from .threshold import (
    ThresholdOtsu,
    ThresholdLi,
    ThresholdYen,
    ThresholdTriangle,
    ThresholdNiblack,
    ThresholdSauvola,
)

from .texture import (
    Gabor,
    LBP,
    GaborBank,
)

from .segmentation import (
    SLIC,
    Felzenszwalb,
    Watershed,
)

from .exposure import (
    AdjustGamma,
    AdjustLog,
    AdjustSigmoid,
    MatchHistograms,
    RescaleIntensity,
)

from .executor import (
    StreamingPipelineExecutor,
    BatchPipelineExecutor,
    ExecutorMetrics,
    StageMetrics,
)

from .benchmark import (
    Benchmark,
    BenchmarkConfig,
    BenchmarkResult,
    ExecutorResult,
    StageResult,
)

# Register aliases for compact DSL
register_alias('blur', GaussianBlur)
register_alias('gaussian', GaussianBlur)
register_alias('gray', Grayscale)
register_alias('grey', Grayscale)
register_alias('lens', LensDistortion)
register_alias('imgen', ImageGenerator)
register_alias('size_match', SizeMatcher)
register_alias('sizematch', SizeMatcher)
register_alias('draw', DrawGeometry)
register_alias('extract', ExtractRegions)
register_alias('merge', MergeRegions)
register_alias('face', FaceDetector)
register_alias('faces', FaceDetector)
register_alias('circles', HoughCircleDetector)
register_alias('lines', HoughLineDetector)

# Rotation shortcuts (parameterized aliases)
register_alias('rot90', Rotate, angle=90)
register_alias('rot180', Rotate, angle=180)
register_alias('rot270', Rotate, angle=270)
register_alias('rotcw', Rotate, angle=-90)   # 90° clockwise
register_alias('rotccw', Rotate, angle=90)   # 90° counter-clockwise

# Flip shortcuts (parameterized aliases)
register_alias('mirror', Flip, mode='h')     # Horizontal flip
register_alias('fliplr', Flip, mode='h')     # Flip left-right
register_alias('flipud', Flip, mode='v')     # Flip up-down
register_alias('flipv', Flip, mode='v')      # Flip vertical

# False color / colormap shortcuts
register_alias('lava', FalseColor, colormap='hot')
register_alias('thermal', FalseColor, colormap='inferno')
register_alias('plasma', FalseColor, colormap='plasma')
register_alias('magma', FalseColor, colormap='magma')
register_alias('viridis', FalseColor, colormap='viridis')
register_alias('coolwarm', FalseColor, colormap='coolwarm')
register_alias('jet', FalseColor, colormap='jet')

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
    # Documentation
    'FilterInfo',
    'ParameterInfo',
    'PortInfo',
    'get_all_filters_info',
    'get_filter_info',
    # Formats
    'BitDepth',
    'Compression',
    'FormatSpec',
    'ImageData',
    # Format conversion filters
    'Encode',
    'Decode',
    'ToDataUrl',
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
    'AutoContrast',
    'Posterize',
    'Solarize',
    'Equalize',
    'FalseColor',
    # Blur/Sharpen/Effects
    'GaussianBlur',
    'BoxBlur',
    'UnsharpMask',
    'Sharpen',
    'MedianBlur',
    'BilateralFilter',
    'MedianFilter',
    'MinFilter',
    'MaxFilter',
    'ModeFilter',
    'Smooth',
    'Detail',
    'Contour',
    'Emboss',
    'FindEdges',
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
    'Scharr',
    # Histogram Operations
    'EqualizeHist',
    'CLAHE',
    'AdaptiveThreshold',
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
    # Skeleton/Topology (scikit-image)
    'Skeletonize',
    'MedialAxis',
    'RemoveSmallObjects',
    'RemoveSmallHoles',
    # Ridge/Vessel Detection (scikit-image)
    'Frangi',
    'Sato',
    'Meijering',
    'Hessian',
    # Denoising/Restoration (scikit-image)
    'DenoiseNLMeans',
    'DenoiseTV',
    'DenoiseWavelet',
    'Inpaint',
    # Advanced Thresholding (scikit-image)
    'ThresholdOtsu',
    'ThresholdLi',
    'ThresholdYen',
    'ThresholdTriangle',
    'ThresholdNiblack',
    'ThresholdSauvola',
    # Texture Analysis (scikit-image)
    'Gabor',
    'LBP',
    'GaborBank',
    # Segmentation (scikit-image)
    'SLIC',
    'Felzenszwalb',
    'Watershed',
    # Exposure Adjustments (scikit-image)
    'AdjustGamma',
    'AdjustLog',
    'AdjustSigmoid',
    'MatchHistograms',
    'RescaleIntensity',
    # Pipeline Executors
    'StreamingPipelineExecutor',
    'BatchPipelineExecutor',
    'ExecutorMetrics',
    'StageMetrics',
    # Benchmarking
    'Benchmark',
    'BenchmarkConfig',
    'BenchmarkResult',
    'ExecutorResult',
    'StageResult',
]
