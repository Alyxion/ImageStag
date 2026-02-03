/**
 * Contour extraction from alpha masks.
 *
 * This module provides sub-pixel precision contour extraction using:
 * - Marching Squares algorithm for contour extraction
 * - Douglas-Peucker algorithm for polyline simplification
 * - Bezier curve fitting for smooth curves
 *
 * The output is geometric data (contours with points/curves), not a modified image.
 */

import { initSync } from '../../wasm/imagestag_rust.js';
import * as wasm from '../../wasm/imagestag_rust.js';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

let wasmInitialized = false;

/**
 * Initialize WASM module (Node.js only).
 */
export async function initWasm() {
    if (wasmInitialized) return;
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const wasmPath = path.join(__dirname, '..', '..', 'wasm', 'imagestag_rust_bg.wasm');
    const wasmBuffer = fs.readFileSync(wasmPath);
    initSync(wasmBuffer);
    wasmInitialized = true;
}

/**
 * A 2D point with sub-pixel precision.
 * @typedef {Object} Point
 * @property {number} x - X coordinate
 * @property {number} y - Y coordinate
 */

/**
 * A cubic Bezier curve segment.
 * @typedef {Object} BezierSegment
 * @property {Point} p0 - Start point
 * @property {Point} p1 - First control point
 * @property {Point} p2 - Second control point
 * @property {Point} p3 - End point
 */

/**
 * A contour represented as either a polyline or Bezier curves.
 * @typedef {Object} Contour
 * @property {Point[]} points - Points forming the contour
 * @property {boolean} isClosed - Whether the contour is closed
 * @property {BezierSegment[]|null} beziers - Optional Bezier curve segments
 */

/**
 * Extract contours from an alpha mask using Marching Squares.
 *
 * @param {Uint8Array|Uint8ClampedArray} mask - Alpha mask as 1D array (flattened HxW)
 * @param {number} width - Mask width in pixels
 * @param {number} height - Mask height in pixels
 * @param {Object} options - Extraction options
 * @param {number} [options.threshold=0.5] - Alpha threshold (0.0-1.0)
 * @param {number} [options.simplifyEpsilon=0.0] - Douglas-Peucker epsilon (0 = no simplification)
 * @param {boolean} [options.fitBeziers=false] - Whether to fit Bezier curves
 * @param {number} [options.bezierSmoothness=0.25] - Bezier smoothness (0.1-0.5)
 * @returns {Contour[]} Array of contours
 */
export function extractContours(mask, width, height, options = {}) {
    const {
        threshold = 0.5,
        simplifyEpsilon = 0.0,
        fitBeziers = false,
        bezierSmoothness = 0.25,
    } = options;

    // Call WASM implementation
    const flatResult = wasm.extract_contours_precise_wasm(
        new Uint8Array(mask.buffer || mask),
        width,
        height,
        threshold,
        simplifyEpsilon,
        fitBeziers,
        bezierSmoothness
    );

    // Parse flat result into contour objects
    return parseFlatContours(flatResult);
}

/**
 * Parse flat contour array from WASM into JavaScript objects.
 *
 * Format: [num_contours,
 *          is_closed_1, num_points_1, x1, y1, x2, y2, ...,
 *          has_beziers_1, (num_beziers, p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y, ...),
 *          ...]
 *
 * @param {Float32Array} flat - Flat array from WASM
 * @returns {Contour[]} Parsed contours
 */
function parseFlatContours(flat) {
    const contours = [];
    let i = 0;

    const numContours = Math.floor(flat[i++]);

    for (let c = 0; c < numContours; c++) {
        const isClosed = flat[i++] === 1.0;
        const numPoints = Math.floor(flat[i++]);

        // Read points
        const points = [];
        for (let p = 0; p < numPoints; p++) {
            points.push({
                x: flat[i++],
                y: flat[i++],
            });
        }

        // Check for beziers
        const hasBeziers = flat[i++] === 1.0;
        let beziers = null;

        if (hasBeziers) {
            const numBeziers = Math.floor(flat[i++]);
            beziers = [];
            for (let b = 0; b < numBeziers; b++) {
                beziers.push({
                    p0: { x: flat[i++], y: flat[i++] },
                    p1: { x: flat[i++], y: flat[i++] },
                    p2: { x: flat[i++], y: flat[i++] },
                    p3: { x: flat[i++], y: flat[i++] },
                });
            }
        }

        contours.push({ points, isClosed, beziers });
    }

    return contours;
}

/**
 * Convert a contour to SVG path data string.
 *
 * @param {Contour} contour - Contour to convert
 * @returns {string} SVG path data string
 */
export function contourToSvgPath(contour) {
    if (contour.points.length === 0) {
        return '';
    }

    const parts = [];

    if (contour.beziers && contour.beziers.length > 0) {
        // Use Bezier curves
        const first = contour.beziers[0];
        parts.push(`M ${first.p0.x.toFixed(3)},${first.p0.y.toFixed(3)}`);
        for (const bez of contour.beziers) {
            parts.push(
                `C ${bez.p1.x.toFixed(3)},${bez.p1.y.toFixed(3)} ` +
                `${bez.p2.x.toFixed(3)},${bez.p2.y.toFixed(3)} ` +
                `${bez.p3.x.toFixed(3)},${bez.p3.y.toFixed(3)}`
            );
        }
    } else {
        // Use polyline
        const first = contour.points[0];
        parts.push(`M ${first.x.toFixed(3)},${first.y.toFixed(3)}`);
        for (let i = 1; i < contour.points.length; i++) {
            const pt = contour.points[i];
            parts.push(`L ${pt.x.toFixed(3)},${pt.y.toFixed(3)}`);
        }
    }

    if (contour.isClosed) {
        parts.push('Z');
    }

    return parts.join(' ');
}

