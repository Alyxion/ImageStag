# ImageStag Filter Overview

Comprehensive comparison of image filters across ImageStag, OpenCV, scikit-image, Adobe Photoshop, Affinity Photo, and GIMP.

**Legend:**
- **Bold** = Implemented in ImageStag
- *Italic* = Planned
- `-` = Not available

---

## Category 1: Basic Color Adjustments

### Brightness

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `brightness` | `amount` | -1.0 to 1.0 | 0.0 |
| OpenCV | `convertScaleAbs` | `beta` | -255 to 255 | 0 |
| SKImage | `adjust_gamma` | `gamma` | 0.01 to 10.0 | 1.0 |
| Photoshop | Brightness/Contrast | Brightness | -150 to 150 | 0 |
| Affinity | Brightness/Contrast | Brightness | -100% to 100% | 0% |
| GIMP | Brightness-Contrast | Brightness | -127 to 127 | 0 |

**Parameter equivalence:** ImageStag 1.0 = Photoshop 150 = GIMP 127 = full white

---

### Contrast

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `contrast` | `amount` | -1.0 to 1.0 | 0.0 |
| OpenCV | `convertScaleAbs` | `alpha` | 0.0 to 3.0 | 1.0 |
| SKImage | `rescale_intensity` | `in_range` | tuple | auto |
| Photoshop | Brightness/Contrast | Contrast | -50 to 100 | 0 |
| Affinity | Brightness/Contrast | Contrast | -100% to 100% | 0% |
| GIMP | Brightness-Contrast | Contrast | -127 to 127 | 0 |

**Parameter equivalence:** ImageStag 0.0 = no change; -1.0 = flat gray; 1.0 = maximum contrast

---

### Saturation

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `saturation` | `amount` | -1.0 to 1.0 | 0.0 |
| OpenCV | HSV multiply S | `scale` | 0.0 to 2.0+ | 1.0 |
| SKImage | HSV adjust | `scale` | 0.0 to 2.0+ | 1.0 |
| Photoshop | Hue/Saturation | Saturation | -100 to 100 | 0 |
| Affinity | HSL | Saturation Shift | -100% to 100% | 0% |
| GIMP | Hue-Saturation | Saturation | -100 to 100 | 0 |

**Parameter equivalence:** ImageStag -1.0 = Photoshop -100 = grayscale; ImageStag 1.0 = Photoshop 100

---

### Hue Shift

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `hue_shift` | `degrees` | -180 to 180 | 0.0 |
| OpenCV | HSV add H | `offset` | 0 to 180 | 0 |
| SKImage | HSV shift | `offset` | 0.0 to 1.0 | 0.0 |
| Photoshop | Hue/Saturation | Hue | -180 to 180 | 0 |
| Affinity | HSL | Hue Shift | -180° to 180° | 0° |
| GIMP | Hue-Saturation | Hue | -180 to 180 | 0 |

**Parameter equivalence:** ImageStag ±180 = Photoshop ±180 = GIMP ±180 = opposite hue. Positive = clockwise, negative = counter-clockwise.

---

### Vibrance

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `vibrance` | `amount` | -1.0 to 1.0 | 0.0 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Vibrance | Vibrance | -100 to 100 | 0 |
| Affinity | Vibrance | Vibrance | -100% to 100% | 0% |
| GIMP | - | - | - | - |

**Note:** Vibrance boosts less-saturated colors more than already-saturated ones, preserving skin tones.

---

### Exposure

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `exposure` | `exposure_val` | -5.0 to 5.0 | 0.0 |
| | | `offset` | -0.5 to 0.5 | 0.0 |
| | | `gamma_val` | 0.1 to 10.0 | 1.0 |
| OpenCV | multiply by 2^exp | `exposure` | -5.0 to 5.0 | 0.0 |
| SKImage | `adjust_gamma` | `gain` | 0.0 to 10.0 | 1.0 |
| Photoshop | Exposure | Exposure | -20 to 20 | 0 |
| | | Offset | -0.5 to 0.5 | 0 |
| | | Gamma | 0.01 to 9.99 | 1.0 |
| Affinity | Exposure | Exposure | -5 to 5 EV | 0 |
| GIMP | Exposure | Exposure | -10 to 10 | 0 |

**Parameter equivalence:** 1 EV = doubling of light; ImageStag matches Photoshop formula: (pixel × 2^exposure + offset)^(1/gamma)

---

### Gamma

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `gamma` | `gamma_value` | 0.1 to 10.0 | 1.0 |
| OpenCV | LUT | `gamma` | 0.1 to 10.0 | 1.0 |
| SKImage | `adjust_gamma` | `gamma` | 0.1 to 10.0 | 1.0 |
| Photoshop | Levels | Gamma (middle) | 0.1 to 9.99 | 1.0 |
| Affinity | Levels | Gamma | 0.1 to 10.0 | 1.0 |
| GIMP | Levels | Gamma | 0.1 to 10.0 | 1.0 |

**Parameter equivalence:** All use identical formula: output = input^(1/gamma). Values <1 brighten, >1 darken.

---

### Color Balance

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `color_balance` | `shadows` | (-1,-1,-1) to (1,1,1) | (0,0,0) |
| | | `midtones` | (-1,-1,-1) to (1,1,1) | (0,0,0) |
| | | `highlights` | (-1,-1,-1) to (1,1,1) | (0,0,0) |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Color Balance | Shadows/Mid/High | -100 to 100 per axis | 0 |
| Affinity | Colour Balance | Shadow/Mid/High | -100% to 100% | 0% |
| GIMP | Color Balance | Shadows/Mid/High | -100 to 100 | 0 |

**Parameter equivalence:** ImageStag 1.0 = Photoshop 100 = GIMP 100. Each tuple is (Cyan-Red, Magenta-Green, Yellow-Blue).

