# Tool System

## Overview

The tool system uses a registry pattern for maximum extensibility. Each tool is a separate file that self-registers. Tools are organized into groups with flyout menus (desktop: hover, tablet: long press) for cycling related tools.

## Base Class

All tools extend the `Tool` base class (`frontend/js/tools/Tool.js`):

```javascript
export class Tool {
    static id = 'tool';           // Unique identifier
    static name = 'Tool';         // Display name
    static icon = 'cursor';       // Icon name (maps to Phosphor SVG)
    static iconEntity = '&#9679;'; // HTML entity fallback
    static shortcut = null;       // Keyboard shortcut
    static group = 'misc';        // Tool group for toolbar grouping
    static groupShortcut = null;  // Shortcut to activate this group
    static priority = 100;        // Sort order within group (lower = first)
    static cursor = 'default';    // CSS cursor
    static limitedMode = false;   // Available in limited/simple mode

    constructor(app) { this.app = app; }

    // Lifecycle
    activate() {}
    deactivate() {}

    // Input handlers
    onMouseDown(e, x, y) {}
    onMouseMove(e, x, y) {}
    onMouseUp(e, x, y) {}
    onMouseLeave(e) {}
    onKeyDown(e) {}
    onKeyUp(e) {}

    // Properties for UI
    getProperties() { return []; }

    // API execution - REQUIRED
    executeAction(action, params) {
        return { success: false, error: 'Not implemented' };
    }
}
```

## Creating a New Tool

1. Create file `frontend/js/tools/MyTool.js`:

```javascript
import { Tool } from './Tool.js';

export class MyTool extends Tool {
    static id = 'mytool';
    static name = 'My Tool';
    static icon = 'star';
    static shortcut = 'm';
    static group = 'brush';      // Group with related tools
    static priority = 40;        // Position within group
    static cursor = 'crosshair';

    onMouseDown(e, x, y) {
        // Start operation
        this.app.history.saveState('My Action');
    }

    onMouseUp(e, x, y) {
        // Finish operation
        this.app.history.finishState();
        this.app.renderer.requestRender();
    }

    getProperties() {
        return [
            { id: 'size', name: 'Size', type: 'range', min: 1, max: 100, value: 10 }
        ];
    }

    executeAction(action, params) {
        if (action === 'draw') {
            // Programmatic execution
            return { success: true };
        }
        return { success: false, error: 'Unknown action' };
    }
}
```

2. Import and add to `allTools` in `frontend/js/tools/index.js`.

## Property Types

Tools can define properties shown in the ribbon:

- `range` - Slider with min/max/step
- `select` - Dropdown with options array
- `checkbox` - Boolean toggle
- `color` - Color picker
- `number` - Numeric input

## Canvas Bounds

Painting tools are prevented from starting strokes outside the document bounds. The following tools are allowed to work outside bounds:
- move
- hand
- selection
- lasso
- crop

## Icons

