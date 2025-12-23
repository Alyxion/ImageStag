"""
ImageStag - A fast and efficient image processing and visualization library for Python
"""

from .image import Image, ImageSourceTypes, SUPPORTED_IMAGE_FILETYPES
from .pixel_format import PixelFormat, PixelFormatTypes
from .interpolation import InterpolationMethod
from .color import Color, Colors, ColorTypes, RawColorType
from .size2d import Size2D, Size2DTypes, Size2DTuple, Size2DIntTuple
from .pos2d import Pos2D, Pos2DTypes, Pos2DTuple
from .bounding import Bounding2D, Bounding2DTypes, RawBoundingType
from .definitions import ImsFramework, get_opencv, PIL_AVAILABLE, OpenCVHandler
from .image_base import ImageBase
from .geometry_list import (
    GeometryType,
    GeometryMeta,
    Rectangle,
    Circle,
    Ellipse,
    Line,
    Polygon,
    Geometry,
    GeometryList,
)
from .image_list import ImageList, RegionMeta

__all__ = [
    # Core Image class
    "Image",
    "ImageSourceTypes",
    "ImageBase",
    "SUPPORTED_IMAGE_FILETYPES",
    # Pixel formats
    "PixelFormat",
    "PixelFormatTypes",
    # Interpolation
    "InterpolationMethod",
    # Colors
    "Color",
    "Colors",
    "ColorTypes",
    "RawColorType",
    # Geometry
    "Size2D",
    "Size2DTypes",
    "Size2DTuple",
    "Size2DIntTuple",
    "Pos2D",
    "Pos2DTypes",
    "Pos2DTuple",
    "Bounding2D",
    "Bounding2DTypes",
    "RawBoundingType",
    # Framework definitions
    "ImsFramework",
    "get_opencv",
    "PIL_AVAILABLE",
    "OpenCVHandler",
    # Geometry primitives
    "GeometryType",
    "GeometryMeta",
    "Rectangle",
    "Circle",
    "Ellipse",
    "Line",
    "Polygon",
    "Geometry",
    "GeometryList",
    # Image lists
    "ImageList",
    "RegionMeta",
]

__version__ = "0.1.0"
