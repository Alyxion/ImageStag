"""Pipeline source classes for defining and loading input data.

This module provides classes for specifying input constraints and
loading input data based on execution mode.

PipelineSource defines:
- Input type (IMAGE, IMAGE_LIST, etc.)
- Supported formats (RGB8, RGBA8, GRAY8, etc.)
- Optional placeholder for designer preview

Usage in production:
    my_image = Image("photo.jpg")
    my_graph = FilterGraph.from_disk("my_filter_graph.json")
    processed_image = my_graph.apply(my_image)

Usage in designer (preview):
    my_graph = FilterGraph.from_disk("my_filter_graph.json")
    # Uses placeholder sample images for preview
    preview_image = my_graph.apply(mode=ExecutionMode.DESIGNER)
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from imagestag import Image


class InputType(Enum):
    """Types of pipeline input data."""

    IMAGE = auto()  # Single Image
    IMAGE_LIST = auto()  # ImageList (multiple images)
    GEOMETRY_LIST = auto()  # GeometryList (detected shapes)
    ANY = auto()  # Any type (no constraint)


class ExecutionMode(Enum):
    """Pipeline execution mode."""

    DESIGNER = auto()  # Load placeholder sample for preview
    PRODUCTION = auto()  # Expect image passed to apply()


@runtime_checkable
class SourceHandler(Protocol):
    """Protocol for loading sources from files/URLs.

    Implementations control security and access permissions.
    The FilterPipeline cannot access disk directly - it must
    go through this handler.
    """

    def load_file(self, path: str) -> Image | None:
        """Load image from file path.

        :param path: File path (relative or absolute)
        :returns: Image if loaded successfully, None if not allowed/found
        """
        ...

    def load_url(self, url: str) -> Image | None:
        """Load image from URL.

        :param url: HTTP/HTTPS URL or data URL
        :returns: Image if loaded successfully, None if not allowed/failed
        """
        ...

    def resolve_path(self, path: str) -> str | None:
        """Resolve and validate a file path.

        :param path: Raw path from source specification
        :returns: Resolved absolute path, or None if not allowed
        """
        ...


# Valid format strings: CHANNEL_BITDEPTH (e.g., RGB8, RGBA8, GRAY8, GRAY16)
VALID_FORMATS = frozenset([
    "RGB8", "RGBA8", "BGR8", "BGRA8", "GRAY8", "HSV8",
    "RGB16", "RGBA16", "GRAY16",
    "RGB32F", "RGBA32F", "GRAY32F",
])


@dataclass
class PipelineSource:
    """Defines an input source for a filter pipeline.

    Specifies:
    - Input type: What kind of data this source expects (IMAGE, IMAGE_LIST, etc.)
    - Formats: Which pixel formats are supported (e.g., ["RGB8", "RGBA8", "GRAY8"])
    - Placeholder: Sample image for designer preview mode

    JSON format:
        {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8", "RGBA8", "GRAY8"],
            "placeholder": "samples://images/group"
        }

    In production, the graph is called with an actual image:
        graph.apply(my_image)

    In designer mode, the placeholder is loaded for preview:
        graph.apply(mode=ExecutionMode.DESIGNER)

    :ivar input_type: Expected input type (IMAGE, IMAGE_LIST, etc.)
    :ivar formats: List of supported format strings (e.g., ["RGB8", "RGBA8"])
    :ivar placeholder: URI for preview image (samples://name, file://path, etc.)
    :ivar name: Input name for multi-input graphs
    :ivar description: Human-readable description
    :ivar required: Whether this input is required
    """

    input_type: InputType = InputType.IMAGE
    formats: list[str] = field(default_factory=lambda: ["RGB8", "RGBA8", "GRAY8"])
    placeholder: str = "samples://images/stag"
    name: str = "input"
    description: str = ""
    required: bool = True

    # Legacy fields for backward compatibility (deprecated)
    _legacy_source_type: str | None = field(default=None, repr=False)
    _legacy_value: str | None = field(default=None, repr=False)

    def __post_init__(self):
        """Validate format strings."""
        for fmt in self.formats:
            if fmt not in VALID_FORMATS:
                # Allow it but warn in development
                pass

    @classmethod
    def image(
        cls,
        formats: list[str] | None = None,
        placeholder: str = "samples://images/stag",
        name: str = "input",
        description: str = "",
        required: bool = True,
    ) -> PipelineSource:
        """Create an Image input source.

        :param formats: List of supported format strings (default: RGB8, RGBA8, GRAY8)
        :param placeholder: URI for preview image in designer mode
        :param name: Input name for multi-input graphs
        :param description: Human-readable description
        :param required: Whether input is required
        :returns: PipelineSource configured for Image input
        """
        return cls(
            input_type=InputType.IMAGE,
            formats=formats or ["RGB8", "RGBA8", "GRAY8"],
            placeholder=placeholder,
            name=name,
            description=description,
            required=required,
        )

    @classmethod
    def image_list(
        cls,
        formats: list[str] | None = None,
        placeholder: str = "samples://images/stag",
        name: str = "input",
        description: str = "",
        required: bool = True,
    ) -> PipelineSource:
        """Create an ImageList input source.

        :param formats: List of supported format strings
        :param placeholder: URI for preview image in designer mode
        :param name: Input name
        :param description: Human-readable description
        :param required: Whether input is required
        :returns: PipelineSource configured for ImageList input
        """
        return cls(
            input_type=InputType.IMAGE_LIST,
            formats=formats or ["RGB8", "RGBA8", "GRAY8"],
            placeholder=placeholder,
            name=name,
            description=description,
            required=required,
        )

    @classmethod
    def any_type(
        cls,
        placeholder: str = "samples://images/stag",
        name: str = "input",
        description: str = "",
        required: bool = False,
    ) -> PipelineSource:
        """Create an unconstrained input source.

        :param placeholder: URI for preview image in designer mode
        :param name: Input name
        :param description: Human-readable description
        :param required: Whether input is required
        :returns: PipelineSource with no type constraints
        """
        return cls(
            input_type=InputType.ANY,
            formats=[],
            placeholder=placeholder,
            name=name,
            description=description,
            required=required,
        )

    # -------------------------------------------------------------------------
    # Legacy factory methods (for backward compatibility)
    # -------------------------------------------------------------------------

    @classmethod
    def sample(cls, name: str) -> PipelineSource:
        """Create a source with sample placeholder (legacy).

        :param name: Sample image name (e.g., 'coins', 'astronaut', 'stag')
        :returns: PipelineSource configured with sample placeholder
        """
        return cls(
            input_type=InputType.IMAGE,
            formats=["RGB8", "RGBA8", "GRAY8"],
            placeholder=f"samples://images/{name}",
            _legacy_source_type="SAMPLE",
            _legacy_value=name,
        )

    @classmethod
    def file(cls, path: str, default_sample: str = "stag") -> PipelineSource:
        """Create a file source (legacy - for designer loading).

        :param path: File path to the image
        :param default_sample: Fallback sample for designer preview
        :returns: PipelineSource configured with file placeholder
        """
        return cls(
            input_type=InputType.IMAGE,
            formats=["RGB8", "RGBA8", "GRAY8"],
            placeholder=f"file://{path}",
            _legacy_source_type="FILE",
            _legacy_value=path,
        )

    @classmethod
    def url(cls, address: str, default_sample: str = "stag") -> PipelineSource:
        """Create a URL source (legacy - for designer loading).

        :param address: HTTP/HTTPS URL or data URL
        :param default_sample: Fallback sample for designer preview
        :returns: PipelineSource configured with URL placeholder
        """
        return cls(
            input_type=InputType.IMAGE,
            formats=["RGB8", "RGBA8", "GRAY8"],
            placeholder=address if address.startswith("data:") else f"url://{address}",
            _legacy_source_type="URL",
            _legacy_value=address,
        )

    @classmethod
    def placeholder(cls, name: str, default_sample: str = "stag") -> PipelineSource:
        """Create a placeholder source (legacy).

        :param name: Placeholder name for binding lookup
        :param default_sample: Fallback sample for designer preview
        :returns: PipelineSource configured as placeholder
        """
        return cls(
            input_type=InputType.IMAGE,
            formats=["RGB8", "RGBA8", "GRAY8"],
            placeholder=f"samples://images/{default_sample}",
            name=name,
            _legacy_source_type="PLACEHOLDER",
            _legacy_value=name,
        )

    @classmethod
    def parse(cls, source_str: str) -> PipelineSource:
        """Parse source from string format (legacy).

        Formats:
            "sample:coins" -> sample source
            "file:/path/to/image.jpg" -> file source
            "url:https://example.com/img.png" -> URL source
            "coins" -> legacy format (interpreted as sample)

        :param source_str: Source specification string
        :returns: PipelineSource instance
        """
        if not source_str:
            return cls.sample("stag")

        if ":" not in source_str:
            # Legacy format: just image name = sample
            return cls.sample(source_str)

        prefix, value = source_str.split(":", 1)
        prefix = prefix.lower()

        if prefix == "sample":
            return cls.sample(value)
        elif prefix == "file":
            return cls.file(value)
        elif prefix == "url":
            return cls.url(value)
        elif prefix == "placeholder":
            return cls.placeholder(value)
        elif prefix == "data":
            # data:image/png;base64,... is a URL type
            return cls.url(source_str)
        else:
            # Unknown prefix, treat as sample name
            return cls.sample(source_str)

    # -------------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------------

    def load(
        self,
        mode: ExecutionMode = ExecutionMode.DESIGNER,
        handler: SourceHandler | None = None,
        bindings: dict[str, Image] | None = None,
    ) -> Image | None:
        """Load the placeholder image for preview.

        In production mode, this returns None - images are passed to apply().
        In designer mode, loads the placeholder for preview.

        :param mode: Execution mode (DESIGNER or PRODUCTION)
        :param handler: Source handler for file/URL loading
        :param bindings: Dict mapping placeholder names to actual images (legacy)
        :returns: Image if loaded successfully, None if unavailable or production mode
        """
        if mode == ExecutionMode.PRODUCTION:
            # In production, images are passed directly - no loading
            return None

        # Designer mode - load placeholder for preview
        return self._load_placeholder(handler)

    def _load_placeholder(self, handler: SourceHandler | None = None) -> Image | None:
        """Load the placeholder image for preview.

        Supports URIs:
            samples://images/name - Built-in sample image
            file://path - Local file (requires handler)
            url://address - HTTP/HTTPS URL (requires handler)
            data:image/...;base64,... - Inline data URL

        :param handler: Optional handler for file/URL loading
        :returns: Image if loaded, None if unavailable
        """
        uri = self.placeholder

        if uri.startswith("samples://images/"):
            # Built-in sample image
            name = uri.replace("samples://images/", "")
            return self._load_sample(name)

        elif uri.startswith("file://"):
            path = uri.replace("file://", "")
            if handler:
                return handler.load_file(path)
            return None

        elif uri.startswith("url://"):
            address = uri.replace("url://", "")
            if handler:
                return handler.load_url(address)
            return None

        elif uri.startswith("data:"):
            return self._load_data_url(uri)

        # Try as sample name for backward compatibility
        return self._load_sample(uri)

    def _load_sample(self, name: str) -> Image | None:
        """Load a sample image by name."""
        from imagestag import samples as imagestag_samples
        from imagestag.skimage import SKImage

        # Try imagestag samples first (stag, group)
        if name in imagestag_samples.list_images():
            return imagestag_samples.load(name)

        # Try scikit-image samples
        try:
            if name in SKImage.list_images():
                return SKImage.load(name)
        except Exception:
            pass

        return None

    def _load_data_url(self, data_url: str) -> Image | None:
        """Load image from data URL."""
        from imagestag import Image

        try:
            # Format: data:image/png;base64,<data>
            if "," not in data_url:
                return None
            _header, encoded = data_url.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            return Image(image_bytes)
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate(self, image: Image) -> tuple[bool, str]:
        """Validate that an input image matches this source's constraints.

        :param image: The input image to validate
        :returns: Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        from imagestag import Image as Img, ImageList
        from imagestag.geometry_list import GeometryList

        if image is None:
            if self.required:
                return False, f"Input '{self.name}' is required but was None"
            return True, ""

        # Type check
        if self.input_type == InputType.IMAGE:
            if not isinstance(image, Img):
                return False, f"Expected Image, got {type(image).__name__}"
        elif self.input_type == InputType.IMAGE_LIST:
            if not isinstance(image, ImageList):
                return False, f"Expected ImageList, got {type(image).__name__}"
        elif self.input_type == InputType.GEOMETRY_LIST:
            if not isinstance(image, GeometryList):
                return False, f"Expected GeometryList, got {type(image).__name__}"
        elif self.input_type == InputType.ANY:
            return True, ""

        # Format check (for images)
        if self.formats and isinstance(image, Img):
            # Build format string: CHANNEL + BITDEPTH
            pf = image.pixel_format
            bit_depth = 8  # Default assumption
            dtype = image.get_pixels().dtype
            if dtype.name == "uint16":
                bit_depth = 16
            elif dtype.name == "float32":
                bit_depth = 32

            suffix = str(bit_depth) if bit_depth != 32 else "32F"
            img_format = f"{pf.name}{suffix}"

            if img_format not in self.formats:
                return False, f"Image format {img_format} not in supported: {self.formats}"

        return True, ""

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_string(self) -> str:
        """Convert to legacy string format.

        :returns: String representation like "sample:coins"
        """
        # For backward compatibility
        if self._legacy_source_type == "SAMPLE":
            return f"sample:{self._legacy_value}"
        elif self._legacy_source_type == "FILE":
            return f"file:{self._legacy_value}"
        elif self._legacy_source_type == "URL":
            return f"url:{self._legacy_value}"
        elif self._legacy_source_type == "PLACEHOLDER":
            return f"placeholder:{self._legacy_value}"

        # Extract name from placeholder URI
        if self.placeholder.startswith("samples://images/"):
            name = self.placeholder.replace("samples://images/", "")
            return f"sample:{name}"

        return self.placeholder

    def to_dict(self, minimal: bool = False) -> dict[str, Any]:
        """Serialize to dictionary.

        :param minimal: If True, omit default values for cleaner output
        :returns: Dictionary representation for JSON serialization
        """
        result: dict[str, Any] = {
            "class": "PipelineSource",
            "type": self.input_type.name,
        }

        # Always include formats (they define the contract)
        if self.formats:
            result["formats"] = self.formats

        # Include placeholder
        result["placeholder"] = self.placeholder

        # Optional fields
        if self.name != "input":
            result["name"] = self.name
        if self.description:
            result["description"] = self.description
        if not self.required:
            result["required"] = False

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineSource:
        """Deserialize from dictionary.

        Supports new format:
            {"class": "PipelineSource", "type": "IMAGE", "formats": [...], "placeholder": "..."}

        And legacy format:
            {"class": "PipelineSource", "type": "SAMPLE", "value": "coins"}

        :param data: Dictionary with source specification
        :returns: PipelineSource instance
        """
        if data.get("class") != "PipelineSource":
            raise ValueError(
                "Invalid PipelineSource format. Expected "
                '{"class": "PipelineSource", ...}'
            )

        type_str = data.get("type", "IMAGE")

        # Check for legacy format (SAMPLE, FILE, URL, PLACEHOLDER)
        if type_str in ("SAMPLE", "FILE", "URL", "PLACEHOLDER"):
            return cls._from_legacy_dict(data)

        # New format
        input_type = InputType[type_str]
        formats = data.get("formats", ["RGB8", "RGBA8", "GRAY8"])
        placeholder = data.get("placeholder", "samples://images/stag")

        return cls(
            input_type=input_type,
            formats=formats,
            placeholder=placeholder,
            name=data.get("name", "input"),
            description=data.get("description", ""),
            required=data.get("required", True),
        )

    @classmethod
    def _from_legacy_dict(cls, data: dict[str, Any]) -> PipelineSource:
        """Parse legacy format with type=SAMPLE/FILE/URL/PLACEHOLDER."""
        type_str = data["type"]
        value = data.get("value", "")
        default_sample = data.get("default_sample", "stag")

        if type_str == "SAMPLE":
            return cls.sample(value)
        elif type_str == "FILE":
            return cls.file(value, default_sample)
        elif type_str == "URL":
            return cls.url(value, default_sample)
        elif type_str == "PLACEHOLDER":
            return cls.placeholder(value, default_sample)
        else:
            return cls.sample("stag")

    # -------------------------------------------------------------------------
    # Properties for backward compatibility
    # -------------------------------------------------------------------------

    @property
    def is_placeholder(self) -> bool:
        """Check if this source was created as a placeholder (legacy)."""
        return self._legacy_source_type == "PLACEHOLDER"

    @property
    def is_sample(self) -> bool:
        """Check if this source uses a sample placeholder."""
        return (
            self._legacy_source_type == "SAMPLE" or
            self.placeholder.startswith("samples://")
        )

    @property
    def source_type(self) -> str:
        """Legacy source type string (deprecated)."""
        return self._legacy_source_type or "IMAGE"

    @property
    def value(self) -> str:
        """Legacy value string (deprecated)."""
        if self._legacy_value:
            return self._legacy_value
        # Extract from placeholder
        if self.placeholder.startswith("samples://images/"):
            return self.placeholder.replace("samples://images/", "")
        return self.placeholder

    def __str__(self) -> str:
        """String representation."""
        return f"PipelineSource({self.input_type.name}, formats={self.formats})"

    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"PipelineSource(type={self.input_type.name}, "
            f"formats={self.formats}, placeholder={self.placeholder!r})"
        )


# Legacy type alias for backward compatibility
SourceType = InputType
