# ImageStag Filters - Base Classes
"""
Base classes for the filter system.

All filters are dataclasses with JSON serialization support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, field, MISSING
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

from imagestag.definitions import ImsFramework

# Type alias for filter output - single image, dict of images, geometry list, or image list
FilterOutput = Union[
    'Image',
    dict[str, 'Image'],
    'GeometryList',
    'ImageList',
    dict[str, Union['Image', 'GeometryList', 'ImageList']]
]


@dataclass
class ParameterInfo:
    """Documentation for a single filter parameter."""

    name: str
    type: str  # 'float', 'int', 'bool', 'str', 'color', 'select', 'tuple'
    default: Any
    description: str = ''
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    options: list[str] | None = None  # For select/enum types

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'name': self.name,
            'type': self.type,
            'default': self.default,
        }
        if self.description:
            result['description'] = self.description
        if self.min_value is not None:
            result['min'] = self.min_value
        if self.max_value is not None:
            result['max'] = self.max_value
        if self.step is not None:
            result['step'] = self.step
        if self.options:
            result['options'] = self.options
        return result


@dataclass
class PortInfo:
    """Documentation for an input or output port."""

    name: str
    description: str = ''
    type: str = 'image'  # 'image', 'mask', 'geometry', etc.

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {'name': self.name, 'description': self.description, 'type': self.type}


@dataclass
class FilterInfo:
    """Comprehensive documentation for a filter.

    Contains all information needed to understand and use a filter:
    - What it does (description)
    - What goes in (inputs)
    - What comes out (outputs)
    - How to configure it (parameters)
    - How to invoke it (aliases, DSL syntax)
    """

    name: str  # Class name
    description: str  # Full docstring
    summary: str  # First line of docstring
    category: str  # e.g., 'color', 'blur', 'geometric', 'detection'

    parameters: list[ParameterInfo] = field(default_factory=list)
    input_ports: list[PortInfo] = field(default_factory=list)
    output_ports: list[PortInfo] = field(default_factory=list)

    aliases: list[str] = field(default_factory=list)  # All registered aliases
    parameterized_aliases: dict[str, dict[str, Any]] = field(default_factory=dict)  # alias -> params

    native_frameworks: list[str] = field(default_factory=list)  # ['PIL', 'CV', 'RAW']
    requires: list[str] = field(default_factory=list)  # Optional dependencies

    examples: list[str] = field(default_factory=list)  # DSL usage examples

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'summary': self.summary,
            'category': self.category,
            'parameters': [p.to_dict() for p in self.parameters],
            'input_ports': [p.to_dict() for p in self.input_ports],
            'output_ports': [p.to_dict() for p in self.output_ports],
            'aliases': self.aliases,
            'parameterized_aliases': self.parameterized_aliases,
            'native_frameworks': self.native_frameworks,
            'requires': self.requires,
            'examples': self.examples,
        }

    def to_markdown(self) -> str:
        """Generate markdown documentation."""
        lines = [f'# {self.name}', '', self.description, '']

        if self.aliases:
            lines.append('## Aliases')
            lines.append('')
            for alias in self.aliases:
                if alias in self.parameterized_aliases:
                    params = self.parameterized_aliases[alias]
                    param_str = ', '.join(f'{k}={v}' for k, v in params.items())
                    lines.append(f'- `{alias}` → `{self.name}({param_str})`')
                else:
                    lines.append(f'- `{alias}`')
            lines.append('')

        if self.parameters:
            lines.append('## Parameters')
            lines.append('')
            lines.append('| Name | Type | Default | Description |')
            lines.append('|------|------|---------|-------------|')
            for p in self.parameters:
                default_str = repr(p.default) if isinstance(p.default, str) else str(p.default)
                lines.append(f'| `{p.name}` | {p.type} | {default_str} | {p.description} |')
            lines.append('')

        if len(self.input_ports) > 1 or (self.input_ports and self.input_ports[0].name != 'input'):
            lines.append('## Input Ports')
            lines.append('')
            for port in self.input_ports:
                lines.append(f'- **{port.name}**: {port.description or port.type}')
            lines.append('')

        if len(self.output_ports) > 1 or (self.output_ports and self.output_ports[0].name != 'output'):
            lines.append('## Output Ports')
            lines.append('')
            for port in self.output_ports:
                lines.append(f'- **{port.name}**: {port.description or port.type}')
            lines.append('')

        if self.examples:
            lines.append('## Examples')
            lines.append('')
            for example in self.examples:
                lines.append(f'```')
                lines.append(example)
                lines.append('```')
            lines.append('')

        if self.native_frameworks:
            lines.append('## Frameworks')
            lines.append('')
            lines.append(f'Native support: {", ".join(self.native_frameworks)}')
            lines.append('')

        if self.requires:
            lines.append('## Requirements')
            lines.append('')
            for req in self.requires:
                lines.append(f'- {req}')
            lines.append('')

        return '\n'.join(lines)


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
FILTER_ALIASES: dict[str, type['Filter'] | tuple[type['Filter'], dict[str, Any]]] = {}


def register_filter(cls: type['Filter']) -> type['Filter']:
    """Decorator to register a filter class."""
    FILTER_REGISTRY[cls.__name__] = cls
    # Also register lowercase version
    FILTER_REGISTRY[cls.__name__.lower()] = cls
    return cls


def register_alias(
    alias: str,
    cls: type['Filter'],
    **default_params: Any
) -> None:
    """Register an alias for a filter class with optional default parameters.

    Examples:
        register_alias('blur', GaussianBlur)  # Simple alias
        register_alias('rot90', Rotate, angle=90)  # Alias with default params
        register_alias('mirror', Flip, mode='h')  # Flip horizontal shortcut
    """
    if default_params:
        FILTER_ALIASES[alias.lower()] = (cls, default_params)
    else:
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

    # Framework preferences for optimized pipeline execution
    # These help minimize unnecessary framework conversions in batch processing
    _native_frameworks: ClassVar[list[ImsFramework]] = []  # Frameworks that work without conversion
    _preferred_framework: ClassVar[ImsFramework | None] = None  # Preferred framework (first native)
    _supports_inplace: ClassVar[bool] = False  # Can this filter modify input buffer directly?

    # Gallery/documentation metadata
    _gallery_skip: ClassVar[bool] = False  # Skip in gallery (needs special input)
    _gallery_sample: ClassVar[str | None] = None  # Specific sample image name
    _gallery_multi_output: ClassVar[bool] = False  # Outputs multiple images (show as grid)
    _gallery_synthetic: ClassVar[str | None] = None  # Needs synthetic image: 'lines', 'circles', etc.

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
    def get_native_frameworks(cls) -> list[ImsFramework]:
        """Get list of frameworks this filter can use without conversion."""
        return cls._native_frameworks

    @classmethod
    def get_preferred_framework(cls) -> ImsFramework | None:
        """Get preferred framework, or first native framework if not set."""
        if cls._preferred_framework:
            return cls._preferred_framework
        if cls._native_frameworks:
            return cls._native_frameworks[0]
        return None

    @classmethod
    def supports_framework(cls, framework: ImsFramework) -> bool:
        """Check if this filter can work natively with a framework."""
        return framework in cls._native_frameworks

    @classmethod
    def supports_inplace(cls) -> bool:
        """Check if this filter supports in-place operations."""
        return cls._supports_inplace

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
        from imagestag.color import Color

        data = {}
        # Only include fields that are actual dataclass fields
        for f in fields(self):
            if not f.name.startswith('_'):
                value = getattr(self, f.name)
                # Handle enums - prefer string value, fallback to lowercase name
                if isinstance(value, Enum):
                    if isinstance(value.value, str):
                        value = value.value
                    else:
                        value = value.name.lower()
                # Handle Color - serialize to hex string
                elif isinstance(value, Color):
                    value = value.to_hex()
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
        """Parse single filter from compact string format.

        Supports two syntaxes:
        1. New compact syntax (space-separated):
            'blur 5'           -> GaussianBlur(radius=5)
            'resize 0.5 0.5'   -> Resize(width=0.5, height=0.5)
            'gray'             -> Grayscale()
            'lens k1=-0.15'    -> LensDistortion(k1=-0.15)

        2. Legacy syntax (parentheses):
            'blur(1.5)'
            'resize(scale=0.5)'

        Examples:
            'blur 5'
            'brightness 1.2'
            'canny 100 200'
            'blend mode=multiply opacity=0.7'
        """
        text = text.strip()

        # Try legacy parentheses syntax first for backward compatibility
        match = re.match(r'^(\w+)\(([^)]*)\)$', text)
        if match:
            name = match.group(1).lower()
            args_str = match.group(2)
            return cls._parse_legacy(name, args_str)

        # New compact syntax: space-separated
        parts = _split_filter_args(text)
        if not parts:
            raise ValueError(f"Invalid filter format: {text}")

        name = parts[0].lower()
        args = parts[1:]

        # Find filter class (check aliases first, then registry)
        alias_entry = FILTER_ALIASES.get(name)
        default_params = {}

        if alias_entry is not None:
            if isinstance(alias_entry, tuple):
                # Alias with default parameters: (cls, {params})
                filter_cls, default_params = alias_entry
            else:
                # Simple alias: just the class
                filter_cls = alias_entry
        else:
            filter_cls = FILTER_REGISTRY.get(name)

        if filter_cls is None:
            raise ValueError(f"Unknown filter: {name}")

        # Start with default params from alias, then override with user args
        kwargs = dict(default_params)

        # Parse positional and keyword arguments
        positional = []
        for arg in args:
            if '=' in arg and not arg.startswith('#'):
                # Keyword argument (but not hex colors like #ff0000)
                key, value = arg.split('=', 1)
                kwargs[key.strip()] = _parse_value(value.strip())
            else:
                # Positional argument
                positional.append(_parse_value(arg))

        # Map positional args to parameter names
        if positional:
            kwargs = cls._map_positional_args(filter_cls, positional, kwargs)

        return filter_cls(**kwargs)

    @classmethod
    def _parse_legacy(cls, name: str, args_str: str) -> 'Filter':
        """Parse legacy parentheses syntax."""
        alias_entry = FILTER_ALIASES.get(name)
        default_params = {}

        if alias_entry is not None:
            if isinstance(alias_entry, tuple):
                filter_cls, default_params = alias_entry
            else:
                filter_cls = alias_entry
        else:
            filter_cls = FILTER_REGISTRY.get(name)

        if filter_cls is None:
            raise ValueError(f"Unknown filter: {name}")

        kwargs = dict(default_params)
        if args_str:
            for i, arg in enumerate(args_str.split(',')):
                arg = arg.strip()
                if not arg:
                    continue
                if '=' in arg:
                    key, value = arg.split('=', 1)
                    kwargs[key.strip()] = _parse_value(value.strip())
                elif i == 0 and filter_cls._primary_param:
                    kwargs[filter_cls._primary_param] = _parse_value(arg)
                else:
                    raise ValueError(f"Positional arg not supported for {name}: {arg}")

        return filter_cls(**kwargs)

    @classmethod
    def _map_positional_args(
        cls,
        filter_cls: type['Filter'],
        positional: list[Any],
        kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """Map positional arguments to filter parameters.

        Uses dataclass field order, skipping fields that start with '_'.
        """
        # Get dataclass fields in order (excluding private ones)
        param_names = []
        for f in fields(filter_cls):
            if not f.name.startswith('_') and f.name != 'inputs':
                param_names.append(f.name)

        # Map positional args to parameter names
        for i, value in enumerate(positional):
            if i < len(param_names):
                param_name = param_names[i]
                if param_name not in kwargs:  # Don't override explicit kwargs
                    kwargs[param_name] = value
            else:
                raise ValueError(
                    f"Too many positional args for {filter_cls.__name__}: "
                    f"got {len(positional)}, max {len(param_names)}"
                )

        return kwargs

    @classmethod
    def get_info(cls) -> FilterInfo:
        """Get comprehensive documentation for this filter.

        Returns a FilterInfo object containing:
        - Description and summary from docstring
        - All parameters with types, defaults, and descriptions
        - Input/output port specifications
        - Registered aliases (including parameterized ones)
        - Native frameworks and requirements

        Example:
            info = GaussianBlur.get_info()
            print(info.to_markdown())
            print(info.to_dict())
        """
        return _build_filter_info(cls)

    @classmethod
    def help(cls) -> str:
        """Get human-readable help text for this filter.

        Returns markdown-formatted documentation.
        """
        return cls.get_info().to_markdown()

    def to_string(self) -> str:
        """Convert filter to compact string format.

        Uses the new space-separated syntax:
            'blur 5'
            'brightness 1.2'
            'blend mode=multiply opacity=0.7'
        """
        parts = [self.type.lower()]

        # Get all non-private, non-default parameters
        for f in fields(self):
            if f.name.startswith('_') or f.name == 'inputs':
                continue
            value = getattr(self, f.name)

            # Skip default values
            if f.default is not MISSING and value == f.default:
                continue
            if f.default_factory is not MISSING:
                try:
                    if value == f.default_factory():
                        continue
                except Exception:
                    pass

            # Format value
            if isinstance(value, Enum):
                if isinstance(value.value, str):
                    value_str = value.value
                else:
                    value_str = value.name.lower()
            elif isinstance(value, str):
                # Quote strings that contain spaces or special chars
                if ' ' in value or '=' in value:
                    value_str = f"'{value}'"
                else:
                    value_str = value
            elif isinstance(value, bool):
                value_str = 'true' if value else 'false'
            else:
                value_str = str(value)

            parts.append(f"{f.name}={value_str}")

        return ' '.join(parts)


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
    """Parse string value to appropriate type.

    Handles:
    - Booleans: true, false
    - Integers: 42, -5
    - Floats: 3.14, -0.5
    - Quoted strings: 'hello', "world" -> hello, world
    - Hex colors: #ff0000 (preserved as string)
    - Plain strings: anything else
    """
    s = s.strip()

    # Handle quoted strings - strip quotes and return as string
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]

    # Hex colors should stay as strings
    if s.startswith('#'):
        return s

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


def _check_skimage() -> None:
    """Check that scikit-image is installed.

    Raises ImportError with helpful message if not available.
    """
    try:
        import skimage  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "scikit-image is required for this filter. "
            "Install with: pip install scikit-image"
        ) from e


def _split_filter_args(text: str) -> list[str]:
    """Split filter text into name and arguments, handling quoted strings.

    Examples:
        'blur 5' -> ['blur', '5']
        'blend mode="normal"' -> ['blend', 'mode="normal"']
        'imgen linear #000 #fff' -> ['imgen', 'linear', '#000', '#fff']
        "size_match 'smaller'" -> ['size_match', "'smaller'"]
    """
    parts = []
    current = []
    in_quotes = None  # None, '"', or "'"

    for char in text:
        if in_quotes:
            current.append(char)
            if char == in_quotes:
                in_quotes = None
        elif char in '"\'':
            in_quotes = char
            current.append(char)
        elif char.isspace():
            if current:
                parts.append(''.join(current))
                current = []
        else:
            current.append(char)

    if current:
        parts.append(''.join(current))

    return parts


def _parse_docstring_params(docstring: str) -> dict[str, str]:
    """Extract parameter descriptions from docstring.

    Supports formats:
        param_name: description
        param_name (type): description
        :param param_name: description

    Returns dict mapping parameter names to descriptions.
    """
    params = {}
    if not docstring:
        return params

    lines = docstring.split('\n')
    current_param = None
    current_desc = []

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            if current_param:
                params[current_param] = ' '.join(current_desc).strip()
                current_param = None
                current_desc = []
            continue

        # :param name: description format
        if line.startswith(':param '):
            if current_param:
                params[current_param] = ' '.join(current_desc).strip()
            match = re.match(r':param\s+(\w+):\s*(.*)', line)
            if match:
                current_param = match.group(1)
                current_desc = [match.group(2)] if match.group(2) else []
            continue

        # name: description format (Parameters section)
        match = re.match(r'^(\w+)(?:\s*\([^)]*\))?:\s*(.*)', line)
        if match and not line.startswith('Example'):
            if current_param:
                params[current_param] = ' '.join(current_desc).strip()
            current_param = match.group(1)
            current_desc = [match.group(2)] if match.group(2) else []
            continue

        # Continuation line
        if current_param and line and not line.endswith(':'):
            current_desc.append(line)

    # Save last parameter
    if current_param:
        params[current_param] = ' '.join(current_desc).strip()

    return params


def _extract_examples(docstring: str) -> list[str]:
    """Extract DSL examples from docstring.

    Looks for Example: or Examples: sections with quoted strings.
    """
    examples = []
    if not docstring:
        return examples

    in_example = False
    for line in docstring.split('\n'):
        line = line.strip()
        if line.lower().startswith('example'):
            in_example = True
            continue
        if in_example:
            # Look for quoted DSL strings
            match = re.search(r"'([^']+)'", line)
            if match:
                examples.append(match.group(1))

    return examples


def _infer_category(cls: type) -> str:
    """Infer filter category from module name or class hierarchy."""
    module = cls.__module__
    if 'color' in module:
        return 'color'
    elif 'blur' in module:
        return 'blur'
    elif 'geometric' in module:
        return 'geometric'
    elif 'edge' in module:
        return 'edge'
    elif 'detection' in module:
        return 'detection'
    elif 'morphology' in module:
        return 'morphology'
    elif 'histogram' in module:
        return 'histogram'
    elif 'channels' in module:
        return 'channels'
    elif 'generator' in module:
        return 'generator'
    elif 'analyzers' in module:
        return 'analyzer'
    elif 'geometry' in module:
        return 'geometry'
    elif 'graph' in module:
        return 'combiner'
    elif 'size_matcher' in module:
        return 'combiner'
    elif 'skeleton' in module or 'ridge' in module:
        return 'morphology'
    elif 'restoration' in module:
        return 'restoration'
    elif 'threshold' in module:
        return 'threshold'
    elif 'texture' in module:
        return 'texture'
    elif 'segmentation' in module:
        return 'segmentation'
    elif 'exposure' in module:
        return 'exposure'
    elif 'converters' in module:
        return 'format'
    return 'other'


def _get_param_type(field_type: Any, field_name: str) -> str:
    """Determine parameter type from field type annotation."""
    from typing import get_origin, get_args

    type_str = str(field_type).lower()

    # Check for Color type
    try:
        from imagestag.color import Color
        if isinstance(field_type, type) and issubclass(field_type, Color):
            return 'color'
    except (TypeError, ImportError):
        pass

    # Check for Enum
    try:
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            return 'select'
    except TypeError:
        pass

    # Basic types
    if 'int' in type_str:
        return 'int'
    elif 'float' in type_str:
        return 'float'
    elif 'bool' in type_str:
        return 'bool'
    elif 'str' in type_str:
        # Check if it looks like a color field by name
        if 'color' in field_name.lower():
            return 'color'
        return 'str'
    elif 'tuple' in type_str:
        return 'tuple'
    elif 'list' in type_str:
        return 'list'

    return 'any'


def _build_filter_info(cls: type['Filter']) -> FilterInfo:
    """Build FilterInfo from a filter class."""
    from typing import get_type_hints

    # Get docstring
    docstring = cls.__doc__ or ''
    lines = docstring.strip().split('\n')
    summary = lines[0].strip() if lines else ''
    description = docstring.strip()

    # Parse parameter descriptions from docstring
    param_docs = _parse_docstring_params(docstring)

    # Extract examples
    examples = _extract_examples(docstring)

    # Get category
    category = _infer_category(cls)

    # Build parameter info
    parameters = []
    try:
        type_hints = get_type_hints(cls)
    except Exception:
        type_hints = {}

    for f in fields(cls):
        if f.name.startswith('_') or f.name == 'inputs':
            continue

        # Get type
        field_type = type_hints.get(f.name, f.type)
        param_type = _get_param_type(field_type, f.name)

        # Get default value
        if f.default is not MISSING:
            default = f.default
        elif f.default_factory is not MISSING:
            try:
                default = f.default_factory()
                # Convert Color to hex for display
                try:
                    from imagestag.color import Color
                    if isinstance(default, Color):
                        default = default.to_hex()
                except ImportError:
                    pass
            except Exception:
                default = None
        else:
            default = None

        # Get enum options
        options = None
        try:
            if isinstance(field_type, type) and issubclass(field_type, Enum):
                options = [e.name.lower() for e in field_type]
        except TypeError:
            pass

        # Get description from docstring
        desc = param_docs.get(f.name, '')

        parameters.append(ParameterInfo(
            name=f.name,
            type=param_type,
            default=default,
            description=desc,
            options=options,
        ))

    # Build port info
    input_ports = []
    for port in cls.get_input_ports():
        input_ports.append(PortInfo(
            name=port.get('name', 'input'),
            description=port.get('description', ''),
            type=port.get('type', 'image'),
        ))

    output_ports = []
    for port in cls.get_output_ports():
        output_ports.append(PortInfo(
            name=port.get('name', 'output'),
            description=port.get('description', ''),
            type=port.get('type', 'image'),
        ))

    # Find aliases
    aliases = []
    parameterized_aliases = {}
    class_name_lower = cls.__name__.lower()

    for alias, entry in FILTER_ALIASES.items():
        if isinstance(entry, tuple):
            alias_cls, params = entry
            if alias_cls is cls:
                aliases.append(alias)
                parameterized_aliases[alias] = params
        else:
            if entry is cls:
                aliases.append(alias)

    # Get native frameworks
    native_frameworks = [fw.name for fw in cls._native_frameworks]

    # Check for requirements
    requires = []
    if 'skimage' in str(cls.__module__) or '_check_skimage' in str(cls.apply):
        requires.append('scikit-image')

    # Check docstring for requirements
    if 'scikit-image' in docstring.lower() or 'skimage' in docstring.lower():
        if 'scikit-image' not in requires:
            requires.append('scikit-image')

    return FilterInfo(
        name=cls.__name__,
        description=description,
        summary=summary,
        category=category,
        parameters=parameters,
        input_ports=input_ports,
        output_ports=output_ports,
        aliases=aliases,
        parameterized_aliases=parameterized_aliases,
        native_frameworks=native_frameworks,
        requires=requires,
        examples=examples,
    )


def get_all_filters_info() -> dict[str, FilterInfo]:
    """Get documentation for all registered filters.

    Returns a dict mapping filter names to FilterInfo objects.

    Example:
        catalog = get_all_filters_info()
        for name, info in catalog.items():
            print(f"{name}: {info.summary}")
    """
    result = {}
    seen = set()

    for name, cls in FILTER_REGISTRY.items():
        # Skip lowercase duplicates
        if cls in seen:
            continue
        if name != cls.__name__:
            continue
        seen.add(cls)

        try:
            result[name] = cls.get_info()
        except Exception:
            # Skip filters that fail to introspect
            pass

    return result


def get_filter_info(name: str) -> FilterInfo | None:
    """Get documentation for a filter by name or alias.

    Args:
        name: Filter class name or alias (e.g., 'GaussianBlur', 'blur', 'rot90')

    Returns:
        FilterInfo object, or None if not found.

    Example:
        info = get_filter_info('blur')
        print(info.to_markdown())
    """
    name_lower = name.lower()

    # Check aliases first
    if name_lower in FILTER_ALIASES:
        entry = FILTER_ALIASES[name_lower]
        if isinstance(entry, tuple):
            cls = entry[0]
        else:
            cls = entry
        return cls.get_info()

    # Check registry
    cls = FILTER_REGISTRY.get(name) or FILTER_REGISTRY.get(name_lower)
    if cls:
        return cls.get_info()

    return None
