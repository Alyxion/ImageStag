/**
 * MarchingSquares - Extract contour polygons from a binary mask.
 *
 * Uses the marching squares algorithm to trace the boundaries between
 * selected (>0) and unselected (0) pixels in an alpha mask.
 *
 * WASM-accelerated when available, falls back to JavaScript implementation.
 */

// WASM module reference (set by initWasmContours)
let _wasmModule = null;
let _wasmInitializing = null;

/**
 * Initialize WASM contour extraction. Safe to call multiple times.
 * @returns {Promise<boolean>} true if WASM is available
 */
export async function initWasmContours() {
    if (_wasmModule) return true;
    if (_wasmInitializing) return _wasmInitializing;

    _wasmInitializing = (async () => {
        try {
            const module = await import('/static/js/selection/index.js');
            await module.initSelection();
            _wasmModule = module;
            console.log('[MarchingSquares] WASM contour extraction available');
            return true;
        } catch (e) {
            console.warn('[MarchingSquares] WASM not available, using JS fallback:', e.message);
            return false;
        } finally {
            _wasmInitializing = null;
        }
    })();

    return _wasmInitializing;
}

/**
 * Check if WASM contour extraction is available.
 * @returns {boolean}
 */
export function isWasmAvailable() {
    return _wasmModule !== null;
}

/**
 * Extract all contours from a mask.
 * Uses WASM if available, falls back to JavaScript.
 * @param {Uint8Array} mask - Alpha mask (0 = unselected, >0 = selected)
 * @param {number} width - Mask width
 * @param {number} height - Mask height
 * @returns {Array<Array<[number, number]>>} Array of contour polygons
 */
export function extractContours(mask, width, height) {
    // Use WASM if available
    if (_wasmModule) {
        try {
            const result = _wasmModule.extractContours(mask, width, height);
            return result;
        } catch (e) {
            console.error('[MarchingSquares] WASM error, falling back to JS:', e);
        }
    }

    // JavaScript fallback
    try {
        return extractContoursJS(mask, width, height);
    } catch (e) {
        console.error('[MarchingSquares] JS fallback error:', e);
        return [];
    }
}

/**
 * JavaScript implementation of contour extraction.
 * @param {Uint8Array} mask
 * @param {number} width
 * @param {number} height
 * @returns {Array<Array<[number, number]>>}
 */
function extractContoursJS(mask, width, height) {
    const contours = [];
    const visited = new Set();

    // Scan for boundary pixels
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            // Check if this is an edge pixel (selected pixel with unselected neighbor)
            if (isBoundaryPixel(mask, width, height, x, y)) {
                const key = `${x},${y}`;
                if (!visited.has(key)) {
                    // Trace contour starting from this pixel
                    const contour = traceContour(mask, width, height, x, y, visited);
                    if (contour.length >= 3) {
                        contours.push(contour);
                    }
                }
            }
        }
    }

    return contours;
}

/**
 * Check if a pixel is on the boundary (selected with at least one unselected neighbor).
 */
function isBoundaryPixel(mask, width, height, x, y) {
    const idx = y * width + x;
    if (mask[idx] === 0) return false;

    // Check 4-connected neighbors
    const neighbors = [
        [x - 1, y],
        [x + 1, y],
        [x, y - 1],
        [x, y + 1]
    ];

    for (const [nx, ny] of neighbors) {
        if (nx < 0 || nx >= width || ny < 0 || ny >= height) {
            return true; // Edge of image
        }
        if (mask[ny * width + nx] === 0) {
            return true; // Unselected neighbor
        }
    }

    return false;
}

/**
 * Trace a contour using Moore neighborhood tracing.
 */
