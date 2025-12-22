# Filter System Design

Dataclass-based filter system supporting PIL, OpenCV, and custom backends.
Filters are JSON-serializable for persistence and transfer.

## Core Principles

1. **Dataclass-based** - All filters are dataclasses with typed parameters
2. **JSON-serializable** - Filters can be saved/loaded as JSON
3. **Backend-agnostic** - Work with PIL, OpenCV, or RAW numpy
4. **Chainable** - Filters can be composed into pipelines
5. **Lazy evaluation** - Pipelines describe transforms, execute on demand

## Base Classes

```python
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from typing import Any
from enum import Enum, auto
import json

from imagestag import Image


class FilterBackend(Enum):
    """Preferred backend for filter execution."""
    AUTO = auto()    # Choose best available
    PIL = auto()     # Pillow
    CV = auto()      # OpenCV
    RAW = auto()     # Pure numpy


@dataclass
class Filter(ABC):
    """Base class for all filters."""

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
        data = asdict(self)
        data['type'] = self.type
        return data

    def to_json(self) -> str:
        """Serialize filter to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Filter':
        """Deserialize filter from dictionary."""
        filter_type = data.pop('type', cls.__name__)
        filter_cls = FILTER_REGISTRY.get(filter_type, cls)
        return filter_cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'Filter':
        """Deserialize filter from JSON string."""
        return cls.from_dict(json.loads(json_str))


# Global registry for filter types
FILTER_REGISTRY: dict[str, type[Filter]] = {}


def register_filter(cls: type[Filter]) -> type[Filter]:
    """Decorator to register a filter class."""
    FILTER_REGISTRY[cls.__name__] = cls
    return cls
```

## Filter Categories

### 1. Color Adjustments

```python
@register_filter
@dataclass
class Brightness(Filter):
    """Adjust image brightness."""
    factor: float = 1.0  # 0.0 = black, 1.0 = original, 2.0 = 2x bright

    def apply(self, image: Image) -> Image:
        # PIL: ImageEnhance.Brightness
        # CV: convertScaleAbs or addWeighted
        pass


@register_filter
@dataclass
class Contrast(Filter):
    """Adjust image contrast."""
    factor: float = 1.0  # 0.0 = gray, 1.0 = original, 2.0 = high contrast

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Saturation(Filter):
    """Adjust color saturation."""
    factor: float = 1.0  # 0.0 = grayscale, 1.0 = original, 2.0 = vivid

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class HueShift(Filter):
    """Shift hue by degrees."""
    degrees: float = 0.0  # -180 to 180

    def apply(self, image: Image) -> Image:
        # Convert to HSV, shift H channel, convert back
        pass


@register_filter
@dataclass
class ColorBalance(Filter):
    """Adjust RGB channel balance."""
    red: float = 1.0
    green: float = 1.0
    blue: float = 1.0

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Grayscale(Filter):
    """Convert to grayscale."""
    method: str = 'luminosity'  # 'luminosity', 'average', 'lightness'

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Invert(Filter):
    """Invert colors (negative)."""

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Threshold(Filter):
    """Binary threshold."""
    value: int = 128          # 0-255
    method: str = 'binary'    # 'binary', 'otsu', 'adaptive'
    adaptive_block: int = 11  # for adaptive method
    adaptive_c: int = 2       # for adaptive method

    def apply(self, image: Image) -> Image:
        # CV: cv2.threshold, cv2.adaptiveThreshold
        pass


@register_filter
@dataclass
class GammaCorrection(Filter):
    """Apply gamma correction."""
    gamma: float = 1.0  # <1 = brighter, >1 = darker

    def apply(self, image: Image) -> Image:
        pass
```

### 2. Blur & Sharpen

