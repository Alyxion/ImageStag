# SVG Filter & Effect Compatibility Analysis

This document maps Stagforge layer effects and JavaScript filters to their SVG equivalents, documenting fidelity levels for SVG export.

---

## Part 1: Layer Effects → SVG Mapping

### Summary Table

| Effect | SVG Equivalent | Fidelity | Pre-Render | Notes |
|--------|---------------|----------|------------|-------|
| Drop Shadow | `<feDropShadow>` | **100%** | - | Native SVG support |
| Inner Shadow | Composite filter | **95%** | - | Requires filter chain |
| Outer Glow | Composite filter | **90%** | - | Blur + composite, spread differs |
| Inner Glow | Composite filter | **85%/60%** | **85%** | Edge mode good, center mode needs pre-render |
| Bevel & Emboss | Lighting filters | **70%** | **80-85%** | Pre-render enables highlight/shadow separation |
| Stroke | Morphology + flood | **80%** | **95%** | Center position needs pre-render |
| Color Overlay | `<feFlood>` + `<feComposite>` | **100%** | - | Full support |

---

### Detailed Effect Analysis

#### 1. DROP SHADOW - Full Support

**Stagforge Parameters:**
- `offsetX`, `offsetY`: Shadow offset
- `blur`: Blur radius (Gaussian sigma)
- `spread`: Expansion before blur
- `color`: Shadow color
- `colorOpacity`: Shadow opacity

**SVG Equivalent:**
```xml
<filter id="dropShadow">
  <feDropShadow dx="4" dy="4" stdDeviation="5" flood-color="#000000" flood-opacity="0.75"/>
</filter>
```

**Limitations:**
- SVG `<feDropShadow>` doesn't have `spread` parameter
- Workaround: Use `<feMorphology operator="dilate">` before blur for spread effect
- **Fidelity: 100%** (with spread workaround)

---

#### 2. INNER SHADOW - Composite Filter Required

**Stagforge Parameters:**
- `offsetX`, `offsetY`: Shadow offset
- `blur`: Blur radius
- `choke`: Contraction factor
- `color`: Shadow color

**SVG Equivalent:**
```xml
<filter id="innerShadow">
  <!-- Create inverted alpha mask -->
  <feComponentTransfer in="SourceAlpha" result="inverted">
    <feFuncA type="table" tableValues="1 0"/>
  </feComponentTransfer>
  <!-- Offset the inverted mask -->
  <feOffset dx="2" dy="2" in="inverted" result="offsetInverted"/>
  <!-- Blur it -->
  <feGaussianBlur stdDeviation="5" in="offsetInverted" result="blurred"/>
  <!-- Clip to original shape -->
  <feComposite in="blurred" in2="SourceAlpha" operator="in" result="shadow"/>
  <!-- Colorize -->
  <feFlood flood-color="#000000" flood-opacity="0.75" result="color"/>
  <feComposite in="color" in2="shadow" operator="in" result="coloredShadow"/>
  <!-- Merge with source -->
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="coloredShadow"/>
  </feMerge>
</filter>
```

**Limitations:**
- `choke` parameter requires additional `<feMorphology operator="erode">` step
- Complex filter chain, but achievable
- **Fidelity: 95%**

---

#### 3. OUTER GLOW - Composite Filter Required

**Stagforge Parameters:**
- `blur`: Glow radius
- `spread`: Expansion before blur
- `color`: Glow color
- `colorOpacity`: Glow opacity

