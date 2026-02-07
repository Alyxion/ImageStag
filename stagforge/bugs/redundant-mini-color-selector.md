# Redundant Mini Color Selector (Black/White Squares)

## Status: OPEN

## Description
Next to the main color selector, there is a small mini color selector showing a black and white square. This is redundant and confusing since the main color selector already provides full color picking functionality.

## Steps to Reproduce
1. Open the editor
2. Look at the color selector area in the toolbar/panel
3. Notice the small black and white squares next to the main color picker

## Expected Behavior
Only the main color selector should be visible. The mini selector adds visual clutter without useful functionality.

## Actual Behavior
A small duplicate/mini color selector with black and white squares is displayed alongside the main color picker.

## Likely Cause
This may be a leftover foreground/background color indicator from an earlier UI design, or a default NiceGUI color input element that was not hidden when the custom color picker was added.

## Affected Files
- Likely in the editor template/component that renders the color picker UI
- Possibly `stagforge/frontend/js/editor/` or the NiceGUI Python component
