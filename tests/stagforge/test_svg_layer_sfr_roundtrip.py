"""Browser integration tests for SVG layer SFR serialization round-trip.

These tests verify that SVG layers survive the full save/load cycle:
1. Create document with pixel and SVG layers
2. Save as SFR ZIP format
3. Load from SFR
4. Verify SVG layer is visible with correct content

Run with: poetry run pytest tests/stagforge/test_svg_layer_sfr_roundtrip.py -v

NOTE: Requires NiceGUI server running at http://localhost:8080
"""

import pytest
from playwright.sync_api import sync_playwright


class DevScreen:
    """Screen fixture that connects to the dev server at port 8080."""

    def __init__(self, page, base_url: str = "http://127.0.0.1:8080"):
        self.page = page
        self.base_url = base_url

    def open(self, path: str = "/"):
        """Navigate to a path."""
        url = f"{self.base_url}{path}" if path.startswith("/") else path
        self.page.goto(url, timeout=30000)

    def wait_for_editor(self, timeout: float = 30.0):
        """Wait for the Stagforge editor to fully load."""
        self.page.wait_for_selector('.editor-root', timeout=timeout * 1000)
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.layerStack?.layers?.length > 0",
            timeout=timeout * 1000
        )
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.documentManager?.getActiveDocument?.() != null",
            timeout=timeout * 1000
        )
        self.page.wait_for_function(
            "() => window.__stagforge_app__?.fileManager != null",
            timeout=timeout * 1000
        )

    def wait(self, seconds: float):
        """Wait for a number of seconds."""
        self.page.wait_for_timeout(seconds * 1000)


@pytest.fixture(scope="module")
def dev_browser():
    """Launch Playwright browser for dev server tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def screen(dev_browser):
    """Create a screen instance connected to dev server at port 8080."""
    page = dev_browser.new_page()
    s = DevScreen(page)
    yield s
    page.close()


class TestSVGLayerSFRRoundtrip:
    """Test SVG layer survives SFR save/load cycle."""

    def test_svg_layer_saved_as_separate_file(self, screen):
        """SVG layer content should be saved as separate .svg file in ZIP."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                // Import SVGLayer
                const { SVGLayer } = await import('/static/js/core/SVGLayer.js');

                const doc = app.documentManager.getActiveDocument();

                // Create simple SVG content
                const svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <rect x="10" y="10" width="80" height="80" fill="#FF0000"/>