**SVG Equivalent:**
```xml
<filter id="outerGlow">
  <!-- Optional spread with morphology -->
  <feMorphology operator="dilate" radius="2" in="SourceAlpha" result="spread"/>
  <!-- Blur the spread result -->
  <feGaussianBlur stdDeviation="10" in="spread" result="blurred"/>
  <!-- Colorize -->
  <feFlood flood-color="#FFFF00" flood-opacity="0.75" result="color"/>
  <feComposite in="color" in2="blurred" operator="in" result="glow"/>
  <!-- Put glow behind source -->
  <feMerge>
    <feMergeNode in="glow"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

**Limitations:**
- Works well for basic glows
- Spread implementation slightly different (morphology vs. true spread)
- **Fidelity: 90%**

---

#### 4. INNER GLOW - Complex Composite Filter

**Stagforge Parameters:**
- `blur`: Glow radius
- `choke`: Contraction factor
- `color`: Glow color
- `source`: 'edge' or 'center'

**SVG Equivalent (edge source):**
```xml
<filter id="innerGlowEdge">
  <!-- Create edge mask by subtracting eroded from original -->
  <feMorphology operator="erode" radius="5" in="SourceAlpha" result="eroded"/>
  <feComposite in="SourceAlpha" in2="eroded" operator="out" result="edge"/>
  <!-- Blur the edge -->
  <feGaussianBlur stdDeviation="5" in="edge" result="blurredEdge"/>
  <!-- Clip to original alpha -->
  <feComposite in="blurredEdge" in2="SourceAlpha" operator="in" result="clipped"/>
  <!-- Colorize -->
  <feFlood flood-color="#FFFF00" flood-opacity="0.75" result="color"/>
  <feComposite in="color" in2="clipped" operator="in" result="glow"/>
  <!-- Composite over source -->
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="glow"/>
  </feMerge>
</filter>
```

**Limitations:**
- 'center' source mode is very different (radial gradient from center) - hard to replicate
- Choke requires additional erosion step
- **Fidelity: 85%** (edge mode), **60%** (center mode)

**Pre-Rendering Enhancement for Center Mode:**

Pre-rendering with resvg allows detection of the shape's geometric center:

1. Render SVG to extract alpha mask
2. Calculate shape centroid (center of mass)
3. Measure maximum distance from centroid to edge
4. Generate positioned `<radialGradient>` at computed coordinates

```xml
<!-- Pre-computed: centroid at (150, 200), max radius 80px -->
<defs>
  <radialGradient id="innerGlowCenter" cx="150" cy="200" r="80"
                  gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#FFFF00" stop-opacity="0.75"/>
    <stop offset="100%" stop-color="#FFFF00" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect fill="url(#innerGlowCenter)" ... />
```

**Fidelity with Pre-Render: 85%** (center mode improved from 60%)

---

#### 5. BEVEL & EMBOSS - Approximation Only

**Stagforge Parameters:**
- `style`: innerBevel, outerBevel, emboss, pillowEmboss
- `depth`, `size`, `soften`
- `angle`, `altitude`: Light source
- `highlightColor`, `highlightOpacity`
- `shadowColor`, `shadowOpacity`

**SVG Approach - Using Lighting Filters:**
```xml
<filter id="bevelEmboss">
  <!-- Create bump map from alpha -->
  <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="blur"/>
  <!-- Apply specular lighting -->
  <feSpecularLighting in="blur" surfaceScale="5" specularConstant="1"
                      specularExponent="20" lighting-color="white" result="specular">
    <feDistantLight azimuth="120" elevation="30"/>
  </feSpecularLighting>
  <!-- Composite with source -->
  <feComposite in="specular" in2="SourceAlpha" operator="in" result="lit"/>
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="lit"/>
  </feMerge>
</filter>
```

**Limitations:**
- SVG lighting is fundamentally different from Photoshop-style bevel
- No direct support for highlight/shadow color separation
- Different visual appearance, especially for emboss/pillow styles
- `feSpecularLighting` / `feDiffuseLighting` create a different look
- **Fidelity: 70%** - Approximation only, won't look identical

**Pre-Rendering Enhancement:**

Pre-rendering allows extraction of highlight and shadow regions as separate masks, bypassing SVG lighting limitations:

1. Render SVG to extract alpha silhouette
2. Pre-compute highlight regions (edges facing the light source based on `angle`)
3. Pre-compute shadow regions (edges facing away from light)
4. Generate separate flood+composite filters for each, with proper colors

```xml
<filter id="bevelPrecomputed">
  <!-- Pre-computed highlight mask as embedded image -->
  <feImage xlink:href="data:image/png;base64,..." result="highlightMask"/>
  <feFlood flood-color="#FFFFFF" flood-opacity="0.75" result="highlight"/>
  <feComposite in="highlight" in2="highlightMask" operator="in" result="highlightLayer"/>

  <!-- Pre-computed shadow mask as embedded image -->
  <feImage xlink:href="data:image/png;base64,..." result="shadowMask"/>
  <feFlood flood-color="#000000" flood-opacity="0.75" result="shadow"/>
  <feComposite in="shadow" in2="shadowMask" operator="in" result="shadowLayer"/>

  <!-- Combine with source -->
  <feMerge>
    <feMergeNode in="SourceGraphic"/>
    <feMergeNode in="shadowLayer"/>
    <feMergeNode in="highlightLayer"/>
  </feMerge>
