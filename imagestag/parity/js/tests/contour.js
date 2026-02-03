/**
 * Tests for contour extraction filter.
 *
 * Tests cover:
 * - Basic contour extraction from simple shapes
 * - Simplification with Douglas-Peucker
 * - Bezier curve fitting
 * - SVG output generation
 * - SVG reconstruction with actual SVG files
 *
 * Run with: node imagestag/parity/js/tests/contour.js
 */

import {
    initWasm,
    extractContours,
    contourToSvgPath,
    contoursToSvg,
    extractContoursToSvg,
} from '../../../filters/js/contour.js';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';

// Simple test framework
let passed = 0;
let failed = 0;

function test(name, fn) {
    try {
        fn();
        passed++;
        console.log(`  ✓ ${name}`);
    } catch (e) {
        failed++;
        console.log(`  ✗ ${name}`);
        console.log(`    Error: ${e.message}`);
    }
}

async function testAsync(name, fn) {
    try {
        await fn();
        passed++;
        console.log(`  ✓ ${name}`);
    } catch (e) {
        failed++;
        console.log(`  ✗ ${name}`);
        console.log(`    Error: ${e.message}`);
    }
}

function assertEqual(actual, expected, message = '') {
    if (actual !== expected) {
        throw new Error(`${message}Expected ${expected}, got ${actual}`);
    }
}

function assertTrue(value, message = '') {
    if (!value) {
        throw new Error(`${message}Expected truthy value, got ${value}`);
    }
}

function assertGreater(a, b, message = '') {
    if (!(a > b)) {
        throw new Error(`${message}Expected ${a} > ${b}`);
    }
}

function assertLess(a, b, message = '') {
    if (!(a < b)) {
        throw new Error(`${message}Expected ${a} < ${b}`);
    }
}

function assertIncludes(str, substr, message = '') {
    if (!str.includes(substr)) {
        throw new Error(`${message}Expected "${str}" to include "${substr}"`);
    }
}

function assertLessOrEqual(a, b, message = '') {
    if (!(a <= b)) {
        throw new Error(`${message}Expected ${a} <= ${b}`);
    }
}

/**
 * Create a circular mask.
 */
function createCircleMask(width, height, centerX, centerY, radius) {
    const mask = new Uint8Array(width * height);
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const dx = x - centerX;
            const dy = y - centerY;
            if (dx * dx + dy * dy < radius * radius) {
                mask[y * width + x] = 255;
            }
        }
    }
    return mask;
}

/**
 * Create a square mask.
 */
function createSquareMask(width, height, left, top, right, bottom) {
    const mask = new Uint8Array(width * height);
    for (let y = top; y < bottom; y++) {
        for (let x = left; x < right; x++) {
            mask[y * width + x] = 255;
        }
    }
    return mask;
}