/**
 * Convert contours to a complete SVG document.
 *
 * @param {Contour[]} contours - Array of contours
 * @param {number} width - SVG width
 * @param {number} height - SVG height
 * @param {Object} options - SVG options
 * @param {string} [options.fillColor='#FFFFFF'] - Fill color
 * @param {string|null} [options.strokeColor=null] - Stroke color
 * @param {number} [options.strokeWidth=0] - Stroke width
 * @param {string|null} [options.backgroundColor=null] - Background color
 * @returns {string} Complete SVG document
 */
export function contoursToSvg(contours, width, height, options = {}) {
    const {
        fillColor = '#FFFFFF',
        strokeColor = null,
        strokeWidth = 0,
        backgroundColor = null,
    } = options;

    const lines = [
        `<svg xmlns="http://www.w3.org/2000/svg" ` +
        `width="${width}px" height="${height}px" viewBox="0 0 ${width} ${height}">`
    ];

    if (backgroundColor) {
        lines.push(
            `  <rect x="0" y="0" width="${width}" height="${height}" ` +
            `fill="${backgroundColor}"/>`
        );
    }

    for (const contour of contours) {
        const pathData = contourToSvgPath(contour);
        if (pathData) {
            let pathAttrs = `d="${pathData}" fill="${fillColor}"`;
            if (strokeColor) {
                pathAttrs += ` stroke="${strokeColor}" stroke-width="${strokeWidth.toFixed(2)}"`;
            }
            lines.push(`  <path ${pathAttrs}/>`);
        }
    }

    lines.push('</svg>');
    return lines.join('\n');
}

/**
 * Extract contours from mask and convert directly to SVG.
 *
 * @param {Uint8Array|Uint8ClampedArray} mask - Alpha mask
 * @param {number} width - Mask width
 * @param {number} height - Mask height
 * @param {Object} options - Extraction and SVG options
 * @returns {string} Complete SVG document
 */
export function extractContoursToSvg(mask, width, height, options = {}) {
    const {
        threshold = 0.5,
        simplifyEpsilon = 0.5,
        fitBeziers = true,
        bezierSmoothness = 0.25,
        fillColor = '#FFFFFF',
        strokeColor = null,
        strokeWidth = 0,
        backgroundColor = null,
    } = options;

    const contours = extractContours(mask, width, height, {
        threshold,
        simplifyEpsilon,
        fitBeziers,
        bezierSmoothness,
    });

    return contoursToSvg(contours, width, height, {
        fillColor,
        strokeColor,
        strokeWidth,
        backgroundColor,
    });
}

/**
 * Simplify a polyline using the Douglas-Peucker algorithm.
 *
 * The Douglas-Peucker algorithm reduces the number of points in a polyline
 * while preserving its shape. Points that deviate less than epsilon from
 * the simplified line are removed.
 *
 * @param {Array<{x: number, y: number}>} points - Array of point objects
 * @param {number} epsilon - Maximum distance threshold for simplification
 * @returns {Array<{x: number, y: number}>} Simplified array of point objects
 */
export function douglasPeucker(points, epsilon) {
    // Convert to flat array for WASM
    const flatPoints = new Float32Array(points.length * 2);
    for (let i = 0; i < points.length; i++) {
        flatPoints[i * 2] = points[i].x;
        flatPoints[i * 2 + 1] = points[i].y;
    }

    const flatResult = wasm.douglas_peucker_wasm(flatPoints, epsilon);

    // Convert back to point objects
    const result = [];
    for (let i = 0; i < flatResult.length; i += 2) {
        result.push({ x: flatResult[i], y: flatResult[i + 1] });
    }
    return result;
}

/**
 * Simplify a closed polygon using the Douglas-Peucker algorithm.
 *
 * This version is optimized for closed polygons. It finds the point farthest
 * from the centroid to use as the starting point, which produces better
 * results than the standard algorithm for closed shapes.
 *
 * @param {Array<{x: number, y: number}>} points - Array of point objects (closed polygon)
 * @param {number} epsilon - Maximum distance threshold for simplification
 * @returns {Array<{x: number, y: number}>} Simplified array of point objects
 */
export function douglasPeuckerClosed(points, epsilon) {
    // Convert to flat array for WASM
    const flatPoints = new Float32Array(points.length * 2);
    for (let i = 0; i < points.length; i++) {
        flatPoints[i * 2] = points[i].x;
        flatPoints[i * 2 + 1] = points[i].y;
    }

    const flatResult = wasm.douglas_peucker_closed_wasm(flatPoints, epsilon);

    // Convert back to point objects
    const result = [];
    for (let i = 0; i < flatResult.length; i += 2) {
        result.push({ x: flatResult[i], y: flatResult[i + 1] });
    }
    return result;
}
