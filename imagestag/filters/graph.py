# ImageStag Filters - Filter Graph
"""
FilterGraph for branching and combining filter operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, ClassVar, TYPE_CHECKING
import re

from pydantic import Field, field_validator

from .base import Filter, FilterContext, register_filter, FILTER_REGISTRY, FILTER_ALIASES
from imagestag.definitions import ImsFramework

if TYPE_CHECKING:
    from imagestag import Image


class BlendMode(Enum):
    """Blend modes for combining images."""
    NORMAL = auto()
    MULTIPLY = auto()
    SCREEN = auto()
    OVERLAY = auto()
    SOFT_LIGHT = auto()
    HARD_LIGHT = auto()
    DARKEN = auto()
    LIGHTEN = auto()
    DIFFERENCE = auto()
    EXCLUSION = auto()
    ADD = auto()
    SUBTRACT = auto()


@dataclass
class GraphSource:
    """Defines the input source for a FilterGraph.

    Similar to TensorFlow's input spec - defines constraints and metadata
    for input images to the graph.

    :ivar name: Source identifier (used as node name in designer)
    :ivar default_image: Default sample image name for preview
    :ivar allowed_formats: List of allowed pixel formats (e.g., ["RGB", "RGBA"]), None = any
    :ivar min_size: Minimum (width, height), None = no minimum
    :ivar max_size: Maximum (width, height), None = no maximum
    :ivar allowed_bit_depths: Allowed bit depths (e.g., [8, 16]), None = any
    """
    name: str = "input"
    default_image: str = "stag"
    allowed_formats: list[str] | None = None
    min_size: tuple[int, int] | None = None
    max_size: tuple[int, int] | None = None
    allowed_bit_depths: list[int] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (skips None values)."""
        result = {
            'name': self.name,
            'default_image': self.default_image,
        }
        if self.allowed_formats:
            result['allowed_formats'] = self.allowed_formats
        if self.min_size:
            result['min_size'] = list(self.min_size)
        if self.max_size:
            result['max_size'] = list(self.max_size)
        if self.allowed_bit_depths:
            result['allowed_bit_depths'] = self.allowed_bit_depths
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphSource:
        """Deserialize from dictionary."""
        return cls(
            name=data.get('name', 'input'),
            default_image=data.get('default_image', 'stag'),
            allowed_formats=data.get('allowed_formats'),
            min_size=tuple(data['min_size']) if data.get('min_size') else None,
            max_size=tuple(data['max_size']) if data.get('max_size') else None,
            allowed_bit_depths=data.get('allowed_bit_depths'),
        )


class CombinerFilter(Filter):
    """Base class for filters that combine multiple inputs."""

    inputs: list[str] = Field(default_factory=list)  # Branch names

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> Image:
        """Apply filter to multiple named inputs.

        :param images: Dict mapping branch names to their output images
        :param contexts: Dict mapping branch names to their contexts (optional)
        :returns: Combined image
        """
        raise NotImplementedError

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        """Single input fallback - just returns the image."""
        return image

    @classmethod
    def parse(cls, text: str) -> CombinerFilter:
        """Parse combiner from string: blend(a, b, multiply)"""
        text = text.strip()
        match = re.match(r'(\w+)\(([^)]+)\)', text)
        if not match:
            raise ValueError(f"Invalid combiner format: {text}")

        name = match.group(1).lower()
        args = [a.strip() for a in match.group(2).split(',')]

        if name == 'blend':
            mode = BlendMode.NORMAL
            if len(args) > 2:
                mode_str = args[2].upper()
                if hasattr(BlendMode, mode_str):
                    mode = BlendMode[mode_str]
            opacity = 1.0
            if len(args) > 3:
                opacity = float(args[3])
            return Blend(inputs=args[:2], mode=mode, opacity=opacity)
        elif name == 'composite':
            return Composite(inputs=args[:3])  # bg, fg, mask
        elif name == 'mask' or name == 'maskapply':
            return MaskApply(inputs=args[:2])  # image, mask

        raise ValueError(f"Unknown combiner: {name}")