---

### Invert

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `invert` | - | - | - |
| OpenCV | `bitwise_not` | - | - | - |
| SKImage | `util.invert` | - | - | - |
| Photoshop | Invert | - | - | - |
| Affinity | Invert | - | - | - |
| GIMP | Invert | - | - | - |

**Note:** Alpha channel is preserved (not inverted).

---

## Category 2: Levels & Curves

### Levels

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `levels` | `in_black` | 0-255 (u8) / 0.0-1.0 (f32) | 0 |
| | | `in_white` | 0-255 / 0.0-1.0 | 255 / 1.0 |
| | | `out_black` | 0-255 / 0.0-1.0 | 0 |
| | | `out_white` | 0-255 / 0.0-1.0 | 255 / 1.0 |
| | | `gamma` | 0.1 to 10.0 | 1.0 |
| OpenCV | `normalize` | `alpha`, `beta` | 0-255 | 0, 255 |
| SKImage | `rescale_intensity` | `in_range`, `out_range` | tuples | auto |
| Photoshop | Levels | Input/Output | 0-255 | 0, 255 |
| Affinity | Levels | Black/White/Gamma | 0-1.0 | 0, 1.0 |
| GIMP | Levels | Input/Output | 0-255 | 0, 255 |

---

### Curves

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `curves` | `points` | list of (x,y) 0.0-1.0 | [(0,0), (1,1)] |
| OpenCV | LUT | `lut` | 256-element array | linear |
| SKImage | - | - | - | - |
| Photoshop | Curves | control points | 0-255 | diagonal |
| Affinity | Curves | control points | 0-1.0 | diagonal |
| GIMP | Curves | control points | 0-255 | diagonal |

**Note:** ImageStag uses Catmull-Rom spline interpolation through control points.

---

### Auto Levels

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `auto_levels` | `clip_percent` | 0.0 to 50.0 | 0.0 |
| OpenCV | `normalize(NORM_MINMAX)` | - | - | - |
| SKImage | `rescale_intensity` | - | - | - |
| Photoshop | Auto Tone | - | - | - |
| Affinity | Auto Levels | - | - | - |
| GIMP | Normalize | - | - | - |

**Parameter:** `clip_percent` ignores outlier pixels at histogram ends for more robust stretching.

---

### Histogram Equalization

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *histogram_eq* | - | - | - |
| OpenCV | `equalizeHist` | - | - | - |
| SKImage | `equalize_hist` | - | - | - |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | Equalize | - | - | - |

---

### CLAHE (Adaptive Histogram)

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *clahe* | `clip_limit` | 1.0 to 100.0 | 40.0 |
| | | `tile_size` | 2 to 64 | 8 |
| OpenCV | `createCLAHE` | `clipLimit` | 1.0 to 100.0 | 40.0 |
| | | `tileGridSize` | (w, h) | (8, 8) |
| SKImage | `equalize_adapthist` | `clip_limit` | 0.0 to 1.0 | 0.01 |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | - | - | - | - |

---

## Category 3: Advanced Color

### Black & White / Grayscale

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `grayscale` | - | - | BT.709 |
| **ImageStag** | `grayscale_weighted` | `r_weight` | any (normalized) | 0.2126 |
| | | `g_weight` | any (normalized) | 0.7152 |
| | | `b_weight` | any (normalized) | 0.0722 |
| OpenCV | `cvtColor(BGR2GRAY)` | - | - | BT.601 |
| SKImage | `rgb2gray` | - | - | BT.601 |
| Photoshop | Black & White | R/Y/G/C/B/M sliders | -200% to 300% | varies |
| Affinity | Black & White | channel sliders | -100% to 200% | varies |
| GIMP | Desaturate | Mode | Luminosity/Average/etc | Luminosity |

**Note:** `grayscale` uses fixed ITU-R BT.709 (Y = 0.2126R + 0.7152G + 0.0722B).
`grayscale_weighted` allows custom RGB weights like Photoshop's Black & White filter.
Weights are automatically normalized (sum to 1.0).

**Example weights:**
- BT.709 (default): r=0.2126, g=0.7152, b=0.0722
- Simple average: r=1, g=1, b=1 (normalized to 0.333 each)
- Red filter effect: r=1.0, g=0, b=0

---

### Channel Mixer

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *channel_mixer* | `red_out` | (-2,-2,-2) to (2,2,2) | (1,0,0) |
| | | `green_out` | (-2,-2,-2) to (2,2,2) | (0,1,0) |
| | | `blue_out` | (-2,-2,-2) to (2,2,2) | (0,0,1) |
| OpenCV | matrix multiply | `matrix` | 3x3 | identity |
| SKImage | matrix multiply | `matrix` | 3x3 | identity |
| Photoshop | Channel Mixer | R/G/B per output | -200% to 200% | 100/0/0 |
| Affinity | Channel Mixer | per channel | -100% to 200% | identity |
| GIMP | Channel Mixer | per channel | -200% to 200% | identity |

---

### Selective Color

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *selective_color* | `color_range` | reds/yellows/greens/cyans/blues/magentas/whites/neutrals/blacks | - |
| | | `cyan` | -100 to 100 | 0 |
| | | `magenta` | -100 to 100 | 0 |
| | | `yellow` | -100 to 100 | 0 |
| | | `black` | -100 to 100 | 0 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Selective Color | C/M/Y/K per range | -100% to 100% | 0% |
| Affinity | Selective Colour | per color range | -100% to 100% | 0% |
| GIMP | Hue-Saturation (per range) | - | - | - |

---

### Photo Filter / Color Temperature

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *photo_filter* | `color` | RGB tuple | (255,178,102) |
| | | `density` | 0 to 100 | 25 |
| | | `preserve_luminosity` | bool | true |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Photo Filter | Color, Density | 0-100% | 25% |
| Affinity | White Balance | Temperature, Tint | -100 to 100 | 0 |
| GIMP | Color Temperature | Temperature | 1000K to 12000K | 6500K |

