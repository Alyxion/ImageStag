"""
Tests for Anchor2D and text alignment classes.
"""

import pytest

from imagestag import (
    Anchor2D,
    HTextAlignment,
    VTextAlignment,
    Size2D,
    Pos2D,
)
from imagestag.anchor2d import Anchor2DTypes, Anchor2DLiterals
from imagestag.text_alignment_definitions import (
    HTextAlignmentTypes,
    HTextAlignmentLiterals,
    VTextAlignmentTypes,
    VTextAlignmentLiterals,
)


class TestAnchor2D:
    """Tests for Anchor2D enum."""

    def test_anchor_values(self):
        """Test that anchor enum values are correct."""
        assert Anchor2D.TOP_LEFT == 0
        assert Anchor2D.TOP == 1
        assert Anchor2D.TOP_RIGHT == 2
        assert Anchor2D.CENTER_LEFT == 3
        assert Anchor2D.CENTER == 4
        assert Anchor2D.CENTER_RIGHT == 5
        assert Anchor2D.BOTTOM_LEFT == 6
        assert Anchor2D.BOTTOM == 7
        assert Anchor2D.BOTTOM_RIGHT == 8

    def test_anchor_from_string_short(self):
        """Test creating anchor from short string codes."""
        assert Anchor2D("tl") == Anchor2D.TOP_LEFT
        assert Anchor2D("t") == Anchor2D.TOP
        assert Anchor2D("tr") == Anchor2D.TOP_RIGHT
        assert Anchor2D("cl") == Anchor2D.CENTER_LEFT
        assert Anchor2D("c") == Anchor2D.CENTER
        assert Anchor2D("cr") == Anchor2D.CENTER_RIGHT
        assert Anchor2D("bl") == Anchor2D.BOTTOM_LEFT
        assert Anchor2D("b") == Anchor2D.BOTTOM
        assert Anchor2D("br") == Anchor2D.BOTTOM_RIGHT

    def test_anchor_from_string_long(self):
        """Test creating anchor from long string codes."""
        assert Anchor2D("topLeft") == Anchor2D.TOP_LEFT
        assert Anchor2D("top") == Anchor2D.TOP
        assert Anchor2D("topRight") == Anchor2D.TOP_RIGHT
        assert Anchor2D("centerLeft") == Anchor2D.CENTER_LEFT
        assert Anchor2D("center") == Anchor2D.CENTER
        assert Anchor2D("centerRight") == Anchor2D.CENTER_RIGHT
        assert Anchor2D("bottomLeft") == Anchor2D.BOTTOM_LEFT
        assert Anchor2D("bottom") == Anchor2D.BOTTOM
        assert Anchor2D("bottomRight") == Anchor2D.BOTTOM_RIGHT

    def test_anchor_invalid_string(self):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            Anchor2D("invalid")

    def test_get_position_shift_top_left(self):
        """Test position shift for top-left anchor (no shift)."""
        size = Size2D(100, 80)
        shift = Anchor2D.TOP_LEFT.get_position_shift(size)
        assert shift == (0.0, 0.0)

    def test_get_position_shift_center(self):
        """Test position shift for center anchor."""
        size = Size2D(100, 80)
        shift = Anchor2D.CENTER.get_position_shift(size)
        assert shift == (-50.0, -40.0)

    def test_get_position_shift_bottom_right(self):
        """Test position shift for bottom-right anchor."""
        size = Size2D(100, 80)
        shift = Anchor2D.BOTTOM_RIGHT.get_position_shift(size)
        assert shift == (-100.0, -80.0)

    def test_get_position_shift_top(self):
        """Test position shift for top anchor."""
        size = Size2D(100, 80)
        shift = Anchor2D.TOP.get_position_shift(size)
        assert shift == (-50.0, 0.0)

    def test_get_position_shift_bottom(self):
        """Test position shift for bottom anchor."""
        size = Size2D(100, 80)
        shift = Anchor2D.BOTTOM.get_position_shift(size)
        assert shift == (-50.0, -80.0)

    def test_get_position_shift_center_left(self):
        """Test position shift for center-left anchor."""
        size = Size2D(100, 80)
        shift = Anchor2D.CENTER_LEFT.get_position_shift(size)
        assert shift == (0.0, -40.0)

    def test_get_position_shift_center_right(self):
        """Test position shift for center-right anchor."""
        size = Size2D(100, 80)
        shift = Anchor2D.CENTER_RIGHT.get_position_shift(size)
        assert shift == (-100.0, -40.0)

    def test_get_position_shift_with_tuple(self):
        """Test position shift with tuple size."""
        shift = Anchor2D.CENTER.get_position_shift((100, 80))
        assert shift == (-50.0, -40.0)

    def test_shift_position(self):
        """Test shift_position method."""
        pos = Pos2D(100, 100)
        size = Size2D(50, 50)
        result = Anchor2D.CENTER.shift_position(pos, size)
        assert result.x == 75.0
        assert result.y == 75.0

    def test_shift_position_rounded(self):
        """Test shift_position with rounding."""
        pos = Pos2D(100, 100)
        size = Size2D(51, 51)  # Odd size for fractional shift
        result = Anchor2D.CENTER.shift_position(pos, size, round_shift=True)
        assert isinstance(result.x, (int, float))
        assert isinstance(result.y, (int, float))

    def test_shift_position_modifies_input(self):
        """Test that shift_position modifies the input position."""
        pos = Pos2D(100, 100)
        size = Size2D(50, 50)
        result = Anchor2D.CENTER.shift_position(pos, size)
        # Should modify and return the same object
        assert result is pos


