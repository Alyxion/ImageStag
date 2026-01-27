"""Parity test registrations for ImageStag filters and effects.

All filters and effects are defined in centralized catalog modules.
Import this module to register all built-in parity tests.

See filter_catalog.py and layer_effect_catalog.py for:
- FILTER_CATALOG: List of all filters with default test parameters
- EFFECT_CATALOG: List of all layer effects with default test parameters
- Adding new filters/effects to the test suite
"""

from ..filter_catalog import register_all_filters
from ..layer_effect_catalog import register_all_effects

# Register all filters from the centralized catalog
_filter_results = register_all_filters()

# Report any filters that failed to register
_failed_filters = [name for name, success in _filter_results.items() if not success]
if _failed_filters:
    import warnings
    warnings.warn(
        f"Some filters not registered (missing Python wrappers): {_failed_filters}",
        stacklevel=2
    )

# Register all layer effects from the centralized catalog
_effect_results = register_all_effects()

# Report any effects that failed to register
_failed_effects = [name for name, success in _effect_results.items() if not success]
if _failed_effects:
    import warnings
    warnings.warn(
        f"Some effects not registered (missing Python wrappers): {_failed_effects}",
        stacklevel=2
    )

__all__ = ['register_all_filters', 'register_all_effects']
