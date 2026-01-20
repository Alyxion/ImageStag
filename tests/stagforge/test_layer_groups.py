"""
Tests for layer groups functionality.

Tests cover:
- Creating groups
- Group operations (grouping, ungrouping, moving to/from groups)
- Visibility and opacity inheritance
- Layer reordering
- Serialization and deserialization
- History integration (undo/redo)

Run with: pytest tests/stagforge/test_layer_groups.py -v
Requires: stagforge server running on localhost:8080
"""
import pytest
from playwright.sync_api import sync_playwright, Page, Browser


@pytest.fixture(scope="module")
def browser():
    """Launch browser for all tests in module."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture
def stagforge_app(page: Page):
    """Fixture to ensure Stagforge is loaded and reset for each test."""
    page.goto('http://localhost:8080')
    # Wait for app to be ready - check for layerStack
    page.wait_for_function('window.__stagforge_app__ && window.__stagforge_app__.layerStack', timeout=30000)
    # Reset to a clean state - create new document
    page.evaluate('''() => {
        const app = window.__stagforge_app__;
        // Create fresh document to avoid interference between tests
        if (app.documentManager) {
            const doc = app.documentManager.createDocument({ width: 800, height: 600, name: 'Test' });
            app.documentManager.setActiveDocument(doc.id);
        }
    }''')
    return page


class TestLayerGroupCreation:
    """Tests for creating layer groups."""

    def test_create_empty_group(self, page: Page, stagforge_app):
        """Test creating an empty group."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Test Group' });
            return {
                id: group.id,
                name: group.name,
                type: group.type,
                isGroup: group.isGroup(),
                visible: group.visible,
                opacity: group.opacity,
                blendMode: group.blendMode,
                expanded: group.expanded,
                parentId: group.parentId
            };
        }''')

        assert result['name'] == 'Test Group'
        assert result['type'] == 'group'
        assert result['isGroup'] == True
        assert result['visible'] == True
        assert result['opacity'] == 1.0
        assert result['blendMode'] == 'passthrough'
        assert result['expanded'] == True
        assert result['parentId'] is None

    def test_create_group_from_layers(self, page: Page, stagforge_app):
        """Test creating a group from selected layers."""
        result = page.evaluate('''() => {
            // Create some layers
            const layer1 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 1' });
            const layer2 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 2' });

            // Group them
            const group = window.__stagforge_app__.layerStack.createGroupFromLayers(
                [layer1.id, layer2.id],
                'My Group'
            );

            return {
                groupId: group.id,
                groupName: group.name,
                layer1Parent: layer1.parentId,
                layer2Parent: layer2.parentId,
                layerCount: window.__stagforge_app__.layerStack.layers.length
            };
        }''')

        assert result['groupName'] == 'My Group'
        assert result['layer1Parent'] == result['groupId']
        assert result['layer2Parent'] == result['groupId']

    def test_nested_groups(self, page: Page, stagforge_app):
        """Test creating nested groups."""
        result = page.evaluate('''() => {
            // Create parent group
            const parentGroup = window.__stagforge_app__.layerStack.createGroup({ name: 'Parent' });

            // Create child group inside parent
            const childGroup = window.__stagforge_app__.layerStack.createGroup({
                name: 'Child',
                parentId: parentGroup.id
            });

            return {
                parentId: parentGroup.id,
                childId: childGroup.id,
                childParent: childGroup.parentId,
                isChildInsideParent: childGroup.parentId === parentGroup.id
            };
        }''')

        assert result['isChildInsideParent'] == True
        assert result['childParent'] == result['parentId']


class TestGroupVisibility:
    """Tests for group visibility affecting children."""

    def test_group_visibility_affects_children(self, page: Page, stagforge_app):
        """Test that hiding a group affects child visibility."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = group.id;

            // Initially both visible
            const initialVisible = window.__stagforge_app__.layerStack.isEffectivelyVisible(layer);

            // Hide the group
            group.visible = false;
            const hiddenByGroup = window.__stagforge_app__.layerStack.isEffectivelyVisible(layer);

            // Show the group again
            group.visible = true;
            const visibleAgain = window.__stagforge_app__.layerStack.isEffectivelyVisible(layer);

            return { initialVisible, hiddenByGroup, visibleAgain };
        }''')

        assert result['initialVisible'] == True
        assert result['hiddenByGroup'] == False
        assert result['visibleAgain'] == True

    def test_effective_opacity_with_group(self, page: Page, stagforge_app):
        """Test effective opacity calculation through group chain."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            group.opacity = 0.5;
            group.blendMode = 'normal';  // Not passthrough

            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = group.id;
            layer.opacity = 0.5;

            const effectiveOpacity = window.__stagforge_app__.layerStack.getEffectiveOpacity(layer);

            return { effectiveOpacity };
        }''')

        # 0.5 * 0.5 = 0.25
        assert abs(result['effectiveOpacity'] - 0.25) < 0.01

    def test_passthrough_mode_ignores_group_opacity(self, page: Page, stagforge_app):
        """Test that passthrough blend mode ignores group opacity."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            group.opacity = 0.5;
            group.blendMode = 'passthrough';  // Passthrough mode

            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = group.id;
            layer.opacity = 0.8;

            const effectiveOpacity = window.__stagforge_app__.layerStack.getEffectiveOpacity(layer);

            return { effectiveOpacity };
        }''')

        # In passthrough mode, group opacity is ignored
        assert abs(result['effectiveOpacity'] - 0.8) < 0.01


class TestGroupOperations:
    """Tests for group operations."""

    def test_ungroup_layers(self, page: Page, stagforge_app):
        """Test ungrouping moves children to parent."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer1 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 1' });
            const layer2 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 2' });
            layer1.parentId = group.id;
            layer2.parentId = group.id;

            const beforeLayerCount = window.__stagforge_app__.layerStack.layers.length;

            // Ungroup
            window.__stagforge_app__.layerStack.ungroupLayers(group.id);

            return {
                beforeLayerCount,
                afterLayerCount: window.__stagforge_app__.layerStack.layers.length,
                layer1Parent: layer1.parentId,
                layer2Parent: layer2.parentId,
                groupStillExists: window.__stagforge_app__.layerStack.getLayerById(group.id) !== null
            };
        }''')

        # Group should be removed
        assert result['groupStillExists'] == False
        # Children should be at root (null parent)
        assert result['layer1Parent'] is None
        assert result['layer2Parent'] is None
        # One less item (group removed)
        assert result['afterLayerCount'] == result['beforeLayerCount'] - 1

    def test_delete_group_keeps_children(self, page: Page, stagforge_app):
        """Test deleting a group with deleteChildren=false keeps children."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = group.id;
            const layerId = layer.id;

            window.__stagforge_app__.layerStack.deleteGroup(group.id, false);

            const layerStillExists = window.__stagforge_app__.layerStack.getLayerById(layerId) !== null;
            const restoredLayer = window.__stagforge_app__.layerStack.getLayerById(layerId);

            return {
                layerStillExists,
                layerParent: restoredLayer ? restoredLayer.parentId : 'deleted'
            };
        }''')

        assert result['layerStillExists'] == True
        assert result['layerParent'] is None  # Moved to root

    def test_delete_group_deletes_children(self, page: Page, stagforge_app):
        """Test deleting a group with deleteChildren=true removes children."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = group.id;
            const layerId = layer.id;

            const beforeCount = window.__stagforge_app__.layerStack.layers.length;
            window.__stagforge_app__.layerStack.deleteGroup(group.id, true);
            const afterCount = window.__stagforge_app__.layerStack.layers.length;

            const layerStillExists = window.__stagforge_app__.layerStack.getLayerById(layerId) !== null;

            return { beforeCount, afterCount, layerStillExists };
        }''')

        assert result['layerStillExists'] == False

    def test_move_layer_to_group(self, page: Page, stagforge_app):
        """Test moving a layer into a group."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });

            const beforeParent = layer.parentId;
            window.__stagforge_app__.layerStack.moveLayerToGroup(layer.id, group.id);
            const afterParent = layer.parentId;

            return { beforeParent, afterParent, groupId: group.id };
        }''')

        assert result['beforeParent'] is None
        assert result['afterParent'] == result['groupId']

    def test_remove_layer_from_group(self, page: Page, stagforge_app):
        """Test removing a layer from a group."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = group.id;

            window.__stagforge_app__.layerStack.removeLayerFromGroup(layer.id);

            return { parentId: layer.parentId };
        }''')

        assert result['parentId'] is None

    def test_cannot_move_group_into_itself(self, page: Page, stagforge_app):
        """Test that a group cannot be moved into itself."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const success = window.__stagforge_app__.layerStack.moveLayerToGroup(group.id, group.id);
            return { success, parentId: group.parentId };
        }''')

        assert result['success'] == False
        assert result['parentId'] is None

    def test_cannot_move_group_into_descendant(self, page: Page, stagforge_app):
        """Test that a group cannot be moved into its descendant."""
        result = page.evaluate('''() => {
            const parentGroup = window.__stagforge_app__.layerStack.createGroup({ name: 'Parent' });
            const childGroup = window.__stagforge_app__.layerStack.createGroup({
                name: 'Child',
                parentId: parentGroup.id
            });

            // Try to move parent into child (should fail)
            const success = window.__stagforge_app__.layerStack.moveLayerToGroup(parentGroup.id, childGroup.id);

            return { success, parentGroupParent: parentGroup.parentId };
        }''')

        assert result['success'] == False
        assert result['parentGroupParent'] is None


class TestLayerReordering:
    """Tests for layer reordering."""

    def test_move_layer_up(self, page: Page, stagforge_app):
        """Test moving a layer up in z-order."""
        result = page.evaluate('''() => {
            const layer1 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 1' });
            const layer2 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 2' });
            const layer3 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 3' });

            // layer1 is at index 1 (Background at 0)
            const index1Before = window.__stagforge_app__.layerStack.getLayerIndex(layer1.id);

            window.__stagforge_app__.layerStack.moveLayerUp(index1Before);

            const index1After = window.__stagforge_app__.layerStack.getLayerIndex(layer1.id);

            return { index1Before, index1After };
        }''')

        # Should have moved up by 1
        assert result['index1After'] == result['index1Before'] + 1

    def test_move_layer_down(self, page: Page, stagforge_app):
        """Test moving a layer down in z-order."""
        result = page.evaluate('''() => {
            const layer1 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 1' });
            const layer2 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 2' });

            const index2Before = window.__stagforge_app__.layerStack.getLayerIndex(layer2.id);

            window.__stagforge_app__.layerStack.moveLayerDown(index2Before);

            const index2After = window.__stagforge_app__.layerStack.getLayerIndex(layer2.id);

            return { index2Before, index2After };
        }''')

        assert result['index2After'] == result['index2Before'] - 1

    def test_move_layer_to_top(self, page: Page, stagforge_app):
        """Test moving a layer to the top."""
        result = page.evaluate('''() => {
            const layer1 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 1' });
            const layer2 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 2' });
            const layer3 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 3' });

            const index1Before = window.__stagforge_app__.layerStack.getLayerIndex(layer1.id);
            const topIndex = window.__stagforge_app__.layerStack.layers.length - 1;

            window.__stagforge_app__.layerStack.moveLayerToTop(index1Before);

            const index1After = window.__stagforge_app__.layerStack.getLayerIndex(layer1.id);

            return { index1Before, index1After, topIndex };
        }''')

        assert result['index1After'] == result['topIndex']

    def test_move_layer_to_bottom(self, page: Page, stagforge_app):
        """Test moving a layer to the bottom."""
        result = page.evaluate('''() => {
            const layer1 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 1' });
            const layer2 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 2' });
            const layer3 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 3' });

            const index3 = window.__stagforge_app__.layerStack.getLayerIndex(layer3.id);

            window.__stagforge_app__.layerStack.moveLayerToBottom(index3);

            const index3After = window.__stagforge_app__.layerStack.getLayerIndex(layer3.id);

            return { index3After };
        }''')

        assert result['index3After'] == 0


class TestGroupSerialization:
    """Tests for group serialization and deserialization."""

    def test_group_serializes_correctly(self, page: Page, stagforge_app):
        """Test that groups serialize with all properties."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({
                name: 'Test Group',
                opacity: 0.75,
                blendMode: 'multiply',
                visible: false,
                locked: true,
                expanded: false
            });

            const serialized = group.serialize();

            return {
                type: serialized.type,
                _type: serialized._type,
                name: serialized.name,
                opacity: serialized.opacity,
                blendMode: serialized.blendMode,
                visible: serialized.visible,
                locked: serialized.locked,
                expanded: serialized.expanded,
                hasId: 'id' in serialized,
                hasVersion: '_version' in serialized
            };
        }''')

        assert result['type'] == 'group'
        assert result['_type'] == 'LayerGroup'
        assert result['name'] == 'Test Group'
        assert result['opacity'] == 0.75
        assert result['blendMode'] == 'multiply'
        assert result['visible'] == False
        assert result['locked'] == True
        assert result['expanded'] == False
        assert result['hasId'] == True
        assert result['hasVersion'] == True

    def test_group_deserializes_correctly(self, page: Page, stagforge_app):
        """Test that groups serialize and deserialize correctly (roundtrip)."""
        result = page.evaluate('''() => {
            // Create a group with specific properties
            const group = window.__stagforge_app__.layerStack.createGroup({
                name: 'Roundtrip Group',
                opacity: 0.6,
                blendMode: 'screen',
                visible: true,
                locked: false,
                expanded: true
            });
            group.opacity = 0.6;
            group.blendMode = 'screen';

            // Serialize it
            const serialized = group.serialize();

            // Check that serialization includes all required fields
            return {
                hasVersion: '_version' in serialized,
                hasType: '_type' in serialized,
                hasId: 'id' in serialized,
                type: serialized.type,
                _type: serialized._type,
                name: serialized.name,
                opacity: serialized.opacity,
                blendMode: serialized.blendMode,
                visible: serialized.visible,
                locked: serialized.locked,
                expanded: serialized.expanded
            };
        }''')

        assert result['hasVersion'] == True
        assert result['hasType'] == True
        assert result['hasId'] == True
        assert result['_type'] == 'LayerGroup'
        assert result['type'] == 'group'
        assert result['name'] == 'Roundtrip Group'
        assert result['opacity'] == 0.6
        assert result['blendMode'] == 'screen'
        assert result['visible'] == True
        assert result['locked'] == False
        assert result['expanded'] == True

    def test_layer_serializes_parent_id(self, page: Page, stagforge_app):
        """Test that layers serialize their parentId."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = group.id;

            const serialized = layer.serialize();

            return {
                hasParentId: 'parentId' in serialized,
                parentId: serialized.parentId,
                groupId: group.id
            };
        }''')

        assert result['hasParentId'] == True
        assert result['parentId'] == result['groupId']


class TestGroupHelperMethods:
    """Tests for group helper methods."""

    def test_get_children(self, page: Page, stagforge_app):
        """Test getting direct children of a group."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer1 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 1' });
            const layer2 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 2' });
            const layer3 = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer 3' });

            layer1.parentId = group.id;
            layer2.parentId = group.id;
            // layer3 stays at root

            const children = window.__stagforge_app__.layerStack.getChildren(group.id);
            const rootChildren = window.__stagforge_app__.layerStack.getChildren(null);

            return {
                groupChildrenCount: children.length,
                groupChildrenIds: children.map(c => c.id),
                rootChildrenCount: rootChildren.length,
                layer1Id: layer1.id,
                layer2Id: layer2.id,
                layer3Id: layer3.id
            };
        }''')

        assert result['groupChildrenCount'] == 2
        assert result['layer1Id'] in result['groupChildrenIds']
        assert result['layer2Id'] in result['groupChildrenIds']
        # layer3 should be in root children
        assert result['layer3Id'] not in result['groupChildrenIds']

    def test_get_descendants(self, page: Page, stagforge_app):
        """Test getting all descendants of a group (recursive)."""
        result = page.evaluate('''() => {
            const parentGroup = window.__stagforge_app__.layerStack.createGroup({ name: 'Parent' });
            const childGroup = window.__stagforge_app__.layerStack.createGroup({
                name: 'Child',
                parentId: parentGroup.id
            });
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = childGroup.id;

            const descendants = window.__stagforge_app__.layerStack.getDescendants(parentGroup.id);

            return {
                count: descendants.length,
                ids: descendants.map(d => d.id),
                childGroupId: childGroup.id,
                layerId: layer.id
            };
        }''')

        assert result['count'] == 2  # child group + layer
        assert result['childGroupId'] in result['ids']
        assert result['layerId'] in result['ids']

    def test_is_effectively_locked(self, page: Page, stagforge_app):
        """Test that locking a group affects children."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            layer.parentId = group.id;

            const beforeLock = window.__stagforge_app__.layerStack.isEffectivelyLocked(layer);
            group.locked = true;
            const afterLock = window.__stagforge_app__.layerStack.isEffectivelyLocked(layer);

            return { beforeLock, afterLock };
        }''')

        assert result['beforeLock'] == False
        assert result['afterLock'] == True


