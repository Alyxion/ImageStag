const API_BASE = '/api';
let currentSession = null;
let currentDocument = null;
let currentLayer = null;
let layersCache = {}; // Cache layer info by ID

// Get internal format description based on layer type
function getInternalFormat(layer) {
    switch (layer.type) {
        case 'vector':
            return 'SVG paths';
        case 'text':
            return 'Text runs';
        case 'group':
            return 'Container';
        case 'raster':
        default:
            return 'RGBA 8-bit';
    }
}

// Get default/preferred format for a layer type
function getPreferredFormat(layer) {
    switch (layer.type) {
        case 'vector':
            return 'svg';
        case 'text':
            return 'png'; // Text renders to raster
        case 'group':
            return 'png';
        case 'raster':
        default:
            return 'png';
    }
}

// Get file extension for format
function getExtension(format) {
    const extensions = { png: '.png', webp: '.webp', avif: '.avif', svg: '.svg', json: '.json' };
    return extensions[format] || '';
}

async function api(path) {
    const resp = await fetch(API_BASE + path);
    if (!resp.ok) {
        throw new Error(`API error: ${resp.status}`);
    }
    return resp.json();
}

function updateBreadcrumb() {
    const bc = document.getElementById('breadcrumb');
    let html = '<a href="#" onclick="loadSessions(); return false;">Sessions</a>';
    if (currentSession) {
        html += '<span class="sep">/</span>';
        html += `<a href="#" onclick="selectSession('${currentSession.id}'); return false;">${currentSession.id.slice(0, 8)}...</a>`;
    }
    if (currentDocument) {
        html += '<span class="sep">/</span>';
        html += `<span>${currentDocument.name || currentDocument.id.slice(0, 8)}</span>`;
    }
    bc.innerHTML = html;
}

