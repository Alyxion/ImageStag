"""Layer effects API endpoints - list available effect types."""

from fastapi import APIRouter

router = APIRouter(prefix="/effects", tags=["effects"])


# Available layer effect types and their parameters
EFFECTS = {
    "dropShadow": {
        "name": "Drop Shadow",
        "description": "Shadow behind the layer",
        "expandsCanvas": True,
        "params": {
            "offsetX": {
                "type": "int",
                "description": "Horizontal offset in pixels",
                "default": 5,
            },
            "offsetY": {
                "type": "int",
                "description": "Vertical offset in pixels",
                "default": 5,
            },
            "blur": {
                "type": "int",
                "description": "Blur radius in pixels",
                "default": 10,
            },
            "spread": {
                "type": "int",
                "description": "Spread distance in pixels",
                "default": 0,
            },
            "color": {
                "type": "string",
                "description": "Shadow color (#RRGGBB)",
                "default": "#000000",
            },
            "colorOpacity": {
                "type": "float",
                "description": "Shadow opacity (0.0-1.0)",
                "default": 0.75,
            },
        },
    },
    "innerShadow": {
        "name": "Inner Shadow",
        "description": "Shadow inside the layer edges",
        "expandsCanvas": False,
        "params": {
            "offsetX": {
                "type": "int",
                "description": "Horizontal offset in pixels",
                "default": 5,
            },
            "offsetY": {
                "type": "int",
                "description": "Vertical offset in pixels",
                "default": 5,
            },
            "blur": {
                "type": "int",
                "description": "Blur radius in pixels",
                "default": 10,
            },
            "choke": {
                "type": "int",
                "description": "Choke distance in pixels",
                "default": 0,
            },
            "color": {
                "type": "string",
                "description": "Shadow color (#RRGGBB)",
                "default": "#000000",
            },
            "colorOpacity": {
                "type": "float",
                "description": "Shadow opacity (0.0-1.0)",
                "default": 0.75,
            },
        },
    },
    "outerGlow": {
        "name": "Outer Glow",
        "description": "Glow radiating outward from the layer",
        "expandsCanvas": True,
        "params": {
            "blur": {
                "type": "int",
                "description": "Blur radius in pixels",
                "default": 10,
            },
            "spread": {
                "type": "int",
                "description": "Spread distance in pixels",
                "default": 0,
            },
            "color": {
                "type": "string",
                "description": "Glow color (#RRGGBB)",
                "default": "#FFFF00",
            },
            "colorOpacity": {
                "type": "float",
                "description": "Glow opacity (0.0-1.0)",
                "default": 0.75,
            },
        },
    },
    "innerGlow": {
        "name": "Inner Glow",
        "description": "Glow radiating inward from edges",
        "expandsCanvas": False,
        "params": {
            "blur": {
                "type": "int",
                "description": "Blur radius in pixels",
                "default": 10,
            },
            "choke": {
                "type": "int",
                "description": "Choke distance in pixels",
                "default": 0,
            },
            "color": {
                "type": "string",
                "description": "Glow color (#RRGGBB)",
                "default": "#FFFF00",
            },
            "colorOpacity": {
                "type": "float",
                "description": "Glow opacity (0.0-1.0)",
                "default": 0.75,
            },
            "source": {
                "type": "string",
                "description": "Glow source: 'center' or 'edge'",
                "default": "edge",
            },
        },
    },
    "bevelEmboss": {
        "name": "Bevel & Emboss",
        "description": "3D raised or sunken appearance",
        "expandsCanvas": False,  # Only 'outer' style expands
        "params": {
            "style": {
                "type": "string",
                "description": "Style: outer, inner, emboss, pillow",
                "default": "inner",
            },
            "depth": {
                "type": "int",
                "description": "Effect depth (1-1000)",
                "default": 100,
            },
            "direction": {
                "type": "string",
                "description": "Direction: up or down",
                "default": "up",
            },
            "size": {
                "type": "int",
                "description": "Size in pixels",
                "default": 5,
            },
            "soften": {
                "type": "int",
                "description": "Soften amount",
                "default": 0,
            },
            "angle": {
                "type": "int",
                "description": "Light angle in degrees",
                "default": 120,
            },
            "altitude": {
                "type": "int",
                "description": "Light altitude in degrees",
                "default": 30,
            },
        },
    },
    "stroke": {
        "name": "Stroke",
        "description": "Outline around layer content",
        "expandsCanvas": True,  # Only 'outside' and 'center' expand
        "params": {
            "size": {
                "type": "int",
                "description": "Stroke width in pixels",
                "default": 3,
            },
            "position": {
                "type": "string",
                "description": "Position: outside, inside, center",
                "default": "outside",
            },
            "color": {
                "type": "string",
                "description": "Stroke color (#RRGGBB)",
                "default": "#000000",
            },
            "colorOpacity": {
                "type": "float",
                "description": "Stroke opacity (0.0-1.0)",
                "default": 1.0,
            },
        },
    },
    "colorOverlay": {
        "name": "Color Overlay",
        "description": "Solid color overlay on the layer",
        "expandsCanvas": False,
        "params": {
            "color": {
                "type": "string",
                "description": "Overlay color (#RRGGBB)",
                "default": "#FF0000",
            },
            "colorOpacity": {
                "type": "float",
                "description": "Color opacity (0.0-1.0)",
                "default": 1.0,
            },
        },
    },
    "gradientOverlay": {
        "name": "Gradient Overlay",
        "description": "Gradient fill overlay on the layer",
        "expandsCanvas": False,
        "params": {
            "gradient": {
                "type": "array",
                "description": "Gradient stops [{position: 0.0-1.0, color: '#RRGGBB'}]",
                "default": [
                    {"position": 0.0, "color": "#000000"},
                    {"position": 1.0, "color": "#FFFFFF"},
                ],
            },
            "style": {
                "type": "string",
                "description": "Style: linear, radial, angle, reflected, diamond",
                "default": "linear",
            },
            "angle": {
                "type": "float",
                "description": "Gradient angle in degrees",
                "default": 90.0,
            },
            "scaleX": {
                "type": "float",
                "description": "Horizontal scale percentage (10-200)",
                "default": 100,
            },
            "scaleY": {
                "type": "float",
                "description": "Vertical scale percentage (10-200)",
                "default": 100,
            },
            "offsetX": {
                "type": "float",
                "description": "Horizontal offset percentage (-100 to 100)",
                "default": 0,
            },
            "offsetY": {
                "type": "float",
                "description": "Vertical offset percentage (-100 to 100)",
                "default": 0,
            },
            "reverse": {
                "type": "bool",
                "description": "Reverse gradient direction",
                "default": False,
            },
        },
    },
}

# Common parameters for all effects
COMMON_PARAMS = {
    "enabled": {
        "type": "bool",
        "description": "Whether the effect is enabled",
        "default": True,
    },
    "blendMode": {
        "type": "string",
        "description": "Blend mode for the effect",
        "default": "normal",
    },
    "opacity": {
        "type": "float",
        "description": "Effect opacity (0.0-1.0)",
        "default": 1.0,
    },
}


@router.get("")
async def list_effects() -> dict:
    """List all available layer effect types with their parameters."""
    return {
        "effects": EFFECTS,
        "common_params": COMMON_PARAMS,
    }


@router.get("/{effect_type}")
async def get_effect(effect_type: str) -> dict:
    """Get details for a specific effect type."""
    if effect_type not in EFFECTS:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404, detail=f"Effect type '{effect_type}' not found"
        )

    return {
        "effect_type": effect_type,
        **EFFECTS[effect_type],
        "common_params": COMMON_PARAMS,
    }
