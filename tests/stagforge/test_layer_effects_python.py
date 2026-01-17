"""
Tests for Python layer effects API.

These tests verify that the ImageStag layer effects Python wrappers
work correctly and produce valid output.
"""

import numpy as np
import pytest


class TestLayerEffectsAPI:
    """Test the OOP layer effects API."""

    @pytest.fixture
    def test_image(self):
        """Create a test image with a red square in the center."""
        img = np.zeros((100, 100, 4), dtype=np.uint8)
        img[25:75, 25:75, :] = [255, 0, 0, 255]  # Red square
        return img

    @pytest.fixture
    def test_image_f32(self, test_image):
        """Create a float32 version of the test image."""
        return test_image.astype(np.float32) / 255.0

    def test_drop_shadow(self, test_image):
        """Test DropShadow effect."""
        from imagestag.layer_effects import DropShadow

        effect = DropShadow(blur=5, offset_x=10, offset_y=10, color=(0, 0, 0), opacity=0.75)
        result = effect.apply(test_image)

        # Output should be larger than input (shadow extends beyond bounds)
        assert result.image.shape[0] > test_image.shape[0]
        assert result.image.shape[1] > test_image.shape[1]
        assert result.image.shape[2] == 4  # RGBA

        # Offset should be negative (canvas expanded)
        assert result.offset_x < 0
        assert result.offset_y < 0

    def test_drop_shadow_f32(self, test_image_f32):
        """Test DropShadow with float32 input."""
        from imagestag.layer_effects import DropShadow

        effect = DropShadow(blur=5, offset_x=5, offset_y=5)
        result = effect.apply(test_image_f32)

        assert result.image.dtype == np.float32
        assert result.image.min() >= 0.0
        assert result.image.max() <= 1.0

    def test_inner_shadow(self, test_image):
        """Test InnerShadow effect."""
        from imagestag.layer_effects import InnerShadow

        effect = InnerShadow(blur=5, offset_x=3, offset_y=3, color=(0, 0, 0), opacity=0.75)
        result = effect.apply(test_image)

        # Inner shadow doesn't expand canvas
        assert result.image.shape == test_image.shape
        assert result.offset_x == 0
        assert result.offset_y == 0

    def test_outer_glow(self, test_image):
        """Test OuterGlow effect."""
        from imagestag.layer_effects import OuterGlow

        effect = OuterGlow(radius=10, color=(255, 255, 0), opacity=0.75)
        result = effect.apply(test_image)

        # Outer glow expands canvas
        assert result.image.shape[0] > test_image.shape[0]
        assert result.image.shape[1] > test_image.shape[1]

    def test_inner_glow(self, test_image):
        """Test InnerGlow effect."""
        from imagestag.layer_effects import InnerGlow

        effect = InnerGlow(radius=10, color=(255, 255, 255), opacity=0.75)
        result = effect.apply(test_image)

        # Inner glow doesn't expand canvas
        assert result.image.shape == test_image.shape

    def test_bevel_emboss(self, test_image):
        """Test BevelEmboss effect."""
        from imagestag.layer_effects import BevelEmboss

        effect = BevelEmboss(depth=5, angle=120, style="inner_bevel")
        result = effect.apply(test_image)

        # Inner bevel doesn't expand canvas
        assert result.image.shape == test_image.shape

    def test_bevel_emboss_outer(self, test_image):
        """Test BevelEmboss outer style."""
        from imagestag.layer_effects import BevelEmboss

        effect = BevelEmboss(depth=5, angle=120, style="outer_bevel")
        result = effect.apply(test_image)

        # Outer bevel expands canvas
        assert result.image.shape[0] > test_image.shape[0]

    def test_stroke_outside(self, test_image):
        """Test Stroke effect with outside position."""
        from imagestag.layer_effects import Stroke

        effect = Stroke(width=3, color=(0, 255, 0), position="outside")
        result = effect.apply(test_image)

        # Outside stroke expands canvas
        assert result.image.shape[0] > test_image.shape[0]
        assert result.image.shape[1] > test_image.shape[1]

    def test_stroke_inside(self, test_image):
        """Test Stroke effect with inside position."""
        from imagestag.layer_effects import Stroke

        effect = Stroke(width=3, color=(0, 255, 0), position="inside")
        result = effect.apply(test_image)

        # Inside stroke doesn't expand canvas
        assert result.image.shape == test_image.shape

    def test_color_overlay(self, test_image):
        """Test ColorOverlay effect."""
        from imagestag.layer_effects import ColorOverlay

        effect = ColorOverlay(color=(0, 0, 255), opacity=1.0)
        result = effect.apply(test_image)

        # Color overlay doesn't change canvas size
        assert result.image.shape == test_image.shape

        # Red pixels should now be blue
        # Check center of the square
        center_pixel = result.image[50, 50]
        assert center_pixel[0] == 0    # R should be 0
        assert center_pixel[1] == 0    # G should be 0
        assert center_pixel[2] == 255  # B should be 255
        assert center_pixel[3] == 255  # A should be preserved

    def test_color_overlay_partial(self, test_image):
        """Test ColorOverlay with partial opacity."""
        from imagestag.layer_effects import ColorOverlay

        effect = ColorOverlay(color=(0, 0, 255), opacity=0.5)
        result = effect.apply(test_image)

        # Center pixel should be blend of red and blue
        center_pixel = result.image[50, 50]
        # 50% blend of red (255,0,0) and blue (0,0,255) = (127, 0, 127)
        assert 120 <= center_pixel[0] <= 135  # R ~127
        assert center_pixel[1] == 0           # G = 0
        assert 120 <= center_pixel[2] <= 135  # B ~127

    def test_disabled_effect(self, test_image):
        """Test that disabled effects return input unchanged."""
        from imagestag.layer_effects import DropShadow

        effect = DropShadow(blur=5, enabled=False)
        result = effect.apply(test_image)

        # Disabled effect should return same size
        assert result.image.shape == test_image.shape
        assert result.offset_x == 0
        assert result.offset_y == 0


