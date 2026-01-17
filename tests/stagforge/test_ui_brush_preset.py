"""UI tests for brush preset menu functionality.

These tests use Selenium to interact with the actual browser UI and verify
the brush preset dropdown menu works correctly.
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException


class TestBrushPresetMenu:
    """Tests for the brush preset dropdown menu in the toolbar."""

    def test_brush_tool_is_default(self, browser_helper):
        """Verify brush tool is selected by default on load."""
        # Check the current tool via Vue data
        current_tool = browser_helper.get_vue_data("currentToolId")
        assert current_tool == "brush", f"Expected brush tool, got {current_tool}"

    def test_brush_preset_thumbnails_generated_on_load(self, browser_helper):
        """Verify brush preset thumbnails are generated on initial load."""
        # Check if thumbnails were generated
        thumbnails_generated = browser_helper.get_vue_data("brushPresetThumbnailsGenerated")
        assert thumbnails_generated is True, "Brush preset thumbnails should be generated on load"

        # Check that thumbnails object has entries
        thumbnails = browser_helper.get_vue_data("brushPresetThumbnails")
        assert thumbnails is not None, "brushPresetThumbnails should not be None"
        assert len(thumbnails) > 0, "brushPresetThumbnails should have entries"

    def test_brush_preset_thumbnail_displayed_in_toolbar(self, browser_helper):
        """Verify the current brush preset thumbnail is displayed in toolbar."""
        # Wait for the thumbnail to appear
        try:
            thumb = browser_helper.wait_for_visible(".brush-preset-thumb", timeout=5)
            assert thumb is not None, "Brush preset thumbnail should be visible in toolbar"
        except TimeoutException:
            # Print debug info
            browser_helper.print_errors()
            current_tool = browser_helper.get_vue_data("currentToolId")
            thumbnails = browser_helper.get_vue_data("brushPresetThumbnails")
            current_preset = browser_helper.get_vue_data("currentBrushPreset")
            print(f"Debug: currentToolId={current_tool}")
            print(f"Debug: currentBrushPreset={current_preset}")
            print(f"Debug: thumbnails keys={list(thumbnails.keys()) if thumbnails else None}")
            raise AssertionError("Brush preset thumbnail not visible in toolbar")

    def test_brush_preset_dropdown_exists(self, browser_helper):
        """Verify the brush preset dropdown element exists."""
        dropdown = browser_helper.find_by_css(".brush-preset-dropdown")
        assert dropdown is not None, "Brush preset dropdown should exist"
        assert dropdown.is_displayed(), "Brush preset dropdown should be visible"

    def test_brush_preset_menu_opens_on_click(self, browser_helper):
        """Test that clicking the preset dropdown opens the menu."""
        # First verify menu is not visible
        menu_visible_before = browser_helper.is_visible(".brush-preset-menu")
        assert not menu_visible_before, "Menu should be hidden initially"

        # Print any existing JS errors before clicking
        errors_before = browser_helper.print_errors()

        # Click the dropdown to open menu
        try:
            browser_helper.click(".brush-preset-dropdown")
        except ElementClickInterceptedException as e:
            print(f"Click intercepted: {e}")
            # Try clicking via JavaScript
            browser_helper.execute_js("""
                document.querySelector('.brush-preset-dropdown').click();
            """)

        # Small delay for Vue reactivity
        time.sleep(0.3)

        # Check for new JS errors after click
        errors_after = browser_helper.print_errors()

        # Check Vue state
        show_menu = browser_helper.get_vue_data("showBrushPresetMenu")
        print(f"Debug: showBrushPresetMenu = {show_menu}")

        # Verify menu is now visible
        try:
            browser_helper.wait_for_visible(".brush-preset-menu", timeout=3)
            menu_visible_after = True
        except TimeoutException:
            menu_visible_after = False

        # If menu didn't open, gather diagnostic info
        if not menu_visible_after:
            # Check if the element exists but is hidden
            menu_exists = browser_helper.execute_js("""
                return document.querySelector('.brush-preset-menu') !== null;
            """)
            menu_display = browser_helper.execute_js("""
                const menu = document.querySelector('.brush-preset-menu');
                if (!menu) return 'element not found';
                const style = window.getComputedStyle(menu);
                return {
                    display: style.display,
                    visibility: style.visibility,
                    opacity: style.opacity,
                    vIf: menu.style.display
                };
            """)
            print(f"Debug: menu element exists = {menu_exists}")
            print(f"Debug: menu style = {menu_display}")

            # Check if v-if condition is met
            tool_props = browser_helper.get_vue_data("toolProperties")
            print(f"Debug: toolProperties has preset = {any(p.get('id') == 'preset' for p in (tool_props or []))}")

        assert menu_visible_after, "Brush preset menu should be visible after clicking dropdown"

    def test_brush_preset_menu_contains_options(self, browser_helper):
        """Test that the opened menu contains preset options."""
        # Open the menu first
        browser_helper.click(".brush-preset-dropdown")
        time.sleep(0.3)

        # Wait for menu to be visible
        browser_helper.wait_for_visible(".brush-preset-menu", timeout=3)

        # Find all preset options
        options = browser_helper.driver.find_elements(By.CSS_SELECTOR, ".brush-preset-option")
        assert len(options) > 0, "Menu should contain preset options"

        # Verify we have the expected number of presets (10 in BrushPresets.js)
        assert len(options) >= 10, f"Expected at least 10 presets, got {len(options)}"

    def test_brush_preset_menu_has_thumbnails(self, browser_helper):
        """Test that preset options have thumbnail images."""
        # Open the menu
        browser_helper.click(".brush-preset-dropdown")
        time.sleep(0.3)
        browser_helper.wait_for_visible(".brush-preset-menu", timeout=3)

        # Find thumbnail images in menu
        thumbs = browser_helper.driver.find_elements(By.CSS_SELECTOR, ".brush-preset-option .preset-thumb")
        assert len(thumbs) > 0, "Menu options should have thumbnail images"

    def test_selecting_preset_changes_brush(self, browser_helper):
        """Test that selecting a preset changes the brush settings."""
        # Get initial preset
        initial_preset = browser_helper.get_vue_data("currentBrushPreset")

        # Open menu and select a different preset
        browser_helper.click(".brush-preset-dropdown")
        time.sleep(0.3)
        browser_helper.wait_for_visible(".brush-preset-menu", timeout=3)

        # Find and click a different preset (soft-round-lg)
        options = browser_helper.driver.find_elements(By.CSS_SELECTOR, ".brush-preset-option")
        for opt in options:
            name_elem = opt.find_element(By.CSS_SELECTOR, ".preset-name")
            if "Soft Round Large" in name_elem.text:
                opt.click()
                break

        time.sleep(0.3)

        # Verify preset changed
        new_preset = browser_helper.get_vue_data("currentBrushPreset")
        assert new_preset != initial_preset, "Preset should have changed after selection"

    def test_menu_closes_after_selection(self, browser_helper):
        """Test that the menu closes after selecting a preset."""
        # Open menu
        browser_helper.click(".brush-preset-dropdown")
        time.sleep(0.3)
        browser_helper.wait_for_visible(".brush-preset-menu", timeout=3)

        # Select first option
        browser_helper.click(".brush-preset-option")
        time.sleep(0.3)

        # Menu should be closed
        show_menu = browser_helper.get_vue_data("showBrushPresetMenu")
        assert show_menu is False, "Menu should be closed after selection"

    def test_menu_closes_on_outside_click(self, browser_helper):
        """Test that clicking outside the menu closes it."""
        # Open menu
        browser_helper.click(".brush-preset-dropdown")
        time.sleep(0.3)
        browser_helper.wait_for_visible(".brush-preset-menu", timeout=3)

        # Click somewhere else (the canvas)
        browser_helper.click(".canvas-container")
        time.sleep(0.3)

        # Menu should be closed
        menu_visible = browser_helper.is_visible(".brush-preset-menu")
        assert not menu_visible, "Menu should close when clicking outside"


class TestBrushPresetMenuDiagnostics:
    """Diagnostic tests to help identify menu issues."""

    def test_diagnose_menu_click_handler(self, browser_helper):
        """Diagnose what happens when the dropdown is clicked."""
        # Check initial state
        initial_state = {
            "showBrushPresetMenu": browser_helper.get_vue_data("showBrushPresetMenu"),
            "currentToolId": browser_helper.get_vue_data("currentToolId"),
            "brushPresetThumbnailsGenerated": browser_helper.get_vue_data("brushPresetThumbnailsGenerated"),
        }
        print(f"\nInitial state: {initial_state}")

        # Check if dropdown element has click handler
        has_click = browser_helper.execute_js("""
            const dropdown = document.querySelector('.brush-preset-dropdown');
            if (!dropdown) return { exists: false };

            // Check for Vue event listeners
            const vueEvents = dropdown.__vueParentComponent?.vnode?.props;

            return {
                exists: true,
                tagName: dropdown.tagName,
                className: dropdown.className,
                innerHTML: dropdown.innerHTML.substring(0, 100),
                hasOnClick: dropdown.onclick !== null,
                vueProps: vueEvents ? Object.keys(vueEvents) : []
            };
        """)
        print(f"Dropdown element info: {has_click}")

        # Try to manually trigger the toggle
        result = browser_helper.execute_js("""
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
        """)
        print(f"Manual toggle result: {result}")

        # Check final state
        final_state = browser_helper.get_vue_data("showBrushPresetMenu")
        print(f"Final showBrushPresetMenu: {final_state}")

        # This test is informational - it passes but prints diagnostics
        assert True

    def test_diagnose_template_rendering(self, browser_helper):
        """Check if the brush preset dropdown template is rendering correctly."""
        # Check if we're on the brush tool
        current_tool = browser_helper.get_vue_data("currentToolId")
        print(f"\nCurrent tool: {current_tool}")

        # Check tool properties
        tool_props = browser_helper.get_vue_data("toolProperties")
        print(f"Tool properties count: {len(tool_props) if tool_props else 0}")

        # Find the preset property
        preset_prop = None
        if tool_props:
            for prop in tool_props:
                if prop.get("id") == "preset":
                    preset_prop = prop
                    break

        print(f"Preset property found: {preset_prop is not None}")
        if preset_prop:
            print(f"Preset type: {preset_prop.get('type')}")
            print(f"Preset options count: {len(preset_prop.get('options', []))}")

        # Check rendered HTML structure
        html_structure = browser_helper.execute_js("""
            const ribbon = document.querySelector('.ribbon-properties');
            if (!ribbon) return { error: 'ribbon-properties not found' };

            return {
                childCount: ribbon.children.length,
                hasPresetDropdown: ribbon.querySelector('.brush-preset-dropdown') !== null,
                hasPresetMenu: ribbon.querySelector('.brush-preset-menu') !== null,
                dropdownHTML: ribbon.querySelector('.brush-preset-dropdown')?.outerHTML?.substring(0, 200)
            };
        """)
        print(f"HTML structure: {html_structure}")

        assert True  # Diagnostic test
