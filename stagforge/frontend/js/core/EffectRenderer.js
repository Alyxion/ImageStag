/**
 * EffectRenderer - Applies layer effects with caching.
 *
 * Effects are rendered to a cached canvas that's invalidated when:
 * - Layer pixels change
 * - Effect parameters change
 * - Layer is resized
 *
 * The rendered result includes any canvas expansion needed for effects
 * like drop shadows or outer glows.
 */

import { effectRenderOrder } from './LayerEffects.js';

export class EffectRenderer {
    constructor() {
        // Cache: layerId -> { canvas, hash, expansion }
        this.cache = new Map();

        // Throttle interval for effect updates (ms)
        this.throttleInterval = 100;

        // Pending renders
        this.pendingRenders = new Map();
    }

    /**
     * Get the rendered layer with effects applied.
     * Returns cached version if available and valid.
     *
     * Returns TWO canvases for proper Photoshop-style compositing:
     * - behindCanvas: Shadow/glow effects that should blend with layers BELOW
     * - contentCanvas: Layer content + stroke (unaffected by behind effects)
     *
     * @param {Layer} layer - The layer to render
     * @returns {{behindCanvas: HTMLCanvasElement, contentCanvas: HTMLCanvasElement, offsetX: number, offsetY: number, behindEffects: Array}|null}
     */
    getRenderedLayer(layer) {
        if (!layer.effects || layer.effects.length === 0) {
            return null; // No effects, use original layer
        }

        const enabledEffects = layer.effects.filter(e => e.enabled);
        if (enabledEffects.length === 0) {
            return null;
        }

        const hash = this.computeHash(layer);
        const cached = this.cache.get(layer.id);

        if (cached && cached.hash === hash) {
            return {
                behindCanvas: cached.behindCanvas,
                contentCanvas: cached.contentCanvas,
                behindEffects: cached.behindEffects,
                offsetX: layer.offsetX - cached.expansion.left,
                offsetY: layer.offsetY - cached.expansion.top
            };
        }

        // Need to render - check if we should throttle
        const now = Date.now();
        const pending = this.pendingRenders.get(layer.id);

        if (pending && now - pending.time < this.throttleInterval) {
            // Return stale cache if available
            if (cached) {
                return {
                    behindCanvas: cached.behindCanvas,
                    contentCanvas: cached.contentCanvas,
                    behindEffects: cached.behindEffects,
                    offsetX: layer.offsetX - cached.expansion.left,
                    offsetY: layer.offsetY - cached.expansion.top
                };
            }
        }

        // Render now
        this.pendingRenders.set(layer.id, { time: now });
        const result = this.renderEffects(layer);

        this.cache.set(layer.id, {
            behindCanvas: result.behindCanvas,
            contentCanvas: result.contentCanvas,
            behindEffects: result.behindEffects,
            hash: hash,
            expansion: result.expansion
        });

        return {
            behindCanvas: result.behindCanvas,
            contentCanvas: result.contentCanvas,
            behindEffects: result.behindEffects,
            offsetX: layer.offsetX - result.expansion.left,
            offsetY: layer.offsetY - result.expansion.top
        };
    }

    /**
     * Compute hash for cache invalidation.
     * @param {Layer} layer
     * @returns {string}
     */
    computeHash(layer) {
        // Include layer dimensions, effect params, and a content checksum
        const effectsHash = layer.effects
            .filter(e => e.enabled)
            .map(e => JSON.stringify(e.serialize()))
            .join('|');

        // Quick content hash using corner pixels
        let contentHash = `${layer.width}x${layer.height}`;
        try {
            const ctx = layer.ctx;
            const corners = [
                ctx.getImageData(0, 0, 1, 1).data,
                ctx.getImageData(layer.width - 1, 0, 1, 1).data,
                ctx.getImageData(0, layer.height - 1, 1, 1).data,
                ctx.getImageData(layer.width - 1, layer.height - 1, 1, 1).data
            ];
            contentHash += corners.map(d => `${d[0]},${d[1]},${d[2]},${d[3]}`).join('-');
        } catch (e) {
            // Fallback to timestamp if getImageData fails
            contentHash += Date.now();
        }

        return `${contentHash}|${effectsHash}`;
    }

