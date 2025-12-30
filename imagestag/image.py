"""
Implements the class :class:`.Image` which is ImageStag's main class for loading,
storing and keeping image data in memory.
"""

from __future__ import annotations
import hashlib
import io
import os
from typing import Union, Any, Literal
from urllib.request import urlopen
from urllib.error import URLError

import PIL.Image
import filetype
import numpy as np

from .color import Color, Colors, ColorTypes
from .bounding import Bounding2DTypes, Bounding2D
from .interpolation import InterpolationMethod
from .pixel_format import PixelFormat, PixelFormatTypes
from .size2d import Size2D, Size2DTypes
from .definitions import ImsFramework, get_opencv
from .image_base import ImageBase

HTTP_PROTOCOL_URL_HEADER = "http://"
HTTPS_PROTOCOL_URL_HEADER = "https://"

SUPPORTED_IMAGE_FILETYPES = ["png", "bmp", "jpg", "jpeg", "gif"]
"List of image file types which can be read and written"

SUPPORTED_IMAGE_FILETYPE_SET = set(SUPPORTED_IMAGE_FILETYPES)
"Set of image file types which can be read and written"

Image = type

ImageSourceTypes = Union[str, np.ndarray, bytes, PIL.Image.Image, Image]
"The valid source type for loading an image"


def _load_from_source(source: str, **params) -> bytes | None:
    """
    Loads image data from a file path or URL.

    :param source: File path or URL
    :param params: Additional parameters
    :return: The loaded bytes or None
    """
    if source.startswith(HTTP_PROTOCOL_URL_HEADER) or source.startswith(
        HTTPS_PROTOCOL_URL_HEADER
    ):
        try:
            with urlopen(source, timeout=30) as response:
                return response.read()
        except URLError:
            return None
    else:
        if os.path.exists(source):
            with open(source, "rb") as f:
                return f.read()
        return None


