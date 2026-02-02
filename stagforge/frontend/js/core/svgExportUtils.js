/**
 * SVG Export Utilities for Stagforge Document Format.
 *
 * Provides utilities for exporting documents as SVG with embedded Stagforge
 * metadata that enables lossless round-trip: Save as SVG → Load = identical document.
 *
 * SVG Structure:
 * - Uses sf: namespace (http://stagforge.io/xmlns/2026) for custom attributes
 * - Layers stored as <g> elements with sf:type, sf:name attributes
 * - Properties stored in <sf:properties> elements as XML
 * - Raster data embedded as PNG data URLs in <image> elements
 * - Layers ordered bottom-to-top (SVG painter's algorithm)
 */

/** Stagforge XML namespace URI */
export const STAGFORGE_NAMESPACE = 'http://stagforge.io/xmlns/2026';

/** Stagforge SVG format version */
export const STAGFORGE_VERSION = '1';

/** Stagforge namespace prefix */
export const STAGFORGE_PREFIX = 'sf';

/**
 * Check if an SVG string is a Stagforge document.
 * A Stagforge SVG must have both the namespace declaration and version attribute.
 *
 * @param {string} svgString - Raw SVG string
 * @returns {boolean} True if this is a Stagforge document
 */
export function isStagforgeSVG(svgString) {
    if (!svgString || typeof svgString !== 'string') {
        return false;
    }
    // Must have both namespace and version attribute
    return svgString.includes(`xmlns:${STAGFORGE_PREFIX}="${STAGFORGE_NAMESPACE}"`) &&
           svgString.includes(`${STAGFORGE_PREFIX}:version=`);
}

/**
 * Convert a JavaScript object to Stagforge XML elements.
 * Handles nested objects, arrays, and primitive values.
 *
 * @param {Object} obj - Object to convert
 * @param {Document} xmlDoc - XML document for creating elements
 * @param {Element} [parentElement] - Parent element to append to (optional)
 * @returns {Element|DocumentFragment} XML element(s) representing the object
 */
export function jsonToStagforgeXML(obj, xmlDoc, parentElement = null) {
    const fragment = parentElement || xmlDoc.createDocumentFragment();

    for (const [key, value] of Object.entries(obj)) {
        // Skip undefined values
        if (value === undefined) continue;

        const element = xmlDoc.createElementNS(STAGFORGE_NAMESPACE, `${STAGFORGE_PREFIX}:${key}`);

        if (value === null) {
            element.textContent = 'null';
            element.setAttribute('type', 'null');
        } else if (typeof value === 'boolean') {
            element.textContent = value.toString();
            element.setAttribute('type', 'boolean');
        } else if (typeof value === 'number') {
            element.textContent = value.toString();
            element.setAttribute('type', 'number');
        } else if (typeof value === 'string') {
            element.textContent = value;
            // No type attribute needed for strings (default)
        } else if (Array.isArray(value)) {
            // Arrays are stored as JSON strings for simplicity
            element.textContent = JSON.stringify(value);
            element.setAttribute('type', 'array');
        } else if (typeof value === 'object') {
            // Objects are stored as JSON strings for simplicity
            element.textContent = JSON.stringify(value);
            element.setAttribute('type', 'object');
        }

        fragment.appendChild(element);
    }

    return fragment;
}

/**
 * Parse Stagforge XML elements back to a JavaScript object.
 *
 * @param {Element} parentElement - Parent element containing sf:* children
 * @returns {Object} Parsed JavaScript object
 */
export function stagforgeXMLToJSON(parentElement) {
    const result = {};

    for (const child of parentElement.children) {
        // Only process elements in the Stagforge namespace
        if (child.namespaceURI !== STAGFORGE_NAMESPACE) continue;

        // Get local name without namespace prefix
        const key = child.localName;
        const type = child.getAttribute('type');
        const text = child.textContent;

        if (type === 'null') {
            result[key] = null;
        } else if (type === 'boolean') {
            result[key] = text === 'true';
        } else if (type === 'number') {
            result[key] = parseFloat(text);
        } else if (type === 'array' || type === 'object') {
            try {
                result[key] = JSON.parse(text);
            } catch (e) {
                console.warn(`Failed to parse ${key} as JSON:`, e);
                result[key] = text;
            }
        } else {
            // Default: string
            result[key] = text;
        }
    }

    return result;
}

