//! Marching Squares algorithm for sub-pixel contour extraction.
//!
//! This module provides high-quality contour extraction from alpha masks:
//! - **Marching Squares**: Sub-pixel precision contour extraction
//! - **Douglas-Peucker**: Polyline simplification
//! - **Bezier Fitting**: Convert polylines to smooth cubic Bezier curves

use std::collections::HashMap;

/// A 2D point with sub-pixel precision.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Point {
    pub x: f32,
    pub y: f32,
}

impl Point {
    pub fn new(x: f32, y: f32) -> Self {
        Self { x, y }
    }

    pub fn distance_to(&self, other: &Point) -> f32 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        (dx * dx + dy * dy).sqrt()
    }

    /// Perpendicular distance from this point to a line segment.
    pub fn distance_to_line(&self, line_start: &Point, line_end: &Point) -> f32 {
        let dx = line_end.x - line_start.x;
        let dy = line_end.y - line_start.y;
        let length_sq = dx * dx + dy * dy;

        if length_sq < 1e-10 {
            // Line segment is essentially a point
            return self.distance_to(line_start);
        }

        // Project point onto line, clamping to segment
        let t = ((self.x - line_start.x) * dx + (self.y - line_start.y) * dy) / length_sq;
        let t = t.clamp(0.0, 1.0);

        let proj_x = line_start.x + t * dx;
        let proj_y = line_start.y + t * dy;

        let px = self.x - proj_x;
        let py = self.y - proj_y;
        (px * px + py * py).sqrt()
    }
}

/// A cubic Bezier curve segment.
#[derive(Clone, Debug)]
pub struct BezierSegment {
    pub p0: Point, // Start point
    pub p1: Point, // First control point
    pub p2: Point, // Second control point
    pub p3: Point, // End point
}

impl BezierSegment {
    pub fn new(p0: Point, p1: Point, p2: Point, p3: Point) -> Self {
        Self { p0, p1, p2, p3 }
    }

    /// Evaluate the Bezier curve at parameter t (0..1).
    pub fn evaluate(&self, t: f32) -> Point {
        let t2 = t * t;
        let t3 = t2 * t;
        let mt = 1.0 - t;
        let mt2 = mt * mt;
        let mt3 = mt2 * mt;

        Point::new(
            mt3 * self.p0.x + 3.0 * mt2 * t * self.p1.x + 3.0 * mt * t2 * self.p2.x + t3 * self.p3.x,
            mt3 * self.p0.y + 3.0 * mt2 * t * self.p1.y + 3.0 * mt * t2 * self.p2.y + t3 * self.p3.y,
        )
    }

    /// Convert to SVG path command (assumes p0 is already the current position).
    pub fn to_svg_command(&self) -> String {
        format!(
            "C {:.3},{:.3} {:.3},{:.3} {:.3},{:.3}",
            self.p1.x, self.p1.y, self.p2.x, self.p2.y, self.p3.x, self.p3.y
        )
    }
}

/// A contour represented as either a polyline or Bezier curves.
#[derive(Clone, Debug)]
pub struct Contour {
    pub points: Vec<Point>,
    pub beziers: Option<Vec<BezierSegment>>,
    pub is_closed: bool,
}

impl Contour {
    pub fn new(points: Vec<Point>, is_closed: bool) -> Self {
        Self {
            points,
            beziers: None,
            is_closed,
        }
    }

    /// Convert contour to SVG path data.
    pub fn to_svg_path(&self) -> String {
        if self.points.is_empty() {
            return String::new();
        }

        let mut path = String::new();

        if let Some(ref beziers) = self.beziers {
            // Use Bezier curves
            if beziers.is_empty() {
                return String::new();
            }
            path.push_str(&format!("M {:.3},{:.3} ", beziers[0].p0.x, beziers[0].p0.y));
            for bez in beziers {
                path.push_str(&bez.to_svg_command());
                path.push(' ');
            }
        } else {
            // Use polyline
            path.push_str(&format!("M {:.3},{:.3} ", self.points[0].x, self.points[0].y));
            for point in &self.points[1..] {
                path.push_str(&format!("L {:.3},{:.3} ", point.x, point.y));
            }
        }

        if self.is_closed {
            path.push('Z');
        }

        path
    }
}

