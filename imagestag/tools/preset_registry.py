# Preset Registry - Central location for all filter pipeline presets
"""
Central registry for filter pipeline presets.

Each preset is defined with:
- graph: The FilterGraph node/connection structure (for visual editor)
- dsl: The compact DSL string (equivalent representation)
- inputs: List of source input names with their sample images
- category: Preset category for organization

The DSL string must produce the SAME output as the graph when executed
with the same input images. This equivalence is verified by unit tests.

Usage:
    from imagestag.tools.preset_registry import PRESETS, get_preset

    preset = get_preset('simple_filter_chain')
    graph = preset.to_graph()
    dsl_pipeline = preset.to_pipeline()

    # Both should produce identical output
    result_graph = graph.execute(my_image)
    result_dsl = dsl_pipeline.apply(my_image)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from imagestag.filters import FilterPipeline
    from imagestag.filters.graph import FilterGraph


class PresetCategory(Enum):
    """Categories for organizing presets."""
    BASIC = auto()          # Simple filter chains
    BLEND = auto()          # Image blending/compositing
    DETECTION = auto()      # Object/feature detection
    EFFECTS = auto()        # Visual effects


@dataclass
class PresetInput:
    """Defines an input source for a preset."""
    name: str                           # Source node name (e.g., 'source_a')
    sample_image: str                   # Sample image for testing (e.g., 'astronaut')
    formats: list[str] = field(default_factory=lambda: ['RGB8', 'RGBA8'])


@dataclass
class Preset:
    """A complete preset definition with graph and DSL representations."""

    key: str                            # Unique identifier (e.g., 'simple_filter_chain')
    name: str                           # Human-readable name
    description: str                    # Brief description
    category: PresetCategory            # Category for organization

    # Graph representation (for visual editor)
    graph: dict[str, Any]               # Nodes and connections

    # DSL representation (compact string)
    dsl: str                            # Pipeline DSL string

    # Input specifications
    inputs: list[PresetInput]           # Input sources with sample images

    def to_graph(self) -> 'FilterGraph':
        """Convert preset graph dict to executable FilterGraph."""
        from imagestag.filters.graph import FilterGraph
        return FilterGraph.from_dict(self.graph)

    def to_dsl_graph(self) -> 'FilterGraph':
        """Convert DSL to executable FilterGraph.

        Works for both linear and complex pipelines with named nodes.
        """
        from imagestag.filters.graph import FilterGraph
        source_names = [inp.name for inp in self.inputs]
        return FilterGraph.parse_dsl(self.dsl, sources=source_names)

    def to_pipeline(self) -> 'FilterPipeline':
        """Convert DSL to executable FilterPipeline.

        Note: Only works for linear pipelines (simple_filter_chain, edge_detection).
        Complex presets with branches should use to_dsl_graph() instead.
        """
        from imagestag.filters import FilterPipeline
        return FilterPipeline.parse(self.dsl)

    def is_linear_pipeline(self) -> bool:
        """Check if this preset is a simple linear pipeline (no branches)."""
        # Linear pipelines don't have named nodes [name: ...]
        return '[' not in self.dsl

    def to_markdown(self) -> str:
        """Generate markdown documentation for this preset.

        :returns: Markdown formatted documentation string
        """
        lines = [f'# {self.name}', '']
        lines.append(self.description)
        lines.append('')

        lines.append(f'**Category:** {self.category.name.title()}')
        lines.append('')

        # Inputs
        if self.inputs:
            lines.append('## Inputs')
            lines.append('')
            for inp in self.inputs:
                formats = ', '.join(inp.formats)
                lines.append(f'- **{inp.name}**: {formats}')
            lines.append('')

        # DSL
        lines.append('## DSL')
        lines.append('')
        lines.append('```')
        lines.append(self.dsl)
        lines.append('```')
        lines.append('')

        # Usage
        lines.append('## Usage')
        lines.append('')
        lines.append('```python')
        lines.append('from imagestag.tools.preset_registry import get_preset')
        lines.append('')
        lines.append(f"preset = get_preset('{self.key}')")
        lines.append('')
        if self.is_linear_pipeline():
            lines.append('# As pipeline')
            lines.append('pipeline = preset.to_pipeline()')
            lines.append('result = pipeline.apply(image)')
        else:
            lines.append('# As graph')
            lines.append('graph = preset.to_graph()')
            if len(self.inputs) == 1:
                lines.append('result = graph.execute(image)')
            else:
                input_args = ', '.join(
                    f'{inp.name}=img{i+1}' for i, inp in enumerate(self.inputs)
                )
                lines.append(f'result = graph.execute({input_args})')
        lines.append('```')
        lines.append('')

        # Graph structure
        if 'nodes' in self.graph:
            lines.append('## Graph Structure')
            lines.append('')
            lines.append('```')
            nodes = self.graph['nodes']
            for name, node in nodes.items():
                cls = node.get('class', 'Unknown')
                params = node.get('params', {})
                if params:
                    param_str = ', '.join(f'{k}={v}' for k, v in params.items())
                    lines.append(f'{name}: {cls}({param_str})')
                else:
                    lines.append(f'{name}: {cls}')
            lines.append('```')
            lines.append('')

        return '\n'.join(lines)


# =============================================================================
# PRESET DEFINITIONS
# =============================================================================

# Helper for common editor positions
def _editor(x: int, y: int) -> dict:
    return {"x": x, "y": y}


# -----------------------------------------------------------------------------
# SIMPLE FILTER CHAIN
# -----------------------------------------------------------------------------
SIMPLE_FILTER_CHAIN = Preset(
    key='simple_filter_chain',
    name='Simple Filter Chain',
    description='Apply blur and brightness adjustment to an image',
    category=PresetCategory.BASIC,
    inputs=[
        PresetInput('input', 'astronaut', ['RGB8', 'RGBA8', 'GRAY8']),
    ],
    dsl='blur 2.0; brightness 1.2',
    graph={
        "nodes": {
            "input": {
                "class": "PipelineSource",
                "type": "IMAGE",
                "formats": ["RGB8", "RGBA8", "GRAY8"],
                "placeholder": "samples://images/astronaut",
                "editor": _editor(80, 150),
            },
            "blur": {
                "class": "GaussianBlur",
                "params": {"radius": 2.0},
                "editor": _editor(320, 150),
            },
            "brighten": {
                "class": "Brightness",
                "params": {"factor": 1.2},
                "editor": _editor(560, 150),
            },
            "output": {
                "class": "PipelineOutput",
                "type": "IMAGE",
                "name": "output",
                "editor": _editor(800, 150),
            },
        },
        "connections": [
            {"from": "input", "to": "blur"},
            {"from": "blur", "to": "brighten"},
            {"from": "brighten", "to": "output"},
        ],
    },
)


# -----------------------------------------------------------------------------
# EDGE DETECTION
# -----------------------------------------------------------------------------
EDGE_DETECTION = Preset(
    key='edge_detection',
    name='Edge Detection',
    description='Detect edges using Canny edge detector',
    category=PresetCategory.BASIC,
    inputs=[
        PresetInput('input', 'astronaut', ['RGB8', 'RGBA8', 'GRAY8']),
    ],
    dsl='canny 100 200',
    graph={
        "nodes": {
            "input": {
                "class": "PipelineSource",
                "type": "IMAGE",
                "formats": ["RGB8", "RGBA8", "GRAY8"],
                "placeholder": "samples://images/astronaut",
                "editor": _editor(80, 150),
            },
            "canny": {
                "class": "Canny",
                "params": {"threshold1": 100, "threshold2": 200},
                "editor": _editor(320, 150),
            },
            "output": {
                "class": "PipelineOutput",
                "type": "IMAGE",
                "name": "output",
                "editor": _editor(560, 150),
            },
        },
        "connections": [
            {"from": "input", "to": "canny"},
            {"from": "canny", "to": "output"},
        ],
    },
)


# -----------------------------------------------------------------------------
# RADIAL VIGNETTE
# -----------------------------------------------------------------------------
RADIAL_VIGNETTE = Preset(
    key='radial_vignette',
    name='Radial Vignette',
    description='Apply a radial vignette effect using multiply blend',
    category=PresetCategory.EFFECTS,
    inputs=[
        PresetInput('source', 'astronaut', ['RGB8', 'RGBA8']),
    ],
    # DSL uses named node for vignette generator, then blends with source
    dsl=(
        "[v: imgen radial color_start=#ffffff color_end=#000000 format=rgb]; "
        "blend a=source b=v mode=multiply opacity=0.7"
    ),
    graph={
        "nodes": {
            "source": {
                "class": "PipelineSource",
                "type": "IMAGE",
                "formats": ["RGB8", "RGBA8"],
                "placeholder": "samples://images/astronaut",
                "editor": _editor(80, 150),
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
                "editor": _editor(320, 300),
            },
            "blend": {
                "class": "Blend",
                "params": {"mode": "MULTIPLY", "opacity": 0.7},
                "editor": _editor(560, 150),
            },
            "output": {
                "class": "PipelineOutput",
                "type": "IMAGE",
                "name": "output",
                "editor": _editor(800, 150),
            },
        },
        "connections": [
            {"from": "source", "to": "vignette"},
            {"from": "source", "to": ["blend", "a"]},
            {"from": "vignette", "to": ["blend", "b"]},
            {"from": "blend", "to": "output"},
        ],
    },
)


# -----------------------------------------------------------------------------
# GRADIENT BLEND
# -----------------------------------------------------------------------------
GRADIENT_BLEND = Preset(
    key='gradient_blend',
    name='Gradient Blend',
    description='Blend two images with a linear gradient mask',
    category=PresetCategory.BLEND,
    inputs=[
        PresetInput('source_a', 'astronaut', ['RGB8', 'RGBA8']),
        PresetInput('source_b', 'chelsea', ['RGB8', 'RGBA8']),
    ],
    # DSL: size_match both inputs, generate gradient mask, blend
    dsl=(
        "[m: size_match source_a source_b smaller aspect=fill]; "
        "[g: imgen linear color_start=#000000 color_end=#ffffff format=gray]; "
        "blend a=m.a b=m.b mask=g"
    ),
    graph={
        "nodes": {
            "source_a": {
                "class": "PipelineSource",
                "type": "IMAGE",
                "formats": ["RGB8", "RGBA8"],
                "placeholder": "samples://images/astronaut",
                "editor": _editor(80, 80),
            },
            "source_b": {
                "class": "PipelineSource",
                "type": "IMAGE",
                "formats": ["RGB8", "RGBA8"],
                "placeholder": "samples://images/chelsea",
                "editor": _editor(80, 280),
            },
            "size_match": {
                "class": "SizeMatcher",
                "params": {
                    "mode": "smaller",
                    "aspect": "fill",
                    "crop": "center",
                    "interp": "linear",
                    "fill": "#000000",
                },
                "editor": _editor(320, 120),
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
                "editor": _editor(560, 320),
            },
            "blend": {
                "class": "Blend",
                "params": {"mode": "NORMAL", "opacity": 1.0},
                "editor": _editor(800, 120),
            },
            "output": {
                "class": "PipelineOutput",
                "type": "IMAGE",
                "name": "output",
                "editor": _editor(1040, 120),
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
    },
)


# -----------------------------------------------------------------------------
# FACE DETECTION
# -----------------------------------------------------------------------------
FACE_DETECTION = Preset(
    key='face_detection',
    name='Face Detection',
    description='Detect faces in group photo and draw bounding boxes',
    category=PresetCategory.DETECTION,
    inputs=[
        PresetInput('source', 'group', ['RGB8', 'RGBA8']),
    ],
    dsl=(
        "[f: facedetector scale_factor=1.52 min_neighbors=3 "
        "rotation_range=15 rotation_step=7]; "
        "drawgeometry input=source geometry=f color=#ff0000 thickness=2"
    ),
    graph={
        "nodes": {
            "source": {
                "class": "PipelineSource",
                "type": "IMAGE",
                "formats": ["RGB8", "RGBA8"],
                "placeholder": "samples://images/group",
                "editor": _editor(80, 150),
            },
            "detect_faces": {
                "class": "FaceDetector",
                "params": {
                    "scale_factor": 1.52,
                    "min_neighbors": 3,
                    "rotation_range": 15,
                    "rotation_step": 7,
                },
                "editor": _editor(320, 250),
            },
            "draw_boxes": {
                "class": "DrawGeometry",
                "params": {"color": "#FF0000", "thickness": 2},
                "editor": _editor(560, 150),
            },
            "output": {
                "class": "PipelineOutput",
                "type": "IMAGE",
                "name": "output",
                "editor": _editor(800, 150),
            },
        },
        "connections": [
            {"from": "source", "to": "detect_faces"},
            {"from": "source", "to": ["draw_boxes", "input"]},
            {"from": "detect_faces", "to": ["draw_boxes", "geometry"]},
            {"from": "draw_boxes", "to": "output"},
        ],
    },
)


# -----------------------------------------------------------------------------
# CIRCLE DETECTION
# -----------------------------------------------------------------------------
CIRCLE_DETECTION = Preset(
    key='circle_detection',
    name='Circle Detection',
    description='Detect all 24 coins using tuned Hough circle detection',
    category=PresetCategory.DETECTION,
    inputs=[
        PresetInput('source', 'coins', ['RGB8', 'RGBA8', 'GRAY8']),
    ],
    dsl=(
        "[c: houghcircledetector dp=0.06 min_dist=14.0 param1=230.0 "
        "param2=30.0 min_radius=10 max_radius=40]; "
        "drawgeometry input=source geometry=c color=#ff0000 thickness=2"
    ),
    graph={
        "nodes": {
            "source": {
                "class": "PipelineSource",
                "type": "IMAGE",
                "formats": ["RGB8", "RGBA8", "GRAY8"],
                "placeholder": "samples://images/coins",
                "editor": _editor(80, 150),
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
                "editor": _editor(320, 250),
            },
            "draw_circles": {
                "class": "DrawGeometry",
                "params": {"color": "#FF0000", "thickness": 2},
                "editor": _editor(560, 150),
            },
            "output": {
                "class": "PipelineOutput",
                "type": "IMAGE",
                "name": "output",
                "editor": _editor(800, 150),
            },
        },
        "connections": [
            {"from": "source", "to": "detect_circles"},
            {"from": "source", "to": ["draw_circles", "input"]},
            {"from": "detect_circles", "to": ["draw_circles", "geometry"]},
            {"from": "draw_circles", "to": "output"},
        ],
    },
)


# -----------------------------------------------------------------------------
# FACE BLUR
# -----------------------------------------------------------------------------
FACE_BLUR = Preset(
    key='face_blur',
    name='Face Blur',
    description='Detect faces and blur them for privacy using region pipeline',
    category=PresetCategory.EFFECTS,
    inputs=[
        PresetInput('source', 'group', ['RGB8', 'RGBA8']),
    ],
    dsl=(
        "[f: facedetector scale_factor=1.52 min_neighbors=3 "
        "rotation_range=15 rotation_step=7]; "
        "[e: extractregions input=source geometry=f padding=10]; "
        "[b: blur 15.0]; "
        "mergeregions input=source regions=b blend_edges=false"
    ),
    graph={
        "nodes": {
            "source": {
                "class": "PipelineSource",
                "type": "IMAGE",
                "formats": ["RGB8", "RGBA8"],
                "placeholder": "samples://images/group",
                "editor": _editor(80, 150),
            },
            "detect_faces": {
                "class": "FaceDetector",
                "params": {
                    "scale_factor": 1.52,
                    "min_neighbors": 3,
                    "rotation_range": 15,
                    "rotation_step": 7,
                },
                "editor": _editor(320, 250),
            },
            "extract": {
                "class": "ExtractRegions",
                "params": {"padding": 10},
                "editor": _editor(560, 150),
            },
            "blur_regions": {
                "class": "GaussianBlur",
                "params": {"radius": 15.0},
                "editor": _editor(800, 80),
            },
            "merge": {
                "class": "MergeRegions",
                "params": {"blend_edges": False},
                "editor": _editor(1040, 150),
            },
            "output": {
                "class": "PipelineOutput",
                "type": "IMAGE",
                "name": "output",
                "editor": _editor(1280, 150),
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
    },
)


# =============================================================================
# REGISTRY
# =============================================================================

# All presets in registration order
ALL_PRESETS: list[Preset] = [
    SIMPLE_FILTER_CHAIN,
    EDGE_DETECTION,
    RADIAL_VIGNETTE,
    GRADIENT_BLEND,
    FACE_DETECTION,
    CIRCLE_DETECTION,
    FACE_BLUR,
]

# Dict for lookup by key
PRESETS: dict[str, Preset] = {p.key: p for p in ALL_PRESETS}


def get_preset(key: str) -> Preset | None:
    """Get a preset by key."""
    return PRESETS.get(key)


def get_preset_names() -> list[tuple[str, str]]:
    """Get list of (key, name) tuples for all presets."""
    return [(p.key, p.name) for p in ALL_PRESETS]


def get_presets_by_category(category: PresetCategory) -> list[Preset]:
    """Get all presets in a category."""
    return [p for p in ALL_PRESETS if p.category == category]


def get_linear_presets() -> list[Preset]:
    """Get presets that are simple linear pipelines (testable via DSL execution)."""
    return [p for p in ALL_PRESETS if p.is_linear_pipeline()]
