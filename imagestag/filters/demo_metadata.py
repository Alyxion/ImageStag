# ImageStag Filters - Demo Metadata
"""
Demo presets, categories, and recommended images for Filter Explorer.

This module provides metadata for interactive filter testing:
- Category assignments for filter organization
- Preset parameter configurations for quick demos
- Recommended sample images that best showcase each filter
"""

from __future__ import annotations

from typing import Any


# Filter category assignments
FILTER_CATEGORIES: dict[str, str] = {
    # Color adjustments
    'Brightness': 'color',
    'Contrast': 'color',
    'Saturation': 'color',
    'Sharpness': 'color',
    'Grayscale': 'color',
    'Invert': 'color',
    'Threshold': 'color',

    # Blur and sharpen
    'GaussianBlur': 'blur',
    'BoxBlur': 'blur',
    'UnsharpMask': 'blur',
    'Sharpen': 'blur',

    # Geometric transforms
    'Resize': 'geometric',
    'Crop': 'geometric',
    'CenterCrop': 'geometric',
    'Rotate': 'geometric',
    'Flip': 'geometric',
    'LensDistortion': 'geometric',
    'Perspective': 'geometric',

    # Edge detection
    'Canny': 'edge',
    'Sobel': 'edge',
    'Laplacian': 'edge',
    'EdgeEnhance': 'edge',

    # Morphological operations
    'Erode': 'morphology',
    'Dilate': 'morphology',
    'MorphOpen': 'morphology',
    'MorphClose': 'morphology',
    'MorphGradient': 'morphology',
    'TopHat': 'morphology',
    'BlackHat': 'morphology',

    # Detection
    'FaceDetector': 'detection',
    'EyeDetector': 'detection',
    'ContourDetector': 'detection',

    # Analyzers
    'ImageStats': 'analyzers',
    'HistogramAnalyzer': 'analyzers',
    'ColorAnalyzer': 'analyzers',
    'RegionAnalyzer': 'analyzers',
    'BoundingBoxDetector': 'analyzers',

    # Format conversion
    'Encode': 'format',
    'Decode': 'format',
    'ConvertFormat': 'format',

    # Compositing
    'Blend': 'compositing',
    'Composite': 'compositing',
    'MaskApply': 'compositing',

    # Channel operations
    'SplitChannels': 'channels',
    'MergeChannels': 'channels',
    'ExtractChannel': 'channels',

    # Size matching
    'SizeMatcher': 'compositing',

    # Image generation
    'ImageGenerator': 'generator',
}

# All available categories in display order
CATEGORIES = [
    'all',
    'color',
    'blur',
    'geometric',
    'edge',
    'morphology',
    'channels',
    'compositing',
    'generator',
    'detection',
    'analyzers',
]

