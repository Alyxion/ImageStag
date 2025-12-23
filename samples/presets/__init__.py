# Graph Presets for Filter Explorer
"""
Pre-defined graph configurations that can be quickly loaded.
"""

# Preset: Gradient Blend - Two images blended with a gradient mask
GRADIENT_BLEND = {
    "name": "Gradient Blend",
    "description": "Blend two images with a linear gradient mask",
    "nodes": {
        "1": {
            "type": "source",
            "name": "Source A",
            "filterName": None,
            "params": [{"name": "image", "type": "select", "value": "astronaut"}],
            "inputPorts": [],
            "outputPorts": [{"name": "output"}],
            "pos_x": 80,
            "pos_y": 80
        },
        "2": {
            "type": "source",
            "name": "Source B",
            "filterName": None,
            "params": [{"name": "image", "type": "select", "value": "chelsea"}],
            "inputPorts": [],
            "outputPorts": [{"name": "output"}],
            "pos_x": 80,
            "pos_y": 280
        },
        "3": {
            "type": "combiner",
            "name": "SizeMatcher",
            "filterName": "SizeMatcher",
            "params": [
                {"name": "size_mode", "type": "select", "value": "smaller_wins"},
                {"name": "aspect_mode", "type": "select", "value": "fill"},
                {"name": "crop_position", "type": "select", "value": "center"},
                {"name": "interpolation", "type": "select", "value": "LINEAR"},
                {"name": "fill_color_r", "type": "int", "value": 0},
                {"name": "fill_color_g", "type": "int", "value": 0},
                {"name": "fill_color_b", "type": "int", "value": 0}
            ],
            "inputPorts": [{"name": "image_a"}, {"name": "image_b"}],
            "outputPorts": [{"name": "output_a"}, {"name": "output_b"}],
            "pos_x": 320,
            "pos_y": 120
        },
        "4": {
            "type": "filter",
            "name": "ImageGenerator",
            "filterName": "ImageGenerator",
            "params": [
                {"name": "gradient_type", "type": "select", "value": "linear", "options": ["solid", "linear", "radial"]},
                {"name": "angle", "type": "float", "value": 0},
                {"name": "color_start", "type": "color", "value": "#000000"},
                {"name": "color_end", "type": "color", "value": "#FFFFFF"},
                {"name": "output_format", "type": "select", "value": "gray", "options": ["gray", "rgb", "rgba"]},
                {"name": "width", "type": "int", "value": 512},
                {"name": "height", "type": "int", "value": 512},
                {"name": "center_x", "type": "float", "value": 0.5},
                {"name": "center_y", "type": "float", "value": 0.5}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 560,
            "pos_y": 320
        },
        "5": {
            "type": "combiner",
            "name": "Blend",
            "filterName": "Blend",
            "params": [
                {"name": "mode", "type": "select", "value": "NORMAL"},
                {"name": "opacity", "type": "float", "value": 1.0, "min": 0, "max": 1, "step": 0.05}
            ],
            "inputPorts": [{"name": "base"}, {"name": "overlay"}, {"name": "mask", "optional": True}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 800,
            "pos_y": 120
        },
        "6": {
            "type": "output",
            "name": "Output",
            "filterName": None,
            "params": [],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [],
            "pos_x": 1040,
            "pos_y": 120
        }
    },
    "connections": [
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 0, "to_port_name": "image_a"},
        {"from_node": "2", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 1, "to_port_name": "image_b"},
        {"from_node": "3", "from_output": 0, "from_port_name": "output_a", "to_node": "5", "to_input": 0, "to_port_name": "base"},
        {"from_node": "3", "from_output": 1, "from_port_name": "output_b", "to_node": "5", "to_input": 1, "to_port_name": "overlay"},
        {"from_node": "3", "from_output": 1, "from_port_name": "output_b", "to_node": "4", "to_input": 0, "to_port_name": "input"},
        {"from_node": "4", "from_output": 0, "from_port_name": "output", "to_node": "5", "to_input": 2, "to_port_name": "mask"},
        {"from_node": "5", "from_output": 0, "from_port_name": "output", "to_node": "6", "to_input": 0, "to_port_name": "input"}
    ]
}

# Preset: Simple Filter Chain - Single image with blur and brightness
SIMPLE_FILTER_CHAIN = {
    "name": "Simple Filter Chain",
    "description": "Apply blur and brightness adjustment to an image",
    "nodes": {
        "1": {
            "type": "source",
            "name": "Source A",
            "filterName": None,
            "params": [{"name": "image", "type": "select", "value": "astronaut"}],
            "inputPorts": [],
            "outputPorts": [{"name": "output"}],
            "pos_x": 80,
            "pos_y": 150
        },
        "2": {
            "type": "filter",
            "name": "GaussianBlur",
            "filterName": "GaussianBlur",
            "params": [
                {"name": "sigma", "type": "float", "value": 2.0, "min": 0.1, "max": 10, "step": 0.1}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 320,
            "pos_y": 150
        },
        "3": {
            "type": "filter",
            "name": "Brightness",
            "filterName": "Brightness",
            "params": [
                {"name": "factor", "type": "float", "value": 1.2, "min": 0, "max": 3, "step": 0.1}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 560,
            "pos_y": 150
        },
        "4": {
            "type": "output",
            "name": "Output",
            "filterName": None,
            "params": [],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [],
            "pos_x": 800,
            "pos_y": 150
        }
    },
    "connections": [
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "2", "to_input": 0, "to_port_name": "input"},
        {"from_node": "2", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 0, "to_port_name": "input"},
        {"from_node": "3", "from_output": 0, "from_port_name": "output", "to_node": "4", "to_input": 0, "to_port_name": "input"}
    ]
}

# Preset: Radial Vignette - Apply radial gradient as vignette
RADIAL_VIGNETTE = {
    "name": "Radial Vignette",
    "description": "Apply a radial vignette effect using multiply blend",
    "nodes": {
        "1": {
            "type": "source",
            "name": "Source A",
            "filterName": None,
            "params": [{"name": "image", "type": "select", "value": "astronaut"}],
            "inputPorts": [],
            "outputPorts": [{"name": "output"}],
            "pos_x": 80,
            "pos_y": 150
        },
        "2": {
            "type": "filter",
            "name": "ImageGenerator",
            "filterName": "ImageGenerator",
            "params": [
                {"name": "gradient_type", "type": "select", "value": "radial", "options": ["solid", "linear", "radial"]},
                {"name": "angle", "type": "float", "value": 0},
                {"name": "color_start", "type": "color", "value": "#FFFFFF"},
                {"name": "color_end", "type": "color", "value": "#000000"},
                {"name": "output_format", "type": "select", "value": "rgb", "options": ["gray", "rgb", "rgba"]},
                {"name": "width", "type": "int", "value": 512},
                {"name": "height", "type": "int", "value": 512},
                {"name": "center_x", "type": "float", "value": 0.5},
                {"name": "center_y", "type": "float", "value": 0.5}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 320,
            "pos_y": 300
        },
        "3": {
            "type": "combiner",
            "name": "Blend",
            "filterName": "Blend",
            "params": [
                {"name": "mode", "type": "select", "value": "MULTIPLY"},
                {"name": "opacity", "type": "float", "value": 0.7, "min": 0, "max": 1, "step": 0.05}
            ],
            "inputPorts": [{"name": "base"}, {"name": "overlay"}, {"name": "mask", "optional": True}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 560,
            "pos_y": 150
        },
        "4": {
            "type": "output",
            "name": "Output",
            "filterName": None,
            "params": [],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [],
            "pos_x": 800,
            "pos_y": 150
        }
    },
    "connections": [
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "2", "to_input": 0, "to_port_name": "input"},
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 0, "to_port_name": "base"},
        {"from_node": "2", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 1, "to_port_name": "overlay"},
        {"from_node": "3", "from_output": 0, "from_port_name": "output", "to_node": "4", "to_input": 0, "to_port_name": "input"}
    ]
}

# Preset: Edge Detection - Canny edge detection
EDGE_DETECTION = {
    "name": "Edge Detection",
    "description": "Detect edges using Canny edge detector",
    "nodes": {
        "1": {
            "type": "source",
            "name": "Source A",
            "filterName": None,
            "params": [{"name": "image", "type": "select", "value": "astronaut"}],
            "inputPorts": [],
            "outputPorts": [{"name": "output"}],
            "pos_x": 80,
            "pos_y": 150
        },
        "2": {
            "type": "filter",
            "name": "Canny",
            "filterName": "Canny",
            "params": [
                {"name": "threshold1", "type": "float", "value": 100, "min": 0, "max": 255, "step": 1},
                {"name": "threshold2", "type": "float", "value": 200, "min": 0, "max": 255, "step": 1}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 320,
            "pos_y": 150
        },
        "3": {
            "type": "output",
            "name": "Output",
            "filterName": None,
            "params": [],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [],
            "pos_x": 560,
            "pos_y": 150
        }
    },
    "connections": [
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "2", "to_input": 0, "to_port_name": "input"},
        {"from_node": "2", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 0, "to_port_name": "input"}
    ]
}

# Preset: Face Detection - Detect faces and draw bounding boxes
FACE_DETECTION = {
    "name": "Face Detection",
    "description": "Detect faces in group photo and draw bounding boxes",
    "nodes": {
        "1": {
            "type": "source",
            "name": "Source A",
            "filterName": None,
            "params": [{"name": "image", "type": "select", "value": "group"}],
            "inputPorts": [],
            "outputPorts": [{"name": "output"}],
            "pos_x": 80,
            "pos_y": 150
        },
        "2": {
            "type": "filter",
            "name": "FaceDetector",
            "filterName": "FaceDetector",
            "params": [
                {"name": "scale_factor", "type": "float", "value": 1.52, "min": 1.01, "max": 2.0, "step": 0.05},
                {"name": "min_neighbors", "type": "int", "value": 3, "min": 1, "max": 10},
                {"name": "rotation_range", "type": "int", "value": 15, "min": 0, "max": 30, "step": 5},
                {"name": "rotation_step", "type": "int", "value": 7, "min": 1, "max": 15, "step": 1}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output", "type": "geometry"}],
            "pos_x": 320,
            "pos_y": 250
        },
        "3": {
            "type": "combiner",
            "name": "DrawGeometry",
            "filterName": "DrawGeometry",
            "params": [
                {"name": "use_geometry_styles", "type": "boolean", "value": True},
                {"name": "color", "type": "color", "value": "#FF0000"},
                {"name": "thickness", "type": "int", "value": 2, "min": 1, "max": 10}
            ],
            "inputPorts": [{"name": "image"}, {"name": "geometry"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 560,
            "pos_y": 150
        },
        "4": {
            "type": "output",
            "name": "Output",
            "filterName": None,
            "params": [],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [],
            "pos_x": 800,
            "pos_y": 150
        }
    },
    "connections": [
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "2", "to_input": 0, "to_port_name": "input"},
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 0, "to_port_name": "image"},
        {"from_node": "2", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 1, "to_port_name": "geometry"},
        {"from_node": "3", "from_output": 0, "from_port_name": "output", "to_node": "4", "to_input": 0, "to_port_name": "input"}
    ]
}

# Preset: Circle Detection - Detect circles using Hough transform (24 coins)
CIRCLE_DETECTION = {
    "name": "Circle Detection",
    "description": "Detect all 24 coins using tuned Hough circle detection",
    "nodes": {
        "1": {
            "type": "source",
            "name": "Source A",
            "filterName": None,
            "params": [{"name": "image", "type": "select", "value": "coins"}],
            "inputPorts": [],
            "outputPorts": [{"name": "output"}],
            "pos_x": 80,
            "pos_y": 150
        },
        "2": {
            "type": "filter",
            "name": "HoughCircleDetector",
            "filterName": "HoughCircleDetector",
            "params": [
                {"name": "dp", "type": "float", "value": 0.06, "min": 0.01, "max": 2.0, "step": 0.01},
                {"name": "min_dist", "type": "float", "value": 14.0, "min": 1, "max": 100, "step": 1},
                {"name": "param1", "type": "float", "value": 230.0, "min": 10, "max": 300, "step": 10},
                {"name": "param2", "type": "float", "value": 30.0, "min": 5, "max": 100, "step": 5},
                {"name": "min_radius", "type": "int", "value": 10, "min": 0, "max": 100, "step": 1},
                {"name": "max_radius", "type": "int", "value": 40, "min": 0, "max": 200, "step": 1}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output", "type": "geometry"}],
            "pos_x": 320,
            "pos_y": 250
        },
        "3": {
            "type": "combiner",
            "name": "DrawGeometry",
            "filterName": "DrawGeometry",
            "params": [
                {"name": "use_geometry_styles", "type": "boolean", "value": True},
                {"name": "color", "type": "color", "value": "#FF0000"},
                {"name": "thickness", "type": "int", "value": 2, "min": 1, "max": 10}
            ],
            "inputPorts": [{"name": "image"}, {"name": "geometry"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 560,
            "pos_y": 150
        },
        "4": {
            "type": "output",
            "name": "Output",
            "filterName": None,
            "params": [],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [],
            "pos_x": 800,
            "pos_y": 150
        }
    },
    "connections": [
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "2", "to_input": 0, "to_port_name": "input"},
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 0, "to_port_name": "image"},
        {"from_node": "2", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 1, "to_port_name": "geometry"},
        {"from_node": "3", "from_output": 0, "from_port_name": "output", "to_node": "4", "to_input": 0, "to_port_name": "input"}
    ]
}

# Preset: Face Blur - Detect and blur faces for privacy
FACE_BLUR = {
    "name": "Face Blur",
    "description": "Detect faces and blur them for privacy using region pipeline",
    "nodes": {
        "1": {
            "type": "source",
            "name": "Source A",
            "filterName": None,
            "params": [{"name": "image", "type": "select", "value": "group"}],
            "inputPorts": [],
            "outputPorts": [{"name": "output"}],
            "pos_x": 80,
            "pos_y": 150
        },
        "2": {
            "type": "filter",
            "name": "FaceDetector",
            "filterName": "FaceDetector",
            "params": [
                {"name": "scale_factor", "type": "float", "value": 1.52, "min": 1.01, "max": 2.0, "step": 0.01},
                {"name": "min_neighbors", "type": "int", "value": 3, "min": 1, "max": 10},
                {"name": "rotation_range", "type": "int", "value": 15, "min": 0, "max": 30, "step": 5},
                {"name": "rotation_step", "type": "int", "value": 7, "min": 1, "max": 15, "step": 1}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output", "type": "geometry"}],
            "pos_x": 320,
            "pos_y": 250
        },
        "3": {
            "type": "combiner",
            "name": "ExtractRegions",
            "filterName": "ExtractRegions",
            "params": [
                {"name": "padding", "type": "int", "value": 10, "min": 0, "max": 50}
            ],
            "inputPorts": [{"name": "image"}, {"name": "geometry"}],
            "outputPorts": [{"name": "output", "type": "image_list"}],
            "pos_x": 560,
            "pos_y": 150
        },
        "4": {
            "type": "filter",
            "name": "GaussianBlur",
            "filterName": "GaussianBlur",
            "params": [
                {"name": "radius", "type": "float", "value": 15.0, "min": 0.1, "max": 30, "step": 0.5}
            ],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 800,
            "pos_y": 80
        },
        "5": {
            "type": "combiner",
            "name": "MergeRegions",
            "filterName": "MergeRegions",
            "params": [
                {"name": "blend_edges", "type": "bool", "value": False}
            ],
            "inputPorts": [{"name": "original"}, {"name": "regions", "type": "image_list"}],
            "outputPorts": [{"name": "output"}],
            "pos_x": 1040,
            "pos_y": 150
        },
        "6": {
            "type": "output",
            "name": "Output",
            "filterName": None,
            "params": [],
            "inputPorts": [{"name": "input"}],
            "outputPorts": [],
            "pos_x": 1280,
            "pos_y": 150
        }
    },
    "connections": [
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "2", "to_input": 0, "to_port_name": "input"},
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 0, "to_port_name": "image"},
        {"from_node": "1", "from_output": 0, "from_port_name": "output", "to_node": "5", "to_input": 0, "to_port_name": "original"},
        {"from_node": "2", "from_output": 0, "from_port_name": "output", "to_node": "3", "to_input": 1, "to_port_name": "geometry"},
        {"from_node": "3", "from_output": 0, "from_port_name": "output", "to_node": "4", "to_input": 0, "to_port_name": "input"},
        {"from_node": "4", "from_output": 0, "from_port_name": "output", "to_node": "5", "to_input": 1, "to_port_name": "regions"},
        {"from_node": "5", "from_output": 0, "from_port_name": "output", "to_node": "6", "to_input": 0, "to_port_name": "input"}
    ]
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