---

### Gradient Map

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *gradient_map* | `stops` | list of (pos, color) | [(0,black),(1,white)] |
| OpenCV | `applyColorMap` | `colormap` | predefined | - |
| SKImage | - | - | - | - |
| Photoshop | Gradient Map | gradient | custom | black-white |
| Affinity | Gradient Map | gradient | custom | black-white |
| GIMP | Gradient Map | gradient | custom | FG-BG |

---

### Color Lookup (LUT)

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *color_lut* | `lut_file` | .cube/.3dl path | - |
| | | `strength` | 0.0 to 1.0 | 1.0 |
| OpenCV | LUT | `lut` | 256 or 3D array | - |
| SKImage | - | - | - | - |
| Photoshop | Color Lookup | 3DLUT File | .cube/.3dl/.look | - |
| Affinity | LUT | LUT file | .cube | - |
| GIMP | - | - | - | - |

---

### Split Toning

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *split_toning* | `shadow_hue` | 0 to 360 | 0 |
| | | `shadow_sat` | 0 to 100 | 0 |
| | | `highlight_hue` | 0 to 360 | 0 |
| | | `highlight_sat` | 0 to 100 | 0 |
| | | `balance` | -100 to 100 | 0 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Split Toning | Hue/Sat/Balance | as above | 0 |
| Affinity | Split Toning | Shadow/Highlight | as above | 0 |
| GIMP | - | - | - | - |

---

### Shadows/Highlights

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *shadows_highlights* | `shadows` | -100 to 100 | 0 |
| | | `highlights` | -100 to 100 | 0 |
| | | `midtone_contrast` | -100 to 100 | 0 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Shadows/Highlights | Amount/Tone/Radius | 0-100%, 0-100%, 0-2500px | varies |
| Affinity | Shadows/Highlights | Shadows/Highlights | -100% to 100% | 0% |
| GIMP | Shadows-Highlights | Shadows/Highlights | -100 to 100 | 0 |

---

### HDR Toning

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *hdr_toning* | `strength` | 0.0 to 1.0 | 0.5 |
| | | `gamma` | 0.1 to 10.0 | 1.0 |
| OpenCV | `createTonemapDrago` | `gamma` | 0.1 to 10.0 | 1.0 |
| | | `saturation` | 0.0 to 2.0 | 1.0 |
| SKImage | - | - | - | - |
| Photoshop | HDR Toning | Edge Glow/Tone/Detail | various | varies |
| Affinity | HDR Merge | Tone Map | various | varies |
| GIMP | - | - | - | - |

---

### Colorize

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *colorize* | `hue` | 0 to 360 | 0 |
| | | `saturation` | 0 to 100 | 50 |
| | | `lightness` | -100 to 100 | 0 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Colorize (in Hue/Sat) | H/S/L | as above | varies |
| Affinity | Recolour | Hue/Saturation | as above | varies |
| GIMP | Colorize | H/S/L | 0-360, 0-100, -100-100 | varies |

---

### Sepia

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *sepia* | `intensity` | 0.0 to 1.0 | 1.0 |
| OpenCV | color matrix | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Photo Filter (Sepia) | Density | 0-100% | 25% |
| Affinity | Sepia | Intensity | 0-100% | 100% |
| GIMP | Sepia | - | - | - |

---

## Category 4: Blur & Smoothing

### Gaussian Blur

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `gaussian_blur` | `sigma` | 0.1 to 250.0 | 1.0 |
| OpenCV | `GaussianBlur` | `sigmaX` | 0.1 to 250.0 | 0 (auto) |
| | | `ksize` | odd int or (0,0) | (0,0) |
| SKImage | `gaussian` | `sigma` | 0.1 to 250.0 | 1.0 |
| Photoshop | Gaussian Blur | Radius | 0.1 to 1000 px | 1.0 |
| Affinity | Gaussian Blur | Radius | 0 to 1000 px | 0 |
| GIMP | Gaussian Blur | Size | 0.5 to 500 px | 1.5 |

**Parameter equivalence:** ImageStag sigma ≈ Photoshop radius (sigma = radius for Gaussian)

---

### Box Blur

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `box_blur` | `radius` | 1 to 250 | 1 |
| OpenCV | `blur` | `ksize` | (w, h) | (3, 3) |
| SKImage | `rank.mean` | `footprint` | array | disk(1) |
| Photoshop | Box Blur | Radius | 1 to 999 px | 1 |
| Affinity | Box Blur | Radius | 0 to 1000 px | 0 |
| GIMP | Pixelize | Block size | 1 to 2048 | 10 |

**Parameter equivalence:** ImageStag radius 1 = 3x3 kernel; radius 2 = 5x5 kernel

---

### Motion Blur

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `motion_blur` | `angle` | 0 to 360 | 0.0 |
| | | `distance` | 1 to 1000 | 10.0 |
| OpenCV | `filter2D` | custom kernel | - | - |
| SKImage | - | - | - | - |
| Photoshop | Motion Blur | Angle | -90° to 90° | 0° |
| | | Distance | 1 to 2000 px | 10 |
| Affinity | Motion Blur | Rotation | 0° to 360° | 0° |
| | | Radius | 0 to 1000 px | 0 |
| GIMP | Motion Blur | Angle | 0 to 360 | 0 |
| | | Length | 1 to 1024 | 5 |

---

### Radial Blur (Spin)

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *radial_blur_spin* | `amount` | 0 to 360 | 10 |
| | | `center` | (x, y) normalized | (0.5, 0.5) |
| OpenCV | `warpPolar` + blur | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Radial Blur (Spin) | Amount | 1 to 100 | 10 |
| Affinity | Radial Blur | Angle | 0° to 360° | 0° |
| GIMP | Motion Blur (Radial) | Angle | 0 to 360 | 5 |

