"""Stagforge file formats.

This module contains document serialization and file I/O classes.
"""

from .sfr import SFRDocument, ViewState, SavedSelection, VERSION
from .document_generator import (
    generate_document_identity,
    generate_document_name,
    generate_document_color,
    generate_document_icon,
    create_empty_document,
    create_sample_document,
    get_adjectives,
    get_nouns,
    get_icons,
)

# Backwards compatibility alias
Document = SFRDocument

__all__ = [
    # SFR format
    'SFRDocument',
    'Document',
    'ViewState',
    'SavedSelection',
    'VERSION',
    # Document generation
    'generate_document_identity',
    'generate_document_name',
    'generate_document_color',
    'generate_document_icon',
    'create_empty_document',
    'create_sample_document',
    'get_adjectives',
    'get_nouns',
    'get_icons',
]
