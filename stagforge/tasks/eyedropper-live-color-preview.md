# Eyedropper Live Color Preview in Toolbar

## Status: PARTIALLY IMPLEMENTED

## Current Issues
1. **Preview color does not update** - Color swatch not updating as cursor moves
2. **Preview should be round** - Currently not circular as designed
3. **Preview should be non-interactive** - Should be display-only
4. **RGBA text overlaps preview** - Text values overlap the preview color region

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
- Fix real-time color sampling on mousemove
- Make preview circular with CSS border-radius
- Fix layout so text doesn't overlap preview
- Works for both dedicated Eyedropper tool and Alt-key temporary mode
