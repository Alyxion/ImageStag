# Graph Presets for Filter Explorer
"""
Pre-defined graph configurations using explicit FilterGraph format.

Preset format:
- nodes: dict of unique_name -> node definition
  - Source nodes: {"class": "PipelineSource", "type": "IMAGE", "formats": [...], "placeholder": "...", "editor": {"x": ..., "y": ...}}
  - Output nodes: {"class": "PipelineOutput", "type": "IMAGE", "name": "output", "editor": {...}}
  - Filter nodes: {"class": "FilterClassName", "params": {name: value}, "editor": {"x": ..., "y": ...}}
- connections: list of connection dicts:
  - {"from": "node", "to": "node"} - default ports (output -> input)
  - {"from": "node", "to": ["node", "port"]} - named to_port
  - {"from": ["node", "port"], "to": ["node", "port"]} - both named
- name: Human-readable preset name
- description: Brief description

Editor metadata (x, y position) is stored in an 'editor' sub-dict within each node
to avoid conflicts with filter parameters that might use x/y.

Source nodes define:
- type: Input data type (IMAGE, IMAGE_LIST, etc.)
- formats: List of supported pixel formats (e.g., ["RGB8", "RGBA8", "GRAY8"])
- placeholder: URI for designer preview (e.g., "samples://images/astronaut")

Node type (filter vs combiner) is derived from the filter registry.
Node names must be unique and descriptive (e.g., "input", "blur", "output").
"""

# Preset: Gradient Blend - Two images blended with a gradient mask
GRADIENT_BLEND = {
    "name": "Gradient Blend",
    "description": "Blend two images with a linear gradient mask",
    "nodes": {
        "source_a": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8"],
            "placeholder": "samples://images/astronaut",
            "editor": {"x": 80, "y": 80},
        },
        "source_b": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8"],
            "placeholder": "samples://images/chelsea",
            "editor": {"x": 80, "y": 280},
        },
        "size_match": {
            "class": "SizeMatcher",
            "params": {
                "mode": "smaller",
                "aspect": "fill",
                "crop": "center",
                "interp": "LINEAR",
                "fill": "#000000",
            },
            "editor": {"x": 320, "y": 120},
        },
        "gradient": {
            "class": "ImageGenerator",
            "params": {
                "gradient_type": "linear",
                "angle": 0,
                "color_start": "#000000",
                "color_end": "#FFFFFF",
                "format": "gray",
                "width": 512,
                "height": 512,
                "cx": 0.5,
                "cy": 0.5,
            },
            "editor": {"x": 560, "y": 320},
        },
        "blend": {
            "class": "Blend",
            "params": {"mode": "NORMAL", "opacity": 1.0},
            "editor": {"x": 800, "y": 120},
        },
        "output": {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
            "editor": {"x": 1040, "y": 120},
        },
    },
    "connections": [
        {"from": "source_a", "to": ["size_match", "a"]},
        {"from": "source_b", "to": ["size_match", "b"]},
        {"from": ["size_match", "a"], "to": ["blend", "a"]},
        {"from": ["size_match", "b"], "to": ["blend", "b"]},
        {"from": ["size_match", "b"], "to": "gradient"},
        {"from": "gradient", "to": ["blend", "mask"]},
        {"from": "blend", "to": "output"},
    ],
}

# Preset: Simple Filter Chain - Single image with blur and brightness
SIMPLE_FILTER_CHAIN = {
    "name": "Simple Filter Chain",
    "description": "Apply blur and brightness adjustment to an image",
    "nodes": {
        "input": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8", "GRAY8"],
            "placeholder": "samples://images/astronaut",
            "editor": {"x": 80, "y": 150},
        },
        "blur": {
            "class": "GaussianBlur",
            "params": {"radius": 2.0},
            "editor": {"x": 320, "y": 150},
        },
        "brighten": {
            "class": "Brightness",
            "params": {"factor": 1.2},
            "editor": {"x": 560, "y": 150},
        },
        "output": {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
            "editor": {"x": 800, "y": 150},
        },
    },
    "connections": [
        {"from": "input", "to": "blur"},
        {"from": "blur", "to": "brighten"},
        {"from": "brighten", "to": "output"},
    ],
}

