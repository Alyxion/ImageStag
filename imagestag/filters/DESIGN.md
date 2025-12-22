# Filter System Design

Dataclass-based filter system supporting PIL, OpenCV, and custom backends.
Filters are JSON-serializable for persistence and transfer.

## Core Principles

1. **Dataclass-based** - All filters are dataclasses with typed parameters
2. **JSON-serializable** - Filters can be saved/loaded as JSON
3. **Backend-agnostic** - Work with PIL, OpenCV, or RAW numpy
4. **Chainable** - Filters can be composed into pipelines
5. **Format-flexible** - Work with Image objects, JPEG/PNG bytes, or numpy arrays

## Architecture Overview

```
Filter (base)
├── apply(image, context) -> Image      # Image-based processing
├── process(data, context) -> ImageData # Universal format processing
└── Format declarations (_accepted_formats, _output_format)

FilterPipeline
├── Sequential filter chain
├── Automatic format conversion between filters
└── String parsing: 'resize(0.5)|blur(1.5)|encode(jpeg)'

FilterGraph
├── Branching filter chains
├── Named branches with combiners
└── String format: '[main:blur(2)][mask:gray]blend(main,mask)'

FilterContext
├── Data passing between filters
├── Hierarchical (parent-child for branches)
└── Analyzer results storage

ImageData
├── Universal container (Image, bytes, numpy array)
├── Factory: from_image(), from_bytes(), from_array()
└── Output: to_image(), to_pil(), to_cv(), to_bytes(), to_array()
```

## Processing Methods

### apply() - Image-based (traditional)
```python
result_image = filter.apply(input_image, context)
result_image = pipeline.apply(input_image)
```

### process() - Format-flexible (universal)
```python
# Input can be Image, JPEG bytes, or numpy array
data = ImageData.from_bytes(jpeg_bytes)
data = ImageData.from_array(cv_frame, pixel_format='BGR')
data = ImageData.from_image(image)

# Process through pipeline
result = pipeline.process(data)

# Output in any format
jpeg_out = result.to_bytes()     # Compressed bytes
cv_array = result.to_cv()        # BGR numpy array
pil_img = result.to_pil()        # PIL Image
image = result.to_image()        # ImageStag Image
```

## Format System

### FormatSpec
Describes image format: pixel format, bit depth, compression.

```python
FormatSpec.RGB         # RGB pixel data
FormatSpec.BGR         # OpenCV-style BGR
FormatSpec.GRAY        # Grayscale
FormatSpec.JPEG        # JPEG compressed
FormatSpec.PNG         # PNG compressed
FormatSpec.ANY         # Accepts any format
```

### Filter Format Declarations
Filters can declare what formats they accept and produce:
- `_accepted_formats` - List of acceptable input formats
- `_output_format` - Format this filter produces
- `_implicit_conversion` - Auto-convert incompatible inputs (default: True)
- `_native_imagedata` - Filter overrides process() for direct format handling

## Filter Categories

### Basic Filters
| Filter | Parameters | Description |
|--------|------------|-------------|
| Brightness | factor (0-2+) | Adjust brightness |
| Contrast | factor (0-2+) | Adjust contrast |
| Saturation | factor (0-2+) | Adjust saturation |
| Grayscale | - | Convert to grayscale |
| Invert | - | Invert colors |
| Threshold | value, method | Binary threshold |

### Blur & Sharpen
| Filter | Parameters | Description |
|--------|------------|-------------|
| GaussianBlur | radius, sigma | Gaussian blur |
| BoxBlur | radius | Box blur |
| Sharpen | amount | Sharpen image |
| UnsharpMask | radius, percent | Unsharp mask |

### Geometric
| Filter | Parameters | Description |
|--------|------------|-------------|
| Resize | scale or size | Resize image |
| Crop | x, y, width, height | Crop region |
| Rotate | angle, expand | Rotate image |
| Flip | horizontal, vertical | Mirror image |
| LensDistortion | k1, k2, k3, p1, p2 | Radial lens distortion |
| Perspective | src_points, dst_points | Perspective transform |

### Coordinate Transforms

Both `LensDistortion` and `Perspective` filters can return a coordinate transform
object for bidirectional point mapping via `apply_with_transform()`:

```python
# Apply filter and get transform
result, transform = LensDistortion(k1=-0.2).apply_with_transform(image)

# Map points from original (distorted) to corrected coordinates
corrected_pt = transform.forward((100, 200))

# Map points from corrected back to original coordinates
original_pt = transform.inverse((150, 180))

# Batch transform multiple points efficiently
corrected_pts = transform.forward_points([(10, 10), (50, 50), (90, 30)])
original_pts = transform.inverse_points(corrected_pts)
```

