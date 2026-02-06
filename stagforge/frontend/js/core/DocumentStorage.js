/**
 * DocumentStorage - Global document cache with browser OPFS storage.
 *
 * Persists ALL documents (including closed/unsaved) in a global storage directory
 * that is shared across browser tabs. Includes:
 * - Thumbnail generation and storage
 * - Size limits and automatic cleanup
 * - Manifest with document metadata
 *
 * Storage Structure (OPFS):
 * stagforge_documents/           # Global (shared across tabs)
 * ├── manifest.json              # Metadata for all documents
 * ├── {doc_id}.sfr               # Full SFR document with thumbnail
 * └── ...
 *
 * SFR Format with Thumbnail:
 * document.sfr (ZIP)
 * ├── content.json
 * ├── thumbnail.jpg              # 256x256 JPEG
 * └── layers/
 *     ├── {id}.webp
 *     └── {id}.svg
 */

import { serializeDocumentToZip, parseDocumentZip, processLayerImages } from './FileManager.js';

/**
 * Generate a thumbnail for a document.
 * Creates a 256x256 JPEG that fits the document proportionally.
 * @param {Document} doc - The document to generate thumbnail for
 * @param {number} [size=256] - Thumbnail size (square)
 * @param {number} [quality=0.75] - JPEG quality (0-1)
 * @returns {Promise<Blob>} JPEG blob
 */
export async function generateDocumentThumbnail(doc, size = 256, quality = 0.75) {
    // Create a temporary canvas for compositing
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    // Fill with checkerboard pattern for transparency
    const checkerSize = 8;
    for (let y = 0; y < size; y += checkerSize) {
        for (let x = 0; x < size; x += checkerSize) {
            const isLight = ((x / checkerSize) + (y / checkerSize)) % 2 === 0;
            ctx.fillStyle = isLight ? '#ffffff' : '#cccccc';
            ctx.fillRect(x, y, checkerSize, checkerSize);
        }
    }

    // Calculate scaling to fit document in thumbnail
    const docWidth = doc.width || doc.layerStack?.width || 800;
    const docHeight = doc.height || doc.layerStack?.height || 600;
    const scale = Math.min(size / docWidth, size / docHeight);
    const scaledWidth = Math.round(docWidth * scale);
    const scaledHeight = Math.round(docHeight * scale);
    const offsetX = Math.round((size - scaledWidth) / 2);
    const offsetY = Math.round((size - scaledHeight) / 2);

    // Create temporary document-sized canvas for compositing
    const docCanvas = document.createElement('canvas');
    docCanvas.width = docWidth;
    docCanvas.height = docHeight;
    const docCtx = docCanvas.getContext('2d');

    // Composite all visible layers (bottom to top)
    const layers = doc.layerStack?.layers || [];
    for (let i = layers.length - 1; i >= 0; i--) {
        const layer = layers[i];
        if (!layer.visible) continue;

        // Skip groups (they don't have canvas)
        if (layer.isGroup && layer.isGroup()) continue;

        // Get layer canvas
        let layerCanvas = layer.canvas;
        if (!layerCanvas && layer.render) {
            // For SVG/text layers, render if needed
            await layer.render();
            layerCanvas = layer.canvas;
        }
        if (!layerCanvas) continue;

        // Apply opacity and blend mode
        docCtx.globalAlpha = layer.opacity ?? 1.0;
        docCtx.globalCompositeOperation = layer.blendMode || 'source-over';

        // Draw layer at its offset position
        const ox = layer.offsetX || 0;
        const oy = layer.offsetY || 0;
        docCtx.drawImage(layerCanvas, ox, oy);
    }

    // Reset composite settings
    docCtx.globalAlpha = 1.0;
    docCtx.globalCompositeOperation = 'source-over';

    // Draw scaled document onto thumbnail canvas with high quality
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(docCanvas, offsetX, offsetY, scaledWidth, scaledHeight);

    // Convert to JPEG blob
    return new Promise((resolve, reject) => {
        canvas.toBlob(
            (blob) => {
                if (blob) {
                    resolve(blob);
                } else {
                    reject(new Error('Failed to generate thumbnail'));
                }
            },
            'image/jpeg',
            quality
        );
    });
}

