/**
 * Stagforge Browser - Simple vanilla JS for browsing sessions/documents/layers
 * No SPA, no routing - just fetch data and render based on current URL
 */

const API_BASE = '/api';

// Auto-refresh timer
let refreshTimer = null;

// ==================== Utilities ====================

async function api(endpoint) {
    const start = performance.now();
    const resp = await fetch(API_BASE + endpoint);
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    const data = await resp.json();
    return { data, duration: performance.now() - start };
}

function formatDuration(ms) {
    return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return 'N/A';
    const time = typeof timestamp === 'string' ? new Date(timestamp).getTime() : timestamp;
    if (isNaN(time)) return 'N/A';
    const seconds = Math.floor((Date.now() - time) / 1000);
    if (seconds < 0) return 'just now';
    if (seconds < 60) return seconds + 's ago';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    return Math.floor(seconds / 3600) + 'h ago';
}

// ==================== URL Parsing ====================

// Detect base path from current URL (e.g., /api/browse)
const BROWSE_BASE = (function() {
    const path = window.location.pathname;
    // Strip everything after "browse" - handles /api/browse, /browse, etc.
    const match = path.match(/^(.*\/browse)\/?/);
    return match ? match[1] : '/browse';
})();

function parseRoute() {
    const path = window.location.pathname;
    const params = new URLSearchParams(window.location.search);

    // Extract the portion after BROWSE_BASE
    // e.g., /api/browse/current/0/layer/foo → current/0/layer/foo
    let subPath = '';
    if (path.startsWith(BROWSE_BASE)) {
        subPath = path.slice(BROWSE_BASE.length);
        // Remove leading slash
        if (subPath.startsWith('/')) subPath = subPath.slice(1);
    }

    // Parse: {session}/{docIndex}/layer/{layerId}
    const match = subPath.match(/^([^\/]+)?(?:\/(\d+))?(?:\/layer\/(.+))?$/);

    if (!match) {
        return { view: 'sessions', session: null, document: null, layer: null, tab: 'layers' };
    }

    const [, sessionPart, docIndex, layerId] = match;
    const tab = params.get('tab') || 'layers';

    if (!sessionPart) {
        return { view: 'sessions', session: null, document: null, layer: null, tab };
    }

    return {
        view: layerId ? 'layer' : (docIndex !== undefined ? 'document' : 'session'),
        session: sessionPart,
        document: docIndex !== undefined ? parseInt(docIndex, 10) : null,
        layer: layerId ? decodeURIComponent(layerId) : null,
        tab,
    };
}

function buildUrl(session, docIndex = null, layerId = null, tab = null) {
    let url = BROWSE_BASE;

    if (session) {
        url += '/' + encodeURIComponent(session);
        if (docIndex !== null) {
            url += '/' + docIndex;
            if (layerId !== null) {
                url += '/layer/' + encodeURIComponent(layerId);
            }
        }
    }

    if (tab && tab !== 'layers') {
        url += '?tab=' + tab;
    }
    return url;
}

// ==================== Views ====================

