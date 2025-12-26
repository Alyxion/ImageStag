# Restoration Filters

[![DenoiseNLMeans](../gallery/filters/denoisenlmeans.jpg)](./denoisenlmeans.md)

## [DenoiseNLMeans](./denoisenlmeans.md)

Non-local means denoising.

**Parameters:** `h`, `patch_size`, `patch_distance`, `fast_mode`

[![DenoiseTV](../gallery/filters/denoisetv.jpg)](./denoisetv.md)

## [DenoiseTV](./denoisetv.md)

Total Variation (Chambolle) denoising.

**Parameters:** `weight`, `n_iter_max`

## [DenoiseWavelet](./denoisewavelet.md)

Wavelet-based denoising.

**Parameters:** `sigma`, `wavelet`, `mode`, `rescale_sigma`

[![Inpaint](../gallery/filters/inpaint.jpg)](./inpaint.md)

## [Inpaint](./inpaint.md)

Biharmonic inpainting to fill missing regions.

**Parameters:** `mask_threshold`