</svg>`;

                // Create SVG layer
                const svgLayer = new SVGLayer({
                    name: 'Test SVG',
                    width: doc.width,
                    height: doc.height,
                    svgContent: svgContent
                });
                await svgLayer.render();

                app.layerStack.addLayer(svgLayer);

                // Serialize to ZIP
                const zipBlob = await app.fileManager.serializeDocumentZip();

                // Read the ZIP to verify contents
                const JSZip = window.JSZip;
                if (!JSZip) {
                    return { error: 'JSZip not loaded' };
                }

                const zip = await JSZip.loadAsync(zipBlob);

                // Check layers folder for SVG file
                const layerFiles = [];
                const layersFolder = zip.folder('layers');
                if (layersFolder) {
                    layersFolder.forEach((path, file) => {
                        layerFiles.push(path);
                    });
                }

                // Check for .svg file
                const svgFiles = layerFiles.filter(f => f.endsWith('.svg'));

                // Read content.json
                const contentFile = zip.file('content.json');
                const contentText = await contentFile.async('string');
                const content = JSON.parse(contentText);

                // Find SVG layer in JSON
                const svgLayerJson = content.document.layers.find(l => l.type === 'svg');

                // If SVG file exists, read its content
                let svgFileContent = '';
                if (svgFiles.length > 0) {
                    const svgFile = layersFolder.file(svgFiles[0].replace('layers/', ''));
                    if (svgFile) {
                        svgFileContent = await svgFile.async('string');
                    }
                }

                return {
                    success: true,
                    totalLayerFiles: layerFiles.length,
                    layerFiles: layerFiles,
                    svgFilesCount: svgFiles.length,
                    svgFiles: svgFiles,
                    svgLayerFound: !!svgLayerJson,
                    svgLayerImageFile: svgLayerJson?.imageFile,
                    svgLayerImageFormat: svgLayerJson?.imageFormat,
                    svgLayerHasInlineSvgContent: !!svgLayerJson?.svgContent,
                    svgFileContentLength: svgFileContent.length,
                    svgFileHasRect: svgFileContent.includes('<rect')
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True

        # SVG should be saved as separate file
        assert result['svgFilesCount'] == 1, \
            f"Should have 1 SVG file in layers/, got {result['svgFilesCount']}. Files: {result['layerFiles']}"
        assert result['svgLayerFound'] is True, "SVG layer should be in content.json"
        assert result['svgLayerImageFile'] is not None, "SVG layer should have imageFile reference"
        assert result['svgLayerImageFile'].endswith('.svg'), \
            f"imageFile should end with .svg, got {result['svgLayerImageFile']}"
        assert result['svgLayerImageFormat'] == 'svg', \
            f"imageFormat should be 'svg', got {result['svgLayerImageFormat']}"
        assert result['svgLayerHasInlineSvgContent'] is False, \
            "SVG content should NOT be inline in JSON (it's in the file)"
        assert result['svgFileContentLength'] > 0, "SVG file should have content"
        assert result['svgFileHasRect'] is True, "SVG file should contain the rect element"

    def test_svg_layer_loaded_from_sfr(self, screen):
        """SVG layer should load correctly from SFR ZIP."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                // Import SVGLayer
                const { SVGLayer } = await import('/static/js/core/SVGLayer.js');
                const { Document } = await import('/static/js/core/Document.js');

                const doc = app.documentManager.getActiveDocument();

                // Create SVG with a blue circle
                const svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="#0000FF"/>
</svg>`;

                // Create SVG layer
                const svgLayer = new SVGLayer({
                    name: 'Blue Circle SVG',
                    width: doc.width,
                    height: doc.height,
                    svgContent: svgContent
                });
                await svgLayer.render();

                // Count blue pixels before save
                const beforeCanvas = svgLayer.canvas;
                const beforeCtx = beforeCanvas.getContext('2d');
                const beforeData = beforeCtx.getImageData(0, 0, beforeCanvas.width, beforeCanvas.height);
                let bluePixelsBefore = 0;
                for (let i = 0; i < beforeData.data.length; i += 4) {
                    const r = beforeData.data[i];
                    const g = beforeData.data[i + 1];
                    const b = beforeData.data[i + 2];
                    const a = beforeData.data[i + 3];
                    if (b > 200 && r < 50 && g < 50 && a > 200) {
                        bluePixelsBefore++;
                    }
                }

                app.layerStack.addLayer(svgLayer);

                // Serialize to ZIP
                const zipBlob = await app.fileManager.serializeDocumentZip();

                // Parse the ZIP
                const parseResult = await app.fileManager.parseFile(
                    new File([zipBlob], 'test.sfr', { type: 'application/zip' })
                );

                const { data, layerImages } = parseResult;

                // Debug: Check what's in layerImages
                const layerImageKeys = layerImages ? Array.from(layerImages.keys()) : [];

                // Process layer images using the shared function
                const { processLayerImages } = await import('/static/js/core/FileManager.js');
                await processLayerImages(data.document, layerImages);

                // Find the SVG layer data
                const svgLayerData = data.document.layers.find(l => l.type === 'svg');

                // Deserialize
                const restoredDoc = await Document.deserialize(data.document, app.eventBus);

                // Find restored SVG layer
                const restoredSvgLayer = restoredDoc.layerStack.layers.find(l => l.type === 'svg');

                // Count blue pixels after load
                let bluePixelsAfter = 0;
                let hasCanvas = false;
                let canvasWidth = 0;
                let canvasHeight = 0;
                let svgContentAfter = '';

                if (restoredSvgLayer) {
                    hasCanvas = !!restoredSvgLayer.canvas;
                    svgContentAfter = restoredSvgLayer.svgContent || '';

                    if (hasCanvas) {
                        canvasWidth = restoredSvgLayer.canvas.width;
                        canvasHeight = restoredSvgLayer.canvas.height;

                        const afterCtx = restoredSvgLayer.canvas.getContext('2d');
                        const afterData = afterCtx.getImageData(0, 0, canvasWidth, canvasHeight);
                        for (let i = 0; i < afterData.data.length; i += 4) {
                            const r = afterData.data[i];
                            const g = afterData.data[i + 1];
                            const b = afterData.data[i + 2];
                            const a = afterData.data[i + 3];
                            if (b > 200 && r < 50 && g < 50 && a > 200) {
                                bluePixelsAfter++;
                            }
                        }
                    }
                }

                return {
                    success: true,
                    layerImageKeys,
                    svgLayerDataFound: !!svgLayerData,
                    svgLayerDataHasSvgContent: !!svgLayerData?.svgContent,
                    svgLayerDataSvgContentLength: svgLayerData?.svgContent?.length || 0,
                    restoredSvgLayerFound: !!restoredSvgLayer,
                    hasCanvas,
                    canvasWidth,
                    canvasHeight,
                    svgContentAfterLength: svgContentAfter.length,
                    svgContentHasCircle: svgContentAfter.includes('<circle'),
                    bluePixelsBefore,
                    bluePixelsAfter,
                    pixelMatch: bluePixelsBefore === bluePixelsAfter,
                    hasVisiblePixels: bluePixelsAfter > 100
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True

        # Debug output
        print(f"Layer image keys: {result['layerImageKeys']}")
        print(f"SVG layer data found: {result['svgLayerDataFound']}")
        print(f"SVG layer data has svgContent: {result['svgLayerDataHasSvgContent']}")
        print(f"SVG content length: {result['svgLayerDataSvgContentLength']}")
        print(f"Restored SVG layer found: {result['restoredSvgLayerFound']}")
        print(f"Has canvas: {result['hasCanvas']}")
        print(f"Canvas size: {result['canvasWidth']}x{result['canvasHeight']}")
        print(f"Blue pixels before: {result['bluePixelsBefore']}, after: {result['bluePixelsAfter']}")

        # Verify SVG content was loaded
        assert result['svgLayerDataFound'] is True, "SVG layer should be in parsed data"
        assert result['svgLayerDataHasSvgContent'] is True, \
            "SVG layer data should have svgContent after processing"
        assert result['svgLayerDataSvgContentLength'] > 0, "svgContent should not be empty"

        # Verify SVG layer was restored
        assert result['restoredSvgLayerFound'] is True, "Restored SVG layer should exist"
        assert result['hasCanvas'] is True, "SVG layer should have canvas"
        assert result['svgContentAfterLength'] > 0, "SVG layer should have svgContent after restore"
        assert result['svgContentHasCircle'] is True, "SVG content should contain the circle"

        # Verify pixels are rendered
        assert result['hasVisiblePixels'] is True, \
            f"SVG layer should have visible blue pixels, got {result['bluePixelsAfter']}"

    def test_svg_layer_with_deer_roundtrip(self, screen):
        """Test loading deer SVG from library, saving, and loading."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                // Fetch deer SVG from API
                let deerSvgContent;
                try {
                    const response = await fetch('/api/svg-samples/openclipart/buck-deer-silhouette.svg');
                    if (!response.ok) {
                        return { error: 'Failed to fetch deer SVG: ' + response.status };
                    }
                    deerSvgContent = await response.text();
                } catch (e) {
                    return { error: 'Failed to fetch deer SVG: ' + e.message };
                }

                if (!deerSvgContent || !deerSvgContent.includes('<svg')) {
                    return { error: 'Invalid deer SVG content' };
                }

                // Import SVGLayer
                const { SVGLayer } = await import('/static/js/core/SVGLayer.js');
                const { Document } = await import('/static/js/core/Document.js');

                const doc = app.documentManager.getActiveDocument();

                // Draw something on base layer
                const baseLayer = app.layerStack.layers[0];
                baseLayer.ctx.fillStyle = '#CCCCCC';
                baseLayer.ctx.fillRect(0, 0, doc.width, doc.height);

                // Create deer SVG layer
                const deerLayer = new SVGLayer({
                    name: 'Deer Silhouette',
                    width: doc.width,
                    height: doc.height,
                    svgContent: deerSvgContent
                });
                await deerLayer.render();

                // Count non-transparent pixels on deer layer before save
                const beforeCtx = deerLayer.canvas.getContext('2d');
                const beforeData = beforeCtx.getImageData(0, 0, deerLayer.width, deerLayer.height);
                let nonTransparentBefore = 0;
                for (let i = 3; i < beforeData.data.length; i += 4) {
                    if (beforeData.data[i] > 0) {
                        nonTransparentBefore++;
                    }
                }

                // Add deer layer on top
                app.layerStack.addLayer(deerLayer);

                // Record state before save
                const layerCountBefore = app.layerStack.layers.length;

                // Serialize to ZIP
                const zipBlob = await app.fileManager.serializeDocumentZip();

                // Check ZIP contents
                const JSZip = window.JSZip;
                const zip = await JSZip.loadAsync(zipBlob);

                const layerFiles = [];
                const layersFolder = zip.folder('layers');
                if (layersFolder) {
                    layersFolder.forEach((path, file) => {
                        layerFiles.push(path);
                    });
                }

                const svgFilesInZip = layerFiles.filter(f => f.endsWith('.svg'));

                // Parse and load
                const parseResult = await app.fileManager.parseFile(
                    new File([zipBlob], 'deer_test.sfr', { type: 'application/zip' })
                );

                const { data, layerImages } = parseResult;

                // Debug: log what we got
                const layerImageKeys = Array.from(layerImages.keys());

                // Process layer images using the shared function
                const { processLayerImages } = await import('/static/js/core/FileManager.js');
                await processLayerImages(data.document, layerImages);

                // Find SVG layer data
                const deerLayerData = data.document.layers.find(l => l.type === 'svg');

                // Deserialize
                const restoredDoc = await Document.deserialize(data.document, app.eventBus);

                // Find restored deer layer
                const restoredDeer = restoredDoc.layerStack.layers.find(l => l.type === 'svg');

                // Count non-transparent pixels after
                let nonTransparentAfter = 0;
                let hasCanvas = false;

                if (restoredDeer) {
                    hasCanvas = !!restoredDeer.canvas;
                    if (hasCanvas) {
                        const afterCtx = restoredDeer.canvas.getContext('2d');
                        const afterData = afterCtx.getImageData(0, 0, restoredDeer.width, restoredDeer.height);
                        for (let i = 3; i < afterData.data.length; i += 4) {
                            if (afterData.data[i] > 0) {
                                nonTransparentAfter++;
                            }
                        }
                    }
                }

                return {
                    success: true,
                    deerSvgContentLength: deerSvgContent.length,
                    layerCountBefore,
                    svgFilesInZip,
                    layerImageKeys,
                    deerLayerDataFound: !!deerLayerData,
                    deerLayerDataHasSvgContent: !!deerLayerData?.svgContent,
                    deerLayerDataSvgContentLength: deerLayerData?.svgContent?.length || 0,
                    restoredDeerFound: !!restoredDeer,
                    restoredDeerName: restoredDeer?.name,
                    hasCanvas,
                    nonTransparentBefore,
                    nonTransparentAfter,
                    deerIsVisible: nonTransparentAfter > 100,
                    pixelCountMatch: nonTransparentBefore === nonTransparentAfter
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True

        # Debug output
        print(f"Deer SVG content length: {result['deerSvgContentLength']}")
        print(f"SVG files in ZIP: {result['svgFilesInZip']}")
        print(f"Layer image keys: {result['layerImageKeys']}")
        print(f"Deer layer data found: {result['deerLayerDataFound']}")
        print(f"Deer layer has svgContent: {result['deerLayerDataHasSvgContent']}")
        print(f"Restored deer found: {result['restoredDeerFound']}")
        print(f"Has canvas: {result['hasCanvas']}")
        print(f"Non-transparent pixels before: {result['nonTransparentBefore']}, after: {result['nonTransparentAfter']}")

        # Verify SVG file is in ZIP
        assert len(result['svgFilesInZip']) == 1, \
            f"Should have 1 SVG file in ZIP, got {len(result['svgFilesInZip'])}"

        # Verify deer layer was restored
        assert result['deerLayerDataFound'] is True, "Deer layer should be in parsed data"
        assert result['deerLayerDataHasSvgContent'] is True, \
            "Deer layer should have svgContent after parsing"
        assert result['restoredDeerFound'] is True, "Restored deer layer should exist"
        assert result['restoredDeerName'] == 'Deer Silhouette', \
            f"Layer name should be preserved, got '{result['restoredDeerName']}'"
        assert result['hasCanvas'] is True, "Deer layer should have canvas"

        # CRITICAL: Deer should be visible
        assert result['deerIsVisible'] is True, \
            f"Deer should be visible (have >100 non-transparent pixels), got {result['nonTransparentAfter']}"
        assert result['nonTransparentAfter'] > 0, \
            "Deer layer should have rendered pixels after loading"

    def test_document_with_pixel_and_svg_layers_full_roundtrip(self, screen):
        """Complete test: pixel layer + SVG deer on top, save, load, verify both visible."""
        screen.open('/')
        screen.wait_for_editor()

        result = screen.page.evaluate("""
            async () => {
                const app = window.__stagforge_app__;

                if (!app.fileManager) {
                    return { error: 'FileManager not available' };
                }

                // Fetch deer SVG
                let deerSvgContent;
                try {
                    const response = await fetch('/api/svg-samples/openclipart/buck-deer-silhouette.svg');
                    if (!response.ok) {
                        return { error: 'Failed to fetch deer SVG: ' + response.status };
                    }
                    deerSvgContent = await response.text();
                } catch (e) {
                    return { error: 'Failed to fetch deer SVG: ' + e.message };
                }

                const { SVGLayer } = await import('/static/js/core/SVGLayer.js');
                const { Document } = await import('/static/js/core/Document.js');

                const doc = app.documentManager.getActiveDocument();
                doc.name = 'DeerDocument';

                // 1. Draw red background on base pixel layer
                const pixelLayer = app.layerStack.layers[0];
                pixelLayer.name = 'Red Background';
                pixelLayer.ctx.fillStyle = '#FF0000';
                pixelLayer.ctx.fillRect(0, 0, doc.width, doc.height);

                // Count red pixels before
                const redDataBefore = pixelLayer.ctx.getImageData(0, 0, doc.width, doc.height);
                let redPixelsBefore = 0;
                for (let i = 0; i < redDataBefore.data.length; i += 4) {
                    if (redDataBefore.data[i] > 200 && redDataBefore.data[i+1] < 50 && redDataBefore.data[i+2] < 50) {
                        redPixelsBefore++;
                    }
                }

                // 2. Create deer SVG layer on top
                const deerLayer = new SVGLayer({
                    name: 'Deer',
                    width: doc.width,
                    height: doc.height,
                    svgContent: deerSvgContent
                });
                await deerLayer.render();

                // Count deer pixels before
                const deerDataBefore = deerLayer.canvas.getContext('2d').getImageData(0, 0, deerLayer.width, deerLayer.height);
                let deerPixelsBefore = 0;
                for (let i = 3; i < deerDataBefore.data.length; i += 4) {
                    if (deerDataBefore.data[i] > 0) {
                        deerPixelsBefore++;
                    }
                }

                app.layerStack.addLayer(deerLayer);

                // 3. Save as SFR
                const zipBlob = await app.fileManager.serializeDocumentZip();

                // 4. Check ZIP structure
                const JSZip = window.JSZip;
                const zip = await JSZip.loadAsync(zipBlob);

                const layerFiles = [];
                const layersFolder = zip.folder('layers');
                if (layersFolder) {
                    layersFolder.forEach((path, file) => {
                        layerFiles.push(path);
                    });
                }

                const webpFiles = layerFiles.filter(f => f.endsWith('.webp'));
                const svgFiles = layerFiles.filter(f => f.endsWith('.svg'));

                // 5. Load from SFR
                const parseResult = await app.fileManager.parseFile(
                    new File([zipBlob], 'deer_doc.sfr', { type: 'application/zip' })
                );

                const { data, layerImages } = parseResult;
                const layerImageKeys = Array.from(layerImages.keys());

                // Process layer images using the shared function
                const { processLayerImages } = await import('/static/js/core/FileManager.js');
                await processLayerImages(data.document, layerImages);

                // 6. Deserialize
                const restoredDoc = await Document.deserialize(data.document, app.eventBus);

                // 7. Find restored layers
                const restoredPixelLayer = restoredDoc.layerStack.layers.find(
                    l => l.name === 'Red Background' || (l.type !== 'svg' && l.type !== 'vector' && l.type !== 'text')
                );
                const restoredDeerLayer = restoredDoc.layerStack.layers.find(l => l.type === 'svg');

                // 8. Verify pixel layer content
                let redPixelsAfter = 0;
                if (restoredPixelLayer && restoredPixelLayer.ctx) {
                    const redDataAfter = restoredPixelLayer.ctx.getImageData(0, 0, restoredPixelLayer.width, restoredPixelLayer.height);
                    for (let i = 0; i < redDataAfter.data.length; i += 4) {
                        if (redDataAfter.data[i] > 200 && redDataAfter.data[i+1] < 50 && redDataAfter.data[i+2] < 50) {
                            redPixelsAfter++;
                        }
                    }
                }

                // 9. Verify deer layer content
                let deerPixelsAfter = 0;
                let deerHasCanvas = false;
                let deerSvgContentAfter = '';
                if (restoredDeerLayer) {
                    deerHasCanvas = !!restoredDeerLayer.canvas;
                    deerSvgContentAfter = restoredDeerLayer.svgContent || '';

                    if (deerHasCanvas) {
                        const deerDataAfter = restoredDeerLayer.canvas.getContext('2d').getImageData(
                            0, 0, restoredDeerLayer.width, restoredDeerLayer.height
                        );
                        for (let i = 3; i < deerDataAfter.data.length; i += 4) {
                            if (deerDataAfter.data[i] > 0) {
                                deerPixelsAfter++;
                            }
                        }
                    }
                }

                return {
                    success: true,
                    // ZIP structure
                    webpFilesCount: webpFiles.length,
                    svgFilesCount: svgFiles.length,
                    layerImageKeys,
                    // Pixel layer results
                    pixelLayerFound: !!restoredPixelLayer,
                    pixelLayerHasCtx: !!restoredPixelLayer?.ctx,
                    redPixelsBefore,
                    redPixelsAfter,
                    redPixelsMatch: redPixelsBefore === redPixelsAfter,
                    // Deer layer results
                    deerLayerFound: !!restoredDeerLayer,
                    deerHasCanvas,
                    deerSvgContentLength: deerSvgContentAfter.length,
                    deerPixelsBefore,
                    deerPixelsAfter,
                    deerIsVisible: deerPixelsAfter > 100,
                    // Overall
                    docName: restoredDoc.name
                };
            }
        """)

        assert 'error' not in result, f"Test failed: {result.get('error')}"
        assert result['success'] is True

        # Debug output
        print(f"WebP files in ZIP: {result['webpFilesCount']}")
        print(f"SVG files in ZIP: {result['svgFilesCount']}")
        print(f"Layer image keys: {result['layerImageKeys']}")
        print(f"Pixel layer found: {result['pixelLayerFound']}, has ctx: {result['pixelLayerHasCtx']}")
        print(f"Red pixels before: {result['redPixelsBefore']}, after: {result['redPixelsAfter']}")
        print(f"Deer layer found: {result['deerLayerFound']}, has canvas: {result['deerHasCanvas']}")
        print(f"Deer SVG content length: {result['deerSvgContentLength']}")
        print(f"Deer pixels before: {result['deerPixelsBefore']}, after: {result['deerPixelsAfter']}")

        # ZIP should have both WebP (pixel) and SVG files
        assert result['webpFilesCount'] == 1, f"Should have 1 WebP file, got {result['webpFilesCount']}"
        assert result['svgFilesCount'] == 1, f"Should have 1 SVG file, got {result['svgFilesCount']}"

        # Pixel layer should be restored correctly
        assert result['pixelLayerFound'] is True, "Pixel layer should be restored"
        assert result['pixelLayerHasCtx'] is True, "Pixel layer should have ctx"
        assert result['redPixelsAfter'] > 0, "Pixel layer should have red pixels"
        assert result['redPixelsMatch'] is True, \
            f"Red pixel count should match: {result['redPixelsBefore']} vs {result['redPixelsAfter']}"

        # CRITICAL: Deer SVG layer should be visible
        assert result['deerLayerFound'] is True, "Deer layer should be restored"
        assert result['deerHasCanvas'] is True, "Deer layer should have canvas"
        assert result['deerSvgContentLength'] > 0, "Deer should have SVG content"
        assert result['deerIsVisible'] is True, \
            f"DEER MUST BE VISIBLE! Got {result['deerPixelsAfter']} pixels (need >100)"

        # Document name should be preserved
        assert result['docName'] == 'DeerDocument', f"Doc name should be preserved, got '{result['docName']}'"
