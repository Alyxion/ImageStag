# MergeChannels

Merge R, G, B grayscale channels back into an RGB image.

Takes three grayscale images and combines them into RGB.

Example:
    merge = MergeChannels(inputs=['R', 'G', 'B'])
    result = merge.apply_multi({'R': r_img, 'G': g_img, 'B': b_img})

## Input Ports

- **R**: Red channel
- **G**: Green channel
- **B**: Blue channel

## Examples

```
R
```
```
R
```

## Frameworks

Native support: RAW, CV
