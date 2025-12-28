"""
Tests for the Canvas class.
"""

import pytest
import numpy as np

from imagestag import (
    Canvas,
    Colors,
    Color,
    Size2D,
    Pos2D,
    PixelFormat,
    Anchor2D,
    HTextAlignment,
    VTextAlignment,
    Font,
    FontRegistry,
)


class TestCanvasConstruction:
    """Tests for Canvas construction."""

    def test_canvas_with_size(self):
        """Test creating canvas with size."""
        canvas = Canvas(size=(300, 256))
        assert canvas.width == 300
        assert canvas.height == 256
        assert canvas.size == (300, 256)

    def test_canvas_with_size2d(self):
        """Test creating canvas with Size2D."""
        canvas = Canvas(size=Size2D(400, 300))
        assert canvas.width == 400
        assert canvas.height == 300

    def test_canvas_grayscale(self):
        """Test creating grayscale canvas."""
        canvas = Canvas(size=(200, 150), pixel_format="L", default_color=0)
        img = canvas.to_image()
        assert img.pixel_format == PixelFormat.GRAY

    def test_canvas_grayscale_gray_format(self):
        """Test creating grayscale canvas with GRAY format."""
        canvas = Canvas(size=(200, 150), pixel_format="GRAY", default_color=0)
        img = canvas.to_image()
        assert img.pixel_format == PixelFormat.GRAY

    def test_canvas_rgba(self):
        """Test creating RGBA canvas."""
        canvas = Canvas(size=(200, 150), pixel_format="RGBA")
        img = canvas.to_image()
        assert img.pixel_format == PixelFormat.RGBA

    def test_canvas_default_color(self):
        """Test canvas with default color."""
        canvas = Canvas(size=(100, 100), default_color=Colors.RED)
        img = canvas.to_image()
        # Verify pixel is red
        pixels = np.array(img.to_pil())
        assert pixels[50, 50, 0] == 255  # Red
        assert pixels[50, 50, 1] == 0  # Green
        assert pixels[50, 50, 2] == 0  # Blue

    def test_canvas_requires_size_or_image(self):
        """Test that canvas requires size or target image."""
        with pytest.raises(ValueError):
            Canvas(size=None, target_image=None)

    def test_canvas_cannot_have_both_size_and_image(self):
        """Test that canvas cannot have both size and target image."""
        from imagestag import Image
        img = Image(np.zeros((100, 100, 3), dtype=np.uint8))
        with pytest.raises(ValueError):
            Canvas(size=(200, 200), target_image=img)

    def test_canvas_immutable_after_creation(self):
        """Test that canvas properties are immutable after creation."""
        canvas = Canvas(size=(100, 100))
        with pytest.raises(RuntimeError):
            canvas.width = 200


