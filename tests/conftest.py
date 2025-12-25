"""
Pytest fixtures for ImageStag tests
"""

import pytest

from imagestag.samples import SAMPLES_DIR

# Enable NiceGUI testing plugin for UI component tests
pytest_plugins = ['nicegui.testing.user_plugin']


@pytest.fixture(scope="module")
def stag_image_data() -> bytes:
    """
    Returns the stag image data for testing.
    :return: The jpeg data
    """
    with open(SAMPLES_DIR / "images" / "stag.jpg", "rb") as f:
        yield f.read()