@register_filter
class Blend(CombinerFilter):
    """Blend two branches together using a blend mode.

    Optionally accepts a mask image as third input to control
    per-pixel blending. White areas in the mask show more overlay,
    black areas show more base.
    """

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'a', 'description': 'Base/first image'},
        {'name': 'b', 'description': 'Overlay/second image'},
        {'name': 'mask', 'description': 'Alpha mask (optional)', 'optional': True},
    ]

    mode: BlendMode = BlendMode.NORMAL
    opacity: float = 1.0

    @field_validator('mode', mode='before')
    @classmethod
    def _coerce_mode(cls, v):
        if isinstance(v, BlendMode):
            return v
        if isinstance(v, str):
            return BlendMode[v.upper()]
        return v

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> Image:
        from imagestag import Image as Img
        import numpy as np

        # Get inputs by port name (a, b) with legacy fallback (base, overlay)
        base = images.get('a') or images.get('base')
        if base is None and self.inputs:
            base = images.get(self.inputs[0])
        overlay = images.get('b') or images.get('overlay')
        if overlay is None and len(self.inputs) > 1:
            overlay = images.get(self.inputs[1])

        if base is None or overlay is None:
            raise ValueError(
                f"Blend requires 'a' and 'b' inputs. Got: {list(images.keys())}"
            )

        # Get optional mask
        mask = images.get('mask')
        if mask is None and len(self.inputs) > 2 and self.inputs[2] in images:
            mask = images[self.inputs[2]]

        # Get pixels as float for blending calculations
        base_px = base.get_pixels().astype(np.float32) / 255.0
        overlay_px = overlay.get_pixels().astype(np.float32) / 255.0

        # Ensure same shape
        if base_px.shape != overlay_px.shape:
            # Resize overlay to match base
            overlay_resized = overlay.resized((base.width, base.height))
            overlay_px = overlay_resized.get_pixels().astype(np.float32) / 255.0

        # Apply blend mode
        blended = self._blend(base_px, overlay_px, self.mode)

        # Calculate per-pixel opacity
        if mask is not None:
            # Get mask pixels and resize if needed
            mask_px = mask.get_pixels()
            if mask_px.shape[:2] != base_px.shape[:2]:
                mask_resized = mask.resized((base.width, base.height))
                mask_px = mask_resized.get_pixels()

            # Convert mask to single channel float
            if len(mask_px.shape) == 3 and mask_px.shape[2] >= 3:
                mask_alpha = np.mean(mask_px[:, :, :3], axis=2).astype(np.float32) / 255.0
            elif len(mask_px.shape) == 2:
                mask_alpha = mask_px.astype(np.float32) / 255.0
            else:
                mask_alpha = mask_px[:, :, 0].astype(np.float32) / 255.0

            # Combine mask with opacity
            per_pixel_opacity = mask_alpha * self.opacity
            per_pixel_opacity = per_pixel_opacity[:, :, np.newaxis]

            # Apply per-pixel opacity blending
            result = base_px * (1 - per_pixel_opacity) + blended * per_pixel_opacity
        else:
            # Apply global opacity
            if self.opacity < 1.0:
                result = base_px * (1 - self.opacity) + blended * self.opacity
            else:
                result = blended

        # Convert back to uint8
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result)

    def _blend(self, base: 'np.ndarray', overlay: 'np.ndarray', mode: BlendMode) -> 'np.ndarray':
        """Apply blend mode."""
        import numpy as np

        if mode == BlendMode.NORMAL:
            return overlay
        elif mode == BlendMode.MULTIPLY:
            return base * overlay
        elif mode == BlendMode.SCREEN:
            return 1 - (1 - base) * (1 - overlay)
        elif mode == BlendMode.OVERLAY:
            # Overlay: multiply if base < 0.5, screen if base >= 0.5
            mask = base < 0.5
            result = np.where(mask, 2 * base * overlay, 1 - 2 * (1 - base) * (1 - overlay))
            return result
        elif mode == BlendMode.SOFT_LIGHT:
            return (1 - 2 * overlay) * base ** 2 + 2 * overlay * base
        elif mode == BlendMode.HARD_LIGHT:
            mask = overlay < 0.5
            return np.where(mask, 2 * base * overlay, 1 - 2 * (1 - base) * (1 - overlay))
        elif mode == BlendMode.DARKEN:
            return np.minimum(base, overlay)
        elif mode == BlendMode.LIGHTEN:
            return np.maximum(base, overlay)
        elif mode == BlendMode.DIFFERENCE:
            return np.abs(base - overlay)
        elif mode == BlendMode.EXCLUSION:
            return base + overlay - 2 * base * overlay
        elif mode == BlendMode.ADD:
            return np.clip(base + overlay, 0, 1)
        elif mode == BlendMode.SUBTRACT:
            return np.clip(base - overlay, 0, 1)
        else:
            return overlay

    def to_dict(self) -> dict[str, Any]:
        return {
            'type': 'Blend',
            'inputs': self.inputs,
            'mode': self.mode.name,
            'opacity': self.opacity,
        }


@register_filter
class Composite(CombinerFilter):
    """Composite foreground over background using a mask."""

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'a', 'description': 'Background/first image'},
        {'name': 'b', 'description': 'Foreground/second image'},
        {'name': 'mask', 'description': 'Alpha mask'},
    ]

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> Image:
        from imagestag import Image as Img
        import numpy as np

        # Get inputs by port name (a, b, mask) with legacy fallback
        bg = images.get('a') or images.get('background')
        if bg is None and self.inputs:
            bg = images.get(self.inputs[0])
        fg = images.get('b') or images.get('foreground')
        if fg is None and len(self.inputs) > 1:
            fg = images.get(self.inputs[1])
        mask_img = images.get('mask')
        if mask_img is None and len(self.inputs) > 2:
            mask_img = images.get(self.inputs[2])

        if bg is None or fg is None or mask_img is None:
            raise ValueError(
                f"Composite requires 'a', 'b', and 'mask' inputs. Got: {list(images.keys())}"
            )

        bg_px = bg.get_pixels().astype(np.float32) / 255.0
        fg_px = fg.get_pixels().astype(np.float32) / 255.0
        mask_px = mask_img.get_pixels().astype(np.float32) / 255.0

        # Resize if needed
        if fg_px.shape[:2] != bg_px.shape[:2]:
            fg_resized = fg.resized((bg.width, bg.height))
            fg_px = fg_resized.get_pixels().astype(np.float32) / 255.0
        if mask_px.shape[:2] != bg_px.shape[:2]:
            mask_resized = mask_img.resized((bg.width, bg.height))
            mask_px = mask_resized.get_pixels().astype(np.float32) / 255.0

        # Use mask as alpha (average if RGB)
        if len(mask_px.shape) == 3 and mask_px.shape[2] >= 3:
            alpha = np.mean(mask_px[:, :, :3], axis=2, keepdims=True)
        else:
            alpha = mask_px
            if len(alpha.shape) == 2:
                alpha = alpha[:, :, np.newaxis]

        # Composite: result = fg * alpha + bg * (1 - alpha)
        result = fg_px * alpha + bg_px * (1 - alpha)
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return Img(result)

    def to_dict(self) -> dict[str, Any]:
        return {
            'type': 'Composite',
            'inputs': self.inputs,
        }


@register_filter
class MaskApply(CombinerFilter):
    """Apply mask to image (set alpha from mask)."""

    _native_frameworks: ClassVar[list[ImsFramework]] = [ImsFramework.RAW, ImsFramework.CV]

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'input', 'description': 'Source image'},
        {'name': 'mask', 'description': 'Alpha mask'},
    ]

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> Image:
        from imagestag import Image as Img
        from imagestag.pixel_format import PixelFormat
        import numpy as np

        # Get inputs by port name with legacy fallback
        image = images.get('input') or images.get('image')
        if image is None and self.inputs:
            image = images.get(self.inputs[0])
        mask_img = images.get('mask')
        if mask_img is None and len(self.inputs) > 1:
            mask_img = images.get(self.inputs[1])

        if image is None or mask_img is None:
            raise ValueError(
                f"MaskApply requires 'input' and 'mask'. Got: {list(images.keys())}"
            )

        img_px = image.get_pixels(PixelFormat.RGBA)
        mask_px = mask_img.get_pixels()

        # Resize mask if needed
        if mask_px.shape[:2] != img_px.shape[:2]:
            mask_resized = mask_img.resized((image.width, image.height))
            mask_px = mask_resized.get_pixels()

        # Extract alpha from mask (average if RGB)
        if len(mask_px.shape) == 3 and mask_px.shape[2] >= 3:
            alpha = np.mean(mask_px[:, :, :3], axis=2).astype(np.uint8)
        elif len(mask_px.shape) == 2:
            alpha = mask_px
        else:
            alpha = mask_px[:, :, 0]

        # Set alpha channel
        img_px[:, :, 3] = alpha
        return Img(img_px, pixel_format=PixelFormat.RGBA)

    def to_dict(self) -> dict[str, Any]:
        return {
            'type': 'MaskApply',
            'inputs': self.inputs,
        }


