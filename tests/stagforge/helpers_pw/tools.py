"""ToolHelper - Tool-specific operations for Stagforge testing with Playwright."""

import asyncio
import json
from typing import Optional, Dict, List, Tuple, Any

from .editor import EditorTestHelper


class ToolHelper:
    """
    Helper class for tool-specific testing operations.

    Provides high-level methods for:
    - Brush/Eraser operations
    - Shape drawing (line, rect, circle, polygon)
    - Fill operations
    - Selection operations
    """

    def __init__(self, editor: EditorTestHelper):
        self.editor = editor

    # ===== Brush Tool =====

    async def brush_stroke(self, points: List[Tuple[float, float]],
                           color: str = None, size: int = None, hardness: int = None):
        """
        Draw a brush stroke through multiple points.

        Args:
            points: List of (x, y) document coordinates
            color: Brush color (hex), or None for current foreground
            size: Brush size in pixels
            hardness: Brush hardness 0-100
        """
        if color:
            await self.editor.set_foreground_color(color)

        await self.editor.select_tool('brush')

        if size is not None:
            await self.editor.set_tool_property('size', size)
        if hardness is not None:
            await self.editor.set_tool_property('hardness', hardness)

        await self.editor.draw_stroke(points)
        return self

    async def brush_dot(self, x: float, y: float, color: str = None, size: int = None):
        """Draw a single brush dot at a location."""
        return await self.brush_stroke([(x, y), (x, y)], color=color, size=size)

    async def brush_line(self, x1: float, y1: float, x2: float, y2: float,
                         color: str = None, size: int = None):
        """Draw a straight brush stroke from (x1, y1) to (x2, y2)."""
        return await self.brush_stroke([(x1, y1), (x2, y2)], color=color, size=size)

    # ===== Eraser Tool =====

    async def eraser_stroke(self, points: List[Tuple[float, float]], size: int = None):
        """
        Erase along a path.

        Args:
            points: List of (x, y) document coordinates
            size: Eraser size in pixels
        """
        await self.editor.select_tool('eraser')

        if size is not None:
            await self.editor.set_tool_property('size', size)

        await self.editor.draw_stroke(points)
        return self

    async def eraser_line(self, x1: float, y1: float, x2: float, y2: float, size: int = None):
        """Erase in a straight line."""
        return await self.eraser_stroke([(x1, y1), (x2, y2)], size=size)

    # ===== Line Tool =====

    async def draw_line(self, x1: float, y1: float, x2: float, y2: float,
                        color: str = None, width: int = None, raster: bool = True):
        """
        Draw a line from (x1, y1) to (x2, y2).

        Args:
            x1, y1: Start point in document coordinates
            x2, y2: End point
            color: Line color (hex), or None for current foreground
            width: Line width in pixels
            raster: If True (default), draw in raster mode; if False, create vector shape
        """
        if color:
            await self.editor.set_foreground_color(color)

        await self.editor.select_tool('line')

        # Set raster mode (vectorMode = false means raster)
        await self.editor.set_tool_property('vectorMode', not raster)

        if width is not None:
            await self.editor.set_tool_property('strokeWidth', width)

        await self.editor.drag_at_doc(x1, y1, x2, y2)
        return self

    # ===== Rectangle Tool =====

    async def draw_rect(self, x: float, y: float, width: float, height: float,
                        fill_color: str = None, stroke_color: str = None,
                        stroke_width: int = None, fill: bool = True, stroke: bool = True,
                        raster: bool = True):
        """
        Draw a rectangle.

        Args:
            x, y: Top-left corner in document coordinates
            width, height: Size of rectangle
            fill_color: Fill color (hex), or None for foreground
            stroke_color: Stroke color (hex), or None for background
            stroke_width: Width of stroke
            fill: Whether to fill
            stroke: Whether to stroke
            raster: If True (default), draw in raster mode; if False, create vector shape
        """
        if fill_color:
            await self.editor.set_foreground_color(fill_color)
        if stroke_color:
            await self.editor.set_background_color(stroke_color)

        await self.editor.select_tool('rect')

        # Set raster mode (vectorMode = false means raster)
        await self.editor.set_tool_property('vectorMode', not raster)

        if stroke_width is not None:
            await self.editor.set_tool_property('strokeWidth', stroke_width)
        await self.editor.set_tool_property('fill', fill)
        await self.editor.set_tool_property('stroke', stroke)

        await self.editor.drag_at_doc(x, y, x + width, y + height)
        return self

    async def draw_filled_rect(self, x: float, y: float, width: float, height: float,
                               color: str = None):
        """Draw a filled rectangle without stroke."""
        return await self.draw_rect(x, y, width, height, fill_color=color, fill=True, stroke=False)

    async def draw_rect_outline(self, x: float, y: float, width: float, height: float,
                                color: str = None, width_: int = 1):
        """Draw a rectangle outline without fill."""
        return await self.draw_rect(x, y, width, height, stroke_color=color,
                                    stroke_width=width_, fill=False, stroke=True)

    # ===== Circle Tool =====

    async def draw_circle(self, cx: float, cy: float, radius: float,
                          fill_color: str = None, stroke_color: str = None,
                          stroke_width: int = None, fill: bool = True, stroke: bool = True,
                          raster: bool = True):
        """
        Draw a circle (or ellipse if dragging creates non-square).

        Args:
            cx, cy: Center point in document coordinates
            radius: Radius of circle
            fill_color: Fill color
            stroke_color: Stroke color
            stroke_width: Width of stroke
            fill: Whether to fill
            stroke: Whether to stroke
            raster: If True (default), draw in raster mode; if False, create vector shape
        """
        if fill_color:
            await self.editor.set_foreground_color(fill_color)
        if stroke_color:
            await self.editor.set_background_color(stroke_color)

        await self.editor.select_tool('circle')

        # Set raster mode (vectorMode = false means raster)
        await self.editor.set_tool_property('vectorMode', not raster)

        if stroke_width is not None:
            await self.editor.set_tool_property('strokeWidth', stroke_width)
        await self.editor.set_tool_property('fill', fill)
        await self.editor.set_tool_property('stroke', stroke)

        # Drag from center-radius to center+radius to create circle
        x1 = cx - radius
        y1 = cy - radius
        x2 = cx + radius
        y2 = cy + radius
        await self.editor.drag_at_doc(x1, y1, x2, y2)
        return self

    async def draw_filled_circle(self, cx: float, cy: float, radius: float, color: str = None):
        """Draw a filled circle without stroke."""
        return await self.draw_circle(cx, cy, radius, fill_color=color, fill=True, stroke=False)

    async def draw_ellipse(self, x: float, y: float, width: float, height: float,
                           fill_color: str = None, stroke_color: str = None,
                           fill: bool = True, stroke: bool = True):
        """Draw an ellipse by specifying bounding box."""
        if fill_color:
            await self.editor.set_foreground_color(fill_color)
        if stroke_color:
            await self.editor.set_background_color(stroke_color)

        await self.editor.select_tool('circle')
        await self.editor.set_tool_property('fill', fill)
        await self.editor.set_tool_property('stroke', stroke)

        await self.editor.drag_at_doc(x, y, x + width, y + height)
        return self

    # ===== Polygon Tool =====

    async def draw_polygon(self, points: List[Tuple[float, float]],
                           fill_color: str = None, stroke_color: str = None,
                           stroke_width: int = None, fill: bool = True, stroke: bool = True):
        """
        Draw a polygon by clicking vertices.

        Args:
            points: List of vertex coordinates
            fill_color: Fill color
            stroke_color: Stroke color
            stroke_width: Width of stroke
            fill: Whether to fill
            stroke: Whether to stroke
        """
        if len(points) < 3:
            return self

        if fill_color:
            await self.editor.set_foreground_color(fill_color)
        if stroke_color:
            await self.editor.set_background_color(stroke_color)

        await self.editor.select_tool('polygon')

        if stroke_width is not None:
            await self.editor.set_tool_property('strokeWidth', stroke_width)
        await self.editor.set_tool_property('fill', fill)
        await self.editor.set_tool_property('stroke', stroke)

        # Click each vertex
        for x, y in points:
            await self.editor.click_at_doc(x, y)
            await asyncio.sleep(0.05)

        # Double-click to close (or click first point again)
        await self.editor.click_at_doc(points[0][0], points[0][1])
        await asyncio.sleep(0.1)

        return self

    # ===== Fill Tool =====

    async def fill_at(self, x: float, y: float, color: str = None, tolerance: int = None):
        """
        Fill (flood fill / paint bucket) starting at a point.

        Args:
            x, y: Start point in document coordinates
            color: Fill color, or None for foreground
            tolerance: Color tolerance for fill expansion
        """
        if color:
            await self.editor.set_foreground_color(color)

        await self.editor.select_tool('fill')

        if tolerance is not None:
            await self.editor.set_tool_property('tolerance', tolerance)

        await self.editor.click_at_doc(x, y)
        return self

    async def gradient_stroke(self, start: tuple, end: tuple,
                              fg_color: str = None, bg_color: str = None,
                              gradient_type: str = None, opacity: int = None):
        """
        Draw a gradient from start to end point.

        Args:
            start: (x, y) start point in document coordinates
            end: (x, y) end point in document coordinates
            fg_color: Start color (foreground), or None for current
            bg_color: End color (background), or None for current
            gradient_type: 'linear' or 'radial'
            opacity: Gradient opacity 1-100
        """
        if fg_color:
            await self.editor.set_foreground_color(fg_color)
        if bg_color:
            await self.editor.set_background_color(bg_color)

        await self.editor.select_tool('gradient')

        if gradient_type is not None:
            await self.editor.set_tool_property('gradientType', gradient_type)
        if opacity is not None:
            await self.editor.set_tool_property('opacity', opacity)

        await self.editor.drag_at_doc(start[0], start[1], end[0], end[1])
        return self

    # ===== Eyedropper Tool =====

    async def pick_color_at(self, x: float, y: float) -> Optional[str]:
        """
        Use eyedropper to pick color at a point.

        Args:
            x, y: Document coordinates

        Returns:
            Picked color as hex string
        """
        await self.editor.select_tool('eyedropper')
        await self.editor.click_at_doc(x, y)
        await asyncio.sleep(0.1)
        return await self.editor.get_foreground_color()

    # ===== Magic Wand Tool =====

    async def magic_wand_select(self, x: float, y: float, tolerance: int = None,
                                contiguous: bool = None):
        """
        Select with magic wand at a point.

        Args:
            x, y: Document coordinates to start selection
            tolerance: Color tolerance 0-255
            contiguous: Whether to only select connected pixels
        """
        await self.editor.select_tool('magicwand')

        if tolerance is not None:
            await self.editor.set_tool_property('tolerance', tolerance)
        if contiguous is not None:
            await self.editor.set_tool_property('contiguous', contiguous)

        await self.editor.click_at_doc(x, y)
        await asyncio.sleep(0.1)
        return self

    # ===== Move Tool =====

    async def move_layer(self, dx: float, dy: float, layer_id: str = None):
        """
        Move a layer by an offset.

        Args:
            dx, dy: Amount to move in document coordinates
            layer_id: Layer to move, or None for active layer
        """
        if layer_id:
            await self.editor.select_layer(layer_id=layer_id)

        # Get current layer position
        layer_info = await self.editor.get_layer_info(layer_id=layer_id)
        if not layer_info:
            return self

        await self.editor.select_tool('move')

        # Drag from current position to new position
        cx = layer_info['offsetX'] + layer_info['width'] / 2
        cy = layer_info['offsetY'] + layer_info['height'] / 2
        await self.editor.drag_at_doc(cx, cy, cx + dx, cy + dy)
        return self

    async def move_selection_content(self, dx: float, dy: float):
        """
        Move the content within a selection.

        Args:
            dx, dy: Amount to move
        """
        selection = await self.editor.get_selection()
        if not selection:
            return self

        await self.editor.select_tool('move')

        cx = selection['x'] + selection['width'] / 2
        cy = selection['y'] + selection['height'] / 2
        await self.editor.drag_at_doc(cx, cy, cx + dx, cy + dy)
        return self

    # ===== API-based Tool Execution =====

    async def execute_tool_action(self, tool_id: str, action: str, params: Dict[str, Any]) -> Dict:
        """
        Execute a tool action via the internal API (not mouse events).

        This uses the tool's executeAction method directly.

        Args:
            tool_id: ID of the tool
            action: Action name
            params: Parameters for the action

        Returns:
            Result dict from the tool
        """
        params_json = json.dumps(params)
        return await self.editor.execute_js(f"""
            (() => {{
                const vm = window.__stagforge_app__;
                const app = vm?.getState?.() || vm;
                const tool = app?.toolManager?.tools?.get('{tool_id}');
                if (!tool || !tool.executeAction) return {{ success: false, error: 'Tool not found or has no executeAction' }};
                return tool.executeAction('{action}', {params_json});
            }})()
        """)

    async def api_draw_line(self, x1: float, y1: float, x2: float, y2: float,
                            color: str = None, width: int = 1) -> Dict:
        """Draw a line using the tool API."""
        params = {
            'start': {'x': x1, 'y': y1},
            'end': {'x': x2, 'y': y2},
            'width': width
        }
        if color:
            params['color'] = color
        return await self.execute_tool_action('line', 'draw', params)

    async def api_draw_rect(self, x: float, y: float, width: float, height: float,
                            fill_color: str = None, stroke_color: str = None,
                            fill: bool = True, stroke: bool = True) -> Dict:
        """Draw a rectangle using the tool API."""
        params = {
            'start': {'x': x, 'y': y},
            'end': {'x': x + width, 'y': y + height},
            'fill': fill,
            'stroke': stroke
        }
        if fill_color:
            params['fillColor'] = fill_color
        if stroke_color:
            params['strokeColor'] = stroke_color
        return await self.execute_tool_action('rect', 'draw', params)

    async def api_draw_circle(self, cx: float, cy: float, radius: float,
                              fill_color: str = None, stroke_color: str = None,
                              fill: bool = True, stroke: bool = True) -> Dict:
        """Draw a circle using the tool API."""
        params = {
            'start': {'x': cx - radius, 'y': cy - radius},
            'end': {'x': cx + radius, 'y': cy + radius},
            'fill': fill,
            'stroke': stroke
        }
        if fill_color:
            params['fillColor'] = fill_color
        if stroke_color:
            params['strokeColor'] = stroke_color
        return await self.execute_tool_action('circle', 'draw', params)

    async def api_fill(self, x: float, y: float, color: str = None, tolerance: int = 32) -> Dict:
        """Fill at a point using the tool API."""
        params = {
            'point': {'x': x, 'y': y},
            'tolerance': tolerance
        }
        if color:
            params['color'] = color
        return await self.execute_tool_action('fill', 'fill', params)

    async def api_brush_stroke(self, points: List[Tuple[float, float]],
                               color: str = None, size: int = 10) -> Dict:
        """Draw a brush stroke using the tool API."""
        params = {
            'points': [{'x': p[0], 'y': p[1]} for p in points],
            'size': size
        }
        if color:
            params['color'] = color
        return await self.execute_tool_action('brush', 'stroke', params)

    async def api_select(self, x: float, y: float, width: float, height: float) -> Dict:
        """Create a selection using the tool API."""
        params = {
            'x': x,
            'y': y,
            'width': width,
            'height': height
        }
        return await self.execute_tool_action('selection', 'select', params)

    # ===== Pencil Tool =====

    async def pencil_stroke(self, points: List[Tuple[float, float]],
                            color: str = None, size: int = None):
        """
        Draw a pencil stroke (hard-edged, aliased) through multiple points.

        Args:
            points: List of (x, y) document coordinates
            color: Pencil color (hex), or None for current foreground
            size: Pencil size in pixels (default 1 for pixel art)
        """
        if color:
            await self.editor.set_foreground_color(color)

        await self.editor.select_tool('pencil')

        if size is not None:
            await self.editor.set_tool_property('size', size)

        await self.editor.draw_stroke(points)
        return self

    async def pencil_line(self, x1: float, y1: float, x2: float, y2: float,
                          color: str = None, size: int = 1):
        """Draw a straight pencil line from (x1, y1) to (x2, y2)."""
        return await self.pencil_stroke([(x1, y1), (x2, y2)], color=color, size=size)

    # ===== Clone Stamp Tool =====

    async def clone_stamp_set_source(self, x: float, y: float):
        """Set the clone stamp source point."""
        await self.editor.select_tool('clonestamp')
        # Alt+click to set source
        await self.editor.alt_click_at_doc(x, y)
        return self

    async def clone_stamp_stroke(self, points: List[Tuple[float, float]], size: int = None):
        """
        Paint with clone stamp.
        Must call clone_stamp_set_source first.

        Args:
            points: List of (x, y) document coordinates to paint at
            size: Stamp size in pixels
        """
        await self.editor.select_tool('clonestamp')

        if size is not None:
            await self.editor.set_tool_property('size', size)

        await self.editor.draw_stroke(points)
        return self

    # ===== Smudge Tool =====

    async def smudge_stroke(self, points: List[Tuple[float, float]],
                            size: int = None, strength: int = None):
        """
        Smudge along a path.

        Args:
            points: List of (x, y) document coordinates
            size: Smudge tool size
            strength: Smudge strength 0-100
        """
        await self.editor.select_tool('smudge')

        if size is not None:
            await self.editor.set_tool_property('size', size)
        if strength is not None:
            await self.editor.set_tool_property('strength', strength)

        await self.editor.draw_stroke(points)
        return self

    # ===== Blur Tool =====

    async def blur_stroke(self, points: List[Tuple[float, float]],
                          size: int = None, strength: int = None):
        """
        Apply blur effect along a path.

        Args:
            points: List of (x, y) document coordinates
            size: Blur tool size
            strength: Blur strength 0-100
        """
        await self.editor.select_tool('blur')

        if size is not None:
            await self.editor.set_tool_property('size', size)
        if strength is not None:
            await self.editor.set_tool_property('strength', strength)

        await self.editor.draw_stroke(points)
        return self

    # ===== Sharpen Tool =====

    async def sharpen_stroke(self, points: List[Tuple[float, float]],
                             size: int = None, strength: int = None):
        """
        Apply sharpen effect along a path.

        Args:
            points: List of (x, y) document coordinates
            size: Sharpen tool size
            strength: Sharpen strength 0-100
        """
        await self.editor.select_tool('sharpen')

        if size is not None:
            await self.editor.set_tool_property('size', size)
        if strength is not None:
            await self.editor.set_tool_property('strength', strength)

        await self.editor.draw_stroke(points)
        return self

    # ===== Dodge Tool =====

    async def dodge_stroke(self, points: List[Tuple[float, float]],
                           size: int = None, exposure: int = None, range_: str = None):
        """
        Lighten areas along a path.

        Args:
            points: List of (x, y) document coordinates
            size: Dodge tool size
            exposure: Exposure 0-100
            range_: Target range ('shadows', 'midtones', 'highlights')
        """
        await self.editor.select_tool('dodge')

        if size is not None:
            await self.editor.set_tool_property('size', size)
        if exposure is not None:
            await self.editor.set_tool_property('exposure', exposure)
        if range_ is not None:
            await self.editor.set_tool_property('range', range_)

        await self.editor.draw_stroke(points)
        return self

    # ===== Burn Tool =====

    async def burn_stroke(self, points: List[Tuple[float, float]],
                          size: int = None, exposure: int = None, range_: str = None):
        """
        Darken areas along a path.

        Args:
            points: List of (x, y) document coordinates
            size: Burn tool size
            exposure: Exposure 0-100
            range_: Target range ('shadows', 'midtones', 'highlights')
        """
        await self.editor.select_tool('burn')

        if size is not None:
            await self.editor.set_tool_property('size', size)
        if exposure is not None:
            await self.editor.set_tool_property('exposure', exposure)
        if range_ is not None:
            await self.editor.set_tool_property('range', range_)

        await self.editor.draw_stroke(points)
        return self

    # ===== Sponge Tool =====

    async def sponge_stroke(self, points: List[Tuple[float, float]],
                            size: int = None, flow: int = None, mode: str = None):
        """
        Saturate or desaturate along a path.

        Args:
            points: List of (x, y) document coordinates
            size: Sponge tool size
            flow: Flow 0-100
            mode: 'saturate' or 'desaturate'
        """
        await self.editor.select_tool('sponge')

        if size is not None:
            await self.editor.set_tool_property('size', size)
        if flow is not None:
            await self.editor.set_tool_property('flow', flow)
        if mode is not None:
            await self.editor.set_tool_property('mode', mode)

        await self.editor.draw_stroke(points)
        return self
