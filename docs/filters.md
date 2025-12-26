# Filter Reference

ImageStag provides 60+ filters organized by category. All filters are dataclasses and JSON-serializable.

## Basic Usage

```python
from imagestag.filters import Resize, GaussianBlur, Brightness

# Apply single filter
result = Resize(scale=0.5).apply(image)

# Chain filters
result = Brightness(factor=1.2).apply(
    GaussianBlur(radius=2).apply(image)
)

# Parse from string
filter = Filter.parse("resize scale=0.5")
result = filter.apply(image)
```

---

## Color Adjustments

| Filter | Parameters | Description |
|--------|------------|-------------|
| `Brightness` | `factor` (0-2+) | Adjust brightness. 0=black, 1=original, 2=2x bright |
| `Contrast` | `factor` (0-2+) | Adjust contrast. 0=gray, 1=original |
| `Saturation` | `factor` (0-2+) | Adjust saturation. 0=grayscale, 2=vivid |
| `Sharpness` | `factor` (0-2+) | Adjust sharpness |
| `Grayscale` | `method` | Convert to grayscale ('luminosity', 'average') |
| `Invert` | - | Invert colors (negative) |
| `Threshold` | `value` (0-255) | Binary threshold |
| `AutoContrast` | `cutoff`, `preserve_tone` | Auto-adjust contrast from histogram |
| `Posterize` | `bits` (1-8) | Reduce bits per channel |
| `Solarize` | `threshold` | Invert pixels above threshold |
| `Equalize` | - | Equalize histogram |
| `FalseColor` | `colormap`, `reverse` | Apply matplotlib colormap |

### FalseColor Examples

```python
from imagestag.filters import FalseColor

# Thermal visualization
thermal = FalseColor(colormap='inferno').apply(image)

# Scientific visualization
viridis = FalseColor(colormap='viridis').apply(image)

# Reversed colormap
reversed = FalseColor(colormap='hot', reverse=True).apply(image)

# Aliases
from imagestag.filters import Filter
lava = Filter.parse('lava')      # hot colormap
thermal = Filter.parse('thermal') # inferno colormap
```

---

## Blur & Sharpen

| Filter | Parameters | Description |
|--------|------------|-------------|
| `GaussianBlur` | `radius`, `sigma` | Gaussian blur |
| `BoxBlur` | `radius` | Box/mean blur |
| `MedianBlur` | `size` | Median filter (noise reduction) |
| `BilateralFilter` | `d`, `sigma_color`, `sigma_space` | Edge-preserving blur |
| `UnsharpMask` | `radius`, `percent`, `threshold` | Sharpen via unsharp mask |
| `Sharpen` | `amount` | Simple sharpening |
| `Smooth` | - | PIL smooth filter |
| `Detail` | - | PIL detail enhancement |
| `Contour` | - | Find edges/contours |
| `Emboss` | - | Emboss effect |
| `FindEdges` | - | Edge detection |

---

## Geometric Transforms

| Filter | Parameters | Description |
|--------|------------|-------------|
| `Resize` | `scale` or `size`, `interpolation` | Resize image |
| `Crop` | `x`, `y`, `width`, `height` | Crop region |
| `CenterCrop` | `width`, `height` | Crop from center |
| `Rotate` | `angle`, `expand`, `fill` | Rotate image |
| `Flip` | `mode` ('h', 'v', 'both') | Mirror image |
| `LensDistortion` | `k1`, `k2`, `k3`, `p1`, `p2` | Radial lens correction |
| `Perspective` | `src_points`, `dst_points` | Perspective transform |

### Resize Performance

Resize uses OpenCV by default for 20x better performance than PIL:

```python
from imagestag.filters import Resize

# Scale-based resize
half = Resize(scale=0.5).apply(image)

# Target size
fhd = Resize(size=(1920, 1080)).apply(image)

# Specific interpolation
from imagestag.interpolation import InterpolationMethod
resized = Resize(size=(800, 600), interpolation=InterpolationMethod.LANCZOS).apply(image)
```

### Rotation Aliases

```python
from imagestag.filters import Filter

rot90 = Filter.parse('rot90')     # 90 degrees
rot180 = Filter.parse('rot180')   # 180 degrees
rot270 = Filter.parse('rot270')   # 270 degrees
rotcw = Filter.parse('rotcw')     # 90 clockwise
rotccw = Filter.parse('rotccw')   # 90 counter-clockwise
mirror = Filter.parse('mirror')   # Horizontal flip
flipud = Filter.parse('flipud')   # Vertical flip
```

---

## Edge Detection

| Filter | Parameters | Description |
|--------|------------|-------------|
| `Canny` | `low_threshold`, `high_threshold` | Canny edge detection |
| `Sobel` | `dx`, `dy`, `ksize` | Sobel operator |
| `Laplacian` | `ksize` | Laplacian edge detection |
| `EdgeEnhance` | `strength` | Enhance edges |
| `Scharr` | `dx`, `dy` | Scharr operator |

---

## Histogram Operations

| Filter | Parameters | Description |
|--------|------------|-------------|
| `EqualizeHist` | - | Histogram equalization |
| `CLAHE` | `clip_limit`, `tile_grid_size` | Adaptive histogram equalization |
| `AdaptiveThreshold` | `block_size`, `c`, `method` | Adaptive thresholding |

---

## Morphological Operations

| Filter | Parameters | Description |
|--------|------------|-------------|
| `Erode` | `kernel_size`, `shape`, `iterations` | Erosion |
| `Dilate` | `kernel_size`, `shape`, `iterations` | Dilation |
| `MorphOpen` | `kernel_size`, `shape` | Opening (erode then dilate) |
| `MorphClose` | `kernel_size`, `shape` | Closing (dilate then erode) |
| `MorphGradient` | `kernel_size`, `shape` | Morphological gradient |
| `TopHat` | `kernel_size`, `shape` | Top-hat transform |
| `BlackHat` | `kernel_size`, `shape` | Black-hat transform |

