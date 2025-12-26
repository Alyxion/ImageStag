"""Tests for Encode, Decode, and ToDataUrl filters."""

import pytest
import numpy as np
import base64
from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import Encode, Decode, ToDataUrl, Filter, FilterPipeline
from imagestag.filters import ImageData, Compression, FormatSpec


@pytest.fixture
def rgb_image():
    """Create a simple RGB test image."""
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    # Red square in top-left
    pixels[0:50, 0:50, 0] = 255
    # Green square in top-right
    pixels[0:50, 50:100, 1] = 255
    # Blue square in bottom-left
    pixels[50:100, 0:50, 2] = 255
    # White square in bottom-right
    pixels[50:100, 50:100, :] = 255
    return Image(pixels, pixel_format=PixelFormat.RGB)


@pytest.fixture
def rgba_image():
    """Create an RGBA test image with transparency."""
    pixels = np.zeros((100, 100, 4), dtype=np.uint8)
    pixels[:, :, 0] = 255  # Red channel
    pixels[:, :, 3] = 128  # 50% alpha
    return Image(pixels, pixel_format=PixelFormat.RGBA)


class TestEncodeFilter:
    """Tests for the Encode filter."""

    def test_encode_jpeg_creates_compressed_image(self, rgb_image):
        """Encode to JPEG should create a compressed Image."""
        result = Encode(format='jpeg', quality=85).apply(rgb_image)

        assert result.is_compressed()
        assert result._compressed_mime == 'image/jpeg'
        assert result.width == rgb_image.width
        assert result.height == rgb_image.height

    def test_encode_png_creates_compressed_image(self, rgb_image):
        """Encode to PNG should create a compressed Image."""
        result = Encode(format='png').apply(rgb_image)

        assert result.is_compressed()
        assert result._compressed_mime == 'image/png'

    def test_encode_jpg_normalized_to_jpeg(self, rgb_image):
        """Format 'jpg' should be normalized to 'jpeg'."""
        encoder = Encode(format='jpg')
        assert encoder.format == 'jpeg'

        result = encoder.apply(rgb_image)
        assert result._compressed_mime == 'image/jpeg'

    def test_encode_quality_affects_size(self, rgb_image):
        """Higher quality should produce larger compressed data."""
        low_quality = Encode(format='jpeg', quality=10).apply(rgb_image)
        high_quality = Encode(format='jpeg', quality=95).apply(rgb_image)

        assert len(low_quality._compressed_data) < len(high_quality._compressed_data)

    def test_encode_preserves_dimensions(self, rgb_image):
        """Encoded image should have same dimensions."""
        result = Encode(format='jpeg').apply(rgb_image)

        assert result.width == rgb_image.width
        assert result.height == rgb_image.height

    def test_encode_compressed_can_still_access_pixels(self, rgb_image):
        """Compressed image should still allow pixel access (lazy decode)."""
        result = Encode(format='jpeg', quality=90).apply(rgb_image)

        # Should be able to get pixels (triggers decode)
        pixels = result.get_pixels(PixelFormat.RGB)

        assert pixels.shape == (100, 100, 3)
        assert pixels.dtype == np.uint8

    def test_encode_to_dict_serialization(self):
        """Encode filter should serialize correctly."""
        encoder = Encode(format='jpeg', quality=75)
        d = encoder.to_dict()

        assert d['type'] == 'Encode'
        assert d['format'] == 'jpeg'
        assert d['quality'] == 75

    def test_encode_from_dict_deserialization(self, rgb_image):
        """Encode filter should deserialize correctly."""
        d = {'type': 'Encode', 'format': 'png', 'quality': 90}
        encoder = Filter.from_dict(d)

        assert isinstance(encoder, Encode)
        assert encoder.format == 'png'

        result = encoder.apply(rgb_image)
        assert result._compressed_mime == 'image/png'

    def test_encode_parse_string(self):
        """Encode should parse from string format."""
        encoder = Filter.parse('encode jpeg')
        assert isinstance(encoder, Encode)
        assert encoder.format == 'jpeg'

    def test_encode_parse_with_quality(self):
        """Encode should parse quality from string."""
        encoder = Filter.parse('encode jpeg quality=80')
        assert isinstance(encoder, Encode)
        assert encoder.format == 'jpeg'
        assert encoder.quality == 80


