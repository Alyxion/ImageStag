# ImageStag Filters - Filter Graph
"""
FilterGraph for branching and combining filter operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, ClassVar, TYPE_CHECKING
import re

from .base import Filter, FilterContext, register_filter, FILTER_REGISTRY, FILTER_ALIASES

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
class CombinerFilter(Filter):
    """Base class for filters that combine multiple inputs."""

    inputs: list[str] = field(default_factory=list)  # Branch names

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> Image:
        """Apply filter to multiple named inputs.

        Args:
            images: Dict mapping branch names to their output images
            contexts: Dict mapping branch names to their contexts (optional)

        Returns:
            Combined image
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
@dataclass
class Blend(CombinerFilter):
    """Blend two branches together using a blend mode.

    Optionally accepts a mask image as third input to control
    per-pixel blending. White areas in the mask show more overlay,
    black areas show more base.
    """

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'base', 'description': 'Base image'},
        {'name': 'overlay', 'description': 'Overlay image'},
        {'name': 'mask', 'description': 'Alpha mask (optional)', 'optional': True},
    ]

    mode: BlendMode = BlendMode.NORMAL
    opacity: float = 1.0

    def __post_init__(self):
        """Convert string values to enums."""
        if isinstance(self.mode, str):
            self.mode = BlendMode[self.mode.upper()]

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> Image:
        from imagestag import Image as Img
        import numpy as np

        if len(self.inputs) < 2:
            raise ValueError("Blend requires at least 2 inputs")

        base = images[self.inputs[0]]
        overlay = images[self.inputs[1]]

        # Get optional mask
        mask = None
        if len(self.inputs) > 2 and self.inputs[2] in images:
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
@dataclass
class Composite(CombinerFilter):
    """Composite foreground over background using a mask."""

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'background', 'description': 'Background image'},
        {'name': 'foreground', 'description': 'Foreground image'},
        {'name': 'mask', 'description': 'Alpha mask'},
    ]

    def apply_multi(
        self,
        images: dict[str, Image],
        contexts: dict[str, FilterContext] | None = None
    ) -> Image:
        from imagestag import Image as Img
        import numpy as np

        if len(self.inputs) < 3:
            raise ValueError("Composite requires 3 inputs: background, foreground, mask")

        bg = images[self.inputs[0]]
        fg = images[self.inputs[1]]
        mask_img = images[self.inputs[2]]

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
@dataclass
class MaskApply(CombinerFilter):
    """Apply mask to image (set alpha from mask)."""

    _input_ports: ClassVar[list[dict]] = [
        {'name': 'image', 'description': 'Source image'},
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

        if len(self.inputs) < 2:
            raise ValueError("MaskApply requires 2 inputs: image, mask")

        image = images[self.inputs[0]]
        mask_img = images[self.inputs[1]]

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


@register_filter
@dataclass
class FilterGraph(Filter):
    """Directed acyclic graph of filter operations with named branches."""

    branches: dict[str, list[Filter]] = field(default_factory=dict)
    output: CombinerFilter | None = None

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
        return {
            'type': 'FilterGraph',
            'branches': {
                name: [f.to_dict() for f in filters]
                for name, filters in self.branches.items()
            },
            'output': self.output.to_dict() if self.output else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterGraph:
        """Deserialize graph from dictionary."""
        branches = {}
        for name, filters_data in data.get('branches', {}).items():
            branches[name] = [Filter.from_dict(f) for f in filters_data]

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

        return cls(branches=branches, output=output)

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
