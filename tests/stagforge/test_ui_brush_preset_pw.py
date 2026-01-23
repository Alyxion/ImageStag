"""UI tests for brush preset menu functionality - Playwright version.

These tests use Playwright to interact with the actual browser UI and verify
the brush preset dropdown menu works correctly.
"""

import pytest
from .helpers_pw import TestHelpers


pytestmark = pytest.mark.asyncio


class TestBrushPresetMenu:
    """Tests for the brush preset dropdown menu in the toolbar."""

    async def test_brush_tool_is_default(self, helpers: TestHelpers):
        """Verify brush tool is selected by default on load."""
        await helpers.new_document(200, 200)

        # Check the current tool via Vue data
        current_tool = await helpers.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root?.__vue_app__?._instance?.proxy;
                return vm?.currentToolId;
            })()
        """)
        assert current_tool == "brush", f"Expected brush tool, got {current_tool}"

    async def test_brush_preset_thumbnails_generated_on_load(self, helpers: TestHelpers):
        """Verify brush preset thumbnails are generated on initial load."""
        await helpers.new_document(200, 200)

        # Check if thumbnails were generated
        result = await helpers.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root?.__vue_app__?._instance?.proxy;
                return {
                    generated: vm?.brushPresetThumbnailsGenerated || false,
                    thumbnailCount: vm?.brushPresetThumbnails ? Object.keys(vm.brushPresetThumbnails).length : 0
                };
            })()
        """)

        assert result['generated'] is True, "Brush preset thumbnails should be generated on load"
        assert result['thumbnailCount'] > 0, "brushPresetThumbnails should have entries"

    async def test_brush_preset_thumbnail_displayed_in_toolbar(self, helpers: TestHelpers):
        """Verify the current brush preset thumbnail is displayed in toolbar."""
        await helpers.new_document(200, 200)

        # Wait for and check the thumbnail
        try:
            await helpers.editor.page.wait_for_selector(".brush-preset-thumb", timeout=5000)
            thumb = await helpers.editor.page.locator(".brush-preset-thumb").is_visible()
            assert thumb, "Brush preset thumbnail should be visible in toolbar"
        except Exception as e:
            # Get debug info
            debug = await helpers.editor.execute_js("""
                (() => {
                    const root = document.querySelector('.editor-root');
                    const vm = root?.__vue_app__?._instance?.proxy;
                    return {
                        currentToolId: vm?.currentToolId,
                        currentBrushPreset: vm?.currentBrushPreset,
                        thumbnailKeys: vm?.brushPresetThumbnails ? Object.keys(vm.brushPresetThumbnails) : []
                    };
                })()
            """)
            raise AssertionError(f"Brush preset thumbnail not visible in toolbar. Debug: {debug}")

    async def test_brush_preset_dropdown_exists(self, helpers: TestHelpers):
        """Verify the brush preset dropdown element exists."""
        await helpers.new_document(200, 200)

        dropdown = await helpers.editor.page.locator(".brush-preset-dropdown")
        assert await dropdown.count() > 0, "Brush preset dropdown should exist"
        assert await dropdown.first.is_visible(), "Brush preset dropdown should be visible"

    async def test_brush_preset_menu_opens_on_click(self, helpers: TestHelpers):
        """Test that clicking the preset dropdown opens the menu."""
        await helpers.new_document(200, 200)

        # First verify menu is not visible
        menu_visible_before = await helpers.editor.page.locator(".brush-preset-menu").is_visible()
        assert not menu_visible_before, "Menu should be hidden initially"

        # Click the dropdown to open menu
        await helpers.editor.page.click(".brush-preset-dropdown")

        # Wait a bit for Vue reactivity
        await helpers.editor.page.wait_for_timeout(300)

        # Verify menu is now visible
        try:
            await helpers.editor.page.wait_for_selector(".brush-preset-menu", state="visible", timeout=3000)
            menu_visible_after = True
        except:
            menu_visible_after = False

        # If menu didn't open, gather diagnostic info
        if not menu_visible_after:
            debug = await helpers.editor.execute_js("""
                (() => {
                    const root = document.querySelector('.editor-root');
                    const vm = root?.__vue_app__?._instance?.proxy;
                    const menu = document.querySelector('.brush-preset-menu');
                    return {
                        showBrushPresetMenu: vm?.showBrushPresetMenu,
                        menuExists: !!menu,
                        menuStyle: menu ? window.getComputedStyle(menu).display : null
                    };
                })()
            """)
            raise AssertionError(f"Brush preset menu should be visible after clicking dropdown. Debug: {debug}")

    async def test_brush_preset_menu_contains_options(self, helpers: TestHelpers):
        """Test that the opened menu contains preset options."""
        await helpers.new_document(200, 200)

        # Open the menu first
        await helpers.editor.page.click(".brush-preset-dropdown")
        await helpers.editor.page.wait_for_timeout(300)

        # Wait for menu to be visible
        await helpers.editor.page.wait_for_selector(".brush-preset-menu", state="visible", timeout=3000)

        # Find all preset options
        options = await helpers.editor.page.locator(".brush-preset-option").count()
        assert options > 0, "Menu should contain preset options"

        # Verify we have the expected number of presets (10 in BrushPresets.js)
        assert options >= 10, f"Expected at least 10 presets, got {options}"

    async def test_brush_preset_menu_has_thumbnails(self, helpers: TestHelpers):
        """Test that preset options have thumbnail images."""
        await helpers.new_document(200, 200)

        # Open the menu
        await helpers.editor.page.click(".brush-preset-dropdown")
        await helpers.editor.page.wait_for_timeout(300)
        await helpers.editor.page.wait_for_selector(".brush-preset-menu", state="visible", timeout=3000)

        # Find thumbnail images in menu
        thumbs = await helpers.editor.page.locator(".brush-preset-option .preset-thumb").count()
        assert thumbs > 0, "Menu options should have thumbnail images"

    async def test_selecting_preset_changes_brush(self, helpers: TestHelpers):
        """Test that selecting a preset changes the brush settings."""
        await helpers.new_document(200, 200)

        # Get initial preset
        initial_preset = await helpers.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root?.__vue_app__?._instance?.proxy;
                return vm?.currentBrushPreset;
            })()
        """)

        # Open menu and select a different preset
        await helpers.editor.page.click(".brush-preset-dropdown")
        await helpers.editor.page.wait_for_timeout(300)
        await helpers.editor.page.wait_for_selector(".brush-preset-menu", state="visible", timeout=3000)

        # Find and click a different preset (soft-round-lg)
        options = await helpers.editor.page.locator(".brush-preset-option").all()
        for opt in options:
            name_elem = await opt.locator(".preset-name").text_content()
            if name_elem and "Soft Round Large" in name_elem:
                await opt.click()
                break

        await helpers.editor.page.wait_for_timeout(300)

        # Verify preset changed
        new_preset = await helpers.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root?.__vue_app__?._instance?.proxy;
                return vm?.currentBrushPreset;
            })()
        """)
        assert new_preset != initial_preset, "Preset should have changed after selection"

    async def test_menu_closes_after_selection(self, helpers: TestHelpers):
        """Test that the menu closes after selecting a preset."""
        await helpers.new_document(200, 200)

        # Open menu
        await helpers.editor.page.click(".brush-preset-dropdown")
        await helpers.editor.page.wait_for_timeout(300)
        await helpers.editor.page.wait_for_selector(".brush-preset-menu", state="visible", timeout=3000)

        # Select first option
        await helpers.editor.page.click(".brush-preset-option")
        await helpers.editor.page.wait_for_timeout(300)

        # Menu should be closed
        show_menu = await helpers.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root?.__vue_app__?._instance?.proxy;
                return vm?.showBrushPresetMenu;
            })()
        """)
        assert show_menu is False, "Menu should be closed after selection"

    async def test_menu_closes_on_outside_click(self, helpers: TestHelpers):
        """Test that clicking outside the menu closes it."""
        await helpers.new_document(200, 200)

        # Open menu
        await helpers.editor.page.click(".brush-preset-dropdown")
        await helpers.editor.page.wait_for_timeout(300)
        await helpers.editor.page.wait_for_selector(".brush-preset-menu", state="visible", timeout=3000)

        # Click somewhere else (the canvas)
        await helpers.editor.page.click(".canvas-container")
        await helpers.editor.page.wait_for_timeout(300)

        # Menu should be closed
        menu_visible = await helpers.editor.page.locator(".brush-preset-menu").is_visible()
        assert not menu_visible, "Menu should close when clicking outside"


class TestBrushPresetMenuDiagnostics:
    """Diagnostic tests to help identify menu issues."""

    async def test_diagnose_menu_click_handler(self, helpers: TestHelpers):
        """Diagnose what happens when the dropdown is clicked."""
        await helpers.new_document(200, 200)

        # Check initial state
        initial_state = await helpers.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root?.__vue_app__?._instance?.proxy;
                return {
                    showBrushPresetMenu: vm?.showBrushPresetMenu,
                    currentToolId: vm?.currentToolId,
                    brushPresetThumbnailsGenerated: vm?.brushPresetThumbnailsGenerated
                };
            })()
        """)
        print(f"\nInitial state: {initial_state}")

        # Check if dropdown element has click handler
        has_click = await helpers.editor.execute_js("""
            (() => {
                const dropdown = document.querySelector('.brush-preset-dropdown');
                if (!dropdown) return { exists: false };

                return {
                    exists: true,
                    tagName: dropdown.tagName,
                    className: dropdown.className,
                    innerHTML: dropdown.innerHTML.substring(0, 100)
                };
            })()
        """)
        print(f"Dropdown element info: {has_click}")

        # Try to manually trigger the toggle
        result = await helpers.editor.execute_js("""
            (() => {
                // Find the Vue component instance
                const root = document.querySelector('.editor-root');
                if (!root || !root.__vue_app__) return { error: 'Vue app not found' };

                const vm = root.__vue_app__._instance?.proxy;
                if (!vm) return { error: 'Vue instance not found' };

                // Check if method exists
                const hasMethod = typeof vm.toggleBrushPresetMenu === 'function';

                // Try calling directly
                if (hasMethod) {
                    try {
                        // Create a mock event
                        const mockEvent = { stopPropagation: () => {} };
                        vm.toggleBrushPresetMenu(mockEvent);
                        return {
                            success: true,
                            showBrushPresetMenu: vm.showBrushPresetMenu
                        };
                    } catch (e) {
                        return { error: e.message };
                    }
                }

                return { hasMethod: false };
            })()
        """)
        print(f"Manual toggle result: {result}")

        # Check final state
        final_state = await helpers.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root?.__vue_app__?._instance?.proxy;
                return vm?.showBrushPresetMenu;
            })()
        """)
        print(f"Final showBrushPresetMenu: {final_state}")

        # This test is informational - it passes but prints diagnostics
        assert True

    async def test_diagnose_template_rendering(self, helpers: TestHelpers):
        """Check if the brush preset dropdown template is rendering correctly."""
        await helpers.new_document(200, 200)

        # Check if we're on the brush tool
        debug_info = await helpers.editor.execute_js("""
            (() => {
                const root = document.querySelector('.editor-root');
                const vm = root?.__vue_app__?._instance?.proxy;

                const currentTool = vm?.currentToolId;
                const toolProps = vm?.toolProperties;

                // Find the preset property
                let presetProp = null;
                if (toolProps) {
                    for (const prop of toolProps) {
                        if (prop.id === 'preset') {
                            presetProp = {
                                type: prop.type,
                                optionsCount: prop.options?.length || 0
                            };
                            break;
                        }
                    }
                }

                // Check rendered HTML structure
                const ribbon = document.querySelector('.ribbon-properties');
                const htmlStructure = {
                    childCount: ribbon?.children?.length || 0,
                    hasPresetDropdown: !!ribbon?.querySelector('.brush-preset-dropdown'),
                    hasPresetMenu: !!ribbon?.querySelector('.brush-preset-menu')
                };

                return {
                    currentTool,
                    toolPropsCount: toolProps?.length || 0,
                    presetProp,
                    htmlStructure
                };
            })()
        """)

        print(f"\nDiagnostic info: {debug_info}")

        assert True  # Diagnostic test
