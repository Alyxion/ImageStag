# Vector Rendering Architecture

## Core Requirement

**All vector graphics MUST be representable as SVG.**

When creating shapes (rectangles, circles, lines, polygons, etc.), temporary visualization with Canvas 2D API is acceptable during editing, but once editing is finished, the actual visual layer representation (rastering to pixels) MUST be done via SVG rendering.

## Why SVG-Based Rendering?

1. **Cross-Platform Parity**: JavaScript and Python must produce identical pixel output
2. **Consistency**: Browser differences in Canvas 2D rendering are eliminated
3. **Serialization**: SVG is a universal interchange format
4. **Print Quality**: SVG can be rendered at any resolution

## Reference Renderers (LOCKED - DO NOT CHANGE)

| Platform | Renderer | Package/Method |
|----------|----------|----------------|
| **JavaScript** | Chrome's native SVG | `<img>` element with SVG blob URL |
| **Python** | resvg | `resvg-py` package |

**These renderers are permanently locked and MUST NOT be substituted:**

- ❌ No resvg-wasm, canvg, or other JS SVG libraries
- ❌ No CairoSVG, librsvg, svglib, or other Python SVG libraries

The goal is to make resvg match Chrome's output, not to find alternative renderers.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Shape Data                                │
│  { type: "rect", x: 10, y: 20, width: 100, height: 50, ... }   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│    JavaScript (Browser)  │   │    Python (Server)       │
├─────────────────────────┤   ├─────────────────────────┤
│ 1. shapes → SVG string   │   │ 1. shapes → SVG string   │
│ 2. SVG → Image element   │   │ 2. SVG → resvg           │
│ 3. Image → Canvas pixels │   │ 3. resvg → PNG → pixels  │
└─────────────────────────┘   └─────────────────────────┘
              │                         │
              └────────────┬────────────┘
                           ▼
              ┌─────────────────────────┐
              │   Identical RGBA Pixels  │
              │   (99.99% match required)│
              └─────────────────────────┘