    /**
     * Render all effects for a layer.
     *
     * Returns TWO separate canvases for proper Photoshop-style compositing:
     * - behindCanvas: Shadow/glow effects (to blend with layers BELOW)
     * - contentCanvas: Layer content + inner effects + stroke (unaffected by shadows)
     *
     * This ensures:
     * - Drop shadow only affects layers below, NOT the layer's own stroke
     * - Stroke is painted last, clean and unaffected by shadows
     * - Effects don't composite onto each other
     *
     * @param {Layer} layer
     * @returns {{behindCanvas: HTMLCanvasElement, contentCanvas: HTMLCanvasElement, behindEffects: Array, expansion: Object}}
     */
    renderEffects(layer) {
        const enabledEffects = layer.effects.filter(e => e.enabled);

        // Calculate total expansion needed
        const expansion = { left: 0, top: 0, right: 0, bottom: 0 };
        for (const effect of enabledEffects) {
            const exp = effect.getExpansion();
            expansion.left = Math.max(expansion.left, exp.left);
            expansion.top = Math.max(expansion.top, exp.top);
            expansion.right = Math.max(expansion.right, exp.right);
            expansion.bottom = Math.max(expansion.bottom, exp.bottom);
        }

        // Create expanded canvas dimensions
        const newWidth = layer.width + expansion.left + expansion.right;
        const newHeight = layer.height + expansion.top + expansion.bottom;

        // Sort effects by render order
        const sortedEffects = [...enabledEffects].sort((a, b) => {
            return effectRenderOrder.indexOf(a.type) - effectRenderOrder.indexOf(b.type);
        });

        // Separate behind-layer effects and on-layer effects
        const behindEffectsList = sortedEffects.filter(e =>
            e.type === 'dropShadow' || e.type === 'outerGlow'
        );
        const onLayerEffects = sortedEffects.filter(e =>
            e.type !== 'dropShadow' && e.type !== 'outerGlow'
        );

        // ===== CANVAS 1: Behind effects (shadow, outer glow) =====
        // These will be composited with layers BELOW, not with this layer's content
        const behindCanvas = document.createElement('canvas');
        behindCanvas.width = newWidth;
        behindCanvas.height = newHeight;
        const behindCtx = behindCanvas.getContext('2d');

        // Render behind effects to separate canvas
        for (const effect of behindEffectsList) {
            this.renderBehindEffect(behindCtx, layer, effect, expansion);
        }

        // ===== CANVAS 2: Content + on-layer effects + stroke =====
        // These are the layer's visible content, unaffected by shadows
        const contentCanvas = document.createElement('canvas');
        contentCanvas.width = newWidth;
        contentCanvas.height = newHeight;
        const contentCtx = contentCanvas.getContext('2d');

        // Draw the original layer content first
        contentCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Render inner effects (innerShadow, innerGlow, bevelEmboss, colorOverlay)
        // These modify the layer content itself
        const innerEffects = onLayerEffects.filter(e => e.type !== 'stroke');
        for (const effect of innerEffects) {
            this.renderSingleEffect(contentCtx, layer, effect, expansion);
        }

        // Render stroke LAST - it should be clean and unaffected by everything
        const strokeEffect = onLayerEffects.find(e => e.type === 'stroke');
        if (strokeEffect) {
            this.renderSingleEffect(contentCtx, layer, strokeEffect, expansion);
        }

        return {
            behindCanvas,
            contentCanvas,
            behindEffects: behindEffectsList,  // Include for blend mode lookup
            expansion
        };
    }

    /**
     * Render a behind effect (shadow/glow) to its own canvas.
     * These effects are NOT composited with the layer content here.
     */
    renderBehindEffect(ctx, layer, effect, expansion) {
        ctx.save();
        ctx.globalAlpha = effect.opacity;

        switch (effect.type) {
            case 'dropShadow':
                this.renderDropShadowOnly(ctx, layer, effect, expansion);
                break;
            case 'outerGlow':
                this.renderOuterGlowOnly(ctx, layer, effect, expansion);
                break;
        }

        ctx.restore();
    }

