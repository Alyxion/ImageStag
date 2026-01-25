# ImageStag Filter Overview

This document provides a comprehensive comparison of all 30 ImageStag filters with their equivalents in OpenCV, scikit-image (SKImage), Adobe Photoshop, Affinity Photo, and GIMP.

## Filter Comparison Table

| # | ImageStag Filter | OpenCV | SKImage | Photoshop | Affinity Photo | GIMP |
|---|------------------|--------|---------|-----------|----------------|------|
| 1 | `brightness` | - | `exposure.adjust_gamma` | Image > Adjustments > Brightness/Contrast | Filters > Colours > Brightness/Contrast | Colors > Brightness-Contrast |
| 2 | `contrast` | `convertScaleAbs` | `exposure.rescale_intensity` | Image > Adjustments > Brightness/Contrast | Filters > Colours > Brightness/Contrast | Colors > Brightness-Contrast |
| 3 | `saturation` | `cvtColor` + adjust S | `color.rgb2hsv` + adjust | Image > Adjustments > Hue/Saturation | Filters > Colours > HSL | Colors > Hue-Saturation |
| 4 | `hue_shift` | `cvtColor` + shift H | `color.rgb2hsv` + shift | Image > Adjustments > Hue/Saturation | Filters > Colours > HSL | Colors > Hue-Saturation |
| 5 | `vibrance` | - | - | Image > Adjustments > Vibrance | Filters > Colours > Vibrance | - |
| 6 | `exposure` | `convertScaleAbs` | `exposure.adjust_gamma` | Image > Adjustments > Exposure | Filters > Colours > Exposure | Colors > Exposure |
| 7 | `gamma` | `LUT` | `exposure.adjust_gamma` | Image > Adjustments > Levels (gamma) | Filters > Colours > Levels | Colors > Levels |
| 8 | `color_balance` | - | - | Image > Adjustments > Color Balance | Filters > Colours > Colour Balance | Colors > Color Balance |
| 9 | `levels` | `normalize` | `exposure.rescale_intensity` | Image > Adjustments > Levels | Filters > Colours > Levels | Colors > Levels |
| 10 | `curves` | `LUT` | - | Image > Adjustments > Curves | Filters > Colours > Curves | Colors > Curves |
| 11 | `auto_levels` | `normalize` | `exposure.rescale_intensity` | Image > Auto Tone | Filters > Colours > Auto Levels | Colors > Auto > Normalize |
| 12 | `gaussian_blur` | `GaussianBlur` | `filters.gaussian` | Filter > Blur > Gaussian Blur | Filters > Blur > Gaussian Blur | Filters > Blur > Gaussian Blur |
| 13 | `box_blur` | `blur` / `boxFilter` | `filters.rank.mean` | Filter > Blur > Box Blur | Filters > Blur > Box Blur | Filters > Blur > Pixelize |
| 14 | `motion_blur` | `filter2D` (custom) | - | Filter > Blur > Motion Blur | Filters > Blur > Motion Blur | Filters > Blur > Motion Blur |
| 15 | `sharpen` | `filter2D` | `filters.unsharp_mask` | Filter > Sharpen > Sharpen | Filters > Sharpen > Sharpen | Filters > Enhance > Sharpen |
| 16 | `unsharp_mask` | `unsharpMask` | `filters.unsharp_mask` | Filter > Sharpen > Unsharp Mask | Filters > Sharpen > Unsharp Mask | Filters > Enhance > Unsharp Mask |
| 17 | `high_pass` | subtract from blur | - | Filter > Other > High Pass | Filters > Sharpen > High Pass | Filters > Enhance > High Pass |
| 18 | `sobel` | `Sobel` | `filters.sobel` | Filter > Stylize > Find Edges | - | Filters > Edge-Detect > Sobel |
| 19 | `laplacian` | `Laplacian` | `filters.laplace` | - | - | Filters > Edge-Detect > Laplacian |
| 20 | `find_edges` | `Canny` | `feature.canny` | Filter > Stylize > Find Edges | Filters > Detect > Edge Detection | Filters > Edge-Detect > Edge |
| 21 | `posterize` | `LUT` | - | Image > Adjustments > Posterize | Filters > Colours > Posterize | Colors > Posterize |
| 22 | `solarize` | `LUT` | `exposure.solarize` | Filter > Stylize > Solarize | Filters > Colours > Invert > Solarize | Filters > Distorts > Value Invert |
| 23 | `threshold` | `threshold` | `filters.threshold_otsu` | Image > Adjustments > Threshold | Filters > Colours > Threshold | Colors > Threshold |
| 24 | `invert` | `bitwise_not` | `util.invert` | Image > Adjustments > Invert | Filters > Colours > Invert | Colors > Invert |
| 25 | `emboss` | `filter2D` | - | Filter > Stylize > Emboss | Filters > Distort > Emboss | Filters > Distorts > Emboss |
| 26 | `add_noise` | `randn` / `randu` | `util.random_noise` | Filter > Noise > Add Noise | Filters > Noise > Add Noise | Filters > Noise > HSV Noise |
| 27 | `median` | `medianBlur` | `filters.median` | Filter > Noise > Median | Filters > Blur > Median | Filters > Enhance > Noise Reduction |
| 28 | `denoise` | `fastNlMeansDenoising` | `restoration.denoise_nl_means` | Filter > Noise > Reduce Noise | Filters > Noise > Denoise | Filters > Enhance > Noise Reduction |
| 29 | `dilate` | `dilate` | `morphology.dilation` | Filter > Other > Maximum | Filters > Distort > Dilate | Filters > Enhance > Dilate |
| 30 | `erode` | `erode` | `morphology.erosion` | Filter > Other > Minimum | Filters > Distort > Erode | Filters > Enhance > Erode |