/// Extract contours from an alpha mask using Marching Squares.
///
/// # Arguments
/// * `mask` - Alpha mask (0-255 values)
/// * `width` - Mask width
/// * `height` - Mask height
/// * `threshold` - Alpha threshold (0.0-1.0) for inside/outside classification
///
/// # Returns
/// Vector of contours with sub-pixel precision.
pub fn marching_squares(
    mask: &[u8],
    width: usize,
    height: usize,
    threshold: f32,
) -> Vec<Contour> {
    if width < 2 || height < 2 {
        return Vec::new();
    }

    let threshold_byte = (threshold * 255.0) as u8;

    // Build edge segments from marching squares
    let mut edges: HashMap<(i32, i32, u8), Vec<(Point, Point)>> = HashMap::new();

    for y in 0..height - 1 {
        for x in 0..width - 1 {
            // Get the 4 corners of this cell
            let tl = mask[y * width + x];
            let tr = mask[y * width + x + 1];
            let bl = mask[(y + 1) * width + x];
            let br = mask[(y + 1) * width + x + 1];

            // Classify corners (1 = inside, 0 = outside)
            let case = ((tl > threshold_byte) as u8)
                | (((tr > threshold_byte) as u8) << 1)
                | (((br > threshold_byte) as u8) << 2)
                | (((bl > threshold_byte) as u8) << 3);

            if case == 0 || case == 15 {
                // All outside or all inside - no edge
                continue;
            }

            // Interpolate edge positions
            let x = x as f32;
            let y = y as f32;

            // Edge midpoints (with interpolation for sub-pixel precision)
            let top = interpolate_edge(tl, tr, threshold_byte, x, y, x + 1.0, y);
            let right = interpolate_edge(tr, br, threshold_byte, x + 1.0, y, x + 1.0, y + 1.0);
            let bottom = interpolate_edge(bl, br, threshold_byte, x, y + 1.0, x + 1.0, y + 1.0);
            let left = interpolate_edge(tl, bl, threshold_byte, x, y, x, y + 1.0);

            // Generate line segments based on case
            let segments = match case {
                1 => vec![(left, top)],
                2 => vec![(top, right)],
                3 => vec![(left, right)],
                4 => vec![(right, bottom)],
                5 => vec![(left, top), (right, bottom)], // Saddle point - ambiguous
                6 => vec![(top, bottom)],
                7 => vec![(left, bottom)],
                8 => vec![(bottom, left)],
                9 => vec![(bottom, top)],
                10 => vec![(top, left), (bottom, right)], // Saddle point - ambiguous
                11 => vec![(bottom, right)],
                12 => vec![(right, left)],
                13 => vec![(right, top)],
                14 => vec![(top, left)],
                _ => vec![],
            };

            for (p1, p2) in segments {
                let cell_key = (x as i32, y as i32, case);
                edges.entry(cell_key).or_default().push((p1, p2));
            }
        }
    }

    // Connect segments into contours
    connect_segments(edges)
}

/// Interpolate edge position based on alpha values.
fn interpolate_edge(
    v1: u8,
    v2: u8,
    threshold: u8,
    x1: f32,
    y1: f32,
    x2: f32,
    y2: f32,
) -> Point {
    if v1 == v2 {
        // Avoid division by zero
        return Point::new((x1 + x2) / 2.0, (y1 + y2) / 2.0);
    }

    let t = (threshold as f32 - v1 as f32) / (v2 as f32 - v1 as f32);
    let t = t.clamp(0.0, 1.0);

    Point::new(x1 + t * (x2 - x1), y1 + t * (y2 - y1))
}