# Preset: Radial Vignette - Apply radial gradient as vignette
RADIAL_VIGNETTE = {
    "name": "Radial Vignette",
    "description": "Apply a radial vignette effect using multiply blend",
    "nodes": {
        "source": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8"],
            "placeholder": "samples://images/astronaut",
            "editor": {"x": 80, "y": 150},
        },
        "vignette": {
            "class": "ImageGenerator",
            "params": {
                "gradient_type": "radial",
                "angle": 0,
                "color_start": "#FFFFFF",
                "color_end": "#000000",
                "format": "rgb",
                "width": 512,
                "height": 512,
                "cx": 0.5,
                "cy": 0.5,
            },
            "editor": {"x": 320, "y": 300},
        },
        "blend": {
            "class": "Blend",
            "params": {"mode": "MULTIPLY", "opacity": 0.7},
            "editor": {"x": 560, "y": 150},
        },
        "output": {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
            "editor": {"x": 800, "y": 150},
        },
    },
    "connections": [
        {"from": "source", "to": "vignette"},
        {"from": "source", "to": ["blend", "a"]},
        {"from": "vignette", "to": ["blend", "b"]},
        {"from": "blend", "to": "output"},
    ],
}

# Preset: Edge Detection - Canny edge detection
EDGE_DETECTION = {
    "name": "Edge Detection",
    "description": "Detect edges using Canny edge detector",
    "nodes": {
        "input": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8", "GRAY8"],
            "placeholder": "samples://images/astronaut",
            "editor": {"x": 80, "y": 150},
        },
        "canny": {
            "class": "Canny",
            "params": {"threshold1": 100, "threshold2": 200},
            "editor": {"x": 320, "y": 150},
        },
        "output": {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
            "editor": {"x": 560, "y": 150},
        },
    },
    "connections": [
        {"from": "input", "to": "canny"},
        {"from": "canny", "to": "output"},
    ],
}

# Preset: Face Detection - Detect faces and draw bounding boxes
FACE_DETECTION = {
    "name": "Face Detection",
    "description": "Detect faces in group photo and draw bounding boxes",
    "nodes": {
        "source": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8"],
            "placeholder": "samples://images/group",
            "editor": {"x": 80, "y": 150},
        },
        "detect_faces": {
            "class": "FaceDetector",
            "params": {
                "scale_factor": 1.52,
                "min_neighbors": 3,
                "rotation_range": 15,
                "rotation_step": 7,
            },
            "editor": {"x": 320, "y": 250},
        },
        "draw_boxes": {
            "class": "DrawGeometry",
            "params": {"color": "#FF0000", "thickness": 2},
            "editor": {"x": 560, "y": 150},
        },
        "output": {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
            "editor": {"x": 800, "y": 150},
        },
    },
    "connections": [
        {"from": "source", "to": "detect_faces"},
        {"from": "source", "to": ["draw_boxes", "input"]},
        {"from": "detect_faces", "to": ["draw_boxes", "geometry"]},
        {"from": "draw_boxes", "to": "output"},
    ],
}

# Preset: Circle Detection - Detect circles using Hough transform (24 coins)
CIRCLE_DETECTION = {
    "name": "Circle Detection",
    "description": "Detect all 24 coins using tuned Hough circle detection",
    "nodes": {
        "source": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8", "GRAY8"],
            "placeholder": "samples://images/coins",
            "editor": {"x": 80, "y": 150},
        },
        "detect_circles": {
            "class": "HoughCircleDetector",
            "params": {
                "dp": 0.06,
                "min_dist": 14.0,
                "param1": 230.0,
                "param2": 30.0,
                "min_radius": 10,
                "max_radius": 40,
            },
            "editor": {"x": 320, "y": 250},
        },
        "draw_circles": {
            "class": "DrawGeometry",
            "params": {"color": "#FF0000", "thickness": 2},
            "editor": {"x": 560, "y": 150},
        },
        "output": {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
            "editor": {"x": 800, "y": 150},
        },
    },
    "connections": [
        {"from": "source", "to": "detect_circles"},
        {"from": "source", "to": ["draw_circles", "input"]},
        {"from": "detect_circles", "to": ["draw_circles", "geometry"]},
        {"from": "draw_circles", "to": "output"},
    ],
}