async function renderSessions() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">Loading sessions...</div>';

    try {
        const [sessionsResult, bridgeResult] = await Promise.all([
            api('/sessions'),
            api('/bridge/stats').catch(() => ({ data: {} }))
        ]);

        const sessions = sessionsResult.data.sessions || [];
        const bridgeData = bridgeResult.data;
        const commandStats = bridgeData.command_stats || {};
        const totalSessions = bridgeData.session_count || 0;
        const connectedSessions = bridgeData.connected_count || 0;
        const bridgeSessions = bridgeData.sessions || [];

        let statsHtml = '';
        if (bridgeData.session_count !== undefined) {
            const bridgeSessionsHtml = bridgeSessions.length > 0 ? `
                <div class="bridge-sessions">
                    <h4>Bridge Sessions</h4>
                    ${bridgeSessions.map(bs => `
                        <div class="bridge-session ${bs.connected ? 'connected' : 'disconnected'}">
                            <span class="id" title="${bs.id}">${bs.id.slice(0, 12)}...</span>
                            <span class="status">${bs.connected ? '🟢' : '🔴'}</span>
                        </div>
                    `).join('')}
                </div>
            ` : '';

            statsHtml = `
                <div class="stats-panel">
                    <h3>Bridge Statistics</h3>
                    <div class="stats-grid">
                        <div class="stat">
                            <span class="label">Connected</span>
                            <span class="value">${connectedSessions}</span>
                            <span class="detail">${totalSessions} total (${totalSessions - connectedSessions} disconnected)</span>
                        </div>
                        ${Object.entries(commandStats).map(([method, stats]) => `
                            <div class="stat">
                                <span class="label">${method}</span>
                                <span class="value">${stats.count}x</span>
                                <span class="detail">avg: ${stats.avg_ms}ms, min: ${stats.min_ms}ms, max: ${stats.max_ms}ms</span>
                            </div>
                        `).join('')}
                    </div>
                    ${bridgeSessionsHtml}
                </div>
            `;
        }

        if (sessions.length === 0) {
            main.innerHTML = `
                <div class="page-header">
                    <h1>Sessions</h1>
                    <span class="meta">Loaded in ${formatDuration(sessionsResult.duration)}</span>
                </div>
                <div class="empty-state">
                    <span class="icon">🖼️</span>
                    <p>No active sessions</p>
                    <p class="hint">Open the editor to create a session</p>
                </div>
                ${statsHtml}
            `;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>Sessions</h1>
                <span class="meta">${sessions.length} session(s) &bull; Loaded in ${formatDuration(sessionsResult.duration)}</span>
            </div>
            <div class="card-grid">
                ${sessions.map((s, i) => `
                    <a href="${buildUrl(i === 0 ? 'current' : s.id)}" class="card session-card">
                        <div class="card-header">
                            <span class="title session-id">${s.id}</span>
                            ${i === 0 ? '<span class="badge current">current</span>' : ''}
                        </div>
                        <div class="card-body">
                            <div class="stat-row">
                                <span class="label">Documents</span>
                                <span class="value">${s.document_count || 0}</span>
                            </div>
                            <div class="stat-row">
                                <span class="label">Last Activity</span>
                                <span class="value">${formatTimeAgo(s.last_activity)}</span>
                            </div>
                        </div>
                    </a>
                `).join('')}
            </div>
            ${statsHtml}
        `;
    } catch (e) {
        main.innerHTML = `<div class="error">${e.message}</div>`;
    }
}

async function renderSession(sessionId) {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">Loading session...</div>';

    try {
        // Resolve 'current' to actual session ID
        let actualSessionId = sessionId;
        if (sessionId === 'current') {
            const { data } = await api('/sessions');
            const sessions = data.sessions || [];
            if (sessions.length === 0) {
                main.innerHTML = '<div class="error">No sessions available</div>';
                return;
            }
            actualSessionId = sessions[0].id;
        }

        const { data, duration } = await api(`/sessions/${actualSessionId}/documents`);
        const documents = data.documents || [];

        if (documents.length === 0) {
            main.innerHTML = `
                <div class="page-header">
                    <h1>Session</h1>
                    <span class="meta session-id">${actualSessionId}</span>
                    <span class="meta">&bull; Loaded in ${formatDuration(duration)}</span>
                </div>
                <div class="empty-state">
                    <span class="icon">📄</span>
                    <p>No documents in this session</p>
                </div>
            `;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>Session</h1>
                <span class="meta session-id">${actualSessionId}</span>
                <span class="meta">&bull; ${documents.length} document(s) &bull; Loaded in ${formatDuration(duration)}</span>
            </div>
            <div class="card-grid">
                ${documents.map((doc, i) => `
                    <a href="${buildUrl(sessionId, i)}" class="card doc-card">
                        <div class="card-thumb">
                            <img src="${API_BASE}/sessions/${actualSessionId}/documents/${doc.id}/image?format=webp&t=${Date.now()}"
                                 alt="${doc.name}" loading="lazy"
                                 onerror="this.parentElement.innerHTML='<span class=\\'thumb-error\\'>No preview</span>'">
                        </div>
                        <div class="card-header">
                            <span class="title">${doc.name || 'Untitled'}</span>
                            ${i === 0 ? '<span class="badge current">current</span>' : ''}
                        </div>
                        <div class="card-body">
                            <div class="stat-row">
                                <span class="label">Size</span>
                                <span class="value">${doc.width}x${doc.height}</span>
                            </div>
                            <div class="stat-row">
                                <span class="label">Layers</span>
                                <span class="value">${doc.layer_count || '?'}</span>
                            </div>
                        </div>
                    </a>
                `).join('')}
            </div>
        `;
    } catch (e) {
        main.innerHTML = `<div class="error">${e.message}</div>`;
    }
}

