# Bevel & Emboss parameters have no effect

## Description

Some Bevel & Emboss parameters do not produce any visible change when adjusted. Specifically `altitude` and `angle` have no impact on the rendered effect.

## Steps to reproduce

1. Add a layer with content
2. Open Layer Effects, enable Bevel & Emboss
3. Change the `angle` slider - no visible change
4. Change the `altitude` slider - no visible change

## Expected behavior

- `angle` should control the direction of the light source, changing which edges appear highlighted vs shadowed
- `altitude` should control the height of the light source, affecting the intensity and spread of highlights/shadows

## Affected files

- `stagforge/frontend/js/core/EffectRenderer.js` - `renderBevelEmboss()`
- `imagestag/layer_effects/bevel_emboss.py` - Rust-backed rendering
