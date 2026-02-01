/**
 * DocumentNameGenerator - Generate memorable random names for documents.
 *
 * Creates names like "Velvet Sunset", "Dreamy Bokeh", "Golden Canvas"
 * using art, photography, and painting themed words.
 *
 * Each adjective has a color and each noun has an emoji.
 * Data is loaded from JSON config files.
 */

// Cache for loaded data
let adjectivesData = null;
let nounsData = null;
let iconPickerData = null;

/**
 * Load adjectives from JSON config.
 * @returns {Promise<Array<{word: string, color: string}>>}
 */
async function loadAdjectives() {
    if (adjectivesData) return adjectivesData;

    try {
        const response = await fetch('/static/js/config/document-adjectives.json');
        const data = await response.json();
        adjectivesData = data.adjectives;
        return adjectivesData;
    } catch (error) {
        console.error('Failed to load adjectives:', error);
        // Fallback minimal set
        adjectivesData = [
            { word: 'luminous', color: '#F6D365' },
            { word: 'velvet', color: '#9B59B6' },
            { word: 'dreamy', color: '#BB8FCE' }
        ];
        return adjectivesData;
    }
}

/**
 * Load nouns from JSON config.
 * @returns {Promise<Array<{word: string, icon: string}>>}
 */
async function loadNouns() {
    if (nounsData) return nounsData;

    try {
        const response = await fetch('/static/js/config/document-nouns.json');
        const data = await response.json();
        nounsData = data.nouns;
        return nounsData;
    } catch (error) {
        console.error('Failed to load nouns:', error);
        // Fallback minimal set
        nounsData = [
            { word: 'canvas', icon: '🎨' },
            { word: 'sunset', icon: '🌅' },
            { word: 'dream', icon: '💭' }
        ];
        return nounsData;
    }
}

/**
 * Load icon picker icons from JSON config.
 * @returns {Promise<Array<string>>}
 */
export async function loadIconPicker() {
    if (iconPickerData) return iconPickerData;

    try {
        const response = await fetch('/static/js/config/icon-picker.json');
        const data = await response.json();
        iconPickerData = data.icons;
        return iconPickerData;
    } catch (error) {
        console.error('Failed to load icon picker:', error);
        // Fallback minimal set
        iconPickerData = ['🎨', '📷', '✨', '🖼️', '🎭', '💎', '🌸', '🦋', '🌊', '⭐'];
        return iconPickerData;
    }
}

/**
 * Preload all config data.
 * Call this early to avoid delays when generating names.
 */
export async function preloadConfigs() {
    await Promise.all([
        loadAdjectives(),
        loadNouns(),
        loadIconPicker()
    ]);
}

/**
 * Get adjectives (sync, returns cached or empty).
 * @returns {Array<{word: string, color: string}>}
 */
export function getAdjectives() {
    return adjectivesData || [];
}

/**
 * Get nouns (sync, returns cached or empty).
 * @returns {Array<{word: string, icon: string}>}
 */
export function getNouns() {
    return nounsData || [];
}

/**
 * Get icon picker icons (sync, returns cached or empty).
 * @returns {Array<string>}
 */
export function getIconPicker() {
    return iconPickerData || [];
}

/**
 * Generate a random document identity (name, icon, color).
 * Uses cached data - call preloadConfigs() first for best results.
 * @returns {{name: string, icon: string, color: string}}
 */
export function generateDocumentIdentity() {
    const adjectives = getAdjectives();
    const nouns = getNouns();

    // Fallback if data not loaded
    if (adjectives.length === 0 || nouns.length === 0) {
        return {
            name: 'New Document',
            icon: '🎨',
            color: '#E0E7FF'
        };
    }

    const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];

    // Capitalize first letter of each word
    const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1);
    const name = `${capitalize(adjective.word)} ${capitalize(noun.word)}`;

    return {
        name,
        icon: noun.icon,
        color: adjective.color
    };
}

/**
 * Generate a random document identity (async version).
 * Ensures data is loaded before generating.
 * @returns {Promise<{name: string, icon: string, color: string}>}
 */
export async function generateDocumentIdentityAsync() {
    await Promise.all([loadAdjectives(), loadNouns()]);
    return generateDocumentIdentity();
}

/**
 * Generate a random document name.
 * @returns {string} A name like "Velvet Sunset" or "Dreamy Canvas"
 */
export function generateDocumentName() {
    return generateDocumentIdentity().name;
}

/**
 * Get a random adjective with its color.
 * @returns {{word: string, color: string}}
 */
export function getRandomAdjective() {
    const adjectives = getAdjectives();
    if (adjectives.length === 0) return { word: 'new', color: '#E0E7FF' };
    return adjectives[Math.floor(Math.random() * adjectives.length)];
}

/**
 * Get a random noun with its icon.
 * @returns {{word: string, icon: string}}
 */
export function getRandomNoun() {
    const nouns = getNouns();
    if (nouns.length === 0) return { word: 'document', icon: '🎨' };
    return nouns[Math.floor(Math.random() * nouns.length)];
}

/**
 * Generate multiple unique document identities.
 * @param {number} count - Number of identities to generate
 * @returns {Array<{name: string, icon: string, color: string}>}
 */
export function generateDocumentIdentities(count) {
    const identities = [];
    const usedNames = new Set();
    const maxAttempts = count * 10;
    let attempts = 0;

    while (identities.length < count && attempts < maxAttempts) {
        const identity = generateDocumentIdentity();
        if (!usedNames.has(identity.name)) {
            usedNames.add(identity.name);
            identities.push(identity);
        }
        attempts++;
    }

    return identities;
}

/**
 * Get the total number of possible combinations.
 * @returns {number}
 */
export function getCombinationCount() {
    return getAdjectives().length * getNouns().length;
}