async function renderDocument(sessionId, docIndex, tab) {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">Loading document...</div>';

    try {
        // Resolve session
        let actualSessionId = sessionId;
        if (sessionId === 'current') {
            const { data } = await api('/sessions');
            const sessions = data.sessions || [];
            if (sessions.length === 0) {
                main.innerHTML = '<div class="error">No sessions available</div>';
                return;
            }
            actualSessionId = sessions[0].id;
        }

        // Get documents list
        const { data: docsData } = await api(`/sessions/${actualSessionId}/documents`);
        const documents = docsData.documents || [];

        if (docIndex >= documents.length) {
            main.innerHTML = `<div class="error">Document ${docIndex} not found</div>`;
            return;
        }

        const doc = documents[docIndex];
        const [{ data: docData }, { data: layersData, duration }] = await Promise.all([
            api(`/sessions/${actualSessionId}/documents/${doc.id}`),
            api(`/sessions/${actualSessionId}/documents/${doc.id}/layers`)
        ]);

        const layers = layersData.layers || [];

        main.innerHTML = `
            <div class="page-header">
                <h1>${docData.name || 'Untitled'}</h1>
                <span class="meta">${docData.width}x${docData.height} &bull; ${layers.length} layer(s) &bull; Loaded in ${formatDuration(duration)}</span>
            </div>

            <div class="tabs">
                <a href="${buildUrl(sessionId, docIndex, null, 'layers')}" class="tab ${tab === 'layers' ? 'active' : ''}">Layers</a>
                <a href="${buildUrl(sessionId, docIndex, null, 'composite')}" class="tab ${tab === 'composite' ? 'active' : ''}">Composite</a>
            </div>

            <div id="tab-content"></div>
        `;

        const tabContent = document.getElementById('tab-content');
        if (tab === 'layers') {
            tabContent.innerHTML = renderLayersTab(actualSessionId, doc.id, layers, sessionId, docIndex);
            startAutoRefresh(actualSessionId, doc.id, 'layers');
        } else if (tab === 'composite') {
            tabContent.innerHTML = renderCompositeTab(actualSessionId, doc.id, docData.name);
            startAutoRefresh(actualSessionId, doc.id, 'composite');
        }
    } catch (e) {
        main.innerHTML = `<div class="error">${e.message}</div>`;
    }
}

function renderLayersTab(actualSessionId, docId, layers, sessionId, docIndex) {
    return `
        <div class="layer-grid">
            ${layers.map(layer => {
                const isGroup = layer.type === 'group';
                const isSVG = layer.type === 'svg';
                const layerSelector = layer.name || layer.id;
                // Use layer's native format if available, fallback to type-based default
                const thumbFormat = layer.format || (isSVG ? 'svg' : 'webp');
                const imgUrl = isGroup ? '' : `${API_BASE}/sessions/${actualSessionId}/documents/${docId}/layers/${encodeURIComponent(layerSelector)}/image?format=${thumbFormat}&t=${Date.now()}`;

                return `
                    <a href="${buildUrl(sessionId, docIndex, layerSelector)}" class="layer-card">
                        <div class="layer-thumb">
                            ${isGroup
                                ? '<span class="thumb-folder">📁</span>'
                                : `<img src="${imgUrl}" alt="${layer.name}" loading="lazy" onerror="this.parentElement.innerHTML='<span class=\\'thumb-error\\'>No preview</span>'">`}
                        </div>
                        <div class="layer-info">
                            <span class="layer-name">${layer.name}</span>
                            <span class="layer-type badge ${layer.type}">${layer.type}</span>
                        </div>
                        <div class="layer-meta-small">
                            ${layer.width || '?'}x${layer.height || '?'} &bull; ${Math.round((layer.opacity || 1) * 100)}%
                        </div>
                    </a>
                `;
            }).join('')}
        </div>
    `;
}

function renderCompositeTab(actualSessionId, docId, docName) {
    // Store composite info for download
    window._currentCompositeDownload = {
        sessionId: actualSessionId,
        docId: docId,
        docName: docName || 'composite'
    };

    return `
        <div class="preview-panel">
            <div class="preview-header">
                <span class="title">Composite</span>
                <div class="actions">
                    <div class="download-dropdown">
                        <button class="download-btn" onclick="toggleDownloadMenu()">Download ▾</button>
                        <div class="download-menu" id="download-menu">
                            <a href="#" onclick="downloadComposite('png'); return false;">PNG</a>
                            <a href="#" onclick="downloadComposite('webp'); return false;">WebP</a>
                            <a href="#" onclick="downloadComposite('avif'); return false;">AVIF</a>
                        </div>
                    </div>
                </div>
            </div>
            <div class="preview-content">
                <img id="composite-img" src="${API_BASE}/sessions/${actualSessionId}/documents/${docId}/image?format=webp&t=${Date.now()}" alt="Composite">
            </div>
        </div>
    `;
}