class TestPixelFormats:
    """Test that effects work with all pixel formats."""

    @pytest.fixture
    def base_image(self):
        """Create a simple test image."""
        img = np.zeros((50, 50, 4), dtype=np.uint8)
        img[15:35, 15:35, :] = [128, 64, 32, 255]
        return img

    def test_rgba8(self, base_image):
        """Test with RGBA8 format."""
        from imagestag.layer_effects import DropShadow

        effect = DropShadow(blur=3)
        result = effect.apply(base_image, format="RGBA8")
        assert result.image.dtype == np.uint8

    def test_rgbaf32(self, base_image):
        """Test with RGBAf32 format."""
        from imagestag.layer_effects import DropShadow

        img_f32 = base_image.astype(np.float32) / 255.0
        effect = DropShadow(blur=3)
        result = effect.apply(img_f32, format="RGBAf32")
        assert result.image.dtype == np.float32
        assert 0.0 <= result.image.max() <= 1.0

    def test_rgb8_auto_alpha(self, base_image):
        """Test that RGB input gets alpha channel added."""
        from imagestag.layer_effects import ColorOverlay

        # Remove alpha channel
        rgb_image = base_image[:, :, :3]
        effect = ColorOverlay(color=(255, 0, 0))
        result = effect.apply(rgb_image)
        # Output should have alpha channel
        assert result.image.shape[2] == 4


class TestExpansion:
    """Test canvas expansion calculations."""

    @pytest.fixture
    def small_image(self):
        """Create a small test image."""
        img = np.zeros((20, 20, 4), dtype=np.uint8)
        img[5:15, 5:15, :] = [255, 255, 255, 255]
        return img

    def test_drop_shadow_expansion(self, small_image):
        """Test DropShadow expansion calculation."""
        from imagestag.layer_effects import DropShadow

        effect = DropShadow(blur=5, offset_x=10, offset_y=10)
        expansion = effect.get_expansion()

        # Expansion should account for blur (~3*sigma) and offset
        assert expansion.left > 0
        assert expansion.top > 0
        assert expansion.right > 0
        assert expansion.bottom > 0

    def test_inner_shadow_no_expansion(self, small_image):
        """Test InnerShadow has no expansion."""
        from imagestag.layer_effects import InnerShadow

        effect = InnerShadow(blur=5)
        expansion = effect.get_expansion()

        assert expansion.left == 0
        assert expansion.top == 0
        assert expansion.right == 0
        assert expansion.bottom == 0

    def test_stroke_expansion_by_position(self, small_image):
        """Test Stroke expansion depends on position."""
        from imagestag.layer_effects import Stroke

        # Outside stroke needs expansion
        outside = Stroke(width=5, position="outside")
        exp_outside = outside.get_expansion()
        assert exp_outside.left > 0

        # Inside stroke doesn't need expansion
        inside = Stroke(width=5, position="inside")
        exp_inside = inside.get_expansion()
        assert exp_inside.left == 0
