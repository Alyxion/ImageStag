/**
 * FileManager Mixin
 *
 * Handles file operations: save, open, export, import, and data retrieval.
 *
 * Required component data:
 *   - statusMessage: String
 *   - docWidth: Number
 *   - docHeight: Number
 *   - apiBase: String
 *
 * Required component methods:
 *   - getState(): Returns the app state object
 *   - updateLayerList(): Refreshes the layers panel
 *   - fitToWindow(): Fits document to viewport
 *   - updateDocumentTabs(): Updates document tab bar
 */
import { IMAGE_EXTENSIONS } from '../../config/ExportConfig.js';

export const FileManagerMixin = {
    methods: {
        /**
         * Save current document to existing file
         */
        async fileSave() {
            const app = this.getState();
            if (!app?.fileManager) {
                console.warn('FileManager not initialized');
                return;
            }

            this.statusMessage = 'Saving...';
            const result = await app.fileManager.save();
            if (result.success) {
                this.statusMessage = `Saved: ${result.filename}`;
                setTimeout(() => { this.statusMessage = 'Ready'; }, 2000);
            } else if (result.error !== 'cancelled') {
                this.statusMessage = `Save failed: ${result.error}`;
            } else {
                this.statusMessage = 'Ready';
            }
        },

        /**
         * Save current document to new file
         */
        async fileSaveAs() {
            const app = this.getState();
            if (!app?.fileManager) {
                console.warn('FileManager not initialized');
                return;
            }

            this.statusMessage = 'Saving...';
            const result = await app.fileManager.saveAs();
            if (result.success) {
                this.statusMessage = `Saved: ${result.filename}`;
                setTimeout(() => { this.statusMessage = 'Ready'; }, 2000);
            } else if (result.error !== 'cancelled') {
                this.statusMessage = `Save failed: ${result.error}`;
            } else {
                this.statusMessage = 'Ready';
            }
        },

        /**
         * Open a file
         */
        async fileOpen() {
            const app = this.getState();
            if (!app?.fileManager) {
                console.warn('FileManager not initialized');
                return;
            }

            this.statusMessage = 'Opening...';
            const result = await app.fileManager.open();
            if (result.success) {
                this.statusMessage = `Opened: ${result.filename}`;
                this.updateLayerList();
                this.fitToWindow();
                setTimeout(() => { this.statusMessage = 'Ready'; }, 2000);
            } else if (result.error !== 'cancelled') {
                this.statusMessage = `Open failed: ${result.error}`;
            } else {
                this.statusMessage = 'Ready';
            }
        },

        /**
         * Load a sample image from the backend
         * @param {Object} img - Image metadata with name, source, id
         */
        async loadSampleImage(img) {
            const app = this.getState();
            if (!app) return;

            this.statusMessage = `Loading ${img.name}...`;
            try {
                const response = await fetch(`${this.apiBase}/images/${img.source}/${img.id}`);
                if (!response.ok) throw new Error('Failed to fetch image');

                // Get metadata from header
                const metadata = JSON.parse(response.headers.get('X-Image-Metadata') || '{}');
                const width = metadata.width || 800;
                const height = metadata.height || 600;

                // Get raw RGBA data
                const buffer = await response.arrayBuffer();
                const rgba = new Uint8ClampedArray(buffer);

                // Create new document with image dimensions
                this.docWidth = width;
                this.docHeight = height;
                app.canvasWidth = width;
                app.canvasHeight = height;

                // Recreate layer stack with new dimensions
                const { LayerStack } = await import('/static/js/core/LayerStack.js');
                app.layerStack = new LayerStack(width, height, app.eventBus);
                app.renderer.layerStack = app.layerStack;
                app.renderer.resize(width, height);

                // Create layer and set image data
                const layer = app.layerStack.addLayer({ name: img.name });
                const imageData = new ImageData(rgba, width, height);
                layer.ctx.putImageData(imageData, 0, 0);

                app.history.clear();
                this.updateLayerList();
                this.fitToWindow();
                this.statusMessage = 'Ready';
            } catch (e) {
                console.error('Failed to load image:', e);
                this.statusMessage = 'Failed to load image';
            }
        },

        /**
         * Apply a filter to the active layer
         * @param {string} filterId - Filter identifier
         * @param {Object} params - Filter parameters
         */
        async applyFilter(filterId, params) {
            const app = this.getState();
            if (!app?.pluginManager) return;

            this.statusMessage = 'Applying filter...';
            try {
                await app.pluginManager.applyFilter(filterId, app.layerStack.getActiveLayer(), params);
                app.renderer.requestRender();
                this.statusMessage = 'Ready';
            } catch (e) {
                console.error('Failed to apply filter:', e);
                this.statusMessage = 'Filter failed';
            }
        },

        /**
         * Export document as PNG
         */
        exportPNG() {
            const app = this.getState();
            if (!app?.layerStack) return;

            // Flatten to temp canvas
            const flatCanvas = document.createElement('canvas');
            flatCanvas.width = this.docWidth;
            flatCanvas.height = this.docHeight;
            const ctx = flatCanvas.getContext('2d');

            // White background
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, this.docWidth, this.docHeight);

            // Draw all visible layers
            for (const layer of app.layerStack.layers) {
                if (!layer.visible) continue;
                ctx.globalAlpha = layer.opacity;
                ctx.drawImage(layer.canvas, 0, 0);
            }

            // Export
            const link = document.createElement('a');
            link.download = 'stagforge-export.png';
            link.href = flatCanvas.toDataURL('image/png');
            link.click();
        },

        /**
         * Get image data as base64 for Python
         * @param {string|number|null} layerId - Layer selector (ID, name, index, or null for composite)
         * @param {string|number|null} documentId - Document selector
         * @returns {Object} Image data with base64 and dimensions
         */
        getImageData(layerId = null, documentId = null) {
            const app = this.getState();
            if (!app?.documentManager) return { error: 'Editor not initialized' };

            try {
                // Resolve document
                let doc = null;
                if (documentId === null || documentId === undefined || documentId === 'current') {
                    doc = app.documentManager.getActiveDocument();
                } else if (typeof documentId === 'number') {
                    doc = app.documentManager.documents[documentId];
                } else if (typeof documentId === 'string') {
                    doc = app.documentManager.documents.find(d => d.id === documentId);
                    if (!doc) {
                        doc = app.documentManager.documents.find(d => d.name === documentId);
                    }
                }

                if (!doc) {
                    return { error: 'Document not found' };
                }

                const layerStack = doc.layerStack;
                if (!layerStack) {
                    return { error: 'Document has no layer stack' };
                }

                let canvas, width, height, layerInfo = {};
                const docWidth = doc.width;
                const docHeight = doc.height;

                if (layerId) {
                    // Get specific layer - can be ID, index, or name
                    let layer = null;
                    if (typeof layerId === 'number') {
                        layer = layerStack.layers[layerId];
                    } else if (typeof layerId === 'string') {
                        layer = layerStack.layers.find(l => l.id === layerId);
                        if (!layer) {
                            layer = layerStack.layers.find(l => l.name === layerId);
                        }
                    }

                    if (!layer) return { error: 'Layer not found' };
                    canvas = layer.canvas;
                    width = canvas.width;
                    height = canvas.height;
                    layerInfo = {
                        name: layer.name,
                        opacity: layer.opacity,
                        blend_mode: layer.blendMode,
                    };
                } else {
                    // Get flattened composite
                    canvas = document.createElement('canvas');
                    canvas.width = docWidth;
                    canvas.height = docHeight;
                    const ctx = canvas.getContext('2d');

                    // White background
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillRect(0, 0, docWidth, docHeight);

                    // Composite all visible layers (bottom to top, so iterate in reverse)
                    for (let i = layerStack.layers.length - 1; i >= 0; i--) {
                        const layer = layerStack.layers[i];
                        if (!layer.visible || layer.isGroup?.()) continue;
                        ctx.globalAlpha = layer.opacity;
                        ctx.drawImage(layer.canvas, layer.offsetX || 0, layer.offsetY || 0);
                    }
                    ctx.globalAlpha = 1.0;
                    width = docWidth;
                    height = docHeight;
                }

                // Get raw pixel data and encode as base64
                const ctx = canvas.getContext('2d');
                const imageData = ctx.getImageData(0, 0, width, height);
                const base64 = this.arrayBufferToBase64(imageData.data.buffer);

                return {
                    data: base64,
                    width: width,
                    height: height,
                    document_id: doc.id,
                    document_name: doc.name,
                    ...layerInfo,
                };
            } catch (e) {
                return { error: e.message };
            }
        },

        /**
         * Convert ArrayBuffer to base64 string
         * @param {ArrayBuffer} buffer - Buffer to convert
         * @returns {string} Base64 encoded string
         */
        arrayBufferToBase64(buffer) {
            let binary = '';
            const bytes = new Uint8Array(buffer);
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return btoa(binary);
        },

        /**
         * Push data to the upload endpoint for a pending request.
         * This is the push-based alternative to getImageData that avoids WebSocket payload limits.
         *
         * @param {string} requestId - Unique request ID for the upload endpoint
         * @param {string|number|null} layerId - Layer selector (ID, name, index, or null for composite)
         * @param {string|number|null} documentId - Document selector (ID, name, index, 'current', or null)
         * @param {string} format - Output format: 'webp', 'avif', 'png', 'svg', 'json'
         * @param {string|null} bg - Background color (e.g., '#FFFFFF') or null for transparent
         */
        async pushData(requestId, layerId = null, documentId = null, format = 'webp', bg = null) {
            console.log(`[pushData] START requestId=${requestId?.slice(0,8)}... layer=${layerId} doc=${documentId} format=${format}`);
            const startTime = performance.now();

            const app = this.getState();

            // Helper to send error response
            const sendError = async (msg) => {
                console.error('pushData:', msg);
                try {
                    await fetch(`${this.$props.apiBase}/upload/${requestId}/error`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ error: msg }),
                    });
                } catch (e) {
                    console.error('pushData: Failed to send error', e);
                }
            };

            if (!app?.documentManager) {
                await sendError('Editor not initialized');
                return;
            }

            try {
                // Resolve document
                let doc = null;
                if (documentId === null || documentId === undefined || documentId === 'current') {
                    doc = app.documentManager.getActiveDocument();
                } else if (typeof documentId === 'number') {
                    doc = app.documentManager.documents[documentId];
                } else if (typeof documentId === 'string') {
                    doc = app.documentManager.documents.find(d => d.id === documentId);
                    if (!doc) {
                        doc = app.documentManager.documents.find(d => d.name === documentId);
                    }
                }

                if (!doc) {
                    await sendError('Document not found');
                    return;
                }

                const layerStack = doc.layerStack;
                if (!layerStack) {
                    await sendError('Document has no layer stack');
                    return;
                }

                // Resolve layer (if specified)
                let layer = null;
                let layerType = null;
                if (layerId !== null && layerId !== undefined) {
                    if (typeof layerId === 'number') {
                        layer = layerStack.layers[layerId];
                    } else if (typeof layerId === 'string') {
                        layer = layerStack.layers.find(l => l.id === layerId);
                        if (!layer) {
                            layer = layerStack.layers.find(l => l.name === layerId);
                        }
                    }
                    if (!layer) {
                        await sendError('Layer not found');
                        return;
                    }
                    // Determine layer type
                    if (layer.shapes !== undefined) {
                        layerType = 'vector';
                    } else if (layer.runs !== undefined || layer.textContent !== undefined) {
                        layerType = 'text';
                    } else if (layer.isGroup?.()) {
                        layerType = 'group';
                    } else {
                        layerType = 'raster';
                    }
                }

                // Prepare data based on format and layer type
                let blob, contentType, metadata;
                const docWidth = doc.width;
                const docHeight = doc.height;

                if (format === 'json' && layer && layerType === 'vector') {
                    // Export vector layer as JSON
                    // VectorShape instances have toData() method for proper serialization
                    const shapes = (layer.shapes || []).map(shape => {
                        if (typeof shape.toData === 'function') {
                            return shape.toData();
                        }
                        return shape;  // Already plain data
                    });
                    const jsonData = JSON.stringify({
                        type: 'vector',
                        shapes: shapes,
                        width: layer.canvas?.width || docWidth,
                        height: layer.canvas?.height || docHeight,
                        offsetX: layer.offsetX || 0,
                        offsetY: layer.offsetY || 0,
                    });
                    blob = new Blob([jsonData], { type: 'application/json' });
                    contentType = 'application/json';
                    metadata = {
                        width: layer.canvas?.width || docWidth,
                        height: layer.canvas?.height || docHeight,
                        layerType: 'vector',
                        dataType: 'vector-json',
                    };
                } else if (format === 'svg' && layer && layerType === 'vector') {
                    // Export vector layer as SVG
                    // Use the layer's toSVG() method if available (VectorLayer instances)
                    // or fall back to manual conversion for plain shape data
                    let svgContent;
                    if (typeof layer.toSVG === 'function') {
                        // VectorLayer has its own SVG generation that properly handles VectorShape instances
                        svgContent = layer.toSVG({
                            bounds: { x: 0, y: 0, width: docWidth, height: docHeight },
                            antialiasing: false
                        });
                    } else {
                        // Fallback for plain shape data
                        svgContent = this._layerToSVG(layer, docWidth, docHeight);
                    }
                    blob = new Blob([svgContent], { type: 'image/svg+xml' });
                    contentType = 'image/svg+xml';
                    metadata = {
                        width: docWidth,
                        height: docHeight,
                        layerType: 'vector',
                        dataType: 'svg',
                    };
                } else {
                    // Render to canvas and export as image
                    let canvas;
                    if (layer) {
                        // Groups don't have a canvas - return error
                        if (layer.isGroup?.()) {
                            await sendError('Cannot export group layers directly');
                            return;
                        }

                        // Single layer - render with effects if present
                        if (layer.hasEffects && layer.hasEffects() && window.effectRenderer) {
                            const rendered = window.effectRenderer.getRenderedLayer(layer);
                            if (rendered) {
                                // Create canvas large enough for effects (shadows etc expand bounds)
                                canvas = document.createElement('canvas');
                                canvas.width = rendered.contentCanvas.width;
                                canvas.height = rendered.contentCanvas.height;
                                const ctx = canvas.getContext('2d');

                                // Draw behind effects (shadows, outer glow)
                                if (rendered.behindCanvas) {
                                    ctx.drawImage(rendered.behindCanvas, 0, 0);
                                }
                                // Draw content + stroke
                                ctx.drawImage(rendered.contentCanvas, 0, 0);

                                metadata = {
                                    width: canvas.width,
                                    height: canvas.height,
                                    layerType: layerType,
                                    dataType: 'image',
                                    offsetX: rendered.offsetX,
                                    offsetY: rendered.offsetY,
                                };
                            } else {
                                canvas = layer.canvas;
                                if (!canvas) {
                                    await sendError('Layer has no canvas');
                                    return;
                                }
                                metadata = {
                                    width: canvas.width,
                                    height: canvas.height,
                                    layerType: layerType,
                                    dataType: 'image',
                                };
                            }
                        } else {
                            canvas = layer.canvas;
                            if (!canvas) {
                                await sendError('Layer has no canvas');
                                return;
                            }
                            metadata = {
                                width: canvas.width,
                                height: canvas.height,
                                layerType: layerType,
                                dataType: 'image',
                            };
                        }
                    } else {
                        // Composite all visible layers with effects
                        canvas = document.createElement('canvas');
                        canvas.width = docWidth;
                        canvas.height = docHeight;
                        const ctx = canvas.getContext('2d');

                        // Optional background color (transparent by default)
                        if (bg) {
                            ctx.fillStyle = bg;
                            ctx.fillRect(0, 0, docWidth, docHeight);
                        }

                        // Composite all visible layers (bottom to top) with effects
                        for (let i = layerStack.layers.length - 1; i >= 0; i--) {
                            const l = layerStack.layers[i];
                            if (!l.visible || l.isGroup?.()) continue;

                            // Check for layer effects
                            if (l.hasEffects && l.hasEffects() && window.effectRenderer) {
                                const rendered = window.effectRenderer.getRenderedLayer(l);
                                if (rendered) {
                                    // Draw behind effects (shadows, outer glow)
                                    if (rendered.behindCanvas) {
                                        ctx.globalAlpha = l.opacity;
                                        ctx.drawImage(rendered.behindCanvas, rendered.offsetX, rendered.offsetY);
                                    }
                                    // Draw content + stroke
                                    ctx.globalAlpha = l.opacity;
                                    ctx.drawImage(rendered.contentCanvas, rendered.offsetX, rendered.offsetY);
                                } else {
                                    ctx.globalAlpha = l.opacity;
                                    ctx.drawImage(l.canvas, l.offsetX || 0, l.offsetY || 0);
                                }
                            } else {
                                ctx.globalAlpha = l.opacity;
                                ctx.drawImage(l.canvas, l.offsetX || 0, l.offsetY || 0);
                            }
                        }
                        ctx.globalAlpha = 1.0;
                        metadata = {
                            width: docWidth,
                            height: docHeight,
                            layerType: null,
                            dataType: 'image',
                        };
                    }

                    // Convert to requested format
                    const mimeType = format === 'avif' ? 'image/avif' :
                                     format === 'png' ? 'image/png' : 'image/webp';
                    const quality = format === 'png' ? undefined : 0.9;

                    blob = await new Promise(resolve => {
                        canvas.toBlob(resolve, mimeType, quality);
                    });

                    if (!blob) {
                        // Fallback to PNG if format not supported
                        blob = await new Promise(resolve => {
                            canvas.toBlob(resolve, 'image/png');
                        });
                        contentType = 'image/png';
                    } else {
                        contentType = mimeType;
                    }
                }

                // POST to upload endpoint
                const uploadUrl = `${this.$props.apiBase}/upload/${requestId}`;
                const headers = {
                    'Content-Type': contentType,
                    'X-Width': String(metadata.width),
                    'X-Height': String(metadata.height),
                    'X-Document-Id': doc.id,
                    'X-Document-Name': doc.name,
                    'X-Data-Type': metadata.dataType,
                };

                if (layer) {
                    headers['X-Layer-Id'] = layer.id;
                    headers['X-Layer-Name'] = layer.name;
                    headers['X-Layer-Type'] = layerType;
                }

                const prepTime = performance.now() - startTime;
                console.log(`[pushData] Prepared data in ${prepTime.toFixed(1)}ms, uploading ${blob.size} bytes...`);

                const response = await fetch(uploadUrl, {
                    method: 'POST',
                    headers: headers,
                    body: blob,
                });

                const totalTime = performance.now() - startTime;
                if (!response.ok) {
                    console.error(`[pushData] Upload failed after ${totalTime.toFixed(1)}ms:`, response.status, await response.text());
                } else {
                    console.log(`[pushData] DONE in ${totalTime.toFixed(1)}ms`);
                }
            } catch (e) {
                console.error('[pushData] Error:', e);
            }
        },

        /**
         * Convert a vector layer to SVG string.
         * @private
         * @param {Object} layer - Vector layer
         * @param {number} docWidth - Document width
         * @param {number} docHeight - Document height
         * @returns {string} SVG markup
         */
        _layerToSVG(layer, docWidth, docHeight) {
            const shapes = layer.shapes || [];
            let svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${docWidth}" height="${docHeight}" viewBox="0 0 ${docWidth} ${docHeight}">`;

            for (const shape of shapes) {
                svgContent += this._shapeToSVGElement(shape);
            }

            svgContent += '</svg>';
            return svgContent;
        },

        /**
         * Convert a shape object to SVG element string.
         * @private
         * @param {Object} shape - Shape object
         * @returns {string} SVG element markup
         */
        _shapeToSVGElement(shape) {
            const fill = shape.fill || 'none';
            const stroke = shape.stroke || 'none';
            const strokeWidth = shape.strokeWidth || 1;

            switch (shape.type) {
                case 'rect':
                    return `<rect x="${shape.x}" y="${shape.y}" width="${shape.width}" height="${shape.height}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'ellipse':
                    const cx = shape.cx || (shape.x + shape.width / 2);
                    const cy = shape.cy || (shape.y + shape.height / 2);
                    const rx = shape.rx || (shape.width / 2);
                    const ry = shape.ry || (shape.height / 2);
                    return `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'circle':
                    return `<circle cx="${shape.cx}" cy="${shape.cy}" r="${shape.r}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'line':
                    return `<line x1="${shape.x1}" y1="${shape.y1}" x2="${shape.x2}" y2="${shape.y2}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'polygon':
                    const points = (shape.points || []).map(p => `${p.x},${p.y}`).join(' ');
                    return `<polygon points="${points}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                case 'path':
                    return `<path d="${shape.d || ''}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
                default:
                    return '';
            }
        },

        /**
         * Handle dragover on the editor root.
         * @param {DragEvent} e
         */
        onFileDragOver(e) {
            if (!e.dataTransfer?.types?.includes('Files')) return;
            e.dataTransfer.dropEffect = 'copy';
        },

        /**
         * Handle dragleave on the editor root.
         */
        onFileDragLeave() {
            // placeholder for future visual feedback
        },

        /**
         * Handle file drop on the editor root.
         * Drop on canvas-container → add as layer.
         * Drop anywhere else → open as new document.
         * @param {DragEvent} e
         */
        async onFileDrop(e) {
            const files = e.dataTransfer?.files;
            if (!files || files.length === 0) return;

            const app = this.getState();
            if (!app?.fileManager) return;

            const file = files[0];
            const ext = file.name.split('.').pop().toLowerCase();
            const isImage = IMAGE_EXTENSIONS.has(ext);
            const isSFR = ext === 'sfr';

            if (!isImage && !isSFR) return;

            // Determine drop target: over the document content area → add as layer
            let onCanvas = false;
            if (e.target.id === 'main-canvas' || e.target.classList?.contains('cursor-overlay')) {
                const renderer = app.renderer;
                if (renderer) {
                    const rect = (e.target.id === 'main-canvas' ? e.target : e.target.parentElement?.querySelector('#main-canvas'))?.getBoundingClientRect();
                    if (rect) {
                        const sx = (e.clientX - rect.left) * (devicePixelRatio || 1);
                        const sy = (e.clientY - rect.top) * (devicePixelRatio || 1);
                        const doc = renderer.screenToCanvas(sx, sy);
                        onCanvas = doc.x >= 0 && doc.y >= 0
                            && doc.x < app.layerStack.width
                            && doc.y < app.layerStack.height;
                    }
                }
            }

            if (isSFR) {
                // Always open SFR as new document
                const { data, layerImages } = await app.fileManager.parseZipFile(file);
                await app.fileManager.loadDocument(data, file.name, layerImages);
                this.updateLayerList();
                this.fitToWindow();
            } else if (onCanvas && app.documentManager?.getActiveDocument()) {
                // Image dropped on canvas → add as layer
                await app.fileManager.loadImageFileAsLayer(file);
                this.updateLayerList();
            } else {
                // Image dropped outside canvas → open as new document
                await app.fileManager.loadImageFile(file);
                this.updateLayerList();
                this.fitToWindow();
            }
        },

        /**
         * Export the full document as JSON for cross-platform transfer
         * @returns {Object} Serialized document
         */
        async exportDocument() {
            const app = this.getState();
            if (!app) return { error: 'Editor not initialized' };

            try {
                const activeDoc = app.documentManager?.getActiveDocument();
                if (!activeDoc) {
                    return { error: 'No active document' };
                }

                // Serialize the document
                const serialized = await activeDoc.serialize();

                // Add format version
                serialized.version = '1.0';

                return { document: serialized };
            } catch (e) {
                return { error: e.message };
            }
        },

        /**
         * Import a full document from JSON
         * @param {Object} documentData - Serialized document data
         * @returns {Object} Result with success/error
         */
        async importDocument(documentData) {
            const app = this.getState();
            if (!app) return { error: 'Editor not initialized' };

            try {
                if (!documentData || !documentData.layers) {
                    return { error: 'Invalid document format' };
                }

                // Import document using Document.deserialize
                const eventBus = app.eventBus;
                const importedDoc = await Document.deserialize(documentData, eventBus);

                // Add to document manager
                if (app.documentManager) {
                    // Close current document and add imported one
                    const currentDocId = app.documentManager.activeDocumentId;
                    app.documentManager.documents.set(importedDoc.id, importedDoc);
                    app.documentManager.switchToDocument(importedDoc.id);

                    // Update Vue state
                    this.docWidth = importedDoc.width;
                    this.docHeight = importedDoc.height;
                    this.updateDocumentTabs();
                }

                // Update renderer
                app.layerStack = importedDoc.layerStack;
                app.renderer.layerStack = importedDoc.layerStack;
                app.renderer.resize(importedDoc.width, importedDoc.height);
                app.renderer.fitToViewport();
                app.renderer.requestRender();

                // Update layers panel
                this.updateLayerList();

                return { success: true, documentId: importedDoc.id };
            } catch (e) {
                return { error: e.message };
            }
        },
    },
};

export default FileManagerMixin;
