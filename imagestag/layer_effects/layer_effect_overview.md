# Layer Effects Overview

Layer effects (Photoshop-style "Layer Styles") are non-destructive visual effects that work with the alpha channel to create shadows, glows, bevels, overlays, and strokes.

## Implementation Status

| Effect | Rust | Python | SVG Export | JS/WASM | Fidelity |
|--------|------|--------|------------|---------|----------|
| Drop Shadow | ✅ | ✅ | ✅ | ❌ | 95% |
| Inner Shadow | ✅ | ✅ | ✅ | ❌ | 85% |
| Outer Glow | ✅ | ✅ | ✅ | ❌ | 90% |
| Inner Glow | ✅ | ✅ | ✅ | ❌ | 85% |
| Bevel & Emboss | ✅ | ✅ | ✅ | ❌ | 70% |
| Satin | ✅ | ✅ | ❌ | ❌ | N/A |
| Color Overlay | ✅ | ✅ | ✅ | ❌ | 100% |
| Gradient Overlay | ✅ | ✅ | ✅ | ❌ | 90% |
| Pattern Overlay | ✅ | ✅ | ✅ | ❌ | 90% |
| Stroke | ✅ | ✅ | ✅ | ❌ | 95% |

## TODO

### High Priority

1. **Canvas Expansion Support for Shadows/Glows**
   - Drop Shadow, Outer Glow, and Stroke (outside) need canvas expansion
   - Currently the `expand` parameter exists but SVG export doesn't account for it
   - Need to adjust SVG viewBox or add padding when effects extend beyond original bounds

2. **JavaScript/WASM Implementation**
   - Transfer all effects to JavaScript using shared templates
   - Use Jinja-like templating to generate both Python and JS from single source
   - Ensures implementations don't diverge
   - Template location: `imagestag/layer_effects/templates/` (to be created)

3. **Satin Effect SVG Export**
   - Currently not implemented (returns `None`)
   - Possible approach: Use two offset/blurred copies with difference blend
   - May require `feDisplacementMap` or custom convolution
   - Fallback: Document as "Rust-only" effect

### Medium Priority

4. **Inner Shadow Intensity Matching**
   - SVG inner shadow is ~85% match to Rust
   - Difference due to alpha gradient handling in SVG filters vs Rust
   - Current workarounds: blur ×0.4, opacity ×2.0
   - Investigate `feConvolveMatrix` for better edge detection

