"""
Tests for layer effects on stag SVGs.

Tests each layer effect with 3 different parameter configurations on two
stag SVG images (deer.svg and male-deer.svg). Also tests:
- Serialization/deserialization (debaking) via to_dict/from_dict
- SVG filter generation via to_svg_filter
- SVG fidelity reporting
"""

import numpy as np
import pytest
from pathlib import Path

# SVG rendering
try:
    from stagforge.rendering.vector import render_svg_string
    HAS_RESVG = True
except ImportError:
    HAS_RESVG = False

# Layer effects
from imagestag.layer_effects import (
    LayerEffect,
    DropShadow,
    InnerShadow,
    OuterGlow,
    InnerGlow,
    BevelEmboss,
    Satin,
    Stroke,
    ColorOverlay,
    GradientOverlay,
    PatternOverlay,
    BevelStyle,
    StrokePosition,
    GradientStyle,
)


# Test SVG files
SVG_DIR = Path(__file__).parent.parent / "imagestag" / "samples" / "svgs"
DEER_SVG = SVG_DIR / "noto-emoji" / "deer.svg"
MALE_DEER_SVG = SVG_DIR / "openclipart" / "male-deer.svg"

# Render size for tests
RENDER_WIDTH = 200
RENDER_HEIGHT = 200


@pytest.fixture(scope="module")
def deer_image():
    """Load and render deer.svg to RGBA array."""
    if not HAS_RESVG:
        pytest.skip("resvg not available")
    svg_content = DEER_SVG.read_text()
    return render_svg_string(svg_content, RENDER_WIDTH, RENDER_HEIGHT, supersample=1)


@pytest.fixture(scope="module")
def male_deer_image():
    """Load and render male-deer.svg to RGBA array."""
    if not HAS_RESVG:
        pytest.skip("resvg not available")
    svg_content = MALE_DEER_SVG.read_text()
    return render_svg_string(svg_content, RENDER_WIDTH, RENDER_HEIGHT, supersample=1)


@pytest.fixture(scope="module")
def test_images(deer_image, male_deer_image):
    """Return both test images."""
    return {
        "deer": deer_image,
        "male_deer": male_deer_image,
    }


class TestDropShadowOnSVGs:
    """Test DropShadow effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Subtle shadow
        {"blur": 3, "offset_x": 2, "offset_y": 2, "color": (0, 0, 0), "opacity": 0.3},
        # Config 2: Strong shadow
        {"blur": 10, "offset_x": 8, "offset_y": 8, "color": (0, 0, 0), "opacity": 0.75},
        # Config 3: Colored shadow
        {"blur": 5, "offset_x": 4, "offset_y": 4, "color": (100, 50, 0), "opacity": 0.5},
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply DropShadow to deer.svg."""
        effect = DropShadow(**config)
        result = effect.apply(deer_image)

        # Output should have valid shape
        assert result.image.ndim == 3
        assert result.image.shape[2] == 4
        # Drop shadow expands canvas
        assert result.image.shape[0] >= deer_image.shape[0]
        assert result.image.shape[1] >= deer_image.shape[1]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply DropShadow to male-deer.svg."""
        effect = DropShadow(**config)
        result = effect.apply(male_deer_image)

        assert result.image.ndim == 3
        assert result.image.shape[2] == 4

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = DropShadow(**self.CONFIGS[0])
        data = original.to_dict()

        assert data["effect_type"] == "dropShadow"
        assert data["blur"] == 3
        assert data["offset_x"] == 2

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, DropShadow)
        assert restored.blur == original.blur
        assert restored.offset_x == original.offset_x
        assert restored.color == original.color

    def test_svg_filter(self):
        """Test SVG filter generation."""
        effect = DropShadow(**self.CONFIGS[0])
        assert effect.svg_fidelity == 100
        assert effect.can_convert_to_svg()

        svg_filter = effect.to_svg_filter("test_shadow")
        assert svg_filter is not None
        assert 'id="test_shadow"' in svg_filter
        assert "<feDropShadow" in svg_filter


class TestInnerShadowOnSVGs:
    """Test InnerShadow effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Subtle inner shadow
        {"blur": 3, "offset_x": 1, "offset_y": 1, "color": (0, 0, 0), "opacity": 0.3},
        # Config 2: Strong inner shadow
        {"blur": 8, "offset_x": 4, "offset_y": 4, "color": (0, 0, 0), "opacity": 0.7},
        # Config 3: Colored inner shadow with choke
        {"blur": 5, "offset_x": 2, "offset_y": 2, "color": (50, 0, 50), "opacity": 0.5, "choke": 2},
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply InnerShadow to deer.svg."""
        effect = InnerShadow(**config)
        result = effect.apply(deer_image)

        # Inner shadow doesn't expand canvas
        assert result.image.shape == deer_image.shape
        assert result.offset_x == 0
        assert result.offset_y == 0

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply InnerShadow to male-deer.svg."""
        effect = InnerShadow(**config)
        result = effect.apply(male_deer_image)
        assert result.image.shape == male_deer_image.shape

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = InnerShadow(**self.CONFIGS[2])
        data = original.to_dict()

        assert data["effect_type"] == "innerShadow"
        assert data["choke"] == 2

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, InnerShadow)
        assert restored.choke == original.choke

    def test_svg_filter(self):
        """Test SVG filter generation."""
        effect = InnerShadow(**self.CONFIGS[0])
        assert effect.svg_fidelity == 95
        assert effect.can_convert_to_svg()

        svg_filter = effect.to_svg_filter("test_inner_shadow")
        assert svg_filter is not None
        assert "<feGaussianBlur" in svg_filter
        assert "<feComposite" in svg_filter


