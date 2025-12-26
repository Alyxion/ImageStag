# DenoiseWavelet

Wavelet-based denoising.

Denoises using wavelet decomposition. Effective for
multi-scale noise patterns.

Requires: scikit-image (optional dependency)

Parameters:
    sigma: Noise standard deviation (None = estimate)
    wavelet: Wavelet type ('db1', 'sym4', 'coif1', etc.)
    mode: Signal extension mode
    rescale_sigma: Rescale sigma for each level (default True)

Example:
    'denoisewavelet()' or 'denoisewavelet(wavelet=sym4)'

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `sigma` | float | None | Noise standard deviation (None = estimate) |
| `wavelet` | str | 'db1' | Wavelet type ('db1', 'sym4', 'coif1', etc.) |
| `mode` | str | 'soft' | Signal extension mode |
| `rescale_sigma` | bool | True | Rescale sigma for each level (default True) |

## Examples

```
denoisewavelet()
```

## Frameworks

Native support: RAW

## Requirements

- scikit-image