---

### Radial Blur (Zoom)

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *radial_blur_zoom* | `amount` | 0 to 100 | 10 |
| | | `center` | (x, y) normalized | (0.5, 0.5) |
| OpenCV | `warpPolar` + blur | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Radial Blur (Zoom) | Amount | 1 to 100 | 10 |
| Affinity | Zoom Blur | Radius | 0 to 1000 px | 0 |
| GIMP | Zoom Motion Blur | Factor | 0.0 to 1.0 | 0.1 |

---

### Bilateral Filter / Surface Blur

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *bilateral* | `sigma_color` | 0 to 200 | 75 |
| | | `sigma_space` | 0 to 200 | 75 |
| OpenCV | `bilateralFilter` | `sigmaColor` | 0 to 200 | 75 |
| | | `sigmaSpace` | 0 to 200 | 75 |
| | | `d` | -1 to 15 | 9 |
| SKImage | - | - | - | - |
| Photoshop | Surface Blur | Radius | 1 to 100 px | 5 |
| | | Threshold | 2 to 255 | 15 |
| Affinity | Bilateral Blur | Radius | 0 to 100 px | 0 |
| | | Tolerance | 0% to 100% | 20% |
| GIMP | Selective Gaussian | Max delta | 0 to 255 | 50 |

---

### Lens Blur / Depth of Field

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *lens_blur* | `radius` | 0 to 100 | 15 |
| | | `blade_count` | 3 to 12 | 6 |
| | | `rotation` | 0 to 360 | 0 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Lens Blur | Radius | 0 to 100 | 15 |
| | | Blade Curvature | 0 to 100 | 0 |
| | | Rotation | 0 to 360 | 0 |
| Affinity | Depth of Field | Radius | 0 to 1000 px | 0 |
| GIMP | Focus Blur | Blur radius | 0 to 100 | 25 |

---

### Tilt-Shift

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *tilt_shift* | `blur_amount` | 0 to 100 | 15 |
| | | `focus_position` | 0.0 to 1.0 | 0.5 |
| | | `focus_width` | 0.0 to 1.0 | 0.2 |
| | | `angle` | 0 to 360 | 0 |
| OpenCV | gradient mask + blur | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Tilt-Shift | Blur | 0 to 500 px | 15 |
| Affinity | Miniature (Tilt-Shift) | Blur Radius | 0 to 1000 px | 0 |
| GIMP | - | - | - | - |

---

## Category 5: Sharpen & Detail

### Sharpen

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `sharpen` | `amount` | 0.0 to 5.0 | 1.0 |
| OpenCV | `filter2D` | kernel | custom | sharpen kernel |
| SKImage | `unsharp_mask` | `amount` | 0.0 to 2.0 | 1.0 |
| Photoshop | Sharpen | - | - | fixed |
| Affinity | Sharpen | Factor | 0 to 500% | 100% |
| GIMP | Sharpen | Sharpness | 0.1 to 10 | 0.5 |

**Parameter equivalence:** ImageStag 1.0 = Affinity 100% = standard sharpening. Max 5.0 = 500%.

---

### Unsharp Mask

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `unsharp_mask` | `amount` | 0.0 to 5.0 | 1.0 |
| | | `radius` | 0.1 to 500 | 1.0 |
| | | `threshold` | 0 to 255 (u8) | 0 |
| OpenCV | subtract blur | - | manual | - |
| SKImage | `unsharp_mask` | `radius` | 0.1 to 100 | 1.0 |
| | | `amount` | 0.0 to 2.0 | 1.0 |
| Photoshop | Unsharp Mask | Amount | 1 to 500% | 100% |
| | | Radius | 0.1 to 1000 px | 1.0 |
| | | Threshold | 0 to 255 | 0 |
| Affinity | Unsharp Mask | Factor | 0 to 500% | 100% |
| | | Radius | 0 to 1000 px | 1.0 |
| GIMP | Unsharp Mask | Amount | 0.0 to 10.0 | 0.5 |
| | | Radius | 0.1 to 500 | 3.0 |
| | | Threshold | 0 to 255 | 0 |

**Parameter equivalence:** ImageStag 1.0 = Photoshop 100% = Affinity 100%. Radius matches GIMP max.

---

### High Pass

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `high_pass` | `radius` | 0.1 to 500 | 10.0 |
| OpenCV | subtract blur from original | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | High Pass | Radius | 0.1 to 1000 px | 10 |
| Affinity | High Pass | Radius | 0 to 1000 px | 3 |
| GIMP | High Pass | Std Dev | 0.0 to 500 | 4.0 |

**Parameter equivalence:** ImageStag default 10.0 matches Photoshop default. Max 500 matches GIMP.

**Note:** Output is centered at 128 (u8) or 0.5 (f32) - gray means no detail.

---

### Clarity

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *clarity* | `amount` | -100 to 100 | 0 |
| OpenCV | local contrast | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Clarity | Clarity | -100 to 100 | 0 |
| Affinity | Clarity | Clarity | -100% to 100% | 0% |
| GIMP | - | - | - | - |

**Note:** Clarity enhances local/midtone contrast without affecting global contrast.

---

### Dehaze

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *dehaze* | `amount` | -100 to 100 | 0 |
| OpenCV | dark channel prior | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Dehaze | Amount | -100 to 100 | 0 |
| Affinity | Dehaze | - | - | - |
| GIMP | - | - | - | - |

---

## Category 6: Edge Detection

### Sobel

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `sobel` | `direction` | "h", "v", "both" | "both" |
| OpenCV | `Sobel` | `dx`, `dy` | 0 or 1 | varies |
| | | `ksize` | 1, 3, 5, 7 | 3 |
| SKImage | `sobel` | - | combined only | - |
| | `sobel_h`, `sobel_v` | - | directional | - |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | Sobel | Horizontal/Vertical/Both | bool | Both |

