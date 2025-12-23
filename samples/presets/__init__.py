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
                {"name": "gradient_type", "type": "select", "value": "linear"},
                {"name": "angle", "type": "float", "value": 0},
                {"name": "color_start_r", "type": "int", "value": 0},
                {"name": "color_start_g", "type": "int", "value": 0},
                {"name": "color_start_b", "type": "int", "value": 0},
                {"name": "color_start_a", "type": "int", "value": 255},
                {"name": "color_end_r", "type": "int", "value": 255},
                {"name": "color_end_g", "type": "int", "value": 255},
                {"name": "color_end_b", "type": "int", "value": 255},
                {"name": "color_end_a", "type": "int", "value": 255},
                {"name": "output_format", "type": "select", "value": "GRAY"},
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
                {"name": "mode", "type": "select", "value": "normal"},
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
                {"name": "gradient_type", "type": "select", "value": "radial"},
                {"name": "angle", "type": "float", "value": 0},
                {"name": "color_start_r", "type": "int", "value": 255},
                {"name": "color_start_g", "type": "int", "value": 255},
                {"name": "color_start_b", "type": "int", "value": 255},
                {"name": "color_start_a", "type": "int", "value": 255},
                {"name": "color_end_r", "type": "int", "value": 0},
                {"name": "color_end_g", "type": "int", "value": 0},
                {"name": "color_end_b", "type": "int", "value": 0},
                {"name": "color_end_a", "type": "int", "value": 255},
                {"name": "output_format", "type": "select", "value": "RGB"},
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
                {"name": "mode", "type": "select", "value": "multiply"},
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

# All available presets
PRESETS = {
    "gradient_blend": GRADIENT_BLEND,
    "simple_filter_chain": SIMPLE_FILTER_CHAIN,
    "radial_vignette": RADIAL_VIGNETTE,
    "edge_detection": EDGE_DETECTION,
}

def get_preset_names() -> list[tuple[str, str]]:
    """Get list of (key, name) tuples for all presets."""
    return [(key, preset["name"]) for key, preset in PRESETS.items()]

def get_preset(key: str) -> dict | None:
    """Get a preset by key."""
    return PRESETS.get(key)
