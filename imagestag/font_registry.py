"""
Font registry for managing available fonts in ImageStag.

This module provides a font registry that:
1. Uses bundled fonts from the assets/fonts directory
2. Falls back to downloading fonts if bundled fonts are not available
3. Caches fonts for performance
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .font import Font

logger = logging.getLogger(__name__)

# Path to bundled fonts
ASSETS_DIR = Path(__file__).parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

# Bundled font files
ROBOTO_REGULAR_PATH = FONTS_DIR / "Roboto-Regular.ttf"
ROBOTO_BOLD_PATH = FONTS_DIR / "Roboto-Bold.ttf"

# Fallback download URLs (Google Fonts) - used if bundled fonts not available
ROBOTO_REGULAR_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
ROBOTO_BOLD_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"


class RegisteredFont:
    """
    A registered font contains information about a single available font and
    it's style variations.

    Upon request it can be used to create a real font handle with the specified
    properties such as weight and style.
    """

    def __init__(
        self,
        font_face: str,
        base_path: str | None = None,
        variations: list[tuple[str, set[str]]] | None = None,
        font_data: bytes | None = None,
    ):
        """
        Initialize a registered font.

        :param font_face: The font's face name, e.g. Roboto
        :param base_path: Base file name without extension,
            e.g. /home/user/myProject/fonts/Roboto
        :param variations: The single font variations. The flags (e.g. "Bold")
            as string and the file name extension, e.g. "-Bold"
        :param font_data: Raw font data bytes (alternative to base_path)
        """
        self.font_face = font_face
        self.base_path = base_path
        self.extension = ".ttf"
        self.variations = variations or [("", set())]
        self.font_data = font_data
        self._cached_fonts: dict[tuple[int, frozenset], "Font"] = {}
        self._cache_lock = RLock()

    def get_handle(self, size: int, flags: set[str] | None = None) -> "Font | None":
        """
        Tries to create a font handle for given font.

        :param size: The font's size
        :param flags: The flags such as {'Bold'} or {'Bold', 'Italic'}
        :return: On success the handle of the font
        """
        if flags is None:
            flags = set()

        cache_key = (size, frozenset(flags))

        with self._cache_lock:
            if cache_key in self._cached_fonts:
                return self._cached_fonts[cache_key]

        from .font import Font
        from .definitions import ImsFramework

        font = None

        # Try loading from font_data first
        if self.font_data is not None:
            try:
                font = Font(source=self.font_data, size=size, framework=ImsFramework.PIL)
            except Exception as e:
                logger.warning(f"Failed to load font from data: {e}")

        # Try loading from base_path
        if font is None and self.base_path is not None:
            for variation in self.variations:
                if flags == variation[1]:
                    full_name = self.base_path + variation[0] + self.extension
                    if os.path.exists(full_name):
                        try:
                            with open(full_name, "rb") as f:
                                data = f.read()
                            font = Font(source=data, size=size, framework=ImsFramework.PIL)
                            break
                        except Exception as e:
                            logger.warning(f"Failed to load font from {full_name}: {e}")

        if font is not None:
            with self._cache_lock:
                self._cached_fonts[cache_key] = font

        return font


class FontRegistry:
    """
    Manages all available fonts which can be used from ImageStag.

    Provides a simple interface to get fonts by name with automatic
    fallback to system fonts or downloaded fonts.
    """

    access_lock = RLock()
    "Multi-thread access lock"
    _base_fonts_registered = False
    "Defines if the base fonts were configured already"
    fonts: dict[str, RegisteredFont] = {}
    "Dictionary of registered fonts"
    _cache_dir: Path | None = None
    "Directory for caching downloaded fonts"

    @classmethod
    def _get_cache_dir(cls) -> Path:
        """Get or create the font cache directory."""
        if cls._cache_dir is None:
            # Use user's cache directory
            cache_base = Path.home() / ".cache" / "imagestag" / "fonts"
            cache_base.mkdir(parents=True, exist_ok=True)
            cls._cache_dir = cache_base
        return cls._cache_dir

    @classmethod
    def register_font(
        cls,
        font_face: str,
        base_path: str | None = None,
        variations: list[tuple[str, set[str]]] | None = None,
        font_data: bytes | None = None,
    ):
        """
        Registers a single font.

        :param font_face: The font's face name, e.g. Roboto
        :param base_path: Base file name without extension
        :param variations: The single font variations
        :param font_data: Raw font data bytes (alternative to base_path)
        """
        if not cls._base_fonts_registered:
            cls._ensure_setup()
        with cls.access_lock:
            if font_face in cls.fonts:
                raise ValueError(f"Font '{font_face}' was already registered")
            cls.fonts[font_face] = RegisteredFont(
                font_face=font_face,
                base_path=base_path,
                variations=variations,
                font_data=font_data,
            )

    @classmethod
    def get_font(
        cls, font_face: str, size: int, flags: set[str] | None = None
    ) -> "Font | None":
        """
        Tries to create a font handle for given font.

        :param font_face: The font's face
        :param size: The font's size in points
        :param flags: The flags such as {'Bold'} or {'Bold', 'Italic'}
        :return: On success the handle of the font
        """
        if not cls._base_fonts_registered:
            cls._ensure_setup()
        reg_font = None
        with cls.access_lock:
            if font_face in cls.fonts:
                reg_font = cls.fonts[font_face]
            if reg_font is None:
                return None
        return reg_font.get_handle(size, flags)

    @classmethod
    def get_fonts(cls) -> dict[str, RegisteredFont]:
        """
        Returns a list of all fonts.

        :return: A dictionary of all registered fonts
        """
        with cls.access_lock:
            import copy
            return copy.copy(cls.fonts)

    @classmethod
    def _ensure_setup(cls):
        """Ensures the standard fonts were set up."""
        with cls.access_lock:
            if not cls._base_fonts_registered:
                cls._base_fonts_registered = True
                cls._register_base_fonts()

    @classmethod
    def _download_font(cls, url: str, name: str) -> bytes | None:
        """Download a font from URL and cache it."""
        cache_dir = cls._get_cache_dir()
        cache_file = cache_dir / name

        # Check cache first
        if cache_file.exists():
            try:
                return cache_file.read_bytes()
            except Exception:
                pass

        # Download
        try:
            import urllib.request
            logger.info(f"Downloading font: {name}")
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read()
            # Cache for next time
            try:
                cache_file.write_bytes(data)
            except Exception as e:
                logger.warning(f"Failed to cache font: {e}")
            return data
        except Exception as e:
            logger.warning(f"Failed to download font from {url}: {e}")
            return None

    @classmethod
    def _try_system_font(cls, font_names: list[str], size: int) -> "Font | None":
        """Try to load a system font by name."""
        import PIL.ImageFont
        from .font import Font
        from .definitions import ImsFramework

        for name in font_names:
            try:
                # PIL will search system font paths
                pil_font = PIL.ImageFont.truetype(name, size)
                # Create Font wrapper
                font = Font(source=name, size=size, framework=ImsFramework.PIL)
                return font
            except Exception:
                continue
        return None

    @classmethod
    def _load_bundled_font(cls, path: Path) -> bytes | None:
        """Load a font from the bundled assets directory.

        :param path: Path to the font file
        :return: Font data bytes or None if not found
        """
        if path.exists():
            try:
                return path.read_bytes()
            except Exception as e:
                logger.warning(f"Failed to load bundled font {path}: {e}")
        return None

    @classmethod
    def _register_base_fonts(cls):
        """Registers the standard fonts - uses bundled fonts first, downloads if needed."""
        # Try bundled fonts first
        roboto_data = cls._load_bundled_font(ROBOTO_REGULAR_PATH)
        roboto_bold_data = cls._load_bundled_font(ROBOTO_BOLD_PATH)

        # Fall back to download if bundled fonts not available
        if roboto_data is None:
            logger.info("Bundled Roboto font not found, downloading...")
            roboto_data = cls._download_font(ROBOTO_REGULAR_URL, "Roboto-Regular.ttf")
        if roboto_bold_data is None:
            roboto_bold_data = cls._download_font(ROBOTO_BOLD_URL, "Roboto-Bold.ttf")

        if roboto_data:
            # Register with data
            cls.fonts["Roboto"] = RegisteredFont(
                font_face="Roboto",
                font_data=roboto_data,
                variations=[("", set())],
            )

            # If we have bold, create a variation-aware registration
            if roboto_bold_data:
                # Store bold data separately for now
                cls.fonts["Roboto-Bold"] = RegisteredFont(
                    font_face="Roboto-Bold",
                    font_data=roboto_bold_data,
                    variations=[("", {"Bold"})],
                )


__all__ = ["FontRegistry", "RegisteredFont"]