---

## Detailed Parameter Comparison

### Category 1: Pixel-wise Color Adjustments

#### 1. Brightness

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `brightness(image, amount)` | `amount`: -1.0 to 1.0 (0 = no change) |
| **OpenCV** | - | No direct function; use `convertScaleAbs(src, alpha=1, beta=brightness*255)` |
| **SKImage** | `exposure.adjust_gamma(image, gamma)` | Brightness via gamma < 1 |
| **Photoshop** | Brightness/Contrast | Brightness: -150 to +150 |
| **Affinity** | Brightness/Contrast | Brightness: -100% to +100% |
| **GIMP** | Brightness-Contrast | Brightness: -127 to +127 |

#### 2. Contrast

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `contrast(image, amount)` | `amount`: -1.0 to 1.0 (0 = no change) |
| **OpenCV** | `convertScaleAbs(src, alpha, beta)` | `alpha`: contrast factor (1.0 = no change) |
| **SKImage** | `exposure.rescale_intensity(image, in_range, out_range)` | Range mapping |
| **Photoshop** | Brightness/Contrast | Contrast: -50 to +100 |
| **Affinity** | Brightness/Contrast | Contrast: -100% to +100% |
| **GIMP** | Brightness-Contrast | Contrast: -127 to +127 |

#### 3. Saturation

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `saturation(image, amount)` | `amount`: -1.0 to 1.0 (-1 = grayscale) |
| **OpenCV** | Convert to HSV, multiply S channel | Manual implementation |
| **SKImage** | `color.rgb2hsv()` then adjust S | Manual implementation |
| **Photoshop** | Hue/Saturation | Saturation: -100 to +100 |
| **Affinity** | HSL Adjustment | Saturation Shift: -100% to +100% |
| **GIMP** | Hue-Saturation | Saturation: -100 to +100 |

#### 4. Hue Shift

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `hue_shift(image, degrees)` | `degrees`: 0 to 360 |
| **OpenCV** | Convert to HSV, add to H channel | H range: 0-180 in OpenCV |
| **SKImage** | `color.rgb2hsv()` then shift H | H range: 0.0-1.0 |
| **Photoshop** | Hue/Saturation | Hue: -180 to +180 |
| **Affinity** | HSL Adjustment | Hue Shift: -180° to +180° |
| **GIMP** | Hue-Saturation | Hue: -180 to +180 |

#### 5. Vibrance

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `vibrance(image, amount)` | `amount`: -1.0 to 1.0 |
| **OpenCV** | - | Not available (custom implementation needed) |
| **SKImage** | - | Not available |
| **Photoshop** | Vibrance | Vibrance: -100 to +100 |
| **Affinity** | Vibrance | Vibrance: -100% to +100% |
| **GIMP** | - | Not available natively |

