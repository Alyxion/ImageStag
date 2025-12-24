"""Pipeline output classes for defining and validating output data.

This module provides classes for specifying output constraints and
validating that pipeline results match expectations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .formats import FormatSpec


class OutputType(Enum):
    """Types of pipeline outputs."""

    IMAGE = auto()  # Single Image
    IMAGE_LIST = auto()  # ImageList (multiple images)
    GEOMETRY_LIST = auto()  # GeometryList (detected shapes)
    DICT = auto()  # Dictionary of named outputs
    ANY = auto()  # Any type (no constraint)


@dataclass
class PipelineOutput:
    """Defines output constraints for a filter pipeline.

    Specifies what type of output is expected and validates
    that the actual output matches the constraints.

    :ivar output_type: Expected output type (IMAGE, IMAGE_LIST, etc.)
    :ivar format_constraints: For IMAGE type, valid pixel formats
    :ivar name: Output name (for named outputs in dict)
    :ivar description: Human-readable description
    :ivar required: Whether this output is required (non-None)
    """

    output_type: OutputType = OutputType.IMAGE
    format_constraints: list[FormatSpec] | None = None
    name: str = "output"
    description: str = ""
    required: bool = True

    @classmethod
    def image(
        cls,
        formats: list[str] | None = None,
        name: str = "output",
        description: str = "",
        required: bool = True,
    ) -> PipelineOutput:
        """Create an Image output constraint.

        :param formats: List of valid pixel format names (e.g., ['RGB', 'RGBA'])
        :param name: Output name
        :param description: Human-readable description
        :param required: Whether output is required
        :returns: PipelineOutput configured for Image output
        """
        from .formats import FormatSpec

        format_specs = None
        if formats:
            format_specs = [FormatSpec(pixel_format=f) for f in formats]
        return cls(
            output_type=OutputType.IMAGE,
            format_constraints=format_specs,
            name=name,
            description=description,
            required=required,
        )

    @classmethod
    def image_list(
        cls,
        name: str = "regions",
        description: str = "",
        required: bool = True,
    ) -> PipelineOutput:
        """Create an ImageList output constraint.

        :param name: Output name
        :param description: Human-readable description
        :param required: Whether output is required
        :returns: PipelineOutput configured for ImageList output
        """
        return cls(
            output_type=OutputType.IMAGE_LIST,
            name=name,
            description=description,
            required=required,
        )

    @classmethod
    def geometry_list(
        cls,
        name: str = "geometry",
        description: str = "",
        required: bool = True,
    ) -> PipelineOutput:
        """Create a GeometryList output constraint.

        :param name: Output name
        :param description: Human-readable description
        :param required: Whether output is required
        :returns: PipelineOutput configured for GeometryList output
        """
        return cls(
            output_type=OutputType.GEOMETRY_LIST,
            name=name,
            description=description,
            required=required,
        )

    @classmethod
    def dict_output(
        cls,
        name: str = "outputs",
        description: str = "",
        required: bool = True,
    ) -> PipelineOutput:
        """Create a dict output constraint.

        :param name: Output name
        :param description: Human-readable description
        :param required: Whether output is required
        :returns: PipelineOutput configured for dict output
        """
        return cls(
            output_type=OutputType.DICT,
            name=name,
            description=description,
            required=required,
        )

    @classmethod
    def any_type(
        cls,
        name: str = "output",
        description: str = "",
        required: bool = False,
    ) -> PipelineOutput:
        """Create an unconstrained output.

        :param name: Output name
        :param description: Human-readable description
        :param required: Whether output is required
        :returns: PipelineOutput with no type constraints
        """
        return cls(
            output_type=OutputType.ANY,
            name=name,
            description=description,
            required=required,
        )

    def validate(self, result: Any) -> tuple[bool, str]:
        """Validate that a result matches this output constraint.

        :param result: The actual output from the pipeline
        :returns: Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        from imagestag import GeometryList, Image, ImageList

        if result is None:
            if self.required:
                return False, f"Output '{self.name}' is required but was None"
            return True, ""

        if self.output_type == OutputType.ANY:
            return True, ""

        if self.output_type == OutputType.IMAGE:
            if not isinstance(result, Image):
                return False, f"Expected Image, got {type(result).__name__}"

            # Check format constraints
            if self.format_constraints:
                pf_name = result.pixel_format.name
                allowed = [
                    f.pixel_format
                    for f in self.format_constraints
                    if f.pixel_format
                ]
                if allowed and pf_name not in allowed:
                    return False, f"Image format {pf_name} not in allowed: {allowed}"

            return True, ""

        elif self.output_type == OutputType.IMAGE_LIST:
            if not isinstance(result, ImageList):
                return False, f"Expected ImageList, got {type(result).__name__}"
            return True, ""

        elif self.output_type == OutputType.GEOMETRY_LIST:
            if not isinstance(result, GeometryList):
                return False, f"Expected GeometryList, got {type(result).__name__}"
            return True, ""

        elif self.output_type == OutputType.DICT:
            if not isinstance(result, dict):
                return False, f"Expected dict, got {type(result).__name__}"
            return True, ""

        return False, f"Unknown output type: {self.output_type}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        :returns: Dictionary representation for JSON serialization
        """
        result: dict[str, Any] = {
            "class": "PipelineOutput",
            "type": self.output_type.name,
            "name": self.name,
        }
        if self.format_constraints:
            result["formats"] = [
                f.pixel_format for f in self.format_constraints if f.pixel_format
            ]
        if self.description:
            result["description"] = self.description
        if not self.required:
            result["required"] = False
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineOutput:
        """Deserialize from dictionary.

        Expects explicit format:
        {"class": "PipelineOutput", "type": "IMAGE", "name": "output"}

        :param data: Dictionary with output specification
        :returns: PipelineOutput instance
        """
        from .formats import FormatSpec

        if data.get("class") != "PipelineOutput":
            raise ValueError(
                "Invalid PipelineOutput format. Expected "
                '{"class": "PipelineOutput", "type": "...", "name": "..."}'
            )

        output_type = OutputType[data.get("type", "IMAGE")]

        format_constraints = None
        if "formats" in data:
            format_constraints = [FormatSpec(pixel_format=f) for f in data["formats"]]

        return cls(
            output_type=output_type,
            format_constraints=format_constraints,
            name=data.get("name", "output"),
            description=data.get("description", ""),
            required=data.get("required", True),
        )

    def __str__(self) -> str:
        """String representation."""
        formats = ""
        if self.format_constraints:
            formats = f"[{', '.join(f.pixel_format or '' for f in self.format_constraints)}]"
        return f"{self.output_type.name}{formats}"

    def __repr__(self) -> str:
        """Debug representation."""
        return f"PipelineOutput({self.output_type.name}, name={self.name!r})"