</filter>
```

This enables proper highlight/shadow color separation which native SVG lighting cannot achieve.

**Fidelity with Pre-Render: 80-85%** (improved from 70%)

---

#### 6. STROKE - Partial Support

**Stagforge Parameters:**
- `size`: Stroke width
- `position`: 'inside', 'outside', 'center'
- `color`: Stroke color

**SVG Equivalent (outside stroke):**
```xml
<filter id="strokeOutside">
  <!-- Dilate alpha by stroke size -->
  <feMorphology operator="dilate" radius="3" in="SourceAlpha" result="dilated"/>
  <!-- Subtract original to get stroke only -->
  <feComposite in="dilated" in2="SourceAlpha" operator="out" result="strokeMask"/>
  <!-- Colorize -->
  <feFlood flood-color="#000000" result="color"/>
  <feComposite in="color" in2="strokeMask" operator="in" result="stroke"/>
  <!-- Combine -->
  <feMerge>
    <feMergeNode in="stroke"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

**Limitations:**
- **Outside**: Works well with morphology
- **Inside**: Requires erosion + "out" composite - works
- **Center**: Complex - half inside, half outside
- Morphology radius is integer-only in SVG (no sub-pixel strokes)
- **Fidelity: 80%**

**Pre-Rendering Enhancement for Center Stroke:**

Pre-rendering allows precise boundary detection for center-positioned strokes:

1. Render SVG to detect exact shape boundary
2. Generate two separate strokes:
   - Inside stroke at half-width (erode + out composite)
   - Outside stroke at half-width (dilate + out composite)
3. Combine both strokes

```xml
<filter id="strokeCenter">
  <!-- Inside half (erode by half stroke width) -->
  <feMorphology operator="erode" radius="2" in="SourceAlpha" result="eroded"/>
  <feComposite in="SourceAlpha" in2="eroded" operator="out" result="insideMask"/>

  <!-- Outside half (dilate by half stroke width) -->
  <feMorphology operator="dilate" radius="2" in="SourceAlpha" result="dilated"/>
  <feComposite in="dilated" in2="SourceAlpha" operator="out" result="outsideMask"/>

  <!-- Combine both halves -->
  <feMerge result="strokeMask">
    <feMergeNode in="insideMask"/>
    <feMergeNode in="outsideMask"/>
  </feMerge>

  <!-- Colorize -->
  <feFlood flood-color="#000000" result="color"/>
  <feComposite in="color" in2="strokeMask" operator="in" result="stroke"/>

  <!-- Final composite -->
  <feMerge>
    <feMergeNode in="stroke"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

**Fidelity with Pre-Render: 95%** (center position improved from ~70%)

---

#### 7. COLOR OVERLAY - Full Support

**Stagforge Parameters:**
- `color`: Overlay color
- `opacity`: Effect opacity
- `blendMode`: Blend mode

**SVG Equivalent:**
```xml
<filter id="colorOverlay">
  <feFlood flood-color="#FF0000" flood-opacity="1" result="color"/>
  <feComposite in="color" in2="SourceAlpha" operator="in" result="overlay"/>
  <feBlend in="overlay" in2="SourceGraphic" mode="normal"/>
