/**
 * EditorBridgeClient - WebSocket bridge for Python-JavaScript communication
 *
 * Provides bidirectional communication between JavaScript and Python:
 * - Python calls JS methods via registered handlers
 * - JS sends events to Python via emit()
 *
 * Example usage:
 *   const bridge = new EditorBridgeClient({
 *       url: `ws://${location.host}/api/ws/editor`,
 *       sessionId: 'my-session-id',
 *   });
 *
 *   // Register handler for Python commands
 *   bridge.registerHandler('executeCommand', (params) => {
 *       return { success: true };
 *   });
 *
 *   // Connect
 *   await bridge.connect();
 *
 *   // Send event to Python
 *   bridge.emit('state-update', { data: 'value' });
 */

export class EditorBridgeClient extends EventTarget {
    /**
     * Create a new bridge client.
     *
     * @param {Object} options Configuration options
     * @param {string} options.url WebSocket URL base (without session ID)
     * @param {string} options.sessionId Unique session identifier
     * @param {number} [options.heartbeatInterval=1000] Heartbeat interval in ms
     * @param {number} [options.reconnectDelay=1000] Delay before reconnect in ms
     * @param {number} [options.maxReconnectAttempts=10] Max reconnect attempts
     * @param {number} [options.responseTimeout=30000] Response timeout in ms
     */
    constructor({
        url,
        sessionId,
        heartbeatInterval = 1000,
        reconnectDelay = 1000,
        maxReconnectAttempts = Infinity,  // Never give up reconnecting
        maxReconnectDelay = 30000,        // Cap backoff at 30 seconds
        responseTimeout = 30000,
    }) {
        super();

        this._url = url;
        this._sessionId = sessionId;
        this._heartbeatInterval = heartbeatInterval;
        this._reconnectDelay = reconnectDelay;
        this._maxReconnectAttempts = maxReconnectAttempts;
        this._maxReconnectDelay = maxReconnectDelay;
        this._responseTimeout = responseTimeout;

        /** @type {WebSocket|null} */
        this._ws = null;

        /** @type {'connecting'|'connected'|'disconnected'|'reconnecting'} */
        this._state = 'disconnected';

        /** @type {number|null} */
        this._heartbeatTimer = null;

        /** @type {number} */
        this._reconnectAttempts = 0;

        /** @type {number|null} */
        this._reconnectTimer = null;

        /** @type {Map<string, Function>} Command handlers by method name */
        this._handlers = new Map();

        /** @type {Map<string, {resolve: Function, reject: Function, timer: number}>} */
        this._pendingResponses = new Map();

        /** @type {number} Time offset: serverTime - clientTime (ms) */
        this._timeOffset = 0;

        /** @type {number|null} Timestamp when connection was established */
        this._connectedAt = null;
    }

    // ==================== Properties ====================

    /**
     * Check if connected to server.
     * @returns {boolean}
     */
    get isConnected() {
        return this._state === 'connected' && this._ws?.readyState === WebSocket.OPEN;
    }

    /**
     * Get session ID.
     * @returns {string}
     */
    get sessionId() {
        return this._sessionId;
    }

    /**
     * Get current connection state.
     * @returns {'connecting'|'connected'|'disconnected'|'reconnecting'}
     */
    get state() {
        return this._state;
    }

    /**
     * Get time offset between server and client (serverTime - clientTime).
     * Positive means server is ahead, negative means client is ahead.
     * @returns {number} Offset in milliseconds
     */
    get timeOffset() {
        return this._timeOffset;
    }

    /**
     * Get the current server time based on local time + offset.
     * @returns {number} Server time in milliseconds since epoch
     */
    get serverTime() {
        return Date.now() + this._timeOffset;
    }

    /**
     * Get the timestamp when connection was established.
     * @returns {number|null}
     */
    get connectedAt() {
        return this._connectedAt;
    }

    // ==================== Connection ====================