/// Connect line segments into closed contours.
fn connect_segments(
    edges: HashMap<(i32, i32, u8), Vec<(Point, Point)>>,
) -> Vec<Contour> {
    // Flatten all segments and sort for deterministic order
    let mut segments: Vec<(Point, Point)> = edges.into_values().flatten().collect();
    // Sort by starting point to ensure consistent contour construction
    segments.sort_by(|a, b| {
        a.0.x.partial_cmp(&b.0.x).unwrap()
            .then(a.0.y.partial_cmp(&b.0.y).unwrap())
            .then(a.1.x.partial_cmp(&b.1.x).unwrap())
            .then(a.1.y.partial_cmp(&b.1.y).unwrap())
    });

    if segments.is_empty() {
        return Vec::new();
    }

    let mut contours = Vec::new();
    let epsilon = 0.01; // Tolerance for point matching

    while !segments.is_empty() {
        let mut contour_points = Vec::new();
        let (start, mut current) = segments.remove(0);
        contour_points.push(start);
        contour_points.push(current);

        let mut found = true;
        while found {
            found = false;

            for i in 0..segments.len() {
                let (p1, p2) = segments[i];

                if points_equal(&current, &p1, epsilon) {
                    contour_points.push(p2);
                    current = p2;
                    segments.remove(i);
                    found = true;
                    break;
                } else if points_equal(&current, &p2, epsilon) {
                    contour_points.push(p1);
                    current = p1;
                    segments.remove(i);
                    found = true;
                    break;
                }
            }
        }

        // Check if contour is closed
        let is_closed = contour_points.len() > 2
            && points_equal(contour_points.first().unwrap(), contour_points.last().unwrap(), epsilon);

        if is_closed {
            contour_points.pop(); // Remove duplicate closing point
        }

        if contour_points.len() >= 3 {
            contours.push(Contour::new(contour_points, is_closed));
        }
    }

    contours
}

fn points_equal(p1: &Point, p2: &Point, epsilon: f32) -> bool {
    (p1.x - p2.x).abs() < epsilon && (p1.y - p2.y).abs() < epsilon
}

/// Simplify a polyline using the Douglas-Peucker algorithm.
///
/// # Arguments
/// * `points` - Input polyline points
/// * `epsilon` - Maximum allowed perpendicular distance
///
/// # Returns
/// Simplified polyline with fewer points.
pub fn douglas_peucker(points: &[Point], epsilon: f32) -> Vec<Point> {
    if points.len() < 3 {
        return points.to_vec();
    }

    // Find the point with maximum distance from the line between first and last
    let first = &points[0];
    let last = &points[points.len() - 1];

    let mut max_dist = 0.0f32;
    let mut max_idx = 0;

    for (i, point) in points.iter().enumerate().skip(1).take(points.len() - 2) {
        let dist = point.distance_to_line(first, last);
        if dist > max_dist {
            max_dist = dist;
            max_idx = i;
        }
    }

    if max_dist > epsilon {
        // Recursively simplify both halves
        let mut left = douglas_peucker(&points[..=max_idx], epsilon);
        let right = douglas_peucker(&points[max_idx..], epsilon);

        // Combine results (remove duplicate point at junction)
        left.pop();
        left.extend(right);
        left
    } else {
        // All points are within epsilon - keep only endpoints
        vec![first.clone(), last.clone()]
    }
}

/// Simplify a closed contour using Douglas-Peucker.
///
/// For closed contours, we need special handling to avoid artifacts at the start/end.
/// The returned points will have first == last to maintain closure.
pub fn douglas_peucker_closed(points: &[Point], epsilon: f32) -> Vec<Point> {
    if points.len() < 4 {
        return points.to_vec();
    }

    // Find the point furthest from all others to use as start
    // This helps avoid simplification artifacts at arbitrary start point
    let mut best_start = 0;
    let mut best_min_dist = 0.0f32;

    for i in 0..points.len() {
        let mut min_dist = f32::MAX;
        for j in 0..points.len() {
            if i != j {
                let dist = points[i].distance_to(&points[j]);
                if dist < min_dist {
                    min_dist = dist;
                }
            }
        }
        if min_dist > best_min_dist {
            best_min_dist = min_dist;
            best_start = i;
        }
    }

    // Rotate points so best_start is at index 0
    let mut rotated: Vec<Point> = points[best_start..].to_vec();
    rotated.extend(points[..best_start].iter().cloned());

    // Add closing point for processing
    rotated.push(rotated[0]);

    // Simplify - this preserves first and last points (which are equal)
    let simplified = douglas_peucker(&rotated, epsilon);

    // Keep the closing point to maintain first == last
    // This ensures the contour stays properly closed after simplification
    simplified
}

