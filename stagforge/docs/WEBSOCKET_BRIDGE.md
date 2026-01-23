# WebSocket Bridge

## Overview

The WebSocket Bridge provides bidirectional communication between the Python backend and JavaScript frontend, replacing NiceGUI's `run_method`/`run_javascript` calls with a reusable, thread-safe WebSocket system.

## Architecture

```
Python Backend                    WebSocket                    JavaScript Frontend
┌─────────────────┐              ┌────────────┐              ┌────────────────────┐
│ EditorBridge    │◄────────────►│   /ws/     │◄────────────►│ EditorBridgeClient │
│ (Thread-safe)   │              │  editor/   │              │ (EventTarget)      │
└─────────────────┘              │  {session} │              └────────────────────┘
                                 └────────────┘
```

## Message Protocol

All messages are JSON with this structure:

```json
{
  "type": "command|response|event|heartbeat|heartbeat_ack|error",
  "id": "uuid",                    // For command/response correlation
  "correlationId": "uuid",         // Response references command id
  "method": "methodName",          // For commands
  "params": {},                    // For commands
  "result": {},                    // For responses
  "error": {"code": 0, "message": ""}, // For errors
  "event": "eventName",            // For events
  "data": {}                       // For events
}
```

### Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `heartbeat` | JS → Python | Keepalive (every 1s) |
| `heartbeat_ack` | Python → JS | Heartbeat response |
| `command` | Python → JS | Execute method, expect response |
| `response` | JS → Python | Result of command |
| `event` | JS → Python | Fire-and-forget notification |
| `error` | Either | Error for failed command |

## Python API

### EditorBridge Class

```python
from stagforge.bridge import EditorBridge

# Create bridge instance (typically done once at startup)
bridge = EditorBridge(
    session_timeout=30.0,      # Cleanup after 30s inactivity
    heartbeat_interval=1.0,    # Expected JS heartbeat rate
    response_timeout=30.0,     # Default call timeout
)

# Start background tasks
bridge.start()

# Call JS method (blocking, thread-safe)
result = bridge.call(session_id, "executeToolAction", {
    "toolId": "brush",
    "action": "stroke",
    "params": {"points": [...], "color": "#FF0000"}
})

# Fire-and-forget command
bridge.fire(session_id, "refreshUI", {"area": "layers"})

# Broadcast to all sessions
bridge.broadcast("configChanged", {"path": "rendering.zoom"})

# Stop bridge
bridge.stop()
```

### Session Management

```python
# Get or create session
session = bridge.get_or_create_session(session_id)

# Get existing session
session = bridge.get_session(session_id)

# Check connection status
if session and session.is_connected:
    # Session is connected

# Remove session
bridge.remove_session(session_id)

# List all sessions
sessions = bridge.get_all_sessions()
```

### WebSocket Endpoint

The bridge integrates with FastAPI:

```python
from fastapi import WebSocket
from stagforge.bridge import editor_bridge

@router.websocket("/ws/editor/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await editor_bridge.websocket_endpoint(websocket, session_id)
```

## JavaScript API

### EditorBridgeClient Class

```javascript
import { EditorBridgeClient } from './bridge/EditorBridgeClient.js';

const bridge = new EditorBridgeClient({
    url: `ws://${location.host}/ws/editor`,
    sessionId: this.sessionId,
    heartbeatInterval: 1000,     // 1 second
    reconnectDelay: 1000,        // 1 second
    maxReconnectAttempts: 10,
    responseTimeout: 30000,      // 30 seconds
});

// Connect
await bridge.connect();

// Check connection
if (bridge.isConnected) {
    // Connected
}

// Emit event to Python (fire-and-forget)
bridge.emit('state-update', { layerCount: 5 });

// Register handler for Python commands
bridge.registerHandler('executeToolAction', async (params) => {
    return this.executeToolAction(params.toolId, params.action, params.params);
});

// Event listeners
bridge.addEventListener('connected', () => console.log('Connected'));
bridge.addEventListener('disconnected', () => console.log('Disconnected'));
bridge.addEventListener('reconnecting', () => console.log('Reconnecting'));
bridge.addEventListener('error', (e) => console.error('Error:', e.detail));