    /**
     * Connect to the WebSocket server.
     * @returns {Promise<void>}
     */
    async connect() {
        if (this._state === 'connected' || this._state === 'connecting') {
            return;
        }

        this._state = 'connecting';
        this._dispatchStateEvent('connecting');

        return new Promise((resolve, reject) => {
            try {
                const wsUrl = `${this._url}/${this._sessionId}`;
                console.log(`[Bridge] Connecting to ${wsUrl}`);

                this._ws = new WebSocket(wsUrl);

                this._ws.onopen = () => {
                    console.log('[Bridge] Connected');
                    this._state = 'connected';
                    this._reconnectAttempts = 0;
                    this._startHeartbeat();
                    this._dispatchStateEvent('connected');
                    resolve();
                };

                this._ws.onclose = (event) => {
                    console.log(`[Bridge] Disconnected (code=${event.code})`);
                    this._handleDisconnect();
                };

                this._ws.onerror = (error) => {
                    console.error('[Bridge] WebSocket error:', error);
                    if (this._state === 'connecting') {
                        // Reset state so reconnect can try again
                        this._state = 'disconnected';
                        reject(new Error('Failed to connect'));
                    }
                };

                this._ws.onmessage = (event) => {
                    this._handleMessage(event.data);
                };

            } catch (error) {
                this._state = 'disconnected';
                reject(error);
            }
        });
    }

    /**
     * Disconnect from the server.
     */
    disconnect() {
        this._stopHeartbeat();
        this._cancelReconnect();

        if (this._ws) {
            this._ws.onclose = null; // Prevent reconnect
            this._ws.close();
            this._ws = null;
        }

        this._state = 'disconnected';
        this._dispatchStateEvent('disconnected');
    }

    // ==================== Command Handlers ====================

    /**
     * Register a handler for Python commands.
     *
     * @param {string} method The method name to handle
     * @param {Function} handler Handler function: (params) => result | Promise<result>
     */
    registerHandler(method, handler) {
        this._handlers.set(method, handler);
    }

    /**
     * Unregister a command handler.
     *
     * @param {string} method The method name to unregister
     */
    unregisterHandler(method) {
        this._handlers.delete(method);
    }

    // ==================== Events (JS -> Python) ====================

    /**
     * Send an event to Python (fire-and-forget).
     *
     * @param {string} event Event name
     * @param {Object} data Event data
     */
    emit(event, data = {}) {
        if (!this.isConnected) {
            console.warn(`[Bridge] Cannot emit '${event}': not connected`);
            return;
        }

        this._send({
            type: 'event',
            event: event,
            data: data,
        });
    }

    // ==================== Internal: Message Handling ====================

    /**
     * Handle incoming WebSocket message.
     * @private
     * @param {string} data Raw message data
     */
    async _handleMessage(data) {
        let message;
        try {
            message = JSON.parse(data);
        } catch (e) {
            console.error('[Bridge] Invalid JSON:', e);
            return;
        }

        const { type } = message;

        switch (type) {
            case 'sync':
                // Server time synchronization
                this._handleSync(message);
                break;

            case 'heartbeat_ack':
                // Server acknowledged heartbeat - nothing to do
                break;

            case 'command':
                await this._handleCommand(message);
                break;

            case 'response':
                this._handleResponse(message);
                break;

            case 'error':
                this._handleError(message);
                break;

            default:
                console.warn(`[Bridge] Unknown message type: ${type}`);
        }
    }

    /**
     * Handle time sync message from server.
     * @private
     * @param {Object} message Sync message with serverTime
     */
    _handleSync(message) {
        const clientTime = Date.now();
        const serverTime = message.serverTime;
        this._timeOffset = serverTime - clientTime;
        this._connectedAt = clientTime;
        console.log(`[Bridge] Time sync: offset=${this._timeOffset}ms (server ${this._timeOffset > 0 ? 'ahead' : 'behind'})`);
    }

    /**
     * Handle a command from Python.
     * @private
     * @param {Object} message Command message
     */
    async _handleCommand(message) {
        const { id, method, params } = message;

        const handler = this._handlers.get(method);
        if (!handler) {
            console.warn(`[Bridge] No handler for method: ${method}`);
            this._sendError(id, -32601, `Method not found: ${method}`);
            return;
        }

        try {
            const result = await handler(params || {});
            this._sendResponse(id, result);
        } catch (error) {
            console.error(`[Bridge] Handler error for ${method}:`, error);
            this._sendError(id, -32000, error.message || 'Handler error');
        }
    }

    /**
     * Handle a response to a pending request.
     * @private
     * @param {Object} message Response message
     */
    _handleResponse(message) {
        const { correlationId, result, error } = message;

        const pending = this._pendingResponses.get(correlationId);
        if (!pending) {
            console.warn(`[Bridge] No pending request for: ${correlationId}`);
            return;
        }

        clearTimeout(pending.timer);
        this._pendingResponses.delete(correlationId);

        if (error) {
            pending.reject(new Error(error.message || 'Unknown error'));
        } else {
            pending.resolve(result);
        }
    }