async function renderLayer(sessionId, docIndex, layerId) {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">Loading layer...</div>';

    try {
        // Resolve session
        let actualSessionId = sessionId;
        if (sessionId === 'current') {
            const { data } = await api('/sessions');
            const sessions = data.sessions || [];
            if (sessions.length === 0) {
                main.innerHTML = '<div class="error">No sessions available</div>';
                return;
            }
            actualSessionId = sessions[0].id;
        }

        // Get documents
        const { data: docsData } = await api(`/sessions/${actualSessionId}/documents`);
        const documents = docsData.documents || [];

        if (docIndex >= documents.length) {
            main.innerHTML = `<div class="error">Document ${docIndex} not found</div>`;
            return;
        }

        const doc = documents[docIndex];

        // Get layers
        const { data: layersData } = await api(`/sessions/${actualSessionId}/documents/${doc.id}/layers`);
        const layers = layersData.layers || [];

        // Find layer by ID or name
        let layer = layers.find(l => l.id === layerId || l.name === layerId);
        if (!layer) {
            main.innerHTML = `<div class="error">Layer "${layerId}" not found</div>`;
            return;
        }

        const isSVG = layer.type === 'svg';
        const isGroup = layer.type === 'group';
        // Use layer's native format if available, fallback to type-based default
        const previewFormat = layer.format || (isSVG ? 'svg' : 'webp');

        if (isGroup) {
            main.innerHTML = `
                <div class="page-header">
                    <h1>${layer.name}</h1>
                    <span class="badge group">group</span>
                </div>
                <div class="preview-panel">
                    <div class="preview-content" style="flex-direction: column; gap: 16px;">
                        <span style="font-size: 64px;">📁</span>
                        <p>Group layers contain other layers and cannot be exported directly.</p>
                        <p class="hint">Children: ${layer.children?.length || 0} layers</p>
                    </div>
                </div>
            `;
            return;
        }

        // Store layer info for download function
        window._currentLayerDownload = {
            sessionId: actualSessionId,
            docId: doc.id,
            layerId: layer.id,
            layerName: layer.name,
            isVector
        };

        main.innerHTML = `
            <div class="page-header">
                <h1>${layer.name}</h1>
                <span class="badge ${layer.type}">${layer.type}</span>
                <span class="meta">${layer.width || '?'}x${layer.height || '?'}</span>
                <span class="refresh-indicator" id="refresh-indicator">🔄</span>
            </div>

            <div class="layer-meta">
                <div class="stat-row"><span class="label">Visible</span><span class="value">${layer.visible ? 'Yes' : 'No'}</span></div>
                <div class="stat-row"><span class="label">Opacity</span><span class="value">${Math.round((layer.opacity || 1) * 100)}%</span></div>
                <div class="stat-row"><span class="label">Blend Mode</span><span class="value">${layer.blend_mode || 'normal'}</span></div>
                <div class="stat-row"><span class="label">Position</span><span class="value">${layer.offset_x || 0}, ${layer.offset_y || 0}</span></div>
            </div>

            <div class="preview-panel">
                <div class="preview-header">
                    <span class="title">Preview</span>
                    <div class="actions">
                        <div class="download-dropdown">
                            <button class="download-btn" onclick="toggleDownloadMenu()">Download ▾</button>
                            <div class="download-menu" id="download-menu">
                                ${isVector ? `
                                    <a href="#" onclick="downloadLayer('svg'); return false;">SVG</a>
                                    <a href="#" onclick="downloadLayer('png'); return false;">PNG</a>
                                    <a href="#" onclick="downloadLayer('webp'); return false;">WebP</a>
                                    <a href="#" onclick="downloadLayer('json'); return false;">JSON</a>
                                ` : `
                                    <a href="#" onclick="downloadLayer('png'); return false;">PNG</a>
                                    <a href="#" onclick="downloadLayer('webp'); return false;">WebP</a>
                                    <a href="#" onclick="downloadLayer('avif'); return false;">AVIF</a>
                                `}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="preview-content" id="preview-content">
                    <img id="layer-preview-img" src="${API_BASE}/sessions/${actualSessionId}/documents/${doc.id}/layers/${layer.id}/image?format=${previewFormat}&t=${Date.now()}" alt="Layer preview">
                </div>
            </div>
        `;

        // Start auto-refresh for layer preview
        startLayerAutoRefresh(actualSessionId, doc.id, layer.id, previewFormat);

    } catch (e) {
        main.innerHTML = `<div class="error">${e.message}</div>`;
    }
}