@dataclass
class GraphNode:
    """A node in a FilterGraph.

    Nodes represent elements in a visual pipeline editor:

    - Source nodes: Define input data via `source` (PipelineSource)
    - Filter nodes: Apply image processing via `filter` (Filter instance)
    - Output nodes: Define pipeline output via `is_output=True` and `output_spec`

    Editor metadata (layout position, etc.) is stored in a separate 'editor' dict
    to avoid conflicts with filter parameters that might use x/y.

    :ivar name: Unique node identifier
    :ivar source: PipelineSource for input nodes
    :ivar filter: Filter instance for processing nodes
    :ivar is_output: True if this is an output node
    :ivar output_spec: PipelineOutput constraints for output nodes
    :ivar editor: Editor metadata dict (x, y position, etc.)
    """
    name: str
    source: 'PipelineSource | str | None' = None
    filter: Filter | None = None
    is_output: bool = False
    output_spec: 'PipelineOutput | None' = None
    editor: dict[str, Any] = field(default_factory=dict)

    def get_source(self) -> 'PipelineSource | None':
        """Get source as PipelineSource (handles string conversion).

        :returns: PipelineSource if this is a source node, None otherwise
        """
        if self.source is None:
            return None

        from .source import PipelineSource

        if isinstance(self.source, PipelineSource):
            return self.source
        # Convert string to PipelineSource
        return PipelineSource.parse(self.source)

    def to_dict(self) -> dict[str, Any]:
        """Serialize node to dictionary with explicit class information.

        Layout (x, y) is stored in an 'editor' sub-dict to avoid conflicts
        with filter parameters.

        :returns: Dict with class, params, and optional editor metadata
        """
        if self.source is not None:
            from .source import PipelineSource

            if isinstance(self.source, PipelineSource):
                # Use explicit format (class, type, value)
                result = self.source.to_dict(minimal=False)
            else:
                # Legacy string source - convert to explicit format
                source = PipelineSource.parse(self.source)
                result = source.to_dict(minimal=False)
        elif self.is_output:
            from .output import PipelineOutput

            # Always include explicit output specification
            if self.output_spec:
                result = self.output_spec.to_dict()
            else:
                # Default output spec for backward compatibility
                result = PipelineOutput.image().to_dict()
        elif self.filter:
            result = {"class": self.filter.__class__.__name__}
            # Get non-default param values
            from imagestag.color import Color
            params = {}
            for name in type(self.filter).model_fields:
                if name.startswith('_') or name == 'inputs':
                    continue
                value = getattr(self.filter, name)
                # Convert enums to string - prefer string value, fallback to lowercase name
                if isinstance(value, Enum):
                    if isinstance(value.value, str):
                        value = value.value
                    else:
                        value = value.name.lower()
                # Convert Color to hex string
                elif isinstance(value, Color):
                    value = value.to_hex()
                params[name] = value
            if params:
                result["params"] = params
        else:
            result = {}

        # Add editor metadata if present
        if self.editor:
            result["editor"] = self.editor

        return result

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> GraphNode:
        """Deserialize node from dictionary.

        Uses explicit class format with editor sub-dict for layout:
        - Source: {"class": "PipelineSource", "type": "IMAGE", ..., "editor": {"x": 80, "y": 150}}
        - Output: {"class": "PipelineOutput", "type": "IMAGE", "name": "output", "editor": {...}}
        - Filter: {"class": "FilterName", "params": {...}, "editor": {"x": 320, "y": 150}}

        Also supports legacy format with x/y at top level for backward compatibility.
        """
        from .source import PipelineSource
        from .output import PipelineOutput

        # Extract editor metadata (new format: editor sub-dict, legacy: top-level x/y)
        if "editor" in data:
            editor = data["editor"]
        elif "x" in data or "y" in data:
            # Legacy format: migrate x/y to editor dict
            editor = {}
            if "x" in data:
                editor["x"] = data["x"]
            if "y" in data:
                editor["y"] = data["y"]
        else:
            editor = {}

        # PipelineSource node (supports both new and legacy formats)
        if data.get("class") == "PipelineSource":
            source = PipelineSource.from_dict(data)
            return cls(name=name, source=source, editor=editor)

        # PipelineOutput node
        if data.get("class") == "PipelineOutput":
            output_spec = PipelineOutput.from_dict(data)
            return cls(name=name, is_output=True, output_spec=output_spec, editor=editor)

        # Filter node
        if "class" in data:
            filter_cls = FILTER_REGISTRY.get(data["class"])
            if filter_cls is None:
                filter_cls = FILTER_ALIASES.get(data["class"].lower())
            if filter_cls is None:
                raise ValueError(f"Unknown filter class: {data['class']}")

            # Parse params, handling enums
            from typing import get_type_hints
            params = data.get("params", {})
            kwargs = {}

            def parse_enum_value(enum_cls: type, value: str):
                """Parse enum value, case-insensitive."""
                # Try exact match first
                try:
                    return enum_cls[value]
                except KeyError:
                    pass
                # Try uppercase (common convention)
                try:
                    return enum_cls[value.upper()]
                except KeyError:
                    pass
                # Try by value if it's a string enum
                for member in enum_cls:
                    if str(member.value).upper() == value.upper():
                        return member
                raise KeyError(f"'{value}' is not a valid {enum_cls.__name__}")

            try:
                hints = get_type_hints(filter_cls)
            except Exception:
                hints = {}

            for name, field_info in filter_cls.model_fields.items():
                if name in params:
                    value = params[name]
                    # Handle enum fields
                    ftype = hints.get(name, field_info.annotation)
                    if ftype and isinstance(ftype, type) and issubclass(ftype, Enum):
                        if isinstance(value, str):
                            value = parse_enum_value(ftype, value)
                    kwargs[name] = value

            filter_instance = filter_cls(**kwargs)
            return cls(name=name, filter=filter_instance, editor=editor)

        return cls(name=name, editor=editor)