/**
 * Serialize a document to ZIP format with thumbnail.
 * @param {Document} doc - The document to serialize
 * @param {Object} options - Options
 * @param {number} [options.thumbnailSize=256] - Thumbnail size
 * @param {number} [options.thumbnailQuality=0.75] - JPEG quality
 * @returns {Promise<Blob>} ZIP blob with thumbnail
 */
export async function serializeDocumentWithThumbnail(doc, options = {}) {
    const { thumbnailSize = 256, thumbnailQuality = 0.75 } = options;

    // Generate base ZIP
    const zipBlob = await serializeDocumentToZip(doc);

    // Generate thumbnail
    const thumbnailBlob = await generateDocumentThumbnail(doc, thumbnailSize, thumbnailQuality);

    // Add thumbnail to ZIP
    const zip = await window.JSZip.loadAsync(zipBlob);
    zip.file('thumbnail.jpg', thumbnailBlob);

    // Regenerate ZIP
    return zip.generateAsync({
        type: 'blob',
        compression: 'STORE'
    });
}

/**
 * Extract thumbnail from an SFR ZIP file.
 * @param {Blob|File} zipBlob - The SFR ZIP file
 * @returns {Promise<Blob|null>} Thumbnail blob or null if not found
 */
export async function extractThumbnail(zipBlob) {
    try {
        const zip = await window.JSZip.loadAsync(zipBlob);
        const thumbnailFile = zip.file('thumbnail.jpg');
        if (thumbnailFile) {
            return await thumbnailFile.async('blob');
        }
        return null;
    } catch (error) {
        console.error('[DocumentStorage] Failed to extract thumbnail:', error);
        return null;
    }
}

export class DocumentStorage {
    /**
     * @param {Object} options - Configuration options
     * @param {number} [options.maxDocumentSize=209715200] - Max size per document (200MB)
     * @param {number} [options.maxTotalSize=2147483648] - Total storage limit (2GB)
     * @param {number} [options.minKeepCount=10] - Always keep N most recent documents
     * @param {number} [options.thumbnailSize=256] - Thumbnail dimensions
     * @param {number} [options.thumbnailQuality=0.75] - JPEG quality (0-1)
     */
    constructor(options = {}) {
        this.maxDocumentSize = options.maxDocumentSize || 200 * 1024 * 1024;  // 200MB
        this.maxTotalSize = options.maxTotalSize || 2 * 1024 * 1024 * 1024;   // 2GB
        this.minKeepCount = options.minKeepCount || 10;
        this.thumbnailSize = options.thumbnailSize || 256;
        this.thumbnailQuality = options.thumbnailQuality || 0.75;

        // State
        this.isInitialized = false;
        this.rootDir = null;

        console.log('[DocumentStorage] Created with options:', {
            maxDocumentSize: this.maxDocumentSize,
            maxTotalSize: this.maxTotalSize,
            minKeepCount: this.minKeepCount
        });
    }

    /**
     * Initialize OPFS storage.
     */
    async initialize() {
        if (this.isInitialized) return;

        try {
            const root = await navigator.storage.getDirectory();
            this.rootDir = await root.getDirectoryHandle('stagforge_documents', { create: true });
            this.isInitialized = true;
            console.log('[DocumentStorage] Initialized');
        } catch (error) {
            console.error('[DocumentStorage] Failed to initialize OPFS:', error);
            throw error;
        }
    }

    /**
     * Ensure storage is initialized.
     */
    async ensureInitialized() {
        if (!this.isInitialized) {
            await this.initialize();
        }
    }

    /**
     * List all stored documents with metadata.
     * @returns {Promise<Array>} Array of document metadata
     */
    async listDocuments() {
        await this.ensureInitialized();

        const manifest = await this.loadManifest();
        return manifest?.documents || [];
    }

