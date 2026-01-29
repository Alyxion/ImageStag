//! Contour extraction from alpha masks.
//!
//! Extracts polygon contours for marching ants display using boundary tracing.

use std::collections::HashSet;

/// Extract all contours from an alpha mask.
///
/// # Arguments
/// * `mask` - Alpha mask (0 = unselected, >0 = selected)
/// * `width` - Mask width
/// * `height` - Mask height
///
/// # Returns
/// Flat array: [num_contours, len1, x1, y1, x2, y2, ..., len2, ...]
pub fn extract_contours(mask: &[u8], width: usize, height: usize) -> Vec<f32> {
    let contours = extract_contours_internal(mask, width, height);

    let mut result = Vec::new();
    result.push(contours.len() as f32);

    for contour in contours {
        result.push(contour.len() as f32);
        for (x, y) in contour {
            result.push(x);
            result.push(y);
        }
    }

    result
}

/// Check if pixel is selected (treating out-of-bounds as unselected).
#[inline]
fn is_selected(mask: &[u8], width: usize, height: usize, x: i32, y: i32) -> bool {
    if x >= 0 && y >= 0 && (x as usize) < width && (y as usize) < height {
        mask[(y as usize) * width + (x as usize)] > 0
    } else {
        false
    }
}

/// Check if a pixel is on the boundary (selected with at least one unselected neighbor).
#[inline]
fn is_boundary(mask: &[u8], width: usize, height: usize, x: i32, y: i32) -> bool {
    if !is_selected(mask, width, height, x, y) {
        return false;
    }
    // Check 4-connected neighbors
    !is_selected(mask, width, height, x - 1, y) ||
    !is_selected(mask, width, height, x + 1, y) ||
    !is_selected(mask, width, height, x, y - 1) ||
    !is_selected(mask, width, height, x, y + 1)
}

/// Extract contours by tracing boundaries.
fn extract_contours_internal(mask: &[u8], width: usize, height: usize) -> Vec<Vec<(f32, f32)>> {
    if width == 0 || height == 0 {
        return Vec::new();
    }

    let mut contours = Vec::new();
    let mut visited: HashSet<(i32, i32)> = HashSet::new();

    // Find all boundary pixels and trace contours
    for y in 0..height as i32 {
        for x in 0..width as i32 {
            if is_boundary(mask, width, height, x, y) && !visited.contains(&(x, y)) {
                // Trace contour starting from this pixel
                let contour = trace_boundary(mask, width, height, x, y, &mut visited);
                if contour.len() >= 3 {
                    contours.push(contour);
                }
            }
        }
    }

    contours
}

/// Moore neighborhood directions (8-connected, clockwise from right)
const DIRECTIONS: [(i32, i32); 8] = [
    (1, 0),   // 0: right
    (1, 1),   // 1: down-right
    (0, 1),   // 2: down
    (-1, 1),  // 3: down-left
    (-1, 0),  // 4: left
    (-1, -1), // 5: up-left
    (0, -1),  // 6: up
    (1, -1),  // 7: up-right
];

/// Trace boundary using Moore neighborhood algorithm.
fn trace_boundary(
    mask: &[u8],
    width: usize,
    height: usize,
    start_x: i32,
    start_y: i32,
    visited: &mut HashSet<(i32, i32)>,
) -> Vec<(f32, f32)> {
    let mut contour = Vec::new();

    // Find initial backtrack direction (first unselected neighbor)
    let mut backtrack_dir = 0usize;
    for (i, &(dx, dy)) in DIRECTIONS.iter().enumerate() {
        if !is_selected(mask, width, height, start_x + dx, start_y + dy) {
            backtrack_dir = i;
            break;
        }
    }

    let mut x = start_x;
    let mut y = start_y;
    let mut dir = backtrack_dir;

    let max_steps = (width * height * 2) as usize;
    let mut steps = 0;

    loop {
        // Add current boundary pixel to contour (offset by 0.5 for edge alignment)
        if !visited.contains(&(x, y)) {
            contour.push((x as f32 + 0.5, y as f32 + 0.5));
            visited.insert((x, y));
        }

        // Search for next boundary pixel using Moore neighbor tracing
        // Start from backtrack direction + 1 (clockwise)
        let search_start = (dir + 5) % 8; // Equivalent to dir - 3, but handles wrap

        let mut found = false;
        for i in 0..8 {
            let check_dir = (search_start + i) % 8;
            let (dx, dy) = DIRECTIONS[check_dir];
            let nx = x + dx;
            let ny = y + dy;

            if is_selected(mask, width, height, nx, ny) {
                // Found next boundary pixel
                if nx == start_x && ny == start_y && steps > 0 {
                    // Back to start - contour complete
                    return contour;
                }

                // Check if it's actually a boundary pixel
                if is_boundary(mask, width, height, nx, ny) {
                    x = nx;
                    y = ny;
                    dir = check_dir;
                    found = true;
                    break;
                }
            }
        }

        if !found {
            // No next pixel found (isolated pixel or error)
            break;
        }

        steps += 1;
        if steps >= max_steps {
            // Safety limit
            break;
        }
    }

    contour
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_mask() {
        let mask = vec![0u8; 100];
        let contours = extract_contours_internal(&mask, 10, 10);
        assert!(contours.is_empty());
    }

    #[test]
    fn test_full_mask() {
        let mask = vec![255u8; 100];
        let contours = extract_contours_internal(&mask, 10, 10);
        // Full mask should have boundary around edges
        assert!(!contours.is_empty());
    }

    #[test]
    fn test_single_pixel() {
        let mut mask = vec![0u8; 25];
        mask[12] = 255; // Center pixel of 5x5
        let contours = extract_contours_internal(&mask, 5, 5);
        assert_eq!(contours.len(), 1);
    }

    #[test]
    fn test_rectangle() {
        // 10x10 mask with 4x3 rectangle
        let mut mask = vec![0u8; 100];
        for y in 2..5 {
            for x in 3..7 {
                mask[y * 10 + x] = 255;
            }
        }
        let contours = extract_contours_internal(&mask, 10, 10);
        assert!(!contours.is_empty());
    }
}