**Note:** Vibrance differs from saturation by boosting less-saturated colors more than already-saturated ones, preserving skin tones.

#### 6. Exposure

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `exposure(image, exposure_val, offset, gamma_val)` | `exposure_val`: -5.0 to 5.0 stops, `offset`: -0.5 to 0.5, `gamma_val`: 0.1-10.0 |
| **OpenCV** | `convertScaleAbs` with 2^exposure | Manual implementation |
| **SKImage** | `exposure.adjust_gamma(image, gamma, gain)` | `gamma`, `gain` |
| **Photoshop** | Exposure | Exposure: -20 to +20, Offset: -0.5 to +0.5, Gamma: 0.01 to 9.99 |
| **Affinity** | Exposure | Exposure: -5 to +5 EV |
| **GIMP** | Exposure | Exposure: -10 to +10 EV |

#### 7. Gamma

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `gamma(image, gamma_value)` | `gamma_value`: 0.1 to 10.0 (1.0 = no change) |
| **OpenCV** | `LUT` with gamma curve | Build LUT: `(i/255)^gamma * 255` |
| **SKImage** | `exposure.adjust_gamma(image, gamma)` | `gamma`: float |
| **Photoshop** | Levels (middle slider) | Gamma: 0.1 to 9.99 |
| **Affinity** | Levels (gamma) | Middle input slider |
| **GIMP** | Levels (middle slider) | Gamma: 0.1 to 10.0 |

#### 8. Color Balance

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `color_balance(image, shadows, midtones, highlights)` | Each: (R, G, B) adjustments -1.0 to 1.0 |
| **OpenCV** | - | Not available (custom implementation) |
| **SKImage** | - | Not available |
| **Photoshop** | Color Balance | Shadows/Midtones/Highlights: -100 to +100 per channel |
| **Affinity** | Colour Balance | Shadow/Midtone/Highlight: separate RGB sliders |
| **GIMP** | Color Balance | Shadows/Midtones/Highlights: -100 to +100 |

---

### Category 2: Levels & Curves

#### 9. Levels

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `levels(image, in_black, in_white, out_black, out_white, gamma)` | u8: 0-255, f32: 0.0-1.0, gamma: 0.1-10.0 |
| **OpenCV** | `normalize` or `LUT` | Various modes |
| **SKImage** | `exposure.rescale_intensity(image, in_range, out_range)` | Tuple ranges |
| **Photoshop** | Levels | Input/Output: 0-255, Gamma slider |
| **Affinity** | Levels | Input/Output levels per channel |
| **GIMP** | Levels | Input/Output: 0-255 |

#### 10. Curves

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `curves(image, points)` | `points`: list of (input, output) tuples 0.0-1.0 |
| **OpenCV** | `LUT` with interpolated curve | Build LUT from spline |
| **SKImage** | - | Not directly available |
| **Photoshop** | Curves | Bezier curve editor |
| **Affinity** | Curves | Spline curve editor |
| **GIMP** | Curves | Spline curve editor |

**Note:** ImageStag uses Catmull-Rom spline interpolation.

#### 11. Auto Levels

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `auto_levels(image, clip_percent)` | `clip_percent`: 0.0-50.0 |
| **OpenCV** | `normalize(src, dst, 0, 255, NORM_MINMAX)` | - |
| **SKImage** | `exposure.rescale_intensity(image)` | Auto-stretches to full range |
| **Photoshop** | Auto Tone | Automatic |
| **Affinity** | Auto Levels | Automatic |
| **GIMP** | Normalize / Stretch Contrast | Automatic |

---

### Category 3: Blur & Sharpen

#### 12. Gaussian Blur

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `gaussian_blur(image, sigma)` | `sigma`: blur radius in pixels |
| **OpenCV** | `GaussianBlur(src, ksize, sigmaX)` | `ksize`: kernel size (odd), `sigmaX`: sigma |
| **SKImage** | `filters.gaussian(image, sigma)` | `sigma`: standard deviation |
| **Photoshop** | Gaussian Blur | Radius: 0.1-1000 pixels |
| **Affinity** | Gaussian Blur | Radius: 0-1000 px |
| **GIMP** | Gaussian Blur | Size: 0.5-500 pixels |