class TestDecodeFilter:
    """Tests for the Decode filter."""

    def test_decode_decompresses_image(self, rgb_image):
        """Decode should decompress a compressed Image."""
        # First encode
        compressed = Encode(format='jpeg', quality=90).apply(rgb_image)
        assert compressed.is_compressed()

        # Then decode
        result = Decode(format='RGB').apply(compressed)

        assert not result.is_compressed()
        assert result.pixel_format == PixelFormat.RGB

    def test_decode_to_rgb(self, rgb_image):
        """Decode should output RGB format."""
        compressed = Encode(format='jpeg').apply(rgb_image)
        result = Decode(format='RGB').apply(compressed)

        assert result.pixel_format == PixelFormat.RGB
        pixels = result.get_pixels()
        assert pixels.shape == (100, 100, 3)

    def test_decode_to_gray(self, rgb_image):
        """Decode should be able to output GRAY format."""
        compressed = Encode(format='jpeg').apply(rgb_image)
        result = Decode(format='GRAY').apply(compressed)

        assert result.pixel_format == PixelFormat.GRAY
        pixels = result.get_pixels()
        assert len(pixels.shape) == 2  # 2D array for grayscale

    def test_decode_to_rgba(self, rgb_image):
        """Decode should be able to output RGBA format."""
        compressed = Encode(format='png').apply(rgb_image)
        result = Decode(format='RGBA').apply(compressed)

        assert result.pixel_format == PixelFormat.RGBA
        pixels = result.get_pixels()
        assert pixels.shape == (100, 100, 4)

    def test_decode_already_uncompressed(self, rgb_image):
        """Decode should work on uncompressed images too."""
        result = Decode(format='RGB').apply(rgb_image)

        assert result.pixel_format == PixelFormat.RGB
        assert result.width == rgb_image.width

    def test_decode_to_dict_serialization(self):
        """Decode filter should serialize correctly."""
        decoder = Decode(format='BGR')
        d = decoder.to_dict()

        assert d['type'] == 'Decode'
        assert d['format'] == 'BGR'

    def test_decode_parse_string(self):
        """Decode should parse from string format."""
        decoder = Filter.parse('decode RGB')
        assert isinstance(decoder, Decode)
        assert decoder.format == 'RGB'


class TestEncodeDecodePipeline:
    """Tests for Encode/Decode in pipelines."""

    def test_encode_decode_roundtrip(self, rgb_image):
        """Encode then Decode should produce valid image."""
        pipeline = FilterPipeline(filters=[
            Encode(format='jpeg', quality=95),
            Decode(format='RGB'),
        ])

        result = pipeline.apply(rgb_image)

        assert not result.is_compressed()
        assert result.width == rgb_image.width
        assert result.height == rgb_image.height

    def test_encode_decode_preserves_content_approximately(self, rgb_image):
        """Encode/Decode should preserve image content (with lossy tolerance)."""
        pipeline = FilterPipeline(filters=[
            Encode(format='jpeg', quality=100),  # Max quality
            Decode(format='RGB'),
        ])

        result = pipeline.apply(rgb_image)

        original_pixels = rgb_image.get_pixels(PixelFormat.RGB)
        result_pixels = result.get_pixels(PixelFormat.RGB)

        # JPEG is lossy, but high quality should be close
        # Allow some difference due to compression
        diff = np.abs(original_pixels.astype(float) - result_pixels.astype(float))
        mean_diff = np.mean(diff)

        assert mean_diff < 10  # Less than 10 average difference

    def test_encode_decode_png_lossless(self, rgb_image):
        """PNG encode/decode should be lossless."""
        pipeline = FilterPipeline(filters=[
            Encode(format='png'),
            Decode(format='RGB'),
        ])

        result = pipeline.apply(rgb_image)

        original_pixels = rgb_image.get_pixels(PixelFormat.RGB)
        result_pixels = result.get_pixels(PixelFormat.RGB)

        # PNG is lossless
        np.testing.assert_array_equal(original_pixels, result_pixels)

    def test_multiple_encode_decode_cycles(self, rgb_image):
        """Multiple encode/decode cycles should work."""
        pipeline = FilterPipeline(filters=[
            Encode(format='jpeg', quality=90),
            Decode(format='RGB'),
            Encode(format='png'),
            Decode(format='RGB'),
        ])

        result = pipeline.apply(rgb_image)

        assert result.width == rgb_image.width
        assert result.height == rgb_image.height

    def test_encode_in_complex_pipeline(self, rgb_image):
        """Encode should work in complex pipelines."""
        from imagestag.filters import Resize, GaussianBlur

        pipeline = FilterPipeline(filters=[
            Resize(scale=0.5),
            GaussianBlur(radius=1),
            Encode(format='jpeg', quality=80),
            Decode(format='RGB'),
        ])

        result = pipeline.apply(rgb_image)

        assert result.width == 50
        assert result.height == 50
        assert not result.is_compressed()