async function loadSessions() {
    currentSession = null;
    currentDocument = null;
    currentLayer = null;
    layersCache = {};
    updateBreadcrumb();

    const list = document.getElementById('sessions-list');
    list.innerHTML = '<div class="loading">Loading...</div>';

    document.getElementById('documents-list').innerHTML = '<div class="empty">Select a session</div>';
    document.getElementById('main-content').innerHTML = '<div class="empty">Select a session and document to view layers</div>';

    try {
        const data = await api('/sessions');
        if (data.sessions.length === 0) {
            list.innerHTML = '<div class="empty">No active sessions</div>';
            return;
        }
        list.innerHTML = data.sessions.map(s => `
            <div class="list-item" onclick="selectSession('${s.id}')">
                <div class="title">${s.id.slice(0, 8)}...</div>
                <div class="meta">${s.document_count || 0} document(s)</div>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = `<div class="error">${e.message}</div>`;
    }
}

async function selectSession(sessionId) {
    currentSession = { id: sessionId };
    currentDocument = null;
    currentLayer = null;
    layersCache = {};
    updateBreadcrumb();

    // Highlight active session
    document.querySelectorAll('#sessions-list .list-item').forEach(el => {
        el.classList.toggle('active', el.onclick.toString().includes(sessionId));
    });

    const list = document.getElementById('documents-list');
    list.innerHTML = '<div class="loading">Loading...</div>';
    document.getElementById('main-content').innerHTML = '<div class="empty">Select a document to view layers</div>';

    try {
        const data = await api(`/sessions/${sessionId}/documents`);
        if (data.documents.length === 0) {
            list.innerHTML = '<div class="empty">No documents</div>';
            return;
        }
        list.innerHTML = data.documents.map(d => `
            <div class="list-item" data-doc-id="${d.id}" onclick="selectDocument('${sessionId}', '${d.id}')">
                <div class="title">${d.name || 'Untitled'}</div>
                <div class="meta">${d.width}x${d.height} &bull; ${d.layer_count || '?'} layer(s)</div>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = `<div class="error">${e.message}</div>`;
    }
}

async function selectDocument(sessionId, docId) {
    currentDocument = { id: docId };
    currentLayer = null;
    layersCache = {};
    updateBreadcrumb();

    // Highlight active document
    document.querySelectorAll('#documents-list .list-item').forEach(el => {
        el.classList.toggle('active', el.dataset.docId === docId);
    });

    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">Loading layers...</div>';

    try {
        const [docData, layersData] = await Promise.all([
            api(`/sessions/${sessionId}/documents/${docId}`),
            api(`/sessions/${sessionId}/documents/${docId}/layers`)
        ]);

        currentDocument = docData;
        updateBreadcrumb();

        // Cache layer info
        for (const layer of layersData.layers) {
            layersCache[layer.id] = layer;
        }

        let html = `
            <div class="doc-header">
                <h2>${docData.name || 'Untitled'}</h2>
                <div class="meta">${docData.width}x${docData.height} &bull; ${layersData.layers.length} layer(s)</div>
            </div>
            <div class="tabs">
                <div class="tab active" onclick="showTab(this, 'layers-view')">Layers</div>
                <div class="tab" onclick="showTab(this, 'composite-view')">Composite</div>
                <div class="tab" onclick="showTab(this, 'storage-view')">Storage</div>
            </div>
            <div id="layers-view">
                <div class="layer-grid">
        `;

        for (const layer of layersData.layers) {
            const preferredFmt = getPreferredFormat(layer);
            const imgUrl = `${API_BASE}/sessions/${sessionId}/documents/${docId}/layers/${layer.id}/image?format=${preferredFmt}&t=${Date.now()}`;
            const typeClass = layer.type || 'raster';
            const internalFmt = getInternalFormat(layer);
            const dims = `${layer.width || '?'}x${layer.height || '?'}`;

            html += `
                <div class="layer-card" data-layer-id="${layer.id}" data-layer-type="${layer.type}" onclick="selectLayer('${sessionId}', '${docId}', '${layer.id}', this)">
                    <div class="layer-thumb">
                        <img src="${imgUrl}" alt="${layer.name}" loading="lazy" onerror="this.parentElement.innerHTML='<span class=\\'thumb-error\\'>No preview</span>'">
                    </div>
                    <div class="layer-info">
                        <div class="name">${layer.name}<span class="badge ${typeClass}">${typeClass}</span></div>
                        <div class="details">
                            ${dims} &bull; ${internalFmt}
                        </div>
                        <div class="details">
                            ${layer.visible ? '👁' : '👁‍🗨'}
                            ${Math.round((layer.opacity || 1) * 100)}%
                            ${layer.locked ? '🔒' : ''}
                            ${layer.offset_x || layer.offset_y ? `@ ${layer.offset_x},${layer.offset_y}` : ''}
                        </div>
                    </div>
                </div>
            `;
        }

        html += `
                </div>
            </div>
            <div id="composite-view" style="display:none;">
                <div class="preview-panel">
                    <div class="preview-header">
                        <span class="title">Composite Image</span>
                        <div class="actions">
                            <select id="composite-format" onchange="updateComposite('${sessionId}', '${docId}')">
                                <option value="png">PNG</option>
                                <option value="webp">WebP</option>
                                <option value="avif">AVIF</option>
                            </select>
                            <button onclick="downloadImage('composite-img', '${docData.name || 'document'}')">Download</button>
                        </div>
                    </div>
                    <div class="preview-content">
                        <img id="composite-img" src="${API_BASE}/sessions/${sessionId}/documents/${docId}/image?format=png&t=${Date.now()}" alt="Composite">
                    </div>
                </div>
            </div>
            <div id="storage-view" style="display:none;">
                <div class="preview-panel">
                    <div class="preview-header">
                        <span class="title">Browser Storage (OPFS)</span>
                        <button onclick="loadStorage('${sessionId}')">Refresh</button>
                    </div>
                    <div id="storage-content" class="loading" style="padding: 16px;">
                        Click refresh to load storage info
                    </div>
                </div>
            </div>
            <div id="layer-preview" style="margin-top: 24px;"></div>
        `;

        main.innerHTML = html;
    } catch (e) {
        main.innerHTML = `<div class="error">${e.message}</div>`;
    }
}

function showTab(tabEl, viewId) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tabEl.classList.add('active');
    document.querySelectorAll('#layers-view, #composite-view, #storage-view').forEach(v => v.style.display = 'none');
    document.getElementById(viewId).style.display = 'block';
}

function updateComposite(sessionId, docId) {
    const format = document.getElementById('composite-format').value;
    const img = document.getElementById('composite-img');
    img.src = `${API_BASE}/sessions/${sessionId}/documents/${docId}/image?format=${format}&t=${Date.now()}`;
}

async function loadStorage(sessionId) {
    const content = document.getElementById('storage-content');
    content.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const data = await api(`/sessions/${sessionId}/storage/documents`);
        const storage = data.storage || {};

        let html = '<div class="storage-info">';
        html += `<div class="label"><strong>Tab ID:</strong> ${storage.tabId || 'N/A'}</div>`;

        if (storage.documents && storage.documents.length > 0) {
            html += '<div style="margin-bottom: 8px;"><strong>Stored Documents:</strong></div>';
            html += '<table class="storage-table">';
            html += '<tr><th>Name</th><th>Saved At</th><th>History</th></tr>';
            for (const doc of storage.documents) {
                const savedAt = doc.savedAt ? new Date(doc.savedAt).toLocaleString() : 'N/A';
                html += `<tr><td>${doc.name || doc.id?.slice(0, 8)}</td><td>${savedAt}</td><td>${doc.historyIndex ?? 'N/A'}</td></tr>`;
            }
            html += '</table>';
        } else {
            html += '<div style="color: #666;">No documents in storage</div>';
        }

        if (storage.files && storage.files.length > 0) {
            html += '<div style="margin: 16px 0 8px;"><strong>Files:</strong></div>';
            for (const file of storage.files) {
                const size = file.size ? `${(file.size / 1024).toFixed(1)} KB` : 'N/A';
                html += `<div class="file-item">${file.name} (${size})</div>`;
            }
        }

        html += '</div>';
        content.innerHTML = html;
    } catch (e) {
        content.innerHTML = `<div class="error">${e.message}</div>`;
    }
}

