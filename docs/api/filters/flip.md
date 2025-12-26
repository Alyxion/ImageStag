# Flip


![Flip example](../gallery/filters/flip.jpg)

Flip image horizontally and/or vertically.

Supports multiple backends for optimal performance.

Parameters:
    mode: Flip direction - 'h' (horizontal/mirror), 'v' (vertical), 'hv' or 'vh' (both)
    backend: Processing backend ('auto', 'pil', 'cv', 'numpy')

Example:
    'flip h'    - mirror horizontally (left-right)
    'flip v'    - flip vertically (top-bottom)
    'flip hv'   - flip both (rotate 180°)

Aliases:
    'mirror' or 'fliplr' - horizontal flip
    'flipud' or 'flipv'  - vertical flip

## Aliases

- `mirror` → `Flip(mode=h)`
- `fliplr` → `Flip(mode=h)`
- `flipud` → `Flip(mode=v)`
- `flipv` → `Flip(mode=v)`

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mode` | str | '' | Flip direction - 'h' (horizontal/mirror), 'v' (vertical), 'hv' or 'vh' (both) |
| `backend` | str | 'auto' | Processing backend ('auto', 'pil', 'cv', 'numpy') |

## Examples

```
flip h
```
```
flip v
```
```
flip hv
```
```
mirror
```
```
flipud
```

## Frameworks

Native support: PIL, CV, RAW