class TestHTextAlignment:
    """Tests for HTextAlignment enum."""

    def test_alignment_values(self):
        """Test that alignment enum values are correct."""
        assert HTextAlignment.LEFT == 0
        assert HTextAlignment.CENTER == 1
        assert HTextAlignment.RIGHT == 2

    def test_alignment_from_short_string(self):
        """Test creating alignment from short string codes."""
        assert HTextAlignment("l") == HTextAlignment.LEFT
        assert HTextAlignment("c") == HTextAlignment.CENTER
        assert HTextAlignment("r") == HTextAlignment.RIGHT

    def test_alignment_from_long_string(self):
        """Test creating alignment from long string codes."""
        assert HTextAlignment("left") == HTextAlignment.LEFT
        assert HTextAlignment("center") == HTextAlignment.CENTER
        assert HTextAlignment("right") == HTextAlignment.RIGHT

    def test_alignment_invalid_string(self):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            HTextAlignment("invalid")


class TestVTextAlignment:
    """Tests for VTextAlignment enum."""

    def test_alignment_values(self):
        """Test that alignment enum values are correct."""
        assert VTextAlignment.TOP == 0
        assert VTextAlignment.CENTER == 1
        assert VTextAlignment.REAL_CENTER == 2
        assert VTextAlignment.BASELINE == 3
        assert VTextAlignment.BOTTOM == 4

    def test_alignment_from_short_string(self):
        """Test creating alignment from short string codes."""
        assert VTextAlignment("t") == VTextAlignment.TOP
        assert VTextAlignment("c") == VTextAlignment.CENTER
        assert VTextAlignment("rc") == VTextAlignment.REAL_CENTER
        assert VTextAlignment("bl") == VTextAlignment.BASELINE
        assert VTextAlignment("b") == VTextAlignment.BOTTOM

    def test_alignment_from_long_string(self):
        """Test creating alignment from long string codes."""
        assert VTextAlignment("top") == VTextAlignment.TOP
        assert VTextAlignment("center") == VTextAlignment.CENTER
        assert VTextAlignment("realCenter") == VTextAlignment.REAL_CENTER
        assert VTextAlignment("baseline") == VTextAlignment.BASELINE
        assert VTextAlignment("bottom") == VTextAlignment.BOTTOM

    def test_alignment_invalid_string(self):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            VTextAlignment("invalid")


class TestAnchorWithCanvas:
    """Tests for Anchor2D with Canvas drawing."""

    def test_text_with_center_anchor(self):
        """Test drawing text with center anchor."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            # Draw text centered at (100, 50)
            canvas.text(
                (100, 50),
                "Centered",
                color=Colors.BLACK,
                font=font,
                anchor=Anchor2D.CENTER,
            )
            img = canvas.to_image()
            assert img is not None

    def test_text_with_anchor_string(self):
        """Test drawing text with anchor as string."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            canvas.text(
                (100, 50),
                "Test",
                color=Colors.BLACK,
                font=font,
                anchor="c",  # center as string
            )
            img = canvas.to_image()
            assert img is not None


class TestAlignmentWithCanvas:
    """Tests for text alignment with Canvas."""

    def test_text_left_aligned(self):
        """Test left-aligned text."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            canvas.text(
                (10, 10),
                "Left aligned",
                color=Colors.BLACK,
                font=font,
                h_align=HTextAlignment.LEFT,
            )
            img = canvas.to_image()
            assert img is not None

    def test_text_center_aligned(self):
        """Test center-aligned text."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            canvas.text(
                (100, 10),
                "Center aligned",
                color=Colors.BLACK,
                font=font,
                h_align=HTextAlignment.CENTER,
            )
            img = canvas.to_image()
            assert img is not None

    def test_text_right_aligned(self):
        """Test right-aligned text."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            canvas.text(
                (190, 10),
                "Right aligned",
                color=Colors.BLACK,
                font=font,
                h_align=HTextAlignment.RIGHT,
            )
            img = canvas.to_image()
            assert img is not None

    def test_text_vertical_alignments(self):
        """Test various vertical alignments."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 200), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            y_pos = 50
            for v_align in [VTextAlignment.TOP, VTextAlignment.CENTER,
                           VTextAlignment.BASELINE, VTextAlignment.BOTTOM]:
                canvas.text(
                    (10, y_pos),
                    f"{v_align.name}",
                    color=Colors.BLACK,
                    font=font,
                    v_align=v_align,
                )
                y_pos += 40
            img = canvas.to_image()
            assert img is not None

    def test_text_alignment_with_strings(self):
        """Test alignment using string codes."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            canvas.text(
                (100, 50),
                "Test",
                color=Colors.BLACK,
                font=font,
                h_align="c",  # center
                v_align="c",  # center
            )
            img = canvas.to_image()
            assert img is not None

    def test_text_center_shortcut(self):
        """Test center=True shortcut."""
        from imagestag import Canvas, Colors

        canvas = Canvas(size=(200, 100), default_color=Colors.WHITE)
        font = canvas.get_default_font(size=16)

        if font is not None:
            canvas.text(
                (100, 50),
                "Centered",
                color=Colors.BLACK,
                font=font,
                center=True,
            )
            img = canvas.to_image()
            assert img is not None