class TestOuterGlowOnSVGs:
    """Test OuterGlow effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Soft white glow
        {"radius": 5, "color": (255, 255, 255), "opacity": 0.5},
        # Config 2: Strong yellow glow
        {"radius": 15, "color": (255, 255, 0), "opacity": 0.75, "spread": 3},
        # Config 3: Blue glow with spread
        {"radius": 10, "color": (0, 100, 255), "opacity": 0.6, "spread": 5},
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply OuterGlow to deer.svg."""
        effect = OuterGlow(**config)
        result = effect.apply(deer_image)

        # Outer glow expands canvas
        assert result.image.shape[0] >= deer_image.shape[0]
        assert result.image.shape[1] >= deer_image.shape[1]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply OuterGlow to male-deer.svg."""
        effect = OuterGlow(**config)
        result = effect.apply(male_deer_image)
        assert result.image.ndim == 3

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = OuterGlow(**self.CONFIGS[1])
        data = original.to_dict()

        assert data["effect_type"] == "outerGlow"
        assert data["spread"] == 3

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, OuterGlow)
        assert restored.spread == original.spread
        assert restored.color == original.color

    def test_svg_filter(self):
        """Test SVG filter generation."""
        effect = OuterGlow(**self.CONFIGS[0])
        assert effect.svg_fidelity == 90
        assert effect.can_convert_to_svg()

        svg_filter = effect.to_svg_filter("test_outer_glow")
        assert svg_filter is not None
        assert "<feMorphology" in svg_filter or "<feGaussianBlur" in svg_filter


class TestInnerGlowOnSVGs:
    """Test InnerGlow effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Soft white glow
        {"radius": 5, "color": (255, 255, 255), "opacity": 0.5},
        # Config 2: Strong orange glow
        {"radius": 10, "color": (255, 150, 0), "opacity": 0.75},
        # Config 3: Blue glow with choke
        {"radius": 8, "color": (100, 200, 255), "opacity": 0.6, "choke": 0.3},
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply InnerGlow to deer.svg."""
        effect = InnerGlow(**config)
        result = effect.apply(deer_image)

        # Inner glow doesn't expand canvas
        assert result.image.shape == deer_image.shape

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply InnerGlow to male-deer.svg."""
        effect = InnerGlow(**config)
        result = effect.apply(male_deer_image)
        assert result.image.shape == male_deer_image.shape

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = InnerGlow(**self.CONFIGS[2])
        data = original.to_dict()

        assert data["effect_type"] == "innerGlow"
        assert data["choke"] == 0.3

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, InnerGlow)
        assert restored.choke == original.choke
        assert restored.color == original.color

    def test_svg_filter(self):
        """Test SVG filter generation."""
        effect = InnerGlow(**self.CONFIGS[0])
        assert effect.svg_fidelity == 85
        assert effect.can_convert_to_svg()

        svg_filter = effect.to_svg_filter("test_inner_glow")
        assert svg_filter is not None


