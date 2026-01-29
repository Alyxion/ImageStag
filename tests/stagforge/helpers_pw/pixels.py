"""PixelHelper - Pixel extraction and verification utilities for Stagforge testing with Playwright."""

import hashlib
from typing import Optional, Dict, List, Tuple, Union
import numpy as np

from .editor import EditorTestHelper


class PixelHelper:
    """
    Helper class for pixel-level inspection and verification.

    Provides methods for:
    - Extracting image data from layers or composite
    - Computing checksums for comparison
    - Getting pixel values at specific coordinates
    - Computing averages, histograms
    - Region-based analysis
    """

    def __init__(self, editor: EditorTestHelper):
        self.editor = editor

    # ===== Image Data Extraction =====

    async def get_layer_image_data(self, layer_id: str = None, as_numpy: bool = True) -> Optional[Union[np.ndarray, Dict]]:
        """
        Get image data from a specific layer.

        Args:
            layer_id: Layer ID, or None for active layer
            as_numpy: If True, return numpy array (H, W, 4). If False, return raw dict.

        Returns:
            RGBA image data as numpy array or dict with data/width/height
        """
        if layer_id:
            result = await self.editor.execute_js(f"""
                (() => {{
                    const vm = window.__stagforge_app__;
                    const app = vm?.getState?.() || vm;
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (!layer) return null;
                    const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);
                    return {{
                        data: Array.from(imageData.data),
                        width: layer.width,
                        height: layer.height,
                        offsetX: layer.offsetX,
                        offsetY: layer.offsetY
                    }};
                }})()
            """)
        else:
            result = await self.editor.execute_js("""
                (() => {
                    const vm = window.__stagforge_app__;
                    const app = vm?.getState?.() || vm;
                    const layer = app?.layerStack?.getActiveLayer();
                    if (!layer) return null;
                    const imageData = layer.ctx.getImageData(0, 0, layer.width, layer.height);
                    return {
                        data: Array.from(imageData.data),
                        width: layer.width,
                        height: layer.height,
                        offsetX: layer.offsetX,
                        offsetY: layer.offsetY
                    };
                })()
            """)

        if not result:
            return None

        if as_numpy:
            data = np.array(result['data'], dtype=np.uint8)
            return data.reshape((result['height'], result['width'], 4))

        return result

    async def get_composite_image_data(self, as_numpy: bool = True) -> Optional[Union[np.ndarray, Dict]]:
        """
        Get the composited image data (all visible layers merged).

        Args:
            as_numpy: If True, return numpy array (H, W, 4). If False, return raw dict.

        Returns:
            RGBA image data as numpy array or dict
        """
        result = await self.editor.execute_js("""
            (() => {
                const vm = window.__stagforge_app__;
                const app = vm?.getState?.() || vm;
                if (!app?.layerStack) return null;

                const width = app.layerStack.width;
                const height = app.layerStack.height;

                // Create composite canvas
                const compositeCanvas = document.createElement('canvas');
                compositeCanvas.width = width;
                compositeCanvas.height = height;
                const ctx = compositeCanvas.getContext('2d');

                // Draw all visible layers (bottom to top)
                for (const layer of app.layerStack.layers) {
                    if (!layer.visible) continue;
                    ctx.globalAlpha = layer.opacity;
                    const ox = layer.offsetX ?? 0;
                    const oy = layer.offsetY ?? 0;
                    ctx.drawImage(layer.canvas, ox, oy);
                }
                ctx.globalAlpha = 1.0;

                const imageData = ctx.getImageData(0, 0, width, height);
                return {
                    data: Array.from(imageData.data),
                    width: width,
                    height: height
                };
            })()
        """)

        if not result:
            return None

        if as_numpy:
            data = np.array(result['data'], dtype=np.uint8)
            return data.reshape((result['height'], result['width'], 4))

        return result

    async def get_region_image_data(self, x: int, y: int, width: int, height: int,
                                    layer_id: str = None, as_numpy: bool = True) -> Optional[Union[np.ndarray, Dict]]:
        """
        Get image data from a specific region.

        Args:
            x, y: Top-left corner in document coordinates
            width, height: Size of region
            layer_id: Layer ID, or None for composite
            as_numpy: Return as numpy array

        Returns:
            RGBA image data for the region
        """
        if layer_id:
            result = await self.editor.execute_js(f"""
                (() => {{
                    const vm = window.__stagforge_app__;
                    const app = vm?.getState?.() || vm;
                    const layer = app?.layerStack?.getLayerById('{layer_id}');
                    if (!layer) return null;

                    // Convert document coords to layer canvas coords
                    const localCoords = layer.docToCanvas({x}, {y});
                    const lx = Math.floor(localCoords.x);
                    const ly = Math.floor(localCoords.y);

                    // Clamp to layer bounds
                    const startX = Math.max(0, lx);
                    const startY = Math.max(0, ly);
                    const endX = Math.min(layer.width, lx + {width});
                    const endY = Math.min(layer.height, ly + {height});

                    if (endX <= startX || endY <= startY) return null;

                    const w = endX - startX;
                    const h = endY - startY;
                    const imageData = layer.ctx.getImageData(startX, startY, w, h);
                    return {{
                        data: Array.from(imageData.data),
                        width: w,
                        height: h
                    }};
                }})()
            """)
        else:
            result = await self.editor.execute_js(f"""
                (() => {{
                    const vm = window.__stagforge_app__;
                    const app = vm?.getState?.() || vm;
                    if (!app?.layerStack) return null;

                    const docWidth = app.layerStack.width;
                    const docHeight = app.layerStack.height;

                    // Clamp to document bounds
                    const startX = Math.max(0, {x});
                    const startY = Math.max(0, {y});
                    const endX = Math.min(docWidth, {x} + {width});
                    const endY = Math.min(docHeight, {y} + {height});

                    if (endX <= startX || endY <= startY) return null;

                    const w = endX - startX;
                    const h = endY - startY;

                    // Create composite canvas
                    const compositeCanvas = document.createElement('canvas');
                    compositeCanvas.width = docWidth;
                    compositeCanvas.height = docHeight;
                    const ctx = compositeCanvas.getContext('2d');

                    for (const layer of app.layerStack.layers) {{
                        if (!layer.visible) continue;
                        ctx.globalAlpha = layer.opacity;
                        const ox = layer.offsetX ?? 0;
                        const oy = layer.offsetY ?? 0;
                        ctx.drawImage(layer.canvas, ox, oy);
                    }}

                    const imageData = ctx.getImageData(startX, startY, w, h);
                    return {{
                        data: Array.from(imageData.data),
                        width: w,
                        height: h
                    }};
                }})()
            """)

        if not result:
            return None

        if as_numpy:
            data = np.array(result['data'], dtype=np.uint8)
            return data.reshape((result['height'], result['width'], 4))

        return result

    # ===== Pixel Inspection =====

    async def get_pixel(self, x: int, y: int, layer_id: str = None) -> Optional[Tuple[int, int, int, int]]:
        """
        Get a single pixel value (R, G, B, A) at document coordinates.

        Args:
            x, y: Document coordinates
            layer_id: Layer ID, or None for composite

        Returns:
            Tuple of (R, G, B, A) values 0-255
        """
        img = await self.get_region_image_data(x, y, 1, 1, layer_id=layer_id, as_numpy=True)
        if img is None or img.size == 0:
            return None
        return tuple(img[0, 0])

    async def get_pixel_color_hex(self, x: int, y: int, layer_id: str = None) -> Optional[str]:
        """Get pixel color as hex string (e.g., '#FF0000')."""
        pixel = await self.get_pixel(x, y, layer_id)
        if pixel is None:
            return None
        return f"#{pixel[0]:02X}{pixel[1]:02X}{pixel[2]:02X}"

    async def pixels_match(self, x: int, y: int, expected_rgba: Tuple[int, int, int, int],
                           tolerance: int = 0, layer_id: str = None) -> bool:
        """
        Check if a pixel matches expected RGBA values within tolerance.

        Args:
            x, y: Document coordinates
            expected_rgba: Expected (R, G, B, A) tuple
            tolerance: Maximum allowed difference per channel
            layer_id: Layer ID, or None for composite

        Returns:
            True if pixel matches within tolerance
        """
        actual = await self.get_pixel(x, y, layer_id)
        if actual is None:
            return False

        for a, e in zip(actual, expected_rgba):
            if abs(a - e) > tolerance:
                return False
        return True

    # ===== Checksums and Hashes =====

    async def compute_checksum(self, layer_id: str = None, region: Tuple[int, int, int, int] = None) -> str:
        """
        Compute MD5 checksum of image data.

        Args:
            layer_id: Layer ID, or None for composite
            region: Optional (x, y, width, height) tuple

        Returns:
            MD5 hex digest string
        """
        if region:
            img = await self.get_region_image_data(*region, layer_id=layer_id, as_numpy=True)
        elif layer_id:
            img = await self.get_layer_image_data(layer_id, as_numpy=True)
        else:
            img = await self.get_composite_image_data(as_numpy=True)

        if img is None:
            return ""

        return hashlib.md5(img.tobytes()).hexdigest()

    async def compute_sha256(self, layer_id: str = None, region: Tuple[int, int, int, int] = None) -> str:
        """Compute SHA256 checksum of image data."""
        if region:
            img = await self.get_region_image_data(*region, layer_id=layer_id, as_numpy=True)
        elif layer_id:
            img = await self.get_layer_image_data(layer_id, as_numpy=True)
        else:
            img = await self.get_composite_image_data(as_numpy=True)

        if img is None:
            return ""

        return hashlib.sha256(img.tobytes()).hexdigest()

    # ===== Statistics =====

    async def compute_average_color(self, layer_id: str = None,
                                    region: Tuple[int, int, int, int] = None) -> Tuple[float, float, float, float]:
        """
        Compute average RGBA values.

        Args:
            layer_id: Layer ID, or None for composite
            region: Optional (x, y, width, height) tuple

        Returns:
            Tuple of (R, G, B, A) averages as floats
        """
        if region:
            img = await self.get_region_image_data(*region, layer_id=layer_id, as_numpy=True)
        elif layer_id:
            img = await self.get_layer_image_data(layer_id, as_numpy=True)
        else:
            img = await self.get_composite_image_data(as_numpy=True)

        if img is None:
            return (0.0, 0.0, 0.0, 0.0)

        return tuple(img.mean(axis=(0, 1)))

    async def get_average_brightness(self, layer_id: str = None,
                                     region: Tuple[int, int, int, int] = None) -> float:
        """
        Compute average luminance/brightness of image.

        Uses standard luminance formula: 0.299*R + 0.587*G + 0.114*B
        """
        if region:
            img = await self.get_region_image_data(*region, layer_id=layer_id, as_numpy=True)
        elif layer_id:
            img = await self.get_layer_image_data(layer_id, as_numpy=True)
        else:
            img = await self.get_composite_image_data(as_numpy=True)

        if img is None:
            return 0.0

        luminance = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
        return float(np.mean(luminance))

    async def count_pixels_with_color(self, color: Tuple[int, int, int, int],
                                      tolerance: int = 0, layer_id: str = None,
                                      region: Tuple[int, int, int, int] = None) -> int:
        """
        Count pixels matching a specific color.

        Args:
            color: RGBA tuple to match
            tolerance: Maximum difference per channel
            layer_id: Layer ID, or None for composite
            region: Optional region to search

        Returns:
            Number of matching pixels
        """
        if region:
            img = await self.get_region_image_data(*region, layer_id=layer_id, as_numpy=True)
        elif layer_id:
            img = await self.get_layer_image_data(layer_id, as_numpy=True)
        else:
            img = await self.get_composite_image_data(as_numpy=True)

        if img is None:
            return 0

        color_arr = np.array(color, dtype=np.uint8)
        diff = np.abs(img.astype(np.int16) - color_arr.astype(np.int16))
        matches = np.all(diff <= tolerance, axis=2)
        return int(np.sum(matches))

    async def count_non_transparent_pixels(self, layer_id: str = None,
                                           region: Tuple[int, int, int, int] = None,
                                           alpha_threshold: int = 0) -> int:
        """
        Count pixels with alpha > threshold.

        Args:
            layer_id: Layer ID, or None for composite
            region: Optional region
            alpha_threshold: Minimum alpha to count as non-transparent

        Returns:
            Number of non-transparent pixels
        """
        if region:
            img = await self.get_region_image_data(*region, layer_id=layer_id, as_numpy=True)
        elif layer_id:
            img = await self.get_layer_image_data(layer_id, as_numpy=True)
        else:
            img = await self.get_composite_image_data(as_numpy=True)

        if img is None:
            return 0

        return int(np.sum(img[:, :, 3] > alpha_threshold))

    async def count_transparent_pixels(self, layer_id: str = None,
                                       region: Tuple[int, int, int, int] = None,
                                       alpha_threshold: int = 0) -> int:
        """
        Count pixels with alpha <= threshold (fully or mostly transparent).
        """
        if region:
            img = await self.get_region_image_data(*region, layer_id=layer_id, as_numpy=True)
        elif layer_id:
            img = await self.get_layer_image_data(layer_id, as_numpy=True)
        else:
            img = await self.get_composite_image_data(as_numpy=True)

        if img is None:
            return 0

        return int(np.sum(img[:, :, 3] <= alpha_threshold))

    async def get_bounding_box_of_content(self, layer_id: str = None,
                                          alpha_threshold: int = 0) -> Optional[Tuple[int, int, int, int]]:
        """
        Find bounding box of non-transparent content.

        Args:
            layer_id: Layer ID, or None for composite
            alpha_threshold: Minimum alpha to consider as content

        Returns:
            (x, y, width, height) or None if no content
        """
        if layer_id:
            img = await self.get_layer_image_data(layer_id, as_numpy=True)
        else:
            img = await self.get_composite_image_data(as_numpy=True)

        if img is None:
            return None

        mask = img[:, :, 3] > alpha_threshold
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            return None

        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]

        return (int(x_min), int(y_min), int(x_max - x_min + 1), int(y_max - y_min + 1))

    # ===== Comparison =====

    def images_identical(self, img1: np.ndarray, img2: np.ndarray) -> bool:
        """Check if two image arrays are identical."""
        if img1.shape != img2.shape:
            return False
        return np.array_equal(img1, img2)

    def images_similar(self, img1: np.ndarray, img2: np.ndarray,
                       max_diff_pixels: int = 0, tolerance: int = 0) -> bool:
        """
        Check if two images are similar within tolerance.

        Args:
            img1, img2: Image arrays to compare
            max_diff_pixels: Maximum number of pixels that can differ
            tolerance: Maximum per-channel difference to consider same

        Returns:
            True if images are similar enough
        """
        if img1.shape != img2.shape:
            return False

        diff = np.abs(img1.astype(np.int16) - img2.astype(np.int16))
        pixel_differs = np.any(diff > tolerance, axis=2)
        num_diff = np.sum(pixel_differs)

        return num_diff <= max_diff_pixels

    def compute_difference_map(self, img1: np.ndarray, img2: np.ndarray) -> np.ndarray:
        """
        Compute per-pixel difference between two images.

        Returns:
            Single-channel array with max absolute difference per pixel
        """
        if img1.shape != img2.shape:
            raise ValueError("Images must have same shape")

        diff = np.abs(img1.astype(np.int16) - img2.astype(np.int16))
        return np.max(diff, axis=2).astype(np.uint8)