// ==================== Actions ====================

function toggleDownloadMenu() {
    const menu = document.getElementById('download-menu');
    if (menu) {
        menu.classList.toggle('show');
    }
}

function downloadLayer(format) {
    const info = window._currentLayerDownload;
    if (!info) return;

    const ext = { png: '.png', webp: '.webp', avif: '.avif', svg: '.svg', json: '.json' }[format] || '';
    const url = `${API_BASE}/sessions/${info.sessionId}/documents/${info.docId}/layers/${info.layerId}/image?format=${format}`;

    const a = document.createElement('a');
    a.href = url;
    a.download = info.layerName + ext;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Hide menu after download
    const menu = document.getElementById('download-menu');
    if (menu) menu.classList.remove('show');
}

function downloadComposite(format) {
    const info = window._currentCompositeDownload;
    if (!info) return;

    const ext = { png: '.png', webp: '.webp', avif: '.avif' }[format] || '.png';
    const url = `${API_BASE}/sessions/${info.sessionId}/documents/${info.docId}/image?format=${format}`;

    const a = document.createElement('a');
    a.href = url;
    a.download = info.docName + ext;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Hide menu after download
    const menu = document.getElementById('download-menu');
    if (menu) menu.classList.remove('show');
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.download-dropdown')) {
        const menu = document.getElementById('download-menu');
        if (menu) menu.classList.remove('show');
    }
});

// ==================== Auto-Refresh ====================

function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

function startAutoRefresh(sessionId, docId, tab) {
    stopAutoRefresh();
    refreshTimer = setInterval(() => {
        const timestamp = Date.now();
        if (tab === 'layers') {
            document.querySelectorAll('.layer-thumb img').forEach(img => {
                const src = img.src.replace(/[&?]t=\d+/, '');
                img.src = src + (src.includes('?') ? '&' : '?') + 't=' + timestamp;
            });
        } else if (tab === 'composite') {
            const img = document.getElementById('composite-img');
            if (img) {
                const src = img.src.replace(/[&?]t=\d+/, '');
                img.src = src + (src.includes('?') ? '&' : '?') + 't=' + timestamp;
            }
        }
    }, 1000);
}

function startLayerAutoRefresh(sessionId, docId, layerId, format) {
    stopAutoRefresh();
    refreshTimer = setInterval(() => {
        const img = document.getElementById('layer-preview-img');
        if (img) {
            const timestamp = Date.now();
            img.src = `${API_BASE}/sessions/${sessionId}/documents/${docId}/layers/${layerId}/image?format=${format}&t=${timestamp}`;
            // Flash indicator
            const indicator = document.getElementById('refresh-indicator');
            if (indicator) {
                indicator.style.opacity = '1';
                setTimeout(() => indicator.style.opacity = '0.3', 200);
            }
        }
    }, 1000);
}

// ==================== Breadcrumb ====================

async function updateBreadcrumb(route) {
    const bc = document.getElementById('breadcrumb');
    let html = `<a href="${BROWSE_BASE}">Sessions</a>`;

    if (route.session) {
        html += '<span class="sep">/</span>';
        // Show full ID for 'current', otherwise show truncated with tooltip for full ID
        const displayId = route.session === 'current' ? 'current' : route.session.slice(0, 12) + '...';
        const titleAttr = route.session === 'current' ? '' : ` title="${route.session}"`;
        html += `<a href="${buildUrl(route.session)}"${titleAttr}>${displayId}</a>`;
    }

    if (route.document !== null) {
        html += '<span class="sep">/</span>';
        html += `<a href="${buildUrl(route.session, route.document)}">Doc ${route.document}</a>`;
    }

    if (route.layer) {
        html += '<span class="sep">/</span>';
        html += `<span>${route.layer}</span>`;
    }

    bc.innerHTML = html;
}

// ==================== Init ====================

// Make functions available for onclick handlers
window.toggleDownloadMenu = toggleDownloadMenu;
window.downloadLayer = downloadLayer;
window.downloadComposite = downloadComposite;

// Parse route and render
async function init() {
    const route = parseRoute();
    updateBreadcrumb(route);

    switch (route.view) {
        case 'sessions':
            await renderSessions();
            break;
        case 'session':
            await renderSession(route.session);
            break;
        case 'document':
            await renderDocument(route.session, route.document, route.tab);
            break;
        case 'layer':
            await renderLayer(route.session, route.document, route.layer);
            break;
    }
}

init();
