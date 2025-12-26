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

      <div v-if="showMetrics" class="stream-view-metrics">
        <div class="metrics-row">FPS: {{ displayFps.toFixed(1) }} | Zoom: {{ zoom.toFixed(1) }}x</div>
        <div class="metrics-row" v-for="(layer, id) in layerMetrics" :key="id">
          Layer {{ id.slice(0,4) }}: {{ layer.fps.toFixed(1) }} fps
        </div>
        <div v-if="Object.keys(layerLatencies).length > 0" class="metrics-timing">
          <div class="timing-header">Birth→Display Latency (ms)</div>
          <div v-for="(latency, layerId) in layerLatencies" :key="'lat-'+layerId" class="layer-latency-row">
            <span class="layer-latency-label">{{ latency.label }}:</span>
            <span class="layer-latency-value" :style="{ color: latency.color }">
              {{ latency.total.toFixed(1) }}ms
            </span>
            <span class="layer-latency-breakdown">
              (py:{{ latency.python.toFixed(1) }} + net:{{ latency.network.toFixed(1) }} + js:{{ latency.js.toFixed(1) }})
            </span>
            <div v-if="latency.filterDetails && latency.filterDetails.length > 0" class="layer-filter-details">
              <span v-for="(f, idx) in latency.filterDetails" :key="'f-'+idx" class="filter-detail">
                {{ f.name }}:{{ f.duration.toFixed(1) }}
              </span>
              <span class="filter-detail">Enc:{{ latency.encode.toFixed(1) }}</span>
            </div>
          </div>
          <div v-if="latencyDelta !== null" class="latency-delta" :class="latencyDeltaClass">
            Δ Thermal-Video: {{ latencyDelta.toFixed(1) }}ms
          </div>
        </div>
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
      maxTimingHistory: 30,      // Keep last N timing samples for averaging
      layerLatencies: {},        // layerId -> { label, total, python, network, js, color }

      // Clock sync for accurate network latency measurement
      clockOffset: 0,            // Estimated offset between Python and JS clocks (ms)
      clockSyncSamples: [],      // Samples for calculating clock offset

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
    };
  },

  computed: {
    containerStyle() {
      return {
        width: `${this.width}px`,
        height: `${this.height}px`,
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

    // Calculate delta between thermal and video latency
    latencyDelta() {
      const latencies = this.layerLatencies;
      let videoLatency = null;
      let thermalLatency = null;

      for (const [id, lat] of Object.entries(latencies)) {
        if (lat.label === 'Video') videoLatency = lat.total;
        if (lat.label === 'Thermal') thermalLatency = lat.total;
      }

      if (videoLatency !== null && thermalLatency !== null) {
        return thermalLatency - videoLatency;
      }
      return null;
    },

    latencyDeltaClass() {
      if (this.latencyDelta === null) return '';
      if (Math.abs(this.latencyDelta) < 10) return 'delta-good';
      if (Math.abs(this.latencyDelta) < 30) return 'delta-warning';
      return 'delta-bad';
    },
  },

  mounted() {
    this.ctx = this.$refs.canvas.getContext('2d');
    this.lastFpsUpdate = performance.now();

    // Start rendering loop
    this.startRenderLoop();
  },

  unmounted() {
    this.stop();
  },

  methods: {
    // === Layer Management ===

    addLayer(config) {
      // Assign display label based on z_index
      let label = `Layer ${config.z_index}`;
      if (config.z_index === 0) label = 'Video';
      else if (config.z_index === 15) label = 'Thermal';
      else if (config.z_index === 5) label = 'Watermark';
      else if (config.z_index === 8) label = 'Heatmap';
      else if (config.z_index === 10) label = 'Boxes';

      const layer = {
        config: { ...config, label },
        image: new Image(),
        lastUpdate: 0,
        lastRequest: 0,
        frameInterval: 1000 / config.target_fps,
        fps: 0,
        frameCount: 0,
        lastFpsCalc: performance.now(),
        isLoading: false,
        hasContent: false,
        // Overscan support: anchor position tracks where the content is centered
        // Display position (x, y) can move independently; offset compensates
        anchorX: config.x ?? 0,
        anchorY: config.y ?? 0,
      };

      // Initialize timing history for this layer
      this.layerTimingHistory[config.id] = [];

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

        // Calculate layer FPS
        const now = performance.now();
        const elapsed = now - layer.lastFpsCalc;
        if (elapsed >= 1000) {
          layer.fps = (layer.frameCount * 1000) / elapsed;
          layer.frameCount = 0;
          layer.lastFpsCalc = now;
          this.layerMetrics[config.id] = { fps: layer.fps };
        }

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

        layer.pendingMetadata = metadata;
      }

      // Update image source (triggers onload)
      // imageData can be a full data URL or raw base64 (legacy)
      layer.isLoading = true;
      if (imageData.startsWith('data:')) {
        layer.image.src = imageData;
      } else {
        // Legacy: raw base64, assume JPEG
        layer.image.src = `data:image/jpeg;base64,${imageData}`;
      }
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
      this.ctx.fillStyle = '#000';
      this.ctx.fillRect(0, 0, this.width, this.height);

      // Draw layers in z-order
      for (const layerId of this.layerOrder) {
        const layer = this.layers.get(layerId);
        if (!layer || !layer.hasContent) continue;

        try {
          // Get position/size from config (null = fill canvas)
          const cfg = layer.config;
          const x = cfg.x ?? 0;
          const y = cfg.y ?? 0;
          const w = cfg.width ?? this.width;
          const h = cfg.height ?? this.height;
          const overscan = cfg.overscan ?? 0;

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
            this.ctx.drawImage(layer.image, drawX, drawY, imgW, imgH);
            this.ctx.restore();
          } else {
            // Standard layer: draw image at specified position/size
            // Note: Server-side cropping handles viewport for content layers,
            // so we always draw the full received image here
            this.ctx.drawImage(layer.image, x, y, w, h);
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
      const scaleX = this.width / rect.width;
      const scaleY = this.height / rect.height;

      // Screen position
      const screenX = (e.clientX - rect.left) * scaleX;
      const screenY = (e.clientY - rect.top) * scaleY;

      // Convert to source image coordinates (accounting for zoom/pan)
      const sourceX = this.viewportX * this.width + screenX / this.zoom;
      const sourceY = this.viewportY * this.height + screenY / this.zoom;

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
      const scaleX = this.width / rect.width;
      const scaleY = this.height / rect.height;

      const screenX = (e.clientX - rect.left) * scaleX;
      const screenY = (e.clientY - rect.top) * scaleY;

      // Convert to source image coordinates
      const sourceX = this.viewportX * this.width + screenX / this.zoom;
      const sourceY = this.viewportY * this.height + screenY / this.zoom;

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
    },

    onGlobalMouseUp() {
      if (this.isDragging) {
        this.isDragging = false;
        this.emitViewportChange();
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
        // Find the first content layer (depth > 0) for nav thumbnail
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
      } catch (e) {
        // Image might not be ready
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
    },

    resetZoom() {
      this.zoom = 1.0;
      this.viewportX = 0;
      this.viewportY = 0;
      this.flashZoomIndicator();
      this.emitViewportChange();
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

      // Store in layerLatencies for display (only for Video and Thermal)
      if (layer.config.label === 'Video' || layer.config.label === 'Thermal') {
        this.layerLatencies = { ...this.layerLatencies, [layerId]: avg };
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
  },
};
