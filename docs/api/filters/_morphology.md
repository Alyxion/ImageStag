# Morphology Filters

[![BlackHat](../gallery/filters/blackhat.jpg)](./blackhat.md)

## [BlackHat](./blackhat.md)

Black-hat transform (difference between closing and input).

**Parameters:** `kernel_size`, `shape`

[![Dilate](../gallery/filters/dilate.jpg)](./dilate.md)

## [Dilate](./dilate.md)

Morphological dilation.

**Parameters:** `kernel_size`, `shape`, `iterations`

[![Erode](../gallery/filters/erode.jpg)](./erode.md)

## [Erode](./erode.md)

Morphological erosion.

**Parameters:** `kernel_size`, `shape`, `iterations`

[![Frangi](../gallery/filters/frangi.jpg)](./frangi.md)

## [Frangi](./frangi.md)

Frangi vesselness filter for vessel/ridge detection.

**Parameters:** `scale_min`, `scale_max`, `scale_step`, `beta1`, ...

[![Hessian](../gallery/filters/hessian.jpg)](./hessian.md)

## [Hessian](./hessian.md)

Hessian-based ridge detection (general-purpose).

**Parameters:** `scale_min`, `scale_max`, `scale_step`, `beta`, ...

[![MedialAxis](../gallery/filters/medialaxis.jpg)](./medialaxis.md)

## [MedialAxis](./medialaxis.md)

Compute the medial axis transform.

**Parameters:** `return_distance`

[![Meijering](../gallery/filters/meijering.jpg)](./meijering.md)

## [Meijering](./meijering.md)

Meijering neuriteness filter for neural structure detection.

**Parameters:** `scale_min`, `scale_max`, `scale_step`, `black_ridges`

[![MorphClose](../gallery/filters/morphclose.jpg)](./morphclose.md)

## [MorphClose](./morphclose.md)

Morphological closing (dilation followed by erosion).

**Parameters:** `kernel_size`, `shape`

[![MorphGradient](../gallery/filters/morphgradient.jpg)](./morphgradient.md)

## [MorphGradient](./morphgradient.md)

Morphological gradient (difference between dilation and erosion).

**Parameters:** `kernel_size`, `shape`

[![MorphOpen](../gallery/filters/morphopen.jpg)](./morphopen.md)

## [MorphOpen](./morphopen.md)

Morphological opening (erosion followed by dilation).

**Parameters:** `kernel_size`, `shape`

[![RemoveSmallHoles](../gallery/filters/removesmallholes.jpg)](./removesmallholes.md)

## [RemoveSmallHoles](./removesmallholes.md)

Fill small holes in binary objects.

**Parameters:** `area_threshold`, `connectivity`

[![RemoveSmallObjects](../gallery/filters/removesmallobjects.jpg)](./removesmallobjects.md)

## [RemoveSmallObjects](./removesmallobjects.md)

Remove small connected regions from binary image.

**Parameters:** `min_size`, `connectivity`

[![Sato](../gallery/filters/sato.jpg)](./sato.md)

## [Sato](./sato.md)

Sato tubeness filter for 2D/3D tubular structure detection.

**Parameters:** `scale_min`, `scale_max`, `scale_step`, `black_ridges`

[![Skeletonize](../gallery/filters/skeletonize.jpg)](./skeletonize.md)

## [Skeletonize](./skeletonize.md)

Reduce binary shapes to 1-pixel-wide skeleton.

**Parameters:** `method`

[![TopHat](../gallery/filters/tophat.jpg)](./tophat.md)

## [TopHat](./tophat.md)

Top-hat transform (difference between input and opening).

**Parameters:** `kernel_size`, `shape`