#### 13. Box Blur

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `box_blur(image, radius)` | `radius`: integer pixels |
| **OpenCV** | `blur(src, ksize)` or `boxFilter` | `ksize`: (width, height) |
| **SKImage** | `filters.rank.mean(image, selem)` | `selem`: structuring element |
| **Photoshop** | Box Blur | Radius: 1-999 pixels |
| **Affinity** | Box Blur | Radius: 0-1000 px |
| **GIMP** | Pixelize | Block size |

#### 14. Motion Blur

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `motion_blur(image, angle, distance)` | `angle`: degrees, `distance`: pixels |
| **OpenCV** | `filter2D` with custom kernel | Build directional kernel |
| **SKImage** | - | Not directly available |
| **Photoshop** | Motion Blur | Angle: -90° to +90°, Distance: 1-2000 px |
| **Affinity** | Motion Blur | Angle: 0-360°, Radius: 0-1000 px |
| **GIMP** | Motion Blur | Type (Linear/Radial/Zoom), Angle, Length |

#### 15. Sharpen

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `sharpen(image, amount)` | `amount`: 0.0-10.0 (1.0 = standard) |
| **OpenCV** | `filter2D(src, -1, kernel)` | Sharpen kernel: `[0,-1,0; -1,5,-1; 0,-1,0]` |
| **SKImage** | `filters.unsharp_mask` | See below |
| **Photoshop** | Sharpen | No parameters (fixed) |
| **Affinity** | Sharpen | Factor: 0-500%, Radius: 0-1000 px |
| **GIMP** | Sharpen (Unsharp Mask) | Amount, Radius, Threshold |

#### 16. Unsharp Mask

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `unsharp_mask(image, amount, radius, threshold)` | `amount`: 0.0-10.0, `radius`: pixels, `threshold`: 0-255 (u8) |
| **OpenCV** | `addWeighted(src, 1+amount, blurred, -amount, 0)` | Manual implementation |
| **SKImage** | `filters.unsharp_mask(image, radius, amount)` | `radius`: sigma, `amount`: 0.0-1.0+ |
| **Photoshop** | Unsharp Mask | Amount: 1-500%, Radius: 0.1-1000 px, Threshold: 0-255 |
| **Affinity** | Unsharp Mask | Factor, Radius, Threshold |
| **GIMP** | Unsharp Mask | Amount, Radius, Threshold |

#### 17. High Pass

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `high_pass(image, radius)` | `radius`: blur radius in pixels |
| **OpenCV** | `src - GaussianBlur(src) + 128` | Manual implementation |
| **SKImage** | - | Not directly available |
| **Photoshop** | High Pass | Radius: 0.1-1000 pixels |
| **Affinity** | High Pass | Radius: 0-1000 px |
| **GIMP** | High Pass | Std. Dev, Contrast |

---

### Category 4: Edge Detection

#### 18. Sobel

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `sobel(image, direction)` | `direction`: "h", "v", or "both" |
| **OpenCV** | `Sobel(src, ddepth, dx, dy, ksize)` | `dx/dy`: derivative order, `ksize`: 1,3,5,7 |
| **SKImage** | `filters.sobel(image)` | No parameters (combined) |
| **Photoshop** | Find Edges (similar) | No direct Sobel |
| **Affinity** | - | Not available separately |
| **GIMP** | Sobel | Horizontal/Vertical/Both, Keep sign |

**Note:** OpenCV Sobel outputs signed values requiring abs() or scaling. SKImage returns float 0.0-1.0.

#### 19. Laplacian

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `laplacian(image, kernel_size)` | `kernel_size`: 3 or 5 |
| **OpenCV** | `Laplacian(src, ddepth, ksize)` | `ksize`: 1, 3, 5, 7 |
| **SKImage** | `filters.laplace(image, ksize)` | `ksize`: optional |
| **Photoshop** | - | Not directly available |
| **Affinity** | - | Not available |
| **GIMP** | Laplacian | - |