    /**
     * Render drop shadow without any compositing - just the shadow itself.
     */
    renderDropShadowOnly(ctx, layer, effect, expansion) {
        // Create temporary canvas for shadow
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = ctx.canvas.width;
        tempCanvas.height = ctx.canvas.height;
        const tempCtx = tempCanvas.getContext('2d');

        // Parse color and apply opacity
        const rgb = this.hexToRgb(effect.color);
        const shadowColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${effect.colorOpacity})`;

        tempCtx.shadowColor = shadowColor;
        tempCtx.shadowBlur = effect.blur;
        tempCtx.shadowOffsetX = effect.offsetX;
        tempCtx.shadowOffsetY = effect.offsetY;

        // Draw layer content to cast shadow
        tempCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Extract just the shadow by removing the original content
        const shadowCanvas = document.createElement('canvas');
        shadowCanvas.width = ctx.canvas.width;
        shadowCanvas.height = ctx.canvas.height;
        const shadowCtx = shadowCanvas.getContext('2d');

        // Draw the shadowed version
        shadowCtx.drawImage(tempCanvas, 0, 0);

        // Remove the original content to leave just shadow
        shadowCtx.globalCompositeOperation = 'destination-out';
        shadowCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Draw just the shadow to the behind canvas (additive)
        ctx.drawImage(shadowCanvas, 0, 0);
    }

    /**
     * Render outer glow without any compositing - just the glow itself.
     */
    renderOuterGlowOnly(ctx, layer, effect, expansion) {
        const rgb = this.hexToRgb(effect.color);
        const glowColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${effect.colorOpacity})`;

        // Create glow using multiple blurred copies
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = ctx.canvas.width;
        tempCanvas.height = ctx.canvas.height;
        const tempCtx = tempCanvas.getContext('2d');

        tempCtx.shadowColor = glowColor;
        tempCtx.shadowBlur = effect.blur;
        tempCtx.shadowOffsetX = 0;
        tempCtx.shadowOffsetY = 0;

        // Draw multiple times for stronger glow
        for (let i = 0; i < 3; i++) {
            tempCtx.drawImage(layer.canvas, expansion.left, expansion.top);
        }

        // Extract glow only
        const glowCanvas = document.createElement('canvas');
        glowCanvas.width = ctx.canvas.width;
        glowCanvas.height = ctx.canvas.height;
        const glowCtx = glowCanvas.getContext('2d');

