"""Filter Explorer - Interactive filter testing with node-based pipeline builder.

This file is a wrapper that runs the Filter Explorer from the main imagestag package.
The actual implementation is now in imagestag.tools.filter_explorer.
"""

from imagestag.tools.filter_explorer import main, FilterExplorerApp, index

if __name__ in {'__main__', '__mp_main__'}:
    main()