Tool icons use [Phosphor Icons](https://phosphoricons.com/) (MIT license). SVG files are in `frontend/icons/`. Icons are theme-aware: inverted for dark theme via CSS `filter: invert(1)`.

---

## Implemented Tools

### Tool Groups (Toolbar Order)

| # | Group | Tools | Shortcut | Cycle |
|---|-------|-------|----------|-------|
| 1 | **Move** | Move | V | - |
| 2 | **Selection** | Marquee, Lasso, Magic Wand | M | Shift+M |
| 3 | **Crop** | Crop | C | - |
| 4 | **Eyedropper** | Eyedropper | I | - |
| 5 | **Stamp** | Clone Stamp | S | - |
| 6 | **Retouch** | Smudge, Blur, Sharpen | - | Shift |
| 7 | **Brush** | Brush, Pencil, Spray | B | Shift+B |
| 8 | **Eraser** | Eraser | E | - |
| 9 | **Fill** | Paint Bucket, Gradient | G | Shift+G |
| 10 | **Dodge/Burn** | Dodge, Burn, Sponge | O | Shift+O |
| 11 | **Pen** | Pen, Direct Select | P | Shift+P |
| 12 | **Shapes** | Rectangle, Circle, Polygon, Line, Shape | U | Shift+U |
| 13 | **Text** | Text | T | - |
| 14 | **Hand** | Hand | H | - |

### All Implemented Tools

| Tool | ID | Group | Priority | Shortcut | Description |
|------|----|-------|----------|----------|-------------|
| Move | `move` | move | 10 | V | Move layers and selections |
| Selection | `selection` | selection | 10 | M | Rectangular marquee selection |
| Lasso | `lasso` | selection | 20 | M (cycle) | Freehand selection |
| Magic Wand | `magicwand` | selection | 30 | M (cycle) | Color-based selection |
| Crop | `crop` | crop | 10 | C | Crop document |
| Eyedropper | `eyedropper` | eyedropper | 10 | I | Sample color from canvas |
| Clone Stamp | `clonestamp` | stamp | 10 | S | Clone pixels from source point |
| Smudge | `smudge` | retouch | 10 | - | Smear/push pixels |
| Blur | `blur` | retouch | 20 | - | Soften/blur area |
| Sharpen | `sharpen` | retouch | 30 | - | Increase local contrast |
| Brush | `brush` | brush | 10 | B | Freehand painting with presets |
| Pencil | `pencil` | brush | 20 | B (cycle) | Hard-edge 1px drawing |
| Spray | `spray` | brush | 30 | B (cycle) | Airbrush/spray effect |
| Eraser | `eraser` | eraser | 10 | E | Erase to transparency |
| Paint Bucket | `fill` | fill | 10 | G | Flood fill with color |
| Gradient | `gradient` | fill | 20 | G (cycle) | Linear/radial gradient fill |
| Dodge | `dodge` | dodge | 10 | O | Lighten areas |
| Burn | `burn` | dodge | 20 | O (cycle) | Darken areas |
| Sponge | `sponge` | dodge | 30 | O (cycle) | Saturate/desaturate |
| Pen | `pen` | pen | 10 | P | Bezier path drawing |
| Direct Select | `vectorshapeedit` | pen | 20 | P (cycle) | Edit vector shape nodes |
| Rectangle | `rect` | shapes | 10 | U | Draw rectangles |
| Circle | `circle` | shapes | 20 | U (cycle) | Draw circles/ellipses |
| Polygon | `polygon` | shapes | 30 | U (cycle) | Draw polygons |
| Shape | `shape` | shapes | 40 | U (cycle) | Custom shapes |
| Line | `line` | shapes | 50 | U (cycle) | Draw straight lines |
| Text | `text` | text | 10 | T | Text layers |
| Hand | `hand` | hand | 10 | H | Pan viewport |

**Total: 28 tools in 14 groups**

---

## Industry Comparison

Comparison with Adobe Photoshop (PS), GIMP, Affinity Photo (AP), and Krita.

### Selection Tools

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Rectangular Marquee | **Yes** | Yes | Yes | Yes | Yes | |
| Elliptical Marquee | No | Yes | Yes | Yes | Yes | Could reuse Selection tool with shape option |
| Single Row/Column Marquee | No | Yes | No | No | No | Rarely used |
| Lasso (Freehand) | **Yes** | Yes | Yes | Yes | Yes | |
| Polygonal Lasso | No | Yes | No | Yes | Yes | Straight-edge lasso variant |
| Magnetic Lasso | No | Yes | Yes | No | No | Edge-snapping lasso |
| Magic Wand | **Yes** | Yes | Yes | Yes | Yes | |
| Quick Selection | No | Yes | No | Yes | No | Brush-based smart selection |
| Object Selection (AI) | No | Yes | No | No | No | AI-powered object detection |
| Color Range Select | No | Yes | Yes | No | Yes | Select by color range |
| Select by Color | No | No | Yes | No | Yes | GIMP/Krita specific |

**Implemented: 3/11** | Priority missing: Elliptical Marquee, Polygonal Lasso, Quick Selection

### Navigation & Transform

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Move | **Yes** | Yes | Yes | Yes | Yes | |
| Hand (Pan) | **Yes** | Yes | Yes | Yes | Yes | |
| Zoom | No | Yes | Yes | Yes | Yes | We use scroll wheel, no dedicated tool |
| Rotate View | No | Yes | No | Yes | Yes | Non-destructive canvas rotation |
| Crop | **Yes** | Yes | Yes | Yes | Yes | |
| Perspective Crop | No | Yes | No | No | No | Crop with perspective correction |
| Free Transform | No | Yes | Yes | Yes | Yes | Scale/rotate/skew via handles |
| Warp | No | Yes | Yes | Yes | No | Mesh-based distortion |

**Implemented: 3/8** | Priority missing: Zoom tool, Free Transform

### Drawing & Painting

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Brush | **Yes** | Yes | Yes | Yes | Yes | With presets |
| Pencil | **Yes** | Yes | Yes | Yes | Yes | Hard-edge |
| Airbrush/Spray | **Yes** | Yes | Yes | Yes | Yes | |
| Eraser | **Yes** | Yes | Yes | Yes | Yes | |
| Background Eraser | No | Yes | No | Yes | No | Erases to transparency based on color |
| Magic Eraser | No | Yes | No | No | No | One-click background removal |
| Color Replacement | No | Yes | No | No | No | Replace color while painting |
| Mixer Brush | No | Yes | No | No | Yes | Wet paint mixing |
| Pattern Stamp | No | Yes | No | No | No | Paint with pattern |

**Implemented: 4/9** | Priority missing: Background Eraser

### Retouching

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Clone Stamp | **Yes** | Yes | Yes | Yes | Yes | |
| Smudge | **Yes** | Yes | Yes | Yes | Yes | |
| Blur | **Yes** | Yes | Yes | Yes | Yes | |
| Sharpen | **Yes** | Yes | Yes | Yes | Yes | |
| Dodge | **Yes** | Yes | Yes | Yes | Yes | |
| Burn | **Yes** | Yes | Yes | Yes | Yes | |
| Sponge | **Yes** | Yes | Yes | Yes | Yes | |
| Spot Healing Brush | No | Yes | Yes | Yes | No | Content-aware spot removal |
| Healing Brush | No | Yes | Yes | Yes | No | Texture-aware clone |
| Patch | No | Yes | No | Yes | No | Area-based healing |
| Content-Aware Move | No | Yes | No | No | No | Move + fill gap |
| Red Eye Removal | No | Yes | Yes | Yes | No | |

**Implemented: 7/12** | Priority missing: Spot Healing, Healing Brush

### Fill & Color

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Paint Bucket / Flood Fill | **Yes** | Yes | Yes | Yes | Yes | |
| Gradient | **Yes** | Yes | Yes | Yes | Yes | |
| Eyedropper / Color Picker | **Yes** | Yes | Yes | Yes | Yes | |
| Color Sampler | No | Yes | No | No | No | Multi-point color info |
| 3D Material Drop | No | Yes | No | No | No | PS-specific |

**Implemented: 3/5** | All essential tools present

### Vector & Path

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Pen (Bezier) | **Yes** | Yes | Yes | Yes | Yes | |
| Direct Select / Node Edit | **Yes** | Yes | Yes | Yes | Yes | |
| Freeform Pen | No | Yes | No | No | No | Draw paths freehand |
| Curvature Pen | No | Yes | No | Yes | No | Simplified bezier |
| Add/Delete Anchor Point | No | Yes | Yes | Yes | Yes | Separate tools in PS |
| Convert Point | No | Yes | Yes | Yes | Yes | Corner ↔ smooth |

**Implemented: 2/6** | Priority missing: Add/Delete/Convert Anchor Point

### Shape Tools

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Rectangle | **Yes** | Yes | Yes | Yes | Yes | |
| Rounded Rectangle | No | Yes | No | Yes | No | Could be rect with radius property |
| Ellipse/Circle | **Yes** | Yes | Yes | Yes | Yes | |
| Polygon | **Yes** | Yes | No | Yes | Yes | |
| Line | **Yes** | Yes | No | Yes | Yes | |
| Custom Shape | **Yes** | Yes | No | Yes | No | |
| Star | No | No | Yes | Yes | Yes | Krita/AP native shape |
| Arrow | No | No | No | Yes | No | Built-in arrow shape |

**Implemented: 5/8** | Priority missing: Rounded Rectangle

### Text

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Horizontal Type | **Yes** | Yes | Yes | Yes | Yes | |
| Vertical Type | No | Yes | No | No | No | |
| Type on Path | No | Yes | Yes | Yes | No | Text along bezier |
| Type Mask | No | Yes | No | No | No | Selection from text |

**Implemented: 1/4** | Priority missing: Type on Path

### Measurement & Annotation

| Tool | Stagforge | PS | GIMP | AP | Krita | Notes |
|------|:---------:|:--:|:----:|:--:|:-----:|-------|
| Ruler / Measure | No | Yes | Yes | No | Yes | Measure distance/angle |
| Note / Annotation | No | Yes | No | No | No | Non-printing notes |
| Count | No | Yes | No | No | No | Count objects |
| Grid / Guide | No | Yes | Yes | Yes | Yes | Not a tool per se |

**Implemented: 0/4** | Priority missing: Ruler/Measure

---

## Summary

| Category | Implemented | Total (union) | Coverage |
|----------|:-----------:|:-------------:|:--------:|
| Selection | 3 | 11 | 27% |
| Navigation & Transform | 3 | 8 | 38% |
| Drawing & Painting | 4 | 9 | 44% |
| Retouching | 7 | 12 | 58% |
| Fill & Color | 3 | 5 | 60% |
| Vector & Path | 2 | 6 | 33% |
| Shape | 5 | 8 | 63% |
| Text | 1 | 4 | 25% |
| Measurement | 0 | 4 | 0% |
| **Total** | **28** | **67** | **42%** |

## Priority Roadmap

### High Priority (Core editing gaps)

1. **Elliptical Marquee** - Add shape option to existing Selection tool
2. **Polygonal Lasso** - Add mode to existing Lasso tool
3. **Quick Selection** - Brush-based smart selection
4. **Free Transform** - Scale/rotate/skew handles on selection/layer
5. **Spot Healing Brush** - Content-aware spot removal
6. **Healing Brush** - Texture-aware clone
7. **Zoom Tool** - Dedicated tool (currently scroll-only)
8. **Rounded Rectangle** - Add corner radius to existing Rectangle tool

### Medium Priority (Professional features)

9. **Ruler / Measure** - Distance and angle measurement
10. **Freeform Pen** - Draw paths freehand
11. **Add/Delete/Convert Anchor Point** - Path editing tools
12. **Type on Path** - Text along bezier curves
13. **Magnetic Lasso** - Edge-snapping selection
14. **Color Range Select** - Select by color similarity
15. **Background Eraser** - Edge-aware eraser
16. **Rotate View** - Non-destructive canvas rotation

### Low Priority (Nice to have)

17. **Patch Tool** - Area-based healing
18. **Content-Aware Move** - Move + fill
19. **Mixer Brush** - Wet paint simulation
20. **Pattern Stamp** - Paint with patterns
21. **Color Replacement** - Replace color while painting
22. **Vertical Type** - Vertical text layout
23. **Star Shape** - Dedicated star shape
24. **Single Row/Column Marquee** - Pixel-line selection

### Phosphor Icons Available

All icons for future tools are pre-downloaded in `frontend/icons/`:

| Future Tool | Icon File |
|-------------|-----------|
| Healing Brush | `heal.svg` |
| Quick Selection | `sparkle.svg` |
| Zoom | `ui-zoom-in.svg` / `ui-zoom-out.svg` |
| Free Transform | `arrows-out-cardinal.svg` |
| Rotate View | `rotate-left.svg` / `rotate-right.svg` |
| Measure/Ruler | `ruler.svg` |
| Perspective | `perspective.svg` |
| Freeform Pen | `bezier.svg` |
| Anchor Point | `anchor.svg` |
| Knife/Slice | `knife.svg` |
| Color Palette | `palette.svg` |
| Highlighter | `highlighter.svg` |

---

## API Execution

All tools must implement `executeAction(action, params)` for programmatic use:

```javascript
// Example: Brush stroke via API
POST /api/sessions/{id}/tools/brush/execute
{
    "action": "stroke",
    "params": {
        "points": [[100, 100], [150, 120], [200, 100]],
        "color": "#ff0000",
        "size": 20
    }
}
```
