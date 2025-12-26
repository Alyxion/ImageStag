# Documentation Generator
"""
Generate markdown documentation from filter and preset definitions.

This tool extracts documentation from:
- Filter class docstrings and type annotations
- Preset definitions in the registry

Usage:
    # Generate all docs to docs/api/
    poetry run python -m imagestag.tools.docgen

    # Custom output directory
    poetry run python -m imagestag.tools.docgen --output docs/reference

    # Generate only filters or presets
    poetry run python -m imagestag.tools.docgen --filters-only
    poetry run python -m imagestag.tools.docgen --presets-only

    # Programmatic usage
    from imagestag.tools.docgen import generate_docs
    generate_docs(output_dir='docs/api')
"""

from __future__ import annotations

import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imagestag.filters.base import FilterInfo


@dataclass
class DocGenConfig:
    """Configuration for documentation generation."""
    output_dir: Path = Path('docs/api')
    filters: bool = True
    presets: bool = True
    index: bool = True


def generate_filter_docs(output_dir: Path, include_thumbnails: bool = True) -> dict[str, list[str]]:
    """Generate markdown documentation for all filters.

    :param output_dir: Directory to write filter docs
    :param include_thumbnails: Include thumbnail images from gallery
    :returns: Dict mapping category to list of filter names
    """
    from imagestag.filters.base import get_all_filters_info

    filters_dir = output_dir / 'filters'
    filters_dir.mkdir(parents=True, exist_ok=True)

    gallery_dir = output_dir / 'gallery' / 'filters'

    catalog = get_all_filters_info()
    categories: dict[str, list[tuple[str, 'FilterInfo']]] = {}

    # Group by category
    for name, info in sorted(catalog.items()):
        cat = info.category or 'other'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((name, info))

    # Generate individual filter pages
    for name, info in catalog.items():
        md = info.to_markdown()

        # Add thumbnail if available
        if include_thumbnails:
            thumb_path = gallery_dir / f'{name.lower()}.jpg'
            if thumb_path.exists():
                thumb_ref = f'\n![{name} example](../gallery/filters/{name.lower()}.jpg)\n'
                # Insert after title
                lines = md.split('\n')
                lines.insert(2, thumb_ref)
                md = '\n'.join(lines)

        (filters_dir / f'{name.lower()}.md').write_text(md)

    # Generate category index pages
    for cat, filters in categories.items():
        lines = [f'# {cat.title()} Filters', '']

        for name, info in sorted(filters, key=lambda x: x[0]):
            # Add thumbnail inline if available
            if include_thumbnails:
                thumb_path = gallery_dir / f'{name.lower()}.jpg'
                if thumb_path.exists():
                    lines.append(f'[![{name}](../gallery/filters/{name.lower()}.jpg)](./{name.lower()}.md)')
                    lines.append('')

            lines.append(f'## [{name}](./{name.lower()}.md)')
            lines.append('')
            lines.append(info.summary or info.description.split('\n')[0])
            lines.append('')

            # Quick parameter reference
            if info.parameters:
                params = ', '.join(f'`{p.name}`' for p in info.parameters[:4])
                if len(info.parameters) > 4:
                    params += ', ...'
                lines.append(f'**Parameters:** {params}')
                lines.append('')

        (filters_dir / f'_{cat}.md').write_text('\n'.join(lines))

    return {cat: [name for name, _ in filters] for cat, filters in categories.items()}


