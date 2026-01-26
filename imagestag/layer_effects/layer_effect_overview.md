# Layer Effects Overview

Layer effects (Photoshop-style "Layer Styles") are non-destructive visual effects that work with the alpha channel to create shadows, glows, bevels, overlays, and strokes.

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

**Cross-platform:** Photoshop, GIMP, Affinity Photo

---

### 2. INNER SHADOW

Creates a shadow inside the layer edges.

**Rust file:** `rust/src/layer_effects/lighting.rs`

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

**Cross-platform:** Photoshop, GIMP (plugin), Affinity Photo

---

### 3. OUTER GLOW

Creates a glow effect radiating outward from layer edges.

**Rust file:** `rust/src/layer_effects/lighting.rs`

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

**Cross-platform:** Photoshop, GIMP (Filter > Light and Shadow > Inner Glow), Affinity Photo

---

### 4. INNER GLOW

Creates a glow effect radiating inward from layer edges.

**Rust file:** `rust/src/layer_effects/lighting.rs`

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

**Cross-platform:** Photoshop, GIMP (built-in), Affinity Photo

---

### 5. BEVEL & EMBOSS

Creates a 3D raised or sunken appearance.

**Rust file:** `rust/src/layer_effects/lighting.rs`

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

**Algorithm:**
1. Compute gradient (bump map) of alpha channel
2. Blur bump map for smoothness
3. Calculate lighting intensity from angle
4. Apply highlights (positive intensity) and shadows (negative intensity)

**Cross-platform:** Photoshop, GIMP (Filters > Generic > Text Styling), Affinity Photo

---

### 6. SATIN

Creates silky interior shading.

**Rust file:** `rust/src/layer_effects/satin.rs`

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

**Cross-platform:** Photoshop (exclusive feature), GIMP (Layer-FX plugin)

---

### 7. COLOR OVERLAY

Fills the layer with a solid color while preserving alpha.

**Rust file:** `rust/src/layer_effects/lighting.rs`

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `color` | (u8,u8,u8) | (255,0,0) | Overlay color |
| `opacity` | f32 | 1.0 | Overlay opacity |

**Algorithm:**
1. Linear blend between original color and overlay color
2. Preserve original alpha

**Cross-platform:** Photoshop, GIMP, Affinity Photo

---

### 8. GRADIENT OVERLAY

Fills the layer with a gradient while preserving alpha.

**Rust file:** `rust/src/layer_effects/gradient_overlay.rs`

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
- **linear**: Straight gradient at specified angle
- **radial**: Circular gradient from center outward
- **angle**: Sweep around center point
- **reflected**: Linear gradient mirrored at center
- **diamond**: Diamond-shaped gradient from center

**Cross-platform:** Photoshop, GIMP (partial), Affinity Photo

---

### 9. PATTERN OVERLAY

Fills the layer with a tiled pattern while preserving alpha.

**Rust file:** `rust/src/layer_effects/pattern_overlay.rs`

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

**Cross-platform:** Photoshop, GIMP (Layer-FX plugin)

---

### 10. STROKE

Creates an outline around layer content.

**Rust file:** `rust/src/layer_effects/stroke.rs`

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

**Algorithm:**
1. Extract alpha channel
2. Create stroke mask based on position:
   - Outside: dilate - original
   - Inside: original - erode
   - Center: dilate(half) - erode(half)
3. Colorize stroke mask
4. Composite appropriately

**Cross-platform:** Photoshop, GIMP, Affinity Photo

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

**GIMP Drop Shadow Parameters:**
| Parameter | Type | Range | Default |
|-----------|------|-------|---------|
| X, Y | pixels | - | - |
| Blur radius | pixels | - | - |
| Grow shape | enum | Circle, Square, Diamond | Circle |
| Grow radius | pixels | (can be negative) | - |
| Color | color | any | - |
| Opacity | float | 0-2.0 | 0.5 |

**GIMP Inner Glow Parameters:**
| Parameter | Type | Range | Default |
|-----------|------|-------|---------|
| X, Y | pixels | - | - |
| Blur radius | pixels | - | - |
| Grow shape | enum | Circle, Square, Diamond | Circle |
| Grow radius | pixels | (can be negative) | - |
| Color | color | any | foreground |
| Opacity | float | - | - |

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

## Sources

- [GIMP 3.0 Documentation - Drop Shadow](https://docs.gimp.org/3.0/en/gimp-filter-drop-shadow.html)
- [GIMP 3.0 Documentation - Inner Glow](https://docs.gimp.org/3.0/en/gegl-inner-glow.html)
- [GIMP 3.0 Documentation - Text Styling](https://docs.gimp.org/3.0/en/gegl-styles.html)
- [Layer-FX 2.10 Plugin](https://www.gimpscripts.net/2020/09/new-layer-modes-with-layer-fx-210.html)