class TestToDataUrlFilter:
    """Tests for the ToDataUrl filter."""

    def test_todataurl_produces_valid_data_url(self, rgb_image):
        """ToDataUrl should produce valid data URL."""
        pipeline = FilterPipeline(filters=[
            Encode(format='jpeg'),
            ToDataUrl(),
        ])

        result = pipeline.apply(rgb_image)

        # Data URL should be in metadata
        assert '_data_url' in result.metadata
        data_url = result.metadata['_data_url']

        assert data_url.startswith('data:image/jpeg;base64,')
        # Verify we can decode it
        _, encoded = data_url.split(',', 1)
        decoded = base64.b64decode(encoded)
        assert len(decoded) > 0

    def test_todataurl_on_uncompressed_image(self, rgb_image):
        """ToDataUrl should work on uncompressed images (compresses first)."""
        result = ToDataUrl(format='jpeg', quality=80).apply(rgb_image)

        assert '_data_url' in result.metadata
        data_url = result.metadata['_data_url']
        assert data_url.startswith('data:image/jpeg;base64,')

    def test_todataurl_png_format(self, rgb_image):
        """ToDataUrl should work with PNG format."""
        pipeline = FilterPipeline(filters=[
            Encode(format='png'),
            ToDataUrl(format='png'),
        ])

        result = pipeline.apply(rgb_image)
        data_url = result.metadata['_data_url']

        assert data_url.startswith('data:image/png;base64,')

    def test_todataurl_preserves_image_content(self, rgb_image):
        """ToDataUrl output should decode to valid image."""
        result = ToDataUrl(format='jpeg', quality=95).apply(rgb_image)
        data_url = result.metadata['_data_url']

        # Decode and create new image
        _, encoded = data_url.split(',', 1)
        decoded = base64.b64decode(encoded)
        restored = Image(decoded)

        assert restored.width == rgb_image.width
        assert restored.height == rgb_image.height

    def test_todataurl_parse_string(self):
        """ToDataUrl should parse from string format."""
        filter = Filter.parse('todataurl')
        assert isinstance(filter, ToDataUrl)

    def test_todataurl_parse_with_format(self):
        """ToDataUrl should parse format from string."""
        filter = Filter.parse('todataurl png')
        assert isinstance(filter, ToDataUrl)
        assert filter.format == 'png'

    def test_todataurl_to_dict_serialization(self):
        """ToDataUrl filter should serialize correctly."""
        filter = ToDataUrl(format='jpeg', quality=75)
        d = filter.to_dict()

        assert d['type'] == 'ToDataUrl'
        assert d['format'] == 'jpeg'
        assert d['quality'] == 75