</filter>
```

**Limitations:**
- Full support including blend modes
- **Fidelity: 100%**

---

### Summary: Layer Effects Enhanced by Pre-Rendering

Pre-rendering with resvg enables extraction of shape geometry that native SVG filters cannot access:

| Effect | Without Pre-Render | With Pre-Render | What We Extract |
|--------|-------------------|-----------------|-----------------|
| Inner Glow (center) | 60% | **85%** | Shape centroid + max radius |
| Bevel & Emboss | 70% | **80-85%** | Highlight/shadow edge masks |
| Stroke (center) | ~70% | **95%** | Exact boundary for split strokes |

**When Pre-Rendering is Justified for Effects:**

| Effect | Justification |
|--------|---------------|
| Inner Glow (center mode) | Only way to position radial gradient at shape center |
| Bevel & Emboss | Only way to achieve separate highlight/shadow colors |
| Stroke (center) | Enables precise half-in/half-out stroke |

**Effects That Do NOT Need Pre-Rendering:**
- Drop Shadow (native `<feDropShadow>`)
- Inner Shadow (composite filter works well)
- Outer Glow (morphology + blur works well)
- Inner Glow (edge mode) (composite filter works well)
- Color Overlay (native support)
- Stroke (inside/outside) (morphology works well)

### Additional Capabilities from Shape Detection

Pre-rendering enables extraction of geometric information beyond simple pixel data:

| Data Extracted | Use Case | SVG Application |
|----------------|----------|-----------------|
| **Alpha silhouette** | Shape boundary mask | Precise `<clipPath>` elements |
| **Centroid** | Shape center of mass | Position radial gradients, glow centers |
| **Bounding box** | Shape extents | Gradient sizing, effect boundaries |
| **Edge contours** | Shape outlines | Stroke positioning, highlight/shadow regions |
| **Average color** | Dominant hue | Smart effect color defaults |
| **Luminance map** | Tonal distribution | Shadow/midtone/highlight separation |

**Contour-Aware Effects:**

With extracted contours, effects can be positioned relative to shape geometry rather than relying on filter approximations:

```xml
<!-- Contour extracted as path, allows precise gradient positioning -->
<path id="shapeContour" d="M10,10 L100,10 L100,80 L10,80 Z"/>
<use href="#shapeContour" fill="url(#preciseGradient)"/>
```

This enables:
- Gradients that follow shape direction (not just axis-aligned)
- Strokes with accurate corner handling
- Effects positioned at specific contour points

---

## Part 2: JavaScript Filters → SVG Mapping

### Summary Table

| Filter | SVG Equivalent | Fidelity | Pre-Compute | Notes |
|--------|---------------|----------|-------------|-------|
| **COLOR ADJUSTMENT** | | | | |
| brightness | `<feComponentTransfer>` | 100% | - | Linear transfer |
| contrast | `<feComponentTransfer>` | 100% | - | Linear transfer |
| saturation | `<feColorMatrix>` | 100% | - | saturate type |
| gamma | `<feComponentTransfer>` | 100% | - | gamma type |
| exposure | `<feComponentTransfer>` | 100% | - | Combined transfer |
| invert | `<feColorMatrix>` | 100% | - | Or feComponentTransfer |
| **COLOR SCIENCE** | | | | |
| hue_shift | `<feColorMatrix>` | 100% | - | hueRotate type |
| vibrance | None | 0% | **70%** | Pre-compute avg saturation |
| color_balance | `<feColorMatrix>` | 70% | **95%** | Pre-compute tone thresholds |
| **LEVELS & CURVES** | | | | |
| levels | `<feComponentTransfer>` | 100% | - | table/linear type |
| curves | `<feComponentTransfer>` | 95% | **100%** | Optimal discretization |
| auto_levels | None | 0% | **100%** | Pre-compute histogram |
| **EDGE DETECTION** | | | | |
| sobel | `<feConvolveMatrix>` | 100% | - | 3x3 kernel |
| laplacian | `<feConvolveMatrix>` | 100% | - | 3x3 or 5x5 kernel |
| find_edges | `<feConvolveMatrix>` | 80% | - | Canny requires multi-step |
| **BLUR** | | | | |
| motion_blur | `<feConvolveMatrix>` | 70% | - | Approximation with kernel |
| gaussian_blur | `<feGaussianBlur>` | 100% | - | Native support |
| **SHARPENING** | | | | |
| sharpen | `<feConvolveMatrix>` | 100% | - | 3x3 sharpen kernel |
| unsharp_mask | Composite | 90% | **95%** | Fine-tune kernel |
| high_pass | Composite | 85% | - | Blur + subtract |
| **NOISE** | | | | |
| add_noise | `<feTurbulence>` | 60% | - | Different noise type |
| median | None | 0% | 0% | Spatial - impossible |
| denoise | None | 0% | 0% | Complex - impossible |
| **STYLISTIC** | | | | |
| posterize | `<feComponentTransfer>` | 100% | - | discrete type |
| solarize | `<feComponentTransfer>` | 100% | - | table type |
| threshold | `<feComponentTransfer>` | 100% | - | discrete type |
| emboss | `<feConvolveMatrix>` | 100% | - | 3x3 emboss kernel |
| **MORPHOLOGY** | | | | |
| dilate | `<feMorphology>` | 100% | - | dilate operator |
| erode | `<feMorphology>` | 100% | - | erode operator |
| **BASIC** | | | | |
| grayscale | `<feColorMatrix>` | 100% | - | luminanceToAlpha or matrix |

---

### Detailed Filter Analysis

#### Fully Supported Filters (100% Fidelity)

**1. Brightness** - `<feComponentTransfer>` with linear slope
```xml
<feComponentTransfer>
  <feFuncR type="linear" slope="1.5" intercept="0"/>
  <feFuncG type="linear" slope="1.5" intercept="0"/>
  <feFuncB type="linear" slope="1.5" intercept="0"/>
