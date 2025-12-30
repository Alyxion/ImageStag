"""
ASCII Art Renderer - Convert images to colored ASCII/Unicode art.

Supports multiple rendering modes:
- Block mode: Uses Unicode block characters for high-fidelity color output
- ASCII mode: Uses ASCII characters based on luminance
- Half-block mode: Uses ▀ character to double vertical resolution

Example:
    from imagestag import Image
    from imagestag.components.ascii import AsciiRenderer

    img = Image.load("photo.jpg")
    renderer = AsciiRenderer(width=80)
    print(renderer.render(img))
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from imagestag.image import Image

# ANSI escape codes
ESC = "\033"
RESET = f"{ESC}[0m"

# Character sets ordered from dark to bright
ASCII_CHARS_10 = " .:-=+*#%@"
ASCII_CHARS_69 = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

# Unicode block characters
FULL_BLOCK = "█"
UPPER_HALF = "▀"
LOWER_HALF = "▄"
LIGHT_SHADE = "░"
MEDIUM_SHADE = "▒"
DARK_SHADE = "▓"


class RenderMode(Enum):
    """Rendering mode for ASCII art."""

    BLOCK = "block"  # Full block characters with foreground color
    HALF_BLOCK = "half_block"  # Half blocks for 2x vertical resolution
    ASCII = "ascii"  # ASCII characters based on luminance (not recommended)
    ASCII_COLOR = "ascii_color"  # Colored ASCII characters
    ASCII_EDGE = "ascii_edge"  # ASCII with edge detection (Sobel filter)
    BRAILLE = "braille"  # Braille characters (highest resolution)


class AsciiRenderer:
    """
    High-performance ASCII/Unicode art renderer with true color support.

    Features:
    - Multiple render modes (block, half-block, ASCII, braille)
    - True color (24-bit) ANSI escape codes
    - Automatic terminal size detection
    - Optimized numpy-based rendering
    """

    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        mode: RenderMode = RenderMode.HALF_BLOCK,
        charset: str = ASCII_CHARS_69,
        max_height: int | None = None,
        char_aspect: float = 0.45,
        margin_x: int = 4,
        margin_y: int = 2,
    ):
        """
        Initialize the ASCII renderer.

        :param width: Output width in characters (None = auto-detect with margins)
        :param height: Output height in characters (None = auto from aspect ratio)
        :param mode: Rendering mode
        :param charset: Character set for ASCII modes (dark to bright)
        :param max_height: Maximum output height in lines (None = auto-detect)
        :param char_aspect: Width/height ratio of terminal chars (default 0.45)
        :param margin_x: Horizontal margin in characters (default 4)
        :param margin_y: Vertical margin in lines (default 2)
        """
        self.mode = mode
        self.charset = charset
        self.char_aspect = char_aspect
        self.margin_x = margin_x
        self.margin_y = margin_y

        # Auto-detect terminal size
        try:
            term_size = os.get_terminal_size()
            term_width = term_size.columns
            term_height = term_size.lines
        except OSError:
            term_width = 80
            term_height = 24

        # Available space after margins
        available_width = term_width - (margin_x * 2)
        available_height = term_height - (margin_y * 2)

        # Apply width (auto-detect uses available space, or explicit)
        if width is None:
            self.width = max(10, available_width)
        else:
            self.width = min(width, available_width)

        self.height = height

        # Apply max_height (auto-detect or explicit)
        if max_height is None:
            self.max_height = max(5, available_height)
        else:
            self.max_height = min(max_height, available_height)

    def render(self, image: "Image") -> str:
        """
        Render an image as ASCII/Unicode art.

        :param image: Image to render
        :return: String with ANSI escape codes for colored output
        """
        # Calculate target dimensions
        aspect_ratio = image.height / image.width

        if self.mode == RenderMode.HALF_BLOCK:
            # Half blocks give us 2x vertical resolution
            target_width = self.width
            if self.height:
                target_height = self.height * 2  # 2 pixels per char vertically
            else:
                target_height = int(target_width * aspect_ratio * self.char_aspect * 2)
            # Limit to max_height (in output lines, so multiply by 2 for pixels)
            if self.max_height:
                max_pixels = self.max_height * 2
                if target_height > max_pixels:
                    target_height = max_pixels
            # Make height even for half-block pairing
            target_height = (target_height // 2) * 2
        elif self.mode == RenderMode.BRAILLE:
            # Braille gives us 2x4 dots per character
            target_width = self.width * 2
            if self.height:
                target_height = self.height * 4
            else:
                target_height = int(target_width * aspect_ratio * self.char_aspect * 4)
            # Limit to max_height (in output lines, so multiply by 4 for pixels)
            if self.max_height:
                max_pixels = self.max_height * 4
                if target_height > max_pixels:
                    target_height = max_pixels
            target_height = (target_height // 4) * 4
        else:
            target_width = self.width
            if self.height:
                target_height = self.height
            else:
                target_height = int(target_width * aspect_ratio * self.char_aspect)
            # Limit to max_height
            if self.max_height and target_height > self.max_height:
                target_height = self.max_height

        # Resize image
        resized = image.resized((target_width, max(1, target_height)))

        # Get RGB pixels
        pixels = resized.get_pixels()
        if pixels.ndim == 2:
            # Grayscale - expand to RGB
            pixels = np.stack([pixels, pixels, pixels], axis=-1)
        elif pixels.shape[2] == 4:
            # RGBA - drop alpha
            pixels = pixels[:, :, :3]

        # Render based on mode
        if self.mode == RenderMode.BLOCK:
            return self._render_block(pixels)
        elif self.mode == RenderMode.HALF_BLOCK:
            return self._render_half_block(pixels)
        elif self.mode == RenderMode.ASCII:
            return self._render_ascii(pixels, colored=False)
        elif self.mode == RenderMode.ASCII_COLOR:
            return self._render_ascii(pixels, colored=True)
        elif self.mode == RenderMode.ASCII_EDGE:
            return self._render_ascii_edge(pixels)
        elif self.mode == RenderMode.BRAILLE:
            return self._render_braille(pixels)
        else:
            return self._render_block(pixels)

    def _render_block(self, pixels: np.ndarray) -> str:
        """Render using full block characters with foreground color."""
        rows = []
        for row in pixels:
            chars = []
            for r, g, b in row:
                if int(r) + int(g) + int(b) < 30:  # Nearly black
                    chars.append(" ")
                else:
                    chars.append(f"{ESC}[38;2;{r};{g};{b}m{FULL_BLOCK}")
            rows.append("".join(chars))
        rows.append(RESET)
        return "\n".join(rows)

    def _render_half_block(self, pixels: np.ndarray) -> str:
        """
        Render using half-block characters for 2x vertical resolution.

        Uses ▀ (upper half block) with foreground = top pixel, background = bottom pixel.
        This effectively doubles the vertical resolution.
        """
        rows = []
        height = pixels.shape[0]
        width = pixels.shape[1]

        # Calculate padding for centering
        pad_left = " " * self.margin_x

        for y in range(0, height - 1, 2):
            top_row = pixels[y]
            bottom_row = pixels[y + 1]
            line_chars = [pad_left]

            for x in range(width):
                tr, tg, tb = int(top_row[x, 0]), int(top_row[x, 1]), int(top_row[x, 2])
                br, bg, bb = int(bottom_row[x, 0]), int(bottom_row[x, 1]), int(bottom_row[x, 2])

                top_dark = tr + tg + tb < 30
                bottom_dark = br + bg + bb < 30

                if top_dark and bottom_dark:
                    line_chars.append(" ")
                elif top_dark:
                    line_chars.append(f"{ESC}[38;2;{br};{bg};{bb}m{LOWER_HALF}")
                elif bottom_dark:
                    line_chars.append(f"{ESC}[38;2;{tr};{tg};{tb}m{UPPER_HALF}")
                else:
                    line_chars.append(
                        f"{ESC}[38;2;{tr};{tg};{tb};48;2;{br};{bg};{bb}m{UPPER_HALF}"
                    )

            line_chars.append(RESET)
            rows.append("".join(line_chars))

        return "\n".join(rows)

    def _render_ascii(self, pixels: np.ndarray, colored: bool = False) -> str:
        """Render using ASCII characters based on luminance."""
        # Convert to grayscale for character selection
        luminance = (
            0.299 * pixels[:, :, 0]
            + 0.587 * pixels[:, :, 1]
            + 0.114 * pixels[:, :, 2]
        )

        # Map luminance to character indices
        char_indices = (luminance / 255 * (len(self.charset) - 1)).astype(np.int32)
        char_indices = np.clip(char_indices, 0, len(self.charset) - 1)

        rows = []
        for y, row in enumerate(char_indices):
            if colored:
                chars = []
                for x, idx in enumerate(row):
                    r, g, b = pixels[y, x]
                    char = self.charset[idx]
                    if int(r) + int(g) + int(b) < 30:
                        chars.append(" ")
                    else:
                        chars.append(f"{ESC}[38;2;{r};{g};{b}m{char}")
                rows.append("".join(chars) + RESET)
            else:
                rows.append("".join(self.charset[idx] for idx in row))

        return "\n".join(rows)

    def _render_ascii_edge(self, pixels: np.ndarray) -> str:
        """
        Render using ASCII characters with Sobel edge detection.

        Uses gradient magnitude and direction to select appropriate
        line characters that visually match edge shapes and intensity.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)

        # Sobel gradients
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        # Gradient magnitude and direction
        magnitude = np.sqrt(gx**2 + gy**2)
        angles = np.arctan2(gy, gx) * 180 / np.pi

        # Normalize magnitude to 0-255
        mag_max = magnitude.max()
        if mag_max > 0:
            magnitude = (magnitude / mag_max * 255).astype(np.uint8)
        else:
            magnitude = magnitude.astype(np.uint8)

        # Build output character array
        h, w = magnitude.shape
        chars = np.full((h, w), ' ', dtype='U1')

        # Normalize angles to 0-180
        norm_angles = np.abs(angles) % 180

        # Characters by direction and intensity:
        # Light edges: . , ' `
        # Medium edges: - | / \
        # Strong edges: = ║ ╱ ╲ or double chars

        # Thresholds for edge strength
        light = (magnitude > 15) & (magnitude <= 50)
        medium = (magnitude > 50) & (magnitude <= 120)
        strong = magnitude > 120

        # Direction masks
        horiz = (norm_angles >= 67.5) & (norm_angles < 112.5)  # horizontal edge
        vert = (norm_angles < 22.5) | (norm_angles >= 157.5)   # vertical edge
        diag1 = (norm_angles >= 22.5) & (norm_angles < 67.5)   # / diagonal
        diag2 = (norm_angles >= 112.5) & (norm_angles < 157.5) # \ diagonal

        # Light edges - subtle marks
        chars[light & horiz] = '.'
        chars[light & vert] = ':'
        chars[light & diag1] = '`'
        chars[light & diag2] = "'"

        # Medium edges - standard line chars
        chars[medium & horiz] = '-'
        chars[medium & vert] = '|'
        chars[medium & diag1] = '/'
        chars[medium & diag2] = '\\'

        # Strong edges - bold chars
        chars[strong & horiz] = '='
        chars[strong & vert] = '#'
        chars[strong & diag1] = '/'
        chars[strong & diag2] = '\\'

        rows = []
        for row in chars:
            rows.append("".join(row))

        return "\n".join(rows)

    def _render_braille(self, pixels: np.ndarray) -> str:
        """
        Render using Braille characters for highest resolution.

        Each Braille character represents a 2x4 grid of dots.
        Braille Unicode: 0x2800 + dot pattern
        Dot positions: 1 4
                       2 5
                       3 6
                       7 8
        """
        # Convert to binary (threshold)
        gray = (
            0.299 * pixels[:, :, 0]
            + 0.587 * pixels[:, :, 1]
            + 0.114 * pixels[:, :, 2]
        )
        binary = gray > 50  # Threshold

        height, width = binary.shape
        rows = []

        # Braille dot values
        dots = [0x01, 0x02, 0x04, 0x40, 0x08, 0x10, 0x20, 0x80]

        for y in range(0, height - 3, 4):
            chars = []
            for x in range(0, width - 1, 2):
                # Get 2x4 block
                code = 0x2800
                for dy in range(4):
                    for dx in range(2):
                        if y + dy < height and x + dx < width:
                            if binary[y + dy, x + dx]:
                                dot_idx = dy + dx * 4 if dy < 3 else 6 + dx
                                code += dots[dot_idx]

                # Get average color of block for coloring
                block = pixels[y : y + 4, x : x + 2]
                avg_color = block.mean(axis=(0, 1)).astype(int)
                r, g, b = avg_color

                if code == 0x2800:
                    chars.append(" ")
                else:
                    chars.append(f"{ESC}[38;2;{r};{g};{b}m{chr(code)}")

            rows.append("".join(chars) + RESET)

        return "\n".join(rows)


def render_frame_to_terminal(
    image: "Image",
    width: int | None = None,
    mode: RenderMode = RenderMode.HALF_BLOCK,
    clear: bool = True,
) -> None:
    """
    Render an image frame directly to terminal with cursor control.

    :param image: Image to render
    :param width: Output width (None = auto)
    :param mode: Rendering mode
    :param clear: Whether to clear screen / move cursor to top
    """
    renderer = AsciiRenderer(width=width, mode=mode)
    output = renderer.render(image)

    if clear:
        # Move cursor to top-left instead of clearing (less flicker)
        sys.stdout.write(f"{ESC}[H")

    sys.stdout.write(output)
    sys.stdout.write("\n")
    sys.stdout.flush()


__all__ = ["AsciiRenderer", "RenderMode", "render_frame_to_terminal"]
