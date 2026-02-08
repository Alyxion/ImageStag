/**
 * Lanczos-3 resampling for high-quality image scaling.
 * Matches Python implementation in stagforge/rendering/lanczos.py
 *
 * This is the shared implementation used by:
 * - TextLayer (for downscaling high-res text renders)
 * - Layer (for scaling pixel layers)
 */

/**
 * Lanczos resampling for high-quality image scaling.
 * Properly scales the kernel for downsampling ratios > 1.
 * @param {ImageData} srcData - Source image data
 * @param {number} dstWidth - Destination width
 * @param {number} dstHeight - Destination height
 * @param {number} [a=3] - Lanczos kernel size (2 or 3)
 * @returns {ImageData} - Resampled image data
 */
export function lanczosResample(srcData, dstWidth, dstHeight, a = 3) {
    const src = srcData.data;
    const srcWidth = srcData.width;
    const srcHeight = srcData.height;

    const dst = new Uint8ClampedArray(dstWidth * dstHeight * 4);

    const scaleX = srcWidth / dstWidth;
    const scaleY = srcHeight / dstHeight;

    // For downscaling, we need to expand the kernel support region
    const filterScaleX = Math.max(1, scaleX);
    const filterScaleY = Math.max(1, scaleY);

    // Lanczos kernel function (normalized for the filter scale)
    const lanczos = (x, filterScale) => {
        const scaled = x / filterScale;
        if (scaled === 0) return 1;
        if (scaled < -a || scaled > a) return 0;
        const pix = Math.PI * scaled;
        return (a * Math.sin(pix) * Math.sin(pix / a)) / (pix * pix);
    };

    // For each destination pixel
    for (let dstY = 0; dstY < dstHeight; dstY++) {
        for (let dstX = 0; dstX < dstWidth; dstX++) {
            // Map to source coordinates (center of the pixel)
            const srcCenterX = (dstX + 0.5) * scaleX;
            const srcCenterY = (dstY + 0.5) * scaleY;

            // Calculate kernel bounds (expanded for downscaling)
            const supportX = a * filterScaleX;
            const supportY = a * filterScaleY;

            const x1 = Math.max(0, Math.floor(srcCenterX - supportX));
            const x2 = Math.min(srcWidth - 1, Math.ceil(srcCenterX + supportX));
            const y1 = Math.max(0, Math.floor(srcCenterY - supportY));
            const y2 = Math.min(srcHeight - 1, Math.ceil(srcCenterY + supportY));

            let r = 0, g = 0, b = 0, alpha = 0;
            let weightSum = 0;

            // Convolve with Lanczos kernel
            for (let sy = y1; sy <= y2; sy++) {
                const dy = sy - srcCenterY;
                const wy = lanczos(dy, filterScaleY);
                if (wy === 0) continue;

                for (let sx = x1; sx <= x2; sx++) {
                    const dx = sx - srcCenterX;
                    const wx = lanczos(dx, filterScaleX);
                    if (wx === 0) continue;

                    const weight = wx * wy;
                    const srcIdx = (sy * srcWidth + sx) * 4;
                    const srcAlpha = src[srcIdx + 3] / 255;

                    // Premultiplied alpha for correct blending
                    r += src[srcIdx] * srcAlpha * weight;
                    g += src[srcIdx + 1] * srcAlpha * weight;
                    b += src[srcIdx + 2] * srcAlpha * weight;
                    alpha += srcAlpha * weight;
                    weightSum += weight;
                }
            }

            const dstIdx = (dstY * dstWidth + dstX) * 4;

            if (weightSum > 0 && alpha > 0) {
                // Unpremultiply alpha
                const invAlpha = 1 / alpha;
                dst[dstIdx] = Math.round(Math.max(0, Math.min(255, r * invAlpha)));
                dst[dstIdx + 1] = Math.round(Math.max(0, Math.min(255, g * invAlpha)));
                dst[dstIdx + 2] = Math.round(Math.max(0, Math.min(255, b * invAlpha)));
                dst[dstIdx + 3] = Math.round(Math.max(0, Math.min(255, alpha / weightSum * 255)));
            } else {
                dst[dstIdx] = 0;
                dst[dstIdx + 1] = 0;
                dst[dstIdx + 2] = 0;
                dst[dstIdx + 3] = 0;
            }
        }
    }

    return new ImageData(dst, dstWidth, dstHeight);
}

/**
 * Fast high-quality downscale using iterative halving + final drawImage.
 * Much faster than Lanczos but far better than a single large drawImage.
 * Suitable for real-time preview updates (thumbnails, navigator).
 *
 * @param {HTMLCanvasElement} srcCanvas - Source canvas
 * @param {number} dstWidth - Target width
 * @param {number} dstHeight - Target height
 * @returns {HTMLCanvasElement} - Downscaled canvas
 */
export function smoothDownscale(srcCanvas, dstWidth, dstHeight) {
    let w = srcCanvas.width;
    let h = srcCanvas.height;

    // If already small enough, just return a copy via drawImage
    if (w <= dstWidth * 2 && h <= dstHeight * 2) {
        const out = document.createElement('canvas');
        out.width = dstWidth;
        out.height = dstHeight;
        const ctx = out.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(srcCanvas, 0, 0, dstWidth, dstHeight);
        return out;
    }

    // Iteratively halve until within 2x of target
    let current = srcCanvas;
    while (w > dstWidth * 2 || h > dstHeight * 2) {
        const nw = Math.max(Math.ceil(w / 2), dstWidth);
        const nh = Math.max(Math.ceil(h / 2), dstHeight);
        const step = document.createElement('canvas');
        step.width = nw;
        step.height = nh;
        const ctx = step.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(current, 0, 0, nw, nh);
        current = step;
        w = nw;
        h = nh;
    }

    // Final step to exact target size
    const out = document.createElement('canvas');
    out.width = dstWidth;
    out.height = dstHeight;
    const ctx = out.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(current, 0, 0, dstWidth, dstHeight);
    return out;
}