</feComponentTransfer>
```

**2. Contrast** - `<feComponentTransfer>` with linear slope + intercept
```xml
<feComponentTransfer>
  <feFuncR type="linear" slope="1.5" intercept="-0.25"/>
  <feFuncG type="linear" slope="1.5" intercept="-0.25"/>
  <feFuncB type="linear" slope="1.5" intercept="-0.25"/>
</feComponentTransfer>
```

**3. Saturation** - `<feColorMatrix type="saturate">`
```xml
<feColorMatrix type="saturate" values="1.5"/>
```

**4. Hue Shift** - `<feColorMatrix type="hueRotate">`
```xml
<feColorMatrix type="hueRotate" values="90"/>
```

**5. Grayscale** - `<feColorMatrix>`
```xml
<feColorMatrix type="matrix" values="0.2126 0.7152 0.0722 0 0
                                      0.2126 0.7152 0.0722 0 0
                                      0.2126 0.7152 0.0722 0 0
                                      0 0 0 1 0"/>
```

**6. Invert** - `<feComponentTransfer>`
```xml
<feComponentTransfer>
  <feFuncR type="table" tableValues="1 0"/>
  <feFuncG type="table" tableValues="1 0"/>
  <feFuncB type="table" tableValues="1 0"/>
</feComponentTransfer>
```

**7. Posterize** - `<feComponentTransfer type="discrete">`
```xml
<feComponentTransfer>
  <feFuncR type="discrete" tableValues="0 0.25 0.5 0.75 1"/>
  <feFuncG type="discrete" tableValues="0 0.25 0.5 0.75 1"/>
  <feFuncB type="discrete" tableValues="0 0.25 0.5 0.75 1"/>
</feComponentTransfer>
```

**8. Threshold** - `<feComponentTransfer type="discrete">`
```xml
<feComponentTransfer>
  <feFuncR type="discrete" tableValues="0 1"/>
  <feFuncG type="discrete" tableValues="0 1"/>
  <feFuncB type="discrete" tableValues="0 1"/>
</feComponentTransfer>
```

**9. Levels/Gamma** - `<feComponentTransfer>`
```xml
<feComponentTransfer>
  <feFuncR type="gamma" amplitude="1" exponent="2.2" offset="0"/>
  <feFuncG type="gamma" amplitude="1" exponent="2.2" offset="0"/>
  <feFuncB type="gamma" amplitude="1" exponent="2.2" offset="0"/>
