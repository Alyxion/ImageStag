"""
Tests for the Font and FontRegistry classes.
"""

import pytest

from imagestag import Font, FontRegistry
from imagestag.font_registry import (
    RegisteredFont,
    FONTS_DIR,
    ROBOTO_REGULAR_PATH,
    ROBOTO_BOLD_PATH,
)
from imagestag.text_alignment_definitions import (
    HTextAlignment,
    VTextAlignment,
)


class TestFontRegistry:
    """Tests for FontRegistry class."""

    def test_bundled_fonts_exist(self):
        """Test that bundled fonts are present."""
        assert FONTS_DIR.exists(), "Fonts directory should exist"
        assert ROBOTO_REGULAR_PATH.exists(), "Roboto Regular should be bundled"
        assert ROBOTO_BOLD_PATH.exists(), "Roboto Bold should be bundled"

    def test_license_exists(self):
        """Test that font license is present."""
        license_path = FONTS_DIR / "LICENSE.txt"
        assert license_path.exists(), "Font license should be bundled"

    def test_get_roboto_font(self):
        """Test getting Roboto font from registry."""
        font = FontRegistry.get_font("Roboto", size=24)
        assert font is not None
        assert font.size == 24
        assert isinstance(font, Font)

    def test_get_roboto_bold_font(self):
        """Test getting Roboto Bold font."""
        font = FontRegistry.get_font("Roboto-Bold", size=18)
        assert font is not None
        assert font.size == 18

    def test_get_font_different_sizes(self):
        """Test getting fonts at different sizes."""
        sizes = [8, 12, 16, 24, 36, 48, 72]
        for size in sizes:
            font = FontRegistry.get_font("Roboto", size=size)
            assert font is not None
            assert font.size == size

    def test_get_nonexistent_font(self):
        """Test getting a font that doesn't exist."""
        font = FontRegistry.get_font("NonExistentFont", size=24)
        assert font is None

    def test_get_fonts_returns_dict(self):
        """Test that get_fonts returns a dictionary."""
        fonts = FontRegistry.get_fonts()
        assert isinstance(fonts, dict)
        assert "Roboto" in fonts

    def test_font_caching(self):
        """Test that fonts are cached."""
        # Get same font twice
        font1 = FontRegistry.get_font("Roboto", size=24)
        font2 = FontRegistry.get_font("Roboto", size=24)
        # Should be the same cached object
        assert font1 is font2

    def test_different_sizes_not_cached_together(self):
        """Test that different sizes are cached separately."""
        font1 = FontRegistry.get_font("Roboto", size=24)
        font2 = FontRegistry.get_font("Roboto", size=36)
        assert font1 is not font2
        assert font1.size != font2.size


class TestRegisteredFont:
    """Tests for RegisteredFont class."""

    def test_create_from_data(self):
        """Test creating RegisteredFont from data."""
        font_data = ROBOTO_REGULAR_PATH.read_bytes()
        reg_font = RegisteredFont(
            font_face="TestFont",
            font_data=font_data,
        )
        assert reg_font.font_face == "TestFont"
        assert reg_font.font_data == font_data

    def test_get_handle_returns_font(self):
        """Test that get_handle returns a Font."""
        font_data = ROBOTO_REGULAR_PATH.read_bytes()
        reg_font = RegisteredFont(
            font_face="TestFont",
            font_data=font_data,
        )
        font = reg_font.get_handle(size=24)
        assert font is not None
        assert isinstance(font, Font)
        assert font.size == 24