    /**
     * Handle an error message.
     * @private
     * @param {Object} message Error message
     */
    _handleError(message) {
        const { correlationId, error } = message;

        if (correlationId) {
            const pending = this._pendingResponses.get(correlationId);
            if (pending) {
                clearTimeout(pending.timer);
                this._pendingResponses.delete(correlationId);
                pending.reject(new Error(error?.message || 'Unknown error'));
                return;
            }
        }

        console.error('[Bridge] Server error:', error);
        this.dispatchEvent(new CustomEvent('error', { detail: error }));
    }

    // ==================== Internal: Sending ====================

    /**
     * Send a message to the server.
     * @private
     * @param {Object} message Message to send
     */
    _send(message) {
        if (this._ws?.readyState === WebSocket.OPEN) {
            this._ws.send(JSON.stringify(message));
        }
    }

    /**
     * Send a response to a command.
     * @private
     * @param {string} commandId Command ID to respond to
     * @param {*} result Result value
     */
    _sendResponse(commandId, result) {
        this._send({
            type: 'response',
            correlationId: commandId,
            result: result,
        });
    }

    /**
     * Send an error response.
     * @private
     * @param {string} commandId Command ID to respond to
     * @param {number} code Error code
     * @param {string} message Error message
     */
    _sendError(commandId, code, message) {
        this._send({
            type: 'error',
            correlationId: commandId,
            error: { code, message },
        });
    }

    // ==================== Internal: Heartbeat ====================

    /**
     * Start sending heartbeats.
     * @private
     */
    _startHeartbeat() {
        this._stopHeartbeat();

        this._heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                this._send({ type: 'heartbeat' });
            }
        }, this._heartbeatInterval);
    }

    /**
     * Stop sending heartbeats.
     * @private
     */
    _stopHeartbeat() {
        if (this._heartbeatTimer) {
            clearInterval(this._heartbeatTimer);
            this._heartbeatTimer = null;
        }
    }

    // ==================== Internal: Reconnection ====================

    /**
     * Handle disconnection and schedule reconnect.
     * @private
     */
    _handleDisconnect() {
        this._stopHeartbeat();
        this._ws = null;

        // Reject all pending responses
        for (const [id, pending] of this._pendingResponses) {
            clearTimeout(pending.timer);
            pending.reject(new Error('Connection lost'));
        }
        this._pendingResponses.clear();

        // Only schedule reconnect if not already reconnecting
        // (onerror + onclose can both fire, and reconnect timeout also schedules)
        if (this._state === 'reconnecting') {
            return; // Already handling reconnection
        }

        if (this._reconnectAttempts < this._maxReconnectAttempts) {
            this._state = 'reconnecting';
            this._dispatchStateEvent('reconnecting');
            this._scheduleReconnect();
        } else {
            this._state = 'disconnected';
            this._dispatchStateEvent('disconnected');
        }
    }

    /**
     * Schedule a reconnection attempt.
     * @private
     */
    _scheduleReconnect() {
        this._cancelReconnect();

        // Exponential backoff with cap
        const delay = Math.min(
            this._reconnectDelay * Math.pow(1.5, this._reconnectAttempts),
            this._maxReconnectDelay
        );
        console.log(`[Bridge] Reconnecting in ${Math.round(delay)}ms (attempt ${this._reconnectAttempts + 1})`);

        this._reconnectTimer = setTimeout(async () => {
            this._reconnectAttempts++;
            try {
                await this.connect();
            } catch (e) {
                console.error('[Bridge] Reconnect failed:', e);
                if (this._reconnectAttempts < this._maxReconnectAttempts) {
                    this._scheduleReconnect();
                } else {
                    this._state = 'disconnected';
                    this._dispatchStateEvent('disconnected');
                }
            }
        }, delay);
    }

    /**
     * Cancel any pending reconnection.
     * @private
     */
    _cancelReconnect() {
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
    }

    // ==================== Internal: Events ====================

    /**
     * Dispatch a state change event.
     * @private
     * @param {string} state New state
     */
    _dispatchStateEvent(state) {
        this.dispatchEvent(new CustomEvent(state));
        this.dispatchEvent(new CustomEvent('statechange', { detail: state }));
    }

    // ==================== Utility ====================

    /**
     * Generate a unique ID.
     * @private
     * @returns {string}
     */
    _generateId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
}

export default EditorBridgeClient;