/// Fit cubic Bezier curves to a polyline.
///
/// Uses a simple approach: fit Bezier curves through groups of points,
/// ensuring C1 continuity at joins.
///
/// # Arguments
/// * `points` - Input polyline points
/// * `is_closed` - Whether the contour is closed
/// * `smoothness` - Control point distance factor (0.0-1.0), higher = smoother curves
///
/// # Returns
/// Vector of Bezier curve segments.
pub fn fit_bezier_curves(
    points: &[Point],
    is_closed: bool,
    smoothness: f32,
) -> Vec<BezierSegment> {
    if points.len() < 2 {
        return Vec::new();
    }

    if points.len() == 2 {
        // Straight line as degenerate Bezier
        let p0 = points[0];
        let p3 = points[1];
        let mid = Point::new((p0.x + p3.x) / 2.0, (p0.y + p3.y) / 2.0);
        return vec![BezierSegment::new(p0, mid, mid, p3)];
    }

    let smoothness = smoothness.clamp(0.1, 0.5);
    let mut curves = Vec::new();

    let n = points.len();

    for i in 0..n {
        let p0 = points[i];
        let p3 = if is_closed {
            points[(i + 1) % n]
        } else if i + 1 < n {
            points[i + 1]
        } else {
            break;
        };

        // Get neighboring points for tangent calculation
        let prev = if is_closed {
            points[(i + n - 1) % n]
        } else if i > 0 {
            points[i - 1]
        } else {
            Point::new(2.0 * p0.x - p3.x, 2.0 * p0.y - p3.y)
        };

        let next = if is_closed {
            points[(i + 2) % n]
        } else if i + 2 < n {
            points[i + 2]
        } else {
            Point::new(2.0 * p3.x - p0.x, 2.0 * p3.y - p0.y)
        };

        // Calculate tangent vectors using Catmull-Rom style
        let tangent0 = Point::new(p3.x - prev.x, p3.y - prev.y);
        let tangent1 = Point::new(next.x - p0.x, next.y - p0.y);

        // Scale tangents by segment length and smoothness
        let seg_len = p0.distance_to(&p3);
        let scale0 = smoothness * seg_len / tangent0.distance_to(&Point::new(0.0, 0.0)).max(0.001);
        let scale1 = smoothness * seg_len / tangent1.distance_to(&Point::new(0.0, 0.0)).max(0.001);

        let p1 = Point::new(
            p0.x + tangent0.x * scale0,
            p0.y + tangent0.y * scale0,
        );
        let p2 = Point::new(
            p3.x - tangent1.x * scale1,
            p3.y - tangent1.y * scale1,
        );

        curves.push(BezierSegment::new(p0, p1, p2, p3));
    }

    curves
}

/// Simplify a contour and optionally fit Bezier curves.
pub fn simplify_contour(contour: &mut Contour, epsilon: f32, fit_beziers: bool, smoothness: f32) {
    // Apply Douglas-Peucker simplification
    let simplified = if contour.is_closed {
        douglas_peucker_closed(&contour.points, epsilon)
    } else {
        douglas_peucker(&contour.points, epsilon)
    };

    contour.points = simplified;

    // Optionally fit Bezier curves
    if fit_beziers && contour.points.len() >= 2 {
        contour.beziers = Some(fit_bezier_curves(&contour.points, contour.is_closed, smoothness));
    }
}

/// Extract contours with full pipeline: marching squares + simplification + optional Bezier fitting.
///
/// # Arguments
/// * `mask` - Alpha mask (0-255 values)
/// * `width` - Mask width
/// * `height` - Mask height
/// * `threshold` - Alpha threshold (0.0-1.0)
/// * `simplify_epsilon` - Douglas-Peucker epsilon (0 to skip simplification)
/// * `fit_beziers` - Whether to fit Bezier curves
/// * `bezier_smoothness` - Smoothness factor for Bezier fitting (0.1-0.5)
///
/// # Returns
/// Vector of processed contours.
pub fn extract_contours_precise(
    mask: &[u8],
    width: usize,
    height: usize,
    threshold: f32,
    simplify_epsilon: f32,
    fit_beziers: bool,
    bezier_smoothness: f32,
) -> Vec<Contour> {
    let mut contours = marching_squares(mask, width, height, threshold);

    if simplify_epsilon > 0.0 || fit_beziers {
        for contour in &mut contours {
            simplify_contour(contour, simplify_epsilon, fit_beziers, bezier_smoothness);
        }
    }

    contours
}