    /**
     * Save a document to storage with thumbnail.
     * @param {Document} doc - The document to save
     * @returns {Promise<boolean>} Success status
     */
    async saveDocument(doc) {
        await this.ensureInitialized();

        try {
            // Serialize document with thumbnail
            const zipBlob = await serializeDocumentWithThumbnail(doc, {
                thumbnailSize: this.thumbnailSize,
                thumbnailQuality: this.thumbnailQuality
            });

            // Check size limit
            if (zipBlob.size > this.maxDocumentSize) {
                console.warn(`[DocumentStorage] Document ${doc.id} exceeds size limit (${zipBlob.size} > ${this.maxDocumentSize}), skipping`);
                return false;
            }

            // Save to OPFS
            const fileName = `${doc.id}.sfr`;
            const fileHandle = await this.rootDir.getFileHandle(fileName, { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(zipBlob);
            await writable.close();

            // Update manifest
            await this.updateManifest(doc, zipBlob.size);

            // Run cleanup if needed
            await this.runCleanup();

            console.log(`[DocumentStorage] Saved document: ${doc.name} (${doc.id}), size: ${zipBlob.size}`);
            return true;
        } catch (error) {
            console.error(`[DocumentStorage] Failed to save document ${doc.id}:`, error);
            return false;
        }
    }

    /**
     * Load a document from storage.
     * @param {string} docId - Document ID
     * @returns {Promise<{data: Object, layerImages: Map}|null>}
     */
    async loadDocument(docId) {
        await this.ensureInitialized();

        try {
            const fileName = `${docId}.sfr`;
            const fileHandle = await this.rootDir.getFileHandle(fileName);
            const file = await fileHandle.getFile();
            return await parseDocumentZip(file);
        } catch (error) {
            if (error.name !== 'NotFoundError') {
                console.error(`[DocumentStorage] Failed to load document ${docId}:`, error);
            }
            return null;
        }
    }

    /**
     * Get thumbnail for a stored document.
     * @param {string} docId - Document ID
     * @returns {Promise<string|null>} Data URL or null
     */
    async getDocumentThumbnail(docId) {
        await this.ensureInitialized();

        try {
            const fileName = `${docId}.sfr`;
            const fileHandle = await this.rootDir.getFileHandle(fileName);
            const file = await fileHandle.getFile();
            const thumbnailBlob = await extractThumbnail(file);

            if (thumbnailBlob) {
                return new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result);
                    reader.onerror = () => resolve(null);
                    reader.readAsDataURL(thumbnailBlob);
                });
            }
            return null;
        } catch (error) {
            return null;
        }
    }

    /**
     * Delete a document from storage.
     * @param {string} docId - Document ID
     * @returns {Promise<boolean>} Success status
     */
    async deleteDocument(docId) {
        await this.ensureInitialized();

        try {
            // Remove file
            const fileName = `${docId}.sfr`;
            await this.rootDir.removeEntry(fileName);

            // Update manifest
            const manifest = await this.loadManifest();
            if (manifest) {
                manifest.documents = manifest.documents.filter(d => d.id !== docId);
                await this.saveManifest(manifest);
            }

            console.log(`[DocumentStorage] Deleted document: ${docId}`);
            return true;
        } catch (error) {
            if (error.name !== 'NotFoundError') {
                console.error(`[DocumentStorage] Failed to delete document ${docId}:`, error);
            }
            return false;
        }
    }

    /**
     * Delete all documents from storage.
     * @returns {Promise<number>} Number of documents deleted
     */
    async deleteAllDocuments() {
        await this.ensureInitialized();

        let count = 0;
        try {
            // Get all entries
            const toDelete = [];
            for await (const entry of this.rootDir.values()) {
                if (entry.kind === 'file' && entry.name.endsWith('.sfr')) {
                    toDelete.push(entry.name);
                }
            }

            // Delete all
            for (const fileName of toDelete) {
                try {
                    await this.rootDir.removeEntry(fileName);
                    count++;
                } catch (e) {
                    console.warn(`[DocumentStorage] Failed to delete ${fileName}:`, e);
                }
            }

            // Clear manifest
            await this.saveManifest({ version: 1, documents: [] });

            console.log(`[DocumentStorage] Deleted all ${count} documents`);
        } catch (error) {
            console.error('[DocumentStorage] Failed to delete all documents:', error);
        }
        return count;
    }

    /**
     * Delete documents older than a specified number of days.
     * @param {number} days - Age threshold in days
     * @returns {Promise<number>} Number of documents deleted
     */
    async deleteDocumentsOlderThan(days) {
        await this.ensureInitialized();

        const threshold = Date.now() - (days * 24 * 60 * 60 * 1000);
        const manifest = await this.loadManifest();
        if (!manifest) return 0;

        const toDelete = manifest.documents.filter(d => d.lastModified < threshold);
        let count = 0;

        for (const doc of toDelete) {
            if (await this.deleteDocument(doc.id)) {
                count++;
            }
        }

        console.log(`[DocumentStorage] Deleted ${count} documents older than ${days} days`);
        return count;
    }

    /**
     * Get storage statistics.
     * @returns {Promise<Object>} Storage stats
     */
    async getStorageStats() {
        await this.ensureInitialized();

        let totalSize = 0;
        let documentCount = 0;

        try {
            for await (const entry of this.rootDir.values()) {
                if (entry.kind === 'file' && entry.name.endsWith('.sfr')) {
                    const fileHandle = await this.rootDir.getFileHandle(entry.name);
                    const file = await fileHandle.getFile();
                    totalSize += file.size;
                    documentCount++;
                }
            }
        } catch (error) {
            console.error('[DocumentStorage] Failed to get storage stats:', error);
        }

        // Try to get browser storage estimate
        let storageEstimate = null;
        try {
            storageEstimate = await navigator.storage.estimate();
        } catch (e) {
            // Not available
        }

        return {
            totalSize,
            documentCount,
            maxDocumentSize: this.maxDocumentSize,
            maxTotalSize: this.maxTotalSize,
            minKeepCount: this.minKeepCount,
            browserQuota: storageEstimate?.quota || null,
            browserUsage: storageEstimate?.usage || null
        };
    }

    /**
     * Run cleanup to enforce size limits.
     * Removes oldest documents until within limits, keeping at least minKeepCount.
     */
    async runCleanup() {
        await this.ensureInitialized();

        const manifest = await this.loadManifest();
        if (!manifest || manifest.documents.length <= this.minKeepCount) {
            return;
        }

        // Calculate total size
        let totalSize = 0;
        for (const doc of manifest.documents) {
            totalSize += doc.fileSize || 0;
        }

        if (totalSize <= this.maxTotalSize) {
            return;
        }

        // Sort by lastModified (oldest first)
        const sorted = [...manifest.documents].sort((a, b) => a.lastModified - b.lastModified);

        // Remove oldest documents until within limit, keeping minKeepCount
        let deleted = 0;
        for (const doc of sorted) {
            if (manifest.documents.length - deleted <= this.minKeepCount) {
                break;
            }
            if (totalSize <= this.maxTotalSize) {
                break;
            }

            if (await this.deleteDocument(doc.id)) {
                totalSize -= doc.fileSize || 0;
                deleted++;
            }
        }

        if (deleted > 0) {
            console.log(`[DocumentStorage] Cleanup removed ${deleted} documents`);
        }
    }

    // === Manifest Operations ===

    /**
     * Load the manifest file.
     * @returns {Promise<Object|null>}
     */
    async loadManifest() {
        try {
            const fileHandle = await this.rootDir.getFileHandle('manifest.json');
            const file = await fileHandle.getFile();
            const text = await file.text();
            return JSON.parse(text);
        } catch (error) {
            if (error.name !== 'NotFoundError') {
                console.error('[DocumentStorage] Failed to load manifest:', error);
            }
            return { version: 1, documents: [] };
        }
    }

    /**
     * Save the manifest file.
     * @param {Object} manifest
     */
    async saveManifest(manifest) {
        try {
            const fileHandle = await this.rootDir.getFileHandle('manifest.json', { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(JSON.stringify(manifest, null, 2));
            await writable.close();
        } catch (error) {
            console.error('[DocumentStorage] Failed to save manifest:', error);
        }
    }

    /**
     * Update manifest with document metadata.
     * @param {Document} doc - The document
     * @param {number} fileSize - File size in bytes
     */
    async updateManifest(doc, fileSize) {
        const manifest = await this.loadManifest();

        // Find or create entry
        const existing = manifest.documents.find(d => d.id === doc.id);
        const entry = {
            id: doc.id,
            name: doc.name,
            icon: doc.icon || '🎨',
            color: doc.color || '#E0E7FF',
            width: doc.width,
            height: doc.height,
            lastModified: Date.now(),
            createdAt: existing?.createdAt || doc.createdAt || Date.now(),
            fileSize: fileSize,
            layerCount: doc.layerStack?.layers?.length || 0
        };

        if (existing) {
            Object.assign(existing, entry);
        } else {
            manifest.documents.push(entry);
        }

        await this.saveManifest(manifest);
    }
}