```python
@register_filter
@dataclass
class GaussianBlur(Filter):
    """Gaussian blur."""
    radius: float = 2.0
    sigma: float | None = None  # Auto-calculate if None

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV  # OpenCV is faster

    def apply(self, image: Image) -> Image:
        # PIL: ImageFilter.GaussianBlur
        # CV: cv2.GaussianBlur
        pass


@register_filter
@dataclass
class BoxBlur(Filter):
    """Box (average) blur."""
    radius: int = 2

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class MedianBlur(Filter):
    """Median blur (good for salt-and-pepper noise)."""
    kernel_size: int = 5  # Must be odd

    def apply(self, image: Image) -> Image:
        # CV: cv2.medianBlur
        pass


@register_filter
@dataclass
class BilateralFilter(Filter):
    """Edge-preserving smoothing."""
    d: int = 9                  # Diameter
    sigma_color: float = 75.0   # Color space sigma
    sigma_space: float = 75.0   # Coordinate space sigma

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: Image) -> Image:
        # CV: cv2.bilateralFilter
        pass


@register_filter
@dataclass
class Sharpen(Filter):
    """Sharpen image."""
    amount: float = 1.0   # Sharpening strength
    radius: float = 1.0   # Blur radius for unsharp mask
    threshold: int = 0    # Minimum difference to sharpen

    def apply(self, image: Image) -> Image:
        # Unsharp mask: original + amount * (original - blurred)
        pass


@register_filter
@dataclass
class UnsharpMask(Filter):
    """Unsharp mask sharpening."""
    radius: float = 2.0
    percent: int = 150
    threshold: int = 3

    def apply(self, image: Image) -> Image:
        # PIL: ImageFilter.UnsharpMask
        pass
```

### 3. Edge Detection

```python
@register_filter
@dataclass
class Canny(Filter):
    """Canny edge detection."""
    threshold1: float = 100.0
    threshold2: float = 200.0
    aperture_size: int = 3

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: Image) -> Image:
        # CV: cv2.Canny
        pass


@register_filter
@dataclass
class Sobel(Filter):
    """Sobel edge detection."""
    dx: int = 1           # Order of derivative x
    dy: int = 1           # Order of derivative y
    kernel_size: int = 3  # 1, 3, 5, or 7

    def apply(self, image: Image) -> Image:
        # CV: cv2.Sobel
        pass


@register_filter
@dataclass
class Laplacian(Filter):
    """Laplacian edge detection."""
    kernel_size: int = 3

    def apply(self, image: Image) -> Image:
        # CV: cv2.Laplacian
        pass


@register_filter
@dataclass
class EdgeEnhance(Filter):
    """Enhance edges."""
    strength: str = 'normal'  # 'normal', 'more'

    def apply(self, image: Image) -> Image:
        # PIL: ImageFilter.EDGE_ENHANCE, EDGE_ENHANCE_MORE
        pass
```

### 4. Geometric Transforms

```python
from imagestag import Size, InterpolationMethod


@register_filter
@dataclass
class Resize(Filter):
    """Resize image."""
    size: tuple[int, int] | None = None  # (width, height)
    scale: float | None = None           # Scale factor (alternative to size)
    method: InterpolationMethod = InterpolationMethod.LANCZOS

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Crop(Filter):
    """Crop image region."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class CenterCrop(Filter):
    """Crop from center."""
    width: int = 0
    height: int = 0

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Rotate(Filter):
    """Rotate image."""
    angle: float = 0.0           # Degrees, counter-clockwise
    expand: bool = False         # Expand canvas to fit
    fill_color: tuple = (0, 0, 0)  # Background fill

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Flip(Filter):
    """Flip image."""
    horizontal: bool = False
    vertical: bool = False

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Pad(Filter):
    """Add padding around image."""
    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0
    color: tuple = (0, 0, 0)
    mode: str = 'constant'  # 'constant', 'edge', 'reflect', 'wrap'

    def apply(self, image: Image) -> Image:
        pass
```

### 5. Lens & Perspective Correction