**Note:** Laplacian detects all edges regardless of direction. Output ranges differ significantly between u8 and f32.

#### 20. Find Edges

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `find_edges(image)` | No parameters |
| **OpenCV** | `Canny(src, threshold1, threshold2)` | Two thresholds |
| **SKImage** | `feature.canny(image, sigma)` | `sigma`: Gaussian smoothing |
| **Photoshop** | Find Edges | No parameters |
| **Affinity** | Edge Detection | Contrast, Radius |
| **GIMP** | Edge | Algorithm, Amount, Border behavior |

---

### Category 5: Stylize Effects

#### 21. Posterize

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `posterize(image, levels)` | `levels`: 2-256 |
| **OpenCV** | `LUT` with quantized values | Manual LUT |
| **SKImage** | - | Not directly available |
| **Photoshop** | Posterize | Levels: 2-255 |
| **Affinity** | Posterize | Levels |
| **GIMP** | Posterize | Levels: 2-256 |

#### 22. Solarize

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `solarize(image, threshold)` | u8: 0-255, f32: 0.0-1.0 |
| **OpenCV** | `LUT` with conditional invert | Manual implementation |
| **SKImage** | `exposure.solarize(image, threshold)` | `threshold`: float |
| **Photoshop** | Solarize | Threshold |
| **Affinity** | Solarize (in Invert) | - |
| **GIMP** | Value Invert (partial) | - |

#### 23. Threshold

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `threshold(image, threshold_val)` | u8: 0-255, f32: 0.0-1.0 |
| **OpenCV** | `threshold(src, thresh, maxval, type)` | Multiple threshold types |
| **SKImage** | `filters.threshold_otsu(image)` | Otsu's method (auto) |
| **Photoshop** | Threshold | Level: 1-255 |
| **Affinity** | Threshold | Threshold slider |
| **GIMP** | Threshold | Low/High threshold |

#### 24. Invert

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `invert(image)` | No parameters |
| **OpenCV** | `bitwise_not(src)` | - |
| **SKImage** | `util.invert(image)` | - |
| **Photoshop** | Invert | - |
| **Affinity** | Invert | - |
| **GIMP** | Invert | - |

#### 25. Emboss

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `emboss(image, angle, depth)` | `angle`: 0-360°, `depth`: 0.1-10.0 |
| **OpenCV** | `filter2D` with emboss kernel | Kernel based on angle |
| **SKImage** | - | Not directly available |
| **Photoshop** | Emboss | Angle, Height, Amount |
| **Affinity** | Emboss | Angle, Radius, Elevation |
| **GIMP** | Emboss | Azimuth, Elevation, Depth |

---

### Category 6: Noise

#### 26. Add Noise

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `add_noise(image, amount, gaussian, monochrome, seed)` | `amount`: 0.0-1.0, `gaussian`: bool, `monochrome`: bool, `seed`: int |
| **OpenCV** | `randn()` or `randu()` + add | Manual implementation |
| **SKImage** | `util.random_noise(image, mode, var, seed)` | `mode`: 'gaussian', 'salt', 'pepper', etc. |
| **Photoshop** | Add Noise | Amount: 0-400%, Gaussian/Uniform, Monochromatic |
| **Affinity** | Add Noise | Intensity, Gaussian |
| **GIMP** | HSV Noise | Holdness, Hue, Saturation, Value |

#### 27. Median Filter

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `median(image, radius)` | `radius`: 1+ (1=3x3, 2=5x5, etc.) |
| **OpenCV** | `medianBlur(src, ksize)` | `ksize`: odd integer |
| **SKImage** | `filters.median(image, selem)` | `selem`: structuring element |
| **Photoshop** | Median | Radius: 1-100 pixels |
| **Affinity** | Median | Radius |
| **GIMP** | Noise Reduction | Strength |

#### 28. Denoise

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `denoise(image, strength)` | `strength`: 0.0-1.0 |
| **OpenCV** | `fastNlMeansDenoising(src, h)` | `h`: filter strength |
| **SKImage** | `restoration.denoise_nl_means(image, h)` | `h`: filter strength, `patch_size`, `patch_distance` |
| **Photoshop** | Reduce Noise | Strength, Preserve Details, Reduce Color Noise |
| **Affinity** | Denoise | Luminance, Detail, Color |
| **GIMP** | Noise Reduction | Strength |