/**
 * Create the root SVG element with Stagforge namespace and attributes.
 *
 * @param {Document} xmlDoc - XML document
 * @param {number} width - Document width
 * @param {number} height - Document height
 * @returns {Element} Root SVG element
 */
export function createStagforgeSVGRoot(xmlDoc, width, height) {
    const svg = xmlDoc.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttributeNS('http://www.w3.org/2000/xmlns/', `xmlns:${STAGFORGE_PREFIX}`, STAGFORGE_NAMESPACE);
    svg.setAttribute('width', width.toString());
    svg.setAttribute('height', height.toString());
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.setAttributeNS(STAGFORGE_NAMESPACE, `${STAGFORGE_PREFIX}:version`, STAGFORGE_VERSION);
    svg.setAttributeNS(STAGFORGE_NAMESPACE, `${STAGFORGE_PREFIX}:software`, 'Stagforge 1.0');
    return svg;
}

/**
 * Create the metadata element with document properties.
 *
 * @param {Document} xmlDoc - XML document
 * @param {Object} docProps - Document properties
 * @returns {Element} Metadata element
 */
export function createDocumentMetadata(xmlDoc, docProps) {
    const metadata = xmlDoc.createElementNS('http://www.w3.org/2000/svg', 'metadata');
    const sfDocument = xmlDoc.createElementNS(STAGFORGE_NAMESPACE, `${STAGFORGE_PREFIX}:document`);

    jsonToStagforgeXML(docProps, xmlDoc, sfDocument);
    metadata.appendChild(sfDocument);

    return metadata;
}

/**
 * Create a layer group element with Stagforge attributes.
 *
 * @param {Document} xmlDoc - XML document
 * @param {string} id - Layer ID
 * @param {string} type - Layer type (raster, text, svg, group)
 * @param {string} name - Layer name
 * @returns {Element} Group element
 */
export function createLayerGroup(xmlDoc, id, type, name) {
    const g = xmlDoc.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('id', id);
    g.setAttributeNS(STAGFORGE_NAMESPACE, `${STAGFORGE_PREFIX}:type`, type);
    g.setAttributeNS(STAGFORGE_NAMESPACE, `${STAGFORGE_PREFIX}:name`, name);
    return g;
}

/**
 * Create a properties element for a layer.
 *
 * @param {Document} xmlDoc - XML document
 * @param {Object} properties - Layer properties
 * @returns {Element} Properties element
 */
export function createPropertiesElement(xmlDoc, properties) {
    const sfProps = xmlDoc.createElementNS(STAGFORGE_NAMESPACE, `${STAGFORGE_PREFIX}:properties`);
    jsonToStagforgeXML(properties, xmlDoc, sfProps);
    return sfProps;
}

/**
 * Serialize an XML document to a string with XML declaration.
 *
 * @param {Document} xmlDoc - XML document
 * @returns {string} Serialized XML string
 */
export function serializeXML(xmlDoc) {
    const serializer = new XMLSerializer();
    const xmlString = serializer.serializeToString(xmlDoc);
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xmlString;
}

/**
 * Parse an SVG string into an XML document.
 *
 * @param {string} svgString - SVG string
 * @returns {Document} Parsed XML document
 */
export function parseSVG(svgString) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgString, 'image/svg+xml');

    // Check for parse errors
    const parseError = doc.querySelector('parsererror');
    if (parseError) {
        throw new Error('Failed to parse SVG: ' + parseError.textContent);
    }

    return doc;
}

/**
 * Get layer type from sf:type attribute.
 *
 * @param {Element} element - Layer group element
 * @returns {string|null} Layer type or null
 */
export function getLayerType(element) {
    return element.getAttributeNS(STAGFORGE_NAMESPACE, 'type');
}

/**
 * Get layer name from sf:name attribute.
 *
 * @param {Element} element - Layer group element
 * @returns {string|null} Layer name or null
 */
export function getLayerName(element) {
    return element.getAttributeNS(STAGFORGE_NAMESPACE, 'name');
}

/**
 * Get properties element from a layer group.
 *
 * @param {Element} layerGroup - Layer group element
 * @returns {Element|null} Properties element or null
 */
export function getPropertiesElement(layerGroup) {
    // Look for sf:properties element
    for (const child of layerGroup.children) {
        if (child.namespaceURI === STAGFORGE_NAMESPACE && child.localName === 'properties') {
            return child;
        }
    }
    return null;
}