```python
@register_filter
@dataclass
class LensDistortionCorrection(Filter):
    """Correct barrel/pincushion lens distortion.

    Uses the Brown-Conrady distortion model.
    Positive k1 = barrel, Negative k1 = pincushion
    """
    # Radial distortion coefficients
    k1: float = 0.0
    k2: float = 0.0
    k3: float = 0.0

    # Tangential distortion coefficients
    p1: float = 0.0
    p2: float = 0.0

    # Focal length (in pixels)
    fx: float | None = None  # Auto-estimate if None
    fy: float | None = None

    # Principal point (optical center)
    cx: float | None = None  # Default to image center
    cy: float | None = None

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: Image) -> Image:
        # CV: cv2.undistort with camera matrix and distortion coefficients
        pass

    @classmethod
    def from_camera_calibration(cls, camera_matrix, dist_coeffs) -> 'LensDistortionCorrection':
        """Create from OpenCV calibration results."""
        pass


@register_filter
@dataclass
class PerspectiveCorrection(Filter):
    """Correct perspective distortion (4-point transform).

    Define 4 source points and 4 destination points.
    """
    # Source points (corners in distorted image)
    src_points: list[tuple[float, float]] = field(default_factory=list)

    # Destination points (where they should be)
    dst_points: list[tuple[float, float]] = field(default_factory=list)

    # Output size (None = auto)
    output_size: tuple[int, int] | None = None

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: Image) -> Image:
        # CV: cv2.getPerspectiveTransform + cv2.warpPerspective
        pass

    @classmethod
    def from_quadrilateral(cls, quad: list[tuple[float, float]],
                           target_width: int, target_height: int) -> 'PerspectiveCorrection':
        """Create transform to straighten a quadrilateral to rectangle."""
        return cls(
            src_points=quad,
            dst_points=[
                (0, 0),
                (target_width, 0),
                (target_width, target_height),
                (0, target_height)
            ],
            output_size=(target_width, target_height)
        )


@register_filter
@dataclass
class AffineTransform(Filter):
    """Apply affine transformation (rotation, scale, shear, translation)."""
    # 2x3 transformation matrix (row-major)
    matrix: list[list[float]] = field(default_factory=lambda: [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0]
    ])

    output_size: tuple[int, int] | None = None

    def apply(self, image: Image) -> Image:
        # CV: cv2.warpAffine
        pass

    @classmethod
    def from_rotation(cls, angle: float, center: tuple[float, float] | None = None,
                      scale: float = 1.0) -> 'AffineTransform':
        """Create rotation transform."""
        # CV: cv2.getRotationMatrix2D
        pass

    @classmethod
    def from_three_points(cls, src: list[tuple[float, float]],
                          dst: list[tuple[float, float]]) -> 'AffineTransform':
        """Create from 3-point correspondence."""
        # CV: cv2.getAffineTransform
        pass


@register_filter
@dataclass
class Deskew(Filter):
    """Automatically straighten skewed images (e.g., scanned documents)."""
    max_angle: float = 45.0  # Maximum skew angle to consider

    @property
    def preferred_backend(self) -> FilterBackend:
        return FilterBackend.CV

    def apply(self, image: Image) -> Image:
        # Detect text/line angle using Hough transform or moments
        # Apply rotation to straighten
        pass
```

### 6. Morphological Operations