```

## Shape Types and SVG Mapping

| Shape Type | JS Class | SVG Element | Key Attributes |
|------------|----------|-------------|----------------|
| Rectangle | `RectShape` | `<rect>` | x, y, width, height, rx, ry |
| Ellipse/Circle | `EllipseShape` | `<ellipse>` | cx, cy, rx, ry |
| Line | `LineShape` | `<line>` | x1, y1, x2, y2, stroke-linecap |
| Polygon | `PolygonShape` | `<polygon>` | points |
| Path | `PathShape` | `<path>` | d |

## SVG Generation

Both JavaScript and Python use the same algorithm to convert shapes to SVG:

### JavaScript (`VectorLayer.toSVG()`)
```javascript
toSVG() {
    const elements = this.shapes.map(shape => shape.toSVGElement());
    return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="${this.width}" height="${this.height}"
     viewBox="0 0 ${this.width} ${this.height}">
  ${elements.join('\n  ')}
</svg>`;
}
```

### Python (`slopstag/rendering/vector.py`)
```python
def shapes_to_svg(shapes, width, height):
    elements = [shape_to_svg_element(shape) for shape in shapes]
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}" height="{height}"
     viewBox="0 0 {width} {height}">
  {chr(10).join(elements)}
</svg>'''
```

## SVG Rendering

### JavaScript (Browser)
```javascript
async renderViaSVG() {
    const svg = this.toSVG();
    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    const img = new Image();
    await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = url;
    });

    this.ctx.clearRect(0, 0, this.width, this.height);
    this.ctx.drawImage(img, 0, 0);
    URL.revokeObjectURL(url);
}
```

### Python (resvg)
```python
from resvg_py import svg_to_bytes
from PIL import Image
from io import BytesIO

def render_svg(svg_string, width, height):
    png_bytes = svg_to_bytes(svg_string=svg_string, width=width, height=height)
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    return np.array(img)
```

## Style Attribute Mapping

| Property | Shape Data | SVG Attribute |
|----------|------------|---------------|
| Fill enabled | `fill: true` | `fill="{color}"` |
| Fill disabled | `fill: false` | `fill="none"` |
| Fill color | `fillColor: "#FF0000"` | `fill="#FF0000"` |
| Stroke enabled | `stroke: true` | `stroke="{color}"` |
| Stroke disabled | `stroke: false` | `stroke="none"` |
| Stroke color | `strokeColor: "#000"` | `stroke="#000"` |
| Stroke width | `strokeWidth: 2` | `stroke-width="2"` |
| Opacity | `opacity: 0.5` | `opacity="0.5"` |
| Line cap | `lineCap: "round"` | `stroke-linecap="round"` |

## Parity Testing

All vector elements MUST pass automated parity tests comparing JS and Python rendering.

### crispEdges for Cross-Platform Parity

**Key Insight:** Chrome and resvg use different anti-aliasing algorithms. With anti-aliasing enabled (`geometricPrecision`), there's a 1-4% pixel difference on curves and diagonals. The shape geometry is identical - only the AA differs.

**Solution:** Use `shape-rendering="crispEdges"` in SVG to disable anti-aliasing. This ensures Chrome and resvg produce **identical** pixel output (<0.1% difference).

| Mode | Diagonal Line | Circle | Notes |
|------|---------------|--------|-------|
| `geometricPrecision` | 3.35% diff | 3.45% diff | Smooth but different AA |
| `crispEdges` | 0.04% diff | 0.02% diff | Aliased but identical |

For production use where smooth output is needed, accept that 1-4% difference on curves/diagonals is expected when using `geometricPrecision`.

### Test Requirements
- Pixel match: **99.9%** (≤0.1% difference allowed)
- All shape types must be tested
- Various style combinations must be tested
- New shape types must include parity tests before merge

### Pixel Diff Algorithm
A pixel is considered "different" if ANY of its RGBA channels differs by **5 or more** (out of 255). Differences below 5 do not count as errors.

**IMPORTANT:** Differences greater than 0.1% indicate a real rendering bug, NOT anti-aliasing variations. DO NOT increase the tolerance - fix the rendering algorithm instead.

### Running Parity Tests
```bash
# All parity tests
poetry run pytest tests/test_vector_parity.py -v

# Specific shape tests
poetry run pytest tests/test_vector_parity.py -k "rect" -v
```

### Test Structure
```python
class TestVectorParity:
    def test_rect_filled(self):
        """Rectangle with fill only"""

    def test_rect_stroked(self):
        """Rectangle with stroke only"""

    def test_rect_filled_and_stroked(self):
        """Rectangle with both fill and stroke"""

    def test_ellipse_*(...):
        """Ellipse variations"""

    def test_line_*(...):
        """Line variations with different caps"""

    def test_polygon_*(...):
        """Polygon variations"""

    def test_multiple_shapes(self):
        """Multiple shapes composited"""

    def test_opacity(self):
        """Shapes with various opacity values"""
```

## Adding New Vector Elements

When adding a new vector shape type:

1. **Create JS Shape Class** (`frontend/js/core/shapes/NewShape.js`)
   - Extend `VectorShape`
   - Implement `render(ctx)` for preview
   - Implement `toSVGElement()` for final rendering
   - Implement `toData()` and `fromData()`

2. **Update Python Renderer** (`slopstag/rendering/vector.py`)
   - Add case to `shape_to_svg_element()`
   - Use identical SVG generation logic as JS

3. **Add Parity Tests** (`tests/test_vector_parity.py`)
   - Test filled variant
   - Test stroked variant
   - Test filled + stroked
   - Test with various opacity values
   - Test edge cases (zero size, negative coords, etc.)

4. **Update Documentation**
   - Add to shape table in this file
   - Document any special attributes

5. **All tests MUST pass before merge**

## API Endpoints

### Get Layer SVG
```
GET /api/sessions/{id}/layers/{layer_id}/svg
```
Returns the SVG representation of a vector layer.

### Get Layer Data
```
GET /api/sessions/{id}/layers/{layer_id}
```
Returns layer data including shape definitions.

### Render Layer Server-Side
```
POST /api/rendering/layer
Content-Type: application/json

{
    "type": "vector",
    "width": 200,
    "height": 200,
    "shapes": [...]
}
```
Returns RGBA pixel data rendered via resvg.

## Layer Auto-Fit and Coordinate System

### Coordinate Spaces

Vector shapes are stored in **document coordinates**, not layer-relative coordinates. This is critical to understand:

```
Document Space (800x600)
┌────────────────────────────────────────┐
│                                        │
│       Shape at (100, 100)              │
│           ●───────┐                    │
│           │       │                    │
│           └───────┘                    │
│       Layer canvas (auto-fitted)       │
│       offset: (48, 48)                 │
│       size: 106x106                    │
│                                        │
└────────────────────────────────────────┘
```

### Auto-Fit Behavior

VectorLayer automatically resizes its canvas to fit the bounding box of its shapes:

1. **On shape add/remove**: `fitToContent()` shrinks canvas to shape bounds
2. **During editing**: Canvas expands to document size for free movement
3. **On editing end**: Canvas shrinks back to fit content

```javascript
// Lifecycle:
layer.addShape(circle);     // → fitToContent() shrinks to ~106x106
layer.startEditing();       // → expands to 800x600 for movement
// ... user drags shape ...
layer.endEditing();         // → fitToContent() shrinks to new bounds
```

### Why Auto-Fit?

- **Memory efficiency**: Small shapes don't allocate full document-sized canvas
- **SVG optimization**: Only render the bounding box area, not full document
- **Performance**: 97%+ reduction in pixels for small shapes on large documents

### Key Implementation Details

**Selection handles**: Drawn directly at shape's document coordinates (no translation needed since shapes and composite canvas are both in document space).

**Preview rendering**: Translates by `-offsetX, -offsetY` so shapes at document position render correctly within the smaller layer canvas:

```javascript
renderPreview() {
    ctx.translate(-this.offsetX, -this.offsetY);
    for (const shape of this.shapes) {
        shape.render(ctx);  // shape uses document coords
    }
}
```

**Editing mode expansion**: When `startEditing()` is called, the canvas temporarily expands to document size. This prevents shapes from being clipped when dragged outside current bounds. `endEditing()` shrinks back.

**Immediate preview on edit end**: After `fitToContent()` resizes the canvas (clearing it), an immediate Canvas 2D render is done before the async SVG render. This prevents a blank flash.

### Common Pitfalls

| Problem | Cause | Solution |
|---------|-------|----------|
| Selection handles offset | Translating by layer offset when drawing handles | Don't translate - shapes are in document coords |
| Shape clipped during drag | Canvas still at auto-fit size | Expand canvas in `startEditing()` |
| Blank layer after drop | Async SVG render not complete | Call `renderPreview()` before async render |
| Wrong bounds returned | Clamping to layer dimensions | Use `getShapesBoundsInDocSpace()` for true bounds |

## Known Limitations

1. **Arrow heads**: Lines with arrows require path conversion (more complex SVG)
2. **Rounded rectangles**: `rx`/`ry` attributes must match between JS and Python
3. **Text on path**: Not yet supported
4. **Gradients in shapes**: Requires `<defs>` section (future enhancement)
5. **Patterns**: Not yet supported

## Troubleshooting

### Pixels don't match
1. Check SVG output from both JS and Python - should be identical
2. Verify coordinate precision (use consistent rounding)
3. Check stroke-width and linecap settings
4. Ensure opacity is applied identically

### Shape renders differently in preview vs final
- Preview uses Canvas 2D (fast, during editing)
- Final uses SVG rendering (accurate, for export/comparison)
- This is expected behavior

### resvg produces different output
- Ensure resvg-py version matches expected
- Check if SVG is well-formed (validate with online tool)
- Some SVG features may not be supported by resvg
