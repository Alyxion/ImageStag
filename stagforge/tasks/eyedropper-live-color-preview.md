# Eyedropper Live Color Preview in Toolbar

## Description
When using the Eyedropper tool (or temporary eyedropper mode via Alt key), show a live color preview in the tools toolbar as the cursor hovers over the canvas.

## Expected Behavior
- Large, round color preview swatch in toolbar (embossed/3D effect)
- Updates in real-time as cursor moves over canvas
- Shows color values in multiple formats:
  - RGBA (0-255): `R: 128  G: 64  B: 192  A: 255`
  - Percent: `R: 50%  G: 25%  B: 75%  A: 100%`
  - HSV/HSL: `H: 270°  S: 67%  V: 75%`
  - Hex: `#8040C0`

## UI Design
```
┌─────────────────────────────┐
│  ╭───────╮                  │
│  │       │  #8040C0         │
│  │  ●●●  │  R: 128 (50%)    │
│  │       │  G: 64  (25%)    │
│  ╰───────╯  B: 192 (75%)    │
│   embossed  A: 255 (100%)   │
│   preview   H: 270° S: 67%  │
│             V: 75%          │
└─────────────────────────────┘
```

## Implementation Notes
- Add color preview component to tool options panel
- Listen to mousemove events while Eyedropper active
- Sample color from composite canvas at cursor position
- Convert color to various formats for display
- CSS for embossed circular preview (box-shadow, gradient)
- Works for both dedicated Eyedropper tool and Alt-key temporary mode