@dataclass
class GraphConnection:
    """A connection between nodes in a FilterGraph.

    JSON format::

        {"from": "input", "to": "blur"}                    - default ports
        {"from": "size_match", "to": ["blend", "base"]}    - named to_port
        {"from": ["size_match", "b"], "to": ["blend", "overlay"]}  - both named

    :ivar from_node: Source node name
    :ivar to_node: Target node name
    :ivar from_port: Source output port name (default: "output")
    :ivar to_port: Target input port name (default: "input")
    """
    from_node: str
    to_node: str
    from_port: str = "output"
    to_port: str = "input"

    def to_dict(self) -> dict[str, Any]:
        """Serialize connection to compact dict format.

        :returns: ``{"from": "node", "to": "node"}`` for default ports,
            ``{"from": "node", "to": ["node", "port"]}`` for named to_port
        """
        # Build from part
        if self.from_port == "output":
            from_part: str | list = self.from_node
        else:
            from_part = [self.from_node, self.from_port]

        # Build to part
        if self.to_port == "input":
            to_part: str | list = self.to_node
        else:
            to_part = [self.to_node, self.to_port]

        return {"from": from_part, "to": to_part}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphConnection:
        """Deserialize connection from dict format.

        Supports:
        - New format: {"from": "node" or ["node", "port"], "to": ...}
        - Legacy format: {"from_node": ..., "to_node": ..., "from_output": 0, "to_input": 1}
        """
        # New format with "from"/"to" keys
        if "from" in data:
            from_part = data["from"]
            to_part = data["to"]

            # Parse from
            if isinstance(from_part, list):
                from_node, from_port = from_part[0], from_part[1]
            else:
                from_node, from_port = from_part, "output"

            # Parse to
            if isinstance(to_part, list):
                to_node, to_port = to_part[0], to_part[1]
            else:
                to_node, to_port = to_part, "input"

            return cls(
                from_node=from_node,
                to_node=to_node,
                from_port=from_port,
                to_port=to_port,
            )

        # Legacy format with "from_node"/"to_node" keys
        from_output = data.get("from_output", 0)
        to_input = data.get("to_input", 0)

        # Convert numeric indices to generic port names
        from_port = "output" if from_output == 0 else f"output_{from_output}"
        to_port = "input" if to_input == 0 else f"input_{to_input}"

        return cls(
            from_node=data["from_node"],
            to_node=data["to_node"],
            from_port=from_port,
            to_port=to_port,
        )