function selectLayer(sessionId, docId, layerId, cardEl) {
    const layer = layersCache[layerId] || { type: 'raster' };
    currentLayer = layer;

    document.querySelectorAll('.layer-card').forEach(c => c.classList.remove('active'));
    cardEl.classList.add('active');

    const preferredFmt = getPreferredFormat(layer);
    const internalFmt = getInternalFormat(layer);
    const isVector = layer.type === 'vector';

    // Build format options with preferred format first
    let formatOptions = '';
    if (isVector) {
        formatOptions = `
            <option value="svg" ${preferredFmt === 'svg' ? 'selected' : ''}>SVG</option>
            <option value="json">JSON (shapes)</option>
            <option value="png">PNG (rasterized)</option>
            <option value="webp">WebP (rasterized)</option>
        `;
    } else {
        formatOptions = `
            <option value="png" ${preferredFmt === 'png' ? 'selected' : ''}>PNG</option>
            <option value="webp">WebP</option>
            <option value="avif">AVIF</option>
        `;
    }

    const preview = document.getElementById('layer-preview');
    preview.innerHTML = `
        <div class="preview-panel">
            <div class="preview-header">
                <span class="title">
                    Layer: ${layer.name || 'Unknown'}
                    <span class="badge ${layer.type}">${layer.type}</span>
                    <span style="color: #888; font-weight: normal; font-size: 12px; margin-left: 8px;">${internalFmt}</span>
                </span>
                <div class="actions">
                    <select id="layer-format" onchange="updateLayerPreview('${sessionId}', '${docId}', '${layerId}')">
                        ${formatOptions}
                    </select>
                    <button id="download-btn" onclick="downloadLayerImage('${sessionId}', '${docId}', '${layerId}', '${layer.name || 'layer'}')">Download</button>
                </div>
            </div>
            <div class="preview-content" id="preview-content">
                <div class="loading">Loading...</div>
            </div>
            <div id="layer-json" style="display: none; padding: 16px; background: #111; font-family: monospace; font-size: 12px; white-space: pre-wrap; max-height: 300px; overflow: auto;"></div>
        </div>
    `;

    // Load the preview
    updateLayerPreview(sessionId, docId, layerId);
}

async function updateLayerPreview(sessionId, docId, layerId) {
    const format = document.getElementById('layer-format').value;
    const previewContent = document.getElementById('preview-content');
    const jsonDiv = document.getElementById('layer-json');

    if (format === 'json') {
        previewContent.style.display = 'none';
        jsonDiv.style.display = 'block';
        jsonDiv.innerHTML = '<div class="loading">Loading...</div>';
        try {
            const resp = await fetch(`${API_BASE}/sessions/${sessionId}/documents/${docId}/layers/${layerId}/image?format=json`);
            if (resp.ok) {
                const data = await resp.json();
                jsonDiv.textContent = JSON.stringify(data, null, 2);
            } else {
                jsonDiv.textContent = 'Error: ' + resp.status + ' (JSON format only works for vector layers)';
            }
        } catch (e) {
            jsonDiv.textContent = 'Error: ' + e.message;
        }
    } else {
        jsonDiv.style.display = 'none';
        previewContent.style.display = 'flex';
        previewContent.innerHTML = '<div class="loading">Loading...</div>';

        const img = new Image();
        img.onload = () => {
            previewContent.innerHTML = '';
            previewContent.appendChild(img);
        };
        img.onerror = () => {
            previewContent.innerHTML = `<div class="error">Failed to load ${format.toUpperCase()} (may not be supported for this layer type)</div>`;
        };
        img.id = 'layer-preview-img';
        img.alt = 'Layer preview';
        img.src = `${API_BASE}/sessions/${sessionId}/documents/${docId}/layers/${layerId}/image?format=${format}&t=${Date.now()}`;
    }
}

function downloadLayerImage(sessionId, docId, layerId, layerName) {
    const format = document.getElementById('layer-format').value;
    const ext = getExtension(format);
    const filename = `${layerName}${ext}`;

    const url = `${API_BASE}/sessions/${sessionId}/documents/${docId}/layers/${layerId}/image?format=${format}&t=${Date.now()}`;

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function downloadImage(imgId, filename) {
    const img = document.getElementById(imgId);
    if (!img || !img.src) return;

    const format = document.getElementById('composite-format')?.value || 'png';
    const ext = getExtension(format);

    const a = document.createElement('a');
    a.href = img.src;
    a.download = filename + ext;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function refresh() {
    if (currentDocument && currentSession) {
        selectDocument(currentSession.id, currentDocument.id);
    } else if (currentSession) {
        selectSession(currentSession.id);
    } else {
        loadSessions();
    }
}

// Initial load
loadSessions();