```python
class MorphShape(Enum):
    RECT = auto()
    ELLIPSE = auto()
    CROSS = auto()


@register_filter
@dataclass
class Erode(Filter):
    """Morphological erosion."""
    kernel_size: int = 3
    shape: MorphShape = MorphShape.RECT
    iterations: int = 1

    def apply(self, image: Image) -> Image:
        # CV: cv2.erode
        pass


@register_filter
@dataclass
class Dilate(Filter):
    """Morphological dilation."""
    kernel_size: int = 3
    shape: MorphShape = MorphShape.RECT
    iterations: int = 1

    def apply(self, image: Image) -> Image:
        # CV: cv2.dilate
        pass


@register_filter
@dataclass
class MorphOpen(Filter):
    """Morphological opening (erosion then dilation)."""
    kernel_size: int = 3
    shape: MorphShape = MorphShape.RECT

    def apply(self, image: Image) -> Image:
        # CV: cv2.morphologyEx MORPH_OPEN
        pass


@register_filter
@dataclass
class MorphClose(Filter):
    """Morphological closing (dilation then erosion)."""
    kernel_size: int = 3
    shape: MorphShape = MorphShape.RECT

    def apply(self, image: Image) -> Image:
        # CV: cv2.morphologyEx MORPH_CLOSE
        pass
```

## Filter Pipeline

```python
@dataclass
class FilterPipeline(Filter):
    """Chain of filters applied in sequence."""
    filters: list[Filter] = field(default_factory=list)

    def apply(self, image: Image) -> Image:
        result = image
        for f in self.filters:
            result = f.apply(result)
        return result

    def append(self, filter: Filter) -> 'FilterPipeline':
        """Add filter to pipeline (chainable)."""
        self.filters.append(filter)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            'type': 'FilterPipeline',
            'filters': [f.to_dict() for f in self.filters]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FilterPipeline':
        filters = [Filter.from_dict(f) for f in data.get('filters', [])]
        return cls(filters=filters)


# Fluent API
pipeline = (
    FilterPipeline()
    .append(Resize(scale=0.5))
    .append(GaussianBlur(radius=2))
    .append(Sharpen(amount=1.5))
    .append(Brightness(factor=1.1))
)

result = pipeline.apply(image)
```

## Composite Filters (Blend Modes)

```python
class BlendMode(Enum):
    NORMAL = auto()
    MULTIPLY = auto()
    SCREEN = auto()
    OVERLAY = auto()
    SOFT_LIGHT = auto()
    HARD_LIGHT = auto()
    DARKEN = auto()
    LIGHTEN = auto()
    DIFFERENCE = auto()
    EXCLUSION = auto()
    ADD = auto()
    SUBTRACT = auto()


@register_filter
@dataclass
class Blend(Filter):
    """Blend two images together."""
    mode: BlendMode = BlendMode.NORMAL
    opacity: float = 1.0  # 0.0-1.0
    overlay_image: Image | str | None = None  # Image, path, or URL

    def apply(self, image: Image) -> Image:
        pass


@register_filter
@dataclass
class Composite(Filter):
    """Composite image with mask."""
    foreground: Image | str | None = None
    mask: Image | str | None = None  # Alpha mask

    def apply(self, image: Image) -> Image:
        # background (input) + foreground using mask
        pass
```

## Serialization

### JSON Format

```json
{
  "type": "FilterPipeline",
  "filters": [
    {
      "type": "Resize",
      "scale": 0.5,
      "method": "LANCZOS"
    },
    {
      "type": "LensDistortionCorrection",
      "k1": -0.15,
      "k2": 0.02,
      "k3": 0.0,
      "p1": 0.0,
      "p2": 0.0
    },
    {
      "type": "GaussianBlur",
      "radius": 1.5
    },
    {
      "type": "Brightness",
      "factor": 1.1
    },
    {
      "type": "Contrast",
      "factor": 1.2
    }
  ]
}
```

### URL/String Format

Compact string format for URLs, query parameters, and quick usage.

**Basic syntax:**
```
filter(args)|filter(args)|filter(args)
```

**Examples:**
```
# Simple - positional args map to primary parameter
resize(0.5)|blur(1.5)|brightness(1.1)

# Named parameters
resize(scale=0.5)|lens(k1=-0.15,k2=0.02)|blur(radius=1.5)

# Mixed
resize(0.5)|blur(radius=1.5,sigma=0.5)|sharpen(2.0)

# URL-safe (semicolon separator)
?filters=resize(0.5);blur(1.5);brightness(1.1)
```