        glowCtx.drawImage(tempCanvas, 0, 0);
        glowCtx.globalCompositeOperation = 'destination-out';
        glowCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Draw just the glow to the behind canvas
        ctx.drawImage(glowCanvas, 0, 0);
    }

    /**
     * Render a single effect.
     * @param {CanvasRenderingContext2D} ctx - Target context
     * @param {Layer} layer - Source layer
     * @param {LayerEffect} effect - Effect to render
     * @param {Object} expansion - Canvas expansion
     */
    renderSingleEffect(ctx, layer, effect, expansion) {
        ctx.save();
        ctx.globalAlpha = effect.opacity;

        switch (effect.type) {
            case 'dropShadow':
                this.renderDropShadow(ctx, layer, effect, expansion);
                break;
            case 'outerGlow':
                this.renderOuterGlow(ctx, layer, effect, expansion);
                break;
            case 'innerShadow':
                this.renderInnerShadow(ctx, layer, effect, expansion);
                break;
            case 'innerGlow':
                this.renderInnerGlow(ctx, layer, effect, expansion);
                break;
            case 'stroke':
                this.renderStroke(ctx, layer, effect, expansion);
                break;
            case 'colorOverlay':
                this.renderColorOverlay(ctx, layer, effect, expansion);
                break;
            case 'bevelEmboss':
                this.renderBevelEmboss(ctx, layer, effect, expansion);
                break;
        }

        ctx.restore();
    }

    /**
     * Render drop shadow using Canvas 2D shadow API.
     */
    renderDropShadow(ctx, layer, effect, expansion) {
        // Create temporary canvas for shadow
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = ctx.canvas.width;
        tempCanvas.height = ctx.canvas.height;
        const tempCtx = tempCanvas.getContext('2d');

        // Parse color and apply opacity
        const rgb = this.hexToRgb(effect.color);
        const shadowColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${effect.colorOpacity})`;

        tempCtx.shadowColor = shadowColor;
        tempCtx.shadowBlur = effect.blur;
        tempCtx.shadowOffsetX = effect.offsetX;
        tempCtx.shadowOffsetY = effect.offsetY;

        // Draw layer content to cast shadow
        tempCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Extract just the shadow by drawing on separate canvas
        const shadowCanvas = document.createElement('canvas');
        shadowCanvas.width = ctx.canvas.width;
        shadowCanvas.height = ctx.canvas.height;
        const shadowCtx = shadowCanvas.getContext('2d');

        // Draw the shadowed version
        shadowCtx.drawImage(tempCanvas, 0, 0);

        // Remove the original content to leave just shadow
        shadowCtx.globalCompositeOperation = 'destination-out';
        shadowCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Draw shadow behind current content
        ctx.globalCompositeOperation = 'destination-over';
        ctx.drawImage(shadowCanvas, 0, 0);
    }

    /**
     * Render outer glow.
     */
    renderOuterGlow(ctx, layer, effect, expansion) {
        const rgb = this.hexToRgb(effect.color);
        const glowColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${effect.colorOpacity})`;

        // Create glow using multiple blurred copies
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = ctx.canvas.width;
        tempCanvas.height = ctx.canvas.height;
        const tempCtx = tempCanvas.getContext('2d');

        tempCtx.shadowColor = glowColor;
        tempCtx.shadowBlur = effect.blur;
        tempCtx.shadowOffsetX = 0;
        tempCtx.shadowOffsetY = 0;

        // Draw multiple times for stronger glow
        for (let i = 0; i < 3; i++) {
            tempCtx.drawImage(layer.canvas, expansion.left, expansion.top);
        }

        // Extract glow only
        const glowCanvas = document.createElement('canvas');
        glowCanvas.width = ctx.canvas.width;
        glowCanvas.height = ctx.canvas.height;
        const glowCtx = glowCanvas.getContext('2d');

        glowCtx.drawImage(tempCanvas, 0, 0);
        glowCtx.globalCompositeOperation = 'destination-out';
        glowCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        ctx.globalCompositeOperation = 'destination-over';
        ctx.drawImage(glowCanvas, 0, 0);
    }

    /**
     * Render inner shadow.
     *
     * Inner shadow creates a shadow INSIDE the shape, as if the shape is cut out
     * and casting a shadow on the surface below it.
     *
     * Technique: Create an inverted shape (hole in a filled canvas), apply shadow
     * to that hole, then clip to the original shape to keep only the inner portion.
     */
    renderInnerShadow(ctx, layer, effect, expansion) {
        const rgb = this.hexToRgb(effect.color);
        const shadowColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${effect.colorOpacity})`;

        const w = ctx.canvas.width;
        const h = ctx.canvas.height;

        // Step 1: Create canvas with the layer shape cut out (inverted)
        const invertedCanvas = document.createElement('canvas');
        invertedCanvas.width = w;
        invertedCanvas.height = h;
        const invertedCtx = invertedCanvas.getContext('2d');

        // Fill entire canvas with opaque color
        invertedCtx.fillStyle = '#000000';
        invertedCtx.fillRect(0, 0, w, h);

        // Cut out the layer shape to create a "hole"
        invertedCtx.globalCompositeOperation = 'destination-out';
        invertedCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Step 2: Draw the inverted shape with shadow
        // The shadow will bleed INTO the hole (which is our shape area)
        const shadowCanvas = document.createElement('canvas');
        shadowCanvas.width = w;
        shadowCanvas.height = h;
        const shadowCtx = shadowCanvas.getContext('2d');

        shadowCtx.shadowColor = shadowColor;
        shadowCtx.shadowBlur = effect.blur;
        shadowCtx.shadowOffsetX = effect.offsetX;
        shadowCtx.shadowOffsetY = effect.offsetY;

        // Draw the inverted shape - shadow bleeds into the hole
        shadowCtx.drawImage(invertedCanvas, 0, 0);

        // Step 3: Extract only the shadow part (remove the solid inverted shape)
        // by using destination-out to remove the original inverted mask
        shadowCtx.globalCompositeOperation = 'destination-out';
        shadowCtx.shadowColor = 'transparent';
        shadowCtx.shadowBlur = 0;
        shadowCtx.shadowOffsetX = 0;
        shadowCtx.shadowOffsetY = 0;
        shadowCtx.drawImage(invertedCanvas, 0, 0);

        // Step 4: Clip the shadow to the original layer shape
        const resultCanvas = document.createElement('canvas');
        resultCanvas.width = w;
        resultCanvas.height = h;
        const resultCtx = resultCanvas.getContext('2d');

        // Draw layer shape as mask
        resultCtx.drawImage(layer.canvas, expansion.left, expansion.top);
        // Keep only where shadow overlaps with layer
        resultCtx.globalCompositeOperation = 'source-in';
        resultCtx.drawImage(shadowCanvas, 0, 0);

        // Step 5: Composite onto the main context
        ctx.globalCompositeOperation = 'source-atop';
        ctx.drawImage(resultCanvas, 0, 0);
    }

    /**
     * Render inner glow.
     */
    renderInnerGlow(ctx, layer, effect, expansion) {
        const rgb = this.hexToRgb(effect.color);
        const glowColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${effect.colorOpacity})`;

        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = ctx.canvas.width;
        tempCanvas.height = ctx.canvas.height;
        const tempCtx = tempCanvas.getContext('2d');

        // Create glow from edges
        tempCtx.fillStyle = glowColor;
        tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

        tempCtx.globalCompositeOperation = 'destination-out';
        tempCtx.filter = `blur(${effect.blur}px)`;
        tempCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Clip to layer shape
        const resultCanvas = document.createElement('canvas');
        resultCanvas.width = ctx.canvas.width;
        resultCanvas.height = ctx.canvas.height;
        const resultCtx = resultCanvas.getContext('2d');

        resultCtx.drawImage(layer.canvas, expansion.left, expansion.top);
        resultCtx.globalCompositeOperation = 'source-in';
        resultCtx.drawImage(tempCanvas, 0, 0);

        ctx.globalCompositeOperation = 'source-atop';
        ctx.drawImage(resultCanvas, 0, 0);
    }

    /**
     * Render stroke effect.
     *
     * Stroke positions:
     * - outside: stroke ring outside the shape boundary
     * - inside: stroke ring inside the shape boundary
     * - center: stroke centered on the boundary (half in, half out)
     *
     * Algorithm uses morphological dilation/erosion via offset drawing.
     */
    renderStroke(ctx, layer, effect, expansion) {
        const rgb = this.hexToRgb(effect.color);
        const strokeColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${effect.colorOpacity})`;
        const size = effect.size;
        const w = ctx.canvas.width;
        const h = ctx.canvas.height;

        if (size <= 0) return;

        /**
         * Helper to create dilated (expanded) shape by drawing at offset positions
         */
        const createDilatedShape = (amount) => {
            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const c = canvas.getContext('2d');

            // Draw at multiple angle offsets for smooth dilation
            const steps = Math.max(24, Math.ceil(amount * 4));
            for (let i = 0; i < steps; i++) {
                const angle = (i / steps) * Math.PI * 2;
                const ox = Math.cos(angle) * amount;
                const oy = Math.sin(angle) * amount;
                c.drawImage(layer.canvas, expansion.left + ox, expansion.top + oy);
            }
            // Also draw center
            c.drawImage(layer.canvas, expansion.left, expansion.top);
            return canvas;
        };

        /**
         * Helper to create eroded (shrunk) shape by intersecting inward-offset copies
         */
        const createErodedShape = (amount) => {
            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const c = canvas.getContext('2d');

            // Start with original shape
            c.drawImage(layer.canvas, expansion.left, expansion.top);

            // For each offset direction, keep only intersection
            const steps = Math.max(16, Math.ceil(amount * 3));
            for (let i = 0; i < steps; i++) {
                const angle = (i / steps) * Math.PI * 2;
                const ox = Math.cos(angle) * amount;
                const oy = Math.sin(angle) * amount;

                // Create offset version
                const offsetCanvas = document.createElement('canvas');
                offsetCanvas.width = w;
                offsetCanvas.height = h;
                const oc = offsetCanvas.getContext('2d');
                oc.drawImage(layer.canvas, expansion.left - ox, expansion.top - oy);

                // Intersect with current result
                c.globalCompositeOperation = 'destination-in';
                c.drawImage(offsetCanvas, 0, 0);
            }
            return canvas;
        };

        // Create the stroke ring based on position
        const strokeCanvas = document.createElement('canvas');
        strokeCanvas.width = w;
        strokeCanvas.height = h;
        const strokeCtx = strokeCanvas.getContext('2d');

        if (effect.position === 'outside') {
            // Outside: dilated shape minus original shape
            const dilated = createDilatedShape(size);
            strokeCtx.drawImage(dilated, 0, 0);
            strokeCtx.globalCompositeOperation = 'destination-out';
            strokeCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        } else if (effect.position === 'inside') {
            // Inside: original shape minus eroded shape
            strokeCtx.drawImage(layer.canvas, expansion.left, expansion.top);
            const eroded = createErodedShape(size);
            strokeCtx.globalCompositeOperation = 'destination-out';
            strokeCtx.drawImage(eroded, 0, 0);

        } else {
            // Center: dilated by half minus eroded by half
            const halfSize = size / 2;
            const dilated = createDilatedShape(halfSize);
            const eroded = createErodedShape(halfSize);
            strokeCtx.drawImage(dilated, 0, 0);
            strokeCtx.globalCompositeOperation = 'destination-out';
            strokeCtx.drawImage(eroded, 0, 0);
        }

        // Fill the stroke ring with color
        strokeCtx.globalCompositeOperation = 'source-in';
        strokeCtx.fillStyle = strokeColor;
        strokeCtx.fillRect(0, 0, w, h);

        // Composite the stroke onto the result
        if (effect.position === 'outside') {
            // Draw behind the layer content
            ctx.globalCompositeOperation = 'destination-over';
            ctx.drawImage(strokeCanvas, 0, 0);
        } else if (effect.position === 'inside') {
            // Draw on top of layer content (replaces edge pixels)
            ctx.globalCompositeOperation = 'source-atop';
            ctx.drawImage(strokeCanvas, 0, 0);
        } else {
            // Center: has both inside and outside parts
            // First draw outside part behind
            ctx.globalCompositeOperation = 'destination-over';
            ctx.drawImage(strokeCanvas, 0, 0);
            // The inside part is already in strokeCanvas and overlaps layer
        }
    }

    /**
     * Render color overlay.
     */
    renderColorOverlay(ctx, layer, effect, expansion) {
        const overlayCanvas = document.createElement('canvas');
        overlayCanvas.width = ctx.canvas.width;
        overlayCanvas.height = ctx.canvas.height;
        const overlayCtx = overlayCanvas.getContext('2d');

        // Draw layer shape
        overlayCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Fill with color using source-in
        overlayCtx.globalCompositeOperation = 'source-in';
        overlayCtx.fillStyle = effect.color;
        overlayCtx.fillRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        ctx.globalCompositeOperation = 'source-atop';
        ctx.drawImage(overlayCanvas, 0, 0);
    }

    /**
     * Render bevel/emboss effect.
     *
     * Bevel creates a 3D raised/lowered appearance by adding highlights on
     * edges facing the light and shadows on edges facing away.
     *
     * For inner bevel:
     * - Highlight on the inner edge toward the light (top-left for angle 135)
     * - Shadow on the inner edge away from the light (bottom-right for angle 135)
     *
     * Algorithm:
     * 1. Create "edge ring" by subtracting eroded shape from original
     * 2. Split edge ring based on light angle - highlight half and shadow half
     */
    renderBevelEmboss(ctx, layer, effect, expansion) {
        const w = ctx.canvas.width;
        const h = ctx.canvas.height;

        const highlightRgb = this.hexToRgb(effect.highlightColor);
        const shadowRgb = this.hexToRgb(effect.shadowColor);

        const angleRad = effect.angle * Math.PI / 180;
        const size = effect.size || effect.depth || 3;
        const dirMult = effect.direction === 'down' ? -1 : 1;

        // Light direction vector (normalized)
        const lightDirX = Math.cos(angleRad) * dirMult;
        const lightDirY = -Math.sin(angleRad) * dirMult;

        // For inner bevel, we need to find the INNER edges of the shape
        // Technique: original shape minus an eroded (shrunk) version = edge ring
        // Then color half of the ring as highlight, half as shadow based on edge direction

        // Step 1: Create edge ring (original - eroded)
        const edgeCanvas = document.createElement('canvas');
        edgeCanvas.width = w;
        edgeCanvas.height = h;
        const edgeCtx = edgeCanvas.getContext('2d');

        // Draw original shape
        edgeCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        // Create eroded shape by intersecting offset copies
        const erodedCanvas = document.createElement('canvas');
        erodedCanvas.width = w;
        erodedCanvas.height = h;
        const erodedCtx = erodedCanvas.getContext('2d');
        erodedCtx.drawImage(layer.canvas, expansion.left, expansion.top);

        const steps = Math.max(16, size * 2);
        for (let i = 0; i < steps; i++) {
            const angle = (i / steps) * Math.PI * 2;
            const ox = Math.cos(angle) * size;
            const oy = Math.sin(angle) * size;

            const offsetCanvas = document.createElement('canvas');
            offsetCanvas.width = w;
            offsetCanvas.height = h;
            const oc = offsetCanvas.getContext('2d');
            oc.drawImage(layer.canvas, expansion.left - ox, expansion.top - oy);

            erodedCtx.globalCompositeOperation = 'destination-in';
            erodedCtx.drawImage(offsetCanvas, 0, 0);
        }

        // Edge ring = original - eroded
        edgeCtx.globalCompositeOperation = 'destination-out';
        edgeCtx.drawImage(erodedCanvas, 0, 0);

        // Step 2: For each pixel in the edge ring, determine if it's highlight or shadow
        // based on its position relative to the eroded center
        const edgeData = edgeCtx.getImageData(0, 0, w, h);
        const erodedData = erodedCtx.getImageData(0, 0, w, h);

        const highlightCanvas = document.createElement('canvas');
        highlightCanvas.width = w;
        highlightCanvas.height = h;
        const highlightCtx = highlightCanvas.getContext('2d');

        const shadowCanvas = document.createElement('canvas');
        shadowCanvas.width = w;
        shadowCanvas.height = h;
        const shadowCtx = shadowCanvas.getContext('2d');

        // Simpler approach: use offset masks to separate highlight/shadow
        // Highlight: where original offset toward light intersects with edge
        // Shadow: where original offset away from light intersects with edge

        // Highlight edge: part of edge ring facing the light
        highlightCtx.drawImage(layer.canvas, expansion.left + lightDirX * size, expansion.top + lightDirY * size);
        highlightCtx.globalCompositeOperation = 'destination-in';
        highlightCtx.drawImage(edgeCanvas, 0, 0);

        // Shadow edge: part of edge ring facing away from light
        shadowCtx.drawImage(layer.canvas, expansion.left - lightDirX * size, expansion.top - lightDirY * size);
        shadowCtx.globalCompositeOperation = 'destination-in';
        shadowCtx.drawImage(edgeCanvas, 0, 0);

        // Apply soften blur
        const soften = effect.soften || 0;
        if (soften > 0) {
            highlightCtx.filter = `blur(${soften}px)`;
            highlightCtx.drawImage(highlightCanvas, 0, 0);
            shadowCtx.filter = `blur(${soften}px)`;
            shadowCtx.drawImage(shadowCanvas, 0, 0);
        }

        // Fill with colors
        highlightCtx.filter = 'none';
        highlightCtx.globalCompositeOperation = 'source-in';
        highlightCtx.fillStyle = `rgba(${highlightRgb.r}, ${highlightRgb.g}, ${highlightRgb.b}, ${effect.highlightOpacity})`;
        highlightCtx.fillRect(0, 0, w, h);

        shadowCtx.filter = 'none';
        shadowCtx.globalCompositeOperation = 'source-in';
        shadowCtx.fillStyle = `rgba(${shadowRgb.r}, ${shadowRgb.g}, ${shadowRgb.b}, ${effect.shadowOpacity})`;
        shadowCtx.fillRect(0, 0, w, h);

        // Apply to context
        if (effect.style === 'innerBevel' || effect.style === 'pillowEmboss') {
            ctx.globalCompositeOperation = 'source-atop';
        } else {
            ctx.globalCompositeOperation = 'destination-over';
        }
        ctx.drawImage(highlightCanvas, 0, 0);
        ctx.drawImage(shadowCanvas, 0, 0);
    }

    /**
     * Convert hex color to RGB.
     */
    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : { r: 0, g: 0, b: 0 };
    }

    /**
     * Invalidate cache for a layer.
     * @param {string} layerId
     */
    invalidate(layerId) {
        this.cache.delete(layerId);
        this.pendingRenders.delete(layerId);
    }

    /**
     * Clear all caches.
     */
    clearAll() {
        this.cache.clear();
        this.pendingRenders.clear();
    }
}

// Singleton instance
export const effectRenderer = new EffectRenderer();
