# Perspective


![Perspective example](../gallery/filters/perspective.jpg)

Apply perspective transformation.

Transform image using four source and destination point pairs.
Points are specified as (x, y) coordinates.

Parameters:
    src_points: Four source points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
    dst_points: Four destination points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
    output_size: Output size (width, height) or None to auto-calculate

If only src_points provided, dst_points defaults to image corners
(perspective correction mode).

Example:
    # Correct skewed document
    perspective = Perspective(
        src_points=[(10, 20), (590, 30), (600, 470), (5, 460)],
        dst_points=[(0, 0), (600, 0), (600, 480), (0, 480)]
    )

For coordinate mapping between original and corrected space:
    result, transform = filter.apply_with_transform(image)
    corrected_pt = transform.forward((100, 200))  # original -> corrected
    original_pt = transform.inverse((150, 180))   # corrected -> original

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `src_points` | tuple | None | Four source points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] |
| `dst_points` | tuple | None | Four destination points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] |
| `output_size` | int | None | Output size (width, height) or None to auto-calculate |

## Frameworks

Native support: CV, RAW