**Note:** u8 clips to 0-255; f32 normalizes to 0.0-1.0 (different output ranges).

---

### Laplacian

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `laplacian` | `kernel_size` | 3 or 5 | 3 |
| OpenCV | `Laplacian` | `ksize` | 1, 3, 5, 7 | 1 |
| SKImage | `laplace` | `ksize` | 3 or larger | 3 |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | Laplacian | - | - | - |

---

### Find Edges

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `find_edges` | - | - | - |
| OpenCV | `Canny` | `threshold1/2` | 0-255 | varies |
| SKImage | `canny` | `sigma` | 0.1 to 10 | 1.0 |
| Photoshop | Find Edges | - | - | - |
| Affinity | Edge Detection | - | - | - |
| GIMP | Edge | Amount | 1.0 to 10.0 | 2.0 |

---

### Canny

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *canny* | `low_threshold` | 0 to 255 | 50 |
| | | `high_threshold` | 0 to 255 | 150 |
| | | `sigma` | 0.1 to 5.0 | 1.0 |
| OpenCV | `Canny` | `threshold1` | 0 to 255 | 100 |
| | | `threshold2` | 0 to 255 | 200 |
| SKImage | `canny` | `sigma` | 0.1 to 10 | 1.0 |
| | | `low_threshold` | 0.0 to 1.0 | None |
| | | `high_threshold` | 0.0 to 1.0 | None |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | Canny | - | - | - |

---

### Difference of Gaussians

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *dog* | `sigma1` | 0.1 to 100 | 1.0 |
| | | `sigma2` | 0.1 to 100 | 2.0 |
| OpenCV | subtract two blurs | - | - | - |
| SKImage | `difference_of_gaussians` | `low_sigma` | 0.1 to 100 | 1.0 |
| | | `high_sigma` | 0.1 to 100 | varies |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | Difference of Gaussians | Radius 1/2 | 0 to 500 | varies |

---

## Category 7: Stylize Effects

### Posterize

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `posterize` | `levels` | 2 to 256 | 4 |
| OpenCV | LUT quantize | `levels` | 2 to 256 | 4 |
| SKImage | - | - | - | - |
| Photoshop | Posterize | Levels | 2 to 255 | 4 |
| Affinity | Posterize | Levels | 2 to 256 | 4 |
| GIMP | Posterize | Levels | 2 to 256 | 3 |

---

### Solarize

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `solarize` | `threshold` | 0-255 (u8) / 0.0-1.0 (f32) | 128 / 0.5 |
| OpenCV | LUT conditional | `threshold` | 0-255 | 128 |
| SKImage | `solarize` | `threshold` | 0.0 to 1.0 | 0.5 |
| Photoshop | Solarize | - | fixed at 128 | - |
| Affinity | Solarize | - | - | - |
| GIMP | - | - | - | - |

**Note:** Pixels above threshold are inverted.

---

### Threshold

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `threshold` | `threshold_val` | 0-255 (u8) / 0.0-1.0 (f32) | 128 / 0.5 |
| OpenCV | `threshold` | `thresh` | 0-255 | 128 |
| | | `type` | BINARY/BINARY_INV/etc | BINARY |
| SKImage | `threshold_otsu` | - | auto | - |
| Photoshop | Threshold | Level | 1 to 255 | 128 |
| Affinity | Threshold | Threshold | 0% to 100% | 50% |
| GIMP | Threshold | Range | 0-255 to 0-255 | 127-255 |

---

### Emboss

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `emboss` | `angle` | 0 to 360 | 135.0 |
| | | `depth` | 0.1 to 10.0 | 1.0 |
| OpenCV | `filter2D` | custom kernel | - | - |
| SKImage | - | - | - | - |
| Photoshop | Emboss | Angle | -360° to 360° | 135° |
| | | Height | 1 to 10 | 3 |
| | | Amount | 1 to 500% | 100% |
| Affinity | Emboss | Radius | 0 to 1000 px | 1 |
| | | Elevation | 0° to 90° | 30° |
| | | Azimuth | 0° to 360° | 135° |
| GIMP | Emboss | Azimuth | 0 to 360 | 315 |
| | | Elevation | 0 to 180 | 45 |
| | | Depth | 1 to 65 | 2 |

---

### Oil Paint

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *oil_paint* | `radius` | 1 to 10 | 4 |
| | | `levels` | 2 to 256 | 30 |
| OpenCV | `xphoto.oilPainting` | `size` | 1 to 10 | 3 |
| | | `dynRatio` | 1 to 5 | 1 |
| SKImage | - | - | - | - |
| Photoshop | Oil Paint | Stylization | 0.1 to 10 | 2.5 |
| | | Cleanliness | 0 to 10 | 8 |
| Affinity | - | - | - | - |
| GIMP | Oilify | Mask size | 3 to 50 | 8 |

---

### Halftone

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *halftone* | `dot_size` | 1 to 50 | 8 |
| | | `angle` | 0 to 180 | 45 |
| | | `shape` | circle/diamond/line | circle |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Color Halftone | Max Radius | 4 to 127 | 8 |
| | | Angles | 0 to 360 per channel | varies |
| Affinity | Halftone | Cell Size | 1 to 256 | 8 |
| GIMP | Newsprint | Cell Size | 1 to 100 | 5 |

---

### Mosaic / Pixelate

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *mosaic* | `cell_size` | 2 to 200 | 10 |
| OpenCV | resize down + up | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Mosaic | Cell Size | 2 to 200 | 10 |
| Affinity | Pixelate | Block Size | 1 to 256 | 10 |
| GIMP | Pixelize | Block width/height | 1 to 2048 | 10 |