def generate_preset_docs(output_dir: Path, include_thumbnails: bool = True) -> list[tuple[str, str, str]]:
    """Generate markdown documentation for all presets.

    :param output_dir: Directory to write preset docs
    :param include_thumbnails: Include thumbnail images from gallery
    :returns: List of (key, name, category) tuples
    """
    from imagestag.tools.preset_registry import PRESETS

    presets_dir = output_dir / 'presets'
    presets_dir.mkdir(parents=True, exist_ok=True)

    gallery_dir = output_dir / 'gallery' / 'presets'

    preset_list = []

    for preset in PRESETS.values():
        md = preset.to_markdown()  # Use the Preset's own method

        # Add thumbnail if available
        if include_thumbnails:
            thumb_path = gallery_dir / f'{preset.key}.jpg'
            if thumb_path.exists():
                thumb_ref = f'\n![{preset.name} example](../gallery/presets/{preset.key}.jpg)\n'
                # Insert after title
                lines = md.split('\n')
                lines.insert(2, thumb_ref)
                md = '\n'.join(lines)

        (presets_dir / f'{preset.key}.md').write_text(md)
        preset_list.append((preset.key, preset.name, preset.category.name))

    # Generate preset index
    categories: dict[str, list] = {}
    for key, name, cat in preset_list:
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, name))

    lines = ['# Presets', '', 'Pre-built filter graphs for common operations.', '']

    for cat, presets in sorted(categories.items()):
        lines.append(f'## {cat.title()}')
        lines.append('')
        for key, name in presets:
            # Add thumbnail inline if available
            if include_thumbnails:
                thumb_path = gallery_dir / f'{key}.jpg'
                if thumb_path.exists():
                    lines.append(f'[![{name}](../gallery/presets/{key}.jpg)](./{key}.md)')
                    lines.append('')
            lines.append(f'- [{name}](./{key}.md)')
        lines.append('')

    (presets_dir / '_index.md').write_text('\n'.join(lines))

    return preset_list


def generate_index(output_dir: Path, filter_categories: dict, preset_list: list):
    """Generate main documentation index.

    :param output_dir: Output directory
    :param filter_categories: Dict of category -> filter names
    :param preset_list: List of (key, name, category) tuples
    """
    lines = [
        '# ImageStag API Reference',
        '',
        'Auto-generated documentation from source code.',
        '',
        '## Filters',
        '',
    ]

    for cat, filters in sorted(filter_categories.items()):
        lines.append(f'### [{cat.title()}](./filters/_{cat}.md)')
        lines.append('')
        # List first few filters
        sample = filters[:5]
        for name in sample:
            lines.append(f'- [{name}](./filters/{name.lower()}.md)')
        if len(filters) > 5:
            lines.append(f'- *...and {len(filters) - 5} more*')
        lines.append('')

    lines.append('## Presets')
    lines.append('')
    lines.append('See [Presets Index](./presets/_index.md)')
    lines.append('')

    for key, name, cat in preset_list[:5]:
        lines.append(f'- [{name}](./presets/{key}.md)')
    if len(preset_list) > 5:
        lines.append(f'- *...and {len(preset_list) - 5} more*')
    lines.append('')

    (output_dir / 'README.md').write_text('\n'.join(lines))


def generate_docs(
    output_dir: str | Path = 'docs/api',
    filters: bool = True,
    presets: bool = True,
    index: bool = True,
) -> dict:
    """Generate all documentation.

    :param output_dir: Output directory path
    :param filters: Generate filter documentation
    :param presets: Generate preset documentation
    :param index: Generate index page
    :returns: Summary dict with counts
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    summary = {'filters': 0, 'presets': 0, 'categories': 0}

    filter_categories = {}
    preset_list = []

    if filters:
        filter_categories = generate_filter_docs(output_path)
        summary['filters'] = sum(len(f) for f in filter_categories.values())
        summary['categories'] = len(filter_categories)

    if presets:
        preset_list = generate_preset_docs(output_path)
        summary['presets'] = len(preset_list)

    if index:
        generate_index(output_path, filter_categories, preset_list)

    return summary


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate ImageStag API documentation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                         # Generate to docs/api/
  %(prog)s --output docs/reference # Custom output directory
  %(prog)s --filters-only          # Only filter docs
  %(prog)s --presets-only          # Only preset docs
"""
    )
    parser.add_argument(
        '--output', '-o',
        default='docs/api',
        help='Output directory (default: docs/api)'
    )
    parser.add_argument(
        '--filters-only',
        action='store_true',
        help='Generate only filter documentation'
    )
    parser.add_argument(
        '--presets-only',
        action='store_true',
        help='Generate only preset documentation'
    )
    args = parser.parse_args()

    filters = not args.presets_only
    presets = not args.filters_only

    print(f'Generating documentation to {args.output}/')

    summary = generate_docs(
        output_dir=args.output,
        filters=filters,
        presets=presets,
    )

    print(f'Generated:')
    print(f'  - {summary["filters"]} filters in {summary["categories"]} categories')
    print(f'  - {summary["presets"]} presets')
    print(f'Done!')


if __name__ == '__main__':
    main()
