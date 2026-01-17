"""Plugin loader and manager."""

import importlib.util
import json
from pathlib import Path
from typing import Any


class PluginLoader:
    """Loads and manages external plugins."""

    def __init__(self):
        self.loaded_plugins: dict[str, Any] = {}

    def load_plugin(self, plugin_path: Path) -> bool:
        """Load a single plugin from a directory."""
        manifest_path = plugin_path / "manifest.json"

        if not manifest_path.exists():
            print(f"No manifest.json in {plugin_path}")
            return False

        try:
            with open(manifest_path) as f:
                manifest = json.load(f)

            plugin_id = manifest.get("id")
            if not plugin_id:
                print(f"Plugin missing 'id' in manifest: {plugin_path}")
                return False

            # Load Python module
            module_file = plugin_path / manifest.get("module", "__init__.py")
            if not module_file.exists():
                print(f"Plugin module not found: {module_file}")
                return False

            spec = importlib.util.spec_from_file_location(plugin_id, module_file)
            if spec is None or spec.loader is None:
                print(f"Failed to load spec for plugin: {plugin_path}")
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Call plugin's register function if it exists
            if hasattr(module, "register"):
                module.register()

            self.loaded_plugins[plugin_id] = {
                "manifest": manifest,
                "module": module,
                "path": plugin_path,
            }

            print(f"Loaded plugin: {manifest.get('name', plugin_id)}")
            return True

        except Exception as e:
            print(f"Failed to load plugin {plugin_path}: {e}")
            return False

    def load_all_from_directory(self, plugins_dir: Path):
        """Load all plugins from a directory."""
        if not plugins_dir.exists():
            return

        for item in plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                self.load_plugin(item)


# Global plugin loader
plugin_loader = PluginLoader()


def load_plugins(plugins_dir: Path):
    """Load all plugins from the specified directory."""
    plugin_loader.load_all_from_directory(plugins_dir)
