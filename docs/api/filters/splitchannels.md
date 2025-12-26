# SplitChannels


![SplitChannels example](../gallery/filters/splitchannels.jpg)

Split RGB/RGBA image into individual channel images.

Each output is a grayscale image with metadata['channel'] set to
the channel name ('R', 'G', 'B', or 'A').

Example:
    split = SplitChannels()
    result = split.apply(rgb_image)
    # result = {'R': gray_r, 'G': gray_g, 'B': gray_b}

## Output Ports

- **R**: Red channel
- **G**: Green channel
- **B**: Blue channel

## Examples

```
R
```

## Frameworks

Native support: RAW, CV