</feComponentTransfer>
```

**10. Edge Detection (Sobel/Laplacian)** - `<feConvolveMatrix>`
```xml
<!-- Sobel horizontal -->
<feConvolveMatrix order="3" kernelMatrix="-1 0 1 -2 0 2 -1 0 1"/>
<!-- Laplacian -->
<feConvolveMatrix order="3" kernelMatrix="0 -1 0 -1 4 -1 0 -1 0"/>
```

**11. Sharpen** - `<feConvolveMatrix>`
```xml
<feConvolveMatrix order="3" kernelMatrix="0 -1 0 -1 5 -1 0 -1 0"/>
```

**12. Emboss** - `<feConvolveMatrix>`
```xml
<feConvolveMatrix order="3" kernelMatrix="-2 -1 0 -1 1 1 0 1 2"/>
```

**13. Dilate/Erode** - `<feMorphology>`
```xml
<feMorphology operator="dilate" radius="2"/>
<feMorphology operator="erode" radius="2"/>
```

---

#### Filters with No SVG Equivalent (0% Fidelity)

| Filter | Reason |
|--------|--------|
| **vibrance** | Requires analyzing each pixel's saturation and applying variable boost |
| **auto_levels** | Requires histogram analysis of the entire image |
| **median** | No median filter primitive in SVG |
| **denoise** | Complex non-local means algorithm, not possible in SVG |

---

#### Filters with Partial Support

**Motion Blur (70%)**: SVG has no native motion blur. Can approximate with elongated kernel:
```xml
<feConvolveMatrix order="1 9" kernelMatrix="0.11 0.11 0.11 0.11 0.11 0.11 0.11 0.11 0.11"/>
```
But this is axis-aligned only. Angled motion blur requires rotation transforms.

**Add Noise (60%)**: SVG `<feTurbulence>` generates Perlin/fractal noise, not uniform/Gaussian noise:
```xml
<feTurbulence type="fractalNoise" baseFrequency="0.5" numOctaves="4"/>
```
Different character than our noise filter.

**Color Balance (70%)**: SVG can apply matrix transforms but can't separate shadows/midtones/highlights without complex masking.

---

## Part 3: Pre-Computation Enhanced Filters

**IMPORTANT: Pre-computation should be the LAST RESORT.**

Pre-computation has significant drawbacks:
- **Increased export size** - embedded parameters/data bloat the SVG
- **Lost scalability** - SVG can no longer scale to higher resolutions cleanly
- **Breaks resolution independence** - the core benefit of vector graphics

**Priority Order for SVG Filter Implementation:**
1. **Native SVG filters** (best) - resolution independent, small, scalable
2. **Composite SVG filter chains** (good) - still vector, resolution independent
3. **Pre-computation** (last resort) - only when no other option exists

---

### Pre-Computation Approach

When a filter absolutely cannot be represented with native SVG primitives, pre-computation may be used:

**Workflow:**
1. Pre-render SVG at 4x or higher resolution using resvg
2. Analyze the rendered bitmap to extract:
   - **Histogram** (per-channel color distribution)
   - **Alpha silhouette** (shape boundary mask)
   - **Luminance map** (for tone separation)
   - **Saturation map** (per-pixel saturation values)
3. Store computed parameters in SVG metadata (sf:filter-params)
4. Generate SVG filter with pre-computed values

### Summary: Filters Enhanced by Pre-Computation

| Filter | Without Pre-Compute | With Pre-Compute | Enhancement |
|--------|---------------------|------------------|-------------|
| auto_levels | 0% | **100%** | Pre-compute histogram -> levels params |
| vibrance | 0% | **70%** | Pre-compute saturation map -> LUT |
| color_balance | 70% | **95%** | Pre-compute luminance -> tone masks |
| curves | 95% | **100%** | Pre-compute exact table values |
| unsharp_mask | 90% | **95%** | Fine-tune kernel from content |
| median | 0% | 0% | Still impossible - spatial operation |
| denoise | 0% | 0% | Still impossible - complex algorithm |

---

### Detailed Pre-Computation Analysis

#### 1. AUTO_LEVELS - Full Support with Pre-Computation

**Current Issue:** Requires histogram analysis of the entire image to determine black/white points.

**Pre-Computation Solution:**
1. Render SVG via resvg
2. Compute histogram, find 0.1% and 99.9% percentiles per channel
3. Calculate input/output mapping: `inputBlack`, `inputWhite` per channel
4. Generate `<feComponentTransfer>` with exact `slope` and `intercept`

**SVG Output:**
```xml
<!-- Pre-computed from histogram analysis -->
<feComponentTransfer>
  <feFuncR type="linear" slope="1.23" intercept="-0.05"/>
  <feFuncG type="linear" slope="1.18" intercept="-0.02"/>
  <feFuncB type="linear" slope="1.31" intercept="-0.08"/>
