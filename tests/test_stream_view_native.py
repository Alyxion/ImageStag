"""Tests for native StreamView implementations (pygame, tkinter, kivy).

Tests the shared compositor, event handling, and pygame-specific components.
"""

import os
import numpy as np
import pytest

from imagestag import Image
from imagestag.components.shared import (
    LayerCompositor,
    Viewport,
    KeyEvent,
    MouseEvent,
    MouseButton,
    ResizeEvent,
)
from imagestag.components.stream_view import StreamViewLayer, ImageStream


class TestViewport:
    """Tests for Viewport class."""

    def test_default_values(self):
        """Test viewport has correct defaults."""
        vp = Viewport()
        assert vp.x == 0.0
        assert vp.y == 0.0
        assert vp.width == 1.0
        assert vp.height == 1.0
        assert vp.zoom == 1.0

    def test_set_zoom_centered(self):
        """Test zoom centered on middle."""
        vp = Viewport()
        vp.set_zoom(2.0, 0.5, 0.5)

        assert vp.zoom == 2.0
        assert vp.width == 0.5
        assert vp.height == 0.5
        assert vp.x == 0.25
        assert vp.y == 0.25

    def test_set_zoom_corner(self):
        """Test zoom centered on top-left corner."""
        vp = Viewport()
        vp.set_zoom(2.0, 0.0, 0.0)

        assert vp.zoom == 2.0
        assert vp.x == 0.0
        assert vp.y == 0.0

    def test_set_zoom_clamps_min(self):
        """Test zoom clamps to minimum 1.0."""
        vp = Viewport()
        vp.set_zoom(0.5)

        assert vp.zoom == 1.0

    def test_set_zoom_clamps_max(self):
        """Test zoom clamps to maximum 10.0."""
        vp = Viewport()
        vp.set_zoom(20.0)

        assert vp.zoom == 10.0

    def test_pan(self):
        """Test panning the viewport."""
        vp = Viewport()
        vp.set_zoom(2.0, 0.5, 0.5)  # Zoom first to allow panning

        initial_x = vp.x
        vp.pan(0.1, 0.0)

        assert vp.x == initial_x + 0.1
        assert vp.y == 0.25  # Unchanged

    def test_pan_clamps_to_bounds(self):
        """Test panning doesn't go out of bounds."""
        vp = Viewport()
        vp.set_zoom(2.0, 0.5, 0.5)

        # Try to pan way past the edge
        vp.pan(10.0, 10.0)

        # Should be clamped
        assert vp.x <= 1.0 - vp.width
        assert vp.y <= 1.0 - vp.height

    def test_reset(self):
        """Test reset returns to defaults."""
        vp = Viewport()
        vp.set_zoom(4.0, 0.3, 0.7)
        vp.pan(0.1, 0.1)

        vp.reset()

        assert vp.x == 0.0
        assert vp.y == 0.0
        assert vp.width == 1.0
        assert vp.height == 1.0
        assert vp.zoom == 1.0


class TestKeyEvent:
    """Tests for KeyEvent dataclass."""

    def test_basic_key_event(self):
        """Test basic key event creation."""
        event = KeyEvent(key='a', key_code=65, is_press=True)

        assert event.key == 'a'
        assert event.key_code == 65
        assert event.is_press is True
        assert event.modifiers == frozenset()

    def test_modifier_properties(self):
        """Test modifier property accessors."""
        event = KeyEvent(
            key='s',
            modifiers=frozenset(['ctrl', 'shift']),
        )

        assert event.ctrl is True
        assert event.shift is True
        assert event.alt is False

    def test_cmd_modifier(self):
        """Test cmd modifier is detected."""
        event = KeyEvent(key='c', modifiers=frozenset(['cmd']))

        assert event.ctrl is True  # cmd counts as ctrl