class Image(ImageBase):
    """
    ImageStag's default class for storing image data in all common pixel formats.

    The data is internally either stored using the PILLOW image library's Image
    class or as a classical numpy array, depending on how it was initialized.
    If not specified otherwise it will always the PILLOW representation
    as this is very well suited to visualize the data or modify it.

    If you want to access the data directly you can at all times call the to_pil
    or get_pixels function.
    """

    def __init__(
        self,
        source: ImageSourceTypes | None = None,
        framework: ImsFramework | Literal["PIL", "RAW", "CV"] = None,
        pixel_format: PixelFormatTypes | None = None,
        size: Size2DTypes | None = None,
        bg_color: ColorTypes | None = None,
        **params,
    ):
        """
        :param source: The image source. Either a file name, a http URL,
            numpy array or one of the supported low level types. Note that
            the pixel source you refer, e.g. a PIL image or a numpy array
            might be referenced directly and modified by this object.
        :param framework: The framework to be used if the file is loaded from
            disk
        :param pixel_format: The pixel format - if the data was passed
            as np.array. RGB by default.
        :param size: The size of the new image - if no source is passed.
        :param bg_color: The background color of the new image
        :param params: Additional loading parameters

        Raises a ValueError if the image could not be loaded
        """
        self.framework = (
            ImsFramework(framework) if framework is not None else ImsFramework.PIL
        )
        "The framework being used. ImsFramework.PIL by default."
        self.metadata: dict = {}
        "Arbitrary metadata attached to this image."
        if pixel_format is not None and isinstance(pixel_format, str):
            pixel_format = PixelFormat(pixel_format)
        if size is not None:
            size = Size2D(size) if not isinstance(size, Size2D) else size
        bg_color = Color(bg_color).to_int_rgb_auto() if bg_color is not None else None

        if self.framework != self.framework.PIL:
            if source is not None and size is not None:
                raise ValueError(
                    "Source and size may only be specified at the same time for "
                    "images initialized with PIL"
                )

        if source is None and size is not None:
            if bg_color is None:
                bg_color = Colors.BLACK.to_int_rgb()
            if pixel_format is None:
                pixel_format = PixelFormat.RGB
            # Create a blank image
            pil_mode = pixel_format.to_pil() or "RGB"
            self._pil_handle = PIL.Image.new(pil_mode, size.to_int_tuple(), bg_color)
            self.width = self._pil_handle.width
            self.height = self._pil_handle.height
            self.pixel_format = pixel_format
            self._pixel_data = None
            self._compressed_data = None
            self._compressed_mime = None
            self.initialized = True
            self._read_only = {"width", "height", "pixel_format", "framework"}
            return

        if pixel_format is None:
            pixel_format = PixelFormat.RGB
        self.width = 1
        "The image's width in pixels"
        self.height = 1
        "The image's height in pixels"
        self._pil_handle: PIL.Image.Image | None = None
        "The PILLOW handle (if available)"
        self._pixel_data: np.ndarray | None = None
        "The pixel data (if available) as numpy array"
        self._compressed_data: bytes | None = None
        "Compressed image data (JPEG, PNG, etc.) if in compressed mode"
        self._compressed_mime: str | None = None
        "MIME type of compressed data (e.g., 'image/jpeg')"
        self.pixel_format: PixelFormat = pixel_format
        "The base format (rgb, rgba, bgr etc.)"
        # ------- preparation of source data -------
        source, self.pixel_format = self._prepare_data_source(
            self.framework, source, self.pixel_format, **params
        )
        # ------------------------------------------
        if self.framework == ImsFramework.PIL:
            self._init_as_pil(source)
        elif self.framework == ImsFramework.RAW:
            self._pixel_data = self._pixel_data_from_source(source)
            self.height, self.width = self._pixel_data.shape[0:2]
            self.pixel_format = self.detect_format(self._pixel_data)
        elif self.framework == ImsFramework.CV:
            self._init_as_cv2(source)
        else:
            raise NotImplementedError
        self.initialized = True
        self._read_only = {"width", "height", "pixel_format", "framework"}

    def __setattr__(self, key, value):
        if "_read_only" in self.__dict__:
            if key in self.__dict__ and key not in ('metadata',):
                raise ValueError(f"{key} can not be modified after initialization")
        self.__dict__[key] = value

    def _repr_png_(self) -> bytes:
        """
        PNG representation for Jupyter

        :return: The PNG data
        """
        return self.to_png()

    @classmethod
    def _prepare_data_source(
        cls,
        framework: ImsFramework,
        source: ImageSourceTypes,
        pixel_format: PixelFormat,
        **params,
    ):
        """
        Prepares and if necessary converts the data source to a supported format

        :param framework: The framework being used
        :param source: The source, a byte stream, a filename or a http URL
        :param params: Source protocol dependent, additional loading parameters
        :return: The prepared source data
        """
        if isinstance(source, cls):
            pixel_format = source.pixel_format
            if framework == ImsFramework.PIL:
                source = source.to_pil()  # no copy needed if read-only
            else:
                source = source.get_pixels()
        if (
            isinstance(source, np.ndarray)
            and pixel_format == PixelFormat.BGR
            and framework != ImsFramework.CV
        ):
            source = cls.normalize_to_rgb(
                source, keep_gray=True, input_format=pixel_format
            )
            pixel_format = cls.detect_format(source)
        # fetch from file or web if desired
        if isinstance(source, str):
            loaded = _load_from_source(source, **params)
            if loaded is None:
                raise ValueError("Image data could not be received")
            source = loaded
        return source, pixel_format

    def _init_as_cv2(self, source: np.ndarray):
        """
        Initializes the image from a numpy array and assuming OpenCV's BGR /
        BGRA color channel order

        :param source: The data source
        """
        if isinstance(source, np.ndarray):
            self._pixel_data = self.normalize_to_bgr(
                source, input_format=self.pixel_format, keep_gray=True
            )
            self.pixel_format = self.detect_format(self._pixel_data, is_cv2=True)
        else:
            self._pixel_data = Image(source).get_pixels(PixelFormat.BGR)
            self.pixel_format = self.detect_format(self._pixel_data, is_cv2=True)
        self.height, self.width = self._pixel_data.shape[0:2]

    def _init_as_pil(
        self,
        source: bytes | np.ndarray | PIL.Image.Image,
    ):
        """
        Initializes the image as PIL image

        :param source: The data source
        """
        try:
            if isinstance(source, bytes):
                data = io.BytesIO(source)
                self._pil_handle = PIL.Image.open(data)
                self._pil_handle.load()
            elif isinstance(source, np.ndarray):
                if not source.dtype == np.uint8:
                    raise ValueError("Unsupported array source")
                self._pil_handle = PIL.Image.fromarray(source)
            elif isinstance(source, PIL.Image.Image):
                self._pil_handle = source
            else:
                raise NotImplementedError
        except PIL.UnidentifiedImageError:
            raise ValueError("Invalid or damaged image data")
        if self._pil_handle.mode == "P":
            if "transparency" in self._pil_handle.info:
                self._pil_handle = self._pil_handle.convert("RGBA")
            else:
                self._pil_handle = self._pil_handle.convert("RGB")
        self.width = self._pil_handle.width
        self.height = self._pil_handle.height
        pf = self._pil_handle.mode.lower()
        self.pixel_format = PixelFormat.from_pil(pf)

    def is_bgr(self) -> bool:
        """
        Returns if the current format is bgr or bgra

        :return: True if the image currently in bgr or bgra format
        """
        return (
            self.pixel_format == PixelFormat.BGR
            or self.pixel_format == PixelFormat.BGRA
        )

    @property
    def size(self) -> tuple[int, int]:
        """
        Returns the image's size in pixels

        :return: The size as tuple (width, height)
        """
        return self.width, self.height

    def get_size(self) -> tuple[int, int]:
        """
        Returns the image's size in pixels

        :return: The size as tuple (width, height)
        """
        return self.width, self.height

    def get_size_as_size(self) -> Size2D:
        """
        Returns the image's size

        :return: The size
        """
        return Size2D(self.width, self.height)

    def cropped(self, box: Bounding2DTypes) -> Image:
        """
        Crops a region of the image and returns it

        :param box: The box in the form x, y, x2, y2
        :return: The image of the defined subregion
        """
        box = Bounding2D(box)
        box = box.to_int_coord_tuple()
        if box[2] < box[0] or box[3] < box[1]:
            raise ValueError("X2 or Y2 are not allowed to be smaller than X or Y")
        if box[0] < 0 or box[1] < 0 or box[2] > self.width or box[3] > self.height:
            raise ValueError("Box region out of image bounds")
        if self._pil_handle:
            return Image(self._pil_handle.crop(box=box))
        else:
            cropped = (
                self._pixel_data[box[1] : box[3], box[0] : box[2], :]
                if len(self._pixel_data.shape) == 3
                else self._pixel_data[box[1] : box[3] + 1, box[0] : box[2] + 1]
            )
            return Image(
                cropped, framework=self.framework, pixel_format=self.pixel_format
            )

    def resize(
        self,
        size: Size2DTypes,
        interpolation: InterpolationMethod = InterpolationMethod.LANCZOS,
    ):
        """
        Resizes the image to given resolution (modifying this image directly)

        :param size: The new size
        :param interpolation: The interpolation method.
        """
        resample_method = interpolation.to_pil()
        resample_method_cv = interpolation.to_cv()
        size = Size2D(size).to_int_tuple()
        if size[0] == self.width and size[1] == self.height:
            return
        if self.framework == ImsFramework.PIL:
            self.__dict__["_pil_handle"] = self._pil_handle.resize(
                size, resample=resample_method
            )
        else:
            cv = get_opencv()
            if cv is not None:
                self.__dict__["_pixel_data"] = cv.resize(
                    self._pixel_data, dsize=size, interpolation=resample_method_cv
                )
            else:
                image = Image(
                    self._pixel_data,
                    framework=ImsFramework.PIL,
                    pixel_format=self.pixel_format,
                )
                image.resize(size, interpolation=interpolation)
                self.__dict__["_pixel_data"] = image.get_pixels(
                    desired_format=self.pixel_format
                )
        self.__dict__["width"], self.__dict__["height"] = size

    def resized(
        self,
        size: Size2DTypes,
        interpolation: InterpolationMethod = InterpolationMethod.LANCZOS,
    ) -> Image:
        """
        Returns an image resized to given resolution

        :param size: The new size
        :param interpolation: The interpolation method.
        """
        size = Size2D(size).to_int_tuple()
        if self.width == size[0] and self.height == size[1]:
            return self
        resample_method = interpolation.to_pil()
        if self.framework == ImsFramework.PIL:
            return Image(
                self._pil_handle.resize(size, resample=resample_method),
                framework=ImsFramework.PIL,
            )
        else:
            return Image(self.to_pil().resize(size, resample=resample_method))

    def resized_ext(
        self,
        size: Size2DTypes | None = None,
        max_size: (
            Size2DTypes | int | float | tuple[int | None, int | None] | None
        ) = None,
        keep_aspect: bool = False,
        target_aspect: float | None = None,
        fill_area: bool = False,
        factor: float | tuple[float, float] | None = None,
        interpolation: InterpolationMethod = InterpolationMethod.LANCZOS,
        background_color=Color(0.0, 0.0, 0.0, 1.0),
    ) -> Image:
        """
        Returns a resized variant of the image with many configuration
        possibilities.

        :param size: The target size as tuple (in pixels) (optional)
        :param max_size: The maximum width and/or height to which the image
            shall be scaled while keeping the aspect_ratio intact.
            You can pass a maximum width, a maximum height or both.
        :param keep_aspect: Defines if the aspect ratio shall be kept.
            if set to true the image will be zoomed or shrunk equally on both
            axis so it fits the target size. False by default.
        :param target_aspect: If defined the image will be forced into given
            aspect ratio by adding "black bars" (or the color you defined in
            "background_color"). Common values are for example 4/3, 16/9 or
            21/9.
        :param fill_area: Defines if the whole area shall be filled with the
            original image. False by default.
        :param factor: Scales the image by given factor. Overwrites size.
        :param interpolation: The interpolation method.
        :param background_color: The color which shall be used to fill the empty
            area, e.g. when a certain aspect ratio is enforced.
        """
        size = Size2D(size).to_int_tuple() if size is not None else None
        if max_size is not None:
            size = self.compute_rescaled_size_from_max_size(
                max_size, self.get_size_as_size()
            )
        handle = self.to_pil()
        resample_method = interpolation.to_pil()
        int_color = background_color.to_int_rgba()
        bordered_image_size = None
        # target image size (including black borders)
        if keep_aspect and size is not None:
            if factor is not None and not isinstance(factor, float):
                raise ValueError("Can not combine a tuple factor with keep_aspect")
            if fill_area:
                factor = max([size[0] / self.width, size[1] / self.height])
                virtual_size = max(int(round(factor * self.width)), 1), max(
                    int(round(factor * self.height)), 1
                )
                ratio = size[0] / virtual_size[0], size[1] / virtual_size[1]
                used_pixels = int(round(self.width * ratio[0])), int(
                    round(self.height * ratio[1])
                )
                offset = (
                    self.width // 2 - used_pixels[0] // 2,
                    self.height // 2 - used_pixels[1] // 2,
                )
                return Image(
                    handle.resize(
                        size,
                        resample=resample_method,
                        box=(
                            offset[0],
                            offset[1],
                            offset[0] + used_pixels[0] - 1,
                            offset[1] + used_pixels[1] - 1,
                        ),
                    )
                )
            else:
                bordered_image_size = size
                factor = min([size[0] / self.width, size[1] / self.height])
        if fill_area:
            raise ValueError(
                "fill_area==True without keep_aspect==True has no effect. "
                "If you anyway just want to "
                + 'fill the whole area with the image just provide "size" and '
                'set "fill_area" to False'
            )
        if target_aspect is not None:
            factor = (1.0, 1.0) if factor is None else factor
            if isinstance(factor, float):
                factor = (factor, factor)
            if size is not None:
                raise ValueError(
                    '"target_aspect" can not be combined with "size" but just '
                    "with factor. "
                    + 'Use "size" + "keep_aspect" instead if you know the desired '
                    "target size already."
                )
            # if the image shall also be resized
            size = int(round(self.width * factor[0])), int(
                round(self.height * factor[1])
            )
            size = max(size[0], 1), max(size[1], 1)  # ensure non-zero size
        if factor is not None:
            if isinstance(factor, float):
                factor = (factor, factor)
            size = (
                int(round(self.width * factor[0])),
                int(round(self.height * factor[1])),
            )
            size = max(size[0], 1), max(size[1], 1)  # ensure non-zero size
        if not (size is not None and size[0] > 0 and size[1] > 0):
            raise ValueError("No valid rescaling parameters provided")
        if size != (self.width, self.height):
            handle = handle.resize(size, resample=resample_method)
        if target_aspect is not None:
            rs = 1.0 / target_aspect
            cur_aspect = self.width / self.height
            if cur_aspect < target_aspect:
                # if cur_aspect is smaller we need to add black bars
                # to the sides
                bordered_image_size = (
                    int(round(self.height * target_aspect * factor[0])),
                    int(round(self.height * factor[1])),
                )
            else:  # otherwise to top and bottom
                bordered_image_size = (
                    int(round(self.width * factor[0])),
                    int(round(self.width * rs ** factor[1])),
                )
            bordered_image_size = (  # ensure non-zero size
                max(1, bordered_image_size[0]),
                max(1, bordered_image_size[1]),
            )
        if bordered_image_size is not None:
            new_image = PIL.Image.new(handle.mode, bordered_image_size, int_color)
            position = (
                new_image.width // 2 - handle.width // 2,
                new_image.height // 2 - handle.height // 2,
            )
            new_image.paste(handle, position)
            return Image(new_image)
        return Image(handle)

    def compute_rescaled_size_from_max_size(
        self, max_size, org_size: Size2D
    ) -> tuple[int, int]:
        """
        Computes the new size of an image after rescaling with a given
        maximum width and/or height and a given original size.

        :param max_size: The maximum size or a tuple containing the maximum
            width, height or both
        :param org_size: The original size
        :return: The effective size in pixels
        """
        if isinstance(max_size, (float, int)):
            max_size = (max_size, max_size)
        if isinstance(max_size, tuple) and len(max_size) == 2:
            max_width = int(round(max_size[0])) if max_size[0] is not None else None
            max_height = int(round(max_size[1])) if max_size[1] is not None else None
        else:
            max_size = Size2D(max_size)
            max_width, max_height = max_size.to_int_tuple()
        if max_width is not None:
            if max_height is not None:
                scaling = min([max_width / self.width, max_height / self.height])
            else:
                scaling = max_width / self.width
        elif max_height is not None:
            scaling = max_height / self.height
        else:
            raise ValueError("Neither a valid maximum width nor height passed")
        return (
            max(int(round(org_size.width * scaling)), 1),
            max(int(round(org_size.height * scaling)), 1),
        )

    def convert(
        self,
        pixel_format: PixelFormat | str,
        bg_fill: ColorTypes | None = None,
        fg_color: ColorTypes | None = None,
    ) -> Image:
        """
        Converts the image's pixel format to another one for example from
        RGB to gray, from RGB to HSV etc.

        :param pixel_format: The new pixel format
        :param bg_fill: For alpha-transparent images only: The color of the
            background of the new non-transparent image.
        :param fg_color: If provided and an image is convert from Grayscale to RGBA
            the gray channel will be interpreted as alpha-channel and the RGB channels
            will be filled with the color provided.
        :return: Self
        """
        pixel_format = PixelFormat(pixel_format)
        original = self._pil_handle
        if original is None:  # ensure a handle is available
            original = self.to_pil()
        pil_format = pixel_format.to_pil()
        if pil_format is None:
            raise NotImplementedError(
                "The conversion to this format is currently not supported"
            )
        if bg_fill is not None:
            bg_fill = Color(bg_fill)
        if (  # first convert to RGB or RGBA if desired
            (pixel_format == PixelFormat.RGBA or pixel_format == PixelFormat.RGB)
            and self.pixel_format == PixelFormat.GRAY
            and fg_color is not None
        ):
            self.convert_gray_to_rgba(fg_color)
            self.convert_to_pil()
            original = self._pil_handle
        if (
            pixel_format == PixelFormat.RGB or bg_fill is not None
        ) and original.mode == "RGBA":
            new_image = Image(
                pixel_format=PixelFormat.RGB, size=self.get_size(), bg_color=bg_fill
            )
            pil_handle = new_image.to_pil()
            pil_handle.paste(original, (0, 0), original)
            self.__dict__["_pil_handle"] = pil_handle
        else:
            self.__dict__["_pil_handle"] = original.convert(pil_format)
        self.__dict__["framework"] = ImsFramework.PIL
        self.__dict__["pixel_format"] = pixel_format
        self.__dict__["_pixel_data"] = None
        return self

    def convert_gray_to_rgba(self, fg_color):
        """
        Converts a grayscale image to an RGBA image.

        The previous gray channel will be used as alpha channel and the color channel
        filled with the color defined.

        :param fg_color: The foreground color
        :return: Self
        """
        if self.pixel_format != PixelFormat.GRAY:
            raise ValueError("Function only supported for grayscale images")
        fg_color = Color(fg_color)
        r, g, b = fg_color.to_int_rgb()
        data = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        gray = self.get_pixels_gray()
        data[:, :, 0:3] = (r, g, b)
        data[:, :, 3] = gray
        self.__dict__["framework"] = ImsFramework.RAW
        self.__dict__["pixel_format"] = PixelFormat.RGBA
        self.__dict__["_pixel_data"] = data
        self.__dict__["_pil_handle"] = None
        return self

    def convert_to_raw(self) -> Image:
        """
        Converts the image to use the RAW framework which is faster if you
        excessively access the pixel data frequently.
        """
        if self.framework == ImsFramework.RAW:
            return self
        self.__dict__["_pixel_data"] = self.get_pixels()
        self.__dict__["_pil_handle"] = None
        self.__dict__["framework"] = ImsFramework.RAW
        return self

    def convert_to_pil(self) -> Image:
        """
        Converts the image to use the PIL framework.
        """
        if self.framework == ImsFramework.PIL:
            return self
        new_format = self.pixel_format.to_pil()
        if new_format is None:
            raise NotImplementedError("This color format is not supported")
        pixels = self.get_pixels()
        self.__dict__["_pil_handle"] = PIL.Image.fromarray(pixels, mode=new_format)
        self.__dict__["_pixel_data"] = None
        self.__dict__["framework"] = ImsFramework.PIL
        return self

    def copy(self) -> Image:
        """
        Creates a copy of this image using the data representation of the
        current image, so a PIL based image will create a new PIL based image
        and a RAW image will create a RAW image copy.

        :return: The copy of this image
        """
        import copy as copy_module

        if self._pil_handle is not None:
            new_image = Image(self.to_pil().copy())
        else:
            new_image = Image(
                copy_module.deepcopy(self._pixel_data),
                pixel_format=self.pixel_format,
                framework=self.framework,
            )
        new_image.metadata = copy_module.deepcopy(self.metadata)
        return new_image

    def get_handle(self) -> np.ndarray | PIL.Image.Image:
        """
        Returns the low level data handle, for example a numpy array or
        a PIL handle.

        :return: The handle
        """
        return (
            self._pil_handle if self.framework == ImsFramework.PIL else self._pixel_data
        )

    @property
    def pixels(self) -> np.ndarray:
        """
        Returns the image's pixel data
        """
        return self.get_pixels()

    def get_pixels(self, desired_format: PixelFormatTypes | None = None) -> np.ndarray:
        """
        Returns the image's pixel data as :class:`np.ndarray`.

        :param desired_format: The desired output pixel format, e.g. see
            :class:`PixelFormat`. By default the own format
        :return: The numpy array containing the pixels
        """
        # Ensure compressed data is decoded before access
        self._ensure_decoded()
        if desired_format is not None:
            desired_format = PixelFormat(desired_format)
        if desired_format is None:
            desired_format = self.pixel_format
        if self.framework != ImsFramework.PIL:  # not PIL
            pixel_data = self._pixel_data
        else:
            image: PIL.Image.Image = self._pil_handle
            # noinspection PyTypeChecker
            pixel_data = np.array(image)
        if self.pixel_format == desired_format:
            return pixel_data
        if self.pixel_format == PixelFormat.RGBA and desired_format == PixelFormat.RGB:
            return pixel_data[:, :, 0:3]
        if self.pixel_format == PixelFormat.RGB and desired_format == PixelFormat.RGBA:
            gray = np.zeros(pixel_data.shape[0:2], dtype=np.uint8)
            gray[:, :] = 255
            return np.dstack((pixel_data, gray))
        to_rgb = desired_format == PixelFormat.RGB or desired_format == PixelFormat.RGBA
        if self.pixel_format not in {PixelFormat.RGB, PixelFormat.RGBA} and to_rgb:
            return self.normalize_to_rgb(pixel_data, input_format=self.pixel_format)
        elif desired_format == PixelFormat.GRAY:
            return self.normalize_to_gray(pixel_data, input_format=self.pixel_format)
        elif desired_format == PixelFormat.BGR or desired_format == PixelFormat.BGRA:
            pixel_data = self.normalize_to_bgr(
                pixel_data, input_format=self.pixel_format
            )
            if pixel_data.shape[2] == 3 and desired_format == PixelFormat.BGRA:
                alpha = (np.ones(pixel_data.shape[0:2]) * 255).astype(np.uint8)
                pixel_data = np.dstack((pixel_data, alpha))
            return pixel_data
        raise NotImplementedError("The request conversion is not supported yet")

    def split(self) -> list[np.ndarray]:
        """
        Returns the single bands as single channels.

        In difference to :meth:`get_pixels` the data is reshaped to
        channel x height x width so each channel can be handled separately.

        :return: The single channels.
        """
        data = self.get_pixels()
        if len(data.shape) == 2:
            return [data]
        else:
            result = np.dsplit(data, data.shape[-1])
            result = [element.reshape((self.height, self.width)) for element in result]
            return result

    @property
    def band_names(self) -> list[str]:
        """
        Returns the names of the single color bands

        :return: The name of the bands
        """
        return self.pixel_format.band_names

    def get_pixels_rgb(self) -> np.ndarray:
        """
        Returns the pixels and ensures they are either rgb or rgba
        """
        return self.get_pixels(desired_format=PixelFormat.RGB)

    def get_pixels_bgr(self) -> np.ndarray:
        """
        Returns the pixels and ensures they are either bgr or bgra
        """
        return self.get_pixels(desired_format=PixelFormat.BGR)

    @property
    def __array_interface__(self) -> dict:
        """
        Conversion to numpy representation

        :return: A dictionary containing shape,typestr and data to be loaded
            into a numpy array
        """
        data = {}
        bands = self.pixel_format.band_count
        data_type = self.pixel_format.data_type
        shape = (
            (self.height, self.width)
            if bands == 1
            else (self.height, self.width, bands)
        )
        data_type_str = (
            "|i1"
            if data_type == int or data_type == np.uint
            else "|f4" if data_type == float else "|u1"
        )
        data["shape"] = shape
        data["typestr"] = data_type_str
        data["version"] = 3
        data["data"] = self.to_pil().tobytes()
        return data

    @staticmethod
    def from_array(
        data: np.ndarray,
        min_val: int | float = None,
        max_val: int | float = None,
        normalize: bool = True,
        cmap: str = "gray",
    ):
        """
        Creates an image from an array

        :param data: The image data as numpy array
        :param min_val: The minimum value. auto-detect by default
        :param max_val: The maximum value. auto-detect by default
        :param normalize: Defines if the values shall be normalized to a range
            from 0..255 for integer or 0..1 for floating point values.
        :param cmap: The color map to apply. gray by default (only gray supported
            without matplotlib)
        :return: The image instance
        """
        if len(data.shape) == 2:
            if cmap == "gray" and not normalize and data.dtype == np.uint8:
                return Image(data)
            # For now, just handle basic gray normalization
            if normalize:
                if min_val is None:
                    min_val = data.min()
                if max_val is None:
                    max_val = data.max()
                if max_val != min_val:
                    data = ((data - min_val) / (max_val - min_val) * 255).astype(
                        np.uint8
                    )
                else:
                    data = np.zeros_like(data, dtype=np.uint8)
            if cmap == "gray":
                return Image(data.astype(np.uint8))
            # For other colormaps, would need matplotlib
            raise NotImplementedError(
                f"Colormap '{cmap}' requires matplotlib. Use 'gray' for basic support."
            )
        else:
            return Image(data)

    def to_cv2(self) -> np.ndarray:
        """
        Converts the pixel data from the current format to it's counter
        type in OpenCV

        :return: The OpenCV numpy data
        """
        return (
            self.get_pixels_bgr()
            if self.pixel_format != PixelFormat.GRAY
            else self.get_pixels(desired_format=PixelFormat.GRAY)
        )

    def get_pixels_gray(self) -> np.ndarray:
        """
        Returns the pixels and ensures they are gray scale
        """
        return self.get_pixels(desired_format=PixelFormat.GRAY)

    def to_pil(self) -> PIL.Image.Image:
        """
        Converts the image to a PIL image object

        :return: The PIL image
        """
        # Ensure compressed data is decoded before access
        self._ensure_decoded()
        if self._pil_handle is not None:
            return self._pil_handle
        else:
            # Explicitly convert to RGB/RGBA for PIL (handles BGR from OpenCV)
            if self.pixel_format in (PixelFormat.RGBA, PixelFormat.BGRA):
                pixel_data = self.get_pixels(PixelFormat.RGBA)
            else:
                pixel_data = self.get_pixels(PixelFormat.RGB)
            return PIL.Image.fromarray(pixel_data)

    def to_canvas(self) -> "Canvas":
        """
        Converts the image to a Canvas for drawing operations.

        The canvas draws directly into this image's PIL pixel data.
        Only works for PIL-backed images - numpy-backed images must be
        converted first as drawing would create a separate copy.

        :return: A Canvas wrapping this image
        :raises NotImplementedError: If image is not PIL-backed
        """
        if self._pil_handle is None:
            raise NotImplementedError(
                "Canvas conversion is only supported for PIL-backed images. "
                "Call to_pil() first to convert, but note that changes won't "
                "affect the original numpy array."
            )
        from .canvas import Canvas

        return Canvas(target_image=self)

    def save(
        self,
        target: str,
        quality: int = 90,
        **params,
    ):
        """
        Saves the image to disk

        :param target: The storage target such as a filename
        :param quality: The image quality between (0 = worst quality) and
            (95 = best quality). >95 = minimal loss
        :param params: See :meth:`~encode`
        :return: True on success
        """
        with open(target, "wb") as output_file:
            extension = os.path.splitext(target)[1]
            data = self.encode(filetype=extension, quality=quality, **params)
            output_file.write(data)
            return data is not None

    def encode(
        self,
        filetype: str | tuple[str, int] = "png",
        quality: int = 90,
        background_color: Color | None = None,
    ) -> bytes | None:
        """
        Compresses the image and returns the compressed file's data as bytes
        object.

        :param filetype: The output file type. Valid types are
            "png", "jpg"/"jpeg", "bmp" and "gif".
        :param quality: The image quality between (0 = worst quality) and
            (95 = best quality). >95 = minimal loss
        :param background_color: The background color to store an RGBA image as
            RGB image.
        :return: The bytes object if no error occurred, otherwise None
        """
        image = self
        if isinstance(filetype, tuple):
            assert (
                len(filetype) == 2
                and isinstance(filetype[0], str)
                and isinstance(filetype[1], int)
            )
            filetype, quality = filetype
        filetype = filetype.lstrip(".").lower()
        if filetype == "jpg":
            filetype = "jpeg"
        if self.is_transparent() and (
            filetype != "png" or background_color is not None
        ):
            color = Colors.WHITE if background_color is None else background_color
            # Create a white background and paste
            bg_image = Image(size=self.get_size(), bg_color=color)
            pil_handle = bg_image.to_pil()
            pil_handle.paste(self.to_pil(), (0, 0), self.to_pil())
            image = Image(pil_handle)
        assert filetype in SUPPORTED_IMAGE_FILETYPE_SET
        parameters = {}
        if filetype.lower() in {"jpg", "jpeg"}:
            assert 0 <= quality <= 100
            parameters["quality"] = quality
        # Convert non-standard pixel formats (HSV, BGR, etc.) to RGB for encoding
        if image.pixel_format not in (PixelFormat.RGB, PixelFormat.RGBA, PixelFormat.GRAY):
            image = image.convert(PixelFormat.RGB)
        output_stream = io.BytesIO()
        image.to_pil().save(output_stream, format=filetype, **parameters)
        data = output_stream.getvalue()
        return data if len(data) > 0 else None

    def to_png(self, quality: int = 90, **params) -> bytes | None:
        """
        Encodes the image as png.

        :param quality: The compression grade (no impact on quality).
        :param params: Advanced encoding params. See :meth:`encode`
        :return: The image as bytes object
        """
        return self.encode("png", quality, **params)

    def to_jpeg(self, quality: int = 90, **params) -> bytes | None:
        """
        Encodes the image as jpeg.

        :param quality: The compression grade.
        :param params: Advanced encoding params. See :meth:`encode`
        :return: The image as bytes object
        """
        return self.encode("jpg", quality, **params)

    # ---- Compressed/Data URL Storage Methods ----

    @classmethod
    def from_compressed(
        cls,
        data: bytes,
        mime_type: str | None = None,
    ) -> 'Image':
        """Create Image from compressed bytes without immediate decoding.

        The image remains in a compressed state until pixel access is needed,
        enabling efficient pipeline transport without decompression overhead.

        :param data: Compressed image bytes (JPEG, PNG, WebP, GIF, BMP)
        :param mime_type: MIME type (auto-detected if not provided)
        :returns: Image in compressed storage mode

        Example::

            # From JPEG bytes
            img = Image.from_compressed(jpeg_bytes)

            # With explicit MIME type
            img = Image.from_compressed(png_bytes, 'image/png')

            # Decode only when needed
            pixels = img.get_pixels()  # Triggers decompression
        """
        import base64

        # Auto-detect MIME type from magic bytes
        if mime_type is None:
            mime_type = cls._detect_mime_type(data)

        # Create image instance without full initialization
        img = object.__new__(cls)
        img._compressed_data = data
        img._compressed_mime = mime_type
        img._pil_handle = None
        img._pixel_data = None
        img.framework = ImsFramework.PIL
        img.metadata = {}

        # Peek at dimensions without fully decoding
        try:
            with PIL.Image.open(io.BytesIO(data)) as pil_img:
                img.width = pil_img.width
                img.height = pil_img.height
                pil_mode = pil_img.mode
                if pil_mode == 'L':
                    img.pixel_format = PixelFormat.GRAY
                elif pil_mode == 'RGBA':
                    img.pixel_format = PixelFormat.RGBA
                else:
                    img.pixel_format = PixelFormat.RGB
        except Exception:
            img.width = 0
            img.height = 0
            img.pixel_format = PixelFormat.RGB

        img.initialized = True
        img._read_only = {"width", "height", "pixel_format", "framework"}
        return img

    @classmethod
    def from_data_url(cls, data_url: str) -> 'Image':
        """Create Image from data URL string.

        Data URLs are commonly used in web contexts. The image remains
        in compressed state until pixel access is needed.

        :param data_url: Data URL like 'data:image/jpeg;base64,...'
        :returns: Image in compressed storage mode

        Example::

            data_url = 'data:image/png;base64,iVBORw0KGgo...'
            img = Image.from_data_url(data_url)
        """
        import base64

        if not data_url.startswith('data:'):
            raise ValueError("Invalid data URL format - must start with 'data:'")

        if ',' not in data_url:
            raise ValueError("Invalid data URL format - missing comma separator")

        # Parse: data:image/jpeg;base64,<encoded_data>
        header, encoded = data_url.split(',', 1)
        # Extract MIME type from header (e.g., 'data:image/jpeg;base64')
        mime_part = header[5:]  # Remove 'data:'
        if ';' in mime_part:
            mime_type = mime_part.split(';')[0]
        else:
            mime_type = mime_part

        data = base64.b64decode(encoded)
        return cls.from_compressed(data, mime_type)

    def to_data_url(
        self,
        format: str = 'jpeg',
        quality: int = 85,
    ) -> str:
        """Convert image to data URL string for web use.

        If the image is already in compressed format matching the requested
        format, uses the cached compressed data to avoid re-encoding.

        :param format: Output format ('jpeg', 'png', 'gif')
        :param quality: JPEG quality (1-100), ignored for PNG
        :returns: Data URL string 'data:image/jpeg;base64,...'

        Example::

            img = Image("photo.jpg")
            data_url = img.to_data_url()  # 'data:image/jpeg;base64,...'

            # Use PNG for transparency
            data_url = img.to_data_url(format='png')
        """
        import base64

        format = format.lower()
        if format == 'jpg':
            format = 'jpeg'

        mime = f'image/{format}'

        # Use cached compressed data if available and matching format
        if (self._compressed_data is not None and
            self._compressed_mime == mime):
            data = self._compressed_data
        else:
            data = self.encode(format, quality=quality)

        encoded = base64.b64encode(data).decode('ascii')
        return f'data:{mime};base64,{encoded}'

    def get_compressed(
        self,
        format: str = 'jpeg',
        quality: int = 85,
    ) -> tuple[bytes, str]:
        """Get compressed bytes and MIME type.

        If the image is already in compressed format matching the requested
        format, returns the cached data. Otherwise encodes to the requested
        format.

        :param format: Target format if encoding needed ('jpeg', 'png', 'gif')
        :param quality: Quality for lossy formats
        :returns: (bytes, mime_type) tuple

        Example::

            data, mime = img.get_compressed('jpeg', quality=80)
            # data is JPEG bytes, mime is 'image/jpeg'
        """
        format = format.lower()
        if format == 'jpg':
            format = 'jpeg'

        mime = f'image/{format}'

        if (self._compressed_data is not None and
            self._compressed_mime == mime):
            return self._compressed_data, self._compressed_mime

        data = self.encode(format, quality=quality)
        return data, mime

    def is_compressed(self) -> bool:
        """Check if image has cached compressed data.

        :returns: True if compressed data is available
        """
        return self._compressed_data is not None

    def _ensure_decoded(self) -> None:
        """Ensure image is decoded for pixel access.

        Called internally before pixel operations to decompress
        images that are in compressed storage mode.
        """
        if self._compressed_data is not None and self._pil_handle is None:
            # Decode compressed data to PIL (bypass read-only protection)
            pil_handle = PIL.Image.open(io.BytesIO(self._compressed_data))
            pil_handle.load()  # Force full load
            self.__dict__["_pil_handle"] = pil_handle
            # Update dimensions if they were unknown
            if self.width == 0:
                self.__dict__["width"] = pil_handle.width
                self.__dict__["height"] = pil_handle.height

    @staticmethod
    def _detect_mime_type(data: bytes) -> str:
        """Detect MIME type from magic bytes.

        :param data: Raw image bytes
        :returns: MIME type string
        """
        if len(data) < 12:
            return 'application/octet-stream'

        # JPEG: FF D8 FF
        if data[:3] == b'\xff\xd8\xff':
            return 'image/jpeg'
        # PNG: 89 50 4E 47 0D 0A 1A 0A
        if data[:4] == b'\x89PNG':
            return 'image/png'
        # WebP: RIFF....WEBP
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'image/webp'
        # BMP: BM
        if data[:2] == b'BM':
            return 'image/bmp'
        # GIF: GIF87a or GIF89a
        if data[:3] == b'GIF':
            return 'image/gif'

        return 'application/octet-stream'

    def to_ipython(self, filetype="png", quality: int = 90, **params) -> Any:
        """
        Converts the image to it's IPython representation, e.g. to allow
            faster visualization via using JPG.

        :param filetype: The file type such as "png" or "jpeg"
        :param quality: The compression level
        :param params: Advanced encoding params. See :meth:`encode`
        :return: The IPython.display.Image
        """
        try:
            from IPython.display import Image as IPImage

            return IPImage(self.encode(filetype=filetype, quality=quality, **params))
        except ModuleNotFoundError:
            raise RuntimeError(
                "Jupyter Notebook not found. "
                "Please install ipython for Jupyter support."
            )

    def is_transparent(self) -> bool:
        """
        Returns if the image is transparent, either alpha transparent or
        color keyed.

        :return: True if the image is transparent
        """
        return (
            self.pixel_format == PixelFormat.BGRA
            or self.pixel_format == PixelFormat.RGBA
        )

    def get_raw_data(self) -> bytes:
        """
        Returns the image's raw pixel data as flattened byte array

        :return: The image's pixel data
        """
        return self.to_pil().tobytes()

    def get_hash(self) -> str:
        """
        Returns an image uniquely identifying it

        :return: The image's hash
        """
        return hashlib.md5(self.to_pil().tobytes()).hexdigest()

    def __eq__(self, other: Image):
        if self.framework == ImsFramework.PIL and other.framework == ImsFramework.PIL:
            return self._pil_handle == other._pil_handle
        if self.pixel_format != other.pixel_format:
            return False
        return np.all(self.get_pixels() == other.get_pixels())

    def __str__(self):
        return (
            f"Image ({self.framework.name} {self.width}x{self.height} "
            f"{''.join(self.pixel_format.band_names)})"
        )


__all__ = ["Image", "ImageSourceTypes", "SUPPORTED_IMAGE_FILETYPES"]