class TestBevelEmbossOnSVGs:
    """Test BevelEmboss effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Inner bevel
        {"depth": 3, "angle": 120, "style": BevelStyle.INNER_BEVEL},
        # Config 2: Emboss with custom highlights
        {
            "depth": 5,
            "angle": 135,
            "style": BevelStyle.EMBOSS,
            "highlight_color": (255, 255, 200),
            "shadow_color": (50, 50, 100),
        },
        # Config 3: Pillow emboss
        {"depth": 4, "angle": 90, "altitude": 45, "style": BevelStyle.PILLOW_EMBOSS},
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply BevelEmboss to deer.svg."""
        effect = BevelEmboss(**config)
        result = effect.apply(deer_image)
        assert result.image.ndim == 3
        assert result.image.shape[2] == 4

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply BevelEmboss to male-deer.svg."""
        effect = BevelEmboss(**config)
        result = effect.apply(male_deer_image)
        assert result.image.ndim == 3

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = BevelEmboss(**self.CONFIGS[1])
        data = original.to_dict()

        assert data["effect_type"] == "bevelEmboss"
        assert data["style"] == BevelStyle.EMBOSS

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, BevelEmboss)
        assert restored.style == original.style
        assert restored.highlight_color == original.highlight_color

    def test_svg_filter(self):
        """Test SVG filter generation."""
        effect = BevelEmboss(**self.CONFIGS[0])
        assert effect.svg_fidelity == 70  # Approximation
        assert effect.can_convert_to_svg()

        svg_filter = effect.to_svg_filter("test_bevel")
        assert svg_filter is not None
        # New edge-based bevel uses morphology and offset for highlight/shadow
        assert "<feMorphology" in svg_filter
        assert "<feOffset" in svg_filter
        assert "highlight" in svg_filter
        assert "shadow" in svg_filter


class TestSatinOnSVGs:
    """Test Satin effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Default satin
        {"color": (0, 0, 0), "opacity": 0.5, "angle": 19, "distance": 11, "size": 14},
        # Config 2: Gold satin
        {"color": (200, 150, 50), "opacity": 0.6, "angle": 45, "distance": 15, "size": 20},
        # Config 3: Inverted satin
        {"color": (100, 100, 100), "opacity": 0.4, "angle": 0, "distance": 8, "size": 10, "invert": True},
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply Satin to deer.svg."""
        effect = Satin(**config)
        result = effect.apply(deer_image)

        # Satin doesn't expand canvas
        assert result.image.shape == deer_image.shape

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply Satin to male-deer.svg."""
        effect = Satin(**config)
        result = effect.apply(male_deer_image)
        assert result.image.shape == male_deer_image.shape

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = Satin(**self.CONFIGS[2])
        data = original.to_dict()

        assert data["effect_type"] == "satin"
        assert data["invert"] is True

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, Satin)
        assert restored.invert == original.invert
        assert restored.distance == original.distance

    def test_svg_filter(self):
        """Test SVG filter generation - Satin has no SVG equivalent."""
        effect = Satin(**self.CONFIGS[0])
        assert effect.svg_fidelity == 0
        assert not effect.can_convert_to_svg()

        svg_filter = effect.to_svg_filter("test_satin")
        assert svg_filter is None


