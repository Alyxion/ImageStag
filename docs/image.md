# Image Class

The `Image` class is the core data type in ImageStag, supporting multiple storage frameworks and pixel formats.

## Creating Images

```python
from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.definitions import ImsFramework

# Load from file
img = Image.load("photo.jpg")

# From PIL Image
from PIL import Image as PILImage
pil_img = PILImage.open("photo.jpg")
img = Image(pil_img)

# From NumPy array (RGB)
import numpy as np
pixels = np.zeros((480, 640, 3), dtype=np.uint8)
img = Image(pixels, pixel_format=PixelFormat.RGB)

# From NumPy array (BGR/OpenCV)
cv_frame = cv2.imread("photo.jpg")
img = Image(cv_frame, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)

# From compressed bytes
with open("photo.jpg", "rb") as f:
    img = Image(f.read())

# From base64 data URL
img = Image.from_data_url("data:image/jpeg;base64,/9j/4AAQ...")
```

## Pixel Formats

| Format | Channels | Description |
|--------|----------|-------------|
| `RGB` | 3 | Standard RGB (PIL default) |
| `RGBA` | 4 | RGB with alpha channel |
| `BGR` | 3 | OpenCV convention |
| `BGRA` | 4 | OpenCV with alpha |
| `GRAY` | 1 | Grayscale |
| `HSV` | 3 | Hue-Saturation-Value |

```python
from imagestag.pixel_format import PixelFormat

# Get pixels in specific format
rgb_pixels = img.get_pixels(PixelFormat.RGB)
gray_pixels = img.get_pixels(PixelFormat.GRAY)
bgr_pixels = img.get_pixels(PixelFormat.BGR)

# Convert image format
gray_img = img.convert(PixelFormat.GRAY)
```

## Storage Frameworks

| Framework | Backend | Use Case |
|-----------|---------|----------|
| `PIL` | Pillow | General use, default |
| `RAW` | NumPy (RGB order) | Fast pixel access |
| `CV` | NumPy (BGR order) | OpenCV integration |

```python
from imagestag.definitions import ImsFramework

# Check current framework
print(img.framework)  # ImsFramework.PIL

# Convert to specific framework
cv_img = img.to_framework(ImsFramework.CV)
```

## Properties

```python
img.width          # Image width in pixels
img.height         # Image height in pixels
img.size           # (width, height) tuple
img.pixel_format   # Current PixelFormat
img.framework      # Current ImsFramework
img.metadata       # Dict for custom metadata
```

## Transformations

```python
# Resize
resized = img.resized((800, 600))
resized = img.resized(scale=0.5)

# Convert pixel format
gray = img.convert(PixelFormat.GRAY)

# Get PIL Image
pil_img = img.to_pil()

# Get NumPy array
pixels = img.get_pixels()
bgr = img.get_pixels(PixelFormat.BGR)
```

## Saving and Encoding

```python
# Save to file
img.save("output.jpg", quality=90)
img.save("output.png")

# Encode to bytes
jpeg_bytes = img.encode("jpeg", quality=85)
png_bytes = img.encode("png")

# To base64 data URL
data_url = img.to_data_url(format="jpeg", quality=80)
```

## Compressed Storage

Images can be stored in compressed form without immediate decoding:

```python
# Create from compressed bytes (lazy decode)
img = Image.from_compressed(jpeg_bytes, mime_type="image/jpeg")
print(img.is_compressed())  # True

# Pixels are decoded on first access
pixels = img.get_pixels()  # Triggers decode
print(img.is_compressed())  # Still True, data cached

# Get compressed data
data, mime = img.get_compressed("jpeg", quality=85)
```

## Sample Images

```python
from imagestag.samples import stag, group

# Built-in sample images
stag_img = stag()   # Stag photo
group_img = group()  # Group photo
```