// Disconnect
bridge.disconnect();
```

### State Property

```javascript
bridge.state  // 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
```

## Registered Handlers

The JavaScript bridge registers these handlers for Python commands:

| Handler | Purpose |
|---------|---------|
| `executeToolAction` | Execute a tool action |
| `executeCommand` | Execute an editor command |
| `pushData` | Push layer/document data to backend |
| `exportDocument` | Export document as JSON |
| `importDocument` | Import document from JSON |
| `getConfig` | Get configuration value |
| `setConfig` | Set configuration value |
| `getLayerEffects` | Get effects for a layer |
| `addLayerEffect` | Add effect to layer |
| `updateLayerEffect` | Update effect parameters |
| `removeLayerEffect` | Remove effect from layer |

## Session Lifecycle

```
1. JS EditorBridgeClient.connect()
   → WebSocket opens to /ws/editor/{sessionId}
   → Python creates/reuses BridgeSession

2. JS sends heartbeat every 1 second
   → Python updates last_heartbeat
   → Python sends heartbeat_ack

3. Python bridge.call(sessionId, method, params)
   → Sends command message to JS
   → JS executes handler
   → JS sends response
   → Python returns result (or raises timeout)

4. JS bridge.emit(event, data)
   → Sends event message to Python
   → Python session.on_event callback fires

5. No heartbeat for 30 seconds
   → Python cleanup task removes session
   → WebSocket closed if still open

6. Disconnect (network, server restart)
   → JS detects close, emits 'disconnected'
   → JS waits reconnectDelay, reconnects
   → Python reuses session if not timed out
```

## Error Handling

### Python Side

```python
from stagforge.bridge import BridgeTimeoutError, BridgeSessionError

try:
    result = bridge.call(session_id, "executeToolAction", params)
except BridgeTimeoutError:
    # Command timed out waiting for response
    pass
except BridgeSessionError:
    # Session not found or not connected
    pass
```

### JavaScript Side

```javascript
bridge.addEventListener('error', (event) => {
    console.error('Bridge error:', event.detail);
});
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STAGFORGE_WS_TIMEOUT` | 30.0 | Response timeout in seconds |
| `STAGFORGE_WS_HEARTBEAT` | 1.0 | Heartbeat interval in seconds |
| `STAGFORGE_WS_SESSION_TIMEOUT` | 30.0 | Session cleanup timeout |

## File Structure

```
stagforge/
├── bridge/
│   ├── __init__.py          # Exports: EditorBridge, BridgeSession, exceptions
│   ├── editor_bridge.py     # Main EditorBridge class
│   ├── session.py           # BridgeSession dataclass
│   └── exceptions.py        # BridgeError, BridgeTimeoutError, etc.
├── frontend/js/
│   └── bridge/
│       └── EditorBridgeClient.js  # JavaScript client
└── api/
    └── router.py            # WebSocket endpoint registration
```

## Migration from NiceGUI

### Before (NiceGUI)

```python
# In canvas_editor.py
result = await session.editor.run_method("executeToolAction", tool_id, action, params)
```

### After (EditorBridge)

```python
# In session_manager.py
result = bridge.call(session_id, "executeToolAction", {
    "toolId": tool_id,
    "action": action,
    "params": params
})
```

### Vue $emit Replacement

```javascript
// Before (Vue)
this.$emit('state-update', stateData);

// After (EditorBridge)
if (this._bridge?.isConnected) {
    this._bridge.emit('state-update', stateData);
}
```

## Debugging

### Check Connection Status

```bash
# Get session info including bridge status
curl http://localhost:8080/api/sessions
```

### Monitor WebSocket Traffic

In browser DevTools, Network tab → WS → select connection → Messages

### Python Logging

```python
import logging
logging.getLogger('stagforge.bridge').setLevel(logging.DEBUG)
```

## Thread Safety

The EditorBridge is fully thread-safe:

- Internal event loop runs in dedicated thread
- `call()` uses `threading.Event` to block until response
- `_pending_calls` dict protected by `threading.Lock`
- `asyncio.run_coroutine_threadsafe()` for cross-thread async calls

This allows synchronous Python code to make blocking calls to JavaScript without blocking the main event loop.