**Primary parameters** (used for positional args):

| Filter | Primary Param |
|--------|---------------|
| `resize` | `scale` |
| `blur`, `gaussian` | `radius` |
| `brightness` | `factor` |
| `contrast` | `factor` |
| `saturation` | `factor` |
| `sharpen` | `amount` |
| `rotate` | `angle` |
| `threshold` | `value` |
| `lens` | `k1` |

**Filter aliases** (case-insensitive):

| Alias | Filter Class |
|-------|--------------|
| `blur`, `gaussian` | GaussianBlur |
| `lens`, `undistort` | LensDistortionCorrection |
| `perspective`, `warp` | PerspectiveCorrection |
| `gray`, `grayscale` | Grayscale |

### Implementation

```python
@dataclass
class FilterPipeline(Filter):
    filters: list[Filter] = field(default_factory=list)

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


class Filter(ABC):
    # ... existing methods ...

    # Primary parameter for positional args in string format
    _primary_param: ClassVar[str | None] = None

    @classmethod
    def parse(cls, text: str) -> 'Filter':
        """Parse single filter from string.

        Examples:
            'blur(1.5)'
            'resize(scale=0.5)'
            'lens(k1=-0.15,k2=0.02)'
        """
        match = re.match(r'(\w+)\(([^)]*)\)', text.strip())
        if not match:
            raise ValueError(f"Invalid filter format: {text}")

        name = match.group(1).lower()
        args_str = match.group(2)

        # Find filter class
        filter_cls = FILTER_ALIASES.get(name) or FILTER_REGISTRY.get(name.title())
        if not filter_cls:
            raise ValueError(f"Unknown filter: {name}")

        # Parse arguments
        kwargs = {}
        if args_str:
            for i, arg in enumerate(args_str.split(',')):
                arg = arg.strip()
                if '=' in arg:
                    key, value = arg.split('=', 1)
                    kwargs[key.strip()] = _parse_value(value.strip())
                elif i == 0 and filter_cls._primary_param:
                    # Positional arg goes to primary parameter
                    kwargs[filter_cls._primary_param] = _parse_value(arg)
                else:
                    raise ValueError(f"Positional arg not supported: {arg}")

        return filter_cls(**kwargs)

    def to_string(self) -> str:
        """Convert filter to compact string format."""
        params = []
        for key, value in asdict(self).items():
            if key.startswith('_'):
                continue
            params.append(f"{key}={value}")
        return f"{self.type.lower()}({','.join(params)})"


# Alias registry
FILTER_ALIASES: dict[str, type[Filter]] = {
    'blur': GaussianBlur,
    'gaussian': GaussianBlur,
    'lens': LensDistortionCorrection,
    'undistort': LensDistortionCorrection,
    'perspective': PerspectiveCorrection,
    'warp': PerspectiveCorrection,
    'gray': Grayscale,
    'grayscale': Grayscale,
}


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
```

### Usage Examples

```python
# Parse from URL
pipeline = FilterPipeline.parse("resize(0.5)|blur(1.5)|brightness(1.1)")

# Parse from request
pipeline = FilterPipeline.parse(request.args.get('filters', ''))

# Convert back to string
s = pipeline.to_string()  # "resize(scale=0.5)|gaussianblur(radius=1.5)|brightness(factor=1.1)"

# Use in image URL
url = f"/image/{image_id}?filters=resize(0.5);blur(1.5)"
```

## Filter Graphs (Branching & Combining)

For complex operations requiring multiple branches that are combined.

### Use Cases

- Create mask from one branch, apply to image from another
- Color correction on background, different treatment for foreground
- Multiple filter chains blended together

### FilterGraph Class

