# Zoom Number Doesn't Fit in Navigator Field Beyond 999%

## Description
When zooming beyond 999%, the zoom percentage number overflows or doesn't fit in the navigator panel's edit field.

## Steps to Reproduce
1. Open a document
2. Zoom in beyond 999% (e.g., 1000%, 1500%)
3. Look at the zoom percentage field in the navigator panel
4. Observe: number is cut off or doesn't display properly

## Expected Behavior
- Field should accommodate 4-digit zoom values (up to 1000% or max zoom)
- Or field should auto-resize
- Or use abbreviation (e.g., "1.5K%")

## Suggested Fix
- Increase input field width
- Or use dynamic width based on content
- Or cap zoom display at 999% even if actual zoom is higher
- Or switch to multiplier format (10x instead of 1000%)