class TestMouseEvent:
    """Tests for MouseEvent dataclass."""

    def test_basic_mouse_event(self):
        """Test basic mouse event creation."""
        event = MouseEvent(x=100, y=200, event_type="move")

        assert event.x == 100
        assert event.y == 200
        assert event.event_type == "move"
        assert event.button is None

    def test_click_event(self):
        """Test click event properties."""
        event = MouseEvent(
            x=50,
            y=50,
            button=MouseButton.LEFT,
            event_type="press",
        )

        assert event.is_click is True
        assert event.left_click is True
        assert event.right_click is False

    def test_scroll_event(self):
        """Test scroll event properties."""
        event = MouseEvent(
            x=100,
            y=100,
            event_type="scroll",
            delta_y=1.0,
        )

        assert event.is_scroll is True
        assert event.delta_y == 1.0


class TestResizeEvent:
    """Tests for ResizeEvent dataclass."""

    def test_resize_event(self):
        """Test resize event creation."""
        event = ResizeEvent(
            width=1920,
            height=1080,
            old_width=1280,
            old_height=720,
        )

        assert event.width == 1920
        assert event.height == 1080
        assert event.old_width == 1280
        assert event.old_height == 720


class TestLayerCompositor:
    """Tests for LayerCompositor class."""

    @pytest.fixture
    def compositor(self):
        """Create a compositor for testing."""
        return LayerCompositor(640, 480)

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        pixels = np.zeros((480, 640, 3), dtype=np.uint8)
        pixels[:, :, 0] = 255  # Red
        return Image(pixels, pixel_format='RGB')

    def test_default_size(self):
        """Test default compositor size."""
        comp = LayerCompositor()
        assert comp.width == 1280
        assert comp.height == 720

    def test_custom_size(self, compositor):
        """Test custom compositor size."""
        assert compositor.width == 640
        assert compositor.height == 480

    def test_set_size(self, compositor):
        """Test changing compositor size."""
        compositor.set_size(1920, 1080)
        assert compositor.width == 1920
        assert compositor.height == 1080

    def test_set_background(self, compositor):
        """Test setting background color."""
        compositor.set_background(128, 64, 32)
        assert compositor._background_color == (128, 64, 32)

    def test_add_layer(self, compositor, test_image):
        """Test adding a layer."""
        layer = StreamViewLayer(image=test_image, z_index=0)
        compositor.add_layer(layer)

        assert layer.id in compositor._layers
        assert len(compositor.layers) == 1

    def test_remove_layer(self, compositor, test_image):
        """Test removing a layer."""
        layer = StreamViewLayer(image=test_image, z_index=0)
        compositor.add_layer(layer)
        compositor.remove_layer(layer.id)

        assert layer.id not in compositor._layers
        assert len(compositor.layers) == 0

    def test_get_layer(self, compositor, test_image):
        """Test getting a layer by ID."""
        layer = StreamViewLayer(image=test_image, z_index=0)
        compositor.add_layer(layer)

        retrieved = compositor.get_layer(layer.id)
        assert retrieved is layer

    def test_get_layer_not_found(self, compositor):
        """Test getting non-existent layer returns None."""
        result = compositor.get_layer("nonexistent")
        assert result is None

    def test_layers_sorted_by_z_index(self, compositor, test_image):
        """Test layers are sorted by z_index."""
        layer1 = StreamViewLayer(image=test_image, z_index=2)
        layer2 = StreamViewLayer(image=test_image, z_index=0)
        layer3 = StreamViewLayer(image=test_image, z_index=1)

        compositor.add_layer(layer1)
        compositor.add_layer(layer2)
        compositor.add_layer(layer3)

        layers = compositor.layers
        assert layers[0].z_index == 0
        assert layers[1].z_index == 1
        assert layers[2].z_index == 2

    def test_composite_empty(self, compositor):
        """Test compositing with no layers returns background."""
        compositor.set_background(64, 128, 192)
        result = compositor.composite_rgb()

        assert result.width == 640
        assert result.height == 480

        # Check background color
        pixels = result.get_pixels()
        assert pixels[0, 0, 0] == 64  # R
        assert pixels[0, 0, 1] == 128  # G
        assert pixels[0, 0, 2] == 192  # B

    def test_composite_single_layer(self, compositor, test_image):
        """Test compositing a single layer."""
        layer = StreamViewLayer(image=test_image, z_index=0)
        compositor.add_layer(layer)

        result = compositor.composite_rgb()

        # Should be red (from test_image)
        pixels = result.get_pixels()
        assert pixels[240, 320, 0] == 255  # R
        assert pixels[240, 320, 1] == 0  # G
        assert pixels[240, 320, 2] == 0  # B

    def test_composite_multiple_layers(self, compositor):
        """Test compositing multiple layers respects z_index."""
        # Bottom layer: red
        red_pixels = np.zeros((480, 640, 3), dtype=np.uint8)
        red_pixels[:, :, 0] = 255
        red_image = Image(red_pixels, pixel_format='RGB')

        # Top layer: blue, smaller, positioned
        blue_pixels = np.zeros((100, 100, 3), dtype=np.uint8)
        blue_pixels[:, :, 2] = 255
        blue_image = Image(blue_pixels, pixel_format='RGB')

        layer1 = StreamViewLayer(image=red_image, z_index=0)
        layer2 = StreamViewLayer(
            image=blue_image,
            z_index=1,
            x=100,
            y=100,
            width=100,
            height=100,
        )

        compositor.add_layer(layer1)
        compositor.add_layer(layer2)

        result = compositor.composite_rgb()
        pixels = result.get_pixels()

        # Check red area (outside blue overlay)
        assert pixels[50, 50, 0] == 255  # Red
        assert pixels[50, 50, 2] == 0  # Not blue

        # Check blue area (inside overlay)
        assert pixels[150, 150, 0] == 0  # Not red
        assert pixels[150, 150, 2] == 255  # Blue

    def test_frame_caching(self, compositor, test_image):
        """Test that frames are cached for reuse."""
        layer = StreamViewLayer(image=test_image, z_index=0)
        compositor.add_layer(layer)

        # First call populates cache
        compositor.get_layer_frame(layer, 0.0)
        assert layer.id in compositor._frame_cache

        # Cache should be cleared when layer is removed
        compositor.remove_layer(layer.id)
        assert layer.id not in compositor._frame_cache

    def test_viewport_integration(self, compositor):
        """Test viewport is accessible and updates layers."""
        vp = compositor.viewport
        assert vp.zoom == 1.0

        compositor.viewport.set_zoom(2.0)
        compositor.update_viewports()

        assert compositor.viewport.zoom == 2.0