/**
 * Get document metadata from SVG.
 *
 * @param {Document} xmlDoc - Parsed SVG document
 * @returns {Object|null} Document properties or null
 */
export function getDocumentMetadata(xmlDoc) {
    const metadata = xmlDoc.querySelector('metadata');
    if (!metadata) return null;

    // Find sf:document element
    for (const child of metadata.children) {
        if (child.namespaceURI === STAGFORGE_NAMESPACE && child.localName === 'document') {
            return stagforgeXMLToJSON(child);
        }
    }
    return null;
}

/**
 * Get layer groups from SVG document.
 * Returns groups in document order (bottom to top for rendering).
 *
 * @param {Document} xmlDoc - Parsed SVG document
 * @returns {Element[]} Array of layer group elements
 */
export function getLayerGroups(xmlDoc) {
    const svg = xmlDoc.documentElement;
    const groups = [];

    for (const child of svg.children) {
        // Skip metadata element
        if (child.tagName === 'metadata') continue;

        // Check if it's a group with sf:type attribute
        if (child.tagName === 'g' && child.getAttributeNS(STAGFORGE_NAMESPACE, 'type')) {
            groups.push(child);
        }
    }

    return groups;
}

/**
 * Get image element from a raster layer group.
 *
 * @param {Element} layerGroup - Layer group element
 * @returns {Element|null} Image element or null
 */
export function getImageElement(layerGroup) {
    return layerGroup.querySelector('image');
}

/**
 * Get inner SVG content from an SVG layer group.
 *
 * @param {Element} layerGroup - Layer group element
 * @returns {Element|null} Inner SVG/group element or null
 */
export function getInnerSVGContent(layerGroup) {
    // Look for nested <g> or <svg> element (not sf:properties)
    for (const child of layerGroup.children) {
        if (child.namespaceURI === STAGFORGE_NAMESPACE) continue;
        if (child.tagName === 'g' || child.tagName === 'svg') {
            return child;
        }
    }
    return null;
}

/**
 * Extract text content elements from a text layer group.
 *
 * @param {Element} layerGroup - Layer group element
 * @returns {Element[]} Array of text elements
 */
export function getTextElements(layerGroup) {
    const elements = [];
    const walker = (el) => {
        if (el.tagName === 'text') {
            elements.push(el);
        }
        for (const child of el.children) {
            walker(child);
        }
    };
    walker(layerGroup);
    return elements;
}

/**
 * "Debake" an SVG layer - extract the original SVG content from the transform envelope.
 *
 * The exported SVG structure is:
 *   <g transform="translate(cx,cy) rotate(r) scale(sx,sy) translate(-natW/2,-natH/2)">
 *     <svg width="natW" height="natH" viewBox="...">...original content...</svg>
 *   </g>
 *
 * This function extracts the inner <svg> element and returns it as a string.
 *
 * @param {Element} layerGroup - Layer group element containing the transform wrapper
 * @returns {string} The original SVG content as a string, or empty string if not found
 */
export function debakeSVGContent(layerGroup) {
    // Find the transform group (first <g> that's not sf:properties)
    let transformGroup = null;
    for (const child of layerGroup.children) {
        if (child.namespaceURI === STAGFORGE_NAMESPACE) continue;
        if (child.tagName === 'g') {
            transformGroup = child;
            break;
        }
    }

    if (!transformGroup) return '';

    // Find the inner <svg> element
    const innerSvg = transformGroup.querySelector('svg');
    if (!innerSvg) return '';

    // Serialize the inner SVG
    const serializer = new XMLSerializer();
    return serializer.serializeToString(innerSvg);
}

/**
 * Map layer type string to sf:type attribute value.
 *
 * @param {string} layerType - Internal layer type
 * @returns {string} SVG sf:type value
 */
export function layerTypeToSVGType(layerType) {
    switch (layerType) {
        case 'raster': return 'raster';
        case 'text': return 'text';
        case 'svg': return 'svg';
        case 'vector': return 'vector';
        case 'group': return 'group';
        default: return layerType;
    }
}

/**
 * Map sf:type attribute value to internal layer type.
 *
 * @param {string} svgType - SVG sf:type value
 * @returns {string} Internal layer type
 */
export function svgTypeToLayerType(svgType) {
    // They map 1:1 currently
    return svgType;
}
