// stream_view.js - Vue component for high-performance multi-layer video streaming
// Supports multiple image layers with independent FPS, canvas compositing, and SVG overlay

export default {
  template: `
    <div ref="container" class="stream-view-container" :style="containerStyle"
         :class="containerClasses"
         @mousemove="onMouseMove" @click="onMouseClick"
         @wheel.prevent="onWheel"
         @mousedown="onMouseDown"
         @dblclick="onDoubleClick">
      <canvas ref="canvas" :width="width" :height="height" class="stream-view-canvas"></canvas>
      <div ref="svgOverlay" class="stream-view-svg" v-html="svgContent"></div>

      <!-- Navigation window (thumbnail with viewport rect) -->
      <div v-if="showNavWindow && zoom > 1" class="stream-view-nav" :class="navWindowPosition"
           @mousedown.stop="onNavMouseDown" @click.stop>
        <canvas ref="navCanvas" :width="navWindowWidth" :height="navWindowHeight"></canvas>
      </div>

      <!-- Zoom indicator (shows briefly on zoom change) -->
      <div class="zoom-indicator" :class="{ visible: showZoomIndicator }">
        {{ (zoom * 100).toFixed(0) }}%
      </div>

      <!-- Compact Metrics Panel -->
      <div v-if="showMetrics" class="metrics-panel"
           :style="metricsPanelStyle"
           :class="{ minimized: metricsMinimized, paused: metricsPaused }">
        <!-- Always-visible header row with key stats -->
        <div class="metrics-header" @mousedown.stop="startPanelDrag">
          <div class="header-stats">
            <span class="header-stat">
              <span class="stat-val">{{ displayFps.toFixed(0) }}</span>
              <span class="stat-unit">fps</span>
            </span>
            <span class="header-divider">|</span>
            <span class="header-stat">
              <span class="stat-val">{{ formatBandwidth(totalBandwidth) }}</span>
            </span>
            <span class="header-divider">|</span>
            <span class="header-stat">
              <span class="stat-val">{{ Object.keys(visibleLayerLatencies).length + Object.keys(webrtcLayers).length }}</span>
              <span class="stat-unit">layers</span>
            </span>
            <span v-if="zoom > 1" class="header-divider">|</span>
            <span v-if="zoom > 1" class="header-stat">
              <span class="stat-val">{{ zoom.toFixed(1) }}x</span>
            </span>
          </div>
          <div class="header-controls">
            <button class="metrics-btn" @click.stop="exportStats()" title="Export last 30s as JSON">
              ⬇
            </button>
            <button class="metrics-btn" @click.stop="metricsPaused = !metricsPaused"
                    :class="{ active: metricsPaused }" :title="metricsPaused ? 'Resume' : 'Pause'">
              {{ metricsPaused ? '▶' : '⏸' }}
            </button>
            <button class="metrics-btn" @click.stop="metricsMinimized = !metricsMinimized"
                    :title="metricsMinimized ? 'Expand' : 'Collapse'">
              {{ metricsMinimized ? '▼' : '▲' }}
            </button>
          </div>
        </div>

        <!-- Expandable content -->
        <div v-if="!metricsMinimized" class="metrics-body">
          <!-- Unified Graph with mode selector -->
          <div class="graph-container">
            <div class="graph-toolbar">
              <button v-for="mode in ['latency', 'fps', 'bandwidth']" :key="mode"
                      class="graph-mode-btn" :class="{ active: graphMode === mode }"
                      @click.stop="graphMode = mode">
                {{ mode.charAt(0).toUpperCase() + mode.slice(1) }}
              </button>
              <span class="graph-time-label">{{ graphTimeWindow }}s</span>
            </div>
            <canvas ref="unifiedChart" class="unified-chart"></canvas>
            <div class="graph-legend">
              <span v-for="(latency, layerId) in visibleLayerLatencies" :key="layerId" class="legend-item">
                <span class="legend-dot" :style="{ background: getLayerColor(layerId) }"></span>
                <span class="legend-label">{{ latency.label }}</span>
              </span>
            </div>
          </div>

          <!-- Combined layers table -->
          <div class="layers-section">
            <table class="layers-table">
              <thead>
                <tr>
                  <th class="col-name">Layer</th>
                  <th class="col-type">Type</th>
                  <th class="col-fps">FPS</th>
                  <th class="col-latency">Lat</th>
                  <th class="col-bw">Rate</th>
                </tr>
              </thead>
              <tbody>
                <!-- WebSocket layers -->
                <template v-for="(latency, layerId) in visibleLayerLatencies" :key="layerId">
                  <tr class="layer-row" :class="{ expanded: expandedLayers[layerId] }"
                      @click="toggleLayerExpand(layerId)">
                    <td class="col-name">
                      <span class="expand-icon">{{ expandedLayers[layerId] ? '▼' : '▶' }}</span>
                      <span class="layer-dot" :style="{ background: getLayerColor(layerId) }"></span>
                      {{ latency.label }}
                    </td>
                    <td class="col-type">
                      <span class="type-badge" :class="getLayerSourceType(layerId)">{{ getLayerTypeShort(layerId) }}</span>
                    </td>
                    <td class="col-fps" :title="'Target: ' + getLayerTargetFps(layerId)">{{ getLayerFps(layerId) }}</td>
                    <td class="col-latency">{{ latency.total.toFixed(1) }}<span class="unit">ms</span></td>
                    <td class="col-bw">{{ formatBandwidthShort(getLayerRate(layerId)) }}</td>
                  </tr>
                  <tr v-if="expandedLayers[layerId]" class="layer-details-row">
                    <td colspan="5">
                      <div class="latency-breakdown">
                        <div class="breakdown-row">
                          <span class="breakdown-bar">
                            <span class="bar-segment python" :style="{ width: getLatencyPercent(latency, 'python') + '%' }"></span>
                            <span class="bar-segment network" :style="{ width: getLatencyPercent(latency, 'network') + '%' }"></span>
                            <span class="bar-segment js" :style="{ width: getLatencyPercent(latency, 'js') + '%' }"></span>
                          </span>
                        </div>
                        <div class="breakdown-labels">
                          <span class="breakdown-item python">Py: {{ latency.python.toFixed(1) }}ms</span>
                          <span class="breakdown-item network">Net: ~{{ latency.network.toFixed(0) }}ms</span>
                          <span class="breakdown-item js">JS: {{ latency.js.toFixed(1) }}ms</span>
                        </div>
                        <div v-if="latency.filterDetails && latency.filterDetails.length > 0" class="filter-breakdown">
                          <span v-for="(f, idx) in latency.filterDetails" :key="idx" class="filter-item">
                            {{ f.name }}: {{ f.duration.toFixed(1) }}ms
                          </span>
                        </div>
                        <div class="bandwidth-details">
                          Res: {{ getLayerResolution(layerId) }} |
                          Avg: {{ formatBytes(getLayerAvgFrameSize(layerId)) }} |
                          Total: {{ formatBytes(getLayerTotalBytes(layerId)) }} |
                          Buf: {{ getLayerBuffer(layerId) }}
                          <span v-if="getLayerBufferPercent(layerId) > 50" style="color: #FF9800;">⚠</span>
                          <span v-if="getLayerBufferPercent(layerId) > 80" style="color: #F44336;">⛔</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                </template>
                <!-- WebRTC layers -->
                <template v-for="(layer, layerId) in webrtcLayers" :key="'rtc-' + layerId">
                  <tr class="layer-row" :class="{ expanded: expandedLayers[layerId] }"
                      @click="toggleLayerExpand(layerId)">
                    <td class="col-name">
                      <span class="expand-icon">{{ expandedLayers[layerId] ? '▼' : '▶' }}</span>
                      <span class="layer-dot" :style="{ background: getLayerColor(layerId) }"></span>
                      {{ layer.name }}
                    </td>
                    <td class="col-type">
                      <span class="type-badge webrtc">RTC</span>
                    </td>
                    <td class="col-fps" :title="'Decoded: ' + (webrtcStats[layerId]?.framesDecoded || 0)">
                      {{ (webrtcStats[layerId]?.fps || 0).toFixed(1) }}
                    </td>
                    <td class="col-latency" title="WebRTC latency varies">
                      {{ webrtcStats[layerId]?.jitter ? webrtcStats[layerId].jitter.toFixed(0) : '-' }}<span class="unit">ms</span>
                    </td>
                    <td class="col-bw">{{ formatWebRTCBitrateShort(webrtcStats[layerId]?.bitrate || 0) }}</td>
                  </tr>
                  <tr v-if="expandedLayers[layerId]" class="layer-details-row">
                    <td colspan="5">
                      <div class="latency-breakdown webrtc-details">
                        <div class="webrtc-stats">
                          <span class="webrtc-stat">
                            <span class="stat-label">FPS:</span>
                            <span class="stat-value">{{ (webrtcStats[layerId]?.fps || 0).toFixed(1) }}</span>
                          </span>
                          <span class="webrtc-stat">
                            <span class="stat-label">Bitrate:</span>
                            <span class="stat-value">{{ formatWebRTCBitrate(webrtcStats[layerId]?.bitrate || 0) }}</span>
                          </span>
                          <span class="webrtc-stat">
                            <span class="stat-label">Jitter:</span>
                            <span class="stat-value">{{ (webrtcStats[layerId]?.jitter || 0).toFixed(1) }} ms</span>
                          </span>
                          <span class="webrtc-stat">
                            <span class="stat-label">Lost:</span>
                            <span class="stat-value" :class="{ 'warn': webrtcStats[layerId]?.packetsLost > 0 }">
                              {{ webrtcStats[layerId]?.packetsLost || 0 }} pkts
                            </span>
                          </span>
                          <span class="webrtc-stat">
                            <span class="stat-label">Frames:</span>
                            <span class="stat-value">{{ webrtcStats[layerId]?.framesDecoded || 0 }}</span>
                          </span>
                        </div>
                        <div class="webrtc-info">
                          Transport: WebRTC (H.264/VP8) | Z-Index: {{ layer.zIndex }}
                        </div>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Resize handle -->
        <div v-if="!metricsMinimized" class="metrics-resize-handle" @mousedown.stop="startPanelResize"></div>
      </div>
    </div>
  `,

  props: {
    width: { type: Number, default: 1920 },
    height: { type: Number, default: 1080 },
    showMetrics: { type: Boolean, default: false },
    // Zoom/pan configuration
    enableZoom: { type: Boolean, default: false },
    minZoom: { type: Number, default: 1.0 },
    maxZoom: { type: Number, default: 10.0 },
    showNavWindow: { type: Boolean, default: false },
    navWindowPosition: { type: String, default: 'bottom-right' },
    navWindowWidth: { type: Number, default: 160 },
    navWindowHeight: { type: Number, default: 90 },
  },

  data() {
    return {
      // Layer state
      layers: new Map(),  // layer_id -> {config, image, canvas, lastUpdate}
      layerOrder: [],     // Sorted by z_index

      // SVG overlay
      svgContent: '',

      // Metrics
      displayFps: 0,
      frameCount: 0,
      lastFpsUpdate: 0,
      layerMetrics: {},

      // Timing tracking - per layer
      layerTimingHistory: {},    // layerId -> rolling history of timing samples
      maxTimingHistory: 60,      // Keep last N timing samples for averaging/graphs
      layerLatencies: {},        // layerId -> { label, total, python, network, js, color }

      // Clock sync for accurate network latency measurement
      clockOffset: 0,            // Estimated offset between Python and JS clocks (ms)
      clockSyncSamples: [],      // Samples for calculating clock offset

      // === Compact Metrics Overlay ===
      metricsPaused: false,           // Pause metrics display updates
      metricsMinimized: false,        // Collapse to header only

      // Graph mode and settings
      graphMode: 'latency',           // 'latency', 'fps', 'bandwidth'
      graphTimeWindow: 10,            // Time window in seconds

      // Layer colors for consistent visualization
      layerColors: {},                // layerId -> color string

      // Panel position and size (draggable/resizable)
      panelPosition: { x: 10, y: 10 },
      panelSize: { width: 320, height: 340 },
      isPanelDragging: false,
      isPanelResizing: false,
      panelDragStart: { x: 0, y: 0 },
      panelSizeStart: { width: 0, height: 0 },

      // History for graphs (per layer)
      fpsHistory: {},                 // layerId -> [{ time, value }]
      latencyHistory: {},             // layerId -> [{ time, python, network, js }]
      maxHistorySamples: 60,          // For graph display

      // Bandwidth tracking (per layer)
      layerBandwidth: {},             // layerId -> { bytesHistory, currentRate, avgFrameSize, totalBytes }

      // Buffer occupancy tracking (per layer)
      layerBufferInfo: {},            // layerId -> { length, capacity }

      // Frame resolution tracking (per layer)
      layerResolution: {},            // layerId -> { width, height }

      // Expanded state for layers table
      expandedLayers: {},             // layerId -> bool (row expanded in table)

      // Zoom/pan state - viewport in normalized coordinates (0-1)
      // The viewport represents what portion of the source image is visible
      zoom: 1.0,                 // Zoom level (1 = full image, 2 = 2x zoom, etc.)
      viewportX: 0,              // Top-left X of viewport (0-1, normalized)
      viewportY: 0,              // Top-left Y of viewport (0-1, normalized)
      // Drag state
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0,
      dragStartViewportX: 0,
      dragStartViewportY: 0,
      // Nav window drag state
      isNavDragging: false,
      // Zoom indicator
      showZoomIndicator: false,
      zoomIndicatorTimeout: null,
      // Thumbnail for nav window (captured periodically)
      navThumbnail: null,

      // State
      isRunning: false,
      animationFrameId: null,

      // Current dimensions (updated by setSize, defaults to props)
      currentWidth: 0,
      currentHeight: 0,

      // WebRTC layers
      webrtcLayers: {},           // layerId -> { video, pc, zIndex, name }
      webrtcStats: {},            // layerId -> { bitrate, packetsLost, jitter }
    };
  },

  created() {
    // Initialize current dimensions from props
    this.currentWidth = this.width;
    this.currentHeight = this.height;
  },

  computed: {
    containerStyle() {
      const w = this.currentWidth || this.width;
      const h = this.currentHeight || this.height;
      return {
        width: `${w}px`,
        height: `${h}px`,
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: '#000',
      };
    },

    containerClasses() {
      return {
        'zoomable': this.enableZoom,
        'zoomed': this.zoom > 1,
        'dragging': this.isDragging,
      };
    },

    // Current viewport as normalized rectangle (0-1 range)
    // This is sent to Python for server-side cropping
    viewport() {
      const size = 1 / this.zoom;
      return {
        x: this.viewportX,
        y: this.viewportY,
        width: size,
        height: size,
        zoom: this.zoom,
      };
    },

    // Style for the draggable/resizable metrics panel
    metricsPanelStyle() {
      return {
        left: `${this.panelPosition.x}px`,
        top: `${this.panelPosition.y}px`,
        width: `${this.panelSize.width}px`,
        height: this.metricsMinimized ? 'auto' : `${this.panelSize.height}px`,
      };
    },

    // Total bandwidth across visible layers (bytes per second)
    totalBandwidth() {
      let total = 0;
      for (const layerId of Object.keys(this.layerBandwidth)) {
        const layer = this.layers.get(layerId);
        if (!layer) continue;
        // Skip off-screen layers
        const x = layer.config.x ?? 0;
        const y = layer.config.y ?? 0;
        if (x < 0 || y < 0) continue;
        total += this.layerBandwidth[layerId]?.currentRate || 0;
      }
      return total;
    },

    // Total bytes transferred across visible layers
    totalBytesTransferred() {
      let total = 0;
      for (const layerId of Object.keys(this.layerBandwidth)) {
        const layer = this.layers.get(layerId);
        if (!layer) continue;
        // Skip off-screen layers
        const x = layer.config.x ?? 0;
        const y = layer.config.y ?? 0;
        if (x < 0 || y < 0) continue;
        total += this.layerBandwidth[layerId]?.totalBytes || 0;
      }
      return total;
    },

    // Filter layerLatencies to only show visible layers (not off-screen)
    visibleLayerLatencies() {
      const result = {};
      for (const [layerId, latency] of Object.entries(this.layerLatencies)) {
        const layer = this.layers.get(layerId);
        if (!layer) continue;
        // Exclude layers at negative positions (off-screen/hidden)
        const x = layer.config.x ?? 0;
        const y = layer.config.y ?? 0;
        if (x < 0 || y < 0) continue;
        result[layerId] = latency;
      }
      return result;
    },
  },

  mounted() {
    this.ctx = this.$refs.canvas.getContext('2d');
    this.lastFpsUpdate = performance.now();

    // Start rendering loop
    this.startRenderLoop();

    // Start chart update timer (5 Hz)
    this.chartUpdateInterval = setInterval(() => {
      this.drawAllCharts();
    }, 200);

    // Signal to Python that we're ready for WebRTC connections
    // Use setTimeout to ensure WebSocket is fully connected
    setTimeout(() => {
      console.log('[StreamView JS] Component mounted, emitting component-ready');
      this.$emit('component-ready', {});
    }, 500);
  },

  unmounted() {
    this.stop();
    if (this.chartUpdateInterval) {
      clearInterval(this.chartUpdateInterval);
    }
  },

  methods: {
    // === Layer Management ===

    addLayer(config) {
      // Use name from config (server provides default if empty)
      const label = config.name || `Layer ${config.z_index}`;

      const layer = {
        config: { ...config, label },
        image: new Image(),
        lastUpdate: 0,
        lastRequest: 0,
        frameInterval: 1000 / config.target_fps,
        fps: 0,
        frameTimes: [],  // Sliding window of frame timestamps for smooth FPS
        isLoading: false,
        hasContent: false,
        // Overscan support: anchor position tracks where the content is centered
        // Display position (x, y) can move independently; offset compensates
        anchorX: config.x ?? 0,
        anchorY: config.y ?? 0,
      };

      // Initialize timing history for this layer
      this.layerTimingHistory[config.id] = [];

      // Initialize bandwidth tracking for this layer
      this.layerBandwidth[config.id] = {
        bytesHistory: [],       // Rolling history of frame sizes
        currentRate: 0,         // Bytes per second
        avgFrameSize: 0,        // Average frame size in bytes
        totalBytes: 0,          // Total bytes transferred
        lastRateCalc: performance.now(),
      };

      // Initialize FPS/latency history for graphs
      this.fpsHistory[config.id] = [];
      this.latencyHistory[config.id] = [];

      // Set up image load handler
      layer.image.onload = () => {
        const decodeEndTime = performance.now();
        layer.isLoading = false;
        layer.hasContent = true;
        layer.lastUpdate = decodeEndTime;
        layer.frameCount++;

        // Process timing metadata if present
        if (layer.pendingMetadata) {
          const meta = layer.pendingMetadata;
          meta.js_decode_end = decodeEndTime;
          meta.js_decode_ms = decodeEndTime - meta.js_decode_start;

          // Calculate network time (approximate - based on Python send_time)
          // This requires clock synchronization which is imperfect
          // For now, estimate based on receive - send (will be offset by clock diff)
          if (meta.send_time && meta.js_receive_time) {
            // Note: This is approximate since Python and JS clocks differ
            // A proper implementation would use clock sync protocol
            meta.network_ms = Math.max(0, 5); // Placeholder - we'll refine this
          }

          // Store for render timing (will be set in render loop)
          layer.lastMetadata = meta;
          layer.pendingMetadata = null;
        }

        // Calculate layer FPS using sliding window
        const now = performance.now();
        this.updateLayerFps(layer, now);
        this.layerMetrics[config.id] = { fps: layer.fps };

        // Request next frame immediately for streaming layers
        if (!config.is_static && this.isRunning) {
          this.requestLayerFrame(config.id);
        }
      };

      // Handle static content
      if (config.is_static && config.static_content) {
        if (config.static_content.startsWith('data:') || config.static_content.startsWith('http')) {
          layer.image.src = config.static_content;
        }
      }

      this.layers.set(config.id, layer);
      this.updateLayerOrder();
    },

    removeLayer(layerId) {
      const layer = this.layers.get(layerId);
      if (layer) {
        // Clean up ImageBitmap if present
        if (layer.imageBitmap) {
          layer.imageBitmap.close();
        }
      }
      this.layers.delete(layerId);
      delete this.layerMetrics[layerId];
      this.updateLayerOrder();
    },

    updateLayerOrder() {
      this.layerOrder = Array.from(this.layers.keys()).sort((a, b) => {
        const layerA = this.layers.get(a);
        const layerB = this.layers.get(b);
        return layerA.config.z_index - layerB.config.z_index;
      });
    },

    updateLayerPosition(layerId, x, y, width, height) {
      const layer = this.layers.get(layerId);
      if (!layer) return;
      // Update position/size in config
      if (x !== null && x !== undefined) layer.config.x = x;
      if (y !== null && y !== undefined) layer.config.y = y;
      if (width !== null && width !== undefined) layer.config.width = width;
      if (height !== null && height !== undefined) layer.config.height = height;
    },

    setLayerMask(layerId, maskData) {
      // Store mask image for client-side alpha compositing
      // Mask is a grayscale PNG where white=opaque, black=transparent
      const layer = this.layers.get(layerId);
      if (!layer) return;

      // Create mask image
      const maskImg = new Image();
      maskImg.onload = () => {
        // Create a canvas to hold the mask for compositing
        const maskCanvas = document.createElement('canvas');
        maskCanvas.width = maskImg.width;
        maskCanvas.height = maskImg.height;
        const maskCtx = maskCanvas.getContext('2d');

        // Draw the grayscale image first
        maskCtx.drawImage(maskImg, 0, 0);

        // Convert grayscale to alpha channel
        // The grayscale values become alpha (white=opaque, black=transparent)
        const imageData = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
          // Use the red channel (grayscale) as alpha
          // Set RGB to white so only alpha matters for compositing
          const alpha = data[i];  // R channel (grayscale value)
          data[i] = 255;     // R = white
          data[i + 1] = 255; // G = white
          data[i + 2] = 255; // B = white
          data[i + 3] = alpha; // A = grayscale value
        }
        maskCtx.putImageData(imageData, 0, 0);

        // Store the mask canvas on the layer
        layer.maskCanvas = maskCanvas;
        console.log(`[StreamView] Mask set for layer ${layerId}: ${maskImg.width}x${maskImg.height}`);
      };
      maskImg.src = maskData;
    },

    drawWithMask(imgSource, maskCanvas, x, y, w, h) {
      // Draw an image with an alpha mask using off-screen compositing
      // maskCanvas contains grayscale values where white=opaque, black=transparent

      // Get or create temp canvas for compositing (reuse for performance)
      if (!this.tempMaskCanvas) {
        this.tempMaskCanvas = document.createElement('canvas');
        this.tempMaskCtx = this.tempMaskCanvas.getContext('2d');
      }

      // Resize temp canvas if needed
      if (this.tempMaskCanvas.width !== w || this.tempMaskCanvas.height !== h) {
        this.tempMaskCanvas.width = w;
        this.tempMaskCanvas.height = h;
      }

      // Clear temp canvas
      this.tempMaskCtx.clearRect(0, 0, w, h);

      // Draw the image content first
      this.tempMaskCtx.drawImage(imgSource, 0, 0, w, h);

      // Apply the mask using destination-in compositing
      // This keeps only the parts of the image where the mask is opaque
      this.tempMaskCtx.globalCompositeOperation = 'destination-in';
      this.tempMaskCtx.drawImage(maskCanvas, 0, 0, w, h);
      this.tempMaskCtx.globalCompositeOperation = 'source-over';

      // Draw the masked result to the main canvas
      this.ctx.drawImage(this.tempMaskCanvas, x, y);
    },

    updateLayerFps(layer, now) {
      // Sliding window FPS calculation for smooth display
      // Window size: 1 second for responsiveness
      const FPS_WINDOW_MS = 1000;

      // Add current frame timestamp
      layer.frameTimes.push(now);

      // Remove timestamps outside the window
      const cutoff = now - FPS_WINDOW_MS;
      while (layer.frameTimes.length > 0 && layer.frameTimes[0] < cutoff) {
        layer.frameTimes.shift();
      }

      // Calculate FPS: frames in window / window duration
      // Use actual window span (not fixed 1s) for accuracy during ramp-up
      if (layer.frameTimes.length >= 2) {
        const windowStart = layer.frameTimes[0];
        const windowEnd = layer.frameTimes[layer.frameTimes.length - 1];
        const windowDuration = (windowEnd - windowStart) / 1000; // seconds

        if (windowDuration >= 0.1) {
          // Need at least 100ms of data for meaningful FPS
          // frames-1 because we're counting intervals, not points
          layer.fps = (layer.frameTimes.length - 1) / windowDuration;
        }
      }
      // Keep previous fps value if not enough data (avoids jumping to 0)
    },

    // === Frame Updates ===

    updateLayer(layerId, imageData, metadata = null) {
      const layer = this.layers.get(layerId);
      if (!layer) return;

      // Track receive time (when JS received the frame)
      const receiveTime = performance.now();

      // Store metadata with JS timing additions
      if (metadata) {
        metadata.js_receive_time = receiveTime;
        metadata.js_decode_start = receiveTime;  // Will update in onload

        // Store nav thumbnail if present (for nav window when zoomed)
        if (metadata.nav_thumbnail) {
          const newThumbUrl = `data:image/jpeg;base64,${metadata.nav_thumbnail}`;
          // Update thumbnail image if it changed
          if (layer.navThumbnail !== newThumbUrl) {
            layer.navThumbnail = newThumbUrl;
            // Create or update the image element
            if (!layer.navThumbnailImage) {
              layer.navThumbnailImage = new Image();
            }
            layer.navThumbnailImage.src = newThumbUrl;
          }
        }

        // Update anchor position for overscan layers
        // When new frame arrives, anchor syncs to current display position
        if (metadata.anchor_x !== undefined && metadata.anchor_y !== undefined) {
          layer.anchorX = metadata.anchor_x;
          layer.anchorY = metadata.anchor_y;
        }

        // Track bandwidth from frame_bytes
        if (metadata.frame_bytes && this.layerBandwidth[layerId]) {
          this.trackBandwidth(layerId, metadata.frame_bytes);
        }

        // Track buffer occupancy
        if (metadata.buffer_capacity > 0) {
          this.layerBufferInfo[layerId] = {
            length: metadata.buffer_length,
            capacity: metadata.buffer_capacity,
          };
        }

        // Track frame resolution
        if (metadata.frame_width > 0 && metadata.frame_height > 0) {
          this.layerResolution[layerId] = {
            width: metadata.frame_width,
            height: metadata.frame_height,
          };
        }

        layer.pendingMetadata = metadata;
      }

      // Update image source using createImageBitmap (no Network tab spam)
      layer.isLoading = true;

      // Store reference to old bitmap (close after new one is ready)
      const oldBitmap = layer.imageBitmap;

      // Convert data URL to Blob
      let dataUrl = imageData;
      if (!imageData.startsWith('data:')) {
        dataUrl = `data:image/jpeg;base64,${imageData}`;
      }

      // Parse data URL and create blob
      const [header, base64] = dataUrl.split(',');
      const mimeMatch = header.match(/data:([^;]+)/);
      const mimeType = mimeMatch ? mimeMatch[1] : 'image/jpeg';
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: mimeType });

      // Use createImageBitmap - decodes off main thread, no Network tab entry
      createImageBitmap(blob).then(bitmap => {
        // Swap in new bitmap, then close old one
        layer.imageBitmap = bitmap;
        if (oldBitmap) {
          oldBitmap.close();
        }

        layer.isLoading = false;
        layer.hasContent = true;
        layer.lastUpdate = performance.now();

        // Process metadata timing
        if (layer.pendingMetadata) {
          layer.pendingMetadata.js_decode_end = performance.now();
          layer.lastMetadata = layer.pendingMetadata;
          layer.pendingMetadata = null;
        }

        // Track FPS using sliding window
        const now = performance.now();
        this.updateLayerFps(layer, now);
      }).catch(err => {
        console.warn('Failed to decode image:', err);
        layer.isLoading = false;
      });
    },

    requestLayerFrame(layerId) {
      const layer = this.layers.get(layerId);
      if (!layer || layer.config.is_static) return;

      const now = performance.now();

      // Rate limit requests based on target FPS
      if (now - layer.lastRequest < layer.frameInterval * 0.5) {
        return;  // Too soon since last request
      }

      layer.lastRequest = now;
      this.$emit('frame-request', { layer_id: layerId });
    },

    // === Rendering ===

    startRenderLoop() {
      this.isRunning = true;
      this.render();
    },

    render() {
      if (!this.isRunning) return;

      const now = performance.now();
      const renderStart = now;

      // Clear canvas
      const canvasW = this.currentWidth || this.width;
      const canvasH = this.currentHeight || this.height;
      // If there are WebRTC layers, make canvas transparent so video shows through
      // Otherwise, fill with black background
      if (Object.keys(this.webrtcLayers).length > 0) {
        this.ctx.clearRect(0, 0, canvasW, canvasH);
      } else {
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, canvasW, canvasH);
      }

      // Draw layers in z-order
      for (const layerId of this.layerOrder) {
        const layer = this.layers.get(layerId);
        if (!layer || !layer.hasContent) continue;

        try {
          // Get position/size from config (null = fill canvas)
          const cfg = layer.config;
          const x = cfg.x ?? 0;
          const y = cfg.y ?? 0;
          const w = cfg.width ?? canvasW;
          const h = cfg.height ?? canvasH;
          const overscan = cfg.overscan ?? 0;

          // Use ImageBitmap if available, fall back to Image element
          const imgSource = layer.imageBitmap || layer.image;

          if (overscan > 0 && cfg.width && cfg.height) {
            // Overscan layer: image is larger, use clipping to show center portion
            // Calculate offset between current display position and anchor position
            const offsetX = x - layer.anchorX;
            const offsetY = y - layer.anchorY;

            // Clamp offset to overscan bounds (can't show beyond what we have)
            const clampedOffsetX = Math.max(-overscan, Math.min(overscan, offsetX));
            const clampedOffsetY = Math.max(-overscan, Math.min(overscan, offsetY));

            // Image is rendered larger (width + 2*overscan, height + 2*overscan)
            // Draw position is adjusted by overscan and offset
            const imgW = w + 2 * overscan;
            const imgH = h + 2 * overscan;
            const drawX = x - overscan - clampedOffsetX;
            const drawY = y - overscan - clampedOffsetY;

            // Use clipping to show only the display area
            this.ctx.save();
            this.ctx.beginPath();
            this.ctx.rect(x, y, w, h);
            this.ctx.clip();

            // Apply mask if layer has one
            if (layer.maskCanvas) {
              this.drawWithMask(imgSource, layer.maskCanvas, drawX, drawY, imgW, imgH);
            } else {
              this.ctx.drawImage(imgSource, drawX, drawY, imgW, imgH);
            }
            this.ctx.restore();
          } else {
            // Standard layer: draw image at specified position/size
            // Note: Server-side cropping handles viewport for content layers,
            // so we always draw the full received image here
            if (layer.maskCanvas) {
              this.drawWithMask(imgSource, layer.maskCanvas, x, y, w, h);
            } else {
              this.ctx.drawImage(imgSource, x, y, w, h);
            }
          }

          // Track render timing for this layer
          if (layer.lastMetadata && !layer.lastMetadata.js_render_time) {
            const renderEnd = performance.now();
            layer.lastMetadata.js_render_time = renderEnd;
            layer.lastMetadata.js_render_ms = renderEnd - renderStart;

            // Update per-layer timing display
            this.updateLayerTiming(layerId, layer.lastMetadata);

            // Clear metadata after processing to avoid double-counting
            layer.lastMetadata = null;
          }
        } catch (e) {
          // Image not ready yet
        }
      }

      // Request frames for streaming layers that need updates
      for (const [layerId, layer] of this.layers) {
        if (layer.config.is_static) continue;

        const timeSinceUpdate = now - layer.lastUpdate;
        if (timeSinceUpdate >= layer.frameInterval && !layer.isLoading) {
          this.requestLayerFrame(layerId);
        }
      }

      // Update FPS counter
      this.frameCount++;
      const elapsed = now - this.lastFpsUpdate;
      if (elapsed >= 1000) {
        this.displayFps = (this.frameCount * 1000) / elapsed;
        this.frameCount = 0;
        this.lastFpsUpdate = now;
      }

      // Update navigation window if visible
      this.updateNavWindow();

      // Schedule next frame
      this.animationFrameId = requestAnimationFrame(() => this.render());
    },

    // === SVG Overlay ===

    updateSvg(content) {
      this.svgContent = content;
    },

    // === Mouse Events ===

    onMouseMove(e) {
      // Handle drag for panning
      if (this.isDragging && this.enableZoom && this.zoom > 1) {
        const rect = this.$refs.container.getBoundingClientRect();
        const dx = (e.clientX - this.dragStartX) / rect.width;
        const dy = (e.clientY - this.dragStartY) / rect.height;

        // Move viewport opposite to drag direction (drag right = view moves left)
        this.viewportX = this.dragStartViewportX - dx / this.zoom;
        this.viewportY = this.dragStartViewportY - dy / this.zoom;
        this.clampViewport();
        return;  // Don't emit mouse-move while dragging
      }

      const rect = this.$refs.canvas.getBoundingClientRect();
      const w = this.currentWidth || this.width;
      const h = this.currentHeight || this.height;
      const scaleX = w / rect.width;
      const scaleY = h / rect.height;

      // Screen position
      const screenX = (e.clientX - rect.left) * scaleX;
      const screenY = (e.clientY - rect.top) * scaleY;

      // Convert to source image coordinates (accounting for zoom/pan)
      const sourceX = this.viewportX * w + screenX / this.zoom;
      const sourceY = this.viewportY * h + screenY / this.zoom;

      this.$emit('mouse-move', {
        x: screenX,
        y: screenY,
        sourceX: sourceX,  // Coordinates in original image
        sourceY: sourceY,
        viewport: this.viewport,
        buttons: e.buttons,
        alt: e.altKey,
        ctrl: e.ctrlKey,
        shift: e.shiftKey,
        meta: e.metaKey,
      });
    },

    onMouseClick(e) {
      const rect = this.$refs.canvas.getBoundingClientRect();
      const w = this.currentWidth || this.width;
      const h = this.currentHeight || this.height;
      const scaleX = w / rect.width;
      const scaleY = h / rect.height;

      const screenX = (e.clientX - rect.left) * scaleX;
      const screenY = (e.clientY - rect.top) * scaleY;

      // Convert to source image coordinates
      const sourceX = this.viewportX * w + screenX / this.zoom;
      const sourceY = this.viewportY * h + screenY / this.zoom;

      this.$emit('mouse-click', {
        x: screenX,
        y: screenY,
        sourceX: sourceX,
        sourceY: sourceY,
        viewport: this.viewport,
        buttons: e.buttons,
        alt: e.altKey,
        ctrl: e.ctrlKey,
        shift: e.shiftKey,
        meta: e.metaKey,
      });
    },

    // === Zoom/Pan Methods ===

    onWheel(e) {
      if (!this.enableZoom) return;

      const rect = this.$refs.container.getBoundingClientRect();
      // Mouse position in normalized coordinates (0-1)
      const mouseNormX = (e.clientX - rect.left) / rect.width;
      const mouseNormY = (e.clientY - rect.top) / rect.height;

      // Calculate zoom change
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const newZoom = Math.max(this.minZoom, Math.min(this.maxZoom, this.zoom * zoomFactor));

      if (newZoom !== this.zoom) {
        // Calculate the point in source coordinates under the mouse
        const viewportSize = 1 / this.zoom;
        const sourceX = this.viewportX + mouseNormX * viewportSize;
        const sourceY = this.viewportY + mouseNormY * viewportSize;

        // Update zoom
        const oldZoom = this.zoom;
        this.zoom = newZoom;

        // Adjust viewport so the same source point stays under the mouse
        const newViewportSize = 1 / this.zoom;
        this.viewportX = sourceX - mouseNormX * newViewportSize;
        this.viewportY = sourceY - mouseNormY * newViewportSize;

        this.clampViewport();
        this.flashZoomIndicator();
        this.emitViewportChange();
        this.updateWebRTCTransform();
      }
    },

    onMouseDown(e) {
      if (!this.enableZoom || this.zoom <= 1) return;
      if (e.button !== 0) return;  // Left click only

      this.isDragging = true;
      this.dragStartX = e.clientX;
      this.dragStartY = e.clientY;
      this.dragStartViewportX = this.viewportX;
      this.dragStartViewportY = this.viewportY;

      // Add global listeners for drag
      document.addEventListener('mousemove', this.onGlobalMouseMove);
      document.addEventListener('mouseup', this.onGlobalMouseUp);
    },

    onGlobalMouseMove(e) {
      if (!this.isDragging) return;

      const rect = this.$refs.container.getBoundingClientRect();
      const dx = (e.clientX - this.dragStartX) / rect.width;
      const dy = (e.clientY - this.dragStartY) / rect.height;

      // Move viewport opposite to drag direction
      this.viewportX = this.dragStartViewportX - dx / this.zoom;
      this.viewportY = this.dragStartViewportY - dy / this.zoom;
      this.clampViewport();
      this.emitViewportChange();  // Update main view during drag
      this.updateWebRTCTransform();
    },

    onGlobalMouseUp() {
      if (this.isDragging) {
        this.isDragging = false;
        this.emitViewportChange();
        this.updateWebRTCTransform();
      }
      document.removeEventListener('mousemove', this.onGlobalMouseMove);
      document.removeEventListener('mouseup', this.onGlobalMouseUp);
    },

    onDoubleClick() {
      if (!this.enableZoom) return;

      // Reset zoom to 1x
      this.zoom = 1.0;
      this.viewportX = 0;
      this.viewportY = 0;
      this.flashZoomIndicator();
      this.emitViewportChange();
      this.updateWebRTCTransform();
    },

    onNavMouseDown(e) {
      if (!this.$refs.navCanvas) return;

      this.isNavDragging = true;
      this.handleNavClick(e);

      document.addEventListener('mousemove', this.onNavMouseMove);
      document.addEventListener('mouseup', this.onNavMouseUp);
    },

    onNavMouseMove(e) {
      if (!this.isNavDragging) return;
      this.handleNavClick(e);
      this.emitViewportChange();  // Update main view during drag
    },

    onNavMouseUp() {
      this.isNavDragging = false;
      this.emitViewportChange();
      document.removeEventListener('mousemove', this.onNavMouseMove);
      document.removeEventListener('mouseup', this.onNavMouseUp);
    },

    handleNavClick(e) {
      const rect = this.$refs.navCanvas.getBoundingClientRect();
      const clickX = (e.clientX - rect.left) / rect.width;
      const clickY = (e.clientY - rect.top) / rect.height;

      // Center viewport on clicked point
      const viewportSize = 1 / this.zoom;
      this.viewportX = clickX - viewportSize / 2;
      this.viewportY = clickY - viewportSize / 2;
      this.clampViewport();
    },

    clampViewport() {
      const viewportSize = 1 / this.zoom;
      // Clamp viewport to stay within 0-1 bounds
      this.viewportX = Math.max(0, Math.min(1 - viewportSize, this.viewportX));
      this.viewportY = Math.max(0, Math.min(1 - viewportSize, this.viewportY));
    },

    emitViewportChange() {
      this.$emit('viewport-change', this.viewport);
    },

    flashZoomIndicator() {
      this.showZoomIndicator = true;
      if (this.zoomIndicatorTimeout) {
        clearTimeout(this.zoomIndicatorTimeout);
      }
      this.zoomIndicatorTimeout = setTimeout(() => {
        this.showZoomIndicator = false;
      }, 1000);
    },

    updateNavWindow() {
      if (!this.showNavWindow || this.zoom <= 1 || !this.$refs.navCanvas) return;

      const navCtx = this.$refs.navCanvas.getContext('2d');

      // Draw full-frame thumbnail for nav window
      // When zoomed, Python sends a nav_thumbnail with the full (uncropped) frame
      navCtx.fillStyle = '#000';
      navCtx.fillRect(0, 0, this.navWindowWidth, this.navWindowHeight);

      try {
        // First try WebRTC layers (they contain the full uncropped video)
        for (const [layerId, layer] of Object.entries(this.webrtcLayers)) {
          if (layer.video && layer.video.readyState >= 2) {
            // WebRTC video is available, capture a frame for nav window
            // Note: WebRTC server-side cropping means video shows cropped content,
            // but we can still use it for nav (better than black)
            navCtx.drawImage(
              layer.video,
              0, 0, this.navWindowWidth, this.navWindowHeight
            );
            break;  // Use first WebRTC layer found
          }
        }

        // If no WebRTC layer, try WebSocket layers
        if (Object.keys(this.webrtcLayers).length === 0) {
          for (const layerId of this.layerOrder) {
            const layer = this.layers.get(layerId);
            if (!layer || !layer.hasContent) continue;

            const depth = layer.config.depth ?? 1.0;
            if (depth > 0) {
              // Use nav thumbnail if available (full frame when zoomed)
              if (layer.navThumbnailImage && layer.navThumbnailImage.complete) {
                navCtx.drawImage(
                  layer.navThumbnailImage,
                  0, 0, this.navWindowWidth, this.navWindowHeight
                );
              } else {
                // No thumbnail yet or not loaded, use main image
                navCtx.drawImage(
                  layer.image,
                  0, 0, this.navWindowWidth, this.navWindowHeight
                );
              }
              break;  // Only use first content layer
            }
          }
        }
      } catch (e) {
        // Image/video might not be ready
        return;
      }

      // Draw viewport rectangle
      const vpX = this.viewportX * this.navWindowWidth;
      const vpY = this.viewportY * this.navWindowHeight;
      const vpW = (1 / this.zoom) * this.navWindowWidth;
      const vpH = (1 / this.zoom) * this.navWindowHeight;

      navCtx.strokeStyle = 'rgba(255, 0, 0, 0.9)';
      navCtx.lineWidth = 2;
      navCtx.strokeRect(vpX, vpY, vpW, vpH);

      // Semi-transparent fill
      navCtx.fillStyle = 'rgba(255, 0, 0, 0.1)';
      navCtx.fillRect(vpX, vpY, vpW, vpH);
    },

    // Programmatic zoom control (called from Python)
    setZoom(zoom, centerX = null, centerY = null) {
      const newZoom = Math.max(this.minZoom, Math.min(this.maxZoom, zoom));

      if (centerX !== null && centerY !== null) {
        // Zoom centered on specific point (normalized 0-1)
        const viewportSize = 1 / newZoom;
        this.viewportX = centerX - viewportSize / 2;
        this.viewportY = centerY - viewportSize / 2;
      }

      this.zoom = newZoom;
      this.clampViewport();
      this.flashZoomIndicator();
      this.emitViewportChange();
      this.updateWebRTCTransform();
    },

    resetZoom() {
      this.zoom = 1.0;
      this.viewportX = 0;
      this.viewportY = 0;
      this.flashZoomIndicator();
      this.emitViewportChange();
      this.updateWebRTCTransform();
    },

    // === Control Methods ===

    start() {
      if (!this.isRunning) {
        this.startRenderLoop();
      }

      // Request initial frames for all streaming layers
      for (const [layerId, layer] of this.layers) {
        if (!layer.config.is_static) {
          this.requestLayerFrame(layerId);
        }
      }
    },

    stop() {
      this.isRunning = false;
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId);
        this.animationFrameId = null;
      }
    },

    // === Timing Visualization ===

    updateLayerTiming(layerId, metadata) {
      const layer = this.layers.get(layerId);
      if (!layer) return;

      // Initialize history if needed
      if (!this.layerTimingHistory[layerId]) {
        this.layerTimingHistory[layerId] = [];
      }

      // Add to layer's history
      const history = this.layerTimingHistory[layerId];
      history.push(metadata);
      if (history.length > this.maxTimingHistory) {
        history.shift();
      }

      // Calculate averaged latency for this layer
      const avg = this.calculateLayerLatency(layerId, history, layer.config.label);

      // Update clock offset estimate (using this sample)
      this.updateClockOffset(metadata);

      // Store in layerLatencies for display (all layers now)
      if (!this.metricsPaused) {
        this.layerLatencies = { ...this.layerLatencies, [layerId]: avg };

        // Update latency history for graphs
        if (this.latencyHistory[layerId]) {
          this.latencyHistory[layerId].push({
            time: performance.now(),
            python: avg.python,
            network: avg.network,
            js: avg.js,
            total: avg.total,
          });
          if (this.latencyHistory[layerId].length > this.maxHistorySamples) {
            this.latencyHistory[layerId].shift();
          }
        }

        // Update FPS history for graphs
        if (this.fpsHistory[layerId]) {
          this.fpsHistory[layerId].push({
            time: performance.now(),
            value: layer.fps,
          });
          if (this.fpsHistory[layerId].length > this.maxHistorySamples) {
            this.fpsHistory[layerId].shift();
          }
        }
      }
    },

    updateClockOffset(metadata) {
      // Estimate clock offset using round-trip assumption
      // Python send_time and JS receive_time should be close if clocks were synced
      // We use the minimum observed (send_time - receive_time) as our offset estimate
      if (metadata.send_time && metadata.js_receive_time) {
        // Convert Python ms timestamp to approximate offset
        // Note: This is imperfect since Python uses perf_counter (relative) not absolute time
        // For now we just track the JS-side processing time accurately
        const sample = {
          pythonSend: metadata.send_time,
          jsReceive: metadata.js_receive_time,
        };
        this.clockSyncSamples.push(sample);
        if (this.clockSyncSamples.length > 10) {
          this.clockSyncSamples.shift();
        }
      }
    },

    calculateLayerLatency(layerId, history, label) {
      if (history.length === 0) {
        return { label, total: 0, python: 0, network: 0, js: 0, color: '#888', filterDetails: [] };
      }

      const count = history.length;

      // Calculate average python processing time (capture to send)
      const avgPython = history.reduce((s, t) => s + (t.python_processing_ms || 0), 0) / count;

      // Calculate average JS processing time (receive to render)
      const avgJsDecode = history.reduce((s, t) => s + (t.js_decode_ms || 0), 0) / count;
      const avgJsRender = history.reduce((s, t) => s + (t.js_render_ms || 0), 0) / count;
      const avgJs = avgJsDecode + avgJsRender;

      // Estimate network latency
      // Since we can't sync clocks perfectly, estimate based on total - (python + js)
      // Or use a fixed estimate based on WebSocket typical latency
      let avgNetwork = 5; // Default estimate

      // If we have encode time, we can be more precise about python time
      const avgEncode = history.reduce((s, t) => s + (t.encode_duration_ms || 0), 0) / count;
      const avgFilters = history.reduce((s, t) => s + (t.total_filter_ms || 0), 0) / count;

      // Aggregate individual filter timings by name
      const filterMap = new Map();
      history.forEach(t => {
        if (t.filter_timings && t.filter_timings.length > 0) {
          t.filter_timings.forEach(f => {
            if (!filterMap.has(f.name)) {
              filterMap.set(f.name, { name: f.name, total: 0, count: 0 });
            }
            const entry = filterMap.get(f.name);
            entry.total += f.duration_ms;
            entry.count++;
          });
        }
      });

      // Calculate averaged filter details
      const filterDetails = Array.from(filterMap.values()).map(f => ({
        name: f.name,
        duration: f.total / f.count,
      }));

      // Total birth-to-display = python processing + network + js processing
      const total = avgPython + avgNetwork + avgJs;

      // Color based on label
      const color = label === 'Video' ? '#4CAF50' : label === 'Thermal' ? '#FF5722' : '#2196F3';

      return {
        label,
        total,
        python: avgPython,
        network: avgNetwork,
        js: avgJs,
        color,
        // Detailed breakdown
        encode: avgEncode,
        filters: avgFilters,
        decode: avgJsDecode,
        render: avgJsRender,
        filterDetails,  // Array of {name, duration} for each step
      };
    },

    // === Metrics ===

    getMetrics() {
      const layerStats = {};
      for (const [layerId, layer] of this.layers) {
        layerStats[layerId] = {
          fps: layer.fps,
          hasContent: layer.hasContent,
          isLoading: layer.isLoading,
          timeSinceUpdate: performance.now() - layer.lastUpdate,
        };
      }

      return {
        displayFps: this.displayFps,
        isRunning: this.isRunning,
        layerCount: this.layers.size,
        layers: layerStats,
      };
    },

    setRunning(running) {
      if (running) {
        this.start();
      } else {
        this.stop();
      }
    },

    // Resize the display canvas
    setSize(width, height) {
      // Update canvas dimensions
      const canvas = this.$refs.canvas;
      if (canvas) {
        canvas.width = width;
        canvas.height = height;
      }

      // Update container style directly
      this.$refs.container.style.width = `${width}px`;
      this.$refs.container.style.height = `${height}px`;

      // Store current dimensions for mouse coordinate calculations
      this.currentWidth = width;
      this.currentHeight = height;

      // Update WebRTC layer transforms for new size
      this.updateWebRTCTransform();
    },

    // === WebRTC Layer Methods ===

    async setupWebRTCLayer(layerId, offer, zIndex, name) {
      console.log('[WebRTC JS] setupWebRTCLayer called:', layerId, zIndex, name);
      console.log('[WebRTC JS] offer type:', offer?.type, 'sdp length:', offer?.sdp?.length);

      // Send immediate acknowledgment that we received the call
      this.$emit('webrtc-debug', { message: 'setupWebRTCLayer called', layerId, zIndex });

      try {
        // Create peer connection
        const pc = new RTCPeerConnection();
        console.log('[WebRTC JS] PeerConnection created');

        // Create video element
        const video = document.createElement('video');
        video.autoplay = true;
        video.playsinline = true;
        video.muted = true;
        video.className = 'webrtc-video';
        // z-index set via CSS class (0), below canvas (z-index: 1)

        // Insert into container
        this.$refs.container.appendChild(video);
        console.log('[WebRTC JS] Video element created and added to container');

        // Handle incoming track
        pc.ontrack = (e) => {
          console.log('[WebRTC JS] ontrack event, streams:', e.streams?.length);
          video.srcObject = e.streams[0];
        };

        // Handle connection state changes
        pc.onconnectionstatechange = () => {
          console.log('[WebRTC JS] Connection state:', pc.connectionState);
        };

        pc.oniceconnectionstatechange = () => {
          console.log('[WebRTC JS] ICE connection state:', pc.iceConnectionState);
        };

        // Set remote description (offer from Python)
        console.log('[WebRTC JS] Setting remote description...');
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        console.log('[WebRTC JS] Remote description set');

        // Create and send answer
        console.log('[WebRTC JS] Creating answer...');
        const answer = await pc.createAnswer();
        console.log('[WebRTC JS] Answer created');
        await pc.setLocalDescription(answer);
        console.log('[WebRTC JS] Local description set');

        console.log('[WebRTC JS] Emitting webrtc-answer for layer:', layerId);
        this.$emit('webrtc-answer', {
          layer_id: layerId,
          answer: {
            sdp: pc.localDescription.sdp,
            type: pc.localDescription.type,
          },
        });
        console.log('[WebRTC JS] Answer emitted successfully');

        // Store for cleanup and stats
        this.webrtcLayers[layerId] = {
          video,
          pc,
          zIndex,
          name: name || `WebRTC-${zIndex}`,
          lastBytes: 0,
          lastFramesDecoded: 0,
          lastStatsTime: performance.now(),
        };

        // Apply current zoom transform
        this.updateWebRTCTransform();

        // Start stats collection
        this.startWebRTCStatsCollection(layerId);

      } catch (error) {
        console.error('[WebRTC JS] Error in setupWebRTCLayer:', error);
        console.error('[WebRTC JS] Stack:', error.stack);
      }
    },

    removeWebRTCLayer(layerId) {
      const layer = this.webrtcLayers[layerId];
      if (layer) {
        layer.pc.close();
        layer.video.remove();
        delete this.webrtcLayers[layerId];
        delete this.webrtcStats[layerId];
      }
    },

    // Update WebRTC layers when viewport changes
    // Server-side cropping is handled via viewport-change event
    updateWebRTCTransform() {
      // No client-side transform - server handles cropping for better quality
      // The viewport-change event (emitViewportChange) notifies Python
      // which updates the WebRTC track's crop region
    },

    // Collect WebRTC stats periodically
    startWebRTCStatsCollection(layerId) {
      const collectStats = async () => {
        const layer = this.webrtcLayers[layerId];
        if (!layer) return;

        try {
          const stats = await layer.pc.getStats();
          let bitrate = 0, packetsLost = 0, jitter = 0, framesDecoded = 0, fps = 0;

          stats.forEach(report => {
            if (report.type === 'inbound-rtp' && report.kind === 'video') {
              const now = performance.now();
              const bytes = report.bytesReceived || 0;
              const frames = report.framesDecoded || 0;
              const deltaTime = (now - layer.lastStatsTime) / 1000;

              if (deltaTime > 0) {
                // Calculate bitrate
                if (layer.lastBytes > 0) {
                  const deltaBits = (bytes - layer.lastBytes) * 8;
                  bitrate = deltaBits / deltaTime;
                }

                // Calculate FPS from frames decoded delta
                if (layer.lastFramesDecoded > 0) {
                  const deltaFrames = frames - layer.lastFramesDecoded;
                  fps = deltaFrames / deltaTime;
                }
              }

              layer.lastBytes = bytes;
              layer.lastFramesDecoded = frames;
              layer.lastStatsTime = now;
              packetsLost = report.packetsLost || 0;
              jitter = (report.jitter || 0) * 1000; // Convert to ms
              framesDecoded = frames;
            }
          });

          this.webrtcStats[layerId] = { bitrate, packetsLost, jitter, framesDecoded, fps };
        } catch (e) {
          // Connection might be closed
        }

        // Continue collecting if layer still exists
        if (this.webrtcLayers[layerId]) {
          setTimeout(collectStats, 1000);
        }
      };

      // Start after a short delay
      setTimeout(collectStats, 1000);
    },

    // Format WebRTC bitrate for display
    formatWebRTCBitrate(bitrate) {
      if (bitrate >= 1000000) {
        return (bitrate / 1000000).toFixed(1) + ' Mbps';
      } else if (bitrate >= 1000) {
        return (bitrate / 1000).toFixed(0) + ' kbps';
      }
      return bitrate.toFixed(0) + ' bps';
    },

    // Format WebRTC bitrate short form for table
    formatWebRTCBitrateShort(bitrate) {
      if (bitrate >= 1000000) {
        return (bitrate / 1000000).toFixed(1) + 'M';
      } else if (bitrate >= 1000) {
        return (bitrate / 1000).toFixed(0) + 'K';
      }
      return '-';
    },

    // === Professional Metrics Panel Methods ===

    // Panel drag functionality
    startPanelDrag(e) {
      this.isPanelDragging = true;
      this.panelDragStart = {
        x: e.clientX - this.panelPosition.x,
        y: e.clientY - this.panelPosition.y,
      };

      const onMouseMove = (e) => {
        if (!this.isPanelDragging) return;
        this.panelPosition = {
          x: Math.max(0, e.clientX - this.panelDragStart.x),
          y: Math.max(0, e.clientY - this.panelDragStart.y),
        };
      };

      const onMouseUp = () => {
        this.isPanelDragging = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    },

    // Panel resize functionality
    startPanelResize(e) {
      this.isPanelResizing = true;
      this.panelSizeStart = { ...this.panelSize };
      this.panelDragStart = { x: e.clientX, y: e.clientY };

      const onMouseMove = (e) => {
        if (!this.isPanelResizing) return;
        const dx = e.clientX - this.panelDragStart.x;
        const dy = e.clientY - this.panelDragStart.y;
        this.panelSize = {
          width: Math.max(250, this.panelSizeStart.width + dx),
          height: Math.max(200, this.panelSizeStart.height + dy),
        };
      };

      const onMouseUp = () => {
        this.isPanelResizing = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    },

    // Toggle layer row expansion
    toggleLayerExpand(layerId) {
      this.expandedLayers = {
        ...this.expandedLayers,
        [layerId]: !this.expandedLayers[layerId],
      };
    },

    // Bandwidth tracking
    trackBandwidth(layerId, frameBytes) {
      const bw = this.layerBandwidth[layerId];
      if (!bw) return;

      const now = performance.now();

      // Add to history
      bw.bytesHistory.push({ time: now, bytes: frameBytes });

      // Keep last 60 samples
      if (bw.bytesHistory.length > 60) {
        bw.bytesHistory.shift();
      }

      // Update total bytes
      bw.totalBytes += frameBytes;

      // Calculate rate every 500ms
      if (now - bw.lastRateCalc > 500 && bw.bytesHistory.length >= 2) {
        const oldest = bw.bytesHistory[0];
        const timeSpanMs = now - oldest.time;
        const bytesInSpan = bw.bytesHistory.reduce((sum, h) => sum + h.bytes, 0);

        // Bytes per second
        bw.currentRate = timeSpanMs > 0 ? (bytesInSpan / timeSpanMs) * 1000 : 0;

        // Average frame size
        bw.avgFrameSize = bytesInSpan / bw.bytesHistory.length;

        bw.lastRateCalc = now;
      }
    },

    // Formatting helpers
    formatBandwidth(bytesPerSec) {
      if (bytesPerSec >= 1024 * 1024) {
        return `${(bytesPerSec / (1024 * 1024)).toFixed(1)} MB/s`;
      } else if (bytesPerSec >= 1024) {
        return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
      }
      return `${bytesPerSec.toFixed(0)} B/s`;
    },

    formatBandwidthShort(bytesPerSec) {
      if (bytesPerSec >= 1024 * 1024) {
        return `${(bytesPerSec / (1024 * 1024)).toFixed(1)}M`;
      } else if (bytesPerSec >= 1024) {
        return `${(bytesPerSec / 1024).toFixed(0)}K`;
      }
      return `${bytesPerSec.toFixed(0)}B`;
    },

    formatBytes(bytes) {
      if (bytes >= 1024 * 1024) {
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
      } else if (bytes >= 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
      }
      return `${bytes.toFixed(0)} B`;
    },

    // Get consistent color for a layer
    getLayerColor(layerId) {
      if (!this.layerColors[layerId]) {
        const colors = [
          '#4CAF50', '#2196F3', '#FF9800', '#E91E63',
          '#9C27B0', '#00BCD4', '#FFEB3B', '#795548',
        ];
        const idx = Object.keys(this.layerColors).length % colors.length;
        this.layerColors[layerId] = colors[idx];
      }
      return this.layerColors[layerId];
    },

    // Calculate latency percentage for breakdown bar
    getLatencyPercent(latency, part) {
      const total = latency.python + latency.network + latency.js;
      if (total <= 0) return 0;
      return (latency[part] / total) * 100;
    },

    // Layer data getters
    getLayerFps(layerId) {
      const layer = this.layers.get(layerId);
      if (!layer) return '0.0';
      // Show actual FPS with 1 decimal for precision
      return layer.fps.toFixed(1);
    },

    getLayerTargetFps(layerId) {
      const layer = this.layers.get(layerId);
      return layer?.config?.target_fps || 0;
    },

    getLayerSourceType(layerId) {
      const layer = this.layers.get(layerId);
      return layer?.config?.source_type || 'unknown';
    },

    getLayerTypeShort(layerId) {
      const layer = this.layers.get(layerId);
      if (!layer) return '?';

      const sourceType = layer.config?.source_type || 'unknown';
      const format = layer.config?.image_format || 'JPEG';

      // Short type labels
      const typeMap = {
        'video': 'VID',
        'custom': 'GEN',
        'stream': 'STR',
        'image': 'IMG',
        'url': 'URL',
      };

      const typeLabel = typeMap[sourceType] || sourceType.substring(0, 3).toUpperCase();
      const formatLabel = format === 'PNG' ? '/P' : '/J';

      return typeLabel + formatLabel;
    },

    getLayerBuffer(layerId) {
      const buf = this.layerBufferInfo[layerId];
      if (!buf) return '-';
      return `${buf.length}/${buf.capacity}`;
    },

    getLayerBufferPercent(layerId) {
      const buf = this.layerBufferInfo[layerId];
      if (!buf || buf.capacity === 0) return 0;
      return (buf.length / buf.capacity) * 100;
    },

    getLayerResolution(layerId) {
      const res = this.layerResolution[layerId];
      if (!res) return '-';
      return `${res.width}×${res.height}`;
    },

    getLayerRate(layerId) {
      return this.layerBandwidth[layerId]?.currentRate || 0;
    },

    getLayerAvgFrameSize(layerId) {
      return this.layerBandwidth[layerId]?.avgFrameSize || 0;
    },

    getLayerTotalBytes(layerId) {
      return this.layerBandwidth[layerId]?.totalBytes || 0;
    },

    // Unified chart drawing - shows all layers in one chart
    drawUnifiedChart() {
      if (this.metricsMinimized || this.metricsPaused) return;

      const canvas = this.$refs.unifiedChart;
      if (!canvas) return;

      // Handle high-DPI displays and responsive sizing
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = rect.width;
      const height = rect.height;

      // Set actual canvas size accounting for device pixel ratio
      canvas.width = width * dpr;
      canvas.height = height * dpr;

      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);

      // Clear canvas completely
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
      ctx.fillRect(0, 0, width, height);

      const layerIds = Object.keys(this.visibleLayerLatencies);
      if (layerIds.length === 0) return;

      const padding = { left: 30, right: 10, top: 5, bottom: 15 };
      const graphWidth = width - padding.left - padding.right;
      const graphHeight = height - padding.top - padding.bottom;

      // Get data based on mode
      let maxValue = 0;
      let unit = '';
      const allData = [];

      for (const layerId of layerIds) {
        let history, getValue;

        if (this.graphMode === 'latency') {
          history = this.latencyHistory[layerId] || [];
          getValue = (h) => h.total;
          unit = 'ms';
        } else if (this.graphMode === 'fps') {
          history = this.fpsHistory[layerId] || [];
          getValue = (h) => h.value;
          unit = 'fps';
        } else {  // bandwidth
          history = this.layerBandwidth[layerId]?.bytesHistory || [];
          getValue = (h) => h.bytes / 1024;  // KB
          unit = 'KB';
        }

        if (history.length > 0) {
          const values = history.map(getValue);
          maxValue = Math.max(maxValue, ...values);
          allData.push({ layerId, history, getValue, color: this.getLayerColor(layerId) });
        }
      }

      if (allData.length === 0 || maxValue === 0) return;

      // Add some headroom
      maxValue = maxValue * 1.1;

      // Draw grid lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
      ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = padding.top + (i / 4) * graphHeight;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
      }

      // Draw lines for each layer
      for (const { layerId, history, getValue, color } of allData) {
        if (history.length < 2) continue;

        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        for (let i = 0; i < history.length; i++) {
          const x = padding.left + (i / (history.length - 1)) * graphWidth;
          const y = padding.top + graphHeight - (getValue(history[i]) / maxValue) * graphHeight;

          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // Draw axis labels
      ctx.fillStyle = '#888';
      ctx.font = '9px monospace';
      ctx.textAlign = 'right';
      ctx.fillText(`${maxValue.toFixed(0)}${unit}`, padding.left - 3, padding.top + 8);
      ctx.fillText('0', padding.left - 3, height - padding.bottom);

      // Time label
      ctx.textAlign = 'center';
      ctx.fillText('now', width - padding.right, height - 2);
    },

    // Draw all charts (called periodically)
    drawAllCharts() {
      this.drawUnifiedChart();
    },

    // Export stats for the last 30 seconds as JSON
    exportStats() {
      const now = performance.now();
      const windowMs = 30 * 1000;  // 30 seconds
      const cutoff = now - windowMs;

      const stats = {
        exportTime: new Date().toISOString(),
        windowSeconds: 30,
        displayFps: this.displayFps,
        zoom: this.zoom,
        totalBandwidth: this.totalBandwidth,
        totalBytesTransferred: this.totalBytesTransferred,
        layers: {},
      };

      // Collect per-layer stats
      for (const [layerId, layer] of this.layers) {
        const config = layer.config || {};
        const latency = this.layerLatencies[layerId] || {};
        const bw = this.layerBandwidth[layerId] || {};

        // Filter history to last 30 seconds
        const fpsHist = (this.fpsHistory[layerId] || [])
          .filter(h => h.time >= cutoff)
          .map(h => ({ t: ((h.time - cutoff) / 1000).toFixed(2), fps: h.value.toFixed(1) }));

        const latencyHist = (this.latencyHistory[layerId] || [])
          .filter(h => h.time >= cutoff)
          .map(h => ({
            t: ((h.time - cutoff) / 1000).toFixed(2),
            total: h.total.toFixed(2),
            python: h.python.toFixed(2),
            network: h.network.toFixed(2),
            js: h.js.toFixed(2),
          }));

        const bwHist = (bw.bytesHistory || [])
          .filter(h => h.time >= cutoff)
          .map(h => ({ t: ((h.time - cutoff) / 1000).toFixed(2), bytes: h.bytes }));

        stats.layers[layerId] = {
          name: config.label || config.name || `Layer ${config.z_index}`,
          sourceType: config.source_type || 'unknown',
          imageFormat: config.image_format || 'JPEG',
          targetFps: config.target_fps || 0,
          currentFps: layer.fps?.toFixed(1) || '0',
          latency: {
            total: latency.total?.toFixed(2) || '0',
            python: latency.python?.toFixed(2) || '0',
            network: latency.network?.toFixed(2) || '0',
            js: latency.js?.toFixed(2) || '0',
          },
          bandwidth: {
            currentRate: bw.currentRate || 0,
            avgFrameSize: bw.avgFrameSize || 0,
            totalBytes: bw.totalBytes || 0,
          },
          buffer: this.layerBufferInfo[layerId] || { length: 0, capacity: 0 },
          resolution: this.layerResolution[layerId] || { width: 0, height: 0 },
          history: {
            fps: fpsHist,
            latency: latencyHist,
            bandwidth: bwHist,
          },
        };
      }

      // Create and download JSON file
      const json = JSON.stringify(stats, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `streamview-stats-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  },
};
