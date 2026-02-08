/**
 * FileManager - Handles SFR file save/load with File System Access API.
 *
 * SFR Format: ZIP archive containing:
 * - content.json: Document structure (layers reference external files)
 * - layers/{id}.webp: Raster layer images (WebP for 8-bit)
 * - layers/{id}.avif: Float layer images (future)
 * - layers/{id}.svg: SVG layers (future)
 *
 * Text and Vector layers are stored inline in content.json.
 *
 * Features:
 * - Save/load .sfr files (ZIP-based document format)
 * - File System Access API for persistent file handles
 * - Ctrl+S saves to original file
 * - Fallback download for unsupported browsers
 */

import { OPEN_IMAGE_ACCEPT, OPEN_IMAGE_ACCEPT_STRING, IMAGE_EXTENSIONS } from '../config/ExportConfig.js';

// Current SFR format version
const SFR_VERSION = 3;

/**
 * Convert Blob to data URL.
 * @param {Blob} blob
 * @returns {Promise<string>}
 */
function blobToDataURL(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

/**
 * Resolve a single imageFile reference in a layer or frame data object.
 * @param {Object} obj - Layer data or frame data with imageFile/imageFormat
 * @param {Map<string, Blob>} layerImages - Map of file key to image Blob
 */
async function resolveImageFile(obj, layerImages) {
    const imageFile = obj.imageFile;
    if (!imageFile) return;

    // Extract the key: strip 'layers/' prefix and file extension
    const key = imageFile.replace(/^layers\//, '').replace(/\.(webp|avif|png|svg)$/, '');

    if (layerImages.has(key)) {
        const blob = layerImages.get(key);

        if (obj.imageFormat === 'svg') {
            obj.svgContent = await blob.text();
        } else {
            obj.imageData = await blobToDataURL(blob);
        }

        delete obj.imageFile;
        delete obj.imageFormat;
    }
}

/**
 * Process layer images from ZIP into document data.
 * Handles pages, multi-frame layers, and single-frame layers.
 * Works with both v3 (pages) and v1/v2 (top-level layers) formats.
 * @param {Object} data - The content.json data
 * @param {Map<string, Blob>} layerImages - Map of file key to image Blob
 */
export async function processLayerImages(data, layerImages) {
    if (!layerImages || layerImages.size === 0) return;

    // Collect all layers from either pages (v3) or docData.layers (v1/v2)
    const allLayers = [];
    if (data.pages) {
        for (const page of data.pages) {
            allLayers.push(...(page.layers || []));
        }
    }
    if (data.document?.pages) {
        for (const page of data.document.pages) {
            allLayers.push(...(page.layers || []));
        }
    }
    if (data.document?.layers) {
        allLayers.push(...data.document.layers);
    }
    if (data.layers && !data.pages) {
        allLayers.push(...data.layers);
    }

    for (const layerData of allLayers) {
        // Handle multi-frame layers — resolve each frame's imageFile
        if (layerData.frames) {
            for (const frame of layerData.frames) {
                await resolveImageFile(frame, layerImages);
            }
        }

        // Handle single-frame / top-level imageFile
        await resolveImageFile(layerData, layerImages);
    }
}

/**
 * Convert canvas to WebP blob.
 * @param {HTMLCanvasElement} canvas
 * @param {number} quality - 0.0 to 1.0 (1.0 = lossless)
 * @returns {Promise<Blob>}
 */
async function canvasToWebP(canvas, quality = 1.0) {
    return new Promise((resolve, reject) => {
        canvas.toBlob(
            (blob) => {
                if (blob) {
                    resolve(blob);
                } else {
                    reject(new Error('Failed to convert canvas to WebP'));
                }
            },
            'image/webp',
            quality
        );
    });
}

/**
 * Serialize a layer for ZIP format (without inline image data for raster).
 * Handles layers, groups, SVG layers, and text layers.
 * @param {Layer|LayerGroup} layer
 * @returns {Object}
 */
function serializeLayerForZipStatic(layer) {
    // For groups, use full serialization (no image data needed)
    if (layer.isGroup && layer.isGroup()) {
        return layer.serialize();
    }

    // For vector, text, and SVG layers, use full serialization (includes inline data)
    if (layer.type === 'vector' || layer.type === 'text' || layer.type === 'svg') {
        return layer.serialize();
    }

    // For raster layers, use base serialize() but strip imageData
    // (image content is stored separately as WebP in the ZIP)
    const data = layer.serialize();
    delete data.imageData;
    return data;
}

/**
 * Save a single layer's image content to the ZIP, updating layerData with file references.
 * Handles both single-frame and multi-frame layers.
 * @param {Object} layer - The live layer object (for canvas access)
 * @param {Object} layerData - Serialized layer data to modify
 * @param {Object} layersFolder - JSZip folder for layer files
 */
async function saveLayerContentToZip(layer, layerData, layersFolder) {
    const isMultiFrame = layer.frameCount > 1;

    // Handle multi-frame layers — save each frame's content separately
    if (layerData.frames && layerData.frames.length > 0) {
        for (let i = 0; i < layerData.frames.length; i++) {
            const frame = layerData.frames[i];
            const suffix = isMultiFrame ? `_frame_${i}` : '';

            // SVG frame content
            if (frame.svgContent) {
                const filename = `${layer.id}${suffix}.svg`;
                layersFolder.file(filename, frame.svgContent);
                frame.imageFile = `layers/${filename}`;
                frame.imageFormat = 'svg';
                delete frame.svgContent;
            }
            // Raster frame content (imageData)
            else if (frame.imageData && frame.imageData.startsWith('data:')) {
                // Strip and re-encode as WebP from the live canvas
                const frameCanvas = layer.getCanvas?.(i);
                if (frameCanvas && frameCanvas.width > 0 && frameCanvas.height > 0) {
                    const webpBlob = await canvasToWebP(frameCanvas, 1.0);
                    const filename = `${layer.id}${suffix}.webp`;
                    layersFolder.file(filename, webpBlob);
                    frame.imageFile = `layers/${filename}`;
                    frame.imageFormat = 'webp';
                    delete frame.imageData;
                }
            }
        }
        return;
    }

    // Handle SVG layers (single-frame, no frames array)
    if (layerData.type === 'svg' && layerData.svgContent) {
        const filename = `${layer.id}.svg`;
        layersFolder.file(filename, layerData.svgContent);
        layerData.imageFile = `layers/${filename}`;
        layerData.imageFormat = 'svg';
        delete layerData.svgContent;
        return;
    }

    // Handle raster layers (single-frame, no frames array)
    if (layer.type !== 'vector' && layer.type !== 'text' && layer.type !== 'svg' && layer.canvas &&
        layer.canvas.width > 0 && layer.canvas.height > 0) {
        let webpBlob;

        // Use cached blob if available (avoids re-encoding unchanged layers)
        if (layer.hasValidImageCache && layer.hasValidImageCache()) {
            webpBlob = layer.getCachedImageBlob();
        } else {
            webpBlob = await canvasToWebP(layer.canvas, 1.0);
            if (layer.setCachedImageBlob) {
                layer.setCachedImageBlob(webpBlob);
            }
        }

        const filename = `${layer.id}.webp`;
        layersFolder.file(filename, webpBlob);
        layerData.imageFile = `layers/${filename}`;
        layerData.imageFormat = 'webp';
    }
}

/**
 * Serialize a document to SFR ZIP format (v3 with pages).
 * Standalone function usable by FileManager and AutoSave.
 * @param {Document} doc - The document to serialize
 * @returns {Promise<Blob>} ZIP blob
 */
export async function serializeDocumentToZip(doc) {
    if (!window.JSZip) {
        throw new Error('JSZip not loaded');
    }

    const zip = new window.JSZip();
    const layersFolder = zip.folder('layers');

    // Build pages array with layer data and image file references
    const pages = [];
    for (const page of doc.pages) {
        const layers = [];
        for (const layer of page.layerStack.layers) {
            const layerData = serializeLayerForZipStatic(layer);

            // Groups have no image data
            if (!(layer.isGroup && layer.isGroup())) {
                await saveLayerContentToZip(layer, layerData, layersFolder);
            }

            layers.push(layerData);
        }

        pages.push({
            id: page.id,
            name: page.name,
            layers,
            activeLayerIndex: page.layerStack.activeLayerIndex,
        });
    }

    // Build content.json
    const content = {
        format: 'stagforge',
        version: SFR_VERSION,
        document: {
            _version: 2,
            _type: 'Document',
            id: doc.id,
            name: doc.name,
            width: doc.width,
            height: doc.height,
            dpi: doc.dpi,
            foregroundColor: doc.foregroundColor,
            backgroundColor: doc.backgroundColor,
            activePageIndex: doc.activePageIndex,
            viewState: {
                zoom: doc.zoom,
                panX: doc.panX,
                panY: doc.panY
            }
        },
        pages,
        metadata: {
            createdAt: doc.createdAt || new Date().toISOString(),
            modifiedAt: new Date().toISOString(),
            software: 'Stagforge 1.0'
        }
    };

    // Add content.json to ZIP
    zip.file('content.json', JSON.stringify(content, null, 2));

    // Generate ZIP blob with STORE compression (no compression)
    // WebP images are already compressed, so DEFLATE would waste CPU
    return zip.generateAsync({
        type: 'blob',
        compression: 'STORE'
    });
}

/**
 * Parse a ZIP file and extract document data + layer images.
 * Standalone function usable by FileManager and AutoSave.
 * @param {File|Blob} file - The ZIP file to parse
 * @returns {Promise<{data: Object, layerImages: Map}>}
 */
export async function parseDocumentZip(file) {
    if (!window.JSZip) {
        throw new Error('JSZip not loaded');
    }

    const zip = await window.JSZip.loadAsync(file);

    // Read content.json
    const contentFile = zip.file('content.json');
    if (!contentFile) {
        throw new Error('Invalid SFR file: missing content.json');
    }
    const contentText = await contentFile.async('string');
    const data = JSON.parse(contentText);

    // Validate format
    if (data.format !== 'stagforge') {
        throw new Error('Invalid file format');
    }

    // Extract layer images (keyed by filename without extension)
    // Handles both single-frame (layer-uuid.webp) and multi-frame (layer-uuid_frame_0.webp)
    const layerImages = new Map();
    const layersFolder = zip.folder('layers');
    if (layersFolder) {
        const files = [];
        layersFolder.forEach((relativePath, zipFile) => {
            files.push({ path: relativePath, zipFile });
        });

        for (const { path, zipFile } of files) {
            const blob = await zipFile.async('blob');
            // Key = filename without extension (preserves _frame_N suffix for multi-frame)
            const key = path.replace(/\.(webp|avif|png|svg)$/, '');
            layerImages.set(key, blob);
        }
    }

    return { data, layerImages };
}

export class FileManager {
    /**
     * @param {Object} app - Application reference
     */
    constructor(app) {
        this.app = app;

        // Persistent file handle for Ctrl+S save
        this.fileHandle = null;

        // Track current file name
        this.currentFileName = null;

        // Check File System Access API support
        this.hasFileSystemAccess = 'showSaveFilePicker' in window;

        // JSZip must be loaded via script tag before using FileManager
        if (!window.JSZip) {
            console.warn('JSZip not loaded. File save/load will not work.');
        }
    }

    /**
     * Serialize the current document to JSON format (for in-memory use and tests).
     * Note: File save uses serializeDocumentZip() which produces ZIP with WebP.
     * @returns {Promise<Object>} SFR document object with inline imageData
     */
    async serializeDocument() {
        const doc = this.app.documentManager.getActiveDocument();
        if (!doc) {
            throw new Error('No active document');
        }

        return {
            format: 'stagforge',
            version: SFR_VERSION,
            document: await doc.serialize(),
            metadata: {
                createdAt: doc.createdAt || new Date().toISOString(),
                modifiedAt: new Date().toISOString(),
                software: 'Stagforge 1.0'
            }
        };
    }

    /**
     * Serialize the current document to SFR format (ZIP with WebP images).
     * @returns {Promise<Blob>} ZIP blob
     */
    async serializeDocumentZip() {
        const doc = this.app.documentManager.getActiveDocument();
        if (!doc) {
            throw new Error('No active document');
        }
        return serializeDocumentToZip(doc);
    }

    /**
     * Serialize a layer for ZIP format (without inline image data for raster).
     * @param {Layer} layer
     * @returns {Object}
     */
    serializeLayerForZip(layer) {
        return serializeLayerForZipStatic(layer);
    }

    /**
     * Save document - updates existing file or prompts for Save As.
     * @returns {Promise<{success: boolean, filename?: string, error?: string}>}
     */
    async save() {
        try {
            if (this.fileHandle) {
                // Update existing file
                await this.writeToHandle(this.fileHandle);
                this.markDocumentClean();
                return { success: true, filename: this.currentFileName };
            }
            // No handle, do Save As
            return this.saveAs();
        } catch (error) {
            console.error('Save failed:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Save document as SVG with Stagforge metadata.
     * Creates an SVG file that can be viewed in any SVG viewer and
     * reloaded in Stagforge with full document restoration.
     * @returns {Promise<{success: boolean, filename?: string, error?: string}>}
     */
    async saveAsSVG() {
        try {
            const doc = this.app.documentManager.getActiveDocument();
            if (!doc) {
                throw new Error('No active document');
            }

            const suggestedName = `${doc.name || 'Untitled'}.svg`;
            const svgString = await doc.toSVG();
            const blob = new Blob([svgString], { type: 'image/svg+xml' });

            if (!this.hasFileSystemAccess) {
                // Fallback: download
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = suggestedName;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                return { success: true, filename: suggestedName };
            }

            const handle = await window.showSaveFilePicker({
                suggestedName,
                types: [{
                    description: 'SVG Document',
                    accept: { 'image/svg+xml': ['.svg'] }
                }]
            });

            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();

            return { success: true, filename: handle.name };
        } catch (error) {
            if (error.name === 'AbortError') {
                return { success: false, error: 'cancelled' };
            }
            console.error('Save As SVG failed:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Save document with file picker (always prompts for location).
     * @returns {Promise<{success: boolean, filename?: string, error?: string}>}
     */
    async saveAs() {
        try {
            const doc = this.app.documentManager.getActiveDocument();
            const suggestedName = `${doc?.name || 'Untitled'}.sfr`;

            if (!this.hasFileSystemAccess) {
                return await this.downloadFallback(suggestedName);
            }

            const handle = await window.showSaveFilePicker({
                suggestedName,
                types: [{
                    description: 'Stagforge Document',
                    accept: { 'application/zip': ['.sfr'] }
                }]
            });

            this.fileHandle = handle;
            this.currentFileName = handle.name;

            // Update document name from filename BEFORE serializing
            if (doc && handle.name.endsWith('.sfr')) {
                doc.name = handle.name.slice(0, -4);
            }

            await this.writeToHandle(handle);
            this.markDocumentClean();

            return { success: true, filename: handle.name };
        } catch (error) {
            if (error.name === 'AbortError') {
                // User cancelled
                return { success: false, error: 'cancelled' };
            }
            console.error('Save As failed:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Write document to file handle (ZIP format).
     * @param {FileSystemFileHandle} handle
     */
    async writeToHandle(handle) {
        const zipBlob = await this.serializeDocumentZip();
        const writable = await handle.createWritable();
        await writable.write(zipBlob);
        await writable.close();
    }

    /**
     * Fallback: Download as file for browsers without File System Access API.
     * @param {string} filename
     * @returns {Promise<{success: boolean, filename: string}>}
     */
    async downloadFallback(filename) {
        const zipBlob = await this.serializeDocumentZip();
        const url = URL.createObjectURL(zipBlob);

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.currentFileName = filename;
        this.markDocumentClean();

        return { success: true, filename };
    }

    /**
     * Open file picker and load document.
     * @returns {Promise<{success: boolean, filename?: string, error?: string}>}
     */
    async open() {
        try {
            if (!this.hasFileSystemAccess) {
                return this.openFallback();
            }

            const [handle] = await window.showOpenFilePicker({
                types: [
                    {
                        description: 'All Supported Files',
                        accept: {
                            'application/octet-stream': [
                                '.sfr',
                                '.png', '.jpg', '.jpeg', '.gif', '.bmp',
                                '.webp', '.avif', '.svg', '.ico', '.tiff', '.tif',
                            ],
                        },
                    },
                    {
                        description: 'Stagforge Document',
                        accept: { 'application/zip': ['.sfr'] },
                    },
                    {
                        description: 'Image Files',
                        accept: OPEN_IMAGE_ACCEPT,
                    },
                ],
            });

            const file = await handle.getFile();
            const ext = handle.name.split('.').pop().toLowerCase();

            if (IMAGE_EXTENSIONS.has(ext)) {
                await this.loadImageFile(file);
                return { success: true, filename: handle.name };
            }

            const { data, layerImages } = await this.parseZipFile(file);

            // Store handle for future saves
            this.fileHandle = handle;
            this.currentFileName = handle.name;

            // Load document
            await this.loadDocument(data, handle.name, layerImages);

            return { success: true, filename: handle.name };
        } catch (error) {
            if (error.name === 'AbortError') {
                return { success: false, error: 'cancelled' };
            }
            console.error('Open failed:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Parse SFR file (ZIP format).
     * @param {File|Blob} file
     * @returns {Promise<{data: Object, layerImages: Map}>}
     */
    async parseFile(file) {
        return parseDocumentZip(file);
    }

    /**
     * Parse ZIP file and extract content + layer images.
     * @param {File|Blob} file
     * @returns {Promise<{data: Object, layerImages: Map}>}
     */
    async parseZipFile(file) {
        return parseDocumentZip(file);
    }

    /**
     * Fallback: Open file using input element.
     * @returns {Promise<{success: boolean, filename?: string, error?: string}>}
     */
    openFallback() {
        return new Promise((resolve) => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = OPEN_IMAGE_ACCEPT_STRING;

            input.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) {
                    resolve({ success: false, error: 'cancelled' });
                    return;
                }

                try {
                    const ext = file.name.split('.').pop().toLowerCase();

                    if (IMAGE_EXTENSIONS.has(ext)) {
                        await this.loadImageFile(file);
                        resolve({ success: true, filename: file.name });
                        return;
                    }

                    const { data, layerImages } = await this.parseZipFile(file);

                    this.currentFileName = file.name;
                    // Note: Can't get file handle in fallback mode, so Ctrl+S won't work

                    await this.loadDocument(data, file.name, layerImages);

                    resolve({ success: true, filename: file.name });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            };

            input.click();
        });
    }

    /**
     * Create an SVGLayer from SVG file content, scaled to fit the document.
     * @param {string} svgContent - Raw SVG string
     * @param {string} name - Layer name
     * @param {number} docW - Document width
     * @param {number} docH - Document height
     * @returns {Promise<SVGLayer>}
     */
    async _createSVGLayer(svgContent, name, docW, docH) {
        const { SVGLayer } = await import('./StaticSVGLayer.js');
        // Parse natural dimensions via temp layer
        const temp = new SVGLayer({ width: 1, height: 1, svgContent });
        const natW = temp.naturalWidth || docW;
        const natH = temp.naturalHeight || docH;

        let targetW = natW;
        let targetH = natH;
        if (natW > docW || natH > docH) {
            const scale = Math.min(docW / natW, docH / natH);
            targetW = Math.round(natW * scale);
            targetH = Math.round(natH * scale);
        }
        const offsetX = Math.round((docW - targetW) / 2);
        const offsetY = Math.round((docH - targetH) / 2);

        const layer = new SVGLayer({
            width: targetW, height: targetH,
            offsetX, offsetY,
            name, svgContent,
        });
        await layer.render();
        return layer;
    }

    /**
     * Load a standard image file (PNG, JPEG, WebP, SVG, etc.) as a new document.
     * @param {File} file - The image file
     */
    async loadImageFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const name = file.name.replace(/\.[^.]+$/, '') || 'Imported';

        if (ext === 'svg') {
            const svgContent = await file.text();

            // Check if this is a Stagforge document
            const { isStagforgeSVG } = await import('./svgExportUtils.js');
            if (isStagforgeSVG(svgContent)) {
                // Load as Stagforge document
                const { Document } = await import('./Document.js');
                const newDoc = await Document.fromSVG(svgContent, this.app.eventBus);

                // Generate a new ID for the loaded document to avoid conflicts
                newDoc.id = crypto.randomUUID();

                // Update document name to match filename
                if (file.name.endsWith('.svg')) {
                    newDoc.name = file.name.slice(0, -4);
                }

                // Add to document manager
                this.app.documentManager.addDocument(newDoc);
                this.app.documentManager.setActiveDocument(newDoc.id);

                // Trigger UI updates
                this.app.renderer.resize(newDoc.width, newDoc.height);
                this.app.renderer.fitToViewport();
                this.app.renderer.requestRender();
                return;
            }

            // Not a Stagforge SVG - import as StaticSVGLayer
            const { SVGLayer } = await import('./StaticSVGLayer.js');
            // Parse natural size
            const temp = new SVGLayer({ width: 1, height: 1, svgContent });
            const w = temp.naturalWidth || 800;
            const h = temp.naturalHeight || 600;

            this.app.documentManager.createDocument({ width: w, height: h, name, activate: true });
            const doc = this.app.documentManager.getActiveDocument();

            const layer = await this._createSVGLayer(svgContent, name, w, h);
            // Replace the default empty raster layer
            doc.layerStack.layers.length = 0;
            doc.layerStack.addLayer(layer);
            doc.layerStack.setActiveLayer(0);

            this.app.renderer.requestRender();
            return;
        }

        const bitmap = await createImageBitmap(file);
        const w = bitmap.width;
        const h = bitmap.height;

        this.app.documentManager.createDocument({ width: w, height: h, name, activate: true });

        const doc = this.app.documentManager.getActiveDocument();
        const layer = doc?.layerStack?.getActiveLayer();
        if (layer?.ctx) {
            layer.ctx.drawImage(bitmap, 0, 0);
            layer.invalidateImageCache();
        }
        bitmap.close();
        this.app.renderer.requestRender();
    }

    /**
     * Load an image file as a new layer in the current document.
     * @param {File} file - The image file
     */
    async loadImageFileAsLayer(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const name = file.name.replace(/\.[^.]+$/, '') || 'Imported';
        const app = this.app;
        const doc = app.documentManager?.getActiveDocument();
        if (!doc) return;

        const history = doc.history || app.history;
        history?.beginCapture('Add Layer from File', []);
        history?.beginStructuralChange();

        if (ext === 'svg') {
            const svgContent = await file.text();
            const docW = doc.layerStack.width;
            const docH = doc.layerStack.height;
            const layer = await this._createSVGLayer(svgContent, name, docW, docH);
            doc.layerStack.addLayer(layer);
            doc.layerStack.setActiveLayer(doc.layerStack.layers.indexOf(layer));
        } else {
            const bitmap = await createImageBitmap(file);
            const { Layer } = await import('./PixelLayer.js');
            const layer = new Layer({ name, width: bitmap.width, height: bitmap.height, offsetX: 0, offsetY: 0 });
            layer.ctx.drawImage(bitmap, 0, 0);
            bitmap.close();
            doc.layerStack.addLayer(layer);
            doc.layerStack.setActiveLayer(doc.layerStack.layers.indexOf(layer));
        }

        history?.commitCapture();
        app.eventBus?.emit('layers:changed');
        app.renderer?.requestRender();
    }

    async loadDocument(data, filename, layerImages = null) {
        const { Document } = await import('./Document.js');

        const docData = data.document;

        // For v3+, pages are in the top-level 'pages' key, merge into docData
        if (data.pages && !docData.pages) {
            docData.pages = data.pages;
        }

        // Process layer images from ZIP (handles pages, frames, and legacy formats)
        await processLayerImages(data, layerImages);

        const newDoc = await Document.deserialize(docData, this.app.eventBus);

        // Generate a new ID for the loaded document to avoid conflicts
        newDoc.id = crypto.randomUUID();

        // Update document name to match filename
        if (filename && filename.endsWith('.sfr')) {
            newDoc.name = filename.slice(0, -4);
        }

        // Add to document manager
        this.app.documentManager.addDocument(newDoc);
        this.app.documentManager.setActiveDocument(newDoc.id);

        // Trigger UI updates
        this.app.renderer.resize(newDoc.width, newDoc.height);
        this.app.renderer.fitToViewport();
        this.app.renderer.requestRender();
    }

    /**
     * Mark current document as clean (no unsaved changes).
     */
    markDocumentClean() {
        const doc = this.app.documentManager.getActiveDocument();
        if (doc) {
            doc.modified = false;
            this.app.eventBus?.emit('document:saved', { document: doc });
        }
    }

    /**
     * Check if document has unsaved changes.
     * @returns {boolean}
     */
    hasUnsavedChanges() {
        const doc = this.app.documentManager.getActiveDocument();
        return doc?.modified ?? false;
    }

    /**
     * Get current file name.
     * @returns {string|null}
     */
    getFileName() {
        return this.currentFileName;
    }

    /**
     * Check if we have a file handle (can do quick save).
     * @returns {boolean}
     */
    canQuickSave() {
        return this.fileHandle !== null;
    }

    /**
     * Clear file handle (for new documents).
     */
    clearFileHandle() {
        this.fileHandle = null;
        this.currentFileName = null;
    }
}