class TestFont:
    """Tests for Font class."""

    @pytest.fixture
    def roboto_font(self):
        """Get Roboto font for testing."""
        return FontRegistry.get_font("Roboto", size=24)

    def test_font_properties(self, roboto_font):
        """Test font properties."""
        assert roboto_font.size == 24
        assert roboto_font.ascend > 0
        assert roboto_font.descend >= 0
        assert roboto_font.row_height == roboto_font.ascend + roboto_font.descend

    def test_font_handle(self, roboto_font):
        """Test getting font handle."""
        handle = roboto_font.get_handle()
        assert handle is not None
        # PIL ImageFont
        import PIL.ImageFont
        assert isinstance(handle, PIL.ImageFont.FreeTypeFont)

    def test_get_text_size_single_line(self, roboto_font):
        """Test measuring single line text."""
        size = roboto_font.get_text_size("Hello")
        assert size.width > 0
        assert size.height > 0
        assert size.height == roboto_font.row_height

    def test_get_text_size_multi_line(self, roboto_font):
        """Test measuring multi-line text."""
        size = roboto_font.get_text_size("Hello\nWorld")
        assert size.width > 0
        assert size.height == roboto_font.row_height * 2

    def test_get_text_size_with_lines(self, roboto_font):
        """Test measuring text with line output."""
        lines = []
        roboto_font.get_text_size("Line1\nLine2\nLine3", out_lines=lines)
        assert len(lines) == 3
        assert lines == ["Line1", "Line2", "Line3"]

    def test_get_text_size_with_widths(self, roboto_font):
        """Test measuring text with width output."""
        widths = []
        roboto_font.get_text_size("Short\nLongerLine", out_widths=widths)
        assert len(widths) == 2
        assert widths[1] > widths[0]  # Longer line has greater width

    def test_get_text_size_empty_string(self, roboto_font):
        """Test measuring empty string."""
        size = roboto_font.get_text_size("")
        assert size.width == 0
        assert size.height == roboto_font.row_height

    def test_get_y_offset_top(self, roboto_font):
        """Test Y offset for top alignment."""
        offset = roboto_font.get_y_offset(VTextAlignment.TOP)
        assert offset == 0

    def test_get_y_offset_bottom(self, roboto_font):
        """Test Y offset for bottom alignment."""
        offset = roboto_font.get_y_offset(VTextAlignment.BOTTOM)
        assert offset == -roboto_font.row_height

    def test_get_y_offset_center(self, roboto_font):
        """Test Y offset for center alignment."""
        offset = roboto_font.get_y_offset(VTextAlignment.CENTER)
        assert offset == -roboto_font.ascend // 2

    def test_get_y_offset_baseline(self, roboto_font):
        """Test Y offset for baseline alignment."""
        offset = roboto_font.get_y_offset(VTextAlignment.BASELINE)
        assert offset == -roboto_font.ascend

    def test_get_y_offset_from_string(self, roboto_font):
        """Test Y offset using string alignment."""
        offset = roboto_font.get_y_offset("t")  # top
        assert offset == 0
        offset = roboto_font.get_y_offset("b")  # bottom
        assert offset == -roboto_font.row_height

    def test_get_covered_area(self, roboto_font):
        """Test getting covered area for text."""
        from imagestag.bounding import Bounding2D
        area = roboto_font.get_covered_area("Hello")
        assert isinstance(area, Bounding2D)
        assert area.width() > 0
        assert area.height() > 0

    def test_get_covered_area_with_alignment(self, roboto_font):
        """Test covered area respects alignment."""
        area_left = roboto_font.get_covered_area("Test", h_align=HTextAlignment.LEFT)
        area_right = roboto_font.get_covered_area("Test", h_align=HTextAlignment.RIGHT)
        # Right-aligned text should have negative x start (pos.x)
        assert area_right.pos.x < area_left.pos.x

    def test_font_from_bytes(self):
        """Test creating font from bytes."""
        font_data = ROBOTO_REGULAR_PATH.read_bytes()
        font = Font(source=font_data, size=16)
        assert font is not None
        assert font.size == 16

    def test_font_from_path(self):
        """Test creating font from file path."""
        font = Font(source=str(ROBOTO_REGULAR_PATH), size=20)
        assert font is not None
        assert font.size == 20


class TestFontWithCanvas:
    """Tests for Font integration with Canvas."""

    def test_canvas_text_rendering(self):
        """Test rendering text on canvas with font."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            canvas.text((10, 10), "Hello World", color=Colors.BLACK, font=font)
            img = canvas.to_image()
            assert img is not None
            assert img.width == 200
            assert img.height == 100

    def test_canvas_get_font(self):
        """Test getting font through canvas."""
        from imagestag import Canvas

        canvas = Canvas(size=(100, 100))
        font = canvas.get_font("Roboto", size=24)
        assert font is not None
        assert font.size == 24

    def test_canvas_get_default_font(self):
        """Test getting default font through canvas."""
        from imagestag import Canvas

        canvas = Canvas(size=(100, 100))
        font = canvas.get_default_font()
        assert font is not None
        assert font.size == 24  # Default size

    def test_canvas_get_default_font_with_size(self):
        """Test getting default font with custom size."""
        from imagestag import Canvas

        canvas = Canvas(size=(100, 100))
        font = canvas.get_default_font(size=32)
        assert font is not None
        assert font.size == 32

    def test_canvas_get_default_font_with_factor(self):
        """Test getting default font with size factor."""
        from imagestag import Canvas

        canvas = Canvas(size=(100, 100))
        font = canvas.get_default_font(size_factor=2.0)
        assert font is not None
        assert font.size == 48  # 24 * 2.0
