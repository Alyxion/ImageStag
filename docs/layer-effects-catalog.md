# Layer Effects Catalog

Complete reference for Photoshop-style layer effects (layer styles) in ImageStag, with cross-application comparison and implementation details.

## Overview

**Layer Effects vs Filters:**
- **Filters**: Transform pixel data directly, fixed canvas size, no position tracking
- **Layer Effects**: Work primarily with alpha channel, may expand canvas, return position offsets, support blend modes and opacity

ImageStag layer effects provide cross-platform parity between Python (PyO3) and JavaScript (WASM), ensuring identical output regardless of platform.

---

## Quick Reference

| Effect | Status | Canvas Expansion | Primary Operation |
|--------|--------|------------------|-------------------|
| [Drop Shadow](#1-drop-shadow) | ✅ Implemented | Yes | Blur + offset alpha |
| [Inner Shadow](#2-inner-shadow) | ✅ Implemented | No | Blur + offset from edge inward |
| [Outer Glow](#3-outer-glow) | ✅ Implemented | Yes | Blur alpha outward |
| [Inner Glow](#4-inner-glow) | ✅ Implemented | No | Blur alpha inward from edge |
| [Bevel & Emboss](#5-bevel--emboss) | ✅ Implemented | Varies by style | Alpha gradient + lighting |
| [Satin](#6-satin) | ✅ Implemented | No | Shifted blur + composite |
| [Color Overlay](#7-color-overlay) | ✅ Implemented | No | Solid color fill |
| [Gradient Overlay](#8-gradient-overlay) | ✅ Implemented | No | Gradient fill |
| [Pattern Overlay](#9-pattern-overlay) | ✅ Implemented | No | Tiled pattern fill |
| [Stroke](#10-stroke) | ✅ Implemented | Varies by position | Dilate/erode alpha |

---

## Effect Stacking Order

When multiple effects are applied to a layer, they render in this order (bottom to top):

1. **Drop Shadow** - Rendered behind all other content
2. **Outer Glow** - Rendered behind layer content
3. **Layer Content** - The actual layer pixels
4. **Inner Shadow** - Rendered on top of content
5. **Inner Glow** - Rendered on top of content
6. **Satin** - Rendered on top of content
7. **Color Overlay** - Rendered on top of content
8. **Gradient Overlay** - Rendered on top of content
9. **Pattern Overlay** - Rendered on top of content
10. **Stroke** - Rendered on top (outside stroke behind, inside stroke on top)
11. **Bevel & Emboss** - Highlights/shadows on top of everything

---

## 1. Drop Shadow

Creates a shadow cast by the layer content, offset and blurred behind the layer.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Blend Mode | ✅ 27 modes | ❌ | ✅ | ✅ |
| Color | ✅ RGBA | ✅ | ✅ | ✅ RGB |
| Opacity | ✅ 0-100% | ✅ | ✅ | ✅ 0.0-1.0 |
| Angle | ✅ -180° to 180° | ❌ (X/Y offset) | ✅ | ✅ degrees |
| Distance | ✅ 0-500px | ❌ | ✅ | ✅ offset_x/y |
| Spread | ✅ 0-100% | ✅ (Grow radius) | ❌ | ✅ 0.0-1.0 |
| Size | ✅ 0-250px | ✅ (Blur radius) | ✅ (Radius) | ✅ blur |
| Contour | ✅ preset/custom | ❌ | ❌ | ❌ |
| Noise | ✅ 0-100% | ❌ | ❌ | ❌ |
| Use Global Light | ✅ | ❌ | ❌ | ❌ |

### Photoshop Defaults
- Blend Mode: Multiply
- Color: Black (#000000)
- Opacity: 75%
- Angle: 120°
- Distance: 5px
- Spread: 0%
- Size: 5px

### Algorithm

1. Extract alpha channel from input image
2. Apply spread (dilate alpha by `size * spread` pixels)
3. Apply Gaussian blur with radius = `size`
4. Offset the blurred alpha by `(distance * cos(angle), distance * sin(angle))`
5. Expand canvas to accommodate offset + blur radius
6. Create shadow pixels using `color * blurred_alpha * opacity`
7. Composite original image on top using Porter-Duff "over"

### ImageStag Usage

```python
from imagestag.layer_effects import DropShadow

effect = DropShadow(
    blur=5.0,           # Blur radius (sigma)
    offset_x=4.0,       # Horizontal offset
    offset_y=4.0,       # Vertical offset
    color=(0, 0, 0),    # Shadow color (RGB, 0-255)
    opacity=0.75,       # Shadow opacity (0.0-1.0)
)
result = effect.apply(image)
# result.image contains output (may be larger than input)
# result.offset_x, result.offset_y indicate position shift
```

---

## 2. Inner Shadow

Creates a shadow inside the layer edges, giving a sunken appearance.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Blend Mode | ✅ 27 modes | ❌ | ✅ | ✅ |
| Color | ✅ RGBA | ❌ | ✅ | ✅ RGB |
| Opacity | ✅ 0-100% | ❌ | ✅ | ✅ 0.0-1.0 |
| Angle | ✅ -180° to 180° | ❌ | ✅ | ✅ degrees |
| Distance | ✅ 0-500px | ❌ | ✅ | ✅ offset_x/y |
| Choke | ✅ 0-100% | ❌ | ❌ | ✅ 0.0-1.0 |
| Size | ✅ 0-250px | ❌ | ✅ | ✅ blur |
| Contour | ✅ preset/custom | ❌ | ❌ | ❌ |
| Noise | ✅ 0-100% | ❌ | ❌ | ❌ |

### Photoshop Defaults
- Blend Mode: Multiply
- Color: Black (#000000)
- Opacity: 75%
- Angle: 120°
- Distance: 5px
- Choke: 0%
- Size: 5px

### Algorithm

1. Extract alpha channel
2. Invert alpha to get "outside" mask
3. Offset inverted alpha by angle/distance (toward inside)
4. Apply choke (erode) to narrow the shadow
5. Apply Gaussian blur
6. Mask result with original alpha (shadow only appears inside)
7. Blend shadow color onto original using multiply (or specified blend mode)

### ImageStag Usage

```python
from imagestag.layer_effects import InnerShadow

effect = InnerShadow(
    blur=5.0,
    offset_x=4.0,
    offset_y=4.0,
    color=(0, 0, 0),
    opacity=0.75,
    choke=0.0,          # Shrink shadow before blur (0.0-1.0)
)
result = effect.apply(image)
```

---

## 3. Outer Glow

Creates a glow effect radiating outward from the layer edges.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Blend Mode | ✅ 27 modes | ❌ | ✅ | ✅ |
| Color | ✅ or Gradient | ❌ | ✅ | ✅ RGB |
| Opacity | ✅ 0-100% | ❌ | ✅ | ✅ 0.0-1.0 |
| Noise | ✅ 0-100% | ❌ | ❌ | ❌ |
| Technique | ✅ Softer/Precise | ❌ | ❌ | ❌ |
| Spread | ✅ 0-100% | ❌ | ✅ (Density) | ✅ 0.0-1.0 |
| Size | ✅ 0-250px | ❌ | ✅ (Radius) | ✅ radius |
| Contour | ✅ preset/custom | ❌ | ❌ | ❌ |
| Range | ✅ 0-100% | ❌ | ❌ | ❌ |
| Jitter | ✅ 0-100% | ❌ | ❌ | ❌ |

### Photoshop Defaults
- Blend Mode: Screen
- Color: Yellow (#FFFF00)
- Opacity: 75%
- Technique: Softer
- Spread: 0%
- Size: 5px

### Algorithm

1. Extract alpha channel
2. Apply spread (dilate alpha by `radius * spread` pixels)
3. Apply Gaussian blur with full radius
4. Subtract original alpha to get glow-only mask
5. Expand canvas to accommodate blur radius
6. Create glow pixels using `color * glow_mask * opacity`
7. Use "screen" blend mode to add glow (additive-like)
8. Composite original on top

### ImageStag Usage

```python
from imagestag.layer_effects import OuterGlow

effect = OuterGlow(
    radius=10.0,        # Glow radius
    color=(255, 255, 0),# Glow color (RGB, 0-255)
    opacity=0.75,
    spread=0.0,         # Solid core before blur (0.0-1.0)
)
result = effect.apply(image)
```

---

## 4. Inner Glow

Creates a glow effect radiating inward from the layer edges (or outward from center).

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Blend Mode | ✅ 27 modes | ❌ | ✅ | ✅ |
| Color | ✅ or Gradient | ❌ | ✅ | ✅ RGB |
| Opacity | ✅ 0-100% | ❌ | ✅ | ✅ 0.0-1.0 |
| Noise | ✅ 0-100% | ❌ | ❌ | ❌ |
| Technique | ✅ Softer/Precise | ❌ | ❌ | ❌ |
| Source | ✅ Center/Edge | ❌ | ❌ | ✅ |
| Choke | ✅ 0-100% | ❌ | ❌ | ✅ 0.0-1.0 |
| Size | ✅ 0-250px | ❌ | ✅ | ✅ radius |
| Contour | ✅ preset/custom | ❌ | ❌ | ❌ |
| Range | ✅ 0-100% | ❌ | ❌ | ❌ |
| Jitter | ✅ 0-100% | ❌ | ❌ | ❌ |

### Photoshop Defaults
- Blend Mode: Screen
- Color: Yellow (#FFFF00)
- Opacity: 75%
- Source: Edge
- Choke: 0%
- Size: 5px

### Algorithm (Source: Edge)

1. Extract alpha channel
2. Apply choke (erode alpha)
3. Apply Gaussian blur
4. Compute edge distance: `original_alpha - blurred_alpha`
5. Mask with original alpha (only inside layer)
6. Blend glow color using "screen" mode

### Algorithm (Source: Center)

1. Extract alpha channel
2. Create distance field from edges
3. Invert to get center-based falloff
4. Apply blur and choke
5. Blend glow color using "screen" mode

### ImageStag Usage

```python
from imagestag.layer_effects import InnerGlow

effect = InnerGlow(
    radius=10.0,
    color=(255, 255, 0),
    opacity=0.75,
    choke=0.0,
    source="edge",      # "edge" or "center"
)
result = effect.apply(image)
```

---

## 5. Bevel & Emboss

Creates a 3D raised or sunken appearance using simulated lighting on the layer edges.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Style | ✅ 5 styles | ❌ | ✅ | ✅ 4 styles |
| Technique | ✅ 3 techniques | ❌ | ❌ | ❌ |
| Depth | ✅ 1-1000% | ❌ | ✅ | ✅ |
| Direction | ✅ Up/Down | ❌ | ❌ | ✅ |
| Size | ✅ 0-250px | ❌ | ✅ | ✅ |
| Soften | ✅ 0-16px | ❌ | ❌ | ✅ |
| Angle | ✅ -180° to 180° | ❌ | ✅ | ✅ |
| Altitude | ✅ 0-90° | ❌ | ❌ | ✅ |
| Gloss Contour | ✅ preset/custom | ❌ | ❌ | ❌ |
| Highlight Mode | ✅ 27 modes | ❌ | ✅ | ❌ |
| Highlight Color | ✅ | ❌ | ✅ | ✅ |
| Highlight Opacity | ✅ 0-100% | ❌ | ✅ | ✅ |
| Shadow Mode | ✅ 27 modes | ❌ | ✅ | ❌ |
| Shadow Color | ✅ | ❌ | ✅ | ✅ |
| Shadow Opacity | ✅ 0-100% | ❌ | ✅ | ✅ |

### Styles

| Style | Description | Canvas Expansion |
|-------|-------------|------------------|
| Outer Bevel | Bevel on outside edge | Yes |
| Inner Bevel | Bevel on inside edge | No |
| Emboss | Raised from surface | No |
| Pillow Emboss | Stamped into surface | No |
| Stroke Emboss | Bevel on stroke (requires Stroke effect) | Depends on stroke |

### Photoshop Defaults
- Style: Inner Bevel
- Technique: Smooth
- Depth: 100%
- Direction: Up
- Size: 5px
- Soften: 0px
- Angle: 120°
- Altitude: 30°
- Highlight: Screen, White, 75%
- Shadow: Multiply, Black, 75%

### Algorithm

1. Create bump map by computing gradient of alpha channel
2. Blur bump map for "Smooth" technique (less blur for "Chisel")
3. Calculate light direction from angle and altitude
4. Compute dot product of bump normals with light direction
5. Positive values = highlight, negative values = shadow
6. Apply highlight color where lit, shadow color where shadowed
7. Mask with appropriate area based on style:
   - Inner Bevel: Inside original alpha
   - Outer Bevel: Outside original alpha (expanded)
   - Emboss: Both inside and outside
   - Pillow Emboss: Inverted lighting inside

### ImageStag Usage

```python
from imagestag.layer_effects import BevelEmboss

effect = BevelEmboss(
    depth=3.0,
    angle=120.0,        # Light angle in degrees
    altitude=30.0,      # Light altitude in degrees
    highlight_color=(255, 255, 255),
    highlight_opacity=0.75,
    shadow_color=(0, 0, 0),
    shadow_opacity=0.75,
    style="inner_bevel", # outer_bevel, inner_bevel, emboss, pillow_emboss
)
result = effect.apply(image)
```

---

## 6. Satin

Creates a silky, satiny interior shading by compositing shifted and blurred copies of the layer alpha.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Blend Mode | ✅ 27 modes | ❌ | ❌ | ✅ |
| Color | ✅ RGBA | ❌ | ❌ | ✅ RGB |
| Opacity | ✅ 0-100% | ❌ | ❌ | ✅ 0.0-1.0 |
| Angle | ✅ -180° to 180° | ❌ | ❌ | ✅ degrees |
| Distance | ✅ 0-250px | ❌ | ❌ | ✅ |
| Size | ✅ 0-250px | ❌ | ❌ | ✅ |
| Contour | ✅ preset/custom | ❌ | ❌ | ❌ |
| Invert | ✅ | ❌ | ❌ | ✅ |

### Photoshop Defaults
- Blend Mode: Multiply
- Color: Black (#000000)
- Opacity: 50%
- Angle: 19°
- Distance: 11px
- Size: 14px
- Invert: false

### Algorithm

1. Extract alpha channel from input
2. Create two offset copies:
   - Copy A: offset by `(distance * cos(angle), distance * sin(angle))`
   - Copy B: offset by `(-distance * cos(angle), -distance * sin(angle))`
3. Apply Gaussian blur (size) to both copies
4. Compute difference: `|Copy_A - Copy_B|`
5. If invert: `1.0 - difference`
6. Mask with original alpha (only inside layer)
7. Blend color using difference as opacity

### ImageStag Usage

```python
from imagestag.layer_effects import Satin

effect = Satin(
    color=(0, 0, 0),
    opacity=0.5,
    angle=19.0,
    distance=11.0,
    size=14.0,
    invert=False,
)
result = effect.apply(image)
```

---

## 7. Color Overlay

Fills the layer with a solid color while preserving transparency.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Blend Mode | ✅ 27 modes | ❌ | ✅ | ✅ |
| Color | ✅ RGBA | ❌ | ✅ | ✅ RGB |
| Opacity | ✅ 0-100% | ❌ | ✅ | ✅ 0.0-1.0 |

### Photoshop Defaults
- Blend Mode: Normal
- Color: Red (#FF0000)
- Opacity: 100%

### Algorithm

1. For each pixel in the image:
2. Keep original alpha value
3. Replace RGB with overlay color
4. Apply opacity: `final_rgb = original_rgb * (1 - opacity) + color * opacity`
5. Blend according to blend mode

### ImageStag Usage

```python
from imagestag.layer_effects import ColorOverlay

effect = ColorOverlay(
    color=(255, 0, 0),  # Red
    opacity=1.0,
    blend_mode="normal",
)
result = effect.apply(image)
```

---

## 8. Gradient Overlay

Fills the layer with a gradient while preserving transparency.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Blend Mode | ✅ 27 modes | Partial | ✅ | ✅ |
| Opacity | ✅ 0-100% | ✅ | ✅ | ✅ 0.0-1.0 |
| Gradient | ✅ preset/custom | ✅ | ✅ | ✅ color stops |
| Style | ✅ 5 styles | ✅ | ✅ | ✅ 5 styles |
| Angle | ✅ -180° to 180° | ✅ | ✅ | ✅ degrees |
| Scale | ✅ 10-150% | ✅ | ✅ | ✅ 0.1-1.5 |
| Reverse | ✅ | ✅ | ✅ | ✅ |
| Align with Layer | ✅ | ❌ | ✅ | ✅ |
| Dither | ✅ | ❌ | ❌ | ❌ |

### Gradient Styles

| Style | Description |
|-------|-------------|
| Linear | Gradient along a line at specified angle |
| Radial | Circular gradient from center outward |
| Angle | Gradient sweeps around center point |
| Reflected | Linear gradient mirrored at center |
| Diamond | Diamond-shaped gradient from center |

### Photoshop Defaults
- Blend Mode: Normal
- Opacity: 100%
- Style: Linear
- Angle: 90° (vertical)
- Scale: 100%
- Reverse: false
- Align with Layer: true

### Algorithm

1. Determine gradient bounds (layer bounds or full canvas)
2. For each pixel, calculate position parameter `t` (0.0 to 1.0):
   - **Linear**: `t = (x * cos(angle) + y * sin(angle)) / length`
   - **Radial**: `t = sqrt((x-cx)² + (y-cy)²) / radius`
   - **Angle**: `t = atan2(y-cy, x-cx) / (2π)`
   - **Reflected**: `t = |2 * linear_t - 1|`
   - **Diamond**: `t = max(|x-cx|, |y-cy|) / radius`
3. Apply scale: `t = t / scale`
4. If reverse: `t = 1.0 - t`
5. Interpolate gradient color stops at `t`
6. Apply to pixels where alpha > 0
7. Blend according to blend mode and opacity

### ImageStag Usage

```python
from imagestag.layer_effects import GradientOverlay

effect = GradientOverlay(
    # Gradient as list of (position, r, g, b) tuples
    gradient=[
        (0.0, 255, 0, 0),    # Red at start
        (0.5, 255, 255, 0),  # Yellow at middle
        (1.0, 0, 255, 0),    # Green at end
    ],
    style="linear",     # linear, radial, angle, reflected, diamond
    angle=90.0,         # Angle in degrees (for linear/reflected)
    scale=1.0,          # Scale factor (1.0 = 100%)
    reverse=False,
    opacity=1.0,
    blend_mode="normal",
)
result = effect.apply(image)
```

---

## 9. Pattern Overlay

Fills the layer with a repeating pattern while preserving transparency.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Blend Mode | ✅ 27 modes | ❌ | ✅ | ✅ |
| Opacity | ✅ 0-100% | ❌ | ✅ | ✅ 0.0-1.0 |
| Pattern | ✅ library | ❌ | ✅ | ✅ numpy array |
| Scale | ✅ 1-1000% | ❌ | ✅ | ✅ 0.01-10.0 |
| Link with Layer | ✅ | ❌ | ✅ | ✅ |
| Offset X/Y | ✅ (Snap to Origin) | ❌ | ✅ | ✅ |

### Photoshop Defaults
- Blend Mode: Normal
- Opacity: 100%
- Scale: 100%
- Link with Layer: true

### Algorithm

1. Scale pattern if scale ≠ 1.0 (using bilinear interpolation)
2. Apply offset to pattern origin
3. For each pixel in layer where alpha > 0:
   - Calculate pattern coordinates: `px = (x + offset_x) % pattern_width`
   - Sample pattern at `(px, py)`
   - Blend pattern color with layer using blend mode and opacity

### ImageStag Usage

```python
from imagestag.layer_effects import PatternOverlay
import numpy as np

# Create or load a pattern (RGBA numpy array)
pattern = np.zeros((16, 16, 4), dtype=np.uint8)
pattern[::2, ::2] = [255, 255, 255, 255]  # Checkerboard
pattern[1::2, 1::2] = [255, 255, 255, 255]

effect = PatternOverlay(
    pattern=pattern,    # RGBA numpy array
    scale=1.0,          # Scale factor
    offset_x=0,         # Horizontal offset
    offset_y=0,         # Vertical offset
    opacity=1.0,
    blend_mode="normal",
)
result = effect.apply(image)
```

---

## 10. Stroke

Creates an outline around the layer content.

### Parameters

| Parameter | Photoshop | GIMP | Affinity | ImageStag |
|-----------|-----------|------|----------|-----------|
| Size | ✅ 1-250px | ✅ | ✅ | ✅ |
| Position | ✅ 3 positions | ✅ | ✅ | ✅ |
| Blend Mode | ✅ 27 modes | ❌ | ✅ | ✅ |
| Opacity | ✅ 0-100% | ✅ | ✅ | ✅ 0.0-1.0 |
| Fill Type | ✅ Color/Gradient/Pattern | ✅ Color | ✅ | ✅ Color only |
| Color | ✅ RGBA | ✅ | ✅ | ✅ RGB |

### Stroke Positions

| Position | Description | Canvas Expansion |
|----------|-------------|------------------|
| Outside | Stroke outside the layer edge | Yes |
| Inside | Stroke inside the layer edge | No |
| Center | Stroke centered on the layer edge | Yes (half) |

### Photoshop Defaults
- Size: 3px
- Position: Outside
- Blend Mode: Normal
- Opacity: 100%
- Fill Type: Color
- Color: Red (#FF0000)

### Algorithm

**Outside Stroke:**
1. Dilate alpha by stroke width
2. Subtract original alpha to get stroke mask
3. Fill stroke area with color
4. Composite original on top

**Inside Stroke:**
1. Erode alpha by stroke width
2. Subtract eroded from original to get stroke mask
3. Fill stroke area with color (masked by original alpha)
4. No canvas expansion needed

**Center Stroke:**
1. Dilate alpha by half stroke width
2. Erode alpha by half stroke width
3. Subtract eroded from dilated to get stroke mask
4. Fill stroke area with color
5. Composite appropriately

### ImageStag Usage

```python
from imagestag.layer_effects import Stroke

effect = Stroke(
    width=3.0,
    color=(255, 0, 0),
    opacity=1.0,
    position="outside",  # outside, inside, center
)
result = effect.apply(image)
```

---

## Blend Modes Reference

All blend modes that can be used with layer effects:

### Normal Group
| Mode | Formula | Description |
|------|---------|-------------|
| Normal | `B` | Replace with source |
| Dissolve | Random dither | Dithered transparency |

### Darken Group
| Mode | Formula | Description |
|------|---------|-------------|
| Darken | `min(A, B)` | Keep darker pixel |
| Multiply | `A × B` | Multiply colors (always darker) |
| Color Burn | `1 - (1-A) / B` | Increase contrast, darken |
| Linear Burn | `A + B - 1` | Subtract colors |
| Darker Color | Compare luminosity | Keep darker based on luminosity |

### Lighten Group
| Mode | Formula | Description |
|------|---------|-------------|
| Lighten | `max(A, B)` | Keep lighter pixel |
| Screen | `1 - (1-A)(1-B)` | Inverse multiply (always lighter) |
| Color Dodge | `A / (1-B)` | Increase brightness |
| Linear Dodge (Add) | `A + B` | Add colors |
| Lighter Color | Compare luminosity | Keep lighter based on luminosity |

### Contrast Group
| Mode | Formula | Description |
|------|---------|-------------|
| Overlay | Multiply/Screen | Multiply darks, screen lights |
| Soft Light | Soft contrast | Gentle contrast adjustment |
| Hard Light | Inverse Overlay | Strong contrast |
| Vivid Light | Burn/Dodge | Extreme contrast |
| Linear Light | Linear Burn/Dodge | Linear contrast |
| Pin Light | Darken/Lighten | Selective replacement |
| Hard Mix | Threshold | Posterize to 8 colors |

### Inversion Group
| Mode | Formula | Description |
|------|---------|-------------|
| Difference | `|A - B|` | Absolute difference |
| Exclusion | `A + B - 2AB` | Lower contrast difference |
| Subtract | `A - B` | Subtract colors |
| Divide | `A / B` | Divide colors |

### Component Group
| Mode | Formula | Description |
|------|---------|-------------|
| Hue | A lum/sat + B hue | Apply source hue |
| Saturation | A lum/hue + B sat | Apply source saturation |
| Color | A lum + B hue/sat | Apply source color |
| Luminosity | A hue/sat + B lum | Apply source luminosity |

---

## Cross-Platform Implementation

### Rust Core

All effects are implemented in Rust for maximum performance:

```
rust/src/
├── filters/
│   ├── core.rs          # Shared utilities (blur, dilate, erode)
│   ├── drop_shadow.rs   # Drop shadow
│   ├── stroke.rs        # Stroke
│   └── lighting.rs      # Bevel, glows, inner shadow, color overlay
└── layer_effects/
    ├── mod.rs           # Module exports
    ├── satin.rs         # Satin effect
    ├── gradient_overlay.rs  # Gradient overlay
    └── pattern_overlay.rs   # Pattern overlay
```

### Python Bindings (PyO3)

```python
# Rust functions exposed via PyO3
from imagestag import imagestag_rust

result = imagestag_rust.drop_shadow_rgba(
    image,      # numpy array (H, W, 4), uint8
    offset_x,   # float
    offset_y,   # float
    blur_radius,# float
    color,      # (r, g, b) tuple
    opacity,    # float
    expand,     # int
)
```

### JavaScript Bindings (WASM)

```javascript
import init, { drop_shadow_rgba_wasm } from './wasm/imagestag_rust.js';

await init();

const result = drop_shadow_rgba_wasm(
    imageData,  // Uint8Array (flat RGBA)
    width,      // number
    height,     // number
    4,          // channels
    offsetX,    // number
    offsetY,    // number
    blurRadius, // number
    colorR, colorG, colorB,
    opacity,    // number
    expand,     // number
);
```

---

## Building

```bash
# Rebuild for Python (PyO3)
poetry run maturin develop --release

# Rebuild for JavaScript (WASM)
wasm-pack build rust/ --target web --out-dir ../imagestag/wasm --features wasm --no-default-features
```

---

## Testing

### Unit Tests

```bash
# Run Python layer effect tests
poetry run pytest tests/stagforge/test_layer_effects_python.py -v
```

### Parity Tests

```bash
# Generate Python reference images
poetry run python -m imagestag.parity.generate --category layer_effects

# Run JavaScript tests and compare
node imagestag/parity/js/run_tests.js --category layer_effects

# Compare results
poetry run pytest tests/test_filter_parity.py -v -k layer_effects
```

---

## References

- [Photoshop Layer Styles](https://helpx.adobe.com/photoshop/using/layer-effects-styles.html)
- [GIMP Filters](https://docs.gimp.org/en/filters.html)
- [Affinity Photo Effects](https://affinity.help/photo/en-US.lproj/index.html)
- [Porter-Duff Compositing](https://en.wikipedia.org/wiki/Alpha_compositing)
