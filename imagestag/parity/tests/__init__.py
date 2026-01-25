"""Parity test registrations for ImageStag filters and effects.

Import this module to register all built-in parity tests.
"""

from .grayscale import register_grayscale_parity

# Register all built-in parity tests
register_grayscale_parity()

__all__ = ['register_grayscale_parity']