---

### Crystallize

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *crystallize* | `cell_size` | 3 to 300 | 10 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Crystallize | Cell Size | 3 to 300 | 10 |
| Affinity | - | - | - | - |
| GIMP | - | - | - | - |

---

### Pointillize

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *pointillize* | `cell_size` | 3 to 300 | 6 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Pointillize | Cell Size | 3 to 300 | 6 |
| Affinity | - | - | - | - |
| GIMP | - | - | - | - |

---

### Neon Glow / Glowing Edges

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *glowing_edges* | `edge_width` | 1 to 14 | 2 |
| | | `brightness` | 0 to 20 | 6 |
| | | `smoothness` | 1 to 15 | 5 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Glowing Edges | Edge Width | 1 to 14 | 2 |
| | | Edge Brightness | 0 to 20 | 6 |
| | | Smoothness | 1 to 15 | 5 |
| Affinity | - | - | - | - |
| GIMP | Neon | - | - | - |

---

## Category 8: Noise

### Add Noise

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `add_noise` | `amount` | 0.0 to 1.0 | 0.1 |
| | | `gaussian` | bool | true |
| | | `monochrome` | bool | false |
| | | `seed` | int | 0 |
| OpenCV | `randn` / `randu` | `stddev` | varies | - |
| SKImage | `random_noise` | `var` | 0.0 to 1.0 | 0.01 |
| | | `mode` | gaussian/s&p/speckle | gaussian |
| Photoshop | Add Noise | Amount | 0 to 400% | 10% |
| | | Distribution | Gaussian/Uniform | Gaussian |
| | | Monochromatic | bool | false |
| Affinity | Add Noise | Intensity | 0 to 100% | 10% |
| | | Gaussian | bool | true |
| GIMP | HSV Noise | various | various | varies |

**Note:** The `seed` parameter enables deterministic noise for cross-platform parity testing.
Professional tools don't expose this parameter - they always use random noise.
Use seed=0 for production (random), or a fixed seed for reproducible results.

---

### Median

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `median` | `radius` | 1 to 100 | 1 |
| OpenCV | `medianBlur` | `ksize` | 3, 5, 7, ... (odd) | 5 |
| SKImage | `median` | `footprint` | disk/square | disk(1) |
| Photoshop | Median | Radius | 1 to 100 px | 1 |
| Affinity | Median | Radius | 0 to 100 px | 1 |
| GIMP | Noise Reduction | Strength | 0 to 1 | varies |

---

### Denoise

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `denoise` | `strength` | 0.0 to 1.0 | 0.5 |
| OpenCV | `fastNlMeansDenoising` | `h` | 0 to 30 | 10 |
| | `fastNlMeansDenoisingColored` | `hForColorComponents` | 0 to 30 | 10 |
| SKImage | `denoise_nl_means` | `h` | 0.0 to 1.0 | 0.1 |
| | | `patch_size` | 3 to 11 | 7 |
| | | `patch_distance` | 3 to 21 | 11 |
| Photoshop | Reduce Noise | Strength | 0 to 10 | 6 |
| | | Preserve Details | 0 to 100% | 60% |
| Affinity | Denoise | Luminance | 0 to 100% | 50% |
| GIMP | Noise Reduction | Strength | 0 to 1 | varies |

---

### Film Grain

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *film_grain* | `amount` | 0 to 100 | 25 |
| | | `size` | 0.5 to 3.0 | 1.0 |
| | | `roughness` | 0 to 100 | 50 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Camera Raw (Grain) | Amount | 0 to 100 | 0 |
| | | Size | 1 to 100 | 25 |
| | | Roughness | 0 to 100 | 50 |
| Affinity | Add Noise | Intensity | 0 to 100% | - |
| GIMP | Film Grain | - | - | - |

---

### Dust & Scratches

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *dust_scratches* | `radius` | 1 to 100 | 1 |
| | | `threshold` | 0 to 255 | 0 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Dust & Scratches | Radius | 1 to 100 px | 1 |
| | | Threshold | 0 to 255 | 0 |
| Affinity | - | - | - | - |
| GIMP | Despeckle | Radius | 1 to 20 | 3 |

---

## Category 9: Morphology

### Dilate

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `dilate` | `radius` | 0.5 to 100 | 1.0 |
| OpenCV | `dilate` | `kernel` | shape | disk |
| | | `iterations` | 1 to 100 | 1 |
| SKImage | `dilation` | `footprint` | disk/square | disk(1) |
| Photoshop | Maximum | Radius | 1 to 500 | 1 |
| Affinity | Dilate | Radius | 0 to 100 px | 1 |
| GIMP | Dilate | - | fixed | - |

**Parameter equivalence:** ImageStag range matches Affinity (0.5-100). Uses circular structuring element.

---

### Erode

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| **ImageStag** | `erode` | `radius` | 0.5 to 100 | 1.0 |
| OpenCV | `erode` | `kernel` | shape | disk |
| | | `iterations` | 1 to 100 | 1 |
| SKImage | `erosion` | `footprint` | disk/square | disk(1) |
| Photoshop | Minimum | Radius | 1 to 500 | 1 |
| Affinity | Erode | Radius | 0 to 100 px | 1 |
| GIMP | Erode | - | fixed | - |

**Parameter equivalence:** ImageStag range matches Affinity (0.5-100). Uses circular structuring element.

---

### Open

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *morph_open* | `radius` | 0.5 to 100 | 1.0 |
| OpenCV | `morphologyEx(MORPH_OPEN)` | `kernel` | shape | disk |
| SKImage | `opening` | `footprint` | disk/square | disk(1) |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | Open | - | - | - |

**Note:** Open = Erode followed by Dilate. Removes small bright spots.

---

