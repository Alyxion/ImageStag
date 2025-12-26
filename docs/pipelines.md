# Filter Pipelines

Pipelines chain multiple filters in sequence with automatic format conversion.

## Creating Pipelines

```python
from imagestag.filters import FilterPipeline, Resize, GaussianBlur, Brightness

# From list of filters
pipeline = FilterPipeline(filters=[
    Resize(scale=0.5),
    GaussianBlur(radius=2),
    Brightness(factor=1.1),
])

# Using append
pipeline = FilterPipeline()
pipeline.append(Resize(scale=0.5))
pipeline.append(GaussianBlur(radius=2))

# Using extend
pipeline.extend([Brightness(factor=1.1), Contrast(factor=1.2)])
```

## Applying Pipelines

```python
# Apply to single image
result = pipeline.apply(image)

# Apply to ImageList
results = pipeline(image_list)
```

## Parsing from String

Pipelines can be parsed from compact string notation:

```python
# Semicolon-separated
pipeline = FilterPipeline.parse("resize 0.5; blur 2.0; brightness 1.1")

# Pipe-separated
pipeline = FilterPipeline.parse("resize(scale=0.5)|blur(radius=2)|brightness(factor=1.1)")

# With keyword arguments
pipeline = FilterPipeline.parse("resize size=800,600; lens k1=-0.15 k2=0.02")
```

## Automatic Format Conversion

Pipelines automatically convert between formats when filters have specific requirements:

```python
from imagestag.filters import Encode, Decode, FilterPipeline

# Encode creates compressed image, next filter auto-decodes if needed
pipeline = FilterPipeline([
    Encode(format='jpeg', quality=85),
    Resize(scale=0.5),  # Auto-decodes compressed input
])
```

To disable auto-conversion:

```python
pipeline = FilterPipeline(filters=[...], auto_convert=False)
```

## ImageData Processing

Pipelines can process any format through `ImageData`:

```python
from imagestag.filters import ImageData, FilterPipeline

# Process JPEG bytes directly
data = ImageData.from_bytes(jpeg_bytes)
result = pipeline.process(data)

# Get output as bytes
output_bytes = result.to_bytes('jpeg', quality=85)

# Process NumPy array
data = ImageData.from_array(cv_frame, pixel_format='BGR')
result = pipeline.process(data)
cv_output = result.to_cv()
```

## Serialization

```python
# To JSON dict
d = pipeline.to_dict()
# {
#   'type': 'FilterPipeline',
#   'filters': [
#     {'type': 'Resize', 'scale': 0.5},
#     {'type': 'GaussianBlur', 'radius': 2.0}
#   ]
# }

# From JSON dict
restored = FilterPipeline.from_dict(d)

# To compact string
s = pipeline.to_string()
# "resize(scale=0.5)|gaussianblur(radius=2.0)"
```

## Pipeline Inspection

```python
# Number of filters
len(pipeline)  # 3

# Iterate filters
for f in pipeline:
    print(f.__class__.__name__)

# Access by index
first_filter = pipeline[0]
```

## Example: Web Image Processing

```python
from imagestag.filters import FilterPipeline, Resize, FalseColor, Encode, ToDataUrl

# Pipeline for web visualization
web_pipeline = FilterPipeline([
    Resize(size=(1920, 1080)),
    FalseColor(colormap='viridis'),
    Encode(format='jpeg', quality=80),
    ToDataUrl(),
])

result = web_pipeline.apply(image)
data_url = result.metadata['_data_url']
# Use in HTML: <img src="{data_url}">
```