@register_filter
class FilterGraph(Filter):
    """Directed acyclic graph of filter operations.

    A FilterGraph represents a complete image processing pipeline that can:
    - Define input constraints via the source specification
    - Have multiple named branches of sequential filters (legacy)
    - Or use a node-based graph with arbitrary connections (new)
    - Combine branch outputs using a CombinerFilter
    - Be serialized to/from JSON for storage and sharing

    Two storage modes:
    - Branch mode: Simple sequential branches with optional combiner
    - Node mode: Arbitrary DAG with named nodes and explicit connections
    """

    # Legacy branch-based fields
    branches: dict[str, list[Filter]] = Field(default_factory=dict)
    output: CombinerFilter | None = None
    source: GraphSource | None = None

    # New node-based fields
    nodes: dict[str, GraphNode] = Field(default_factory=dict)
    connections: list[GraphConnection] = Field(default_factory=list)

    # Visual layout metadata (node positions)
    layout: dict[str, Any] | None = None

    def uses_node_format(self) -> bool:
        """Check if this graph uses the node-based format."""
        return bool(self.nodes)

    def branch(self, name: str, filters: list[Filter]) -> str:
        """Define a named branch of filters. Returns branch name."""
        self.branches[name] = filters
        return name

    def apply(self, image: Image, context: FilterContext | None = None) -> Image:
        """Apply graph to image with branch-specific contexts.

        Each branch gets its own context that inherits from the parent context.
        This allows branches to write data without affecting each other.
        """
        # Create parent context if not provided
        if context is None:
            context = FilterContext()

        # Execute each branch with its own child context
        results: dict[str, Image] = {}
        branch_contexts: dict[str, FilterContext] = {}

        for name, filters in self.branches.items():
            # Create branch-specific context
            branch_ctx = context.branch(name)
            branch_contexts[name] = branch_ctx

            result = image
            for f in filters:
                result = f.apply(result, branch_ctx)
            results[name] = result

        # Apply output combiner
        if self.output:
            return self.output.apply_multi(results, branch_contexts)

        # If no combiner, return last branch result
        if results:
            return list(results.values())[-1]
        return image

    def to_dict(self) -> dict[str, Any]:
        """Serialize to minimal dictionary format for storage.

        Uses node-based format if nodes are present, otherwise branch format.
        Node format: {nodes: {...}, connections: [...]}

        Layout (x, y) is stored inline within each node definition.
        Connections use compact format:
            {"from": "node", "to": "node"}  - default ports
            {"from": "node", "to": ["node", "port"]}  - named to_port
        """
        # Use node-based format if nodes are present
        if self.uses_node_format():
            return {
                'nodes': {
                    name: node.to_dict()
                    for name, node in self.nodes.items()
                },
                'connections': [c.to_dict() for c in self.connections],
            }

        # Legacy branch format
        result = {
            'type': 'FilterGraph',
            'source': self.source.to_dict() if self.source else None,
            'branches': {
                name: [f.to_dict() for f in filters]
                for name, filters in self.branches.items()
            },
            'output': self.output.to_dict() if self.output else None,
        }
        if self.layout:
            result['layout'] = self.layout
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterGraph:
        """Deserialize graph from dictionary.

        Supports both node-based format (with 'nodes' key) and legacy
        branch-based format (with 'branches' key).
        """
        # Detect format by presence of 'nodes' key
        if 'nodes' in data:
            return cls._from_node_dict(data)
        else:
            return cls._from_branch_dict(data)

    @classmethod
    def _from_node_dict(cls, data: dict[str, Any]) -> FilterGraph:
        """Parse node-based format.

        Supports both:
        - New format: layout (x, y) stored inline in each node
        - Legacy format: separate "layout" dict at top level
        """
        # Check for legacy layout section
        legacy_layout = data.get('layout', {})

        nodes = {}
        for name, node_data in data.get('nodes', {}).items():
            # Merge legacy layout into node_data if not already present
            if legacy_layout and name in legacy_layout:
                if 'x' not in node_data and 'y' not in node_data:
                    node_data = {**node_data, **legacy_layout[name]}
            nodes[name] = GraphNode.from_dict(name, node_data)

        connections = [
            GraphConnection.from_dict(c)
            for c in data.get('connections', [])
        ]

        return cls(nodes=nodes, connections=connections)

    @classmethod
    def _from_branch_dict(cls, data: dict[str, Any]) -> FilterGraph:
        """Parse legacy branch-based format."""
        # Parse source
        source = None
        if data.get('source'):
            source = GraphSource.from_dict(data['source'])

        # Parse branches
        branches = {}
        for name, filters_data in data.get('branches', {}).items():
            branches[name] = [Filter.from_dict(f) for f in filters_data]

        # Parse output combiner
        output = None
        if data.get('output'):
            output_data = data['output']
            output_type = output_data.get('type', '')
            if output_type == 'Blend':
                mode = BlendMode[output_data.get('mode', 'NORMAL')]
                output = Blend(
                    inputs=output_data.get('inputs', []),
                    mode=mode,
                    opacity=output_data.get('opacity', 1.0)
                )
            elif output_type == 'Composite':
                output = Composite(inputs=output_data.get('inputs', []))
            elif output_type == 'MaskApply':
                output = MaskApply(inputs=output_data.get('inputs', []))

        # Parse optional layout
        layout = data.get('layout')

        return cls(branches=branches, output=output, source=source, layout=layout)

    @classmethod
    def parse(cls, text: str) -> FilterGraph:
        """Parse graph from string format.

        Format:
            [branch_name: filter|filter|...]
            [another_branch: filter|filter|...]
            combiner(branch1, branch2, args)

        Examples:
            [main: resize(0.5)|blur(1.5)]
            [mask: gray|threshold(128)]
            blend(main, mask, multiply)

        Or single-line:
            [a:resize(0.5)|blur(1.5)][b:gray]blend(a,b,multiply)
        """
        graph = cls()
        text = text.strip()

        # Handle multi-line or single-line
        if '\n' in text:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
        else:
            # Single line: split on ][ or ][combiner
            # Find all [...] blocks and the combiner at end
            lines = []
            remaining = text
            while remaining:
                if remaining.startswith('['):
                    # Find matching ]
                    end = remaining.find(']')
                    if end == -1:
                        break
                    lines.append(remaining[:end + 1])
                    remaining = remaining[end + 1:].strip()
                elif remaining:
                    # This should be the combiner
                    lines.append(remaining)
                    break

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Branch definition: [name: filters]
            branch_match = re.match(r'\[(\w+):\s*([^\]]+)\]', line)
            if branch_match:
                name = branch_match.group(1)
                filters_str = branch_match.group(2)
                filters = []
                for f_str in re.split(r'[|;]', filters_str):
                    f_str = f_str.strip()
                    if f_str:
                        filters.append(Filter.parse(f_str))
                graph.branches[name] = filters
                continue

            # Output combiner: blend(a, b, mode)
            if '(' in line and not line.startswith('['):
                graph.output = CombinerFilter.parse(line)

        return graph

    @classmethod
    def parse_dsl(cls, dsl: str, sources: list[str] | None = None) -> 'FilterGraph':
        """Parse graph from compact DSL string.

        DSL Syntax:
        - `;` separates statements
        - `[name: filter args]` defines a named node
        - `source` is the implicit first input
        - `other` is the implicit second input (for 2-input pipelines)
        - `node` or `node.port` references a node output
        - Keyword args with node refs: `image=source`, `geometry=f`

        Examples:
            # Linear pipeline (no named nodes)
            'blur 2.0; brightness 1.2'

            # Face detection with named nodes
            '[f: facedetector scale_factor=1.52]; drawgeometry image=source geometry=f'

            # Gradient blend with two inputs
            '[m: size_match source other smaller]; blend base=m.a overlay=m.b'

        :param dsl: DSL string to parse
        :param sources: List of source node names (default: ['source'] or ['source', 'other'])
        :returns: FilterGraph with nodes and connections
        """
        from .source import PipelineSource
        from .output import PipelineOutput
        from .base import _split_filter_args, _parse_value

        graph = cls()
        dsl = dsl.strip()

        # Detect if we need multiple sources based on 'other' keyword
        if sources is None:
            if 'other' in dsl.split() or ' other ' in dsl or dsl.endswith(' other'):
                sources = ['source', 'other']
            else:
                sources = ['source']

        # Add source nodes
        for i, src_name in enumerate(sources):
            source_spec = PipelineSource.image()
            graph.nodes[src_name] = GraphNode(
                name=src_name,
                source=source_spec,
                editor={"x": 80, "y": 80 + i * 200}
            )

        # Split into statements
        statements = [s.strip() for s in dsl.split(';') if s.strip()]

        # Track named nodes and the last output node
        named_nodes: dict[str, str] = {}  # alias -> node_name
        last_node: str | None = None
        node_x = 320

        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue

            # Check for named node: [name: filter args]
            named_match = re.match(r'\[(\w+):\s*(.+)\]$', stmt)
            if named_match:
                node_alias = named_match.group(1)
                filter_spec = named_match.group(2).strip()
            else:
                node_alias = None
                filter_spec = stmt

            # Parse the filter specification
            # Need to separate filter name from args, handling node references
            parts = _split_filter_args(filter_spec)
            if not parts:
                continue

            filter_name = parts[0].lower()
            args = parts[1:]

            # Find filter class
            filter_cls = FILTER_ALIASES.get(filter_name) or FILTER_REGISTRY.get(filter_name)
            if filter_cls is None:
                raise ValueError(f"Unknown filter: {filter_name}")

            # Parse arguments, separating node references from regular params
            positional = []
            kwargs = {}
            node_refs: dict[str, tuple[str, str]] = {}  # param -> (node, port)

            # Get input port names to distinguish from filter params
            input_ports = filter_cls.get_input_ports()
            input_port_names = set(p['name'] for p in input_ports)

            for arg in args:
                if '=' in arg and not arg.startswith('#'):
                    key, value = arg.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Check if this is an input port assignment (node reference)
                    # or if the value looks like a node reference
                    is_port_assignment = key in input_port_names
                    is_node_ref = cls._is_node_reference(value, sources, named_nodes)

                    if is_port_assignment or is_node_ref:
                        # This is a connection, not a parameter
                        ref_node, ref_port = cls._parse_node_ref(value, named_nodes)
                        node_refs[key] = (ref_node, ref_port)
                    else:
                        kwargs[key] = _parse_value(value)
                else:
                    parsed = _parse_value(arg)
                    # Check if positional arg is a node reference
                    if isinstance(parsed, str) and cls._is_node_reference(parsed, sources, named_nodes):
                        # Store as positional node ref (handle later)
                        positional.append(('__noderef__', parsed))
                    else:
                        positional.append(parsed)

            # Map positional args to parameter names (excluding node refs)
            real_positional = [p for p in positional if not (isinstance(p, tuple) and p[0] == '__noderef__')]
            if real_positional:
                param_names = []
                for fname in filter_cls.model_fields:
                    if not fname.startswith('_') and fname != 'inputs':
                        param_names.append(fname)
                for i, value in enumerate(real_positional):
                    if i < len(param_names) and param_names[i] not in kwargs:
                        kwargs[param_names[i]] = value

            # Create filter instance
            try:
                filter_instance = filter_cls(**kwargs)
            except TypeError as e:
                raise ValueError(f"Error creating {filter_name}: {e}")

            # Generate node name
            if node_alias:
                node_name = node_alias
                named_nodes[node_alias] = node_alias
            else:
                node_name = f"{filter_name}_{len(graph.nodes)}"

            # Create node
            graph.nodes[node_name] = GraphNode(
                name=node_name,
                filter=filter_instance,
                editor={"x": node_x, "y": 150}
            )
            node_x += 240

            # Create connections based on node references
            # (input_port_names already computed above as a set, convert to list for indexing)
            input_port_names_list = [p['name'] for p in input_ports]

            # Connect explicit node references (from kwargs)
            for param, (ref_node, ref_port) in node_refs.items():
                # Map param name to input port name
                to_port = param if param in input_port_names else 'input'
                graph.connections.append(GraphConnection(
                    from_node=ref_node,
                    to_node=node_name,
                    from_port=ref_port,
                    to_port=to_port
                ))

            # Handle positional node references
            positional_refs = [(i, p[1]) for i, p in enumerate(positional)
                              if isinstance(p, tuple) and p[0] == '__noderef__']
            for i, ref_str in positional_refs:
                ref_node, ref_port = cls._parse_node_ref(ref_str, named_nodes)
                to_port = input_port_names_list[i] if i < len(input_port_names_list) else 'input'
                graph.connections.append(GraphConnection(
                    from_node=ref_node,
                    to_node=node_name,
                    from_port=ref_port,
                    to_port=to_port
                ))

            # If no explicit input connections and this isn't the first filter,
            # connect from previous node (linear chain) or from source
            has_input_connection = any(
                c.to_node == node_name for c in graph.connections
            )
            if not has_input_connection:
                if last_node:
                    # Connect from previous node
                    graph.connections.append(GraphConnection(
                        from_node=last_node,
                        to_node=node_name,
                        from_port='output',
                        to_port=input_port_names_list[0] if input_port_names_list else 'input'
                    ))
                elif sources:
                    # Connect from first source
                    graph.connections.append(GraphConnection(
                        from_node=sources[0],
                        to_node=node_name,
                        from_port='output',
                        to_port=input_port_names_list[0] if input_port_names_list else 'input'
                    ))

            last_node = node_name

        # Add output node connected to last filter
        if last_node:
            output_name = 'output'
            graph.nodes[output_name] = GraphNode(
                name=output_name,
                is_output=True,
                output_spec=PipelineOutput.image(),
                editor={"x": node_x, "y": 150}
            )
            graph.connections.append(GraphConnection(
                from_node=last_node,
                to_node=output_name,
                from_port='output',
                to_port='input'
            ))

        return graph

    @classmethod
    def _is_node_reference(
        cls,
        value: str,
        sources: list[str],
        named_nodes: dict[str, str]
    ) -> bool:
        """Check if a value is a node reference."""
        # Handle port syntax: node.port
        base = value.split('.')[0] if '.' in value else value

        # Check if it's a source or named node
        return base in sources or base in named_nodes

    @classmethod
    def _parse_node_ref(
        cls,
        ref: str,
        named_nodes: dict[str, str]
    ) -> tuple[str, str]:
        """Parse a node reference like 'source', 'f', or 'm.a'.

        :returns: (node_name, port_name)
        """
        if '.' in ref:
            parts = ref.split('.', 1)
            node = named_nodes.get(parts[0], parts[0])
            port = parts[1]
        else:
            node = named_nodes.get(ref, ref)
            port = 'output'
        return node, port

    def to_string(self) -> str:
        """Convert graph to compact string format."""
        parts = []
        for name, filters in self.branches.items():
            filters_str = '|'.join(f.to_string() for f in filters)
            parts.append(f'[{name}:{filters_str}]')
        if self.output:
            inputs = ','.join(self.output.inputs)
            if isinstance(self.output, Blend):
                parts.append(f'blend({inputs},{self.output.mode.name.lower()})')
            elif isinstance(self.output, Composite):
                parts.append(f'composite({inputs})')
            elif isinstance(self.output, MaskApply):
                parts.append(f'mask({inputs})')
        return ''.join(parts)

    # -------------------------------------------------------------------------
    # JSON/Base64 Serialization
    # -------------------------------------------------------------------------

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize to minimal JSON string for storage.

        Only stores essential data: source spec, filter names + param values,
        combiner, and optional layout metadata.

        :param indent: JSON indentation (None for compact)
        :returns: JSON string
        """
        import json
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> FilterGraph:
        """Deserialize from JSON string.

        :param json_str: JSON string from to_json()
        :returns: FilterGraph instance
        """
        import json
        return cls.from_dict(json.loads(json_str))

    def to_base64(self) -> str:
        """Serialize to URL-safe base64 string.

        Useful for sharing graphs via URL query parameters.

        :returns: Base64-encoded string
        """
        import base64
        import json
        json_str = json.dumps(self.to_dict())
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    @classmethod
    def from_base64(cls, encoded: str) -> FilterGraph:
        """Deserialize from base64-encoded string.

        :param encoded: Base64 string from to_base64()
        :returns: FilterGraph instance
        """
        import base64
        import json
        json_str = base64.urlsafe_b64decode(encoded.encode()).decode()
        return cls.from_dict(json.loads(json_str))

    # -------------------------------------------------------------------------
    # Incremental Graph Operations (for visual editor synchronization)
    # -------------------------------------------------------------------------

    def add_node(
        self,
        name: str,
        node: GraphNode,
        x: float = 0,
        y: float = 0
    ) -> None:
        """Add a node to the graph (idempotent).

        If the node already exists, updates its position only.

        :param name: Unique node identifier
        :param node: The GraphNode to add
        :param x: X position for layout
        :param y: Y position for layout
        """
        if name not in self.nodes:
            self.nodes[name] = node
        # Set layout in editor dict
        self.nodes[name].editor["x"] = x
        self.nodes[name].editor["y"] = y

    def remove_node(self, name: str) -> None:
        """Remove a node and all its connections.

        :param name: Node identifier to remove
        """
        if name not in self.nodes:
            return
        del self.nodes[name]
        # Remove all connections involving this node
        self.connections = [
            c for c in self.connections
            if c.from_node != name and c.to_node != name
        ]

    def add_connection(self, conn: GraphConnection) -> None:
        """Add a connection between nodes.

        :param conn: The connection to add
        """
        # Validate nodes exist
        if conn.from_node not in self.nodes:
            raise ValueError(f"Source node '{conn.from_node}' does not exist")
        if conn.to_node not in self.nodes:
            raise ValueError(f"Target node '{conn.to_node}' does not exist")
        # Check for duplicate
        for existing in self.connections:
            if (existing.from_node == conn.from_node and
                existing.to_node == conn.to_node and
                existing.from_port == conn.from_port and
                existing.to_port == conn.to_port):
                return  # Already exists
        self.connections.append(conn)

    def remove_connection(
        self,
        from_node: str,
        to_node: str,
        from_output: int = 0,
        to_input: int = 0
    ) -> None:
        """Remove a specific connection.

        :param from_node: Source node name
        :param to_node: Target node name
        :param from_output: Source output port index
        :param to_input: Target input port index
        """
        from_port = 'output' if from_output == 0 else f'output_{from_output}'
        to_port = 'input' if to_input == 0 else f'input_{to_input}'
        self.connections = [
            c for c in self.connections
            if not (c.from_node == from_node and
                    c.to_node == to_node and
                    c.from_port == from_port and
                    c.to_port == to_port)
        ]

    def update_param(
        self,
        node_name: str,
        param_name: str,
        value: Any
    ) -> None:
        """Update a parameter on a node's filter.

        :param node_name: Node identifier
        :param param_name: Parameter name to update
        :param value: New parameter value
        """
        if node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' does not exist")
        node = self.nodes[node_name]
        if node.filter is None:
            raise ValueError(f"Node '{node_name}' has no filter")
        if not hasattr(node.filter, param_name):
            raise ValueError(
                f"Filter '{node.filter.__class__.__name__}' "
                f"has no parameter '{param_name}'"
            )
        setattr(node.filter, param_name, value)

    def update_layout(self, node_name: str, x: float, y: float) -> None:
        """Update a node's visual position.

        :param node_name: Node identifier
        :param x: New X position
        :param y: New Y position
        """
        if node_name in self.nodes:
            self.nodes[node_name].editor["x"] = x
            self.nodes[node_name].editor["y"] = y

    # -------------------------------------------------------------------------
    # File I/O
    # -------------------------------------------------------------------------

    def to_disk(self, path: str, indent: int = 2) -> None:
        """Save graph to a JSON file.

        :param path: File path to write to
        :param indent: JSON indentation (default 2)
        """
        from pathlib import Path
        Path(path).write_text(self.to_json(indent=indent))

    @classmethod
    def from_disk(cls, path: str) -> FilterGraph:
        """Load graph from a JSON file.

        :param path: File path to read from
        :returns: FilterGraph instance

        Example::

            graph = FilterGraph.from_disk("my_filter.json")
            result = graph.apply(my_image)
        """
        from pathlib import Path
        return cls.from_json(Path(path).read_text())

    # -------------------------------------------------------------------------
    # Production Execution
    # -------------------------------------------------------------------------

    def get_source_nodes(self) -> list[tuple[str, GraphNode]]:
        """Get all source nodes in the graph.

        :returns: List of (name, node) tuples for source nodes
        """
        sources = []
        for name, node in self.nodes.items():
            if node.source is not None:
                sources.append((name, node))
        return sources

    def get_output_node(self) -> tuple[str, GraphNode] | None:
        """Get the output node in the graph.

        :returns: (name, node) tuple for output node, or None if not found
        """
        for name, node in self.nodes.items():
            if node.is_output:
                return (name, node)
        return None

    def execute(
        self,
        *args: 'Image',
        inputs: 'dict[str, Image] | Image | None' = None,
        mode: 'ExecutionMode | None' = None,
        **kwargs: 'Image',
    ) -> 'Image | dict[str, Any] | None':
        """Execute the filter graph on input image(s).

        This is the main entry point for production use. Supports multiple
        calling conventions for flexibility:

        1. Positional args: Fill source nodes in alphabetical order by name
        2. Keyword args: Map directly to source node names
        3. Dict via inputs param: Explicit mapping of source names to images

        :param args: Images assigned to source nodes in alphabetical order
        :param inputs: Input image(s) as dict or single Image (legacy style)
        :param mode: Execution mode (defaults to PRODUCTION if inputs provided)
        :param kwargs: Images mapped to source nodes by name
        :returns: Output image or dict of outputs (for multi-output graphs)

        Example::

            graph = FilterGraph.from_disk("blend_pipeline.json")

            # Style 1: Positional args (alphabetical order: source_a, source_b)
            result = graph.execute(image_a, image_b)

            # Style 2: Keyword args (explicit names)
            result = graph.execute(source_a=image_a, source_b=image_b)

            # Style 3: Dict via inputs parameter
            result = graph.execute(inputs={
                "source_a": image_a,
                "source_b": image_b,
            })

            # Single input (most common)
            result = graph.execute(my_image)

            # Designer preview (loads placeholders)
            preview = graph.execute(mode=ExecutionMode.DESIGNER)
        """
        from .source import ExecutionMode

        # Get source nodes sorted alphabetically by name
        source_nodes = self.get_source_nodes()
        if not source_nodes:
            raise ValueError("Graph has no source nodes")
        source_nodes_sorted = sorted(source_nodes, key=lambda x: x[0])

        # Build input images dict from various input styles
        input_images: dict[str, Image] = {}

        # Style 1: Positional args - fill sources in alphabetical order
        if args:
            for i, img in enumerate(args):
                if i < len(source_nodes_sorted):
                    source_name = source_nodes_sorted[i][0]
                    input_images[source_name] = img

        # Style 2: Keyword args - map by name
        if kwargs:
            input_images.update(kwargs)

        # Style 3: Dict via inputs parameter (legacy/explicit style)
        if inputs is not None:
            if isinstance(inputs, dict):
                input_images.update(inputs)
            else:
                # Single image: assign to first source (alphabetically)
                first_source_name = source_nodes_sorted[0][0]
                input_images[first_source_name] = inputs

        # Determine execution mode
        if mode is None:
            mode = ExecutionMode.PRODUCTION if input_images else ExecutionMode.DESIGNER

        # Execute the node graph
        return self._execute_node_graph(input_images, mode)

    def _execute_node_graph(
        self,
        input_images: dict[str, Image],
        mode: 'ExecutionMode',
    ) -> Image | dict[str, Any] | None:
        """Execute node-based graph.

        Executes nodes in topological order, passing results between
        connected nodes using named ports.

        :param input_images: Dict mapping source node names to input images
        :param mode: Execution mode
        :returns: Output from the output node
        """
        from .source import ExecutionMode

        if not self.nodes:
            return None

        # Build adjacency lists using named ports
        outgoing: dict[str, list[dict]] = {name: [] for name in self.nodes}
        incoming: dict[str, list[dict]] = {name: [] for name in self.nodes}

        for conn in self.connections:
            if conn.from_node in self.nodes and conn.to_node in self.nodes:
                outgoing[conn.from_node].append({
                    'node': conn.to_node,
                    'from_port': conn.from_port,
                    'to_port': conn.to_port,
                })
                incoming[conn.to_node].append({
                    'node': conn.from_node,
                    'from_port': conn.from_port,
                    'to_port': conn.to_port,
                })

        # Execute nodes in topological order
        node_results: dict[str, Any] = {}

        # Initialize source nodes
        for name, node in self.nodes.items():
            if node.source is not None:
                source = node.get_source()
                if source:
                    # Try to get from input_images first (production)
                    if name in input_images:
                        node_results[name] = input_images[name]
                    elif mode == ExecutionMode.DESIGNER:
                        # Designer mode: load placeholder
                        loaded = source.load(mode=mode)
                        if loaded:
                            node_results[name] = loaded

        # Find execution order
        processed = set(node_results.keys())
        to_process = [name for name in self.nodes if name not in processed]

        max_iterations = len(self.nodes) * 2
        iteration = 0

        while to_process and iteration < max_iterations:
            iteration += 1

            for node_name in list(to_process):
                node = self.nodes[node_name]
                inc = incoming.get(node_name, [])

                # Check if all inputs are ready
                if all(c['node'] in processed for c in inc):
                    # Get inputs for this node using named ports
                    node_inputs: dict[str, Any] = {}
                    for conn in inc:
                        from_result = node_results.get(conn['node'])
                        if from_result is not None:
                            # Handle multi-output nodes (dict results keyed by port name)
                            if isinstance(from_result, dict):
                                from_port = conn['from_port']
                                from_result = from_result.get(from_port, next(iter(from_result.values())))

                            # Use the target port name as the key
                            to_port = conn['to_port']
                            node_inputs[to_port] = from_result

                    # Execute node
                    if node.is_output:
                        # Output node: pass through first input
                        if node_inputs:
                            node_results[node_name] = next(iter(node_inputs.values()))
                        else:
                            node_results[node_name] = None
                    elif node.filter:
                        # Filter node
                        try:
                            if hasattr(node.filter, 'apply_multi') and len(node_inputs) > 1:
                                # Multi-input combiner - pass inputs keyed by port name
                                result = node.filter.apply_multi(node_inputs)
                            elif node_inputs:
                                # Single-input filter
                                first_input = next(iter(node_inputs.values()))
                                result = node.filter(first_input)
                            else:
                                # Generator (no inputs)
                                result = node.filter(None)
                            node_results[node_name] = result
                        except Exception as e:
                            # On error, pass through first input if available
                            import traceback
                            traceback.print_exc()
                            if node_inputs:
                                node_results[node_name] = next(iter(node_inputs.values()))
                            else:
                                node_results[node_name] = None
                    else:
                        # Unknown node type, pass through
                        if node_inputs:
                            node_results[node_name] = next(iter(node_inputs.values()))

                    processed.add(node_name)
                    to_process.remove(node_name)

        # Return output node result
        output = self.get_output_node()
        if output:
            return node_results.get(output[0])

        # No output node - return last result
        if node_results:
            return list(node_results.values())[-1]

        return None


# Rebuild Pydantic models that reference dataclass types with forward annotations
# (GraphNode uses 'PipelineSource' and 'PipelineOutput' as string annotations,
#  PipelineOutput uses FormatSpec)
from .source import PipelineSource  # noqa: E402
from .output import PipelineOutput  # noqa: E402
from .formats import FormatSpec  # noqa: E402
FilterGraph.model_rebuild(_types_namespace={
    'PipelineSource': PipelineSource,
    'PipelineOutput': PipelineOutput,
    'FormatSpec': FormatSpec,
})