### Close

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *morph_close* | `radius` | 0.5 to 100 | 1.0 |
| OpenCV | `morphologyEx(MORPH_CLOSE)` | `kernel` | shape | disk |
| SKImage | `closing` | `footprint` | disk/square | disk(1) |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | Close | - | - | - |

**Note:** Close = Dilate followed by Erode. Fills small dark holes.

---

### Morphological Gradient

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *morph_gradient* | `radius` | 0.5 to 100 | 1.0 |
| OpenCV | `morphologyEx(MORPH_GRADIENT)` | `kernel` | shape | disk |
| SKImage | dilation - erosion | - | - | - |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | - | - | - | - |

**Note:** Gradient = Dilate - Erode. Produces edge outline.

---

### Top Hat

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *top_hat* | `radius` | 0.5 to 100 | 1.0 |
| OpenCV | `morphologyEx(MORPH_TOPHAT)` | `kernel` | shape | disk |
| SKImage | `white_tophat` | `footprint` | disk/square | disk(1) |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | - | - | - | - |

**Note:** Top Hat = Original - Open. Extracts bright features smaller than kernel.

---

### Black Hat

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *black_hat* | `radius` | 0.5 to 100 | 1.0 |
| OpenCV | `morphologyEx(MORPH_BLACKHAT)` | `kernel` | shape | disk |
| SKImage | `black_tophat` | `footprint` | disk/square | disk(1) |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | - | - | - | - |

**Note:** Black Hat = Close - Original. Extracts dark features smaller than kernel.

---

## Category 10: Distortion & Transform

### Spherize

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *spherize* | `amount` | -100 to 100 | 100 |
| | | `mode` | normal/horizontal/vertical | normal |
| OpenCV | `remap` | custom | - | - |
| SKImage | - | - | - | - |
| Photoshop | Spherize | Amount | -100% to 100% | 100% |
| | | Mode | Normal/Horizontal/Vertical | Normal |
| Affinity | Spherical | - | - | - |
| GIMP | Spherize | Curvature | -1 to 1 | 0.5 |

---

### Pinch

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *pinch* | `amount` | -100 to 100 | 50 |
| OpenCV | `remap` | custom | - | - |
| SKImage | - | - | - | - |
| Photoshop | Pinch | Amount | -100% to 100% | 50% |
| Affinity | - | - | - | - |
| GIMP | Whirl and Pinch | Pinch | -1 to 1 | 0 |

---

### Twirl / Swirl

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *twirl* | `angle` | -999 to 999 | 50 |
| | | `radius` | 0 to 100% | 100 |
| OpenCV | `remap` | custom | - | - |
| SKImage | `swirl` | `rotation` | -2π to 2π | 0 |
| | | `strength` | 0 to 100 | 10 |
| Photoshop | Twirl | Angle | -999° to 999° | 50° |
| Affinity | - | - | - | - |
| GIMP | Whirl and Pinch | Whirl | -360 to 360 | 90 |

---

### Wave

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *wave* | `amplitude` | 1 to 999 | 10 |
| | | `wavelength` | 1 to 999 | 120 |
| | | `type` | sine/triangle/square | sine |
| OpenCV | `remap` | custom | - | - |
| SKImage | - | - | - | - |
| Photoshop | Wave | Amplitude | 1 to 999 | varies |
| | | Wavelength | 1 to 999 | varies |
| | | Type | Sine/Triangle/Square | Sine |
| Affinity | - | - | - | - |
| GIMP | Waves | Amplitude | 0 to 1000 | 10 |
| | | Wavelength | 0 to 1000 | 10 |

---

### Ripple

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *ripple* | `amount` | -999 to 999 | 100 |
| | | `size` | small/medium/large | medium |
| OpenCV | `remap` | custom | - | - |
| SKImage | - | - | - | - |
| Photoshop | Ripple | Amount | -999% to 999% | 100% |
| | | Size | Small/Medium/Large | Medium |
| Affinity | - | - | - | - |
| GIMP | Ripple | Amplitude | 0 to 200 | 5 |

---

### Polar Coordinates

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *polar_coordinates* | `mode` | rect_to_polar / polar_to_rect | rect_to_polar |
| OpenCV | `warpPolar` | `flags` | WARP_POLAR_LINEAR/LOG | LINEAR |
| SKImage | - | - | - | - |
| Photoshop | Polar Coordinates | - | Rectangular to Polar / Polar to Rectangular | R to P |
| Affinity | - | - | - | - |
| GIMP | Polar Coordinates | - | - | - |

---

### Displace

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *displace* | `map` | grayscale image | - |
| | | `x_scale` | -999 to 999 | 10 |
| | | `y_scale` | -999 to 999 | 10 |
| OpenCV | `remap` | `map1`, `map2` | float arrays | - |
| SKImage | - | - | - | - |
| Photoshop | Displace | Horizontal/Vertical Scale | -999 to 999 | 10 |
| Affinity | Displace | - | - | - |
| GIMP | Displace | X/Y displacement | -500 to 500 | varies |

---

### Liquify

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *liquify* | `mesh` | displacement mesh | - |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Liquify | interactive | - | - |
| Affinity | Liquify | interactive | - | - |
| GIMP | Warp Transform | interactive | - | - |

---

## Category 11: Lens Corrections & Effects

### Lens Correction

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *lens_correction* | `k1` | -1 to 1 | 0 |
| | | `k2` | -1 to 1 | 0 |
| | | `k3` | -1 to 1 | 0 |
| OpenCV | `undistort` | `cameraMatrix`, `distCoeffs` | calibrated | - |
| SKImage | - | - | - | - |
| Photoshop | Lens Correction | Distortion | -100 to 100 | 0 |
| Affinity | Lens Correction | profile-based | - | - |
| GIMP | Lens Distortion | Main/Edge/Zoom | -100 to 100 | 0 |

---