# Filter metadata: presets and recommended images
FILTER_METADATA: dict[str, dict[str, Any]] = {
    # === Color Filters ===
    'Brightness': {
        'description': 'Adjust image brightness',
        'recommended_images': ['moon', 'camera', 'astronaut'],
        'presets': [
            {'name': 'Subtle', 'params': {'factor': 1.2}},
            {'name': 'Bright', 'params': {'factor': 1.5}},
            {'name': 'Very Bright', 'params': {'factor': 2.0}},
            {'name': 'Dim', 'params': {'factor': 0.7}},
            {'name': 'Dark', 'params': {'factor': 0.4}},
        ],
    },
    'Contrast': {
        'description': 'Adjust image contrast',
        'recommended_images': ['camera', 'moon', 'astronaut'],
        'presets': [
            {'name': 'Low', 'params': {'factor': 0.5}},
            {'name': 'Subtle', 'params': {'factor': 1.3}},
            {'name': 'High', 'params': {'factor': 1.8}},
            {'name': 'Extreme', 'params': {'factor': 2.5}},
        ],
    },
    'Saturation': {
        'description': 'Adjust color saturation',
        'recommended_images': ['astronaut', 'chelsea', 'coffee', 'rocket'],
        'presets': [
            {'name': 'Muted', 'params': {'factor': 0.5}},
            {'name': 'Desaturated', 'params': {'factor': 0.0}},
            {'name': 'Vivid', 'params': {'factor': 1.5}},
            {'name': 'Intense', 'params': {'factor': 2.0}},
        ],
    },
    'Sharpness': {
        'description': 'Adjust image sharpness',
        'recommended_images': ['camera', 'astronaut', 'text'],
        'presets': [
            {'name': 'Soft', 'params': {'factor': 0.5}},
            {'name': 'Sharp', 'params': {'factor': 1.5}},
            {'name': 'Very Sharp', 'params': {'factor': 2.5}},
        ],
    },
    'Grayscale': {
        'description': 'Convert to grayscale',
        'recommended_images': ['astronaut', 'chelsea', 'rocket'],
        'presets': [
            {'name': 'Luminosity', 'params': {'method': 'luminosity'}},
            {'name': 'Average', 'params': {'method': 'average'}},
            {'name': 'Lightness', 'params': {'method': 'lightness'}},
        ],
    },
    'Invert': {
        'description': 'Invert colors (negative)',
        'recommended_images': ['astronaut', 'camera', 'text'],
        'presets': [
            {'name': 'Default', 'params': {}},
        ],
    },
    'Threshold': {
        'description': 'Binary threshold',
        'recommended_images': ['camera', 'coins', 'page', 'text'],
        'presets': [
            {'name': 'Low', 'params': {'value': 64}},
            {'name': 'Mid', 'params': {'value': 128}},
            {'name': 'High', 'params': {'value': 192}},
        ],
    },

    # === Blur Filters ===
    'GaussianBlur': {
        'description': 'Gaussian blur smoothing',
        'recommended_images': ['camera', 'astronaut', 'coins'],
        'presets': [
            {'name': 'Subtle', 'params': {'radius': 1.0}},
            {'name': 'Medium', 'params': {'radius': 3.0}},
            {'name': 'Strong', 'params': {'radius': 6.0}},
            {'name': 'Heavy', 'params': {'radius': 10.0}},
        ],
    },
    'BoxBlur': {
        'description': 'Box filter blur',
        'recommended_images': ['camera', 'astronaut'],
        'presets': [
            {'name': 'Small', 'params': {'radius': 2}},
            {'name': 'Medium', 'params': {'radius': 5}},
            {'name': 'Large', 'params': {'radius': 10}},
        ],
    },
    'UnsharpMask': {
        'description': 'Sharpen via unsharp masking',
        'recommended_images': ['camera', 'astronaut', 'text'],
        'presets': [
            {'name': 'Subtle', 'params': {'radius': 1.0, 'percent': 50, 'threshold': 3}},
            {'name': 'Standard', 'params': {'radius': 2.0, 'percent': 100, 'threshold': 3}},
            {'name': 'Strong', 'params': {'radius': 3.0, 'percent': 150, 'threshold': 2}},
        ],
    },
    'Sharpen': {
        'description': 'Sharpen image',
        'recommended_images': ['camera', 'astronaut', 'text'],
        'presets': [
            {'name': 'Light', 'params': {'factor': 1.5}},
            {'name': 'Medium', 'params': {'factor': 2.0}},
            {'name': 'Strong', 'params': {'factor': 3.0}},
        ],
    },

    # === Geometric Transforms ===
    'Resize': {
        'description': 'Resize image by scale or size',
        'recommended_images': ['astronaut', 'camera'],
        'presets': [
            {'name': 'Half', 'params': {'scale': 0.5}},
            {'name': 'Quarter', 'params': {'scale': 0.25}},
            {'name': 'Double', 'params': {'scale': 2.0}},
        ],
    },
    'Crop': {
        'description': 'Crop image region',
        'recommended_images': ['astronaut', 'camera'],
        'presets': [
            {'name': 'Top-Left Quarter', 'params': {'x': 0, 'y': 0, 'width': 256, 'height': 256}},
            {'name': 'Center', 'params': {'x': 128, 'y': 128, 'width': 256, 'height': 256}},
        ],
    },
    'CenterCrop': {
        'description': 'Crop from center',
        'recommended_images': ['astronaut', 'camera'],
        'presets': [
            {'name': 'Square 256', 'params': {'width': 256, 'height': 256}},
            {'name': 'Square 128', 'params': {'width': 128, 'height': 128}},
        ],
    },
    'Rotate': {
        'description': 'Rotate image',
        'recommended_images': ['astronaut', 'camera', 'rocket'],
        'presets': [
            {'name': '45 degrees', 'params': {'angle': 45, 'expand': True}},
            {'name': '90 degrees', 'params': {'angle': 90, 'expand': True}},
            {'name': '180 degrees', 'params': {'angle': 180}},
            {'name': '-30 degrees', 'params': {'angle': -30, 'expand': True}},
        ],
    },
    'Flip': {
        'description': 'Flip image horizontally or vertically',
        'recommended_images': ['astronaut', 'chelsea', 'rocket'],
        'presets': [
            {'name': 'Horizontal', 'params': {'horizontal': True}},
            {'name': 'Vertical', 'params': {'vertical': True}},
            {'name': 'Both', 'params': {'horizontal': True, 'vertical': True}},
        ],
    },
    'LensDistortion': {
        'description': 'Apply or correct lens distortion',
        'recommended_images': ['camera', 'rocket', 'hubble_deep_field'],
        'presets': [
            {'name': 'Barrel (subtle)', 'params': {'k1': 0.1}},
            {'name': 'Barrel (strong)', 'params': {'k1': 0.3}},
            {'name': 'Pincushion', 'params': {'k1': -0.2}},
            {'name': 'Fish-eye', 'params': {'k1': 0.5}},
        ],
    },
    'Perspective': {
        'description': 'Apply perspective transformation',
        'recommended_images': ['page', 'camera', 'rocket'],
        'presets': [
            {'name': 'Tilt Left', 'params': {
                'src_points': [(0, 0), (511, 0), (511, 511), (0, 511)],
                'dst_points': [(50, 30), (461, 0), (511, 511), (0, 481)],
            }},
            {'name': 'Tilt Right', 'params': {
                'src_points': [(0, 0), (511, 0), (511, 511), (0, 511)],
                'dst_points': [(0, 0), (461, 30), (511, 481), (50, 511)],
            }},
        ],
    },

    # === Edge Detection ===
    'Canny': {
        'description': 'Canny edge detection',
        'recommended_images': ['camera', 'coins', 'astronaut'],
        'presets': [
            {'name': 'Default', 'params': {'threshold1': 100, 'threshold2': 200}},
            {'name': 'Fine', 'params': {'threshold1': 50, 'threshold2': 100}},
            {'name': 'Coarse', 'params': {'threshold1': 150, 'threshold2': 250}},
        ],
    },
    'Sobel': {
        'description': 'Sobel gradient edge detection',
        'recommended_images': ['camera', 'coins', 'moon'],
        'presets': [
            {'name': 'Horizontal', 'params': {'dx': 1, 'dy': 0}},
            {'name': 'Vertical', 'params': {'dx': 0, 'dy': 1}},
            {'name': 'Combined', 'params': {'dx': 1, 'dy': 1}},
        ],
    },
    'Laplacian': {
        'description': 'Laplacian edge detection',
        'recommended_images': ['camera', 'coins', 'moon'],
        'presets': [
            {'name': 'Default', 'params': {'ksize': 3}},
            {'name': 'Fine', 'params': {'ksize': 1}},
            {'name': 'Smooth', 'params': {'ksize': 5}},
        ],
    },
    'EdgeEnhance': {
        'description': 'Enhance edges using PIL',
        'recommended_images': ['camera', 'astronaut', 'text'],
        'presets': [
            {'name': 'Normal', 'params': {'strength': 'normal'}},
            {'name': 'More', 'params': {'strength': 'more'}},
        ],
    },

    # === Morphological Operations ===
    'Erode': {
        'description': 'Morphological erosion',
        'recommended_images': ['horse', 'coins', 'page'],
        'presets': [
            {'name': 'Light', 'params': {'kernel_size': 3, 'iterations': 1}},
            {'name': 'Medium', 'params': {'kernel_size': 5, 'iterations': 1}},
            {'name': 'Strong', 'params': {'kernel_size': 3, 'iterations': 3}},
        ],
    },
    'Dilate': {
        'description': 'Morphological dilation',
        'recommended_images': ['horse', 'coins', 'page'],
        'presets': [
            {'name': 'Light', 'params': {'kernel_size': 3, 'iterations': 1}},
            {'name': 'Medium', 'params': {'kernel_size': 5, 'iterations': 1}},
            {'name': 'Strong', 'params': {'kernel_size': 3, 'iterations': 3}},
        ],
    },
    'MorphOpen': {
        'description': 'Opening (erosion then dilation)',
        'recommended_images': ['horse', 'coins', 'page'],
        'presets': [
            {'name': 'Small', 'params': {'kernel_size': 3}},
            {'name': 'Medium', 'params': {'kernel_size': 5}},
            {'name': 'Large', 'params': {'kernel_size': 7}},
        ],
    },
    'MorphClose': {
        'description': 'Closing (dilation then erosion)',
        'recommended_images': ['horse', 'coins', 'page'],
        'presets': [
            {'name': 'Small', 'params': {'kernel_size': 3}},
            {'name': 'Medium', 'params': {'kernel_size': 5}},
            {'name': 'Large', 'params': {'kernel_size': 7}},
        ],
    },
    'MorphGradient': {
        'description': 'Morphological gradient (edge outline)',
        'recommended_images': ['horse', 'coins', 'camera'],
        'presets': [
            {'name': 'Thin', 'params': {'kernel_size': 3}},
            {'name': 'Thick', 'params': {'kernel_size': 5}},
        ],
    },
    'TopHat': {
        'description': 'Top-hat transform (bright regions)',
        'recommended_images': ['coins', 'moon', 'camera'],
        'presets': [
            {'name': 'Small', 'params': {'kernel_size': 9}},
            {'name': 'Large', 'params': {'kernel_size': 15}},
        ],
    },
    'BlackHat': {
        'description': 'Black-hat transform (dark regions)',
        'recommended_images': ['coins', 'moon', 'camera'],
        'presets': [
            {'name': 'Small', 'params': {'kernel_size': 9}},
            {'name': 'Large', 'params': {'kernel_size': 15}},
        ],
    },

    # === Detection ===
    'FaceDetector': {
        'description': 'Detect faces using Haar cascades',
        'recommended_images': ['astronaut'],
        'presets': [
            {'name': 'Default', 'params': {'draw': True}},
            {'name': 'Sensitive', 'params': {'draw': True, 'min_neighbors': 3}},
            {'name': 'Strict', 'params': {'draw': True, 'min_neighbors': 8}},
        ],
    },
    'EyeDetector': {
        'description': 'Detect eyes using Haar cascades',
        'recommended_images': ['astronaut'],
        'presets': [
            {'name': 'Default', 'params': {'draw': True}},
            {'name': 'Sensitive', 'params': {'draw': True, 'min_neighbors': 3}},
        ],
    },
    'ContourDetector': {
        'description': 'Detect contours/boundaries',
        'recommended_images': ['coins', 'horse', 'camera'],
        'presets': [
            {'name': 'Default', 'params': {'threshold': 128, 'draw': True}},
            {'name': 'Low Threshold', 'params': {'threshold': 64, 'draw': True}},
            {'name': 'High Threshold', 'params': {'threshold': 192, 'draw': True}},
        ],
    },

    # === Analyzers ===
    'ImageStats': {
        'description': 'Compute image statistics',
        'recommended_images': ['astronaut', 'camera', 'moon'],
        'presets': [
            {'name': 'Default', 'params': {}},
        ],
    },
    'HistogramAnalyzer': {
        'description': 'Compute color histograms',
        'recommended_images': ['astronaut', 'camera', 'chelsea'],
        'presets': [
            {'name': 'Default', 'params': {}},
            {'name': 'Fine Bins', 'params': {'bins': 256}},
            {'name': 'Coarse Bins', 'params': {'bins': 32}},
        ],
    },
    'ColorAnalyzer': {
        'description': 'Analyze dominant colors',
        'recommended_images': ['astronaut', 'chelsea', 'coffee', 'rocket'],
        'presets': [
            {'name': 'Default', 'params': {}},
        ],
    },
    'RegionAnalyzer': {
        'description': 'Analyze image regions',
        'recommended_images': ['astronaut', 'camera'],
        'presets': [
            {'name': 'Default', 'params': {}},
        ],
    },

    # === Channel Operations ===
    'SplitChannels': {
        'description': 'Split image into R, G, B channel images',
        'recommended_images': ['astronaut', 'chelsea', 'coffee', 'rocket'],
        'presets': [
            {'name': 'Default', 'params': {}},
        ],
    },
    'MergeChannels': {
        'description': 'Merge R, G, B channels back into RGB image',
        'recommended_images': ['astronaut', 'chelsea', 'coffee', 'rocket'],
        'presets': [
            {'name': 'Default', 'params': {}},
        ],
    },
    'ExtractChannel': {
        'description': 'Extract single color channel',
        'recommended_images': ['astronaut', 'chelsea', 'coffee', 'rocket'],
        'presets': [
            {'name': 'Red', 'params': {'channel': 'R'}},
            {'name': 'Green', 'params': {'channel': 'G'}},
            {'name': 'Blue', 'params': {'channel': 'B'}},
        ],
    },

    # === Compositing ===
    'Blend': {
        'description': 'Blend two images with various blend modes and optional mask',
        'recommended_images': ['astronaut', 'camera', 'rocket'],
        'presets': [
            {'name': 'Normal', 'params': {'mode': 'NORMAL', 'opacity': 0.5}},
            {'name': 'Multiply', 'params': {'mode': 'MULTIPLY', 'opacity': 1.0}},
            {'name': 'Screen', 'params': {'mode': 'SCREEN', 'opacity': 1.0}},
            {'name': 'Overlay', 'params': {'mode': 'OVERLAY', 'opacity': 1.0}},
            {'name': 'Soft Light', 'params': {'mode': 'SOFT_LIGHT', 'opacity': 1.0}},
        ],
    },
    'SizeMatcher': {
        'description': 'Match dimensions of two images with resize/crop options',
        'recommended_images': ['astronaut', 'camera', 'rocket'],
        'presets': [
            {'name': 'Smaller Wins (Fit)', 'params': {'size_mode': 'SMALLER_WINS', 'aspect_mode': 'FIT'}},
            {'name': 'Bigger Wins (Fill)', 'params': {'size_mode': 'BIGGER_WINS', 'aspect_mode': 'FILL'}},
            {'name': 'First Wins', 'params': {'size_mode': 'FIRST_WINS', 'aspect_mode': 'STRETCH'}},
        ],
    },

    # === Image Generation ===
    'ImageGenerator': {
        'description': 'Generate gradient or solid color images for masks and effects',
        'recommended_images': ['astronaut', 'camera'],
        'presets': [
            {'name': 'Solid Color', 'params': {'gradient_type': 'SOLID'}},
            {'name': 'Horizontal Gradient', 'params': {'gradient_type': 'LINEAR', 'angle': 0.0}},
            {'name': 'Vertical Gradient', 'params': {'gradient_type': 'LINEAR', 'angle': 90.0}},
            {'name': 'Diagonal Gradient', 'params': {'gradient_type': 'LINEAR', 'angle': 45.0}},
            {'name': 'Radial Gradient', 'params': {'gradient_type': 'RADIAL'}},
            {'name': 'Radial Off-center', 'params': {'gradient_type': 'RADIAL', 'center_x': 0.25, 'center_y': 0.25}},
        ],
    },
}


def get_filter_metadata(filter_name: str) -> dict[str, Any]:
    """Get metadata for a filter.

    Returns:
        Dict with 'description', 'recommended_images', 'presets'
    """
    return FILTER_METADATA.get(filter_name, {
        'description': f'{filter_name} filter',
        'recommended_images': ['astronaut'],
        'presets': [],
    })


def get_filter_category(filter_name: str) -> str:
    """Get category for a filter."""
    return FILTER_CATEGORIES.get(filter_name, 'general')


def get_recommended_image(filter_name: str) -> str:
    """Get the first recommended image for a filter."""
    meta = get_filter_metadata(filter_name)
    images = meta.get('recommended_images', ['astronaut'])
    return images[0] if images else 'astronaut'


def get_presets(filter_name: str) -> list[dict[str, Any]]:
    """Get demo presets for a filter."""
    meta = get_filter_metadata(filter_name)
    return meta.get('presets', [])


def get_filters_by_category(category: str) -> list[str]:
    """Get all filter names in a category.

    Args:
        category: Category name or 'all' for all filters

    Returns:
        List of filter names
    """
    if category == 'all':
        return list(FILTER_CATEGORIES.keys())
    return [name for name, cat in FILTER_CATEGORIES.items() if cat == category]
