# FilterPipeline

Chain of filters applied in sequence.

Supports automatic format conversion between filters when a filter declares
specific input format requirements and implicit_conversion is enabled.

Can process:
- Image objects (via apply())
- ImageData containers (via process())
- Any format that ImageData supports (JPEG bytes, numpy arrays, etc.)

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `filters` | list | [] |  |
| `auto_convert` | bool | True |  |