```python
@dataclass
class FilterGraph(Filter):
    """Directed acyclic graph of filter operations with named branches."""

    branches: dict[str, list[Filter]] = field(default_factory=dict)
    output: Filter | None = None  # Combining filter (e.g., Blend, Composite)

    def branch(self, name: str, filters: list[Filter]) -> 'BranchRef':
        """Define a named branch of filters."""
        self.branches[name] = filters
        return BranchRef(name)

    def apply(self, image: Image) -> Image:
        """Apply graph to image."""
        # Execute each branch
        results: dict[str, Image] = {}
        for name, filters in self.branches.items():
            result = image
            for f in filters:
                result = f.apply(result)
            results[name] = result

        # Apply output combiner
        if self.output:
            return self.output.apply_multi(results)

        # If no combiner, return last branch
        return list(results.values())[-1]

    @classmethod
    def parse(cls, text: str) -> 'FilterGraph':
        """Parse graph from string format.

        Format:
            [branch_name: filter|filter|...]
            [another_branch: filter|filter|...]
            combiner(branch1, branch2, args)

        Example:
            [main: resize(0.5)|blur(1.5)]
            [mask: gray|threshold(128)]
            blend(main, mask, multiply)
        """
        graph = cls()
        lines = [l.strip() for l in text.strip().split('\n') if l.strip()]

        # Also handle single-line: [a:...][b:...]combiner(...)
        if len(lines) == 1:
            lines = re.split(r'(?<=\])\s*(?=\[|[a-z])', lines[0])

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Branch definition: [name: filters]
            branch_match = re.match(r'\[(\w+):\s*([^\]]+)\]', line)
            if branch_match:
                name = branch_match.group(1)
                filters_str = branch_match.group(2)
                filters = [Filter.parse(f.strip())
                           for f in re.split(r'[|;]', filters_str) if f.strip()]
                graph.branches[name] = filters
                continue

            # Output combiner: blend(a, b, mode)
            if '(' in line:
                graph.output = CombinerFilter.parse(line)

        return graph

    def to_dict(self) -> dict[str, Any]:
        return {
            'type': 'FilterGraph',
            'branches': {
                name: [f.to_dict() for f in filters]
                for name, filters in self.branches.items()
            },
            'output': self.output.to_dict() if self.output else None,
        }

    def to_string(self) -> str:
        parts = []
        for name, filters in self.branches.items():
            filters_str = '|'.join(f.to_string() for f in filters)
            parts.append(f'[{name}:{filters_str}]')
        if self.output:
            parts.append(self.output.to_string())
        return ''.join(parts)


@dataclass
class BranchRef:
    """Reference to a named branch in a FilterGraph."""
    name: str
```

### Combiner Filters

Filters that take multiple inputs:

```python
@dataclass
class CombinerFilter(Filter):
    """Base class for filters that combine multiple inputs."""

    inputs: list[str] = field(default_factory=list)  # Branch names

    def apply_multi(self, images: dict[str, Image]) -> Image:
        """Apply filter to multiple named inputs."""
        raise NotImplementedError

    def apply(self, image: Image) -> Image:
        # Single input fallback
        return image

    @classmethod
    def parse(cls, text: str) -> 'CombinerFilter':
        """Parse combiner: blend(a, b, multiply)"""
        match = re.match(r'(\w+)\(([^)]+)\)', text.strip())
        if not match:
            raise ValueError(f"Invalid combiner format: {text}")

        name = match.group(1).lower()
        args = [a.strip() for a in match.group(2).split(',')]

        if name == 'blend':
            return Blend(
                inputs=args[:2],
                mode=BlendMode[args[2].upper()] if len(args) > 2 else BlendMode.NORMAL
            )
        elif name == 'composite':
            return Composite(inputs=args[:3])  # bg, fg, mask
        elif name == 'mask':
            return MaskApply(inputs=args[:2])  # image, mask

        raise ValueError(f"Unknown combiner: {name}")


@register_filter
@dataclass
class Blend(CombinerFilter):
    """Blend two branches together."""
    mode: BlendMode = BlendMode.NORMAL
    opacity: float = 1.0

    def apply_multi(self, images: dict[str, Image]) -> Image:
        if len(self.inputs) < 2:
            raise ValueError("Blend requires 2 inputs")
        base = images[self.inputs[0]]
        overlay = images[self.inputs[1]]
        return blend_images(base, overlay, self.mode, self.opacity)


@register_filter
@dataclass
class Composite(CombinerFilter):
    """Composite foreground over background using mask."""

    def apply_multi(self, images: dict[str, Image]) -> Image:
        if len(self.inputs) < 3:
            raise ValueError("Composite requires 3 inputs: bg, fg, mask")
        bg = images[self.inputs[0]]
        fg = images[self.inputs[1]]
        mask = images[self.inputs[2]]
        return composite_images(bg, fg, mask)


@register_filter
@dataclass
class MaskApply(CombinerFilter):
    """Apply mask to image (set alpha from mask)."""

    def apply_multi(self, images: dict[str, Image]) -> Image:
        if len(self.inputs) < 2:
            raise ValueError("MaskApply requires 2 inputs: image, mask")
        image = images[self.inputs[0]]
        mask = images[self.inputs[1]]
        return apply_mask(image, mask)
```

