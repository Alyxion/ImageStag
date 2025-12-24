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
                "size_mode": "SMALLER_WINS",
                "aspect_mode": "FILL",
                "crop_position": "CENTER",
                "interpolation": "LINEAR",
                "fill_color_r": 0,
                "fill_color_g": 0,
                "fill_color_b": 0,
            },
            "editor": {"x": 320, "y": 120},
        },
        "gradient": {
            "class": "ImageGenerator",
            "params": {
                "gradient_type": "LINEAR",
                "angle": 0,
                "color_start": "#000000",
                "color_end": "#FFFFFF",
                "output_format": "GRAY",
                "width": 512,
                "height": 512,
                "center_x": 0.5,
                "center_y": 0.5,
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
        {"from": "source_a", "to": ["size_match", "image_a"]},
        {"from": "source_b", "to": ["size_match", "image_b"]},
        {"from": ["size_match", "output_a"], "to": ["blend", "base"]},
        {"from": ["size_match", "output_b"], "to": ["blend", "overlay"]},
        {"from": ["size_match", "output_b"], "to": "gradient"},
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
            "params": {"sigma": 2.0},
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
        "input": {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8"],
            "placeholder": "samples://images/astronaut",
            "editor": {"x": 80, "y": 150},
        },
        "vignette": {
            "class": "ImageGenerator",
            "params": {
                "gradient_type": "RADIAL",
                "angle": 0,
                "color_start": "#FFFFFF",
                "color_end": "#000000",
                "output_format": "RGB",
                "width": 512,
                "height": 512,
                "center_x": 0.5,
                "center_y": 0.5,
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
        {"from": "input", "to": "vignette"},
        {"from": "input", "to": ["blend", "base"]},
        {"from": "vignette", "to": ["blend", "overlay"]},
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
        "input": {
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
        {"from": "input", "to": "detect_faces"},
        {"from": "input", "to": ["draw_boxes", "image"]},
        {"from": "detect_faces", "to": ["draw_boxes", "geometry"]},
        {"from": "draw_boxes", "to": "output"},
    ],
}

# Preset: Circle Detection - Detect circles using Hough transform (24 coins)
CIRCLE_DETECTION = {
    "name": "Circle Detection",
    "description": "Detect all 24 coins using tuned Hough circle detection",
    "nodes": {
        "input": {
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
        {"from": "input", "to": "detect_circles"},
        {"from": "input", "to": ["draw_circles", "image"]},
        {"from": "detect_circles", "to": ["draw_circles", "geometry"]},
        {"from": "draw_circles", "to": "output"},
    ],
}

# Preset: Face Blur - Detect and blur faces for privacy
FACE_BLUR = {
    "name": "Face Blur",
    "description": "Detect faces and blur them for privacy using region pipeline",
    "nodes": {
        "input": {
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
        {"from": "input", "to": "detect_faces"},
        {"from": "input", "to": ["extract", "image"]},
        {"from": "input", "to": ["merge", "original"]},
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


def get_preset_names() -> list[tuple[str, str]]:
    """Get list of (key, name) tuples for all presets."""
    return [(key, preset["name"]) for key, preset in PRESETS.items()]


def get_preset(key: str) -> dict | None:
    """Get a preset by key."""
    return PRESETS.get(key)
