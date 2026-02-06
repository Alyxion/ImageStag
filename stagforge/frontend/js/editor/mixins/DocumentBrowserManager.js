/**
 * DocumentBrowserManager Mixin
 *
 * Provides Vue component methods for browsing and managing stored documents.
 * Handles the Document Manager dialog and landing page recent documents.
 */

export const DocumentBrowserManagerMixin = {
    data() {
        return {
            // Stored documents from global storage
            storedDocuments: [],
            storedDocumentThumbnails: {},  // docId -> data URL

            // Storage statistics
            storageStats: null,

            // UI state
            documentBrowserOpen: false,
            deleteConfirmOpen: false,
            deleteConfirmDocId: null,
            deleteAllConfirmOpen: false,
            deleteOldConfirmOpen: false,
            deleteOldDays: 30,

            // Loading states
            loadingStoredDocuments: false,
            loadingThumbnails: new Set(),
        };
    },

    computed: {
        /**
         * Format storage usage for display.
         */
        formattedStorageUsage() {
            if (!this.storageStats) return '';
            return `${this.formatFileSize(this.storageStats.totalSize)} / ${this.formatFileSize(this.storageStats.maxTotalSize)}`;
        },

        /**
         * Storage usage percentage.
         */
        storageUsagePercent() {
            if (!this.storageStats) return 0;
            return Math.round((this.storageStats.totalSize / this.storageStats.maxTotalSize) * 100);
        },

        /**
         * Recent documents for landing page (up to 12).
         */
        recentDocuments() {
            return this.storedDocuments
                .slice()
                .sort((a, b) => b.lastModified - a.lastModified)
                .slice(0, 12);
        },
    },

    methods: {
        /**
         * Load stored documents from global storage.
         */
        async loadStoredDocuments() {
            if (!this.getState()?.documentStorage) return;

            this.loadingStoredDocuments = true;
            try {
                this.storedDocuments = await this.getState().documentStorage.listDocuments();
                this.storageStats = await this.getState().documentStorage.getStorageStats();

                // Load thumbnails for visible documents
                await this.loadVisibleThumbnails();
            } catch (error) {
                console.error('[DocumentBrowserManager] Failed to load stored documents:', error);
            } finally {
                this.loadingStoredDocuments = false;
            }
        },

        /**
         * Load thumbnails for visible documents.
         */
        async loadVisibleThumbnails() {
            if (!this.getState()?.documentStorage) return;

            // Load thumbnails for recent documents
            const docs = this.recentDocuments.slice(0, 12);
            for (const doc of docs) {
                if (!this.storedDocumentThumbnails[doc.id] && !this.loadingThumbnails.has(doc.id)) {
                    this.loadThumbnail(doc.id);
                }
            }
        },

        /**
         * Load a single thumbnail.
         */
        async loadThumbnail(docId) {
            if (!this.getState()?.documentStorage) return;
            if (this.loadingThumbnails.has(docId)) return;

            this.loadingThumbnails.add(docId);
            try {
                const dataUrl = await this.getState().documentStorage.getDocumentThumbnail(docId);
                if (dataUrl) {
                    this.storedDocumentThumbnails[docId] = dataUrl;
                }
            } catch (error) {
                console.warn(`[DocumentBrowserManager] Failed to load thumbnail for ${docId}:`, error);
            } finally {
                this.loadingThumbnails.delete(docId);
            }
        },

        /**
         * Open a stored document.
         */
        async openStoredDocument(docId) {
            if (!this.getState()?.documentStorage) return;

            try {
                const result = await this.getState().documentStorage.loadDocument(docId);
                if (!result) {
                    this.showStatusMessage('Document not found', 'error');
                    return;
                }

                const { data, layerImages } = result;
                const docData = data.document;

                // Process layer images
                const { processLayerImages } = await import('/static/js/core/FileManager.js');
                await processLayerImages(docData, layerImages);

                // Deserialize document
                const { Document } = await import('/static/js/core/Document.js');
                const doc = await Document.deserialize(docData, this.getState().eventBus);

                // Add to document manager
                this.getState().documentManager.addDocument(doc);
                this.getState().documentManager.setActiveDocument(doc.id);

                // Update renderer
                this.getState().renderer.resize(doc.width, doc.height);
                this.getState().renderer.fitToViewport();
                this.getState().renderer.requestRender();

                // Close browser dialog
                this.documentBrowserOpen = false;

                this.showStatusMessage(`Opened "${doc.name}"`, 'success');
            } catch (error) {
                console.error('[DocumentBrowserManager] Failed to open stored document:', error);
                this.showStatusMessage('Failed to open document', 'error');
            }
        },

        /**
         * Show delete confirmation for a document.
         */
        confirmDeleteStoredDocument(docId) {
            this.deleteConfirmDocId = docId;
            this.deleteConfirmOpen = true;
        },

        /**
         * Delete a stored document after confirmation.
         */
        async deleteStoredDocument() {
            if (!this.getState()?.documentStorage || !this.deleteConfirmDocId) return;

            try {
                await this.getState().documentStorage.deleteDocument(this.deleteConfirmDocId);
                this.storedDocuments = this.storedDocuments.filter(d => d.id !== this.deleteConfirmDocId);
                delete this.storedDocumentThumbnails[this.deleteConfirmDocId];
                this.storageStats = await this.getState().documentStorage.getStorageStats();
                this.showStatusMessage('Document deleted', 'success');
            } catch (error) {
                console.error('[DocumentBrowserManager] Failed to delete document:', error);
                this.showStatusMessage('Failed to delete document', 'error');
            } finally {
                this.deleteConfirmOpen = false;
                this.deleteConfirmDocId = null;
            }
        },

        /**
         * Show delete all confirmation.
         */
        confirmDeleteAllStoredDocuments() {
            this.deleteAllConfirmOpen = true;
        },

        /**
         * Delete all stored documents after confirmation.
         */
        async deleteAllStoredDocuments() {
            if (!this.getState()?.documentStorage) return;

            try {
                const count = await this.getState().documentStorage.deleteAllDocuments();
                this.storedDocuments = [];
                this.storedDocumentThumbnails = {};
                this.storageStats = await this.getState().documentStorage.getStorageStats();
                this.showStatusMessage(`Deleted ${count} documents`, 'success');
            } catch (error) {
                console.error('[DocumentBrowserManager] Failed to delete all documents:', error);
                this.showStatusMessage('Failed to delete documents', 'error');
            } finally {
                this.deleteAllConfirmOpen = false;
            }
        },

        /**
         * Show delete old documents confirmation.
         */
        confirmDeleteOldDocuments() {
            this.deleteOldConfirmOpen = true;
        },

        /**
         * Delete old documents after confirmation.
         */
        async deleteOldDocuments() {
            if (!this.getState()?.documentStorage) return;

            try {
                const count = await this.getState().documentStorage.deleteDocumentsOlderThan(this.deleteOldDays);
                await this.loadStoredDocuments();
                this.showStatusMessage(`Deleted ${count} documents older than ${this.deleteOldDays} days`, 'success');
            } catch (error) {
                console.error('[DocumentBrowserManager] Failed to delete old documents:', error);
                this.showStatusMessage('Failed to delete old documents', 'error');
            } finally {
                this.deleteOldConfirmOpen = false;
            }
        },

        /**
         * Open the Document Manager dialog.
         */
        openDocumentBrowser() {
            this.documentBrowserOpen = true;
            this.loadStoredDocuments();
        },

        /**
         * Close the Document Manager dialog.
         */
        closeDocumentBrowser() {
            this.documentBrowserOpen = false;
        },

        /**
         * Format file size for display.
         */
        formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
        },

        /**
         * Format date for display.
         */
        formatDate(timestamp) {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;

            // Less than 24 hours ago
            if (diff < 24 * 60 * 60 * 1000) {
                const hours = Math.floor(diff / (60 * 60 * 1000));
                if (hours < 1) {
                    const minutes = Math.floor(diff / (60 * 1000));
                    return minutes < 1 ? 'Just now' : `${minutes}m ago`;
                }
                return `${hours}h ago`;
            }

            // Less than 7 days ago
            if (diff < 7 * 24 * 60 * 60 * 1000) {
                const days = Math.floor(diff / (24 * 60 * 60 * 1000));
                return `${days}d ago`;
            }

            // Older - show date
            return date.toLocaleDateString();
        },

        /**
         * Get document name by ID.
         */
        getStoredDocumentName(docId) {
            const doc = this.storedDocuments.find(d => d.id === docId);
            return doc?.name || 'Unknown';
        },

        /**
         * Show status message (delegates to existing mixin method if available).
         */
        showStatusMessage(message, type = 'info') {
            // Try to use existing status message system
            if (this.statusMessage !== undefined) {
                this.statusMessage = message;
                if (this.statusMessageTimeout) {
                    clearTimeout(this.statusMessageTimeout);
                }
                this.statusMessageTimeout = setTimeout(() => {
                    this.statusMessage = '';
                }, 3000);
            } else {
                console.log(`[${type}] ${message}`);
            }
        },
    },
};
