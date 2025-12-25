# Tests for channel filter operations
"""
Test SplitChannels, MergeChannels, and ExtractChannel filters.
"""

import numpy as np
import pytest

from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import (
    SplitChannels,
    MergeChannels,
    ExtractChannel,
    Brightness,
    FilterGraph,
    Blend,
    BlendMode,
)


@pytest.fixture
def rgb_image():
    """Create a test RGB image with known channel values."""
    # Create 100x100 image where:
    # R channel = 100, G channel = 150, B channel = 200
    data = np.zeros((100, 100, 3), dtype=np.uint8)
    data[:, :, 0] = 100  # Red
    data[:, :, 1] = 150  # Green
    data[:, :, 2] = 200  # Blue
    return Image(data, pixel_format=PixelFormat.RGB)


@pytest.fixture
def gradient_rgb_image():
    """Create a test RGB image with gradient values."""
    data = np.zeros((100, 100, 3), dtype=np.uint8)
    # Horizontal gradient in each channel
    for x in range(100):
        data[:, x, 0] = int(x * 2.55)  # R: 0-255
        data[:, x, 1] = int((99 - x) * 2.55)  # G: 255-0
        data[:, x, 2] = 128  # B: constant
    return Image(data, pixel_format=PixelFormat.RGB)


class TestSplitChannels:
    """Tests for SplitChannels filter."""

    def test_split_rgb_produces_three_outputs(self, rgb_image):
        """SplitChannels should return R, G, B channel images."""
        result = SplitChannels().apply(rgb_image)

        assert isinstance(result, dict)
        assert set(result.keys()) == {'R', 'G', 'B'}

    def test_split_outputs_are_grayscale(self, rgb_image):
        """Each channel output should be a grayscale image."""
        result = SplitChannels().apply(rgb_image)

        for name, img in result.items():
            assert img.pixel_format == PixelFormat.GRAY
            assert len(img.get_pixels().shape) == 2

    def test_split_outputs_have_correct_metadata(self, rgb_image):
        """Each output should have channel metadata set."""
        result = SplitChannels().apply(rgb_image)

        assert result['R'].metadata['channel'] == 'R'
        assert result['G'].metadata['channel'] == 'G'
        assert result['B'].metadata['channel'] == 'B'

        # Also check source format
        for img in result.values():
            assert img.metadata['source_format'] == 'RGB'

    def test_split_preserves_channel_values(self, rgb_image):
        """Split channels should contain the correct pixel values."""
        result = SplitChannels().apply(rgb_image)

        # Original: R=100, G=150, B=200
        r_pixels = result['R'].get_pixels()
        g_pixels = result['G'].get_pixels()
        b_pixels = result['B'].get_pixels()

        assert np.all(r_pixels == 100)
        assert np.all(g_pixels == 150)
        assert np.all(b_pixels == 200)

    def test_split_maintains_dimensions(self, rgb_image):
        """Split channels should have same dimensions as original."""
        result = SplitChannels().apply(rgb_image)

        for img in result.values():
            assert img.width == rgb_image.width
            assert img.height == rgb_image.height

    def test_port_specs(self):
        """SplitChannels should have correct port specifications."""
        assert SplitChannels.is_multi_output()
        assert not SplitChannels.is_multi_input()

        ports = SplitChannels.get_output_ports()
        assert len(ports) == 3
        assert ports[0]['name'] == 'R'
        assert ports[1]['name'] == 'G'
        assert ports[2]['name'] == 'B'


class TestMergeChannels:
    """Tests for MergeChannels filter."""

    def test_merge_rgb_roundtrip(self, rgb_image):
        """Split -> Merge should produce original image."""
        split_result = SplitChannels().apply(rgb_image)

        merge = MergeChannels(inputs=['R', 'G', 'B'])
        merged = merge.apply_multi(split_result)

        # Compare pixels
        original_pixels = rgb_image.get_pixels()
        merged_pixels = merged.get_pixels()
        np.testing.assert_array_equal(original_pixels, merged_pixels)

    def test_merge_produces_rgb(self, rgb_image):
        """MergeChannels should produce an RGB image."""
        split_result = SplitChannels().apply(rgb_image)
        merged = MergeChannels(inputs=['R', 'G', 'B']).apply_multi(split_result)

        assert merged.pixel_format == PixelFormat.RGB

    def test_merge_with_swapped_channels(self, rgb_image):
        """MergeChannels can combine channels in different order."""
        split_result = SplitChannels().apply(rgb_image)

        # Swap R and B channels
        merge = MergeChannels(inputs=['B', 'G', 'R'])
        merged = merge.apply_multi(split_result)

        pixels = merged.get_pixels()
        # Original: R=100, G=150, B=200
        # After swap: R=200, G=150, B=100
        assert np.all(pixels[:, :, 0] == 200)  # New R = old B
        assert np.all(pixels[:, :, 1] == 150)  # G unchanged
        assert np.all(pixels[:, :, 2] == 100)  # New B = old R

    def test_merge_maintains_dimensions(self, rgb_image):
        """Merged image should have same dimensions as inputs."""
        split_result = SplitChannels().apply(rgb_image)
        merged = MergeChannels(inputs=['R', 'G', 'B']).apply_multi(split_result)

        assert merged.width == rgb_image.width
        assert merged.height == rgb_image.height

    def test_port_specs(self):
        """MergeChannels should have correct port specifications."""
        assert MergeChannels.is_multi_input()
        assert not MergeChannels.is_multi_output()

        ports = MergeChannels.get_input_ports()
        assert len(ports) == 3
        assert ports[0]['name'] == 'R'
        assert ports[1]['name'] == 'G'
        assert ports[2]['name'] == 'B'