</feComponentTransfer>
```

**Fidelity: 100%** - Exact same result as runtime analysis

---

#### 2. VIBRANCE - Partial Support with Pre-Computation

**Current Issue:** Requires per-pixel saturation analysis - pixels with low saturation get boosted more.

**Pre-Computation Solution:**
1. Render SVG via resvg
2. For each pixel, compute current saturation
3. Create 256-entry lookup table mapping input saturation -> output saturation
4. Apply via `<feComponentTransfer>` on HSL or approximate with color matrix

**Limitation:** SVG doesn't have native HSL color space operations. Must approximate with RGB color matrix, which is less accurate for complex saturation curves.

**SVG Approximation:**
```xml
<!-- Approximate vibrance boost via saturation matrix -->
<!-- Pre-computed average boost based on image analysis -->
<feColorMatrix type="saturate" values="1.35"/>
```

**Fidelity: 70%** - Uniform saturation boost approximates vibrance but isn't identical

---

#### 3. COLOR_BALANCE - Near-Full Support with Pre-Computation

**Current Issue:** Needs to apply different adjustments to shadows/midtones/highlights based on luminance.

**Pre-Computation Solution:**
1. Render SVG via resvg
2. Compute luminance histogram, determine shadow/midtone/highlight thresholds
3. Generate three color matrices with blend masks

**SVG with Tone Separation:**
```xml
<filter id="colorBalance">
  <!-- Extract luminance -->
  <feColorMatrix type="matrix" in="SourceGraphic"
    values="0.2126 0.7152 0.0722 0 0
            0.2126 0.7152 0.0722 0 0
            0.2126 0.7152 0.0722 0 0
            0 0 0 1 0" result="luma"/>

  <!-- Shadow mask (dark pixels) - threshold from pre-computation -->
  <feComponentTransfer in="luma" result="shadowMask">
    <feFuncR type="table" tableValues="1 1 0.5 0 0 0 0 0"/>
    <feFuncG type="table" tableValues="1 1 0.5 0 0 0 0 0"/>
    <feFuncB type="table" tableValues="1 1 0.5 0 0 0 0 0"/>
  </feComponentTransfer>

  <!-- Apply shadow color shift -->
  <feColorMatrix type="matrix" in="SourceGraphic" result="shadowAdjusted"
    values="1.1 0 0 0 0
            0 1.0 0 0 0
            0 0 0.9 0 0
            0 0 0 1 0"/>

  <!-- Blend based on mask -->
  <feComposite in="shadowAdjusted" in2="shadowMask" operator="in" result="shadows"/>
  <!-- ... similar for midtones and highlights ... -->
  <feMerge>
    <feMergeNode in="shadows"/>
    <feMergeNode in="midtones"/>
    <feMergeNode in="highlights"/>
  </feMerge>
</filter>
```

**Fidelity: 95%** - Tone separation works with pre-computed thresholds

---

#### 4. CURVES - Full Support with Pre-Computation

**Current Issue:** Curves discretization to table values may not be optimal without knowing the actual value distribution.

**Pre-Computation Solution:**
1. Analyze histogram to find which value ranges are most populated
2. Use more table entries in populated ranges for better precision
3. Generate optimized `tableValues` with variable density

**Fidelity: 100%** - Optimal discretization from content analysis

---

### Filters Still Impossible with Pre-Computation

| Filter | Reason |
|--------|--------|
| **median** | Spatial non-linear filter. Each output pixel depends on neighborhood sorting. No SVG primitive can replicate this - would need per-pixel pre-computation which defeats the purpose. |
| **denoise** | Non-local means algorithm compares pixel neighborhoods across the image. Cannot be represented as a static filter. |
| **add_noise** (true random) | SVG `<feTurbulence>` generates deterministic Perlin noise. True random noise would need pre-generated noise texture as `<feImage>`. |

---

### Implementation Notes

**Metadata Storage:**
```xml
<svg xmlns:sf="https://stagforge.io/svg">
  <defs>
    <filter id="autoLevels" sf:precomputed="true" sf:source-hash="abc123">
      <sf:params>
        {"histogram": {"r": [...], "g": [...], "b": [...]},
         "blackPoint": {"r": 5, "g": 8, "b": 3},
         "whitePoint": {"r": 248, "g": 251, "b": 250}}
      </sf:params>
      <feComponentTransfer>...</feComponentTransfer>
    </filter>
  </defs>