class TestStrokeOnSVGs:
    """Test Stroke effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Outside stroke
        {"width": 3, "color": (0, 0, 0), "position": StrokePosition.OUTSIDE},
        # Config 2: Inside stroke
        {"width": 5, "color": (255, 0, 0), "position": StrokePosition.INSIDE},
        # Config 3: Center stroke
        {"width": 4, "color": (0, 100, 200), "position": StrokePosition.CENTER, "opacity": 0.8},
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply Stroke to deer.svg."""
        effect = Stroke(**config)
        result = effect.apply(deer_image)
        assert result.image.ndim == 3
        assert result.image.shape[2] == 4

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply Stroke to male-deer.svg."""
        effect = Stroke(**config)
        result = effect.apply(male_deer_image)
        assert result.image.ndim == 3

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = Stroke(**self.CONFIGS[0])
        data = original.to_dict()

        assert data["effect_type"] == "stroke"
        assert data["position"] == StrokePosition.OUTSIDE

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, Stroke)
        assert restored.position == original.position
        assert restored.width == original.width

    def test_svg_filter(self):
        """Test SVG filter generation."""
        effect = Stroke(**self.CONFIGS[0])
        assert effect.svg_fidelity == 100  # 100% via contour-based path
        assert effect.can_convert_to_svg()

        svg_filter = effect.to_svg_filter("test_stroke")
        assert svg_filter is not None
        assert "<feMorphology" in svg_filter


class TestColorOverlayOnSVGs:
    """Test ColorOverlay effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Red overlay
        {"color": (255, 0, 0), "opacity": 1.0},
        # Config 2: Semi-transparent blue
        {"color": (0, 0, 255), "opacity": 0.5},
        # Config 3: Green with low opacity
        {"color": (0, 200, 50), "opacity": 0.3},
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply ColorOverlay to deer.svg."""
        effect = ColorOverlay(**config)
        result = effect.apply(deer_image)

        # Color overlay doesn't change canvas size
        assert result.image.shape == deer_image.shape

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply ColorOverlay to male-deer.svg."""
        effect = ColorOverlay(**config)
        result = effect.apply(male_deer_image)
        assert result.image.shape == male_deer_image.shape

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = ColorOverlay(**self.CONFIGS[0])
        data = original.to_dict()

        assert data["effect_type"] == "colorOverlay"
        assert data["color"] == [255, 0, 0]

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, ColorOverlay)
        assert restored.color == original.color

    def test_svg_filter(self):
        """Test SVG filter generation."""
        effect = ColorOverlay(**self.CONFIGS[0])
        assert effect.svg_fidelity == 100
        assert effect.can_convert_to_svg()

        svg_filter = effect.to_svg_filter("test_color_overlay")
        assert svg_filter is not None
        assert "<feFlood" in svg_filter
        assert 'flood-color="#FF0000"' in svg_filter


class TestGradientOverlayOnSVGs:
    """Test GradientOverlay effect with 3 configurations."""

    CONFIGS = [
        # Config 1: Linear black to white
        {
            "gradient": [(0.0, 0, 0, 0), (1.0, 255, 255, 255)],
            "style": GradientStyle.LINEAR,
            "angle": 90,
        },
        # Config 2: Radial rainbow
        {
            "gradient": [(0.0, 255, 0, 0), (0.5, 0, 255, 0), (1.0, 0, 0, 255)],
            "style": GradientStyle.RADIAL,
        },
        # Config 3: Reflected gradient
        {
            "gradient": [(0.0, 255, 200, 100), (1.0, 100, 50, 0)],
            "style": GradientStyle.REFLECTED,
            "angle": 45,
            "reverse": True,
        },
    ]

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_deer(self, deer_image, config_idx, config):
        """Apply GradientOverlay to deer.svg."""
        effect = GradientOverlay(**config)
        result = effect.apply(deer_image)

        # Gradient overlay doesn't change canvas size
        assert result.image.shape == deer_image.shape

    @pytest.mark.parametrize("config_idx,config", enumerate(CONFIGS))
    def test_apply_to_male_deer(self, male_deer_image, config_idx, config):
        """Apply GradientOverlay to male-deer.svg."""
        effect = GradientOverlay(**config)
        result = effect.apply(male_deer_image)
        assert result.image.shape == male_deer_image.shape

    def test_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = GradientOverlay(**self.CONFIGS[2])
        data = original.to_dict()

        assert data["effect_type"] == "gradientOverlay"
        assert data["style"] == GradientStyle.REFLECTED
        assert data["reverse"] is True

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, GradientOverlay)
        assert restored.style == original.style
        assert restored.reverse == original.reverse

    def test_svg_filter(self):
        """Test SVG defs generation (gradient overlay uses defs, not filter)."""
        # Linear gradient has good fidelity
        linear = GradientOverlay(**self.CONFIGS[0])
        assert linear.svg_fidelity == 80
        assert linear.can_convert_to_svg()

        # Gradient overlay uses to_svg_defs() instead of to_svg_filter()
        svg_filter = linear.to_svg_filter("test_gradient")
        assert svg_filter is None  # No filter-based approach

        svg_defs = linear.to_svg_defs("test_gradient")
        assert svg_defs is not None
        assert "linearGradient" in svg_defs
        assert "stop" in svg_defs

        # Radial gradient
        radial = GradientOverlay(**self.CONFIGS[1])
        svg_defs_radial = radial.to_svg_defs("test_gradient_radial")
        assert svg_defs_radial is not None
        assert "radialGradient" in svg_defs_radial

    def test_blend_modes(self, deer_image):
        """Test gradient overlay with different blend modes."""
        gradient = [(0.0, 255, 0, 0), (1.0, 0, 0, 255)]

        # Normal blend mode
        normal_effect = GradientOverlay(gradient=gradient, blend_mode="normal")
        result_normal = normal_effect.apply(deer_image)
        assert result_normal.image is not None
        assert normal_effect.blend_mode == "normal"

        # Multiply blend mode
        multiply_effect = GradientOverlay(gradient=gradient, blend_mode="multiply")
        result_multiply = multiply_effect.apply(deer_image)
        assert result_multiply.image is not None
        assert multiply_effect.blend_mode == "multiply"

        # Both should produce valid SVG defs
        assert normal_effect.to_svg_defs("normal_grad") is not None
        assert multiply_effect.to_svg_defs("multiply_grad") is not None


