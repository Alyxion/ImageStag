/**
 * AutoSave - Automatic document persistence using browser OPFS.
 *
 * Periodically checks for document changes and saves to Origin Private File System.
 * Restores documents on page reload.
 *
 * Features:
 * - Per-browser-tab storage using sessionStorage tab ID
 * - Periodic change detection based on history index
 * - Full document serialization including layers
 * - Automatic restoration on page load
 */

export class AutoSave {
    /**
     * @param {Object} app - The editor app context
     * @param {Object} options - Configuration options
     * @param {number} [options.interval=5000] - Check interval in milliseconds
     * @param {number} [options.sessionTimeout=1800000] - Session cleanup timeout (30 min default)
     */
    constructor(app, options = {}) {
        this.app = app;
        this.interval = options.interval || 5000;  // 5 seconds default
        this.sessionTimeout = options.sessionTimeout || 30 * 60 * 1000;  // 30 minutes

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
                    const docData = await this.loadDocument(docInfo.id);
                    if (docData) {
                        // Import Document class dynamically
                        const { Document } = await import('./Document.js');

                        // Deserialize the document
                        const doc = await Document.deserialize(docData, this.app.eventBus);

                        // Add to document manager
                        this.app.documentManager.documents.push(doc);

                        // Track the history state
                        this.lastSavedState.set(doc.id, docData._historyIndex || 0);

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
                    // Serialize the document
                    const docData = await doc.serialize();

                    // Add history index for change tracking
                    docData._historyIndex = doc.history?.getCurrentIndex() || 0;
                    docData._savedAt = Date.now();

                    // Save to OPFS
                    await this.saveDocument(doc.id, docData);

                    // Update tracking
                    this.lastSavedState.set(doc.id, docData._historyIndex);

                    manifest.documents.push({
                        id: doc.id,
                        name: doc.name,
                        savedAt: docData._savedAt
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
                        savedAt: this.lastSavedState.get(doc.id) ? Date.now() : 0
                    });
                }
            }

            // Save manifest
            await this.saveManifest(manifest);

            const savedAt = Date.now();
            console.log(`[AutoSave] Saved ${documents.length} document(s)`);

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
     * Save a document to OPFS.
     */
    async saveDocument(docId, docData) {
        const fileName = `doc_${docId}.json`;
        const fileHandle = await this.tabDir.getFileHandle(fileName, { create: true });
        const writable = await fileHandle.createWritable();
        await writable.write(JSON.stringify(docData));
        await writable.close();
    }

    /**
     * Load a document from OPFS.
     */
    async loadDocument(docId) {
        try {
            const fileName = `doc_${docId}.json`;
            const fileHandle = await this.tabDir.getFileHandle(fileName);
            const file = await fileHandle.getFile();
            const text = await file.text();
            return JSON.parse(text);
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
