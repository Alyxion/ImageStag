/**
 * AutoSave - Automatic document persistence using browser OPFS.
 *
 * Periodically checks for document changes and saves to Origin Private File System.
 * Restores documents on page reload.
 *
 * Features:
 * - Per-browser-tab storage using sessionStorage tab ID
 * - Periodic change detection based on history index
 * - ZIP-based document serialization (consistent with .sfr file format)
 * - WebP image caching for fast saves
 * - Automatic restoration on page load
 */

import { serializeDocumentToZip, parseDocumentZip, processLayerImages } from './FileManager.js';

export class AutoSave {
    /**
     * @param {Object} app - The editor app context
     * @param {Object} options - Configuration options
     * @param {number} [options.interval=5000] - Check interval in milliseconds
     * @param {number} [options.sessionTimeout=1800000] - Session cleanup timeout (30 min default)
     * @param {boolean} [options.disabled=false] - Disable auto-save (for isolated/embedded mode)
     */
    constructor(app, options = {}) {
        this.app = app;
        this.interval = options.interval || 5000;  // 5 seconds default
        this.sessionTimeout = options.sessionTimeout || 30 * 60 * 1000;  // 30 minutes
        this.disabled = options.disabled || false;

        // State tracking
        this.tabId = this.getOrCreateTabId();
        this.lastSavedState = new Map();  // documentId -> historyIndex
        this.timer = null;
        this.isInitialized = false;
        this.isSaving = false;

        // OPFS handles
        this.rootDir = null;
        this.tabDir = null;

        console.log(`[AutoSave] Initialized with tabId: ${this.tabId}`);
    }

    /**
     * Get or create a unique tab ID that persists across page reloads.
     */
    getOrCreateTabId() {
        const storageKey = 'stagforge_autosave_tab_id';
        let tabId = sessionStorage.getItem(storageKey);
        if (!tabId) {
            tabId = crypto.randomUUID();
            sessionStorage.setItem(storageKey, tabId);
        }
        return tabId;
    }

    /**
     * Initialize OPFS storage and start auto-save timer.
     */
    async initialize() {
        if (this.disabled) {
            console.log('[AutoSave] Disabled (isolated mode)');
            return;
        }

        try {
            // Initialize OPFS directory structure
            const root = await navigator.storage.getDirectory();
            this.rootDir = await root.getDirectoryHandle('stagforge_autosave', { create: true });
            this.tabDir = await this.rootDir.getDirectoryHandle(this.tabId, { create: true });

            this.isInitialized = true;
            console.log('[AutoSave] OPFS initialized');

            // Start the auto-save timer
            this.startTimer();

            // Set up cleanup on tab close
            window.addEventListener('beforeunload', () => this.saveSessionCloseTime());

            // Clean up stale sessions from other tabs
            await this.cleanupStaleSessions();

        } catch (error) {
            console.error('[AutoSave] Failed to initialize OPFS:', error);
            this.isInitialized = false;
        }
    }

    /**
     * Check for saved documents and restore them.
     * Call this BEFORE creating the default document.
     * @returns {Promise<boolean>} True if documents were restored
     */
    async restoreDocuments() {
        if (this.disabled) {
            console.log('[AutoSave] Restore disabled (isolated mode)');
            return false;
        }

        if (!this.isInitialized) {
            await this.initialize();
        }

        if (!this.tabDir) {
            console.warn('[AutoSave] Cannot restore - OPFS not available');
            return false;
        }

        try {
            const manifest = await this.loadManifest();
            if (!manifest || manifest.documents.length === 0) {
                console.log('[AutoSave] No documents to restore');
                return false;
            }

            console.log(`[AutoSave] Restoring ${manifest.documents.length} document(s)`);

            let restoredCount = 0;
            for (const docInfo of manifest.documents) {
                try {
                    const result = await this.loadDocumentZip(docInfo.id);
                    if (result) {
                        const { data, layerImages } = result;
                        const docData = data.document;

                        // Process layers to load images/SVGs from ZIP
                        await processLayerImages(docData, layerImages);

                        // Import Document class dynamically
                        const { Document } = await import('./Document.js');

                        // Deserialize the document (keeps original ID for stable auto-save)
                        const doc = await Document.deserialize(docData, this.app.eventBus);

                        // Add to document manager
                        this.app.documentManager.documents.push(doc);

                        // Mark as modified - restored documents have no file representation
                        doc.markModified();

                        // Track the history state from manifest
                        this.lastSavedState.set(doc.id, docInfo.historyIndex || 0);

                        restoredCount++;
                        console.log(`[AutoSave] Restored document: ${doc.name} (${doc.id})`);
                    }
                } catch (error) {
                    console.error(`[AutoSave] Failed to restore document ${docInfo.id}:`, error);
                }
            }

            if (restoredCount > 0) {
                // Activate the first document
                const firstDoc = this.app.documentManager.documents[0];
                if (firstDoc) {
                    this.app.documentManager.setActiveDocument(firstDoc.id);
                }

                // Emit event to update UI
                this.app.eventBus.emit('documents:restored', { count: restoredCount });

                return true;
            }

            return false;

        } catch (error) {
            console.error('[AutoSave] Failed to restore documents:', error);
            return false;
        }
    }

