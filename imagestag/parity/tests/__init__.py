"""Parity test registrations for ImageStag filters and effects.

All filters are defined in the centralized filter_catalog module.
Import this module to register all built-in parity tests.

See filter_catalog.py for:
- FILTER_CATALOG: List of all filters with default test parameters
- Adding new filters to the test suite
"""

from ..filter_catalog import register_all_filters

# Register all filters from the centralized catalog
_results = register_all_filters()

# Report any filters that failed to register
_failed = [name for name, success in _results.items() if not success]
if _failed:
    import warnings
    warnings.warn(
        f"Some filters not registered (missing Python wrappers): {_failed}",
        stacklevel=2
    )

__all__ = ['register_all_filters']