class TestPatternOverlayOnSVGs:
    """Test PatternOverlay effect with 3 configurations."""

    @pytest.fixture
    def checkerboard_pattern(self):
        """Create a simple 4x4 checkerboard pattern."""
        pattern = np.zeros((4, 4, 4), dtype=np.uint8)
        pattern[::2, ::2] = [255, 255, 255, 255]
        pattern[1::2, 1::2] = [255, 255, 255, 255]
        return pattern

    @pytest.fixture
    def stripe_pattern(self):
        """Create a horizontal stripe pattern."""
        pattern = np.zeros((8, 8, 4), dtype=np.uint8)
        pattern[::2] = [200, 100, 50, 255]
        pattern[1::2] = [50, 100, 200, 255]
        return pattern

    @pytest.fixture
    def gradient_pattern(self):
        """Create a gradient pattern."""
        pattern = np.zeros((16, 16, 4), dtype=np.uint8)
        for i in range(16):
            gray = int(i * 255 / 15)
            pattern[i] = [gray, gray, gray, 255]
        return pattern

    def test_apply_to_deer_checkerboard(self, deer_image, checkerboard_pattern):
        """Apply checkerboard PatternOverlay to deer.svg."""
        effect = PatternOverlay(pattern=checkerboard_pattern, scale=1.0)
        result = effect.apply(deer_image)
        assert result.image.shape == deer_image.shape

    def test_apply_to_deer_stripe(self, deer_image, stripe_pattern):
        """Apply stripe PatternOverlay to deer.svg."""
        effect = PatternOverlay(pattern=stripe_pattern, scale=2.0, offset_x=4)
        result = effect.apply(deer_image)
        assert result.image.shape == deer_image.shape

    def test_apply_to_male_deer_gradient(self, male_deer_image, gradient_pattern):
        """Apply gradient PatternOverlay to male-deer.svg."""
        effect = PatternOverlay(pattern=gradient_pattern, scale=0.5, opacity=0.8)
        result = effect.apply(male_deer_image)
        assert result.image.shape == male_deer_image.shape

    def test_serialization(self, checkerboard_pattern):
        """Test to_dict/from_dict roundtrip."""
        original = PatternOverlay(pattern=checkerboard_pattern, scale=2.0, offset_x=5)
        data = original.to_dict()

        assert data["effect_type"] == "patternOverlay"
        assert data["scale"] == 2.0
        assert data["offset_x"] == 5
        # Pattern should be base64 encoded
        assert data["pattern"] is not None

        restored = LayerEffect.from_dict(data)
        assert isinstance(restored, PatternOverlay)
        assert restored.scale == original.scale
        assert restored.offset_x == original.offset_x
        # Pattern should be restored
        assert restored.pattern is not None
        assert restored.pattern.shape == original.pattern.shape

    def test_svg_filter(self, checkerboard_pattern):
        """Test SVG defs generation (pattern overlay uses defs, not filter)."""
        effect = PatternOverlay(pattern=checkerboard_pattern)
        assert effect.svg_fidelity == 80  # 80% via embedded pattern image
        assert effect.can_convert_to_svg()

        # Pattern overlay uses to_svg_defs() instead of to_svg_filter()
        svg_filter = effect.to_svg_filter("test_pattern")
        assert svg_filter is None  # No filter-based approach

        svg_defs = effect.to_svg_defs("test_pattern")
        assert svg_defs is not None
        assert "<pattern" in svg_defs
        assert "<image" in svg_defs
        assert "data:image/png;base64," in svg_defs

    def test_blend_modes(self, deer_image, checkerboard_pattern):
        """Test pattern overlay with different blend modes."""
        # Normal blend mode
        normal_effect = PatternOverlay(pattern=checkerboard_pattern, blend_mode="normal")
        result_normal = normal_effect.apply(deer_image)
        assert result_normal.image is not None
        assert normal_effect.blend_mode == "normal"

        # Multiply blend mode
        multiply_effect = PatternOverlay(pattern=checkerboard_pattern, blend_mode="multiply")
        result_multiply = multiply_effect.apply(deer_image)
        assert result_multiply.image is not None
        assert multiply_effect.blend_mode == "multiply"

        # Both should produce valid SVG defs
        assert normal_effect.to_svg_defs("normal_pattern") is not None
        assert multiply_effect.to_svg_defs("multiply_pattern") is not None