</svg>
```

**Invalidation:**
- Store content hash (`sf:source-hash`) with pre-computed filter
- If SVG content changes, pre-computed params become invalid
- Re-render and re-compute on next export

---

## Recommendations

### Priority Order (Resolution Independence is Key)

**Always prefer solutions that maintain SVG scalability:**

| Priority | Approach | Scalable | Size Impact | Use When |
|----------|----------|----------|-------------|----------|
| 1st | Native SVG filter | Yes | Minimal | Filter has direct SVG equivalent |
| 2nd | Composite filter chain | Yes | Small | Can build from SVG primitives |
| 3rd | Accept approximation | Yes | Small | 70%+ fidelity acceptable |
| 4th | Store params only | Yes | Tiny | Re-apply on load |
| **Last** | Pre-computation | No | Large | No other option exists |

### For Layer Effects in SVG Export:

1. **Use native SVG filters** for: Drop Shadow, Color Overlay
2. **Generate composite filters** for: Inner Shadow, Outer Glow, Inner Glow (edge), Stroke (outside/inside)
3. **Use pre-rendering** for: Inner Glow (center), Bevel & Emboss, Stroke (center)
4. **Accept approximation** for: Bevel & Emboss when pre-rendering overhead is unacceptable

**Layer Effect Pre-Rendering Decision Tree:**
```
Is the effect one of: Inner Glow (center), Bevel & Emboss, Stroke (center)?
├── Yes → Pre-render to extract shape geometry
│         Store minimal computed values (centroid, masks)
│         Generate SVG filter with pre-computed parameters
└── No  → Use native SVG or composite filter chain
```

### For Filters Applied to Layers:

Filters modify pixel data permanently, so they're already "baked in" to the layer content when saved. No SVG filter equivalent needed - the filtered pixels are simply exported as PNG data in the `<image>` element.

However, if we wanted to export as **non-destructive SVG filters** (for future editing):
- **22 of 35 filters** have good SVG equivalents (100% or close)
- **9 filters** have partial equivalents (60-90%)
- **4 filters** have no SVG equivalent

### Filters to AVOID Pre-Computation For:

Even though pre-computation is possible, these filters should use their native SVG equivalents or approximations instead:

| Filter | Why Avoid Pre-Computation | Better Alternative |
|--------|---------------------------|-------------------|
| curves | 95% fidelity is acceptable | Use `<feComponentTransfer>` with discretized table |
| unsharp_mask | 90% fidelity is acceptable | Use composite blur + arithmetic |
| color_balance | 70% fidelity often sufficient | Use simple `<feColorMatrix>` |
| vibrance | Consider using saturation instead | `<feColorMatrix type="saturate">` |

### When Pre-Computation MAY Be Justified:

| Filter | Justification |
|--------|---------------|
| auto_levels | **Only option** - histogram analysis cannot be approximated |

Even for auto_levels, consider:
- Storing just the computed `slope`/`intercept` values (tiny overhead)
- NOT embedding full histogram data

---

## Verification

To verify SVG filter fidelity:

1. Create test document with each effect type
2. Export to SVG
3. View in browser and compare visual appearance
4. Document any differences

---

## Related Files

- `stagforge/frontend/js/core/svgExport.js` - SVG export implementation
- `stagforge/frontend/js/core/svgImport.js` - SVG import implementation
- `imagestag/filters/` - Filter implementations
- `imagestag/layer_effects/` - Layer effect implementations