/// Convert contours to a complete SVG document.
///
/// # Arguments
/// * `contours` - Vector of contours to render
/// * `width` - SVG width
/// * `height` - SVG height
/// * `fill_color` - Fill color for paths
/// * `stroke_color` - Optional stroke color
/// * `stroke_width` - Stroke width
/// * `background_color` - Optional background color (adds a rect behind paths)
pub fn contours_to_svg(
    contours: &[Contour],
    width: usize,
    height: usize,
    fill_color: &str,
    stroke_color: Option<&str>,
    stroke_width: f32,
    background_color: Option<&str>,
) -> String {
    // Use explicit width/height matching viewBox for better compatibility
    // Some viewers (like Mac Finder) need this to display correctly
    let mut svg = format!(
        r#"<svg xmlns="http://www.w3.org/2000/svg" width="{}px" height="{}px" viewBox="0 0 {} {}">"#,
        width, height, width, height
    );
    svg.push('\n');

    // Add background rect if specified
    if let Some(bg) = background_color {
        svg.push_str(&format!(
            r#"  <rect x="0" y="0" width="{}" height="{}" fill="{}"/>"#,
            width, height, bg
        ));
        svg.push('\n');
    }

    for contour in contours {
        let path_data = contour.to_svg_path();
        if !path_data.is_empty() {
            svg.push_str("  <path d=\"");
            svg.push_str(&path_data);
            svg.push_str("\" fill=\"");
            svg.push_str(fill_color);
            svg.push('"');

            if let Some(stroke) = stroke_color {
                svg.push_str(&format!(
                    " stroke=\"{}\" stroke-width=\"{:.2}\"",
                    stroke, stroke_width
                ));
            }

            svg.push_str("/>\n");
        }
    }

    svg.push_str("</svg>\n");
    svg
}

/// Flatten contours to a flat f32 array for FFI.
///
/// Format: [num_contours,
///          is_closed_1, num_points_1, x1, y1, x2, y2, ...,
///          has_beziers_1, (if has_beziers: num_beziers, p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y, ...),
///          is_closed_2, num_points_2, ...]
pub fn contours_to_flat(contours: &[Contour]) -> Vec<f32> {
    let mut result = Vec::new();
    result.push(contours.len() as f32);

    for contour in contours {
        result.push(if contour.is_closed { 1.0 } else { 0.0 });
        result.push(contour.points.len() as f32);

        for point in &contour.points {
            result.push(point.x);
            result.push(point.y);
        }

        if let Some(ref beziers) = contour.beziers {
            result.push(1.0); // has_beziers
            result.push(beziers.len() as f32);
            for bez in beziers {
                result.push(bez.p0.x);
                result.push(bez.p0.y);
                result.push(bez.p1.x);
                result.push(bez.p1.y);
                result.push(bez.p2.x);
                result.push(bez.p2.y);
                result.push(bez.p3.x);
                result.push(bez.p3.y);
            }
        } else {
            result.push(0.0); // no beziers
        }
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_point_distance() {
        let p1 = Point::new(0.0, 0.0);
        let p2 = Point::new(3.0, 4.0);
        assert!((p1.distance_to(&p2) - 5.0).abs() < 0.001);
    }

    #[test]
    fn test_point_to_line_distance() {
        let p = Point::new(1.0, 1.0);
        let l1 = Point::new(0.0, 0.0);
        let l2 = Point::new(2.0, 0.0);
        assert!((p.distance_to_line(&l1, &l2) - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_douglas_peucker_simple() {
        let points = vec![
            Point::new(0.0, 0.0),
            Point::new(1.0, 0.1), // Nearly on line
            Point::new(2.0, 0.0),
        ];
        let simplified = douglas_peucker(&points, 0.2);
        assert_eq!(simplified.len(), 2); // Middle point removed
    }

    #[test]
    fn test_marching_squares_simple() {
        // 4x4 mask with a 2x2 square in the center
        let mut mask = vec![0u8; 16];
        mask[5] = 255;
        mask[6] = 255;
        mask[9] = 255;
        mask[10] = 255;

        let contours = marching_squares(&mask, 4, 4, 0.5);
        assert!(!contours.is_empty());
    }

    #[test]
    fn test_bezier_evaluate() {
        let bez = BezierSegment::new(
            Point::new(0.0, 0.0),
            Point::new(0.0, 1.0),
            Point::new(1.0, 1.0),
            Point::new(1.0, 0.0),
        );

        let start = bez.evaluate(0.0);
        let end = bez.evaluate(1.0);

        assert!((start.x - 0.0).abs() < 0.001);
        assert!((start.y - 0.0).abs() < 0.001);
        assert!((end.x - 1.0).abs() < 0.001);
        assert!((end.y - 0.0).abs() < 0.001);
    }
}