    /**
     * Start the auto-save timer.
     */
    startTimer() {
        if (this.timer) {
            clearInterval(this.timer);
        }

        this.timer = setInterval(() => this.checkAndSave(), this.interval);
        console.log(`[AutoSave] Timer started (${this.interval}ms interval)`);
    }

    /**
     * Stop the auto-save timer.
     */
    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
            console.log('[AutoSave] Timer stopped');
        }
    }

    /**
     * Check all documents for changes and save if needed.
     */
    async checkAndSave() {
        if (!this.isInitialized || this.isSaving) {
            return;
        }

        if (!this.app.documentManager) {
            return;
        }

        const documents = this.app.documentManager.documents;
        if (!documents || documents.length === 0) {
            return;
        }

        const changedDocs = [];

        for (const doc of documents) {
            const currentIndex = doc.history?.getCurrentIndex() || 0;
            const lastIndex = this.lastSavedState.get(doc.id) || 0;

            if (currentIndex !== lastIndex) {
                changedDocs.push(doc);
            }
        }

        if (changedDocs.length > 0) {
            await this.saveDocuments(changedDocs);
        }
    }

    /**
     * Save multiple documents to OPFS.
     */
    async saveDocuments(documents) {
        if (this.isSaving) {
            return;
        }

        this.isSaving = true;

        // Emit saving event for status indicator
        this.app.eventBus.emit('autosave:saving', { count: documents.length });

        try {
            const manifest = {
                tabId: this.tabId,
                savedAt: Date.now(),
                documents: []
            };

            for (const doc of documents) {
                try {
                    // Get current history index for change tracking
                    const historyIndex = doc.history?.getCurrentIndex() || 0;
                    const savedAt = Date.now();

                    // Serialize document to ZIP format (uses cached WebP blobs)
                    const zipBlob = await serializeDocumentToZip(doc);

                    // Save ZIP to OPFS
                    await this.saveDocumentZip(doc.id, zipBlob);

                    // Update tracking
                    this.lastSavedState.set(doc.id, historyIndex);

                    manifest.documents.push({
                        id: doc.id,
                        name: doc.name,
                        savedAt: savedAt,
                        historyIndex: historyIndex
                    });

                } catch (error) {
                    console.error(`[AutoSave] Failed to save document ${doc.id}:`, error);
                }
            }

            // Also include unchanged documents in manifest
            for (const doc of this.app.documentManager.documents) {
                if (!manifest.documents.find(d => d.id === doc.id)) {
                    manifest.documents.push({
                        id: doc.id,
                        name: doc.name,
                        savedAt: this.lastSavedState.get(doc.id) ? Date.now() : 0,
                        historyIndex: this.lastSavedState.get(doc.id) || 0
                    });
                }
            }

            // Save manifest
            await this.saveManifest(manifest);

            // Clean up orphaned document files not in manifest
            await this.cleanupOrphanedFiles(manifest);

            const savedAt = Date.now();
            console.log(`[AutoSave] Saved ${documents.length} document(s) as ZIP`);

            // Emit saved event for status indicator
            this.app.eventBus.emit('autosave:saved', {
                count: documents.length,
                timestamp: savedAt
            });

        } finally {
            this.isSaving = false;
        }
    }

    /**
     * Force save all documents (e.g., before page unload).
     */
    async saveAll() {
        if (!this.isInitialized || !this.app.documentManager) {
            return;
        }

        const documents = this.app.documentManager.documents;
        if (documents && documents.length > 0) {
            await this.saveDocuments(documents);
        }
    }

    // === OPFS Operations ===

    /**
     * Save a document ZIP blob to OPFS.
     * @param {string} docId - Document ID
     * @param {Blob} zipBlob - ZIP blob from serializeDocumentToZip
     */
    async saveDocumentZip(docId, zipBlob) {
        const fileName = `doc_${docId}.sfr`;
        const fileHandle = await this.tabDir.getFileHandle(fileName, { create: true });
        const writable = await fileHandle.createWritable();
        await writable.write(zipBlob);
        await writable.close();
    }

    /**
     * Load a document ZIP from OPFS and parse it.
     * @param {string} docId - Document ID
     * @returns {Promise<{data: Object, layerImages: Map}|null>}
     */
    async loadDocumentZip(docId) {
        try {
            const fileName = `doc_${docId}.sfr`;
            const fileHandle = await this.tabDir.getFileHandle(fileName);
            const file = await fileHandle.getFile();

            // Parse the ZIP file
            return await parseDocumentZip(file);
        } catch (error) {
            if (error.name !== 'NotFoundError') {
                console.error(`[AutoSave] Error loading document ${docId}:`, error);
            }
            return null;
        }
    }

    /**
     * Save the manifest file.
     */
    async saveManifest(manifest) {
        const fileHandle = await this.tabDir.getFileHandle('manifest.json', { create: true });
        const writable = await fileHandle.createWritable();
        await writable.write(JSON.stringify(manifest));
        await writable.close();
    }

    /**
     * Load the manifest file.
     */
    async loadManifest() {
        try {
            const fileHandle = await this.tabDir.getFileHandle('manifest.json');
            const file = await fileHandle.getFile();
            const text = await file.text();
            return JSON.parse(text);
        } catch (error) {
            if (error.name !== 'NotFoundError') {
                console.error('[AutoSave] Error loading manifest:', error);
            }
            return null;
        }
    }

    /**
     * Save session close time for cleanup detection.
     */
    async saveSessionCloseTime() {
        if (!this.tabDir) return;

        try {
            const fileHandle = await this.tabDir.getFileHandle('_session.json', { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(JSON.stringify({
                tabId: this.tabId,
                closedAt: Date.now(),
                timeout: this.sessionTimeout
            }));
            await writable.close();
        } catch (error) {
            // Ignore errors during unload
        }
    }

    /**
     * Clean up stale sessions from other tabs.
     */
    async cleanupStaleSessions() {
        if (!this.rootDir) return;

        const now = Date.now();
        const toDelete = [];

        try {
            for await (const entry of this.rootDir.values()) {
                if (entry.kind !== 'directory' || entry.name === this.tabId) {
                    continue;
                }

                try {
                    const tabDir = await this.rootDir.getDirectoryHandle(entry.name);
                    const sessionHandle = await tabDir.getFileHandle('_session.json');
                    const sessionFile = await sessionHandle.getFile();
                    const sessionData = JSON.parse(await sessionFile.text());

                    if (sessionData.closedAt) {
                        const expireTime = sessionData.closedAt + (sessionData.timeout || this.sessionTimeout);
                        if (now > expireTime) {
                            toDelete.push(entry.name);
                        }
                    }
                } catch (error) {
                    // No session file or invalid - check if directory is old
                    // We could add more sophisticated cleanup here
                }
            }

            // Delete stale tab directories
            for (const tabId of toDelete) {
                try {
                    await this.rootDir.removeEntry(tabId, { recursive: true });
                    console.log(`[AutoSave] Cleaned up stale session: ${tabId}`);
                } catch (error) {
                    console.warn(`[AutoSave] Failed to clean up session ${tabId}:`, error);
                }
            }

        } catch (error) {
            console.warn('[AutoSave] Error during session cleanup:', error);
        }
    }

    /**
     * Remove document files that are not referenced in the manifest.
     * @param {Object} manifest - Current manifest with document list
     */
    async cleanupOrphanedFiles(manifest) {
        if (!this.tabDir) return;

        const validIds = new Set(manifest.documents.map(d => d.id));
        const toDelete = [];

        try {
            for await (const entry of this.tabDir.values()) {
                if (entry.kind === 'file' && entry.name.startsWith('doc_') && entry.name.endsWith('.sfr')) {
                    // Extract document ID from filename: doc_{id}.sfr
                    const docId = entry.name.slice(4, -4);  // Remove 'doc_' prefix and '.sfr' suffix
                    if (!validIds.has(docId)) {
                        toDelete.push(entry.name);
                    }
                }
            }

            for (const fileName of toDelete) {
                try {
                    await this.tabDir.removeEntry(fileName);
                    console.log(`[AutoSave] Removed orphaned file: ${fileName}`);
                } catch (error) {
                    console.warn(`[AutoSave] Failed to remove orphaned file ${fileName}:`, error);
                }
            }
        } catch (error) {
            console.warn('[AutoSave] Error during orphan cleanup:', error);
        }
    }

    /**
     * Clear all auto-save data for current tab.
     */
    async clear() {
        if (!this.rootDir || !this.tabId) return;

        try {
            await this.rootDir.removeEntry(this.tabId, { recursive: true });
            this.tabDir = await this.rootDir.getDirectoryHandle(this.tabId, { create: true });
            this.lastSavedState.clear();
            console.log('[AutoSave] Cleared all auto-save data');
        } catch (error) {
            console.error('[AutoSave] Failed to clear auto-save data:', error);
        }
    }

    /**
     * Dispose of resources.
     */
    dispose() {
        this.stopTimer();
        this.isInitialized = false;
    }
}