async function runTests() {
    console.log('Contour Extraction JavaScript Tests');
    console.log('=' .repeat(50));

    // Initialize WASM first
    await initWasm();
    console.log('WASM initialized');
    console.log('');

    // Basic Extraction Tests
    console.log('Basic Extraction:');

    test('extract contours from circle', () => {
        const mask = createCircleMask(100, 100, 50, 50, 30);
        const contours = extractContours(mask, 100, 100, {
            threshold: 0.5,
        });
        assertEqual(contours.length, 1);
        assertTrue(contours[0].isClosed);
        assertGreater(contours[0].points.length, 10);
    });

    test('extract contours from square', () => {
        const mask = createSquareMask(100, 100, 20, 20, 80, 80);
        const contours = extractContours(mask, 100, 100, {
            threshold: 0.5,
        });
        assertEqual(contours.length, 1);
        assertTrue(contours[0].isClosed);
    });

    test('empty mask produces no contours', () => {
        const mask = new Uint8Array(100 * 100);
        const contours = extractContours(mask, 100, 100, {
            threshold: 0.5,
        });
        assertEqual(contours.length, 0);
    });

    test('full mask produces no contours', () => {
        const mask = new Uint8Array(100 * 100).fill(255);
        const contours = extractContours(mask, 100, 100, {
            threshold: 0.5,
        });
        assertEqual(contours.length, 0);
    });

    // Simplification Tests
    console.log('\nSimplification:');

    test('simplification reduces point count', () => {
        const mask = createCircleMask(100, 100, 50, 50, 30);

        const raw = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.0,
        });
        const simplified = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
        });

        assertEqual(raw.length, 1);
        assertEqual(simplified.length, 1);
        assertLess(simplified[0].points.length, raw[0].points.length);
    });

    test('simplification preserves closure', () => {
        const mask = createSquareMask(100, 100, 20, 20, 80, 80);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
        });

        assertEqual(contours.length, 1);
        assertTrue(contours[0].isClosed);
    });

    test('higher epsilon means more simplification', () => {
        const mask = createCircleMask(100, 100, 50, 50, 30);

        const eps03 = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.3,
        });
        const eps05 = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
        });

        assertTrue(eps05[0].points.length <= eps03[0].points.length);
    });

    // Bezier Fitting Tests
    console.log('\nBezier Fitting:');

    test('bezier fitting produces curves', () => {
        const mask = createCircleMask(100, 100, 50, 50, 30);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
            fitBeziers: true,
            bezierSmoothness: 0.25,
        });

        assertEqual(contours.length, 1);
        assertTrue(contours[0].beziers !== null);
        assertGreater(contours[0].beziers.length, 0);
    });

    test('bezier segments have valid structure', () => {
        const mask = createSquareMask(100, 100, 20, 20, 80, 80);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
            fitBeziers: true,
        });

        for (const bez of contours[0].beziers) {
            assertTrue(typeof bez.p0.x === 'number');
            assertTrue(typeof bez.p0.y === 'number');
            assertTrue(typeof bez.p1.x === 'number');
            assertTrue(typeof bez.p1.y === 'number');
            assertTrue(typeof bez.p2.x === 'number');
            assertTrue(typeof bez.p2.y === 'number');
            assertTrue(typeof bez.p3.x === 'number');
            assertTrue(typeof bez.p3.y === 'number');
        }
    });

    test('bezier segments connect', () => {
        const mask = createCircleMask(100, 100, 50, 50, 30);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
            fitBeziers: true,
        });

        const beziers = contours[0].beziers;
        for (let i = 1; i < beziers.length; i++) {
            const prevEnd = beziers[i - 1].p3;
            const currStart = beziers[i].p0;
            const dist = Math.sqrt(
                (prevEnd.x - currStart.x) ** 2 +
                (prevEnd.y - currStart.y) ** 2
            );
            assertLess(dist, 0.01, `Segment ${i} doesn't connect: `);
        }
    });

    // SVG Output Tests
    console.log('\nSVG Output:');

    test('contourToSvgPath generates path string', () => {
        const mask = createSquareMask(100, 100, 20, 20, 80, 80);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
        });

        const path = contourToSvgPath(contours[0]);
        assertIncludes(path, 'M ');  // Move command
        assertIncludes(path, 'L ');  // Line command
        assertIncludes(path, 'Z');   // Close command
    });

    test('contoursToSvg generates valid SVG', () => {
        const mask = createSquareMask(100, 100, 20, 20, 80, 80);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
        });

        const svg = contoursToSvg(contours, 100, 100);
        assertIncludes(svg, '<svg');
        assertIncludes(svg, '</svg>');
        assertIncludes(svg, '<path');
        assertIncludes(svg, 'viewBox="0 0 100 100"');
    });

    test('contoursToSvg with background adds rect', () => {
        const mask = createSquareMask(100, 100, 20, 20, 80, 80);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
        });

        const svg = contoursToSvg(contours, 100, 100, {
            backgroundColor: '#000000',
        });
        assertIncludes(svg, '<rect');
        assertIncludes(svg, 'fill="#000000"');
    });

    test('contoursToSvg with stroke adds stroke attrs', () => {
        const mask = createSquareMask(100, 100, 20, 20, 80, 80);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
        });

        const svg = contoursToSvg(contours, 100, 100, {
            strokeColor: '#FF0000',
            strokeWidth: 2.0,
        });
        assertIncludes(svg, 'stroke="#FF0000"');
        assertIncludes(svg, 'stroke-width="2.00"');
    });

    test('extractContoursToSvg convenience function works', () => {
        const mask = createSquareMask(100, 100, 20, 20, 80, 80);

        const svg = extractContoursToSvg(mask, 100, 100, {
            simplifyEpsilon: 0.5,
            fitBeziers: true,
            fillColor: '#FFFFFF',
            backgroundColor: '#000000',
        });

        assertIncludes(svg, '<svg');
        assertIncludes(svg, '</svg>');
        assertIncludes(svg, '<path');
        assertIncludes(svg, '<rect');
    });

    test('bezier SVG uses C commands', () => {
        const mask = createCircleMask(100, 100, 50, 50, 30);
        const contours = extractContours(mask, 100, 100, {
            simplifyEpsilon: 0.5,
            fitBeziers: true,
        });

        const path = contourToSvgPath(contours[0]);
        assertIncludes(path, 'M ');  // Move command
        assertIncludes(path, 'C ');  // Cubic bezier command
    });

    // SVG Reconstruction Tests
    console.log('\nSVG Reconstruction:');

    // Get path to sample SVGs
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const samplesDir = path.join(__dirname, '..', '..', '..', 'samples', 'svgs');
    const deerSvgPath = path.join(samplesDir, 'noto-emoji', 'deer.svg');
    const maleDeerSvgPath = path.join(samplesDir, 'openclipart', 'male-deer.svg');

    // Test size - smaller for faster tests
    const TEST_SIZE = 256;

    // Maximum allowed pixel difference percentage for various configs
    // Note: Using 256x256 for faster tests results in higher diff than 512x512
    const MAX_DIFF_RAW = 4.0;
    const MAX_DIFF_SIMPLIFIED = 4.5;
    const MAX_DIFF_BEZIER = 5.0;

    /**
     * Render SVG to alpha mask using sharp.
     */
    async function renderSvgToMask(svgPath, size) {
        const svgBuffer = fs.readFileSync(svgPath);
        const { data, info } = await sharp(svgBuffer)
            .resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
            .ensureAlpha()
            .raw()
            .toBuffer({ resolveWithObject: true });

        // Extract alpha channel
        const mask = new Uint8Array(size * size);
        for (let i = 0; i < size * size; i++) {
            mask[i] = data[i * 4 + 3]; // Alpha channel
        }
        return mask;
    }

    /**
     * Render SVG string to alpha mask using sharp.
     */
    async function renderSvgStringToMask(svgString, size) {
        const svgBuffer = Buffer.from(svgString);
        const { data, info } = await sharp(svgBuffer)
            .resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
            .ensureAlpha()
            .raw()
            .toBuffer({ resolveWithObject: true });

        // Extract alpha channel
        const mask = new Uint8Array(size * size);
        for (let i = 0; i < size * size; i++) {
            mask[i] = data[i * 4 + 3]; // Alpha channel
        }
        return mask;
    }

    /**
     * Calculate pixel difference between two masks.
     */
    function calculateMaskDiff(mask1, mask2) {
        if (mask1.length !== mask2.length) {
            throw new Error('Mask sizes do not match');
        }

        let diffSum = 0;
        for (let i = 0; i < mask1.length; i++) {
            diffSum += Math.abs(mask1[i] - mask2[i]);
        }

        // Return as percentage of max possible difference
        const maxDiff = mask1.length * 255;
        return (diffSum / maxDiff) * 100;
    }

    /**
     * Run SVG reconstruction test with given options.
     */
    async function testSvgReconstruction(svgPath, options, maxDiff, testName) {
        // Load and render original SVG to mask
        const originalMask = await renderSvgToMask(svgPath, TEST_SIZE);

        // Extract contours
        const contours = extractContours(originalMask, TEST_SIZE, TEST_SIZE, options);

        // Generate SVG from contours (white fill, no background to preserve alpha)
        const reconstructedSvg = contoursToSvg(contours, TEST_SIZE, TEST_SIZE, {
            fillColor: '#FFFFFF',
        });

        // Render reconstructed SVG to mask (alpha channel shows shape)
        const reconstructedMask = await renderSvgStringToMask(reconstructedSvg, TEST_SIZE);

        // Calculate difference
        const diff = calculateMaskDiff(originalMask, reconstructedMask);

        if (diff > maxDiff) {
            throw new Error(`${testName} diff ${diff.toFixed(2)}% exceeds ${maxDiff}%`);
        }

        return { diff, contours };
    }

    // Check if SVG files exist
    const deerExists = fs.existsSync(deerSvgPath);
    const maleDeerExists = fs.existsSync(maleDeerSvgPath);

    if (deerExists) {
        await testAsync('deer raw extraction', async () => {
            await testSvgReconstruction(deerSvgPath, {
                threshold: 0.5,
                simplifyEpsilon: 0.0,
                fitBeziers: false,
            }, MAX_DIFF_RAW, 'Deer raw');
        });

        await testAsync('deer simplified extraction', async () => {
            await testSvgReconstruction(deerSvgPath, {
                threshold: 0.5,
                simplifyEpsilon: 0.5,
                fitBeziers: false,
            }, MAX_DIFF_SIMPLIFIED, 'Deer simplified');
        });

        await testAsync('deer bezier extraction', async () => {
            await testSvgReconstruction(deerSvgPath, {
                threshold: 0.5,
                simplifyEpsilon: 0.5,
                fitBeziers: true,
                bezierSmoothness: 0.25,
            }, MAX_DIFF_BEZIER, 'Deer bezier');
        });
    } else {
        console.log('  (deer.svg not found, skipping deer tests)');
    }

    if (maleDeerExists) {
        await testAsync('male-deer raw extraction', async () => {
            await testSvgReconstruction(maleDeerSvgPath, {
                threshold: 0.5,
                simplifyEpsilon: 0.0,
                fitBeziers: false,
            }, MAX_DIFF_RAW, 'Male-deer raw');
        });

        await testAsync('male-deer simplified extraction', async () => {
            await testSvgReconstruction(maleDeerSvgPath, {
                threshold: 0.5,
                simplifyEpsilon: 0.5,
                fitBeziers: false,
            }, MAX_DIFF_SIMPLIFIED, 'Male-deer simplified');
        });

        await testAsync('male-deer bezier extraction', async () => {
            await testSvgReconstruction(maleDeerSvgPath, {
                threshold: 0.5,
                simplifyEpsilon: 0.5,
                fitBeziers: true,
                bezierSmoothness: 0.25,
            }, MAX_DIFF_BEZIER, 'Male-deer bezier');
        });
    } else {
        console.log('  (male-deer.svg not found, skipping male-deer tests)');
    }

    if (deerExists) {
        await testAsync('simplification reduces points on deer', async () => {
            const originalMask = await renderSvgToMask(deerSvgPath, TEST_SIZE);

            const rawContours = extractContours(originalMask, TEST_SIZE, TEST_SIZE, {
                simplifyEpsilon: 0.0,
            });
            const simplifiedContours = extractContours(originalMask, TEST_SIZE, TEST_SIZE, {
                simplifyEpsilon: 0.5,
            });

            const rawPoints = rawContours.reduce((sum, c) => sum + c.points.length, 0);
            const simplifiedPoints = simplifiedContours.reduce((sum, c) => sum + c.points.length, 0);

            assertLess(simplifiedPoints, rawPoints);
        });

        await testAsync('bezier fitting on real SVG', async () => {
            const originalMask = await renderSvgToMask(deerSvgPath, TEST_SIZE);

            const contours = extractContours(originalMask, TEST_SIZE, TEST_SIZE, {
                simplifyEpsilon: 0.5,
                fitBeziers: true,
            });

            for (const contour of contours) {
                assertTrue(contour.beziers !== null);
                assertGreater(contour.beziers.length, 0);
            }
        });
    }

    // Summary
    console.log('\n' + '=' .repeat(50));
    console.log(`Results: ${passed} passed, ${failed} failed`);
    console.log('=' .repeat(50));

    process.exit(failed > 0 ? 1 : 0);
}

runTests().catch(err => {
    console.error('Test runner error:', err);
    process.exit(1);
});