# Preset: Face Blur - Detect and blur faces for privacy
FACE_BLUR = {
    "name": "Face Blur",
    "description": "Detect faces and blur them for privacy using region pipeline",
    "nodes": {
        "source": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8"],
            "placeholder": "samples://images/group",
            "editor": {"x": 80, "y": 150},
        },
        "detect_faces": {
            "class": "FaceDetector",
            "params": {
                "scale_factor": 1.52,
                "min_neighbors": 3,
                "rotation_range": 15,
                "rotation_step": 7,
            },
            "editor": {"x": 320, "y": 250},
        },
        "extract": {
            "class": "ExtractRegions",
            "params": {"padding": 10},
            "editor": {"x": 560, "y": 150},
        },
        "blur_regions": {
            "class": "GaussianBlur",
            "params": {"radius": 15.0},
            "editor": {"x": 800, "y": 80},
        },
        "merge": {
            "class": "MergeRegions",
            "params": {"blend_edges": False},
            "editor": {"x": 1040, "y": 150},
        },
        "output": {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
            "editor": {"x": 1280, "y": 150},
        },
    },
    "connections": [
        {"from": "source", "to": "detect_faces"},
        {"from": "source", "to": ["extract", "input"]},
        {"from": "source", "to": ["merge", "input"]},
        {"from": "detect_faces", "to": ["extract", "geometry"]},
        {"from": "extract", "to": "blur_regions"},
        {"from": "blur_regions", "to": ["merge", "regions"]},
        {"from": "merge", "to": "output"},
    ],
}

# All available presets
PRESETS = {
    "gradient_blend": GRADIENT_BLEND,
    "simple_filter_chain": SIMPLE_FILTER_CHAIN,
    "radial_vignette": RADIAL_VIGNETTE,
    "edge_detection": EDGE_DETECTION,
    "face_detection": FACE_DETECTION,
    "face_blur": FACE_BLUR,
    "circle_detection": CIRCLE_DETECTION,
}

# DSL string representations for presets
# These are equivalent to the graph definitions above
#
# DSL Syntax:
#   - `;` or newline separates statements
#   - `[name: filter args]` defines a named node
#   - `name` or `name.port` references a node output
#   - `source` is the implicit first input
#   - `other` is the implicit second input (for 2-input pipelines)
#   - Positional args: `blur 5`, `canny 100 200`
#   - Keyword args: `mode=multiply`, `color=#ff0000`

PRESET_DSL = {
    # Simple Filter Chain: input -> blur -> brightness -> output
    # Linear pipeline - just filter sequence
    "simple_filter_chain": "blur 2.0; brightness 1.2",

    # Edge Detection: input -> canny -> output
    # Single filter
    "edge_detection": "canny 100 200",

    # Radial Vignette: source -> [vignette generator] -> blend(source, vignette)
    # Uses source for sizing the vignette generator
    "radial_vignette": (
        "[v: imgen radial color_start=#ffffff color_end=#000000 format=rgb]; "
        "blend a=source b=v mode=multiply opacity=0.7"
    ),

    # Gradient Blend: two inputs -> size_match -> gradient -> blend
    "gradient_blend": (
        "[m: size_match source_a source_b smaller aspect=fill]; "
        "[g: imgen linear color_start=#000000 color_end=#ffffff format=gray]; "
        "blend a=m.a b=m.b mask=g"
    ),

    # Face Detection: source -> detect -> draw
    "face_detection": (
        "[f: facedetector scale_factor=1.52 min_neighbors=3 "
        "rotation_range=15 rotation_step=7]; "
        "drawgeometry input=source geometry=f color=#ff0000 thickness=2"
    ),

    # Circle Detection: source -> detect -> draw
    "circle_detection": (
        "[c: houghcircledetector dp=0.06 min_dist=14.0 param1=230.0 "
        "param2=30.0 min_radius=10 max_radius=40]; "
        "drawgeometry input=source geometry=c color=#ff0000 thickness=2"
    ),

    # Face Blur: source -> detect -> extract -> blur -> merge
    "face_blur": (
        "[f: facedetector scale_factor=1.52 min_neighbors=3 "
        "rotation_range=15 rotation_step=7]; "
        "[e: extractregions input=source geometry=f padding=10]; "
        "[b: blur 15.0]; "
        "mergeregions input=source regions=b blend_edges=false"
    ),
}


def get_preset_dsl(key: str) -> str | None:
    """Get the DSL string for a preset."""
    return PRESET_DSL.get(key)


def get_preset_names() -> list[tuple[str, str]]:
    """Get list of (key, name) tuples for all presets."""
    return [(key, preset["name"]) for key, preset in PRESETS.items()]


def get_preset(key: str) -> dict | None:
    """Get a preset by key."""
    return PRESETS.get(key)