| Transform Class | Used By | forward() | inverse() |
|-----------------|---------|-----------|-----------|
| LensTransform | LensDistortion | distorted → undistorted | undistorted → distorted |
| PerspectiveTransform | Perspective | original → corrected | corrected → original |

### Edge Detection
| Filter | Parameters | Description |
|--------|------------|-------------|
| Canny | threshold1, threshold2 | Canny edge detection |
| Sobel | ksize, dx, dy | Sobel gradient |
| Laplacian | ksize | Laplacian edge detection |
| EdgeEnhance | strength | PIL edge enhancement |

### Morphological
| Filter | Parameters | Description |
|--------|------------|-------------|
| Erode | kernel_size, iterations | Erode foreground |
| Dilate | kernel_size, iterations | Dilate foreground |
| MorphOpen | kernel_size | Opening (erode then dilate) |
| MorphClose | kernel_size | Closing (dilate then erode) |
| MorphGradient | kernel_size | Morphological gradient |
| TopHat | kernel_size | Top-hat transform |
| BlackHat | kernel_size | Black-hat transform |

### Detection
| Filter | Parameters | Description |
|--------|------------|-------------|
| FaceDetector | draw, color | Haar cascade face detection |
| EyeDetector | draw, color | Haar cascade eye detection |
| ContourDetector | threshold, min_area, draw | Contour detection |

### Format Conversion
| Filter | Parameters | Description |
|--------|------------|-------------|
| Encode | format, quality | Compress to JPEG/PNG/WebP |
| Decode | format | Decompress to pixels |
| ConvertFormat | format | Convert pixel format (RGB/BGR/GRAY) |

### Analyzers
Analyzers compute information without modifying images. Results stored in context.

| Filter | Result Key | Description |
|--------|------------|-------------|
| ImageStats | stats | Width, height, brightness, channel stats |
| HistogramAnalyzer | histogram | Color histograms |
| ColorAnalyzer | colors | Dominant colors |

## String Format

### Pipeline Syntax
```
filter(args)|filter(args)|filter(args)
```

### Examples
```
# Positional args (primary parameter)
resize(0.5)|blur(1.5)|brightness(1.1)

# Named parameters
resize(scale=0.5)|encode(format=jpeg,quality=85)

# URL-safe (semicolon separator)
?filters=resize(0.5);blur(1.5);brightness(1.1)
```

### Primary Parameters
Each filter has a primary parameter for positional args:
- `resize` -> scale
- `blur` -> radius
- `brightness/contrast/saturation` -> factor
- `encode` -> format

### Aliases
- `blur`, `gaussian` -> GaussianBlur
- `gray`, `grey` -> Grayscale
- `lens` -> LensDistortion

## Filter Graphs

For complex operations with branching and combining:

```
[branch_name: filter|filter|...]
[another_branch: filter|filter|...]
combiner(branch1, branch2, args)
```

### Example: Masked Blur
```
[sharp: sharpen(2.0)]
[blurred: blur(10)]
[mask: gray|threshold(200)|invert]
composite(sharp, blurred, mask)
```

### Combiners
- `blend(a, b, mode)` - Blend two branches
- `composite(bg, fg, mask)` - Composite with mask
- `mask(image, mask)` - Apply mask as alpha

## JSON Serialization

```json
{
  "type": "FilterPipeline",
  "filters": [
    {"type": "Resize", "scale": 0.5},
    {"type": "GaussianBlur", "radius": 1.5},
    {"type": "Encode", "format": "jpeg", "quality": 85}
  ]
}
```

## Implementation Status

### Completed
- [x] Filter base class with JSON serialization
- [x] FilterPipeline with string parsing
- [x] FilterContext and FilterGraph
- [x] Format system (FormatSpec, ImageData, process())
- [x] Basic filters (Brightness, Contrast, Saturation, etc.)
- [x] Blur & Sharpen filters
- [x] Geometric transforms (Resize, Crop, Rotate, Flip)
- [x] Lens correction (LensDistortion, Perspective)
- [x] Edge detection (Canny, Sobel, Laplacian, EdgeEnhance)
- [x] Morphological operations (Erode, Dilate, Open, Close, Gradient, TopHat, BlackHat)
- [x] Detection filters (FaceDetector, EyeDetector, ContourDetector)
- [x] Format converters (Encode, Decode, ConvertFormat)
- [x] Analyzer filters (ImageStats, HistogramAnalyzer, ColorAnalyzer, RegionAnalyzer)
- [x] Compositing (BlendMode, Blend, Composite, MaskApply)

### Planned
- [ ] Advanced threshold (Otsu, adaptive)
- [ ] Color space conversions (LAB, HSL)
- [ ] Noise reduction (bilateral, non-local means)
