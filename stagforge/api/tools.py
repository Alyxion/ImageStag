"""Tools API endpoints - list available tools and their parameters."""

from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["tools"])


# Available tools and their actions/parameters
TOOLS = {
    "selection": {
        "name": "Selection",
        "icon": "crop_free",
        "shortcut": "M",
        "description": "Select rectangular areas",
        "actions": {
            "select": {
                "description": "Select a rectangular area",
                "params": {
                    "x": {"type": "int", "description": "Left edge"},
                    "y": {"type": "int", "description": "Top edge"},
                    "width": {"type": "int", "description": "Selection width"},
                    "height": {"type": "int", "description": "Selection height"},
                },
            },
            "select_all": {
                "description": "Select the entire document",
                "params": {},
            },
            "clear": {
                "description": "Clear the selection",
                "params": {},
            },
            "get": {
                "description": "Get current selection bounds",
                "params": {},
            },
        },
    },
    "lasso": {
        "name": "Lasso",
        "icon": "gesture",
        "shortcut": "L",
        "description": "Freehand selection",
        "actions": {
            "select": {
                "description": "Select a freehand area",
                "params": {
                    "points": {
                        "type": "array",
                        "description": "Array of [x, y] points",
                    },
                },
            },
            "clear": {
                "description": "Clear the selection",
                "params": {},
            },
        },
    },
    "magicwand": {
        "name": "Magic Wand",
        "icon": "auto_fix_high",
        "shortcut": "W",
        "description": "Select similar colors",
        "actions": {
            "select": {
                "description": "Select area by color similarity",
                "params": {
                    "x": {"type": "int", "description": "Click X position"},
                    "y": {"type": "int", "description": "Click Y position"},
                    "tolerance": {
                        "type": "int",
                        "description": "Color tolerance (0-255)",
                        "default": 32,
                    },
                    "contiguous": {
                        "type": "bool",
                        "description": "Only select connected pixels",
                        "default": True,
                    },
                },
            },
        },
    },
    "move": {
        "name": "Move",
        "icon": "open_with",
        "shortcut": "V",
        "description": "Move and resize layers",
        "actions": {
            "move": {
                "description": "Move the active layer by a relative offset",
                "params": {
                    "dx": {"type": "int", "description": "Horizontal offset in pixels"},
                    "dy": {"type": "int", "description": "Vertical offset in pixels"},
                },
            },
            "set_position": {
                "description": "Set the active layer's absolute position",
                "params": {
                    "x": {"type": "int", "description": "X position in document coordinates"},
                    "y": {"type": "int", "description": "Y position in document coordinates"},
                },
            },
            "resize": {
                "description": "Resize the active layer to specific dimensions",
                "params": {
                    "width": {"type": "int", "description": "Target width in pixels"},
                    "height": {"type": "int", "description": "Target height in pixels"},
                    "maintainAspectRatio": {
                        "type": "bool",
                        "description": "Maintain aspect ratio (default: false)",
                        "default": False,
                    },
                },
            },
            "scale": {
                "description": "Scale the active layer by a factor",
                "params": {
                    "scale": {"type": "float", "description": "Uniform scale factor (e.g., 2.0 = 200%)"},
                    "scaleX": {"type": "float", "description": "Horizontal scale factor (overrides scale)"},
                    "scaleY": {"type": "float", "description": "Vertical scale factor (overrides scale)"},
                },
            },
        },
    },
    "brush": {
        "name": "Brush",
        "icon": "brush",
        "shortcut": "B",
        "description": "Paint with brush strokes",
        "actions": {
            "stroke": {
                "description": "Draw a brush stroke",
                "params": {
                    "points": {
                        "type": "array",
                        "description": "Array of [x, y] points",
                    },
                    "color": {
                        "type": "string",
                        "description": "Hex color (#RRGGBB)",
                        "default": "#000000",
                    },
                    "size": {"type": "int", "description": "Brush size", "default": 10},
                    "hardness": {
                        "type": "int",
                        "description": "Brush hardness (0-100)",
                        "default": 100,
                    },
                    "opacity": {
                        "type": "int",
                        "description": "Brush opacity (0-100)",
                        "default": 100,
                    },
                    "flow": {
                        "type": "int",
                        "description": "Brush flow (0-100)",
                        "default": 100,
                    },
                },
            },
            "dot": {
                "description": "Draw a single dot",
                "params": {
                    "x": {"type": "int", "description": "X position"},
                    "y": {"type": "int", "description": "Y position"},
                    "size": {"type": "int", "description": "Dot size"},
                    "color": {"type": "string", "description": "Hex color"},
                },
            },
        },
    },
    "spray": {
        "name": "Airbrush",
        "icon": "blur_on",
        "shortcut": "A",
        "description": "Spray paint effect",
        "actions": {
            "spray": {
                "description": "Spray paint at a point",
                "params": {
                    "x": {"type": "int", "description": "X position"},
                    "y": {"type": "int", "description": "Y position"},
                    "size": {"type": "int", "description": "Spray radius"},
                    "density": {"type": "float", "description": "Particle density"},
                    "color": {"type": "string", "description": "Hex color"},
                    "count": {"type": "int", "description": "Number of particles"},
                },
            },
            "stroke": {
                "description": "Spray along a path",
                "params": {
                    "points": {"type": "array", "description": "Array of [x, y] points"},
                    "size": {"type": "int", "description": "Spray radius"},
                    "density": {"type": "float", "description": "Particle density"},
                    "color": {"type": "string", "description": "Hex color"},
                },
            },
        },
    },
    "eraser": {
        "name": "Eraser",
        "icon": "auto_fix_off",
        "shortcut": "E",
        "description": "Erase pixels to transparency",
        "actions": {
            "stroke": {
                "description": "Erase along a path",
                "params": {
                    "points": {"type": "array", "description": "Array of [x, y] points"},
                    "size": {"type": "int", "description": "Eraser size"},
                },
            },
        },
    },
    "line": {
        "name": "Line",
        "icon": "horizontal_rule",
        "shortcut": "L",
        "description": "Draw straight lines",
        "actions": {
            "draw": {
                "description": "Draw a line",
                "params": {
                    "start": {"type": "array", "description": "[x, y] start point"},
                    "end": {"type": "array", "description": "[x, y] end point"},
                    "color": {"type": "string", "description": "Hex color"},
                    "width": {"type": "int", "description": "Line width"},
                },
            },
        },
    },
    "rect": {
        "name": "Rectangle",
        "icon": "rectangle",
        "shortcut": "R",
        "description": "Draw rectangles",
        "actions": {
            "draw": {
                "description": "Draw a rectangle",
                "params": {
                    "x": {"type": "int", "description": "Left edge"},
                    "y": {"type": "int", "description": "Top edge"},
                    "width": {"type": "int", "description": "Width"},
                    "height": {"type": "int", "description": "Height"},
                    "color": {"type": "string", "description": "Fill color"},
                    "stroke": {"type": "string", "description": "Stroke color"},
                    "strokeWidth": {"type": "int", "description": "Stroke width"},
                },
            },
        },
    },
    "circle": {
        "name": "Ellipse",
        "icon": "circle",
        "shortcut": "C",
        "description": "Draw ellipses and circles",
        "actions": {
            "draw": {
                "description": "Draw an ellipse",
                "params": {
                    "center": {"type": "array", "description": "[x, y] center point"},
                    "radius": {"type": "int", "description": "Radius (for circle)"},
                    "radiusX": {"type": "int", "description": "Horizontal radius"},
                    "radiusY": {"type": "int", "description": "Vertical radius"},
                    "color": {"type": "string", "description": "Fill color"},
                    "stroke": {"type": "string", "description": "Stroke color"},
                    "strokeWidth": {"type": "int", "description": "Stroke width"},
                },
            },
        },
    },
    "polygon": {
        "name": "Polygon",
        "icon": "hexagon",
        "shortcut": "P",
        "description": "Draw polygons",
        "actions": {
            "draw": {
                "description": "Draw a polygon",
                "params": {
                    "points": {"type": "array", "description": "Array of [x, y] vertices"},
                    "color": {"type": "string", "description": "Fill color"},
                    "fill": {"type": "bool", "description": "Fill the polygon"},
                    "stroke": {"type": "string", "description": "Stroke color"},
                    "strokeWidth": {"type": "int", "description": "Stroke width"},
                },
            },
        },
    },
    "fill": {
        "name": "Fill",
        "icon": "format_color_fill",
        "shortcut": "G",
        "description": "Fill connected area with color",
        "actions": {
            "fill": {
                "description": "Flood fill from a point",
                "params": {
                    "point": {"type": "array", "description": "[x, y] start point"},
                    "color": {"type": "string", "description": "Fill color"},
                    "tolerance": {
                        "type": "int",
                        "description": "Color tolerance",
                        "default": 0,
                    },
                },
            },
        },
    },
    "gradient": {
        "name": "Gradient",
        "icon": "gradient",
        "shortcut": "G",
        "description": "Draw color gradients",
        "actions": {
            "draw": {
                "description": "Draw a gradient",
                "params": {
                    "x1": {"type": "int", "description": "Start X"},
                    "y1": {"type": "int", "description": "Start Y"},
                    "x2": {"type": "int", "description": "End X"},
                    "y2": {"type": "int", "description": "End Y"},
                    "type": {
                        "type": "string",
                        "description": "Gradient type: linear, radial",
                        "default": "linear",
                    },
                    "startColor": {"type": "string", "description": "Start color"},
                    "endColor": {"type": "string", "description": "End color"},
                },
            },
        },
    },
    "text": {
        "name": "Text",
        "icon": "text_fields",
        "shortcut": "T",
        "description": "Add text to the image",
        "actions": {
            "draw": {
                "description": "Add text",
                "params": {
                    "text": {"type": "string", "description": "Text content"},
                    "x": {"type": "int", "description": "X position"},
                    "y": {"type": "int", "description": "Y position"},
                    "fontSize": {"type": "int", "description": "Font size in pixels"},
                    "fontFamily": {
                        "type": "string",
                        "description": "Font family",
                        "default": "Arial",
                    },
                    "color": {"type": "string", "description": "Text color"},
                },
            },
        },
    },
    "crop": {
        "name": "Crop",
        "icon": "crop",
        "shortcut": "C",
        "description": "Crop the document",
        "actions": {
            "crop": {
                "description": "Crop to a region",
                "params": {
                    "x": {"type": "int", "description": "Left edge"},
                    "y": {"type": "int", "description": "Top edge"},
                    "width": {"type": "int", "description": "Crop width"},
                    "height": {"type": "int", "description": "Crop height"},
                },
            },
        },
    },
    "eyedropper": {
        "name": "Eyedropper",
        "icon": "colorize",
        "shortcut": "I",
        "description": "Pick colors from the canvas",
        "actions": {
            "pick": {
                "description": "Pick a color",
                "params": {
                    "x": {"type": "int", "description": "X position"},
                    "y": {"type": "int", "description": "Y position"},
                },
            },
        },
    },
}


@router.get("")
async def list_tools() -> dict:
    """List all available tools with their parameters."""
    return {"tools": TOOLS}


@router.get("/{tool_id}")
async def get_tool(tool_id: str) -> dict:
    """Get details for a specific tool."""
    if tool_id not in TOOLS:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")

    return {"tool_id": tool_id, **TOOLS[tool_id]}