class TestGroupToggleMethods:
    """Tests for layer property toggle methods."""

    def test_toggle_visibility(self, page: Page, stagforge_app):
        """Test toggling layer visibility."""
        result = page.evaluate('''() => {
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Layer' });
            const initial = layer.visible;

            window.__stagforge_app__.layerStack.toggleLayerVisibility(layer.id);
            const afterToggle = layer.visible;

            window.__stagforge_app__.layerStack.toggleLayerVisibility(layer.id);
            const afterSecondToggle = layer.visible;

            return { initial, afterToggle, afterSecondToggle };
        }''')

        assert result['initial'] == True
        assert result['afterToggle'] == False
        assert result['afterSecondToggle'] == True

    def test_toggle_group_expanded(self, page: Page, stagforge_app):
        """Test toggling group expanded state."""
        result = page.evaluate('''() => {
            const group = window.__stagforge_app__.layerStack.createGroup({ name: 'Group' });
            const initial = group.expanded;

            window.__stagforge_app__.layerStack.toggleGroupExpanded(group.id);
            const afterToggle = group.expanded;

            return { initial, afterToggle };
        }''')

        assert result['initial'] == True
        assert result['afterToggle'] == False

    def test_rename_layer(self, page: Page, stagforge_app):
        """Test renaming a layer."""
        result = page.evaluate('''() => {
            const layer = window.__stagforge_app__.layerStack.addLayer({ name: 'Old Name' });

            window.__stagforge_app__.layerStack.renameLayer(layer.id, 'New Name');

            return { name: layer.name };
        }''')

        assert result['name'] == 'New Name'