class TestCanvasDrawing:
    """Tests for Canvas drawing operations."""

    def test_rect_fill(self):
        """Test drawing filled rectangle."""
        canvas = Canvas(size=(100, 100), default_color=Colors.BLACK)
        canvas.rect((10, 10), (50, 50), color=Colors.RED)
        img = canvas.to_image()
        pixels = np.array(img.to_pil())
        # Check inside rectangle
        assert pixels[35, 35, 0] == 255  # Red
        # Check outside rectangle
        assert pixels[5, 5, 0] == 0  # Black

    def test_rect_outline(self):
        """Test drawing rectangle outline."""
        canvas = Canvas(size=(100, 100), default_color=Colors.BLACK)
        canvas.rect((10, 10), (50, 50), outline_color=Colors.GREEN, outline_width=2)
        img = canvas.to_image()
        pixels = np.array(img.to_pil())
        # Check outline pixel
        assert pixels[10, 10, 1] == 255  # Green

    def test_circle_fill(self):
        """Test drawing filled circle."""
        canvas = Canvas(size=(100, 100), default_color=Colors.BLACK)
        canvas.circle((50, 50), radius=30, color=Colors.BLUE)
        img = canvas.to_image()
        pixels = np.array(img.to_pil())
        # Check center
        assert pixels[50, 50, 2] == 255  # Blue

    def test_ellipse(self):
        """Test drawing ellipse."""
        canvas = Canvas(size=(100, 100), default_color=Colors.BLACK)
        canvas.circle((50, 50), radius=(40, 20), color=Colors.CYAN)
        img = canvas.to_image()
        assert img is not None

    def test_line(self):
        """Test drawing line."""
        canvas = Canvas(size=(100, 100), default_color=Colors.BLACK)
        canvas.line([(10, 10), (90, 90)], color=Colors.WHITE, width=2)
        img = canvas.to_image()
        pixels = np.array(img.to_pil())
        # Check diagonal pixel (approximately)
        assert pixels[50, 50, 0] > 0

    def test_polygon(self):
        """Test drawing polygon."""
        canvas = Canvas(size=(100, 100), default_color=Colors.BLACK)
        points = [(20, 20), (80, 20), (80, 80), (20, 80)]
        canvas.polygon(points, color=Colors.YELLOW)
        img = canvas.to_image()
        pixels = np.array(img.to_pil())
        # Check inside polygon
        assert pixels[50, 50, 0] == 255  # Red component of yellow
        assert pixels[50, 50, 1] == 255  # Green component of yellow


class TestCanvasGrayscaleMask:
    """Tests for creating grayscale masks with Canvas."""

    def test_create_circle_mask(self):
        """Test creating circular mask for layer composition."""
        canvas = Canvas(size=(200, 150), pixel_format="L", default_color=0)
        canvas.circle((100, 75), radius=70, color=255)
        mask = canvas.to_image()
        assert mask.width == 200
        assert mask.height == 150
        assert mask.pixel_format == PixelFormat.GRAY
        # Check center is white (allowing for anti-aliasing)
        pixels = np.array(mask.to_pil())
        assert pixels[75, 100] == 255
        # Check corner is black
        assert pixels[0, 0] == 0

    def test_create_ellipse_mask(self):
        """Test creating elliptical mask."""
        canvas = Canvas(size=(200, 150), pixel_format="GRAY", default_color=0)
        canvas.circle((100, 75), radius=(90, 60), color=255)
        mask = canvas.to_image()
        pixels = np.array(mask.to_pil())
        # Center should be white
        assert pixels[75, 100] == 255

    def test_create_rect_mask(self):
        """Test creating rectangular mask."""
        canvas = Canvas(size=(200, 150), pixel_format="L", default_color=0)
        canvas.rect((25, 25), (150, 100), color=255)
        mask = canvas.to_image()
        pixels = np.array(mask.to_pil())
        # Check inside rect
        assert pixels[75, 100] == 255
        # Check outside rect
        assert pixels[10, 10] == 0


class TestCanvasTransformations:
    """Tests for Canvas transformations."""

    def test_offset_shift(self):
        """Test offset shifting."""
        canvas = Canvas(size=(100, 100))
        canvas.add_offset_shift((10, 20))
        assert canvas.offset == (10, 20)

    def test_push_pop_state(self):
        """Test push and pop state."""
        canvas = Canvas(size=(100, 100))
        canvas.add_offset_shift((10, 20))
        canvas.push_state()
        canvas.add_offset_shift((5, 5))
        assert canvas.offset == (15, 25)
        canvas.pop_state()
        assert canvas.offset == (10, 20)

    def test_transform_list(self):
        """Test transforming coordinate list."""
        canvas = Canvas(size=(100, 100))
        coords = [(10, 10), (20, 20)]
        result = canvas.transform_list(coords)
        assert result == [(10, 10), (20, 20)]

        canvas.add_offset_shift((5, 5))
        result = canvas.transform_list(coords)
        assert result == [(15, 15), (25, 25)]

    def test_transform_pos2d(self):
        """Test transforming Pos2D."""
        canvas = Canvas(size=(100, 100))
        canvas.add_offset_shift((10, 20))
        result = canvas.transform(Pos2D(5, 5))
        assert result == (15, 25)

    def test_clip(self):
        """Test clipping."""
        canvas = Canvas(size=(100, 100))
        canvas.clip((25, 25), (50, 50))
        assert canvas.offset == (25, 25)
        assert canvas.clip_region == ((25, 25), (75, 75))


