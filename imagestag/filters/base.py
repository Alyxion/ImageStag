# ImageStag Filters - Base Classes
"""
Base classes for the filter system.

All filters are dataclasses with JSON serialization support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, field
from enum import Enum, auto
from typing import Any, ClassVar, TYPE_CHECKING, Union
import copy
import json
import re

if TYPE_CHECKING:
    from imagestag import Image
    from imagestag.geometry_list import GeometryList
    from imagestag.image_list import ImageList
    from .formats import FormatSpec, ImageData

# Type alias for filter output - single image, dict of images, geometry list, or image list
FilterOutput = Union[
    'Image',
    dict[str, 'Image'],
    'GeometryList',
    'ImageList',
    dict[str, Union['Image', 'GeometryList', 'ImageList']]
]


@dataclass
class FilterContext:
    """Context object passed through filter pipelines.

    Allows filters to store and retrieve arbitrary data during processing.
    In FilterGraph, each branch gets its own context that inherits from
    the parent context.
    """

    data: dict[str, Any] = field(default_factory=dict)
    _parent: 'FilterContext | None' = field(default=None, repr=False)

    def __getitem__(self, key: str) -> Any:
        """Get a value, checking parent context if not found locally."""
        if key in self.data:
            return self.data[key]
        if self._parent is not None:
            return self._parent[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a value in this context."""
        self.data[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if key exists in this context or parent."""
        if key in self.data:
            return True
        if self._parent is not None:
            return key in self._parent
        return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value with optional default."""
        try:
            return self[key]
        except KeyError:
            return default

    def branch(self, name: str | None = None) -> 'FilterContext':
        """Create a child context that inherits from this one.

        Changes in the child don't affect the parent.
        Child can read parent values but writes go to child only.
        """
        child = FilterContext(_parent=self)
        if name:
            child.data['_branch'] = name
        return child

    def to_dict(self) -> dict[str, Any]:
        """Get all data including inherited values."""
        if self._parent is not None:
            result = self._parent.to_dict()
            result.update(self.data)
            return result
        return dict(self.data)

    def copy(self) -> 'FilterContext':
        """Create a shallow copy of this context (no parent link)."""
        return FilterContext(data=copy.copy(self.data))


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
    """Base class for all filters.

    Filters can declare their format requirements via class variables:
        _accepted_formats: List of FormatSpec that this filter accepts
        _output_format: FormatSpec describing what format this filter outputs
        _implicit_conversion: Whether to auto-convert incompatible inputs (default: True)

    When implicit_conversion is enabled (default), incompatible input formats are
    automatically converted before processing. Filter authors don't need to worry
    about format handling - just declare what formats you need.

    Example:
        @register_filter
        @dataclass
        class MyFilter(Filter):
            _accepted_formats: ClassVar[list[FormatSpec]] = [FormatSpec.RGB, FormatSpec.RGBA]
            _output_format: ClassVar[FormatSpec | None] = FormatSpec.RGB

            def apply(self, image: Image, context: FilterContext | None = None) -> Image:
                # Can assume image is in RGB or RGBA format
                ...
    """

    # Primary parameter name for string parsing (e.g., 'factor' for Brightness)
    _primary_param: ClassVar[str | None] = None

    # Format declarations (subclasses can override)
    _accepted_formats: ClassVar[list['FormatSpec'] | None] = None  # None = accepts any
    _output_format: ClassVar['FormatSpec | None'] = None  # None = same as input
    _implicit_conversion: ClassVar[bool] = True  # Auto-convert incompatible inputs
    _native_imagedata: ClassVar[bool] = False  # Override process() directly for native ImageData handling

    # Port specifications for multi-input/multi-output filters
    # None = single unnamed port (default behavior)
    # List of dicts with 'name' and optional 'description' keys
    _input_ports: ClassVar[list[dict] | None] = None
    _output_ports: ClassVar[list[dict] | None] = None

    @abstractmethod
    def apply(self, image: 'Image', context: FilterContext | None = None) -> 'Image':
        """Apply filter to image and return result.

        :param image: The input image to process.
        :param context: Optional context for storing/retrieving data during
            pipeline execution. Filters can read from and write to this.
        :returns: The processed image.
        """
        pass

    def __call__(
        self,
        image: 'Image | ImageList',
        context: FilterContext | None = None
    ) -> 'Image | ImageList':
        """Apply filter, automatically handling ImageList.

        If the input is an ImageList, applies the filter to each image
        and returns a new ImageList with processed images and preserved metadata.

        :param image: Single Image or ImageList to process.
        :param context: Optional context for pipeline execution.
        :returns: Processed Image or ImageList (same type as input).
        """
        from imagestag.image_list import ImageList

        if isinstance(image, ImageList):
            # Apply filter to each image, preserve metadata
            processed = [self.apply(img, context) for img in image.images]
            return image.with_images(processed)

        return self.apply(image, context)

    def process(self, data: 'ImageData', context: FilterContext | None = None) -> 'ImageData':
        """Process ImageData and return result.

        This is the universal processing method that works with any format
        (Image objects, compressed bytes, numpy arrays). By default, it
        converts to Image, calls apply(), and wraps the result back.

        Filters that want to work with non-Image data (e.g., JPEG bytes,
        numpy arrays) should override this method directly and set
        _native_imagedata = True.

        :param data: Input data in any supported format.
        :param context: Optional context for storing/retrieving data.
        :returns: Processed data wrapped in ImageData.
        """
        from .formats import ImageData
        # Default implementation: convert to Image, call apply(), wrap result
        image = data.to_image()
        result = self.apply(image, context)
        return ImageData.from_image(result)

    @classmethod
    def has_native_imagedata(cls) -> bool:
        """Check if this filter has native ImageData support.

        Filters with native support override process() directly and can
        work with compressed bytes or numpy arrays without conversion.
        """
        return cls._native_imagedata

    @classmethod
    def get_accepted_formats(cls) -> list['FormatSpec'] | None:
        """Get list of accepted input formats, or None if any format is accepted."""
        return cls._accepted_formats

    @classmethod
    def get_output_format(cls) -> 'FormatSpec | None':
        """Get the output format, or None if same as input."""
        return cls._output_format

    @classmethod
    def accepts_implicit_conversion(cls) -> bool:
        """Whether this filter allows automatic format conversion."""
        return cls._implicit_conversion

    @classmethod
    def get_input_ports(cls) -> list[dict]:
        """Get input port specifications.

        Returns list of dicts with 'name' and optional 'description'.
        Default: single 'input' port for standard filters.
        """
        return cls._input_ports or [{'name': 'input'}]

    @classmethod
    def get_output_ports(cls) -> list[dict]:
        """Get output port specifications.

        Returns list of dicts with 'name' and optional 'description'.
        Default: single 'output' port for standard filters.
        """
        return cls._output_ports or [{'name': 'output'}]

    @classmethod
    def is_multi_input(cls) -> bool:
        """Check if this filter has multiple input ports."""
        return cls._input_ports is not None and len(cls._input_ports) > 1

    @classmethod
    def is_multi_output(cls) -> bool:
        """Check if this filter has multiple output ports."""
        return cls._output_ports is not None and len(cls._output_ports) > 1

    @classmethod
    def accepts_format(cls, format_spec: 'FormatSpec') -> bool:
        """Check if this filter accepts a given format."""
        if cls._accepted_formats is None:
            return True  # Accepts any format
        return any(fmt.matches(format_spec) for fmt in cls._accepted_formats)

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
        for f in fields(self):
            if not f.name.startswith('_'):
                value = getattr(self, f.name)
                # Handle enums
                if isinstance(value, Enum):
                    value = value.name
                data[f.name] = value
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
        for f in fields(self):
            if f.name.startswith('_'):
                continue
            value = getattr(self, f.name)
            # Skip default values
            if value == f.default:
                continue
            # Handle enums
            if isinstance(value, Enum):
                value = value.name.lower()
            params.append(f"{f.name}={value}")
        return f"{self.type.lower()}({','.join(params)})"


@dataclass
class AnalyzerFilter(Filter):
    """Base class for filters that analyze images without modifying them.

    Analyzers compute information about the image (statistics, detected objects,
    quality metrics, etc.) and store results in context and/or image metadata.
    The image itself is returned unchanged.

    Subclasses should override `analyze()` to perform the actual analysis.

    Example:
        @register_filter
        @dataclass
        class BrightnessAnalyzer(AnalyzerFilter):
            result_key: str = 'brightness'

            def analyze(self, image: Image) -> float:
                pixels = image.get_pixels()
                return float(np.mean(pixels))
    """

    # Where to store results
    store_in_context: bool = True
    store_in_metadata: bool = False
    result_key: str = ''  # Key for storing result (defaults to lowercase class name)

    @abstractmethod
    def analyze(self, image: Image) -> Any:
        """Analyze the image and return results.

        Override this method to implement the analysis logic.

        :param image: The image to analyze.
        :returns: Analysis results (can be any type: dict, list, float, etc.)
        """
        pass

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        """Run analysis, store results, and return the image unchanged."""
        result = self.analyze(image)
        key = self.result_key or self.__class__.__name__.lower()

        if context is not None and self.store_in_context:
            context[key] = result

        if self.store_in_metadata:
            image.metadata[key] = result

        return image  # Return unchanged

    def process(self, data: 'ImageData', context: FilterContext | None = None) -> 'ImageData':
        """Run analysis on ImageData and return unchanged.

        Preserves the original format - if input was JPEG bytes, output is JPEG bytes.
        """
        # For analysis, we need to decode to Image for pixel access
        image = data.to_image()
        self.apply(image, context)

        # Return original data unchanged (preserve format)
        return data


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