class TestImageDataDataUrl:
    """Tests for ImageData data URL methods."""

    def test_imagedata_to_data_url(self, rgb_image):
        """ImageData.to_data_url() should produce valid data URL."""
        data = ImageData.from_image(rgb_image)
        data_url = data.to_data_url('jpeg', quality=80)

        assert data_url.startswith('data:image/jpeg;base64,')

    def test_imagedata_from_data_url(self):
        """ImageData.from_data_url() should parse data URL correctly."""
        # Create a simple JPEG data URL
        img = Image(np.zeros((10, 10, 3), dtype=np.uint8))
        jpeg_bytes = img.encode('jpeg')
        encoded = base64.b64encode(jpeg_bytes).decode('ascii')
        data_url = f"data:image/jpeg;base64,{encoded}"

        data = ImageData.from_data_url(data_url)

        assert data.format.compression == Compression.JPEG
        assert data._bytes is not None
        assert data._data_url == data_url

    def test_imagedata_from_data_url_png(self):
        """ImageData.from_data_url() should work with PNG."""
        img = Image(np.zeros((10, 10, 3), dtype=np.uint8))
        png_bytes = img.encode('png')
        encoded = base64.b64encode(png_bytes).decode('ascii')
        data_url = f"data:image/png;base64,{encoded}"

        data = ImageData.from_data_url(data_url)

        assert data.format.compression == Compression.PNG

    def test_imagedata_with_data_url(self):
        """ImageData.with_data_url() should return copy with URL set."""
        data = ImageData.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        assert not data.has_data_url

        new_data = data.with_data_url('data:image/jpeg;base64,test')

        assert new_data.has_data_url
        assert new_data.data_url == 'data:image/jpeg;base64,test'
        # Original unchanged
        assert not data.has_data_url

    def test_imagedata_to_data_url_uses_cached_bytes(self):
        """ImageData.to_data_url() should use existing compressed bytes."""
        # Create ImageData with compressed bytes
        img = Image(np.zeros((10, 10, 3), dtype=np.uint8))
        jpeg_bytes = img.encode('jpeg')
        data = ImageData.from_bytes(jpeg_bytes, 'image/jpeg')

        data_url = data.to_data_url('jpeg')

        # Should use existing bytes without re-encoding
        assert data_url.startswith('data:image/jpeg;base64,')
        _, encoded = data_url.split(',', 1)
        decoded = base64.b64decode(encoded)
        assert decoded == jpeg_bytes

    def test_imagedata_to_data_url_returns_cached(self):
        """ImageData.to_data_url() should return cached data URL if available."""
        data = ImageData(
            format=FormatSpec(compression=Compression.JPEG),
            _bytes=b'dummy',
            _data_url='data:image/jpeg;base64,cached'
        )

        result = data.to_data_url('jpeg')

        assert result == 'data:image/jpeg;base64,cached'

    def test_imagedata_roundtrip(self, rgb_image):
        """ImageData data URL roundtrip should preserve content."""
        data = ImageData.from_image(rgb_image)
        data_url = data.to_data_url('png')

        restored = ImageData.from_data_url(data_url)
        restored_image = restored.to_image()

        assert restored_image.width == rgb_image.width
        assert restored_image.height == rgb_image.height


class TestFullPipeline:
    """Integration tests for full encode/base64 pipeline."""

    def test_full_pipeline_with_todataurl(self, rgb_image):
        """Full pipeline: Resize -> Encode -> ToDataUrl."""
        from imagestag.filters import Resize

        pipeline = FilterPipeline(filters=[
            Resize(scale=0.5),
            Encode(format='jpeg', quality=80),
            ToDataUrl(),
        ])

        result = pipeline.apply(rgb_image)

        assert result.is_compressed()
        assert '_data_url' in result.metadata
        data_url = result.metadata['_data_url']
        assert data_url.startswith('data:image/jpeg;base64,')

        # Verify content
        _, encoded = data_url.split(',', 1)
        decoded = base64.b64decode(encoded)
        restored = Image(decoded)
        assert restored.width == 50
        assert restored.height == 50