### Chromatic Aberration

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *chromatic_aberration* | `red_shift` | -20 to 20 | 0 |
| | | `blue_shift` | -20 to 20 | 0 |
| OpenCV | channel shift | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Lens Correction | Chromatic Aberration | - | - |
| Affinity | Chromatic Aberration | R/G/B shift | - | - |
| GIMP | - | - | - | - |

---

### Vignette

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *vignette* | `amount` | -100 to 100 | -50 |
| | | `midpoint` | 0 to 100 | 50 |
| | | `roundness` | -100 to 100 | 0 |
| | | `feather` | 0 to 100 | 50 |
| OpenCV | radial gradient multiply | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Lens Correction | Vignette | -100 to 100 | 0 |
| Affinity | Vignette | Exposure, Hardness, Scale | varies | varies |
| GIMP | Vignette | Softness, Radius | 0-100%, 0-200% | varies |

---

### Lens Flare

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *lens_flare* | `position` | (x, y) normalized | (0.5, 0.5) |
| | | `brightness` | 0 to 300 | 100 |
| | | `type` | 50-300mm/35mm/etc | 50-300mm |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Lens Flare | Brightness | 10% to 300% | 100% |
| | | Lens Type | 50-300mm/35mm/etc | 50-300mm |
| Affinity | Light Leak | - | - | - |
| GIMP | Lens Flare | - | - | - |

---

## Category 12: Render & Generate

### Gradient

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *gradient* | `type` | linear/radial/angle/reflected/diamond | linear |
| | | `colors` | list of (pos, color) | [(0,black),(1,white)] |
| | | `angle` | 0 to 360 | 0 |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Gradient | Type, Colors, Angle | as above | varies |
| Affinity | Gradient | Type, Colors, Angle | as above | varies |
| GIMP | Gradient | Type, Colors | as above | FG-BG |

---

### Clouds / Plasma

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *clouds* | `scale` | 1 to 100 | 25 |
| | | `seed` | int | random |
| OpenCV | Perlin/Simplex noise | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | Clouds | - | - | - |
| | | Difference Clouds | - | blends | - |
| Affinity | Clouds | Scale | 0 to 1000% | 100% |
| GIMP | Plasma | Turbulence | 0 to 7 | 1 |

---

### Perlin Noise

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *perlin_noise* | `scale` | 0.01 to 100 | 1.0 |
| | | `octaves` | 1 to 16 | 4 |
| | | `persistence` | 0 to 1 | 0.5 |
| | | `seed` | int | random |
| OpenCV | - | - | - | - |
| SKImage | - | - | - | - |
| Photoshop | - | - | - | - |
| Affinity | Perlin Noise | Scale, Detail | varies | varies |
| GIMP | Perlin Noise | Scale, Detail, Tileable | varies | varies |

---

### Checkerboard

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *checkerboard* | `size` | 1 to 1000 | 8 |
| | | `color1` | RGB | (0,0,0) |
| | | `color2` | RGB | (255,255,255) |
| OpenCV | - | - | - | - |
| SKImage | `checkerboard` | - | - | - |
| Photoshop | - | - | - | - |
| Affinity | - | - | - | - |
| GIMP | Checkerboard | Size | 1 to 1024 | 10 |

---

## Category 13: Blend Modes

### Standard Blend Modes

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *blend* | `mode` | see list below | normal |
| | | `opacity` | 0.0 to 1.0 | 1.0 |

**Supported modes:** normal, multiply, screen, overlay, darken, lighten, color_dodge, color_burn, hard_light, soft_light, difference, exclusion, hue, saturation, color, luminosity

**All software supports these modes:** Photoshop, Affinity, GIMP, and most image editors.

---

## Category 14: Analysis

### Histogram

| Software | Function | Parameter | Range | Default |
|----------|----------|-----------|-------|---------|
| *ImageStag* | *histogram* | `bins` | 1 to 256 | 256 |
| | | `channel` | r/g/b/luminosity/all | all |
| OpenCV | `calcHist` | `histSize` | 1 to 256 | 256 |
| SKImage | `histogram` | `nbins` | 1 to 256 | 256 |
| Photoshop | Histogram | - | - | - |
| Affinity | Histogram | - | - | - |
| GIMP | Histogram | - | - | - |

---

## Implementation Summary

### Implemented (30 filters)

| Category | Count | Filters |
|----------|-------|---------|
| Basic Color | 9 | brightness, contrast, saturation, hue_shift, vibrance, exposure, gamma, color_balance, invert |
| Levels & Curves | 3 | levels, curves, auto_levels |
| Advanced Color | 1 | grayscale (= Black & White) |
| Blur | 3 | gaussian_blur, box_blur, motion_blur |
| Sharpen | 3 | sharpen, unsharp_mask, high_pass |
| Edge Detection | 3 | sobel, laplacian, find_edges |
| Stylize | 4 | posterize, solarize, threshold, emboss |
| Noise | 3 | add_noise, median, denoise |
| Morphology | 2 | dilate, erode |

### Planned Priority

**High (Next 20):** bilateral, lens_blur, canny, oil_paint, halftone, film_grain, morph_open, morph_close, vignette, chromatic_aberration, channel_mixer, selective_color, gradient_map, color_lut, clarity, dehaze, radial_blur_spin, radial_blur_zoom, spherize, twirl

**Medium (Next 30):** All remaining distortion, render, and stylize filters.

---

## Bit Depth Differences

| Filter | u8 Output | f32 Output | Reason |
|--------|-----------|------------|--------|
| Sobel | 0-255 clipped | 0.0-1.0 normalized | Kernel sum can exceed 255 |
| Laplacian | 0-255 clipped | 0.0-1.0 normalized | Kernel sum can exceed 255 |
| Find Edges | 0-255 clipped | 0.0-1.0 normalized | Uses Sobel internally |

All other filters produce equivalent normalized results.