function traceContour(mask, width, height, startX, startY, visited) {
    const contour = [];

    // Moore neighborhood (8 directions, clockwise from left)
    const directions = [
        [-1, 0],  // 0: left
        [-1, -1], // 1: top-left
        [0, -1],  // 2: top
        [1, -1],  // 3: top-right
        [1, 0],   // 4: right
        [1, 1],   // 5: bottom-right
        [0, 1],   // 6: bottom
        [-1, 1]   // 7: bottom-left
    ];

    let x = startX;
    let y = startY;
    let dir = 0; // Start looking left

    // Find initial direction (first unselected neighbor)
    for (let i = 0; i < 8; i++) {
        const [dx, dy] = directions[i];
        const nx = x + dx;
        const ny = y + dy;
        if (nx < 0 || nx >= width || ny < 0 || ny >= height || mask[ny * width + nx] === 0) {
            dir = i;
            break;
        }
    }

    const maxSteps = width * height * 2; // Prevent infinite loops
    let steps = 0;

    do {
        // Add current point
        const key = `${x},${y}`;
        if (!visited.has(key)) {
            contour.push([x, y]);
            visited.add(key);
        }

        // Find next boundary pixel (Moore-neighbor tracing)
        let found = false;
        const startDir = (dir + 5) % 8; // Start from backtrack direction + 1

        for (let i = 0; i < 8; i++) {
            const checkDir = (startDir + i) % 8;
            const [dx, dy] = directions[checkDir];
            const nx = x + dx;
            const ny = y + dy;

            if (nx >= 0 && nx < width && ny >= 0 && ny < height && mask[ny * width + nx] > 0) {
                x = nx;
                y = ny;
                dir = checkDir;
                found = true;
                break;
            }
        }

        if (!found) break;
        steps++;

    } while ((x !== startX || y !== startY) && steps < maxSteps);

    return contour;
}

/**
 * Simplify contour by removing collinear points.
 * @param {Array<[number, number]>} contour - Input contour
 * @param {number} tolerance - Simplification tolerance
 * @returns {Array<[number, number]>} Simplified contour
 */
export function simplifyContour(contour, tolerance = 1.0) {
    if (contour.length < 3) return contour;

    const result = [contour[0]];

    for (let i = 1; i < contour.length - 1; i++) {
        const prev = result[result.length - 1];
        const curr = contour[i];
        const next = contour[i + 1];

        // Check if curr is collinear with prev and next
        const cross = (curr[0] - prev[0]) * (next[1] - prev[1]) -
                     (curr[1] - prev[1]) * (next[0] - prev[0]);

        if (Math.abs(cross) > tolerance) {
            result.push(curr);
        }
    }

    result.push(contour[contour.length - 1]);
    return result;
}

/**
 * Convert mask to simplified outline for fast rendering.
 * Uses a simpler approach - finds horizontal runs and creates a path.
 */
export function extractSimpleOutline(mask, width, height) {
    const outlines = [];

    // Find horizontal edge segments
    const topEdges = [];    // Edges where mask goes from 0 to 1 (top of selected area)
    const bottomEdges = []; // Edges where mask goes from 1 to 0 (bottom of selected area)

    for (let y = 0; y <= height; y++) {
        for (let x = 0; x < width; x++) {
            const above = y > 0 ? mask[(y - 1) * width + x] : 0;
            const below = y < height ? mask[y * width + x] : 0;

            if (above === 0 && below > 0) {
                // Top edge
                topEdges.push({ x, y, dir: 'top' });
            } else if (above > 0 && below === 0) {
                // Bottom edge
                bottomEdges.push({ x, y, dir: 'bottom' });
            }
        }
    }

    // Convert to simple polygon outline
    // For rectangular selections, this creates a simple rectangle
    const bounds = getBoundsFromMask(mask, width, height);
    if (bounds) {
        outlines.push([
            [bounds.x, bounds.y],
            [bounds.x + bounds.width, bounds.y],
            [bounds.x + bounds.width, bounds.y + bounds.height],
            [bounds.x, bounds.y + bounds.height]
        ]);
    }

    return outlines;
}

/**
 * Get bounding box from mask.
 */
function getBoundsFromMask(mask, width, height) {
    let minX = width, minY = height, maxX = 0, maxY = 0;
    let found = false;

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            if (mask[y * width + x] > 0) {
                found = true;
                minX = Math.min(minX, x);
                minY = Math.min(minY, y);
                maxX = Math.max(maxX, x);
                maxY = Math.max(maxY, y);
            }
        }
    }

    if (!found) return null;

    return {
        x: minX,
        y: minY,
        width: maxX - minX + 1,
        height: maxY - minY + 1
    };
}