class TestPygameEventConversion:
    """Tests for pygame event conversion functions."""

    def test_convert_key_event(self):
        """Test converting pygame key events."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame.events import convert_key_event
        import pygame

        # Create a mock pygame event
        class MockEvent:
            type = pygame.KEYDOWN
            key = pygame.K_SPACE

        event = convert_key_event(MockEvent())
        assert event is not None
        assert event.key == 'space'
        assert event.is_press is True

    def test_convert_mouse_motion(self):
        """Test converting pygame mouse motion events."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame.events import convert_mouse_event
        import pygame

        class MockEvent:
            type = pygame.MOUSEMOTION
            pos = (100, 200)

        event = convert_mouse_event(MockEvent())
        assert event is not None
        assert event.x == 100
        assert event.y == 200
        assert event.event_type == "move"

    def test_convert_mouse_click(self):
        """Test converting pygame mouse click events."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame.events import convert_mouse_event
        import pygame

        class MockEvent:
            type = pygame.MOUSEBUTTONDOWN
            pos = (50, 75)
            button = 1  # Left click

        event = convert_mouse_event(MockEvent())
        assert event is not None
        assert event.x == 50
        assert event.y == 75
        assert event.event_type == "press"
        assert event.button == MouseButton.LEFT


class TestStreamViewPygame:
    """Tests for StreamViewPygame class."""

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        pixels = np.zeros((480, 640, 3), dtype=np.uint8)
        pixels[:, :, 1] = 255  # Green
        return Image(pixels, pixel_format='RGB')

    def test_initialization(self):
        """Test StreamViewPygame initialization."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame import StreamViewPygame

        view = StreamViewPygame(800, 600, title="Test")

        assert view.width == 800
        assert view.height == 600
        assert view.title == "Test"
        assert view.target_fps == 60

    def test_add_layer(self, test_image):
        """Test adding layers to the view."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame import StreamViewPygame

        view = StreamViewPygame(640, 480)
        layer = view.add_layer(image=test_image, z_index=0)

        assert layer is not None
        assert layer.id in view._layers
        assert len(view.layers) == 1

    def test_remove_layer(self, test_image):
        """Test removing layers from the view."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame import StreamViewPygame

        view = StreamViewPygame(640, 480)
        layer = view.add_layer(image=test_image, z_index=0)
        view.remove_layer(layer.id)

        assert layer.id not in view._layers
        assert len(view.layers) == 0

    def test_event_handler_registration(self):
        """Test registering event handlers."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame import StreamViewPygame

        view = StreamViewPygame(640, 480)

        @view.on_key
        def handle_key(event):
            pass

        @view.on_mouse
        def handle_mouse(event):
            pass

        @view.on_resize
        def handle_resize(event):
            pass

        assert len(view._key_handlers) == 1
        assert len(view._mouse_handlers) == 1
        assert len(view._resize_handlers) == 1

    def test_zoom_control(self, test_image):
        """Test zoom control methods."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame import StreamViewPygame

        view = StreamViewPygame(640, 480)
        view.add_layer(image=test_image, z_index=0)

        view.set_zoom(2.0, 0.5, 0.5)
        assert view.viewport.zoom == 2.0

        view.reset_zoom()
        assert view.viewport.zoom == 1.0

    def test_pause_resume(self, test_image):
        """Test pause and resume functionality."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame import StreamViewPygame

        view = StreamViewPygame(640, 480)
        view.add_layer(image=test_image, z_index=0)

        assert view.is_paused is False

        view.pause()
        assert view.is_paused is True

        view.resume()
        assert view.is_paused is False

        view.toggle_pause()
        assert view.is_paused is True

    def test_compositing_modes(self):
        """Test both compositing modes are accepted."""
        pytest.importorskip("pygame")
        from imagestag.components.pygame import StreamViewPygame

        view_python = StreamViewPygame(640, 480, compositing_mode="python")
        assert view_python.compositing_mode == "python"

        view_native = StreamViewPygame(640, 480, compositing_mode="native")
        assert view_native.compositing_mode == "native"


class TestStreamViewPygameHeadless:
    """Tests for StreamViewPygame rendering in headless mode."""

    @pytest.fixture(autouse=True)
    def setup_headless(self):
        """Set up headless pygame for testing."""
        pygame = pytest.importorskip("pygame")
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        pygame.init()
        yield
        pygame.quit()

    def test_blit_image(self):
        """Test blitting an image to a surface."""
        import pygame
        from imagestag.components.pygame import StreamViewPygame

        view = StreamViewPygame(640, 480)

        # Create a test image
        pixels = np.zeros((480, 640, 3), dtype=np.uint8)
        pixels[:, :, 0] = 200  # Red
        test_image = Image(pixels, pixel_format='RGB')

        # Create a mock screen surface
        view._screen = pygame.Surface((640, 480))

        # Blit the image
        view._blit_image(test_image)

        # Verify the surface has the correct color
        color = view._screen.get_at((320, 240))
        assert color[0] == 200  # Red channel