### Examples

**Create masked blur effect:**
```python
# String format
graph = FilterGraph.parse("""
    [sharp: sharpen(2.0)]
    [blurred: blur(10)]
    [mask: gray|threshold(200)|invert]
    composite(sharp, blurred, mask)
""")

# Python API
graph = FilterGraph()
graph.branch('sharp', [Sharpen(amount=2.0)])
graph.branch('blurred', [GaussianBlur(radius=10)])
graph.branch('mask', [Grayscale(), Threshold(value=200), Invert()])
graph.output = Composite(inputs=['sharp', 'blurred', 'mask'])
```

**Color grading with luminosity blend:**
```python
graph = FilterGraph.parse("""
    [color: saturation(1.5)|hue(15)]
    [luma: gray]
    blend(color, luma, luminosity)
""")
```

**Compact single-line:**
```
[a:resize(0.5)|blur(1.5)][b:gray|threshold(128)]blend(a,b,multiply)
```

### JSON Format

```json
{
  "type": "FilterGraph",
  "branches": {
    "main": [
      {"type": "Resize", "scale": 0.5},
      {"type": "GaussianBlur", "radius": 1.5}
    ],
    "mask": [
      {"type": "Grayscale"},
      {"type": "Threshold", "value": 128}
    ]
  },
  "output": {
    "type": "Blend",
    "inputs": ["main", "mask"],
    "mode": "MULTIPLY"
  }
}
```

## Usage with Stage

```python
from imagestag import Stage, SyncMode
from imagestag.filters import FilterPipeline, GaussianBlur, Sharpen

# Create filter pipeline
enhance = FilterPipeline([
    GaussianBlur(radius=1),
    Sharpen(amount=2.0),
])

# Use as layer filter
stage = Stage()
camera = stage.add_layer(source=CameraProvider())
enhanced = stage.add_layer(
    source=enhance,
    input_layer=camera,
    sync_mode=SyncMode.SYNCED
)
```

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Filter base class with JSON serialization
- [ ] Filter registry
- [ ] FilterPipeline

### Phase 2: Basic Filters
- [ ] Brightness, Contrast, Saturation
- [ ] Grayscale, Invert
- [ ] GaussianBlur, Sharpen

### Phase 3: Geometric
- [ ] Resize, Crop, Rotate, Flip
- [ ] Pad

### Phase 4: Computer Vision
- [ ] Canny, Sobel, Laplacian
- [ ] Threshold (binary, Otsu, adaptive)
- [ ] Morphological operations

### Phase 5: Lens Correction
- [ ] LensDistortionCorrection
- [ ] PerspectiveCorrection
- [ ] AffineTransform
- [ ] Deskew

### Phase 6: Compositing
- [ ] Blend modes
- [ ] Composite with mask