5. **Bevel & Emboss Algorithm**
   - SVG uses edge extraction (different from Rust's gradient-based lighting)
   - ~70% visual fidelity - fundamental algorithm difference
   - Consider documenting as "approximation only"

---

## SVG Export Implementation

### Approach

Each effect implements `to_svg_filter(filter_id: str, scale: float) -> str` method that returns an SVG `<filter>` element. The scale factor converts pixel values to viewBox units:

```python
scale = viewBox_size / render_size
# Example: 128px viewBox rendered at 300px → scale = 0.427
```

### Key Findings

1. **SVG feMorphology produces ~2x visual effect** compared to Rust's dilate/erode
   - Solution: Divide morphology radius by 2

2. **SVG feGaussianBlur matches Rust** (1:1 sigma mapping)
   - No correction needed for blur radius

3. **primitiveUnits="userSpaceOnUse"** required for viewBox-based coordinates
   - Without this, filter values are relative to bounding box

4. **Pattern images need `image-rendering: pixelated`**
   - Prevents interpolation blur when scaling patterns
   - Critical for large viewBox SVGs (e.g., 841×841)

5. **Stroke uses contour extraction** for smooth bezier curves
   - Filter-based `feMorphology` produces jagged edges
   - `to_svg_path()` extracts contours with Douglas-Peucker simplification
   - Parameters: `simplify_epsilon=0.05`, `bezier_smoothness=0.1`
   - Lower epsilon preserves inner hard curves on complex shapes

### Scaling Factors Applied

| Effect | Parameter | Scaling |
|--------|-----------|---------|
| Drop Shadow | blur | `blur * scale` |
| Inner Shadow | blur | `blur * scale * 0.4` |
| Inner Shadow | opacity | `min(1.0, opacity * 2.0)` |
| Outer Glow | blur | `radius * scale` |
| Inner Glow | blur/choke | `value * scale / 2.0` |
| Bevel & Emboss | depth | `depth * scale / 4.0` |
| Stroke (filter) | radius | `width * scale` |
| Stroke (contour) | stroke-width | `width / 2.0` |

---

## Layer Effects vs Filters

| Aspect | Filters | Layer Effects |
|--------|---------|---------------|
| Canvas size | Fixed | May expand (drop shadow, outer glow, stroke) |
| Position | None | Returns offset_x/y for compositing |
| Alpha handling | Processes all channels | Works specifically with alpha channel |
| Output | Just the image array | `EffectResult(image, offset_x, offset_y)` |
| Use case | Pixel transformations | Layer styling for compositing |

## Rust Implementation

All layer effects are implemented in `rust/src/layer_effects/`:

| File | Effects | Description |
|------|---------|-------------|
| `drop_shadow.rs` | Drop Shadow | Shadow cast behind the layer |
| `lighting.rs` | Inner Shadow, Outer Glow, Inner Glow, Bevel & Emboss, Color Overlay | Lighting-based effects |
| `satin.rs` | Satin | Silky interior shading |
| `gradient_overlay.rs` | Gradient Overlay | Gradient fill (5 styles) |
| `pattern_overlay.rs` | Pattern Overlay | Tiled pattern fill |
| `stroke.rs` | Stroke | Outline around layer content |

## Python Wrappers

Python wrappers in `imagestag/layer_effects/`:

| File | Class | Rust Function |
|------|-------|---------------|
| `drop_shadow.py` | `DropShadow` | `drop_shadow_rgba`, `drop_shadow_rgba_f32` |
| `inner_shadow.py` | `InnerShadow` | `inner_shadow_rgba`, `inner_shadow_rgba_f32` |
| `outer_glow.py` | `OuterGlow` | `outer_glow_rgba` |
| `inner_glow.py` | `InnerGlow` | `inner_glow_rgba` |
| `bevel_emboss.py` | `BevelEmboss` | `bevel_emboss_rgba` |
| `satin.py` | `Satin` | `satin_rgba`, `satin_rgba_f32` |
| `color_overlay.py` | `ColorOverlay` | `color_overlay_rgba`, `color_overlay_rgba_f32` |
| `gradient_overlay.py` | `GradientOverlay` | `gradient_overlay_rgba`, `gradient_overlay_rgba_f32` |
| `pattern_overlay.py` | `PatternOverlay` | `pattern_overlay_rgba`, `pattern_overlay_rgba_f32` |
| `stroke.py` | `Stroke` | `stroke_rgba`, `stroke_rgba_f32` |

## WASM Implementation

WASM implementations in `rust/src/wasm.rs`:

| Function | Description |
|----------|-------------|
| `satin_rgba_wasm` | Satin effect (u8) |
| `gradient_overlay_rgba_wasm` | Gradient overlay (u8) |
| `pattern_overlay_rgba_wasm` | Pattern overlay (u8) |

Note: Drop shadow, stroke, and lighting effects are not yet exposed to WASM.

---

## Effect Reference

### 1. DROP SHADOW

Creates a shadow cast behind the layer.

**Rust file:** `rust/src/layer_effects/drop_shadow.rs`

**SVG Implementation:** `<feDropShadow>` or composite filter chain

**SVG Fidelity:** 95% - Minor differences in edge handling

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `offset_x` | f32 | 4.0 | Horizontal shadow offset (positive = right) |
| `offset_y` | f32 | 4.0 | Vertical shadow offset (positive = down) |
| `blur_radius` | f32 | 5.0 | Shadow blur radius (Gaussian sigma) |
| `color` | (u8,u8,u8) | (0,0,0) | Shadow color RGB |
| `opacity` | f32 | 0.75 | Shadow opacity (0.0-1.0) |
| `expand` | usize | 0 | Extra canvas padding (auto-calculated if 0) |

**Algorithm:**
1. Extract alpha channel
2. Blur alpha with Gaussian kernel
3. Offset the blurred alpha
4. Colorize with shadow color
5. Composite original on top using Porter-Duff "over"

**TODO:** SVG export needs to handle `expand` parameter for canvas expansion.

---

### 2. INNER SHADOW

Creates a shadow inside the layer edges.

**Rust file:** `rust/src/layer_effects/lighting.rs`

**SVG Implementation:** Inverted alpha → blur → offset → clip → colorize → composite

**SVG Fidelity:** 85% - Alpha gradient handling differs between SVG and Rust

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `offset_x` | f32 | 2.0 | Horizontal offset |
| `offset_y` | f32 | 2.0 | Vertical offset |
| `blur_radius` | f32 | 5.0 | Shadow blur radius |
| `choke` | f32 | 0.0 | Contraction before blur (0.0-1.0) |
| `color` | (u8,u8,u8) | (0,0,0) | Shadow color |
| `opacity` | f32 | 0.75 | Shadow opacity |

**Algorithm:**
1. Invert alpha (shadow comes from outside)
2. Apply choke (dilate inverted alpha)
3. Blur the result
4. Offset and mask with original alpha

**SVG Adjustments:**
- Blur: `blur * scale * 0.4` (concentrated at edges)
- Opacity: `min(1.0, opacity * 2.0)` (intensity boost)

---

### 3. OUTER GLOW

Creates a glow effect radiating outward from layer edges.

**Rust file:** `rust/src/layer_effects/lighting.rs`

**SVG Implementation:** Alpha → dilate (spread) → blur → colorize → composite under source

**SVG Fidelity:** 90% - Spread parameter limited by integer morphology

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `radius` | f32 | 10.0 | Glow blur radius |
| `color` | (u8,u8,u8) | (255,255,0) | Glow color |
| `opacity` | f32 | 0.75 | Glow opacity |
| `spread` | f32 | 0.0 | Expansion before blur (0.0-1.0) |
| `expand` | usize | 0 | Extra canvas padding |

**Algorithm:**
1. Extract alpha, optionally dilate (spread)
2. Blur alpha
3. Subtract original alpha (glow = blurred - original)
4. Colorize and composite

**TODO:** SVG export needs to handle `expand` parameter.

---

### 4. INNER GLOW

Creates a glow effect radiating inward from layer edges.

**Rust file:** `rust/src/layer_effects/lighting.rs`

**SVG Implementation:** Edge detection via blur difference → screen blend

**SVG Fidelity:** 85% - Center mode challenging to replicate

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `radius` | f32 | 10.0 | Glow blur radius |
| `color` | (u8,u8,u8) | (255,255,0) | Glow color |
| `opacity` | f32 | 0.75 | Glow opacity |
| `choke` | f32 | 0.0 | Contraction before blur (0.0-1.0) |

**Algorithm:**
1. Erode alpha (choke)
2. Blur eroded alpha
3. Compute glow mask: original - blurred
4. Screen blend glow color over original

**SVG Adjustments:**
- Blur/choke: `value * scale / 2.0` (morphology correction)

---

### 5. BEVEL & EMBOSS

Creates a 3D raised or sunken appearance.

**Rust file:** `rust/src/layer_effects/lighting.rs`

**SVG Implementation:** Edge extraction + offset for fake highlight/shadow

**SVG Fidelity:** 70% - Fundamentally different algorithm (edge-based vs gradient-based lighting)

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `depth` | f32 | 3.0 | Bevel depth in pixels |
| `angle` | f32 | 120.0 | Light source angle (degrees) |
| `altitude` | f32 | 30.0 | Light altitude (degrees) |
| `highlight_color` | (u8,u8,u8) | (255,255,255) | Highlight color |
| `highlight_opacity` | f32 | 0.75 | Highlight opacity |
| `shadow_color` | (u8,u8,u8) | (0,0,0) | Shadow color |
| `shadow_opacity` | f32 | 0.75 | Shadow opacity |
| `style` | str | "inner_bevel" | Style: outer_bevel, inner_bevel, emboss, pillow_emboss |

**Rust Algorithm:**
1. Compute gradient (bump map) of alpha channel
2. Blur bump map for smoothness
3. Calculate lighting intensity from angle
4. Apply highlights (positive intensity) and shadows (negative intensity)

**SVG Algorithm (approximation):**
1. Extract edge via morphology erode + subtract
2. Offset edge for highlight (opposite to light direction)
3. Offset edge for shadow (light direction)
4. Colorize and merge

**SVG Adjustments:**
- Depth: `depth * scale / 4.0` (aggressive reduction for subtle effect)

---

### 6. SATIN

Creates silky interior shading.

**Rust file:** `rust/src/layer_effects/satin.rs`

**SVG Implementation:** ❌ Not implemented

**SVG Fidelity:** N/A

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `color` | (u8,u8,u8) | (0,0,0) | Satin color |
| `opacity` | f32 | 0.5 | Satin opacity |
| `angle` | f32 | 19.0 | Offset angle (degrees) |
| `distance` | f32 | 11.0 | Offset distance (pixels) |
| `size` | f32 | 14.0 | Blur size |
| `invert` | bool | false | Invert the satin mask |

**Algorithm:**
1. Create two offset copies of alpha (positive and negative direction)
2. Blur both copies
3. Compute absolute difference
4. Optionally invert
5. Mask with original alpha and composite

**TODO:** Investigate SVG implementation using:
- Two `<feOffset>` + `<feGaussianBlur>` chains
- `<feComposite>` with arithmetic mode for difference
- May require `feConvolveMatrix` for proper blending

---

### 7. COLOR OVERLAY

Fills the layer with a solid color while preserving alpha.

**Rust file:** `rust/src/layer_effects/lighting.rs`

**SVG Implementation:** `<feFlood>` + `<feComposite in="SourceAlpha">`

**SVG Fidelity:** 100%

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `color` | (u8,u8,u8) | (255,0,0) | Overlay color |
| `opacity` | f32 | 1.0 | Overlay opacity |

**Algorithm:**
1. Linear blend between original color and overlay color
2. Preserve original alpha

---

### 8. GRADIENT OVERLAY

Fills the layer with a gradient while preserving alpha.

**Rust file:** `rust/src/layer_effects/gradient_overlay.rs`

**SVG Implementation:** `<linearGradient>` or `<radialGradient>` + mask/clip

**SVG Fidelity:** 90% - Linear and radial styles work well; angle/reflected/diamond are approximations

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gradient` | list | black→white | Color stops: [(pos, r, g, b), ...] |
| `style` | str | "linear" | Style: linear, radial, angle, reflected, diamond |
| `angle` | f32 | 90.0 | Gradient angle (degrees) |
| `scale` | f32 | 1.0 | Scale factor |
| `reverse` | bool | false | Reverse gradient direction |
| `opacity` | f32 | 1.0 | Overlay opacity |

**Gradient Styles:**
- **linear**: `<linearGradient>` at specified angle ✅
- **radial**: `<radialGradient>` from center outward ✅
- **angle**: Sweep around center point (approximation)
- **reflected**: Linear gradient mirrored at center (approximation)
- **diamond**: Diamond-shaped gradient (approximation)

**SVG Blend Modes:**
- `normal`: Uses mask with `feColorMatrix` to convert content to white
- `multiply`: Uses mask with `mix-blend-mode: multiply`

---

### 9. PATTERN OVERLAY

Fills the layer with a tiled pattern while preserving alpha.

**Rust file:** `rust/src/layer_effects/pattern_overlay.rs`

**SVG Implementation:** `<pattern>` with embedded image + mask

**SVG Fidelity:** 90%

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pattern` | ndarray | checkerboard | Pattern image (H,W,3 or 4) |
| `scale` | f32 | 1.0 | Pattern scale factor |
| `offset_x` | int | 0 | Horizontal offset |
| `offset_y` | int | 0 | Vertical offset |
| `opacity` | f32 | 1.0 | Overlay opacity |

**Algorithm:**
1. For each pixel, calculate pattern coordinates with scale and offset
2. Sample pattern with modulo wrapping (tiling)
3. Blend pattern with original based on opacity and pattern alpha

**SVG Implementation:**
- Pattern embedded as base64 PNG in `<pattern>` element
- `image-rendering: pixelated; image-rendering: crisp-edges;` prevents blur
- `viewbox_scale` parameter adjusts pattern size for different viewBoxes

---

### 10. STROKE

Creates an outline around layer content.

**Rust file:** `rust/src/layer_effects/stroke.rs`

**SVG Implementation:** Two approaches available:
1. **Filter-based:** `<feMorphology>` dilate/erode (faster, jagged edges)
2. **Contour-based:** `to_svg_path()` with bezier curves (smooth, preferred)

**SVG Fidelity:** 95% (contour-based), 80% (filter-based)

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `width` | f32 | 2.0 | Stroke width in pixels |
| `color` | (u8,u8,u8) | (0,0,0) | Stroke color |
| `opacity` | f32 | 1.0 | Stroke opacity |
| `position` | str | "outside" | Position: outside, inside, center |
| `expand` | usize | 0 | Extra canvas padding |

**Stroke Positions:**
- **outside**: Stroke expands outward from edges
- **inside**: Stroke contracts inward from edges
- **center**: Stroke straddles the edge

**Contour-based SVG (preferred):**
- Uses `extract_contours()` with `fit_beziers=True`
- Douglas-Peucker simplification: `epsilon=0.05` (very low to preserve hard curves)
- Bezier smoothness: `0.1`
- Native SVG stroke with `stroke-linejoin="round"`, `stroke-linecap="round"`
- Stroke-width adjusted by `/2.0` to match Rust visual output

**TODO:** SVG export needs to handle `expand` parameter for outside position.

---

## JavaScript Implementation Plan

### Shared Template Approach

To ensure Python and JavaScript implementations don't diverge, use a Jinja-like templating system:

```
imagestag/layer_effects/templates/
├── drop_shadow.filter.jinja     # Shared SVG filter template
├── inner_shadow.filter.jinja
├── outer_glow.filter.jinja
├── inner_glow.filter.jinja
├── bevel_emboss.filter.jinja
├── color_overlay.filter.jinja
├── gradient_overlay.defs.jinja
├── pattern_overlay.defs.jinja
└── stroke.filter.jinja
```

### Template Variables

Each template receives:
- Effect parameters (blur, color, opacity, etc.)
- Computed values (scaled blur, hex color, etc.)
- Filter ID for unique naming

### Code Generation

```bash
# Generate Python and JS from templates
python scripts/generate_layer_effects.py --target python
python scripts/generate_layer_effects.py --target javascript
```

### JS Implementation Structure

```javascript
// imagestag/layer_effects/index.js
export class DropShadow extends LayerEffect {
  toSvgFilter(filterId, scale) {
    // Generated from drop_shadow.filter.jinja
    return `<filter id="${filterId}" ...>...</filter>`;
  }
}
```

---

## Cross-Application Comparison

### GIMP Layer Effects

GIMP provides layer effects through:
1. **Built-in filters** (Filters > Light and Shadow):
   - Drop Shadow
   - Inner Glow
2. **Text Styling filter** (Filters > Generic > Text Styling):
   - Outline, Shadow/Glow, Bevel, Inner Glow
3. **Layer-FX plugin**:
   - Full Photoshop-style layer effects

### Affinity Photo Layer Effects

Affinity Photo provides layer effects similar to Photoshop:
- Outer Shadow (Drop Shadow)
- Inner Shadow
- Outer Glow
- Inner Glow
- Bevel/Emboss
- Color Overlay
- Gradient Overlay
- Outline (Stroke)

---

## Testing

### Comparison Script

```bash
poetry run python scripts/generate_effect_samples.py
```

Generates side-by-side comparisons in `tmp/effect_samples/comparisons/`:
- `{effect}_{svg}_comparison.png` - Three-column comparison (Rust, SVG Filter, Baked)
- `{effect}_{svg}.svg` - Generated SVG with filter applied
- `{effect}_{svg}_baked.svg` - SVG with Rust-rendered effect baked as raster image

---

## Baked SVG Export

For 100% fidelity SVG output, effects can be "baked" by embedding the Rust-rendered result directly into the SVG as a raster image. This provides pixel-perfect accuracy at the cost of larger file size and non-scalability.

### Baking Strategies

Effects are baked using one of four strategies based on how they modify the content.
**Key insight**: Most effects preserve the original SVG vector content—only the effect itself is rasterized or rendered as a vector overlay.

| Strategy | Effects | Description |
|----------|---------|-------------|
| **UNDERLAY** | Drop Shadow, Outer Glow | Effect-only layer under vector SVG. Uses dedicated Rust `*_only` functions. |
| **OVERLAY** | Stroke, Inner Glow | Effect-only layer over vector SVG. Uses dedicated Rust `*_only` functions. |
| **SVG_FILTER_ONLY** | Inner Shadow | Cannot be cleanly separated; uses SVG filter only (no baking). |
| **VECTOR_OVERLAY** | Gradient Overlay, Pattern Overlay | Native SVG gradient/pattern with mask. No rasterization at all! |
| **REPLACEMENT** | Color Overlay, Bevel/Emboss, Satin | Full rasterization required (effect modifies pixels). |

### Effect-Only Rust Functions

For clean effect layer extraction without edge artifacts, dedicated Rust functions return ONLY the effect:

| Effect | Function | Description |
|--------|----------|-------------|
| Drop Shadow | `drop_shadow_only_rgba` | Full shadow area (including "under" the object) |
| Outer Glow | `outer_glow_only_rgba` | Full glow area (including "under" the object) |
| Stroke | `stroke_only_rgba` | Stroke mask without original content |
| Inner Glow | `inner_glow_only_rgba` | Glow inside shape without original content |

These functions eliminate edge artifacts that occur when trying to extract effects from composited results.

This approach:
1. Eliminates edge glow artifacts that occur with soft alpha blending
2. Keeps original SVG vector paths sharp when zoomed
3. Only rasterizes the effect layer, not the content

### Baked SVG Structure

```xml
<!-- UNDERLAY: Effect-only layer under vector content -->
<svg viewBox="-14 -14 157 157"> <!-- viewBox expanded for shadow -->
  <!-- Baked shadow/glow layer (hard-masked, no edge glow) -->
  <image href="data:image/png;base64,..." width="157" height="157"/>
  <!-- Original SVG vector content (stays sharp when zoomed) -->
  <path d="M73.99,78.07L62.3,83.14..." fill="#8A5B51"/>
</svg>

<!-- OVERLAY: Vector content under effect-only layer -->
<svg viewBox="-2 -2 132 132"> <!-- viewBox expanded for stroke -->
  <!-- Original SVG vector content (stays sharp when zoomed) -->
  <path d="M73.99,78.07L62.3,83.14..." fill="#8A5B51"/>
  <!-- Baked effect layer (stroke/inner shadow/inner glow) -->
  <image href="data:image/png;base64,..." width="132" height="132"/>
</svg>

<!-- VECTOR_OVERLAY: Native SVG gradient/pattern (no rasterization!) -->
<svg viewBox="0 0 128 128">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#323296"/>
      <stop offset="100%" stop-color="#C89632"/>
    </linearGradient>
    <mask id="mask">...</mask>
  </defs>
  <!-- Original SVG vector content -->
  <path d="M73.99,78.07..." fill="#8A5B51"/>
  <!-- Native SVG gradient overlay (vector, stays sharp!) -->
  <rect fill="url(#grad)" mask="url(#mask)" opacity="0.8"/>
</svg>

<!-- REPLACEMENT: Full rasterization (effect modifies pixels) -->
<svg viewBox="0 0 128 128">
  <image href="data:image/png;base64,..." width="128" height="128"/>
</svg>
```

### Usage

```python
from imagestag.layer_effects import DropShadow
import numpy as np

# Render original and apply effect
original_image = render_svg(svg_content)  # Your SVG renderer
effect = DropShadow(blur=5, color=(0, 0, 0))
result = effect.apply(original_image)

# Create baked SVG (preserves vector content for UNDERLAY/OVERLAY effects)
from scripts.generate_effect_samples import create_baked_svg

baked_svg = create_baked_svg(
    svg_content,           # Original SVG string
    effect,                # Effect instance (determines strategy)
    result.image,          # Rust-rendered result
    original_image,        # Original without effect
    render_size=300,       # Render size in pixels
    offset_x=result.offset_x,  # Canvas expansion offset
    offset_y=result.offset_y,
)
```

### Trade-offs

| Approach | Fidelity | File Size | Scalability | Use Case |
|----------|----------|-----------|-------------|----------|
| **SVG Filters** | 70-100% | Small | Vector | Web, editing |
| **Baked SVG** | 100% | Large | Raster | Archival, print |

For most use cases, SVG filters are preferred. Use baked SVG when exact visual match is required and file size is not a concern.

### Fidelity Metrics

Visual comparison targets:
- **100%**: Pixel-perfect match
- **95%+**: Excellent - minor edge differences
- **85-94%**: Good - noticeable but acceptable differences
- **70-84%**: Approximation - different algorithm, similar visual result
- **<70%**: Poor - significant visual differences

---

## Sources

- [GIMP 3.0 Documentation - Drop Shadow](https://docs.gimp.org/3.0/en/gimp-filter-drop-shadow.html)
- [GIMP 3.0 Documentation - Inner Glow](https://docs.gimp.org/3.0/en/gegl-inner-glow.html)
- [GIMP 3.0 Documentation - Text Styling](https://docs.gimp.org/3.0/en/gegl-styles.html)
- [Layer-FX 2.10 Plugin](https://www.gimpscripts.net/2020/09/new-layer-modes-with-layer-fx-210.html)
- [SVG Filter Effects](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/filter)
- [SVG feGaussianBlur](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/feGaussianBlur)
- [SVG feMorphology](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/feMorphology)