---

### Category 7: Morphology

#### 29. Dilate

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `dilate(image, radius)` | `radius`: float |
| **OpenCV** | `dilate(src, kernel, iterations)` | `kernel`: structuring element |
| **SKImage** | `morphology.dilation(image, selem)` | `selem`: structuring element |
| **Photoshop** | Maximum | Radius: 1-500 |
| **Affinity** | Dilate | Radius |
| **GIMP** | Dilate | - |

#### 30. Erode

| Library | Function | Parameters |
|---------|----------|------------|
| **ImageStag** | `erode(image, radius)` | `radius`: float |
| **OpenCV** | `erode(src, kernel, iterations)` | `kernel`: structuring element |
| **SKImage** | `morphology.erosion(image, selem)` | `selem`: structuring element |
| **Photoshop** | Minimum | Radius: 1-500 |
| **Affinity** | Erode | Radius |
| **GIMP** | Erode | - |

---

## Bit Depth Behavior Differences

Several filters produce different outputs between u8 (0-255) and f32 (0.0-1.0) modes:

### Filters with Identical Behavior
- Brightness, Contrast, Saturation, Gamma, Invert
- Posterize, Solarize, Threshold
- Gaussian Blur, Box Blur, Motion Blur
- Sharpen, Unsharp Mask, High Pass
- Median, Denoise
- Dilate, Erode

### Filters with Different Output Ranges

| Filter | u8 Output Range | f32 Output Range | Notes |
|--------|-----------------|------------------|-------|
| **Sobel** | 0-255 (clipped) | 0.0-1.0 (normalized) | f32 divides kernel by 4 for normalization |
| **Laplacian** | 0-255 (clipped) | 0.0-1.0 (normalized) | f32 divides kernel by center value |
| **Find Edges** | 0-255 | 0.0-1.0 | Same as Sobel |

**Reason:** Edge detection kernels produce values that can exceed the 0-255 range. The u8 version clips to this range, while f32 normalizes the kernel weights to keep output in 0.0-1.0.

---

## Reference Library Mappings

### OpenCV (cv2)

```python
import cv2
import numpy as np

# Brightness (add offset)
cv2.convertScaleAbs(image, alpha=1.0, beta=brightness * 255)

# Contrast (multiply)
cv2.convertScaleAbs(image, alpha=1.0 + contrast, beta=0)

# Gaussian Blur
cv2.GaussianBlur(image, (0, 0), sigma)

# Sobel
sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
sobel = np.sqrt(sobel_x**2 + sobel_y**2)

# Laplacian
laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)

# Median
cv2.medianBlur(image, ksize)

# Dilate/Erode
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
cv2.dilate(image, kernel)
cv2.erode(image, kernel)
```

### scikit-image (skimage)

```python
from skimage import filters, exposure, morphology, restoration, util, color

# Gaussian Blur
filters.gaussian(image, sigma=sigma)

# Sobel
filters.sobel(gray_image)

# Laplacian
filters.laplace(gray_image)

# Gamma
exposure.adjust_gamma(image, gamma)

# Auto Levels
exposure.rescale_intensity(image)

# Solarize
exposure.solarize(image, threshold)

# Median
filters.median(image, morphology.disk(radius))

# Denoise
restoration.denoise_nl_means(image, h=strength)

# Dilate/Erode
morphology.dilation(image, morphology.disk(radius))
morphology.erosion(image, morphology.disk(radius))

# Invert
util.invert(image)

# Noise
util.random_noise(image, mode='gaussian', var=variance)
```

---

## Implementation Notes

1. **ImageStag uses Rust backend** - All filters are implemented in Rust for performance, with Python and JavaScript bindings.

2. **Cross-platform parity** - Python and JavaScript/WASM implementations produce identical outputs.

3. **Channel preservation** - Filters preserve channel count (1, 3, or 4 channels). Alpha channel is never modified.

4. **Value clamping** - u8 outputs are clamped to 0-255, f32 outputs to 0.0-1.0.

5. **No fallbacks** - Rust backend is mandatory; there are no Python fallback implementations.