class TestEffectRegistry:
    """Test the effect class registry and from_dict functionality."""

    def test_all_effects_registered(self):
        """Verify all effects are in the registry."""
        from imagestag.layer_effects.base import LayerEffect

        expected_types = [
            "dropShadow",
            "innerShadow",
            "outerGlow",
            "innerGlow",
            "bevelEmboss",
            "satin",
            "stroke",
            "colorOverlay",
            "gradientOverlay",
            "patternOverlay",
        ]

        for effect_type in expected_types:
            assert effect_type in LayerEffect._registry, f"{effect_type} not in registry"

    def test_unknown_effect_type_raises(self):
        """Verify unknown effect types raise an error."""
        with pytest.raises(ValueError, match="Unknown effect type"):
            LayerEffect.from_dict({"effect_type": "nonexistent"})

    def test_disabled_effect_returns_input(self, deer_image):
        """Verify disabled effects return input unchanged."""
        effect = DropShadow(blur=10, enabled=False)
        result = effect.apply(deer_image)

        # Should return same size as input
        assert result.image.shape == deer_image.shape
        assert result.offset_x == 0
        assert result.offset_y == 0


class TestSVGFidelityReport:
    """Generate a report of SVG fidelity for all effects."""

    def test_fidelity_summary(self):
        """Print fidelity summary for all effects."""
        effects = [
            ("DropShadow", DropShadow()),
            ("InnerShadow", InnerShadow()),
            ("OuterGlow", OuterGlow()),
            ("InnerGlow", InnerGlow()),
            ("BevelEmboss", BevelEmboss()),
            ("Satin", Satin()),
            ("Stroke", Stroke()),
            ("ColorOverlay", ColorOverlay()),
            ("GradientOverlay (linear)", GradientOverlay(style=GradientStyle.LINEAR)),
            ("GradientOverlay (radial)", GradientOverlay(style=GradientStyle.RADIAL)),
            ("GradientOverlay (angle)", GradientOverlay(style=GradientStyle.ANGLE)),
            ("PatternOverlay", PatternOverlay()),
        ]

        print("\n" + "=" * 60)
        print("SVG Fidelity Report")
        print("=" * 60)
        print(f"{'Effect':<30} {'Fidelity':>10} {'SVG Support':>15}")
        print("-" * 60)

        for name, effect in effects:
            fidelity = effect.svg_fidelity
            can_convert = "Yes" if effect.can_convert_to_svg() else "No"
            print(f"{name:<30} {fidelity:>10}% {can_convert:>15}")

        print("=" * 60)

        # Assertions to ensure the report matches expected values
        assert DropShadow().svg_fidelity == 100
        assert ColorOverlay().svg_fidelity == 100
        assert Stroke().svg_fidelity == 100  # 100% via contour-based path
        assert InnerShadow().svg_fidelity == 95
        assert OuterGlow().svg_fidelity == 90
        assert InnerGlow().svg_fidelity == 85
        assert GradientOverlay(style=GradientStyle.LINEAR).svg_fidelity == 80
        assert PatternOverlay().svg_fidelity == 80  # 80% via embedded image
        assert BevelEmboss().svg_fidelity == 70
        assert Satin().svg_fidelity == 0
