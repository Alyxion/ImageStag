# Edge Filters Ignore Alpha Channel

## Status: OPEN

## Description
Edge detection filters (Sobel, Canny, Laplacian) do not respect the alpha channel. They process transparent areas as if they were opaque, and the original alpha mask is lost in the output. Alpha boundaries should be treated as real edges.

## Steps to Reproduce
1. Create a layer with partial transparency (e.g. a shape on a transparent background)
2. Apply an edge detection filter (Sobel, Canny, or Laplacian)
3. Observe the result

## Expected Behavior
- Edge detection should only operate within the non-transparent region
- Alpha boundaries (transitions from opaque to transparent) should be detected as real edges
- The original alpha mask should be retained in the output (transparent areas stay transparent)

## Actual Behavior
- Edge detection runs across the entire canvas including transparent areas
- Alpha boundaries are not detected as edges
- The alpha channel is destroyed — previously transparent areas become opaque

## Likely Cause
The filters likely convert to grayscale and run edge detection on RGB only, discarding alpha. They need to:
1. Use alpha as an additional edge signal (alpha gradients = edges)
2. Mask the output so transparent regions remain transparent
3. Only compute edges within the valid (non-transparent) area

## Affected Files
- `imagestag/filters/` — edge detection filter implementations
- Possibly Rust implementations in `rust/src/filters/`