class TestCanvasClear:
    """Tests for Canvas clear operation."""

    def test_clear_with_color(self):
        """Test clearing canvas with color."""
        canvas = Canvas(size=(100, 100), default_color=Colors.RED)
        canvas.clear(Colors.BLUE)
        img = canvas.to_image()
        pixels = np.array(img.to_pil())
        assert pixels[50, 50, 2] == 255  # Blue


class TestCanvasFont:
    """Tests for Canvas font operations."""

    def test_get_default_font(self):
        """Test getting default font."""
        canvas = Canvas(size=(100, 100))
        font = canvas.get_default_font()
        # Font may be None if download fails, which is acceptable
        if font is not None:
            assert isinstance(font, Font)
            assert font.size == 24

    def test_get_font_with_size(self):
        """Test getting font with custom size."""
        canvas = Canvas(size=(100, 100))
        font = canvas.get_default_font(size=16)
        if font is not None:
            assert font.size == 16

    def test_get_font_with_factor(self):
        """Test getting font with size factor."""
        canvas = Canvas(size=(100, 100))
        font = canvas.get_default_font(size_factor=0.5)
        if font is not None:
            assert font.size == 12


class TestCanvasText:
    """Tests for Canvas text rendering."""

    def test_text_basic(self):
        """Test basic text rendering."""
        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font()
        if font is not None:
            canvas.text((10, 10), "Hello", color=Colors.BLACK, font=font)
            img = canvas.to_image()
            assert img is not None

    def test_text_centered(self):
        """Test centered text."""
        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font()
        if font is not None:
            canvas.text((100, 50), "Centered", color=Colors.BLACK, font=font, center=True)
            img = canvas.to_image()
            assert img is not None


class TestCanvasDrawImage:
    """Tests for Canvas draw_image operation."""

    def test_draw_image(self):
        """Test drawing image onto canvas."""
        from imagestag import Image

        # Create a small red image
        red_img = Image(np.full((20, 20, 3), [255, 0, 0], dtype=np.uint8))

        # Draw onto canvas
        canvas = Canvas(size=(100, 100), default_color=Colors.BLACK)
        canvas.draw_image(red_img, (10, 10))

        result = canvas.to_image()
        pixels = np.array(result.to_pil())
        assert pixels[20, 20, 0] == 255  # Red

    def test_draw_image_with_offset(self):
        """Test drawing image with offset."""
        from imagestag import Image

        red_img = Image(np.full((20, 20, 3), [255, 0, 0], dtype=np.uint8))

        canvas = Canvas(size=(100, 100), default_color=Colors.BLACK)
        canvas.add_offset_shift((10, 10))
        canvas.draw_image(red_img, (0, 0))

        result = canvas.to_image()
        pixels = np.array(result.to_pil())
        assert pixels[20, 20, 0] == 255  # Red (10+10 = 20)


class TestAnchor2D:
    """Tests for Anchor2D."""

    def test_anchor_from_string(self):
        """Test creating anchor from string."""
        assert Anchor2D("tl") == Anchor2D.TOP_LEFT
        assert Anchor2D("center") == Anchor2D.CENTER
        assert Anchor2D("br") == Anchor2D.BOTTOM_RIGHT

    def test_anchor_position_shift(self):
        """Test anchor position shift calculation."""
        size = Size2D(100, 100)

        assert Anchor2D.TOP_LEFT.get_position_shift(size) == (0.0, 0.0)
        assert Anchor2D.CENTER.get_position_shift(size) == (-50.0, -50.0)
        assert Anchor2D.BOTTOM_RIGHT.get_position_shift(size) == (-100.0, -100.0)

    def test_anchor_shift_position(self):
        """Test anchor shift_position method."""
        pos = Pos2D(100, 100)
        size = Size2D(50, 50)

        result = Anchor2D.CENTER.shift_position(pos, size)
        assert result.x == 75.0
        assert result.y == 75.0