class TestExtractChannel:
    """Tests for ExtractChannel filter."""

    def test_extract_red_channel(self, rgb_image):
        """ExtractChannel should extract the R channel."""
        result = ExtractChannel(channel='R').apply(rgb_image)

        assert result.pixel_format == PixelFormat.GRAY
        assert result.metadata['channel'] == 'R'
        assert np.all(result.get_pixels() == 100)

    def test_extract_green_channel(self, rgb_image):
        """ExtractChannel should extract the G channel."""
        result = ExtractChannel(channel='G').apply(rgb_image)

        assert result.metadata['channel'] == 'G'
        assert np.all(result.get_pixels() == 150)

    def test_extract_blue_channel(self, rgb_image):
        """ExtractChannel should extract the B channel."""
        result = ExtractChannel(channel='B').apply(rgb_image)

        assert result.metadata['channel'] == 'B'
        assert np.all(result.get_pixels() == 200)

    def test_extract_by_index(self, rgb_image):
        """ExtractChannel should work with numeric index."""
        result = ExtractChannel(channel='1').apply(rgb_image)  # Green = index 1

        assert result.metadata['channel'] == 'G'
        assert np.all(result.get_pixels() == 150)

    def test_extract_invalid_channel_raises(self, rgb_image):
        """ExtractChannel should raise error for invalid channel."""
        with pytest.raises(ValueError, match="not found"):
            ExtractChannel(channel='X').apply(rgb_image)

    def test_extract_invalid_index_raises(self, rgb_image):
        """ExtractChannel should raise error for out-of-range index."""
        with pytest.raises(ValueError, match="out of range"):
            ExtractChannel(channel='5').apply(rgb_image)


class TestChannelPipeline:
    """Tests for channel operations in pipelines."""

    def test_split_process_merge_roundtrip(self, gradient_rgb_image):
        """Split -> process each channel -> merge should work correctly."""
        # This simulates a more realistic use case
        split_result = SplitChannels().apply(gradient_rgb_image)

        # Apply brightness to each channel (identity transform with factor=1.0)
        processed = {}
        for name, img in split_result.items():
            processed[name] = Brightness(factor=1.0).apply(img)

        # Merge back
        merged = MergeChannels(inputs=['R', 'G', 'B']).apply_multi(processed)

        # Should be very close to original (minor floating point differences)
        original_pixels = gradient_rgb_image.get_pixels()
        merged_pixels = merged.get_pixels()
        np.testing.assert_allclose(original_pixels, merged_pixels, atol=1)

    def test_split_modify_single_channel(self, rgb_image):
        """Modify only one channel and merge back."""
        split_result = SplitChannels().apply(rgb_image)

        # Invert just the red channel by scaling
        r_modified = Brightness(factor=0.0).apply(split_result['R'])  # Black out red
        split_result['R'] = r_modified

        merged = MergeChannels(inputs=['R', 'G', 'B']).apply_multi(split_result)

        pixels = merged.get_pixels()
        assert np.all(pixels[:, :, 0] == 0)    # R is now 0
        assert np.all(pixels[:, :, 1] == 150)  # G unchanged
        assert np.all(pixels[:, :, 2] == 200)  # B unchanged

    def test_metadata_set_by_split(self, rgb_image):
        """Channel metadata is set by SplitChannels."""
        split_result = SplitChannels().apply(rgb_image)

        # Verify metadata is set correctly after split
        for name in ['R', 'G', 'B']:
            assert split_result[name].metadata.get('channel') == name
            assert split_result[name].metadata.get('source_format') == 'RGB'


class TestPortSpecifications:
    """Tests for port specification system."""

    def test_standard_filter_has_default_ports(self):
        """Standard filters should have single input/output ports."""
        ports_in = Brightness.get_input_ports()
        ports_out = Brightness.get_output_ports()

        assert len(ports_in) == 1
        assert len(ports_out) == 1
        assert ports_in[0]['name'] == 'input'
        assert ports_out[0]['name'] == 'output'

    def test_blend_has_named_input_ports(self):
        """Blend filter should have named input ports."""
        ports = Blend.get_input_ports()

        assert len(ports) == 3
        assert ports[0]['name'] == 'a'
        assert ports[1]['name'] == 'b'
        assert ports[2]['name'] == 'mask'
        assert ports[2].get('optional') is True

    def test_is_multi_output_false_for_standard(self):
        """Standard filters should not be multi-output."""
        assert not Brightness.is_multi_output()
        assert not Blend.is_multi_output()

    def test_is_multi_input_true_for_combiners(self):
        """Combiner filters should be multi-input."""
        assert Blend.is_multi_input()
        assert MergeChannels.is_multi_input()
