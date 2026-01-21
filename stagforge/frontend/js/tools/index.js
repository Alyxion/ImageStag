/**
 * Tools Index - Auto-discovery and group building
 *
 * Tools are self-describing via static properties. This module:
 * - Imports all tools
 * - Extracts metadata from static properties
 * - Auto-builds groups sorted by priority
 * - Provides icon lookups from tool definitions
 * - Supports filtering for limited mode
 */

// Import all tools
import { BlurTool } from './BlurTool.js';
import { BrushTool } from './BrushTool.js';
import { BurnTool } from './BurnTool.js';
import { CircleTool } from './CircleTool.js';
import { CloneStampTool } from './CloneStampTool.js';
import { CropTool } from './CropTool.js';
import { DodgeTool } from './DodgeTool.js';
import { EraserTool } from './EraserTool.js';
import { EyedropperTool } from './EyedropperTool.js';
import { FillTool } from './FillTool.js';
import { GradientTool } from './GradientTool.js';
import { HandTool } from './HandTool.js';
import { LassoTool } from './LassoTool.js';
import { LineTool } from './LineTool.js';
import { MagicWandTool } from './MagicWandTool.js';
import { MoveTool } from './MoveTool.js';
import { PencilTool } from './PencilTool.js';
import { PenTool } from './PenTool.js';
import { PolygonTool } from './PolygonTool.js';
import { RectTool } from './RectTool.js';
import { SelectionTool } from './SelectionTool.js';
import { ShapeTool } from './ShapeTool.js';
import { SharpenTool } from './SharpenTool.js';
import { SmudgeTool } from './SmudgeTool.js';
import { SpongeTool } from './SpongeTool.js';
import { SprayTool } from './SprayTool.js';
import { TextTool } from './TextTool.js';
import { VectorShapeEditTool } from './VectorShapeEditTool.js';

/**
 * All available tool classes
 */
export const allTools = [
    SelectionTool,
    LassoTool,
    MagicWandTool,
    MoveTool,
    CropTool,
    HandTool,
    BrushTool,
    PencilTool,
    SprayTool,
    EraserTool,
    CloneStampTool,
    SmudgeTool,
    BlurTool,
    SharpenTool,
    DodgeTool,
    BurnTool,
    SpongeTool,
    PenTool,
    VectorShapeEditTool,
    RectTool,
    CircleTool,
    PolygonTool,
    ShapeTool,
    LineTool,
    FillTool,
    GradientTool,
    TextTool,
    EyedropperTool,
];

/**
 * Tool metadata extracted from static properties
 */
export const toolMetadata = allTools.map(Tool => ({
    id: Tool.id,
    name: Tool.name,
    icon: Tool.icon || Tool.id,
    iconEntity: Tool.iconEntity || '&#9679;',
    shortcut: Tool.shortcut || null,
    group: Tool.group || 'misc',
    groupShortcut: Tool.groupShortcut || null,
    priority: Tool.priority ?? 100,
    cursor: Tool.cursor || 'crosshair',
    limitedMode: Tool.limitedMode || false,
    Tool: Tool,
}));

/**
 * Tool lookup by ID
 */
export const toolsById = Object.fromEntries(
    allTools.map(Tool => [Tool.id, Tool])
);

/**
 * Icon entity lookup by tool ID or icon name
 * Auto-built from tool metadata, includes both id and icon mappings
 */
export const toolIcons = Object.fromEntries([
    // Map by tool id
    ...toolMetadata.map(t => [t.id, t.iconEntity]),
    // Map by icon name (if different from id)
    ...toolMetadata.filter(t => t.icon !== t.id).map(t => [t.icon, t.iconEntity]),
]);

/**
 * Get icon entity for a tool
 * @param {string} toolId - Tool or icon identifier
 * @returns {string} HTML entity
 */
export function getToolIcon(toolId) {
    return toolIcons[toolId] || '&#9679;';
}

/**
 * Group order for toolbar display (top to bottom)
 */
const groupOrder = [
    'selection', 'freeform', 'quicksel',  // Selection tools
    'move', 'crop', 'hand',               // Navigation
    'brush', 'eraser',                    // Drawing
    'stamp', 'retouch', 'dodge',          // Retouching
    'pen', 'shapes',                      // Vector
    'fill', 'text', 'eyedropper',         // Other
    'misc'                                // Fallback
];

/**
 * Auto-build tool groups from tool metadata
 * Groups are sorted by groupOrder, tools within groups by priority
 */
export function buildToolGroups() {
    // Group tools by their group property
    const grouped = {};
    for (const tool of toolMetadata) {
        const group = tool.group;
        if (!grouped[group]) {
            grouped[group] = {
                id: group,
                name: group.charAt(0).toUpperCase() + group.slice(1),
                shortcut: null,
                tools: []
            };
        }
        grouped[group].tools.push(tool);
        // Take group shortcut from first tool that defines it
        if (tool.groupShortcut && !grouped[group].shortcut) {
            grouped[group].shortcut = tool.groupShortcut;
        }
    }

    // Sort tools within each group by priority
    for (const group of Object.values(grouped)) {
        group.tools.sort((a, b) => a.priority - b.priority);
    }

    // Build final array sorted by groupOrder
    const result = [];
    for (const groupId of groupOrder) {
        if (grouped[groupId]) {
            result.push(grouped[groupId]);
            delete grouped[groupId];
        }
    }
    // Add any remaining groups not in groupOrder
    for (const group of Object.values(grouped)) {
        result.push(group);
    }

    return result;
}

/**
 * Pre-built tool groups for toolbar
 */
export const toolGroups = buildToolGroups();

/**
 * Get tools available in limited mode
 * @param {string[]} excludeNames - Tool IDs to exclude
 * @returns {Object[]} Filtered tool metadata
 */
export function getLimitedModeTools(excludeNames = []) {
    return toolMetadata.filter(t =>
        t.limitedMode && !excludeNames.includes(t.id)
    );
}

/**
 * Get tools by specific IDs
 * @param {string[]} toolIds - Tool IDs to include
 * @returns {Object[]} Filtered tool metadata
 */
export function getToolsByIds(toolIds) {
    return toolIds
        .map(id => toolMetadata.find(t => t.id === id))
        .filter(Boolean);
}

/**
 * Register all tools with a ToolManager instance
 * @param {ToolManager} toolManager - The tool manager to register with
 */
export function registerAllTools(toolManager) {
    for (const Tool of allTools) {
        toolManager.register(Tool);
    }
}

// Named exports for individual tools
export {
    BlurTool,
    BrushTool,
    BurnTool,
    CircleTool,
    CloneStampTool,
    CropTool,
    DodgeTool,
    EraserTool,
    EyedropperTool,
    FillTool,
    GradientTool,
    HandTool,
    LassoTool,
    LineTool,
    MagicWandTool,
    MoveTool,
    PencilTool,
    PenTool,
    PolygonTool,
    RectTool,
    SelectionTool,
    ShapeTool,
    SharpenTool,
    SmudgeTool,
    SpongeTool,
    SprayTool,
    TextTool,
    VectorShapeEditTool,
};