---

## Detection Filters

| Filter | Output | Description |
|--------|--------|-------------|
| `FaceDetector` | GeometryList | Haar cascade face detection |
| `EyeDetector` | GeometryList | Eye detection |
| `ContourDetector` | GeometryList | Contour detection |
| `HoughCircleDetector` | GeometryList | Circle detection |
| `HoughLineDetector` | GeometryList | Line detection |

```python
from imagestag.filters import FaceDetector, DrawGeometry

# Detect faces
faces = FaceDetector(scale_factor=1.3, min_neighbors=5).apply(image)

# Draw detected faces on image
result = DrawGeometry(color='#FF0000', thickness=2).apply_multi({
    'input': image,
    'geometry': faces
})
```

---

## Geometry Processing

| Filter | Inputs | Description |
|--------|--------|-------------|
| `DrawGeometry` | `input`, `geometry` | Draw geometries on image |
| `ExtractRegions` | `input`, `geometry` | Crop regions to ImageList |
| `MergeRegions` | `input`, `regions` | Paste regions back |

---

## Channel Operations

| Filter | Description |
|--------|-------------|
| `SplitChannels` | Split image into separate channels |
| `MergeChannels` | Merge channels into image |
| `ExtractChannel` | Extract single channel |

---

## Combiner Filters

Multi-input filters for blending and compositing:

| Filter | Inputs | Description |
|--------|--------|-------------|
| `Blend` | `a`, `b`, `mask` (optional) | Blend with mode |
| `Composite` | `a`, `b`, `mask` | Composite overlay |
| `MaskApply` | `input`, `mask` | Apply mask as alpha |
| `SizeMatcher` | `a`, `b` | Match two images to same size |

### Blend Modes

```python
from imagestag.filters import Blend, BlendMode

blended = Blend(mode=BlendMode.MULTIPLY, opacity=0.8).apply_multi({
    'a': base_image,
    'b': overlay_image
})
```

Available modes: `NORMAL`, `MULTIPLY`, `SCREEN`, `OVERLAY`, `DARKEN`, `LIGHTEN`, `COLOR_DODGE`, `COLOR_BURN`, `HARD_LIGHT`, `SOFT_LIGHT`, `DIFFERENCE`, `EXCLUSION`

---

## Format Converters

| Filter | Parameters | Description |
|--------|------------|-------------|
| `Encode` | `format`, `quality` | Encode to JPEG/PNG bytes |
| `Decode` | `format` | Decode compressed image |
| `ToDataUrl` | `format`, `quality` | Convert to base64 data URL |
| `ConvertFormat` | `format` | Convert pixel format |

```python
from imagestag.filters import Encode, ToDataUrl, FilterPipeline

# Encode pipeline for web
pipeline = FilterPipeline([
    Resize(size=(800, 600)),
    Encode(format='jpeg', quality=85),
    ToDataUrl()
])

result = pipeline.apply(image)
data_url = result.metadata['_data_url']
```

---

## Image Generation

```python
from imagestag.filters import ImageGenerator, GradientType

# Create gradient
gradient = ImageGenerator(
    gradient_type=GradientType.LINEAR,
    color_start='#000000',
    color_end='#FFFFFF',
    size=(256, 256)
).apply()

# Radial gradient
radial = ImageGenerator(
    gradient_type=GradientType.RADIAL,
    color_start='#FF0000',
    color_end='#0000FF'
).apply()
```

---

## Scikit-image Filters

Advanced filters using scikit-image (optional dependency):

### Skeleton/Topology
- `Skeletonize` - Reduce to skeleton
- `MedialAxis` - Medial axis transform
- `RemoveSmallObjects` - Remove small objects
- `RemoveSmallHoles` - Fill small holes

### Ridge Detection
- `Frangi` - Frangi vesselness filter
- `Sato` - Sato tubeness filter
- `Meijering` - Meijering neuriteness
- `Hessian` - Hessian filter

### Restoration
- `DenoiseNLMeans` - Non-local means denoising
- `DenoiseTV` - Total variation denoising
- `DenoiseWavelet` - Wavelet denoising
- `Inpaint` - Inpainting

### Thresholding
- `ThresholdOtsu` - Otsu's method
- `ThresholdLi` - Li's method
- `ThresholdYen` - Yen's method
- `ThresholdTriangle` - Triangle method
- `ThresholdNiblack` - Niblack local threshold
- `ThresholdSauvola` - Sauvola local threshold

### Texture Analysis
- `Gabor` - Gabor filter
- `LBP` - Local Binary Pattern
- `GaborBank` - Bank of Gabor filters

### Segmentation
- `SLIC` - SLIC superpixels
- `Felzenszwalb` - Felzenszwalb segmentation
- `Watershed` - Watershed segmentation

### Exposure
- `AdjustGamma` - Gamma correction
- `AdjustLog` - Logarithmic adjustment
- `AdjustSigmoid` - Sigmoid adjustment
- `MatchHistograms` - Match histogram to reference
- `RescaleIntensity` - Rescale intensity range

---

## Serialization

All filters serialize to JSON:

```python
from imagestag.filters import Resize, Filter

# To dict/JSON
resize = Resize(scale=0.5)
d = resize.to_dict()
# {'type': 'Resize', 'scale': 0.5, ...}

# From dict
restored = Filter.from_dict(d)

# To/from string
s = resize.to_string()  # "resize(scale=0.5)"
parsed = Filter.parse(s)
```
