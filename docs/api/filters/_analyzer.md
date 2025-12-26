# Analyzer Filters

## [BoundingBoxDetector](./boundingboxdetector.md)

Base class for object detection that returns bounding boxes.

**Parameters:** `store_in_context`, `store_in_metadata`, `result_key`, `min_confidence`

## [ColorAnalyzer](./coloranalyzer.md)

Analyze dominant colors in the image.

**Parameters:** `store_in_context`, `store_in_metadata`, `result_key`

## [HistogramAnalyzer](./histogramanalyzer.md)

Compute image histogram.

**Parameters:** `store_in_context`, `store_in_metadata`, `result_key`, `bins`

## [ImageStats](./imagestats.md)

Compute basic image statistics.

**Parameters:** `store_in_context`, `store_in_metadata`, `result_key`

## [RegionAnalyzer](./regionanalyzer.md)

Analyze a specific region of the image.

**Parameters:** `store_in_context`, `store_in_metadata`, `result_key`, `x`, ...