class TestTextAlignment:
    """Tests for text alignment enums."""

    def test_h_alignment_from_string(self):
        """Test horizontal alignment from string."""
        assert HTextAlignment("l") == HTextAlignment.LEFT
        assert HTextAlignment("center") == HTextAlignment.CENTER
        assert HTextAlignment("r") == HTextAlignment.RIGHT

    def test_v_alignment_from_string(self):
        """Test vertical alignment from string."""
        assert VTextAlignment("t") == VTextAlignment.TOP
        assert VTextAlignment("center") == VTextAlignment.CENTER
        assert VTextAlignment("bottom") == VTextAlignment.BOTTOM


class TestImageToCanvas:
    """Tests for Image.to_canvas() method."""

    def test_to_canvas_from_pil_image(self):
        """Test converting PIL-backed image to canvas."""
        import PIL.Image
        from imagestag import Image

        # Create a PIL-backed image directly
        pil_img = PIL.Image.new("RGB", (100, 100), (255, 0, 0))
        img = Image(pil_img)

        # Convert to canvas and draw on it
        canvas = img.to_canvas()
        canvas.rect(pos=(10, 10), size=(20, 20), color=Colors.GREEN)

        # Verify drawing affected the original image
        pixels = np.array(img.to_pil())
        assert pixels[20, 20, 0] == 0  # Not red anymore
        assert pixels[20, 20, 1] == 255  # Green (0, 255, 0)

    def test_to_canvas_cv2_raises(self):
        """Test that CV2-backed (numpy) images raise NotImplementedError."""
        from imagestag import Image
        from imagestag.definitions import ImsFramework

        # Create a CV2-backed image (numpy array storage)
        pixels = np.full((100, 100, 3), [0, 0, 255], dtype=np.uint8)
        img = Image(pixels, framework=ImsFramework.CV)

        # Should raise because CV2 images can't be drawn on in-place
        with pytest.raises(NotImplementedError):
            img.to_canvas()

    def test_to_canvas_preserves_dimensions(self):
        """Test that canvas has same dimensions as image."""
        import PIL.Image
        from imagestag import Image

        pil_img = PIL.Image.new("RGB", (300, 200), (0, 0, 0))
        img = Image(pil_img)
        canvas = img.to_canvas()

        assert canvas.width == 300
        assert canvas.height == 200

    def test_to_canvas_modifies_original(self):
        """Test that drawing on canvas modifies the original image."""
        import PIL.Image
        from imagestag import Image

        # Create PIL image
        pil_img = PIL.Image.new("RGB", (100, 100), (0, 0, 0))
        img = Image(pil_img)

        # Draw on canvas
        canvas = img.to_canvas()
        canvas.circle((50, 50), radius=20, color=Colors.WHITE)

        # Original image should be modified
        pixels = np.array(img.to_pil())
        assert pixels[50, 50, 0] == 255  # White center
        assert pixels[50, 50, 1] == 255
        assert pixels[50, 50, 2] == 255

    def test_to_canvas_grayscale(self):
        """Test to_canvas with grayscale PIL image."""
        import PIL.Image
        from imagestag import Image

        # Create grayscale PIL image
        pil_img = PIL.Image.new("L", (50, 50), 128)
        img = Image(pil_img)

        # Convert to canvas
        canvas = img.to_canvas()
        canvas.circle((25, 25), radius=10, color=255)

        # Verify
        pixels = np.array(img.to_pil())
        assert pixels[25, 25] == 255  # White center
