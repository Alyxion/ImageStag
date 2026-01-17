/**
 * Layer Effects Module
 *
 * Exports all effect classes, the registry, and utility functions.
 * This module provides layer effects.
 */

// Base class and registration
import { LayerEffect, setEffectRegistry } from './LayerEffect.js';

// Individual effects
import { DropShadowEffect } from './DropShadowEffect.js';
import { InnerShadowEffect } from './InnerShadowEffect.js';
import { OuterGlowEffect } from './OuterGlowEffect.js';
import { InnerGlowEffect } from './InnerGlowEffect.js';
import { BevelEmbossEffect } from './BevelEmbossEffect.js';
import { StrokeEffect } from './StrokeEffect.js';
import { ColorOverlayEffect } from './ColorOverlayEffect.js';

/**
 * Registry of effect types for deserialization.
 */
export const effectRegistry = {
    dropShadow: DropShadowEffect,
    innerShadow: InnerShadowEffect,
    outerGlow: OuterGlowEffect,
    innerGlow: InnerGlowEffect,
    bevelEmboss: BevelEmbossEffect,
    stroke: StrokeEffect,
    colorOverlay: ColorOverlayEffect
};

// Set the registry for LayerEffect.deserialize()
setEffectRegistry(effectRegistry);

/**
 * Order effects should be applied (bottom to top).
 * Standard layer effect stacking order.
 */
export const effectRenderOrder = [
    'dropShadow',      // Behind layer
    'outerGlow',       // Behind layer
    'innerShadow',     // On layer
    'innerGlow',       // On layer
    'bevelEmboss',     // On layer
    'colorOverlay',    // On layer
    'stroke'           // On top of layer
];

/**
 * Get list of all available effect types.
 * @returns {Array<{type: string, displayName: string}>}
 */
export function getAvailableEffects() {
    return Object.entries(effectRegistry).map(([type, cls]) => ({
        type,
        displayName: cls.displayName
    }));
}

// Re-export all classes for direct import
export {
    LayerEffect,
    DropShadowEffect,
    InnerShadowEffect,
    OuterGlowEffect,
    InnerGlowEffect,
    BevelEmbossEffect,
    StrokeEffect,
    ColorOverlayEffect
};
